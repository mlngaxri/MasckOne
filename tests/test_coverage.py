from __future__ import annotations

import math

import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.coverage import (
    CoverageError,
    REGION_ACTIVE_OTHER,
    REGION_T_FOREHEAD,
    REGION_T_NOSE_PHILTRUM,
    TZoneDevelopmentDefinition,
    build_facial_coverage_mesh,
    build_t_zone_development_definition,
)
from masck_one.facial_surface import build_planar_development_surface
from masck_one.protected_volumes import build_protected_volumes


def _build():
    authority = load_authority()
    reference = build_facial_reference(authority)
    surface = build_planar_development_surface(authority)
    protected = build_protected_volumes(authority, reference, surface)
    coverage = build_facial_coverage_mesh(authority, reference, surface, protected)
    return authority, reference, surface, protected, coverage


def test_every_surface_triangle_has_exactly_one_coverage_cell():
    _, _, surface, _, coverage = _build()

    assert len(coverage.triangles) == surface.mesh.triangle_count
    assert [cell.triangle_index for cell in coverage.triangles] == list(range(surface.mesh.triangle_count))


def test_partition_conserves_surface_area():
    _, _, _, _, coverage = _build()

    assert coverage.area_conservation_error_mm2 < 1e-8
    assert coverage.total_surface_area_mm2 == pytest.approx(
        coverage.target_area_mm2 + coverage.protected_area_mm2,
        abs=1e-8,
    )


def test_authority_coverage_thresholds_are_consumed_exactly():
    authority, _, _, _, coverage = _build()

    assert coverage.aggregate_min_percent == authority.number("coverage", "aggregate_min_percent") == 90.0
    assert coverage.t_zone_min_percent == authority.number("coverage", "t_zone_min_percent") == 90.0
    assert coverage.unexplained_hole_max_mm2 == authority.number("coverage", "unexplained_hole_max_mm2") == 100.0


def test_t_zone_development_definition_is_derived_from_existing_geometry():
    authority, reference, _, protected, _ = _build()
    t_zone = build_t_zone_development_definition(authority, reference, protected)

    expected_stem_half_width = (
        abs(protected.nostril_right.zone.center.x)
        + protected.nostril_right.zone.envelope_width_mm / 2.0
    )
    assert t_zone.stem_half_width_mm == pytest.approx(expected_stem_half_width)
    assert t_zone.stem_y_min_mm == pytest.approx(-24.5)
    assert t_zone.stem_y_max_mm == pytest.approx(50.0)
    assert t_zone.forehead_half_width_mm == pytest.approx(54.5)
    assert t_zone.forehead_y_min_mm == pytest.approx(50.0)
    assert "NOT_ANATOMICAL_VALIDATION" in t_zone.evidence_status


def test_t_zone_stem_and_forehead_have_no_unexplained_vertical_gap():
    _, _, _, _, coverage = _build()
    t_zone = coverage.t_zone_definition

    assert t_zone.stem_y_max_mm == t_zone.forehead_y_min_mm


def test_segmentation_contains_active_other_and_both_t_zone_regions():
    _, _, _, _, coverage = _build()
    regions = set(coverage.region_area_mm2)

    assert REGION_ACTIVE_OTHER in regions
    assert REGION_T_FOREHEAD in regions
    assert REGION_T_NOSE_PHILTRUM in regions
    assert coverage.t_zone_target_area_mm2 > 0.0


def test_nose_to_upper_lip_philtrum_target_area_is_not_missing():
    _, _, _, _, coverage = _build()

    assert coverage.philtrum_target_area_mm2 > 0.0
    assert any(
        cell.region_id == REGION_T_NOSE_PHILTRUM
        and cell.is_target
        and coverage.t_zone_definition.stem_y_min_mm <= cell.centroid.y <= 0.0
        for cell in coverage.triangles
    )


