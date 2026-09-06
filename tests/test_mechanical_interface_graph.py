from __future__ import annotations

from dataclasses import replace
import json
import math

import pytest

from masck_one.mechanical_interface_graph import (
    AUTHORITY_REVISION,
    SOURCE_MAIN_SHA,
    SOURCE_MAIN_TREE_SHA,
    SUPERSEDED_RETENTION_PRS,
    WORLD_FRAME_ID,
    MechanicalInterfaceGraphError,
    build_mechanical_interface_graph,
    candidate_source_heads,
    manifest_json,
    source_binding_map,
    unresolved_interface_ids,
)


def _motions():
    return {item.motion_id: item for item in build_mechanical_interface_graph().service_motions}


def _interfaces():
    return {item.interface_id: item for item in build_mechanical_interface_graph().interfaces}


def test_graph_is_bound_to_post_pr121_current_main_and_canonical_world():
    graph = build_mechanical_interface_graph()
    assert SOURCE_MAIN_SHA == "b3be4c2483f45b2b8dfff6f0c3d9810c2b8511dc"
    assert SOURCE_MAIN_TREE_SHA == "b857c48059a4b29c412969e19ed90721d2758e3d"
    assert AUTHORITY_REVISION == "2026-08-30-R1"
    payload = graph.manifest()
    assert payload["source_main_sha"] == SOURCE_MAIN_SHA
    assert payload["source_main_tree_sha"] == SOURCE_MAIN_TREE_SHA
    assert payload["frame_id"] == WORLD_FRAME_ID
    assert payload["units"] == "mm"


def test_legacy_retention_prs_remain_collapsed():
    graph = build_mechanical_interface_graph()
    assert SUPERSEDED_RETENTION_PRS == (83, 87, 89)
    assert graph.manifest()["superseded_retention_prs"] == [83, 87, 89]
    assert all(item.pr_number not in SUPERSEDED_RETENTION_PRS for item in graph.sources)


def test_exact_candidate_heads_and_blobs_are_pinned():
    graph = build_mechanical_interface_graph()
    assert candidate_source_heads(graph) == (
        (120, "90d20231710a24bbf02ba0c9ae52ef8b37f0ce73"),
        (117, "34273de3bd86294080e51873c212e988b4a966f4"),
        (118, "37e03df4b6abbd222422c8bfd4e70b03a4e5ae07"),
        (127, "dfdd8468731ae7e58e0aa3f7910662fbbef1ba60"),
        (92, "88a88bed01fd3b3acfb38ff5f6f3ae3d5bbf54fe"),
        (123, "25686766238b66ecf900009042d721c08e042592"),
        (71, "0b5a619c6cea344038b0e8b8cc10a50e3d193390"),
        (109, "fb586cc1ea1cde92526417593f9e5aa990d2ae4f"),
        (114, "630cc19497661ae834032eb8ea06e28dfd6100b7"),
    )
    sources = source_binding_map(graph)
    expected_blobs = {
        "REGISTRY_V2": "d68a109c93532bfa424a574fdbd899230ae20d0b",
        "FRAME_V1": "0ea2ada736825fe1a0e06491d16690ae98cfccde",
        "CARRIER_V1": "9c613f40ed1b8cb43c3a40bb945d53084a71d121",
        "ACTUATOR_DONOR_AUDIT_V1": "d23b574ed0048aba76f64e63471a3327fde2fd5b",
        "RETENTION_V2": "9647405b36642105c929a3fdd0617d03bfe68c98",
        "OCCIPITAL_YOKES_V1": "6d35c96bc65bb1e0e877deadc65481bf44954b4e",
        "QUICK_RELEASE_V1": "11d90a75eb108c53f5a1621abdace7271bf5cac5",
        "RETENTION_GUARDS_V1": "b497e9154067cef9ee24da4d421ea6c7861c348e",
        "SERVICE_INVENTORY_V1": "e44c8ca12d7b163a5a3fb54fbce7ca2c16d0fc5c",
    }
    assert {key: sources[key].blob_sha for key in expected_blobs} == expected_blobs


def test_cell7_donor_audit_is_semantic_evidence_not_mount_geometry():
    graph = build_mechanical_interface_graph()
    audit = source_binding_map(graph)["ACTUATOR_DONOR_AUDIT_V1"]
    assert audit.pr_number == 127
    assert "rejects legacy collar/shoe/frame overlap as attachment" in audit.note
    assert "semantics only" in audit.note
    assert all(node.source_id != "ACTUATOR_DONOR_AUDIT_V1" for node in graph.nodes)


