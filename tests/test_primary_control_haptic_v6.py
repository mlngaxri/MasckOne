from __future__ import annotations

from masck_one.primary_control_haptic_v6 import (
    MIN_ROOT_OUTER_POLYMER_COVER_MM,
    SCHEMA,
    SOURCE_MAIN_SHA,
    build_primary_control_haptic_architecture_v6,
)


def test_v6_preload_leaf_is_one_rooted_manufactured_solid_with_shell_reaction():
    architecture = build_primary_control_haptic_architecture_v6()
    material = dict(architecture.material_parts)
    leaf = material["anti_rotation_preload_leaf_insert_molded"]
    shell = material["shell_with_primary_control_interface"]

    assert architecture.source_main_sha == SOURCE_MAIN_SHA
    assert leaf.isValid() and len(leaf.Solids()) == 1 and leaf.Volume() > 0.0
    assert shell.isValid() and shell.Solids() and shell.Volume() > 0.0
    assert architecture.leaf_root_shell_removed_mm3 > 0.0
    assert architecture.leaf_shell_intersection_mm3 == 0.0
    assert architecture.leaf_outer_polymer_cover_mm >= MIN_ROOT_OUTER_POLYMER_COVER_MM


def test_v6_replaces_free_floating_leaf_names_and_keeps_installed_reference():
    architecture = build_primary_control_haptic_architecture_v6()
    material_names = {name for name, _shape in architecture.material_parts}
    reference_names = {name for name, _shape in architecture.reference_parts}

    assert "anti_rotation_preload_leaf_free" not in material_names
    assert "anti_rotation_preload_leaf_insert_molded" in material_names
    assert "anti_rotation_leaf_installed_reference" not in reference_names
    assert "anti_rotation_leaf_rooted_installed_reference" in reference_names


def test_v6_manifest_does_not_turn_preload_seed_into_force_claim():
    architecture = build_primary_control_haptic_architecture_v6()
    manifest = architecture.manifest()
    preload = manifest["anti_rotation_preload"]

    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes"].endswith("FREE_FLOATING_ANTI_ROTATION_PRELOAD_LEAF_WITHOUT_REACTION_PATH")
    assert preload["architecture"].startswith("STAMPED_SPRING_METAL_ACTIVE_TONGUE")
    assert preload["separate_fastener_parts"] == 0
    assert preload["adhesive_required"] is False
    assert preload["preload_force_validated"] is False
    assert manifest["physical_validation_eligible"] is False
    assert manifest["tactile_generator_status"].startswith("CURRENT_SHORT_BEAM_CUSTOM_SPRING_REJECTED")
