from dataclasses import replace

import pytest

from masck_one.waste_routes import WasteNode, WasteNodeKind, WasteRouteNetwork, WasteRouteSegment

SOURCE = "a" * 64


def network():
    nodes = {
        "acq_eye_safe": WasteNode("acq_eye_safe", WasteNodeKind.REGIONAL_ACQUISITION, True),
        "acq_cheek": WasteNode("acq_cheek", WasteNodeKind.REGIONAL_ACQUISITION),
        "buffer": WasteNode("buffer", WasteNodeKind.TRANSIENT_BUFFER),
        "pump_in": WasteNode("pump_in", WasteNodeKind.PUMP_INLET),
        "pump_out": WasteNode("pump_out", WasteNodeKind.PUMP_OUTLET),
        "barrier": WasteNode("barrier", WasteNodeKind.PASSIVE_BACKFLOW_BARRIER),
        "cart_in": WasteNode("cart_in", WasteNodeKind.CARTRIDGE_INLET),
        "retention": WasteNode("retention", WasteNodeKind.CARTRIDGE_RETENTION),
    }
    segments = (
        WasteRouteSegment("s1", "acq_eye_safe", "buffer", True),
        WasteRouteSegment("s2", "acq_cheek", "buffer", True),
        WasteRouteSegment("s3", "buffer", "pump_in", True),
        WasteRouteSegment("s4", "pump_out", "barrier", True),
        WasteRouteSegment("s5", "barrier", "cart_in", True),
        WasteRouteSegment("s6", "cart_in", "retention", True),
    )
    return WasteRouteNetwork(SOURCE, nodes, segments)


def test_complete_mixed_phase_route_is_deterministic():
    n = network(); n.validate()
    assert n.manifest_sha256() == n.manifest_sha256()


def test_route_source_must_match_current_waste_architecture():
    n = network()
    n.validate_current_source(expected_waste_architecture_sha256=SOURCE)
    with pytest.raises(ValueError, match="stale"):
        n.validate_current_source(expected_waste_architecture_sha256="b" * 64)


def test_missing_passive_backflow_barrier_fails_pump_off_architecture():
    n = network()
    nodes = dict(n.nodes); del nodes["barrier"]
    segments = tuple(s for s in n.segments if "barrier" not in (s.source_node_id, s.target_node_id))
    with pytest.raises(ValueError, match="passive backflow barrier"):
        replace(n, nodes=nodes, segments=segments).validate()


def test_barrier_not_on_pump_to_cartridge_path_is_rejected():
    n = network()
    segments = tuple(s for s in n.segments if s.segment_id not in {"s4", "s5"}) + (
        WasteRouteSegment("direct", "pump_out", "cart_in", True),
    )
    with pytest.raises(ValueError, match="downstream of pump outlet"):
        replace(n, segments=segments).validate()


def test_parallel_pump_to_cartridge_path_cannot_bypass_backflow_barrier():
    n = network()
    # Keep the valid barrier-containing path intact, then add a parallel direct bypass.
    # The former implementation accepted this because it only proved that *some* path
    # traversed a barrier. Pump-off protection requires every route to cartridge inlet
    # to cross at least one passive barrier.
    bypassed = replace(
        n,
        segments=n.segments + (WasteRouteSegment("s_bypass", "pump_out", "cart_in", True),),
    )
    with pytest.raises(ValueError, match="bypasses all passive backflow barriers"):
        bypassed.validate()


def test_disconnected_regional_acquisition_is_rejected():
    n = network()
    segments = tuple(s for s in n.segments if s.segment_id != "s2")
    with pytest.raises(ValueError, match="no route to pump inlet"):
        replace(n, segments=segments).validate()


def test_mixed_phase_semantics_cannot_be_silently_downgraded():
    n = network(); segments = list(n.segments)
    segments[0] = replace(segments[0], mixed_phase=False)
    with pytest.raises(ValueError, match="mixed-phase"):
        replace(n, segments=tuple(segments)).validate()


def test_digital_route_cannot_claim_physical_performance():
    n = network(); segments = list(n.segments)
    segments[0] = replace(segments[0], physical_performance_state="VERIFIED")
    with pytest.raises(ValueError, match="cannot promote physical performance"):
        replace(n, segments=tuple(segments)).validate()


def test_duplicate_segment_identity_is_rejected():
    n = network()
    with pytest.raises(ValueError, match="duplicate"):
        replace(n, segments=n.segments + (replace(n.segments[0]),)).validate()


def test_unknown_node_reference_is_rejected():
    n = network(); segments = list(n.segments)
    segments[0] = replace(segments[0], target_node_id="missing")
    with pytest.raises(ValueError, match="unknown node"):
        replace(n, segments=tuple(segments)).validate()


def test_manifest_changes_when_route_topology_changes():
    n = network(); original = n.manifest_sha256()
    nodes = dict(n.nodes); nodes["buffer2"] = WasteNode("buffer2", WasteNodeKind.TRANSIENT_BUFFER)
    segments = tuple(replace(s, target_node_id="buffer2") if s.segment_id in {"s1", "s2"} else s for s in n.segments)
    segments += (WasteRouteSegment("buffer-link", "buffer2", "buffer", True),)
    changed = replace(n, nodes=nodes, segments=segments)
    assert changed.manifest_sha256() != original


def test_boolean_protected_region_alias_is_rejected():
    n = network(); nodes = dict(n.nodes)
    nodes["acq_cheek"] = replace(nodes["acq_cheek"], protected_region_adjacent=1)
    with pytest.raises(ValueError, match="literal bool"):
        replace(n, nodes=nodes).validate()
