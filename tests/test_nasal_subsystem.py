import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.coverage import REGION_T_NOSE_PHILTRUM, build_facial_coverage_mesh
from masck_one.facial_surface import build_planar_development_surface
from masck_one.interface_topology import build_compliant_interface_topology
from masck_one.nasal_subsystem import (
    ROLE_BRIDGE_DORSUM,
    ROLE_LOBE,
    ROLE_PHILTRUM,
    ROLE_SIDEWALL_LEFT,
    ROLE_SIDEWALL_RIGHT,
    build_nasal_subsystem_topology,
    derive_nasal_development_boundaries,
)
from masck_one.protected_volumes import build_protected_volumes


def _build():
    authority = load_authority()
    reference = build_facial_reference(authority)
    surface = build_planar_development_surface(authority)
    protected = build_protected_volumes(authority, reference, surface)
    coverage = build_facial_coverage_mesh(authority, reference, surface, protected)
    interface = build_compliant_interface_topology(authority, coverage)
    nasal = build_nasal_subsystem_topology(authority, coverage, interface, protected)
    return authority, protected, coverage, interface, nasal


def test_every_central_t_zone_target_is_assigned_once():
    _, _, coverage, interface, nasal = _build()
    expected = {
        triangle.triangle_index
        for triangle in coverage.triangles
        if triangle.region_id == REGION_T_NOSE_PHILTRUM and triangle.is_target
    }
    interface_expected = {
        assignment.triangle_index
        for assignment in interface.contact_assignments
        if assignment.parameter_zone_id == "INTERFACE_T_ZONE_NOSE_PHILTRUM"
    }
    assert nasal.triangle_indices == frozenset(expected)
    assert expected == interface_expected
    assert len(nasal.assignments) == len(expected)


def test_nasal_role_partition_conserves_central_target_area():
    _, _, coverage, _, nasal = _build()
    expected_area = sum(
        triangle.area_mm2
        for triangle in coverage.triangles
        if triangle.region_id == REGION_T_NOSE_PHILTRUM and triangle.is_target
    )
    assert nasal.total_target_area_mm2 == pytest.approx(expected_area, abs=1e-8)
    assert sum(nasal.role_area_mm2.values()) == pytest.approx(expected_area, abs=1e-8)


def test_all_five_functional_roles_are_present_on_current_development_mesh():
    _, _, _, _, nasal = _build()
    assert set(nasal.role_area_mm2) == {
        ROLE_BRIDGE_DORSUM,
        ROLE_SIDEWALL_LEFT,
        ROLE_SIDEWALL_RIGHT,
        ROLE_LOBE,
        ROLE_PHILTRUM,
    }
    assert all(area > 0.0 for area in nasal.role_area_mm2.values())


def test_left_and_right_sidewall_roles_are_sagittally_balanced():
    _, _, _, _, nasal = _build()
    assert nasal.role_area_mm2[ROLE_SIDEWALL_LEFT] == pytest.approx(
        nasal.role_area_mm2[ROLE_SIDEWALL_RIGHT],
        abs=1e-6,
    )


def test_boundary_derivation_uses_existing_nostril_geometry_without_arbitrary_width_factor():
    _, protected, coverage, _, _ = _build()
    boundaries = derive_nasal_development_boundaries(coverage, protected)
    assert boundaries.bridge_dorsum_half_width_mm == pytest.approx(
        abs(protected.nostril_left.zone.center.x),
        abs=1e-12,
    )
    assert boundaries.lobe_y_min_mm == pytest.approx(
        protected.nostril_left.zone.center.y - boundaries.nostril_envelope_half_height_mm,
        abs=1e-12,
    )
    assert boundaries.lobe_y_max_mm == pytest.approx(
        protected.nostril_left.zone.center.y + boundaries.nostril_envelope_half_height_mm,
        abs=1e-12,
    )
    assert "NOT_ANATOMICAL_TRUTH" in boundaries.evidence_status


def test_nasal_lobe_thickness_is_localized_and_does_not_leak_to_other_roles():
    authority, _, _, _, nasal = _build()
    lobe = nasal.role_by_id[ROLE_LOBE]
    assert lobe.nominal_thickness_mm == authority.number(
        "geometry", "nasal_lobe_membrane", "thickness_center_mm"
    ) == 0.30
    assert lobe.thickness_doe_mm == tuple(
        float(value)
        for value in authority.get("geometry", "nasal_lobe_membrane", "thickness_doe_mm")
    ) == (0.25, 0.30, 0.35)
    for role_id in (ROLE_BRIDGE_DORSUM, ROLE_SIDEWALL_LEFT, ROLE_SIDEWALL_RIGHT, ROLE_PHILTRUM):
        role = nasal.role_by_id[role_id]
        assert role.nominal_thickness_mm is None
        assert role.thickness_doe_mm == ()


def test_protected_nostrils_never_enter_nasal_contact_role_assignments():
    _, _, coverage, _, nasal = _build()
    coverage_by_id = {triangle.triangle_index: triangle for triangle in coverage.triangles}
    assert all(coverage_by_id[assignment.triangle_index].protected_zone_id is None for assignment in nasal.assignments)
    assert all(coverage_by_id[assignment.triangle_index].is_target for assignment in nasal.assignments)


def test_philtrum_role_remains_present_between_nose_and_mouth_exclusion():
    _, _, coverage, _, nasal = _build()
    philtrum = [assignment for assignment in nasal.assignments if assignment.role_id == ROLE_PHILTRUM]
    assert philtrum
    assert all(
        coverage.t_zone_definition.stem_y_min_mm <= assignment.centroid_y_mm < nasal.boundaries.lobe_y_min_mm
        for assignment in philtrum
    )


def test_nasal_topology_is_deterministic_and_not_validation_eligible():
    *_, first = _build()
    *_, second = _build()
    assert first.topology_sha256 == second.topology_sha256
    assert first.manifest() == second.manifest()
    assert first.anatomical_validation_eligible is False
    assert "NOT_ANATOMICAL" in first.evidence_status
