from __future__ import annotations

from masck_one.primary_control_haptic_v10 import (
    FREE_TO_INSTALLED_MEMBRANE_COMPRESSION_SEED_MM,
    MIN_CAPTURE_HOSTILE_INTERSECTION_MM3,
    MIN_GROOVE_LIGAMENT_TO_BARREL_OD_MM,
    SCHEMA,
    SOURCE_MAIN_SHA,
    build_primary_control_haptic_architecture_v10,
)


def test_v10_integral_capture_is_clear_at_rest_but_engages_hostile_overpull():
    architecture = build_primary_control_haptic_architecture_v10()

    assert architecture.source_main_sha == SOURCE_MAIN_SHA
    assert architecture.capture_flange_root_overlap_mm3 > 0.0
    assert architecture.capture_rest_bushing_intersection_mm3 == 0.0
    assert architecture.capture_at_nominal_limit_intersection_mm3 == 0.0
    assert architecture.capture_hostile_overpull_intersection_mm3 >= MIN_CAPTURE_HOSTILE_INTERSECTION_MM3


def test_v10_installed_diaphragm_has_real_shell_reaction_without_rigid_overlap():
    architecture = build_primary_control_haptic_architecture_v10()
    refs = dict(architecture.reference_parts)

    assert architecture.diaphragm_groove_removed_mm3 > 0.0
    assert architecture.installed_diaphragm_shell_intersection_mm3 == 0.0
    assert architecture.installed_diaphragm_moving_intersection_mm3 == 0.0
    assert architecture.groove_outer_ligament_mm >= MIN_GROOVE_LIGAMENT_TO_BARREL_OD_MM
    assert "wet_diaphragm_installed_return_reference" in refs
    installed = refs["wet_diaphragm_installed_return_reference"]
    assert installed.isValid() and len(installed.Solids()) == 1 and installed.Volume() > 0.0


def test_v10_keeps_free_manufactured_elastomer_separate_from_installed_reference():
    architecture = build_primary_control_haptic_architecture_v10()
    material = dict(architecture.material_parts)
    refs = dict(architecture.reference_parts)
    manifest = architecture.manifest()

    assert "wet_diaphragm" in material
    assert "wet_diaphragm_installed_return_reference" in refs
    assert manifest["diaphragm"]["manufactured_free_geometry"] == "wet_diaphragm"
    assert manifest["diaphragm"]["installed_deformed_reference"] == "wet_diaphragm_installed_return_reference"
    assert FREE_TO_INSTALLED_MEMBRANE_COMPRESSION_SEED_MM > 0.0
    assert manifest["diaphragm"]["guidance_role"].startswith("NONE_")


def test_v10_preserves_low_cost_precision_feel_rule_and_package_clearance():
    architecture = build_primary_control_haptic_architecture_v10()
    manifest = architecture.manifest()

    assert manifest["schema"] == SCHEMA
    assert max(architecture.keepout_intersections_mm3.values(), default=0.0) == 0.0
    assert "ZERO_EXTRA_REST_FASTENER" in manifest["cost_rule"]
    assert "PRECISION_FEEL_ONLY" in manifest["tactile_reference_rule"]
    assert manifest["physical_validation_eligible"] is False
    assert "SUBJECTIVE_FEEL" in manifest["physical_validation"]
