from dataclasses import replace
import math

import pytest

from masck_one.waste_route_accounting import WasteRouteVolumeAccounting, WasteRouteVolumeStage
from masck_one.waste_route_geometry import WasteRouteGeometryLedger, WasteRouteGeometrySegment
from masck_one.waste_routes import WasteNode, WasteNodeKind, WasteRouteNetwork, WasteRouteSegment

SOURCE = "a" * 64


class LyingStr(str):
    def __eq__(self, other):
        return True

    def __hash__(self):
        return str.__hash__(self)


def network():
    nodes = {
        "acq": WasteNode("acq", WasteNodeKind.REGIONAL_ACQUISITION, True),
        "buffer": WasteNode("buffer", WasteNodeKind.TRANSIENT_BUFFER),
        "pump_in": WasteNode("pump_in", WasteNodeKind.PUMP_INLET),
        "pump_out": WasteNode("pump_out", WasteNodeKind.PUMP_OUTLET),
        "barrier": WasteNode("barrier", WasteNodeKind.PASSIVE_BACKFLOW_BARRIER),
        "cart_in": WasteNode("cart_in", WasteNodeKind.CARTRIDGE_INLET),
        "retention": WasteNode("retention", WasteNodeKind.CARTRIDGE_RETENTION),
    }
    segments = (
        WasteRouteSegment("s1", "acq", "buffer", True),
        WasteRouteSegment("s2", "buffer", "pump_in", True),
        WasteRouteSegment("s3", "pump_out", "barrier", True),
        WasteRouteSegment("s4", "barrier", "cart_in", True),
        WasteRouteSegment("s5", "cart_in", "retention", True),
    )
    return WasteRouteNetwork(SOURCE, nodes, segments)


def geometry(n):
    records = {
        segment.segment_id: WasteRouteGeometrySegment(
            segment.segment_id,
            centerline_length_mm=20.0 + index,
            inner_diameter_mm=1.0,
            required_min_bend_radius_mm=4.0,
            realized_min_bend_radius_mm=5.0,
        )
        for index, segment in enumerate(n.segments)
    }
    return WasteRouteGeometryLedger(n.manifest_sha256(), records)


def accounting(n, g):
    return WasteRouteVolumeAccounting(
        n.manifest_sha256(),
        g.manifest_sha256(network=n),
    )


def test_stage_accounting_is_deterministic_and_conserves_geometric_volume():
    n = network(); g = geometry(n); a = accounting(n, g)
    a.validate(network=n, geometry=g)
    stages = a.segment_ids_by_stage(network=n, geometry=g)
    assert stages[WasteRouteVolumeStage.PRE_PUMP] == ("s1", "s2")
    assert stages[WasteRouteVolumeStage.POST_PUMP_TO_CARTRIDGE] == ("s3", "s4")
    assert stages[WasteRouteVolumeStage.CARTRIDGE_INTERNAL] == ("s5",)
    stage_total = math.fsum(
        a.geometric_volume_ml(stage, network=n, geometry=g)
        for stage in WasteRouteVolumeStage
    )
    assert stage_total == pytest.approx(g.total_geometric_internal_volume_ml(network=n))
    assert a.manifest_sha256(network=n, geometry=g) == a.manifest_sha256(network=n, geometry=g)


def test_geometry_change_invalidates_accounting_before_public_volume_use():
    n = network(); g = geometry(n); a = accounting(n, g)
    changed = dict(g.segments)
    changed["s1"] = replace(changed["s1"], centerline_length_mm=25.0)
    stale_geometry = replace(g, segments=changed)
    with pytest.raises(ValueError, match="stale for the supplied geometry"):
        a.geometric_volume_ml(WasteRouteVolumeStage.PRE_PUMP, network=n, geometry=stale_geometry)


def test_topology_change_invalidates_accounting_before_stage_use():
    n = network(); g = geometry(n); a = accounting(n, g)
    altered_nodes = dict(n.nodes)
    altered_nodes["buffer2"] = WasteNode("buffer2", WasteNodeKind.TRANSIENT_BUFFER)
    altered_segments = (
        WasteRouteSegment("s1", "acq", "buffer2", True),
        WasteRouteSegment("s2", "buffer2", "pump_in", True),
        *n.segments[2:],
    )
    altered = WasteRouteNetwork(SOURCE, altered_nodes, altered_segments)
    altered_g = geometry(altered)
    with pytest.raises(ValueError, match="stale for the supplied topology"):
        a.segment_ids_by_stage(network=altered, geometry=altered_g)


def test_hostile_sha_subclasses_fail_closed():
    n = network(); g = geometry(n); a = accounting(n, g)
    with pytest.raises(ValueError, match="exact built-in"):
        replace(a, source_route_manifest_sha256=LyingStr(n.manifest_sha256())).validate(network=n, geometry=g)
    with pytest.raises(ValueError, match="exact built-in"):
        replace(a, source_geometry_manifest_sha256=LyingStr(g.manifest_sha256(network=n))).validate(network=n, geometry=g)


def test_contract_cannot_promote_digital_volume_to_physical_performance():
    n = network(); g = geometry(n); a = accounting(n, g)
    with pytest.raises(ValueError, match="cannot promote physical performance"):
        replace(a, physical_performance_state="VERIFIED").validate(network=n, geometry=g)
    with pytest.raises(ValueError, match="controlled digital accounting only"):
        replace(a, accounting_state="MEASURED_DEAD_VOLUME").validate(network=n, geometry=g)


def test_stage_requires_exact_enum_contract():
    n = network(); g = geometry(n); a = accounting(n, g)
    with pytest.raises(ValueError, match="exact WasteRouteVolumeStage"):
        a.geometric_volume_ml("PRE_PUMP", network=n, geometry=g)


def test_network_and_geometry_contract_subclasses_are_rejected():
    class EvilNetwork(WasteRouteNetwork):
        pass

    class EvilGeometry(WasteRouteGeometryLedger):
        pass

    n = network(); g = geometry(n); a = accounting(n, g)
    evil_n = EvilNetwork(n.source_waste_architecture_sha256, n.nodes, n.segments)
    evil_g = EvilGeometry(g.source_route_manifest_sha256, g.segments)
    with pytest.raises(ValueError, match="exact WasteRouteNetwork"):
        a.validate(network=evil_n, geometry=g)
    with pytest.raises(ValueError, match="exact WasteRouteGeometryLedger"):
        a.validate(network=n, geometry=evil_g)
