from dataclasses import replace

import cadquery as cq
import pytest

from masck_one.exterior_ingestion import (
    DIGITAL_EVIDENCE_STATUS,
    WORLD_FRAME_ID,
    ExteriorCandidateBinding,
    ExteriorIngestionError,
    ExteriorManufacturingClosure,
    assess_exterior_geometry,
    ingest_exterior_candidate,
    radial_wall_screen,
    replace_shell_only,
)
from masck_one.model import Component, build_model


CURRENT_MAIN = "628ec5f5766937433b1bdf8f30edc372924cf41e"


@pytest.fixture(scope="module")
def baseline():
    return build_model()


def _safe_ring_shell() -> Component:
    # Synthetic ingestion fixture only. It sits anterior of released package geometry,
    # outside all facial visual keepouts, inside the authority XY envelope, and carries
    # a true 2.0 mm radial wall. It is not Masck One product-form evidence.
    solid = (
        cq.Workplane("XY")
        .circle(84.0)
        .circle(82.0)
        .extrude(4.0)
        .translate((0.0, 0.0, 30.0))
    )
    return Component(
        name="rigid_shell",
        solid=solid,
        status="SYNTHETIC_INGESTION_TEST_FIXTURE",
        notes="Test-only annular shell fixture; never product geometry.",
    )


def _binding(**changes) -> ExteriorCandidateBinding:
    binding = ExteriorCandidateBinding(
        source_pr=70,
        source_head_sha="a" * 40,
        source_base_main_sha=CURRENT_MAIN,
        source_geometry_blob_sha="b" * 40,
        source_integration_blob_sha="c" * 40,
        source_evidence_blob_sha="d" * 40,
        source_manifest_sha256="e" * 64,
        world_frame_id=WORLD_FRAME_ID,
        ci_conclusion="SUCCESS",
        independent_review_disposition="APPROVED",
        blockers=(),
    )
    return replace(binding, **changes)


def _manufacturing(**changes) -> ExteriorManufacturingClosure:
    closure = ExteriorManufacturingClosure(
        eye_inner_edge_roll_radius_mm=3.0,
        eye_roll_geometry_status="FINAL_BREP_VERIFIED",
        tooling_architecture_status="DIGITAL_TOOLING_ARCHITECTURE_RESOLVED",
        mold_draft_screen_status="PASS",
        mold_draft_nominal_deg=1.0,
        secondary_operation_exceptions=(),
        mvp_design_review_status="APPROVED_FOR_MVP_FREEZE",
        physical_validation_eligible=False,
    )
    return replace(closure, **changes)


def test_radial_wall_screen_measures_actual_brep_not_control_net():
    thick = cq.Workplane("XY").circle(40.0).circle(38.2).extrude(4.0).val()
    thin = cq.Workplane("XY").circle(40.0).circle(38.8).extrude(4.0).val()

    thick_screen = radial_wall_screen(thick, z_levels_mm=(2.0,), radial_step_mm=0.25)
    thin_screen = radial_wall_screen(thin, z_levels_mm=(2.0,), radial_step_mm=0.25)

    assert thick_screen.minimum_wall_mm == pytest.approx(1.8, abs=0.01)
    assert thin_screen.minimum_wall_mm == pytest.approx(1.2, abs=0.01)
    assert thick_screen.sampled_ray_count == 24
    assert thin_screen.sampled_ray_count == 24


def test_candidate_source_gate_fails_closed_on_stale_frame_ci_review_or_blockers():
    cases = (
        (_binding(source_base_main_sha="f" * 40), "stale"),
        (_binding(world_frame_id="MASCK_ONE_OTHER_WORLD"), "canonical authority-world"),
        (_binding(ci_conclusion="IN_PROGRESS"), "CI is not SUCCESS"),
        (_binding(independent_review_disposition="REWORK"), "independent approval"),
        (_binding(blockers=("FINAL_BREP_WALL_BELOW_AUTHORITY_MINIMUM",)), "release blockers"),
    )
    for binding, message in cases:
        with pytest.raises(ExteriorIngestionError, match=message):
            binding.validate(reconstructed_main_sha=CURRENT_MAIN)


