from __future__ import annotations

from masck_one.primary_control_haptic_v3 import (
    CAP_STEM_ROOT_OVERLAP_MM,
    MIN_CONNECTED_OVERLAP_MM3,
    RIB_STEM_ROOT_OVERLAP_MM,
    SCHEMA,
    SOURCE_MAIN_SHA,
    build_primary_control_haptic_architecture_v3,
)


def _part(architecture, name):
    return dict(architecture.material_parts)[name]


def test_v3_moving_polymer_is_one_positive_manufactured_solid():
    architecture = build_primary_control_haptic_architecture_v3()
    moving = _part(architecture, "primary_control_cap_stem")

    assert architecture.source_main_sha == SOURCE_MAIN_SHA
    assert moving.isValid()
    assert len(moving.Solids()) == 1
    assert moving.Volume() > 0.0
    assert CAP_STEM_ROOT_OVERLAP_MM > 0.0
    assert RIB_STEM_ROOT_OVERLAP_MM > 0.0
    assert architecture.joint_overlap_mm3["cap_to_stem"] >= MIN_CONNECTED_OVERLAP_MM3
    assert architecture.joint_overlap_mm3["stem_to_anti_rotation_rib"] >= MIN_CONNECTED_OVERLAP_MM3


def test_v3_preserves_current_keepouts_and_continuous_motion_reference():
    architecture = build_primary_control_haptic_architecture_v3()

    assert max(architecture.keepout_intersections_mm3.values(), default=0.0) == 0.0
    assert architecture.motion_sweep.isValid()
    assert architecture.motion_sweep.Solids()


def test_v3_manifest_encodes_tactile_not_acoustic_reference_and_cost_rule():
    architecture = build_primary_control_haptic_architecture_v3()
    manifest = architecture.manifest()

    assert manifest["schema"] == SCHEMA
    assert manifest["source_main_sha"] == SOURCE_MAIN_SHA
    assert "DO_NOT_REPLICATE_SOUND" in manifest["tactile_reference_rule"]
    assert "NO INTENTIONAL LIGHTER_PING" in manifest["sound_rule"]
    assert "GEOMETRY_PRELOAD_CONSTRAINT_DAMPING" in manifest["cost_rule"]
    assert manifest["moving_part_connectivity"]["visible_cap_geometry_changed"] is False
    assert manifest["moving_part_connectivity"]["external_rib_projection_changed"] is False
    assert manifest["physical_validation_eligible"] is False
