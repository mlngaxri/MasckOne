from __future__ import annotations

from dataclasses import replace
import json
import math

import pytest

from masck_one.mechanical_interface_graph import (
    AUTHORITY_REVISION,
    MechanicalInterfaceGraph,
    MechanicalInterfaceGraphError,
    SOURCE_MAIN_SHA,
    WORLD_FRAME_ID,
    build_mechanical_interface_graph,
    candidate_source_heads,
    manifest_json,
    source_binding_map,
    unresolved_interface_ids,
)

EXPECTED_CANDIDATE_HEADS = (
    (120, "90d20231710a24bbf02ba0c9ae52ef8b37f0ce73"),
    (117, "34273de3bd86294080e51873c212e988b4a966f4"),
    (118, "37e03df4b6abbd222422c8bfd4e70b03a4e5ae07"),
    (92, "ce1a175a79f87da65d88a40eca146f3dc5419528"),
    (71, "0b5a619c6cea344038b0e8b8cc10a50e3d193390"),
    (109, "fb586cc1ea1cde92526417593f9e5aa990d2ae4f"),
    (114, "630cc19497661ae834032eb8ea06e28dfd6100b7"),
)
EXPECTED_BLOBS = {
    "REGISTRY_V2": "d68a109c93532bfa424a574fdbd899230ae20d0b",
    "FRAME_V1": "0ea2ada736825fe1a0e06491d16690ae98cfccde",
    "CARRIER_V1": "9c613f40ed1b8cb43c3a40bb945d53084a71d121",
    "RETENTION_V2": "9647405b36642105c929a3fdd0617d03bfe68c98",
    "QUICK_RELEASE_V1": "11d90a75eb108c53f5a1621abdace7271bf5cac5",
    "RETENTION_GUARDS_V1": "b497e9154067cef9ee24da4d421ea6c7861c348e",
    "SERVICE_INVENTORY_V1": "e44c8ca12d7b163a5a3fb54fbce7ca2c16d0fc5c",
}


def graph_with(*, nodes=None, interfaces=None, motions=None, sources=None):
    graph = build_mechanical_interface_graph()
    return MechanicalInterfaceGraph(
        graph.sources if sources is None else tuple(sources),
        graph.nodes if nodes is None else tuple(nodes),
        graph.interfaces if interfaces is None else tuple(interfaces),
        graph.service_motions if motions is None else tuple(motions),
    )


def test_graph_is_canonical_deterministic_and_source_bound():
    first = build_mechanical_interface_graph()
    second = build_mechanical_interface_graph()
    assert first == second
    assert first.graph_sha256 == second.graph_sha256
    assert manifest_json(first) == manifest_json(second)
    manifest = json.loads(manifest_json(first))
    assert manifest["source_main_sha"] == SOURCE_MAIN_SHA
    assert manifest["authority_revision"] == AUTHORITY_REVISION
    assert manifest["frame_id"] == WORLD_FRAME_ID
    assert manifest["units"] == "mm"
    assert manifest["canonical_registry_status"] == "CANDIDATE_PR_BINDING_NOT_RELEASE_AUTHORITY"
    assert manifest["whole_mechanical_package_closed"] is False
    assert manifest["graph_sha256"] == first.graph_sha256


def test_exact_candidate_heads_and_blobs_are_pinned_for_review_invalidation():
    graph = build_mechanical_interface_graph()
    assert candidate_source_heads(graph) == EXPECTED_CANDIDATE_HEADS
    bindings = source_binding_map(graph)
    assert {key: value.blob_sha for key, value in bindings.items()} == EXPECTED_BLOBS
    assert all(binding.status == "CANDIDATE_PR" for binding in bindings.values())


