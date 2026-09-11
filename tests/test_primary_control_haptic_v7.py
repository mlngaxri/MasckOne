from __future__ import annotations

from masck_one.primary_control_haptic_v7 import (
    LOCK_AZIMUTHS_DEG,
    MIN_LOCK_HEAD_TO_BARREL_BORE_RADIAL_CLEARANCE_MM,
    MIN_RIGID_STOP_PROJECTED_AREA_FRACTION,
    SCHEMA,
    SOURCE_MAIN_SHA,
    build_primary_control_haptic_architecture_v7,
)


def test_v7_replaces_overlapping_landing_parts_with_one_connected_body():
    architecture = build_primary_control_haptic_architecture_v7()
    material = dict(architecture.material_parts)
    names = set(material)

    assert architecture.source_main_sha == SOURCE_MAIN_SHA
    assert "landing_stage_1" not in names
    assert "landing_stage_2" not in names
    assert "landing_progressive_overmold" in names

    landing = material["landing_progressive_overmold"]
    assert landing.isValid()
    assert len(landing.Solids()) == 1
    assert landing.Volume() > 0.0


def test_v7_mechanical_locks_remove_shelf_without_false_material_overlap():
    architecture = build_primary_control_haptic_architecture_v7()
    material = dict(architecture.material_parts)

    assert architecture.landing_lock_slot_removed_mm3 > 0.0
    assert architecture.landing_shell_intersection_mm3 == 0.0
    assert material["shell_with_primary_control_interface"].isValid()
    assert len(LOCK_AZIMUTHS_DEG) == 3
    assert architecture.lock_head_to_barrel_bore_clearance_mm >= MIN_LOCK_HEAD_TO_BARREL_BORE_RADIAL_CLEARANCE_MM


def test_v7_preserves_independent_rigid_abuse_stop_projected_area():
    architecture = build_primary_control_haptic_architecture_v7()

    assert architecture.rigid_stop_projected_area_fraction >= MIN_RIGID_STOP_PROJECTED_AREA_FRACTION
    assert architecture.rigid_stop_projected_area_fraction > 0.98


def test_v7_manifest_keeps_landing_feel_as_unvalidated_physical_behavior():
    architecture = build_primary_control_haptic_architecture_v7()
    manifest = architecture.manifest()
    landing = manifest["landing"]

    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes"].endswith("OVERLAPPING_TWO_PART_LANDING_STACK_WITHOUT_POSITIVE_RETENTION")
    assert landing["architecture"].startswith("ONE_PIECE_PROGRESSIVE_ELASTOMER")
    assert landing["separate_elastomer_landing_parts"] == 1
    assert landing["separate_fasteners"] == 0
    assert landing["adhesive_required"] is False
    assert landing["durometer_validated"] is False
    assert landing["compression_set_validated"] is False
    assert manifest["physical_validation_eligible"] is False
    assert "FORCE_TRAVEL" in manifest["physical_validation"]


def test_v7_recomputed_keepouts_remain_clear():
    architecture = build_primary_control_haptic_architecture_v7()
    assert max(architecture.keepout_intersections_mm3.values(), default=0.0) == 0.0
