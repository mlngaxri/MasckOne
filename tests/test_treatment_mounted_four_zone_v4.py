from __future__ import annotations

from masck_one.structural_frame_actuator_reactions import REACTION_IDS
from masck_one.treatment_mounted_four_zone_v4 import (
    SCHEMA_V4,
    SOURCE_MAIN_SHA,
    SOURCE_TREATMENT_HEAD_SHA,
    build_mounted_four_zone_architecture_v4,
    manifest_v4,
)
from masck_one.treatment_terminal_datum_preload import SOURCE_CELL6_HEAD_SHA


def test_v4_uses_deterministic_datums_without_promoting_unattached_preload_shoes_to_material():
    architecture, datums = build_mounted_four_zone_architecture_v4()
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
        assert "terminal_preload_x_installed" in reference
        assert "terminal_preload_z_installed" in reference
        assert "terminal_preload_x_installed" not in material
        terminal = station.truss_screen["terminal_datum_preload"]
        assert terminal["spring_root_attachment_status"].startswith("OPEN_EXPLICIT_CAPTURE_REQUIRED")


def test_v4_manifest_supersedes_overconstrained_v3_but_keeps_physical_closure_open():
    architecture, datums = build_mounted_four_zone_architecture_v4()
    manifest = manifest_v4(architecture, datums)
    assert manifest["schema"] == SCHEMA_V4
    assert manifest["source_main_sha"] == SOURCE_MAIN_SHA
    assert manifest["source_cell6_head_sha"] == SOURCE_CELL6_HEAD_SHA
    assert manifest["source_treatment_head_sha"] == SOURCE_TREATMENT_HEAD_SHA
    assert manifest["terminal_datum_preload_architecture_sha256"] == datums.architecture_sha256
    assert manifest["physical_validation_eligible"] is False
    assert "DETERMINISTIC_RIGID_X_Z_MASTER_DATUMS" in manifest["mechanical_status"]
    assert manifest["normal_reaction_path"].startswith("RIGID_MASTER_DATUMS")
    assert manifest["buttery_service_intent"].startswith("CLEARANCE_RAIL_APPROACH")
    assert manifest["material_boundary"].startswith("RIGID_DATUMS_AND_BACKUPS_ARE_MATERIAL")
    assert manifest["supersedes_as_v1_baseline"].endswith("V3")
