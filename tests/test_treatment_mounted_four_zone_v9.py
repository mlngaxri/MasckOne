from __future__ import annotations

import pytest

from masck_one.structural_frame_actuator_reactions import REACTION_IDS
from masck_one.treatment_mounted_four_zone_v9 import (
    SCHEMA_V9,
    SOURCE_CELL6_HEAD_SHA,
    build_mounted_four_zone_architecture_v9,
    fusion_handoff_manifest,
    manifest_v9,
)


@pytest.fixture(scope="module")
def built_v9():
    return build_mounted_four_zone_architecture_v9()


def test_v9_builds_all_four_live_source_bound_guided_stations(built_v9):
    architecture, datums = built_v9
    assert datums.source_cell6_head_sha == SOURCE_CELL6_HEAD_SHA
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
        datum = station.truss_screen["terminal_datum_preload_v4"]
        assert datum["contact_resultant_alignment"]["preload_couple_proxy_Nmm"] == 0.0
        assert max(station.truss_screen["v9_material_partition_mm3"].values()) == 0.0


def test_v9_preserves_nominal_operational_and_full_service_clearance(built_v9):
    architecture, _datums = built_v9
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
        assert len(station.operational_sweep.Solids()) > 1
        assert len(station.service_sweep.Solids()) > 1


def test_v9_manifest_records_kernel_successor_and_fusion_handoff(built_v9):
    architecture, datums = built_v9
    manifest = manifest_v9(architecture, datums)
    assert manifest["schema"] == SCHEMA_V9
    assert "COAXIAL_RIGID_MASTER_PRELOAD_PAIRS" in manifest["selected_buttery_candidate"]
    assert manifest["V8_rejection"].startswith("SUPERSEDED_AS_CURRENT_CANDIDATE")
    assert "BOOLEAN_FREE" in manifest["verification_revision"]
    assert manifest["physical_validation_eligible"] is False

    handoff = fusion_handoff_manifest(architecture, datums)
    assert handoff["cad_platform"] == "AUTODESK_FUSION_360"
    assert handoff["schema"] == "MASCK_ONE_TREATMENT_FUSION_HANDOFF_V2"
    assert handoff["reference_sweep_semantics"].startswith("BOOLEAN_FREE")
    assert len(handoff["stations"]) == 4
    for station in handoff["stations"]:
        assert station["carrier_insertion_direction_world_unit"] == [0.0, -1.0, 0.0]
        assert station["carrier_service_withdrawal_direction_world_unit"] == [0.0, 1.0, 0.0]
        assert station["terminal_contact_alignment"]["preload_couple_proxy_Nmm"] == 0.0
