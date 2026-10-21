from __future__ import annotations

from masck_one.primary_control_haptic_v8 import (
    MIN_RECESS_INNER_LIGAMENT_MM,
    MIN_RECESS_OUTER_BARREL_COVER_MM,
    MIN_SIDE_MAGNET_RADIAL_POLYMER_COVER_MM,
    MIN_SIDE_MAGNET_TO_LOWER_GUIDE_AXIAL_CLEARANCE_MM,
    SCHEMA,
    SOURCE_MAIN_SHA,
    build_primary_control_haptic_architecture_v8,
)


def test_v8_removes_rear_hall_support_and_rear_sensor_reference():
    architecture = build_primary_control_haptic_architecture_v8()
    material_names = {name for name, _shape in architecture.material_parts}
    reference_names = {name for name, _shape in architecture.reference_parts}

    assert architecture.source_main_sha == SOURCE_MAIN_SHA
    assert "hall_pcb_support" not in material_names
    assert "hall_sensor_envelope" not in reference_names
    assert "hall_side_sensor_fpc_envelope" in reference_names
    assert "hall_flex_tail_reference" in reference_names


def test_v8_restores_old_axial_magnet_cavity_and_traps_new_off_axis_target():
    architecture = build_primary_control_haptic_architecture_v8()

    assert architecture.restored_axial_cavity_polymer_mm3 > 0.0
    assert architecture.side_magnet_cavity_removed_mm3 > 0.0
    assert architecture.side_magnet_polymer_intersection_mm3 == 0.0
    assert architecture.side_magnet_radial_polymer_cover_mm >= MIN_SIDE_MAGNET_RADIAL_POLYMER_COVER_MM
    assert architecture.side_magnet_to_lower_guide_axial_clearance_mm >= MIN_SIDE_MAGNET_TO_LOWER_GUIDE_AXIAL_CLEARANCE_MM


def test_v8_side_sensor_and_flex_are_outside_full_motion_envelope():
    architecture = build_primary_control_haptic_architecture_v8()

    assert architecture.motion_sweep.isValid()
    assert architecture.sensor_motion_intersection_mm3 == 0.0
    assert architecture.flex_motion_intersection_mm3 == 0.0


def test_v8_sensor_recess_preserves_bore_and_outer_barrel_ligaments():
    architecture = build_primary_control_haptic_architecture_v8()

    assert architecture.sensor_recess_removed_mm3 > 0.0
    assert architecture.flex_channel_removed_mm3 > 0.0
    assert architecture.recess_inner_ligament_mm >= MIN_RECESS_INNER_LIGAMENT_MM
    assert architecture.recess_outer_barrel_cover_mm >= MIN_RECESS_OUTER_BARREL_COVER_MM


def test_v8_manifest_keeps_sensor_transfer_and_bonding_unvalidated():
    architecture = build_primary_control_haptic_architecture_v8()
    manifest = architecture.manifest()
    sensor = manifest["sensor"]

    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes"].endswith("COLLIDING_WITH_FULL_STEM_TRAVEL")
    assert sensor["legacy_rear_pcb_support_removed"] is True
    assert sensor["sensor_full_motion_intersection_mm3"] == 0.0
    assert sensor["flex_full_motion_intersection_mm3"] == 0.0
    assert sensor["electrical_sensor_selected"] is False
    assert sensor["magnetic_transfer_validated"] is False
    assert sensor["bond_process_validated"] is False
    assert manifest["physical_validation_eligible"] is False


def test_v8_recomputed_external_keepouts_remain_clear():
    architecture = build_primary_control_haptic_architecture_v8()
    assert max(architecture.keepout_intersections_mm3.values(), default=0.0) == 0.0