def test_four_carriers_keep_local_capture_but_no_world_mount():
    graph = build_mechanical_interface_graph()
    carriers = [node for node in graph.nodes if node.source_native_id == "ACTUATOR-CARRIER-TEMPLATE"]
    assert [node.instance_index for node in carriers] == [0, 1, 2, 3]
    for index in range(4):
        local = next(edge for edge in graph.interfaces if edge.interface_id == f"CARRIER_LOCAL_CLOSURE_ZONE_{index}")
        frame = next(edge for edge in graph.interfaces if edge.interface_id == f"FRAME_TO_CARRIER_ZONE_{index}")
        assert (local.semantics, local.positive_attachment, local.status) == (
            "positive_attachment",
            True,
            "CANDIDATE_REALIZED",
        )
        assert (frame.semantics, frame.positive_attachment, frame.status) == (
            "reference_only",
            False,
            "CANDIDATE_OPEN",
        )
        assert "protected-envelope conflict" in frame.note


def test_retention_frame_release_and_guard_interfaces_remain_open():
    graph = build_mechanical_interface_graph()
    expected_open = {
        "FRAME_TO_RETENTION_CROWN",
        "FRAME_TO_RETENTION_FACIAL_REACTION",
        "RETENTION_TO_QUICK_RELEASE",
        "QUICK_RELEASE_TO_GUARD",
        "RETENTION_TO_LEFT_GUARD",
        "RETENTION_TO_RIGHT_GUARD",
    }
    assert expected_open.issubset(set(unresolved_interface_ids(graph)))
    for edge in graph.interfaces:
        if edge.interface_id in expected_open:
            assert edge.status == "CANDIDATE_OPEN"
            assert edge.positive_attachment is False


def test_service_motion_truth_does_not_promote_latch_pull_to_whole_removal():
    graph = build_mechanical_interface_graph()
    pull = next(m for m in graph.service_motions if m.motion_id == "RIGHT_QUICK_RELEASE_PULL")
    whole = next(m for m in graph.service_motions if m.motion_id == "WHOLE_HEAD_REMOVAL")
    separation = next(m for m in graph.service_motions if m.motion_id == "RETENTION_CARRIER_SEPARATION_REASSEMBLY")
    assert (pull.status, pull.continuous, pull.travel_mm, pull.sample_count) == (
        "CANDIDATE_CONTINUOUS",
        True,
        7.3,
        39,
    )
    assert pull.whole_product_motion is False
    assert whole.status == "UNRESOLVED" and whole.source_id is None
    assert whole.continuous is False and whole.whole_product_motion is True
    assert separation.status == "UNRESOLVED" and separation.continuous is False


def test_guard_factory_sweeps_are_candidate_reference_motion_only():
    graph = build_mechanical_interface_graph()
    expected = {
        "RIGHT_QUICK_RELEASE_GUARD_FACTORY_INSTALL": 35.0,
        "LEFT_RETENTION_GUARD_FACTORY_INSTALL": 22.0,
        "RIGHT_RETENTION_GUARD_FACTORY_INSTALL": 22.0,
    }
    for motion_id, travel in expected.items():
        motion = next(item for item in graph.service_motions if item.motion_id == motion_id)
        assert motion.status == "CANDIDATE_CONTINUOUS"
        assert motion.continuous is True
        assert motion.travel_mm == pytest.approx(travel)
        assert motion.whole_product_motion is False
        assert "reference motion only" in motion.note


def test_frame_unit_identity_and_actuator_index_drift_fail_closed():
    graph = build_mechanical_interface_graph()
    with pytest.raises(MechanicalInterfaceGraphError, match="canonical world-mm"):
        replace(graph.nodes[0], frame_id="WRONG_FRAME")
    with pytest.raises(MechanicalInterfaceGraphError, match="canonical world-mm"):
        replace(graph.nodes[0], units="inch")
    with pytest.raises(MechanicalInterfaceGraphError, match="unknown canonical component id"):
        replace(graph.nodes[0], canonical_component_id="Frame_Structure")
    carrier = next(node for node in graph.nodes if node.node_id == "ACTUATOR_CARRIER_ZONE_0")
    with pytest.raises(MechanicalInterfaceGraphError, match="instance index 0..3"):
        replace(carrier, instance_index=4)