def test_four_carrier_zones_keep_local_capture_but_no_frame_join():
    graph = build_mechanical_interface_graph()
    carriers = [node for node in graph.nodes if node.canonical_component_id == "actuator_zone"]
    assert [node.instance_index for node in carriers] == [0, 1, 2, 3]
    edges = _interfaces()
    for index in range(4):
        local = edges[f"CARRIER_LOCAL_CLOSURE_ZONE_{index}"]
        assert local.status == "CANDIDATE_REALIZED"
        assert local.semantics == "positive_attachment"
        assert local.positive_attachment is True
        world = edges[f"FRAME_TO_CARRIER_ZONE_{index}"]
        assert world.status == "CANDIDATE_OPEN"
        assert world.semantics == "reference_only"
        assert world.positive_attachment is False
        assert "protected-envelope conflicted" in world.note
        assert "forbids" in world.note


def test_frame_retention_and_quick_release_cross_boundary_edges_stay_open():
    edges = _interfaces()
    for interface_id in (
        "FRAME_TO_RETENTION_CROWN",
        "FRAME_TO_RETENTION_FACIAL_REACTION",
        "RETENTION_TO_QUICK_RELEASE",
    ):
        edge = edges[interface_id]
        assert edge.status == "CANDIDATE_OPEN"
        assert edge.semantics == "reference_only"
        assert edge.positive_attachment is False
    assert set(unresolved_interface_ids()) >= {
        "FRAME_TO_RETENTION_CROWN",
        "FRAME_TO_RETENTION_FACIAL_REACTION",
        "RETENTION_TO_QUICK_RELEASE",
    }


def test_exact_quick_release_reference_motion_is_not_whole_head_motion():
    motion = _motions()["RIGHT_QUICK_RELEASE_PULL"]
    assert motion.status == "CANDIDATE_CONTINUOUS"
    assert motion.source_id == "QUICK_RELEASE_V1"
    assert motion.travel_mm == pytest.approx(7.3)
    assert motion.sample_count == 39
    assert motion.continuous is True
    assert motion.whole_product_motion is False
    assert motion.blocking_source_ids == ()


def test_quick_release_guard_reference_sweep_remains_clear():
    motion = _motions()["RIGHT_QUICK_RELEASE_GUARD_FACTORY_INSTALL"]
    assert motion.status == "CANDIDATE_CONTINUOUS"
    assert motion.travel_mm == pytest.approx(35.0)
    assert motion.interference_mm3 == pytest.approx(0.0)
    assert motion.blocking_source_ids == ()


def test_bilateral_guard_pure_x_sweeps_are_reference_motion_with_measured_interference():
    motions = _motions()
    for side in ("LEFT", "RIGHT"):
        reference = motions[f"{side}_RETENTION_GUARD_PURE_X_SWEEP_REFERENCE"]
        assert reference.status == "CANDIDATE_CONTINUOUS"
        assert reference.source_id == "RETENTION_GUARDS_V1"
        assert reference.travel_mm == pytest.approx(22.0)
        assert reference.sample_count == 2
        assert reference.interference_mm3 == pytest.approx(39.840676)
        assert "not a collision-free integrated factory path" in reference.note


def test_bilateral_guard_factory_install_paths_fail_closed_on_yoke_collision():
    motions = _motions()
    for side in ("LEFT", "RIGHT"):
        factory = motions[f"{side}_RETENTION_GUARD_FACTORY_INSTALL"]
        assert factory.status == "UNRESOLVED"
        assert factory.source_id is None
        assert factory.continuous is False
        assert factory.travel_mm is None
        assert factory.sample_count is None
        assert set(factory.blocking_source_ids) == {"RETENTION_GUARDS_V1", "OCCIPITAL_YOKES_V1"}
        assert factory.interference_mm3 == pytest.approx(39.840676)


def test_retention_reassembly_and_whole_head_removal_remain_unresolved():
    motions = _motions()
    separation = motions["RETENTION_CARRIER_SEPARATION_REASSEMBLY"]
    whole = motions["WHOLE_HEAD_REMOVAL"]
    assert separation.status == "UNRESOLVED"
    assert set(separation.blocking_source_ids) == {"RETENTION_V2", "SERVICE_INVENTORY_V1"}
    assert whole.status == "UNRESOLVED"
    assert whole.whole_product_motion is True
    assert set(whole.blocking_source_ids) == {"RETENTION_V2", "SERVICE_INVENTORY_V1"}