def test_manufacturing_closure_requires_final_brep_eye_roll_dfm_and_authority_draft(baseline):
    authority = baseline.authority
    with pytest.raises(ExteriorIngestionError, match="eye inner-edge roll"):
        _manufacturing(eye_inner_edge_roll_radius_mm=2.5).validate(authority)
    with pytest.raises(ExteriorIngestionError, match="final B-rep"):
        _manufacturing(eye_roll_geometry_status="CONTROL_NET_ONLY").validate(authority)
    with pytest.raises(ExteriorIngestionError, match="tooling/part-split"):
        _manufacturing(tooling_architecture_status="UNRESOLVED").validate(authority)
    with pytest.raises(ExteriorIngestionError, match="draft baseline"):
        _manufacturing(mold_draft_nominal_deg=0.0).validate(authority)
    with pytest.raises(ExteriorIngestionError, match="MVP exterior design"):
        _manufacturing(mvp_design_review_status="REWORK").validate(authority)
    with pytest.raises(ExteriorIngestionError, match="physical validation"):
        _manufacturing(physical_validation_eligible=True).validate(authority)


def test_complete_brep_assessment_checks_wall_packages_keepouts_and_released_waste_route(baseline):
    assessment = assess_exterior_geometry(baseline, _safe_ring_shell())
    assert assessment.accepted is True
    assert assessment.blockers == ()
    assert assessment.shell_valid is True
    assert assessment.shell_solid_count == 1
    assert assessment.wall_screen.minimum_wall_mm == pytest.approx(2.0, abs=0.01)
    assert assessment.wall_screen.minimum_wall_mm >= assessment.absolute_wall_requirement_mm
    assert all(volume <= 1e-5 for _, volume in assessment.package_intersection_mm3)
    assert all(volume <= 1e-5 for _, volume in assessment.protected_keepout_intersection_mm3)
    assert assessment.mixed_waste_route_a_clearance_mm >= assessment.mixed_waste_route_a_required_radius_mm
    assert len(assessment.released_waste_manifest_sha256) == 64
    assert assessment.physical_validation_eligible is False


def test_thin_actual_brep_is_rejected_even_when_authored_dimensions_could_claim_nominal_wall(baseline):
    thin = Component(
        "rigid_shell",
        cq.Workplane("XY").circle(84.0).circle(82.8).extrude(4.0).translate((0.0, 0.0, 30.0)),
        "SYNTHETIC_THIN_WALL_TEST",
    )
    assessment = assess_exterior_geometry(baseline, thin)
    assert assessment.wall_screen.minimum_wall_mm == pytest.approx(1.2, abs=0.01)
    assert "FINAL_BREP_WALL_BELOW_AUTHORITY_MINIMUM" in assessment.blockers
    assert assessment.accepted is False


def test_shell_substitution_preserves_every_foreign_lane_object_identity(baseline):
    candidate = _safe_ring_shell()
    integrated = replace_shell_only(baseline, candidate)
    assert integrated.shell is candidate
    for field in (
        "authority",
        "datums",
        "facial_reference",
        "facial_surface",
        "protected_volumes",
        "worn_pose_regression",
        "coverage_mesh",
        "compliant_interface_topology",
        "nasal_subsystem_topology",
        "nasal_interface",
        "actuator_envelopes",
        "water_reservoir_envelope",
        "waste_cartridge_envelope",
        "battery_reference_envelope",
        "visual_keepouts",
    ):
        assert getattr(integrated, field) is getattr(baseline, field)


def test_green_reviewed_candidate_can_ingest_as_one_object_with_deterministic_receipt(baseline):
    candidate = _safe_ring_shell()
    integrated, receipt = ingest_exterior_candidate(
        baseline,
        candidate,
        binding=_binding(),
        manufacturing=_manufacturing(),
        reconstructed_main_sha=CURRENT_MAIN,
    )
    assert integrated.shell is candidate
    assert receipt.accepted is True
    assert receipt.evidence_status == DIGITAL_EVIDENCE_STATUS
    assert receipt.physical_validation_eligible is False
    assert len(receipt.receipt_sha256) == 64
    assert receipt.receipt_sha256 == receipt.receipt_sha256
    assert receipt.manifest()["receipt_sha256"] == receipt.receipt_sha256


def test_ingestion_refuses_noncanonical_candidate_before_geometry_substitution(baseline):
    with pytest.raises(ExteriorIngestionError, match="canonical authority-world"):
        ingest_exterior_candidate(
            baseline,
            _safe_ring_shell(),
            binding=_binding(world_frame_id="UNBOUND_LOCAL_FRAME"),
            manufacturing=_manufacturing(),
            reconstructed_main_sha=CURRENT_MAIN,
        )
