from __future__ import annotations

import pytest

from masck_one.structural_frame_actuator_reactions import REACTION_IDS
from masck_one.treatment_mounted_four_zone_v8 import (
    SCHEMA_V8,
    build_mounted_four_zone_architecture_v8,
    fusion_handoff_manifest,
    manifest_v8,
)


@pytest.fixture(scope="module")
def built_v8():
    return build_mounted_four_zone_architecture_v8()


def test_v8_builds_all_four_moment_balanced_guided_stations(built_v8):
    architecture, datums = built_v8
    assert tuple(station.reaction_id for station in architecture.stations) == REACTION_IDS
    assert tuple(station.reaction_id for station in datums.stations) == REACTION_IDS
    for station in architecture.stations:
        material = dict(station.material_parts)
        reference = dict(station.reference_parts)
        assert "terminal_x_spring_installed" in material
        assert "terminal_z_spring_installed" in material
        assert "terminal_x_preload_shoe" in material
        assert "terminal_z_preload_shoe" in material
        assert "terminal_x_spring_free" in reference
        assert "terminal_z_spring_free" in reference
        assert station.truss_screen["terminal_datum_preload_v3"]["contact_resultant_alignment"]["preload_couple_proxy_Nmm"] == 0.0
        assert max(station.truss_screen["v8_material_partition_mm3"].values()) == 0.0


def test_v8_preserves_nominal_operational_and_service_clearance(built_v8):
    architecture, _datums = built_v8
    for station in architecture.stations:
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


def test_v8_manifest_rejects_v7_and_exposes_fusion_handoff(built_v8):
    architecture, datums = built_v8
    manifest = manifest_v8(architecture, datums)
    assert manifest["schema"] == SCHEMA_V8
    assert "COAXIAL_RIGID_MASTER_PRELOAD_PAIRS" in manifest["selected_buttery_candidate"]
    assert manifest["V7_rejection"].startswith("REJECTED_AS_CURRENT_CANDIDATE")
    assert manifest["physical_validation_eligible"] is False
    handoff = fusion_handoff_manifest(architecture, datums)
    assert handoff["cad_platform"] == "AUTODESK_FUSION_360"
    assert len(handoff["stations"]) == 4
    assert handoff["export_rules"]["manufactured_springs"] == "EXPORT_STRESS_FREE_BREP"
    for station in handoff["stations"]:
        assert station["carrier_insertion_direction_world_unit"] == [0.0, -1.0, 0.0]
        assert station["carrier_service_withdrawal_direction_world_unit"] == [0.0, 1.0, 0.0]
        assert station["terminal_contact_alignment"]["preload_couple_proxy_Nmm"] == 0.0
