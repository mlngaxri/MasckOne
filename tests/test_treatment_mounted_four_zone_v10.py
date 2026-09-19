from __future__ import annotations

from masck_one.structural_frame_actuator_reactions import REACTION_IDS
from masck_one.treatment_mounted_four_zone_v10 import (
    GEOMETRY_SOURCE_CELL6_HEAD_SHA,
    SCHEMA_V10,
    SOURCE_CELL6_HEAD_SEMANTICS,
    SOURCE_CELL6_HEAD_SHA,
    build_mounted_four_zone_architecture_v10,
    fusion_handoff_manifest_v10,
    manifest_v10,
)


def test_v10_reuses_selected_geometry_with_precise_cell6_source_semantics():
    architecture, datums = build_mounted_four_zone_architecture_v10()

    assert SOURCE_CELL6_HEAD_SHA == GEOMETRY_SOURCE_CELL6_HEAD_SHA
    assert datums.source_cell6_head_sha == GEOMETRY_SOURCE_CELL6_HEAD_SHA
    assert tuple(station.reaction_id for station in architecture.stations) == REACTION_IDS
    assert tuple(station.reaction_id for station in datums.stations) == REACTION_IDS

    manifest = manifest_v10(architecture, datums)
    assert manifest["schema"] == SCHEMA_V10
    assert manifest["source_cell6_head_sha"] == GEOMETRY_SOURCE_CELL6_HEAD_SHA
    assert manifest["source_cell6_geometry_head_sha"] == GEOMETRY_SOURCE_CELL6_HEAD_SHA
    assert manifest["source_cell6_head_semantics"] == SOURCE_CELL6_HEAD_SEMANTICS
    assert manifest["active_cell6_owner_head_claimed"] is False
    assert manifest["live_cell6_owner_recheck_required_before_promotion"] is True
    assert "REVERIFY_EXACT_CONSUMED_COUNTERFACE_GIT_BLOBS" in manifest["compatibility_rule"]
    assert manifest["supersedes"].endswith("V9")
    assert manifest["physical_architecture_changed_from_v9"] is False
    assert manifest["physical_validation_eligible"] is False


def test_v10_preserves_all_nominal_operational_and_service_clearance_gates():
    architecture, _datums = build_mounted_four_zone_architecture_v10()

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
        assert max(station.truss_screen["v9_material_partition_mm3"].values()) == 0.0


def test_v10_records_tangent_filtered_kernel_and_fusion_handoff_v3():
    architecture, datums = build_mounted_four_zone_architecture_v10()
    manifest = manifest_v10(architecture, datums)

    assert "TANGENT_FACE_FILTER" in manifest["verification_revision"]
    assert "LIVE_OWNER_RECHECK_REQUIRED" in manifest["verification_revision"]
    assert "NO_COLLISION_OR_VALIDITY_THRESHOLD_WEAKENED" in manifest["verification_revision"]
    assert manifest["V9_status"].startswith("SUPERSEDED_AS_PROMOTION_CANDIDATE")

    handoff = fusion_handoff_manifest_v10(architecture, datums)
    assert handoff["schema"] == "MASCK_ONE_TREATMENT_FUSION_HANDOFF_V3"
    assert handoff["source_cell6_head_sha"] == GEOMETRY_SOURCE_CELL6_HEAD_SHA
    assert handoff["source_cell6_geometry_head_sha"] == GEOMETRY_SOURCE_CELL6_HEAD_SHA
    assert handoff["active_cell6_owner_head_claimed"] is False
    assert handoff["live_cell6_owner_recheck_required_before_promotion"] is True
    assert "ANALYTICALLY_ZERO_VOLUME" in handoff["reference_sweep_semantics"]
    assert len(handoff["stations"]) == 4
    for station in handoff["stations"]:
        assert station["carrier_insertion_direction_world_unit"] == [0.0, -1.0, 0.0]
        assert station["carrier_service_withdrawal_direction_world_unit"] == [0.0, 1.0, 0.0]