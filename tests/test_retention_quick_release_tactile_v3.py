from __future__ import annotations

from masck_one import retention_quick_release_tactile as v1
from masck_one import retention_quick_release_tactile_v2 as v2
from masck_one.retention_quick_release_tactile_v3 import (
    BUMPER_RIB_RELIEF_WIDTH_Y_MM,
    MIN_BUMPER_RELIEF_SIDE_CLEARANCE_MM,
    SCHEMA,
    SUPERSEDES_SCHEMA,
    build_retention_quick_release_tactile_v3,
)


def test_v3_keeps_exact_bezier_cam_and_single_owner_lineage():
    candidate = build_retention_quick_release_tactile_v3()
    manifest = candidate.manifest()

    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes_schema"] == SUPERSEDES_SCHEMA == v2.SCHEMA
    assert manifest["owner_branch"] == v1.OWNER_BRANCH
    assert manifest["detent"]["cam_profile"] == v2.CAM_PROFILE_ID
    assert manifest["detent"]["faceted_contact_profile"] is False
    assert manifest["physical_validation_eligible"] is False


def test_relief_clears_rib_without_splitting_bumper_or_removing_free_engagement():
    candidate = build_retention_quick_release_tactile_v3()
    mechanism = candidate.mechanism

    assert candidate.bumper_relief_side_clearance_mm >= MIN_BUMPER_RELIEF_SIDE_CLEARANCE_MM
    assert BUMPER_RIB_RELIEF_WIDTH_Y_MM > v1.ANTI_ROTATION_RIB_WIDTH_Y_MM
    for bumper in (*mechanism.bumper_free_regions, *mechanism.bumper_installed_references):
        assert bumper.val().isValid()
        assert len(bumper.val().Solids()) == 1
        assert bumper.val().Volume() > 0.0

    assert mechanism.inboard_bumper_free_interference_mm3 > 0.0
    assert mechanism.outboard_bumper_free_interference_mm3 > 0.0
    assert mechanism.inboard_bumper_installed_interference_mm3 == 0.0
    assert mechanism.outboard_bumper_installed_interference_mm3 == 0.0


def test_v3_preserves_low_play_guidance_and_independent_abuse_stops():
    mechanism = build_retention_quick_release_tactile_v3().mechanism

    assert 0.0 < mechanism.rail_radial_clearance_mm <= v1.MAX_SPOOL_RAIL_RADIAL_CLEARANCE_MM
    assert 0.0 < mechanism.anti_rotation_side_clearance_mm <= v1.MAX_ANTI_ROTATION_SIDE_CLEARANCE_MM
    assert mechanism.flexure_free_slider_interference_mm3 > 0.0
    assert mechanism.flexure_installed_slider_interference_mm3 == 0.0
    assert mechanism.rigid_inboard_overtravel_intersection_mm3 > 0.0
    assert mechanism.rigid_outboard_overtravel_intersection_mm3 > 0.0


def test_v3_manifest_keeps_damping_and_physical_validation_firewall_explicit():
    manifest = build_retention_quick_release_tactile_v3().manifest()
    damping = manifest["end_state_damping"]

    assert damping["anti_rotation_rib_relief_width_y_mm"] == BUMPER_RIB_RELIEF_WIDTH_Y_MM
    assert damping["installed_reference_rib_overlap_mm3"] == [0.0, 0.0]
    assert damping["rigid_hard_stops_preserved"] is True
    assert "ANTI-ROTATION RIB" in manifest["quality_patch"]
    assert "SUBJECTIVE_FEEL" in manifest["physical_validation"]