def test_whole_package_cannot_be_falsely_closed():
    graph = build_mechanical_interface_graph()
    with pytest.raises(MechanicalInterfaceGraphError, match="whole mechanical package must remain open"):
        replace(graph, whole_mechanical_package_closed=True)


def test_whole_head_motion_cannot_be_promoted_from_latch_reference():
    graph = build_mechanical_interface_graph()
    spoofed = []
    for motion in graph.service_motions:
        if motion.motion_id == "WHOLE_HEAD_REMOVAL":
            spoofed.append(
                replace(
                    motion,
                    status="CANDIDATE_CONTINUOUS",
                    source_id="QUICK_RELEASE_V1",
                    continuous=True,
                    travel_mm=7.3,
                    sample_count=39,
                    blocking_source_ids=(),
                    interference_mm3=None,
                )
            )
        else:
            spoofed.append(motion)
    with pytest.raises(MechanicalInterfaceGraphError, match="whole-head removal must remain unresolved"):
        replace(graph, service_motions=tuple(spoofed))


def test_measured_guard_collision_cannot_be_relabelled_as_factory_motion():
    graph = build_mechanical_interface_graph()
    spoofed = []
    for motion in graph.service_motions:
        if motion.motion_id == "LEFT_RETENTION_GUARD_FACTORY_INSTALL":
            spoofed.append(
                replace(
                    motion,
                    status="CANDIDATE_CONTINUOUS",
                    source_id="RETENTION_GUARDS_V1",
                    continuous=True,
                    travel_mm=22.0,
                    sample_count=2,
                    blocking_source_ids=(),
                )
            )
        else:
            spoofed.append(motion)
    with pytest.raises(MechanicalInterfaceGraphError, match="factory install must remain unresolved"):
        replace(graph, service_motions=tuple(spoofed))


def test_cross_boundary_join_cannot_be_relabelled_positive():
    graph = build_mechanical_interface_graph()
    spoofed = []
    for edge in graph.interfaces:
        if edge.interface_id == "FRAME_TO_RETENTION_CROWN":
            spoofed.append(replace(edge, semantics="positive_attachment", status="CANDIDATE_REALIZED", positive_attachment=True))
        else:
            spoofed.append(edge)
    with pytest.raises(MechanicalInterfaceGraphError, match="cross-boundary joins"):
        replace(graph, interfaces=tuple(spoofed))


def test_unresolved_motion_cannot_fabricate_numeric_evidence():
    motion = _motions()["WHOLE_HEAD_REMOVAL"]
    with pytest.raises(MechanicalInterfaceGraphError, match="unresolved motion cannot fabricate"):
        replace(motion, travel_mm=7.3)
    with pytest.raises(MechanicalInterfaceGraphError, match="unresolved motion cannot claim continuity"):
        replace(motion, continuous=True)


def test_candidate_motion_cannot_keep_unresolved_blockers():
    motion = _motions()["LEFT_RETENTION_GUARD_FACTORY_INSTALL"]
    with pytest.raises(MechanicalInterfaceGraphError, match="cannot claim unresolved blockers"):
        replace(motion, status="CANDIDATE_CONTINUOUS", source_id="RETENTION_GUARDS_V1", continuous=True, travel_mm=22.0, sample_count=2)


def test_source_sha_and_motion_numerics_fail_closed():
    graph = build_mechanical_interface_graph()
    source = graph.sources[0]
    with pytest.raises(MechanicalInterfaceGraphError, match="40-character Git SHA"):
        replace(source, head_sha="not-a-sha")
    motion = _motions()["RIGHT_QUICK_RELEASE_PULL"]
    with pytest.raises(MechanicalInterfaceGraphError, match="finite and positive"):
        replace(motion, travel_mm=math.nan)


def test_manifest_is_deterministic_and_digest_covers_current_truth():
    first = build_mechanical_interface_graph()
    second = build_mechanical_interface_graph()
    assert first.graph_sha256 == second.graph_sha256
    assert manifest_json(first) == manifest_json(second)
    payload = json.loads(manifest_json(first))
    assert payload["graph_sha256"] == first.graph_sha256
    assert payload["whole_mechanical_package_closed"] is False
    assert "DIGITAL_SOURCE_BOUND_INTERFACE_KINEMATIC_AND_SWEPT_VOLUME_CLASSIFICATION_ONLY" in payload["evidence_status"]