def test_protected_cells_are_never_active_cleansing_targets():
    _, _, _, _, coverage = _build()

    assert coverage.protected_triangles
    assert all(not cell.is_target for cell in coverage.protected_triangles)
    assert all(cell.protected_zone_id is not None for cell in coverage.protected_triangles)
    assert all(not cell.is_t_zone_target for cell in coverage.protected_triangles)


def test_full_geometric_target_screen_is_100_percent_but_not_product_validation():
    _, _, _, _, coverage = _build()
    all_targets = [cell.triangle_index for cell in coverage.target_triangles]

    result = coverage.evaluate(
        all_targets,
        evidence_status="SYNTHETIC_ALL_TARGETS_TEST_FIXTURE",
        evidence_eligible=True,
    )

    assert result.aggregate_percent == pytest.approx(100.0)
    assert result.t_zone_percent == pytest.approx(100.0)
    assert result.largest_uncovered_hole_mm2 == 0.0
    assert result.numeric_gate_passed is True
    assert result.product_validation_status == "NUMERIC_SCREEN_PASS_NOT_PRODUCT_VALIDATION"
    assert coverage.anatomical_validation_eligible is False


def test_empty_coverage_fails_numeric_gate_and_has_uncovered_area():
    _, _, _, _, coverage = _build()

    result = coverage.evaluate([], evidence_status="SYNTHETIC_EMPTY_TEST_FIXTURE")

    assert result.aggregate_percent == 0.0
    assert result.t_zone_percent == 0.0
    assert result.largest_uncovered_hole_mm2 > 100.0
    assert result.numeric_gate_passed is False
    assert result.product_validation_status == "NUMERIC_GATE_FAIL"


def test_evaluation_hash_is_order_independent_for_same_covered_set():
    _, _, _, _, coverage = _build()
    subset = [cell.triangle_index for cell in coverage.target_triangles[:50]]

    forward = coverage.evaluate(subset, evidence_status="ORDER_TEST")
    reverse = coverage.evaluate(reversed(subset), evidence_status="ORDER_TEST")

    assert forward.evaluation_sha256 == reverse.evaluation_sha256


def test_protected_triangle_cannot_be_submitted_as_covered_target():
    _, _, _, _, coverage = _build()
    protected_id = coverage.protected_triangles[0].triangle_index

    with pytest.raises(CoverageError, match="non-target or unknown"):
        coverage.evaluate([protected_id], evidence_status="INVALID_TEST")


def test_unknown_triangle_index_is_rejected():
    _, _, _, _, coverage = _build()

    with pytest.raises(CoverageError, match="non-target or unknown"):
        coverage.evaluate([len(coverage.triangles) + 100], evidence_status="INVALID_TEST")


def test_segmentation_is_deterministic():
    *_, coverage_a = _build()
    *_, coverage_b = _build()

    assert coverage_a.segmentation_sha256 == coverage_b.segmentation_sha256
    assert coverage_a.region_area_mm2 == coverage_b.region_area_mm2


def test_target_area_is_bilaterally_balanced_on_neutral_symmetric_development_mesh():
    _, _, _, _, coverage = _build()
    left = sum(cell.area_mm2 for cell in coverage.target_triangles if cell.centroid.x < -1e-12)
    right = sum(cell.area_mm2 for cell in coverage.target_triangles if cell.centroid.x > 1e-12)

    assert left == pytest.approx(right, rel=0.0, abs=1e-6)


def test_invalid_t_zone_definition_with_gap_is_rejected():
    with pytest.raises(CoverageError, match="meet without an unexplained Y gap"):
        TZoneDevelopmentDefinition(
            stem_half_width_mm=20.0,
            stem_y_min_mm=-20.0,
            stem_y_max_mm=40.0,
            forehead_half_width_mm=50.0,
            forehead_y_min_mm=45.0,
        )


def test_all_areas_and_centroids_are_finite():
    _, _, _, _, coverage = _build()

    assert all(math.isfinite(cell.area_mm2) and cell.area_mm2 > 0.0 for cell in coverage.triangles)
    assert all(
        all(math.isfinite(value) for value in cell.centroid.as_tuple())
        for cell in coverage.triangles
    )
