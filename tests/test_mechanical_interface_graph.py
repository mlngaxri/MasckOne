from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path

import pytest

from masck_one.mechanical_interface_graph import (
    MechanicalInterfaceGraph,
    MechanicalInterfaceGraphError,
    SOURCE_MAIN_SHA,
    WORLD_FRAME_ID,
    assert_local_source_bindings,
    build_mechanical_interface_graph,
    manifest_json,
    source_binding_map,
    unresolved_interface_ids,
)


def graph_with(*, nodes=None, interfaces=None, motions=None, sources=None):
    graph = build_mechanical_interface_graph()
    return MechanicalInterfaceGraph(
        graph.sources if sources is None else tuple(sources),
        graph.nodes if nodes is None else tuple(nodes),
        graph.interfaces if interfaces is None else tuple(interfaces),
        graph.service_motions if motions is None else tuple(motions),
    )


def test_graph_is_deterministic_current_main_bound_and_retention_path_closed():
    first = build_mechanical_interface_graph()
    second = build_mechanical_interface_graph()
    assert first == second
    assert first.graph_sha256 == second.graph_sha256
    manifest = json.loads(manifest_json(first))
    assert manifest["schema"] == "MASCK_ONE_MECHANICAL_INTERFACE_GRAPH_V3"
    assert manifest["source_main_sha"] == SOURCE_MAIN_SHA == "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
    assert manifest["frame_id"] == WORLD_FRAME_ID
    assert manifest["units"] == "mm"
    assert manifest["selected_retention_load_path_closed"] is True
    assert manifest["whole_mechanical_package_closed"] is False


def test_local_cell6_and_released_registry_blobs_fail_closed_if_source_moves():
    repo_root = Path(__file__).resolve().parents[1]
    assert_local_source_bindings(repo_root)
    bindings = source_binding_map()
    assert bindings["FRAME_RETENTION_ROOTS_V1"].blob_sha == "982c9722792a1190075a6a52a9ca756ebd5d502b"
    assert bindings["OCCIPITAL_YOKES_V1"].blob_sha == "6d35c96bc65bb1e0e877deadc65481bf44954b4e"
    assert bindings["OCCIPITAL_YOKES_V1"].head_sha == "25686766238b66ecf900009042d721c08e042592"


def test_selected_retention_chain_has_only_realized_load_transfer_edges():
    graph = build_mechanical_interface_graph()
    required = {
        "FRAME_TO_RETENTION_ROOT_LEFT",
        "FRAME_TO_RETENTION_ROOT_RIGHT",
        "RETENTION_ROOT_TO_YOKE_LEFT",
        "RETENTION_ROOT_TO_YOKE_RIGHT",
        "YOKE_TO_ADJUSTMENT_LEFT",
        "YOKE_TO_ADJUSTMENT_RIGHT",
        "ADJUSTMENT_TO_CARRIER_LEFT",
        "ADJUSTMENT_TO_CARRIER_RIGHT",
        "CARRIER_TO_CROWN_LEFT",
        "CARRIER_TO_CROWN_RIGHT",
    }
    edges = {edge.interface_id: edge for edge in graph.interfaces}
    assert required.issubset(edges)
    for interface_id in required:
        edge = edges[interface_id]
        assert edge.status == "CANDIDATE_REALIZED"
        assert edge.transfers_load_digitally is True
    for interface_id in {
        "RETENTION_ROOT_TO_YOKE_LEFT",
        "RETENTION_ROOT_TO_YOKE_RIGHT",
        "YOKE_TO_ADJUSTMENT_LEFT",
        "YOKE_TO_ADJUSTMENT_RIGHT",
        "ADJUSTMENT_TO_CARRIER_LEFT",
        "ADJUSTMENT_TO_CARRIER_RIGHT",
        "CARRIER_TO_CROWN_LEFT",
        "CARRIER_TO_CROWN_RIGHT",
    }:
        assert edges[interface_id].positive_attachment is True


def test_no_floating_retention_material_and_stale_quick_release_is_reference_only():
    graph = build_mechanical_interface_graph()
    bindings = source_binding_map(graph)
    assert bindings["QUICK_RELEASE_V1"].status == "HISTORICAL_DONOR"
    quick = next(node for node in graph.nodes if node.node_id == "QUICK_RELEASE_RIGHT")
    assert quick.geometry_role == "mechanical_reference"
    guards = [
        node for node in graph.nodes
        if node.node_id in {"QUICK_RELEASE_GUARD_RIGHT", "RETENTION_GUARD_LEFT", "RETENTION_GUARD_RIGHT"}
    ]
    assert all(node.geometry_role == "mechanical_reference" for node in guards)

    with pytest.raises(MechanicalInterfaceGraphError, match="floating material candidate"):
        bad = replace(quick, geometry_role="physical_material_candidate")
        graph_with(nodes=tuple(bad if node.node_id == quick.node_id else node for node in graph.nodes))


