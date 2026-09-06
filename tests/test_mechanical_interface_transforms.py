from __future__ import annotations

from dataclasses import replace
import math

import pytest

from masck_one.mechanical_interface_graph import WORLD_FRAME_ID, build_mechanical_interface_graph
from masck_one.mechanical_interface_transforms import (
    IDENTITY_TRANSFORM,
    LOCAL_ACTUATOR_FRAME_ID,
    RESOLVED,
    UNRESOLVED,
    MechanicalTransformError,
    build_mechanical_transform_bindings,
    transform_manifest,
)


def test_transform_ledger_covers_every_graph_node_exactly_once():
    graph = build_mechanical_interface_graph()
    bindings = build_mechanical_transform_bindings()
    assert [item.node_id for item in bindings] == [item.node_id for item in graph.nodes]
    assert len({item.node_id for item in bindings}) == len(bindings)
    assert transform_manifest()["target_frame_id"] == WORLD_FRAME_ID


def test_only_actuator_carrier_world_mounts_remain_unresolved():
    bindings = build_mechanical_transform_bindings()
    unresolved = [item for item in bindings if item.status == UNRESOLVED]
    assert [item.node_id for item in unresolved] == [
        "ACTUATOR_CARRIER_ZONE_0",
        "ACTUATOR_CARRIER_ZONE_1",
        "ACTUATOR_CARRIER_ZONE_2",
        "ACTUATOR_CARRIER_ZONE_3",
    ]
    for item in unresolved:
        assert item.source_frame_id == LOCAL_ACTUATOR_FRAME_ID
        assert item.target_frame_id == WORLD_FRAME_ID
        assert item.transform_row_major is None
        assert item.source_schema_or_component_id == "MASCK_ONE_CELL7_ACTUATOR_CARRIER_TEMPLATE_V1"
        assert "no protected-clear accepted world mount" in item.note


def test_world_authored_nodes_use_exact_identity_transform():
    bindings = build_mechanical_transform_bindings()
    for item in bindings:
        if item.status == RESOLVED:
            assert item.source_frame_id == WORLD_FRAME_ID
            assert item.target_frame_id == WORLD_FRAME_ID
            assert item.transform_row_major == IDENTITY_TRANSFORM


def test_source_native_schema_and_component_id_bindings_are_exact():
    bindings = {item.node_id: item.source_schema_or_component_id for item in build_mechanical_transform_bindings()}
    assert bindings["FRAME_REACTION_LOOP"] == "MASCK_ONE-FRAME-MEMBER-PERIMETER-REACTION-LOOP-V1"
    assert bindings["RETENTION_LOAD_PATH"] == "MASCK_ONE_CELL3_RETENTION_LOAD_PATH_V1"
    assert bindings["QUICK_RELEASE_RIGHT"] == "MASCK_ONE_CELL3_RIGHT_QUICK_RELEASE_LATCH_V3"
    assert bindings["QUICK_RELEASE_GUARD_RIGHT"] == "RETENTION_QUICK_RELEASE_GUARD_RIGHT"
    assert bindings["RETENTION_GUARD_LEFT"] == "RETENTION_OCCIPITAL_GUARD_LEFT"
    assert bindings["RETENTION_GUARD_RIGHT"] == "RETENTION_OCCIPITAL_GUARD_RIGHT"


def test_unresolved_world_mount_cannot_fabricate_matrix():
    binding = next(
        item
        for item in build_mechanical_transform_bindings()
        if item.node_id == "ACTUATOR_CARRIER_ZONE_0"
    )
    with pytest.raises(MechanicalTransformError, match="cannot carry a fabricated transform"):
        replace(binding, transform_row_major=IDENTITY_TRANSFORM)


def test_world_authored_resolved_node_cannot_change_frame_or_matrix():
    binding = next(
        item for item in build_mechanical_transform_bindings() if item.node_id == "FRAME_REACTION_LOOP"
    )
    with pytest.raises(MechanicalTransformError, match="exact identity transform"):
        replace(binding, source_frame_id="WRONG_FRAME")
    bad = list(IDENTITY_TRANSFORM)
    bad[3] = 1.0
    with pytest.raises(MechanicalTransformError, match="exact identity transform"):
        replace(binding, transform_row_major=tuple(bad))


def test_nonfinite_or_malformed_transform_fails_closed():
    binding = next(
        item for item in build_mechanical_transform_bindings() if item.node_id == "FRAME_REACTION_LOOP"
    )
    bad = list(IDENTITY_TRANSFORM)
    bad[0] = math.nan
    with pytest.raises(MechanicalTransformError, match="finite"):
        replace(binding, transform_row_major=tuple(bad))
    with pytest.raises(MechanicalTransformError, match="4x4"):
        replace(binding, transform_row_major=(1.0, 0.0))


def test_unresolved_status_is_illegal_for_world_authored_node():
    binding = next(
        item for item in build_mechanical_transform_bindings() if item.node_id == "FRAME_REACTION_LOOP"
    )
    with pytest.raises(MechanicalTransformError, match="world-authored node"):
        replace(binding, status=UNRESOLVED, transform_row_major=None)