def test_open_cross_boundary_join_cannot_become_positive_attachment():
    graph = build_mechanical_interface_graph()
    edge = next(item for item in graph.interfaces if item.interface_id == "FRAME_TO_RETENTION_CROWN")
    with pytest.raises(MechanicalInterfaceGraphError, match="open/unresolved interface cannot be positive attachment"):
        replace(edge, semantics="positive_attachment", positive_attachment=True)
    with pytest.raises(MechanicalInterfaceGraphError, match="agree exactly"):
        replace(edge, positive_attachment=True)


def test_unknown_sources_endpoints_duplicates_and_nonfinite_motion_fail_closed():
    graph = build_mechanical_interface_graph()
    bad_node = replace(graph.nodes[0], source_id="MISSING_SOURCE")
    with pytest.raises(MechanicalInterfaceGraphError, match="unknown source"):
        graph_with(nodes=(bad_node,) + graph.nodes[1:])
    bad_edge = replace(graph.interfaces[0], to_node="MISSING_NODE")
    with pytest.raises(MechanicalInterfaceGraphError, match="endpoint"):
        graph_with(interfaces=(bad_edge,) + graph.interfaces[1:])
    with pytest.raises(MechanicalInterfaceGraphError, match="duplicate node id"):
        graph_with(nodes=graph.nodes + (graph.nodes[0],))
    pull = next(m for m in graph.service_motions if m.motion_id == "RIGHT_QUICK_RELEASE_PULL")
    with pytest.raises(MechanicalInterfaceGraphError, match="finite and positive"):
        replace(pull, travel_mm=math.nan)


def test_unresolved_motion_cannot_fabricate_source_or_continuity():
    graph = build_mechanical_interface_graph()
    whole = next(m for m in graph.service_motions if m.motion_id == "WHOLE_HEAD_REMOVAL")
    with pytest.raises(MechanicalInterfaceGraphError, match="cannot claim continuity"):
        replace(whole, continuous=True)
    with pytest.raises(MechanicalInterfaceGraphError, match="cannot fabricate"):
        replace(whole, source_id="QUICK_RELEASE_V1", travel_mm=7.3, sample_count=39)


def test_whole_package_and_whole_head_motion_cannot_be_falsely_closed():
    graph = build_mechanical_interface_graph()
    with pytest.raises(MechanicalInterfaceGraphError, match="must remain open"):
        replace(graph, whole_mechanical_package_closed=True)
    motions = list(graph.service_motions)
    index = next(i for i, motion in enumerate(motions) if motion.motion_id == "WHOLE_HEAD_REMOVAL")
    motions[index] = replace(
        motions[index],
        status="CANDIDATE_CONTINUOUS",
        source_id="QUICK_RELEASE_V1",
        continuous=True,
        travel_mm=7.3,
        sample_count=39,
    )
    with pytest.raises(MechanicalInterfaceGraphError, match="whole-head removal must remain unresolved"):
        graph_with(motions=motions)


def test_malformed_source_identity_fails_closed_and_moved_head_invalidates_digest():
    graph = build_mechanical_interface_graph()
    source = graph.sources[0]
    with pytest.raises(MechanicalInterfaceGraphError, match="40-character Git SHA"):
        replace(source, head_sha="ABC")
    with pytest.raises(MechanicalInterfaceGraphError, match="positive PR number"):
        replace(source, pr_number=0)

    sources = list(graph.sources)
    frame_index = next(i for i, item in enumerate(sources) if item.source_id == "FRAME_V1")
    sources[frame_index] = replace(
        sources[frame_index],
        head_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        note="hostile moved-head fixture",
    )
    moved = graph_with(sources=sources)
    assert moved.graph_sha256 != graph.graph_sha256
    assert candidate_source_heads(moved) != EXPECTED_CANDIDATE_HEADS


def test_candidate_geometry_never_becomes_released_material():
    graph = build_mechanical_interface_graph()
    assert all(node.geometry_role != "physical_material" for node in graph.nodes)
    assert all(source.status != "RELEASED_MAIN" for source in graph.sources)