def test_open_facial_and_quick_release_edges_cannot_be_promoted_by_overlap():
    graph = build_mechanical_interface_graph()
    open_ids = {
        "FRAME_TO_RETENTION_FACIAL_REACTION_LEFT",
        "FRAME_TO_RETENTION_FACIAL_REACTION_RIGHT",
        "RETENTION_TO_QUICK_RELEASE",
        "QUICK_RELEASE_TO_GUARD",
        "RETENTION_TO_LEFT_GUARD",
        "RETENTION_TO_RIGHT_GUARD",
    }
    assert open_ids.issubset(set(unresolved_interface_ids(graph)))
    edge = next(item for item in graph.interfaces if item.interface_id == "RETENTION_TO_QUICK_RELEASE")
    with pytest.raises(MechanicalInterfaceGraphError, match="open/unresolved interface cannot be positive attachment"):
        replace(
            edge,
            semantics="positive_attachment",
            positive_attachment=True,
            status="CANDIDATE_OPEN",
        )


def test_latest_guard_owner_supersedes_old_colliding_inboard_sweep():
    graph = build_mechanical_interface_graph()
    bindings = source_binding_map(graph)
    assert bindings["RETENTION_GUARDS_V2"].head_sha == "82087afce9db01d041ca745dc3d464912fb12123"
    assert bindings["RETENTION_GUARDS_V2"].blob_sha == "7620ce296d37f7c109aeb7ff26925c75898ce24f"

    for side in ("LEFT", "RIGHT"):
        motion = next(
            item for item in graph.service_motions
            if item.motion_id == f"{side}_RETENTION_GUARD_OUTBOARD_FACTORY_INSTALL"
        )
        assert motion.status == "CANDIDATE_CONTINUOUS"
        assert motion.continuous is True
        assert motion.travel_mm == pytest.approx(22.0)
        assert motion.interference_mm3 == pytest.approx(0.0)
        assert "outboard" in motion.note

    manifest = graph.manifest()
    superseded = json.dumps(manifest["superseded_evidence"])
    assert "39.840676" in superseded
    assert "superseded" in superseded


def test_quick_release_pull_remains_donor_motion_not_whole_head_removal():
    graph = build_mechanical_interface_graph()
    pull = next(m for m in graph.service_motions if m.motion_id == "RIGHT_QUICK_RELEASE_PULL")
    whole = next(m for m in graph.service_motions if m.motion_id == "WHOLE_HEAD_REMOVAL")
    assert (pull.status, pull.continuous, pull.travel_mm, pull.sample_count) == (
        "CANDIDATE_CONTINUOUS",
        True,
        7.3,
        39,
    )
    assert pull.whole_product_motion is False
    assert whole.status == "UNRESOLVED"
    assert whole.continuous is False
    assert whole.whole_product_motion is True
    assert whole.source_id is None
    assert whole.travel_mm is None


def test_missing_positive_counterpart_breaks_selected_retention_chain():
    graph = build_mechanical_interface_graph()
    interfaces = tuple(
        edge for edge in graph.interfaces if edge.interface_id != "RETENTION_ROOT_TO_YOKE_LEFT"
    )
    with pytest.raises(MechanicalInterfaceGraphError, match="lacks positive/integral counterparts"):
        graph_with(interfaces=interfaces)


def test_whole_package_and_whole_head_cannot_be_falsely_closed():
    graph = build_mechanical_interface_graph()
    with pytest.raises(MechanicalInterfaceGraphError, match="must remain open"):
        replace(graph, whole_mechanical_package_closed=True)

    motions = list(graph.service_motions)
    idx = next(i for i, motion in enumerate(motions) if motion.motion_id == "WHOLE_HEAD_REMOVAL")
    motions[idx] = replace(
        motions[idx],
        status="CANDIDATE_CONTINUOUS",
        source_id="QUICK_RELEASE_V1",
        continuous=True,
        travel_mm=7.3,
        sample_count=39,
        blocking_source_ids=(),
    )
    with pytest.raises(MechanicalInterfaceGraphError, match="whole-head removal must remain unresolved"):
        graph_with(motions=motions)


def test_nonfinite_or_fabricated_motion_evidence_fails_closed():
    graph = build_mechanical_interface_graph()
    pull = next(m for m in graph.service_motions if m.motion_id == "RIGHT_QUICK_RELEASE_PULL")
    with pytest.raises(MechanicalInterfaceGraphError, match="finite and positive"):
        replace(pull, travel_mm=math.nan)
    whole = next(m for m in graph.service_motions if m.motion_id == "WHOLE_HEAD_REMOVAL")
    with pytest.raises(MechanicalInterfaceGraphError, match="cannot fabricate"):
        replace(whole, source_id="QUICK_RELEASE_V1", travel_mm=7.3, sample_count=39)


def test_four_actuator_carriers_are_preserved_without_claiming_world_mount():
    graph = build_mechanical_interface_graph()
    carriers = [
        node for node in graph.nodes
        if node.source_native_id == "ACTUATOR-CARRIER-TEMPLATE"
    ]
    assert [node.instance_index for node in carriers] == [0, 1, 2, 3]
    for index in range(4):
        local = next(
            edge for edge in graph.interfaces
            if edge.interface_id == f"CARRIER_LOCAL_CLOSURE_ZONE_{index}"
        )
        frame = next(
            edge for edge in graph.interfaces
            if edge.interface_id == f"FRAME_TO_CARRIER_ZONE_{index}"
        )
        assert local.positive_attachment is True
        assert frame.positive_attachment is False
        assert frame.status == "CANDIDATE_OPEN"
