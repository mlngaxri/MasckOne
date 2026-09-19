from __future__ import annotations

from masck_one.structural_frame_actuator_reactions import REACTION_IDS
from masck_one.treatment_mounted_four_zone_v5 import (
    SCHEMA_V5,
    SOURCE_MAIN_SHA,
    SOURCE_TREATMENT_HEAD_SHA,
    build_mounted_four_zone_architecture_v5,
    integral_flexure_screen,
    manifest_v5,
)
from masck_one.treatment_terminal_datum_preload import SOURCE_CELL6_HEAD_SHA


def test_v5_integral_preload_flexures_form_one_backbone_and_preserve_sweeps():
    architecture, datums = build_mounted_four_zone_architecture_v5()
    assert tuple(station.reaction_id for station in architecture.stations) == REACTION_IDS
    assert tuple(item.reaction_id for item in datums.stations) == REACTION_IDS
    for station in architecture.stations:
        material = dict(station.material_parts)
        reference = dict(station.reference_parts)
        assert material["fixed_backbone"].isValid()
        assert len(material["fixed_backbone"].Solids()) == 1
        assert max(station.nominal_source_intersections_mm3.values()) == 0.0
        assert max(station.nominal_protected_intersections_mm3.values()) == 0.0
        assert station.nominal_shell_intersection_mm3 == 0.0
        assert station.operational_fixed_intersection_mm3 == 0.0
        assert station.operational_source_intersection_mm3 == 0.0
        assert station.operational_protected_intersection_mm3 == 0.0
        assert station.operational_shell_intersection_mm3 == 0.0
        assert station.service_source_intersection_mm3 == 0.0
        assert station.service_protected_intersection_mm3 == 0.0
        assert station.service_shell_intersection_mm3 == 0.0
        assert "terminal_x_flexure_beam" in reference
        assert "terminal_z_flexure_beam" in reference
        assert "terminal_preload_x_free_reference" in reference
        assert "terminal_x_lossy_backup_reference" in reference
        flexure = station.truss_screen["integral_preload_flexure"]
        assert flexure["architecture_rule"].startswith("FLEXURES_ONLY_MAINTAIN_DATUM_CONTACT")


def test_integral_flexure_screen_has_preload_margin_without_high_stress_proxy():
    screen = integral_flexure_screen()
    x = screen["x_flexure"]
    z = screen["z_flexure"]
    for axis in (x, z):
        assert axis["preload_target_N"] == 0.30
        assert 0.10 < axis["preload_deflection_seed_mm"] < 0.20
        assert axis["preload_root_stress_proxy_MPa"] < 35.0
    assert screen["physical_validation"].startswith("OPEN_")


def test_v5_manifest_removes_spring_insert_interfaces_but_keeps_bumper_and_material_open():
    architecture, datums = build_mounted_four_zone_architecture_v5()
    manifest = manifest_v5(architecture, datums)
    assert manifest["schema"] == SCHEMA_V5
    assert manifest["source_main_sha"] == SOURCE_MAIN_SHA
    assert manifest["source_cell6_head_sha"] == SOURCE_CELL6_HEAD_SHA
    assert manifest["source_treatment_head_sha"] == SOURCE_TREATMENT_HEAD_SHA
    assert manifest["physical_validation_eligible"] is False
    assert "INTEGRAL_RELIEVED_PRELOAD_TONGUES" in manifest["mechanical_status"]
    assert manifest["part_count_change_vs_spring_insert_direction"].startswith("REMOVES_SEPARATE_X_Z_SPRING_INSERTS")
    assert manifest["buttery_mechanics_intent"].startswith("FREE_RAIL_APPROACH")
    assert manifest["physical_validation"].startswith("OPEN_")
    assert manifest["supersedes_as_v1_baseline"].endswith("V4")
