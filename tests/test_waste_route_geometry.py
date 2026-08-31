from dataclasses import replace
import math

import pytest

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
        "acq_eye_safe": WasteNode("acq_eye_safe", WasteNodeKind.REGIONAL_ACQUISITION, True),
        "buffer": WasteNode("buffer", WasteNodeKind.TRANSIENT_BUFFER),
        "pump_in": WasteNode("pump_in", WasteNodeKind.PUMP_INLET),
        "pump_out": WasteNode("pump_out", WasteNodeKind.PUMP_OUTLET),
        "barrier": WasteNode("barrier", WasteNodeKind.PASSIVE_BACKFLOW_BARRIER),
        "cart_in": WasteNode("cart_in", WasteNodeKind.CARTRIDGE_INLET),
        "retention": WasteNode("retention", WasteNodeKind.CARTRIDGE_RETENTION),
    }
    segments = (
        WasteRouteSegment("s1", "acq_eye_safe", "buffer", True),
        WasteRouteSegment("s2", "buffer", "pump_in", True),
        WasteRouteSegment("s3", "pump_out", "barrier", True),
        WasteRouteSegment("s4", "barrier", "cart_in", True),
        WasteRouteSegment("s5", "cart_in", "retention", True),
    )
    return WasteRouteNetwork(SOURCE, nodes, segments)


def ledger(n=None):
    n = n or network()
    geometry = {
        segment.segment_id: WasteRouteGeometrySegment(
            segment.segment_id,
            centerline_length_mm=20.0 + index,
            inner_diameter_mm=1.2,
            required_min_bend_radius_mm=4.0,
            realized_min_bend_radius_mm=5.0,
        )
        for index, segment in enumerate(n.segments)
    }
    return WasteRouteGeometryLedger(n.manifest_sha256(), geometry)


def test_geometry_ledger_binds_exactly_to_topology_and_is_deterministic():
    n = network()
    g = ledger(n)
    g.validate(network=n)
    assert g.manifest_sha256(network=n) == g.manifest_sha256(network=n)
    assert g.total_geometric_internal_volume_ml(network=n) > 0.0


def test_geometric_volume_uses_centerline_length_and_inner_diameter():
    segment = WasteRouteGeometrySegment("s1", 100.0, 2.0, 4.0, 4.0)
    assert segment.geometric_internal_volume_ml() == pytest.approx(math.pi * 100.0 / 1000.0)


def test_stale_topology_manifest_is_rejected():
    n = network()
    with pytest.raises(ValueError, match="stale"):
        replace(ledger(n), source_route_manifest_sha256="b" * 64).validate(network=n)


def test_geometry_cannot_omit_topology_segment():
    n = network(); g = ledger(n); segments = dict(g.segments); segments.pop("s5")
    with pytest.raises(ValueError, match="exactly one record"):
        replace(g, segments=segments).validate(network=n)


def test_geometry_cannot_add_uncontrolled_segment():
    n = network(); g = ledger(n); segments = dict(g.segments)
    segments["extra"] = WasteRouteGeometrySegment("extra", 20.0, 1.0, 4.0, 4.0)
    with pytest.raises(ValueError, match="exactly one record"):
        replace(g, segments=segments).validate(network=n)


def test_mapping_key_must_match_segment_identity():
    n = network(); g = ledger(n); segments = dict(g.segments); item = segments.pop("s1"); segments["alias"] = item
    with pytest.raises(ValueError, match="mapping key must equal"):
        replace(g, segments=segments).validate(network=n)


def test_realized_bend_radius_must_meet_required_minimum():
    with pytest.raises(ValueError, match="bend radius"):
        WasteRouteGeometrySegment("s1", 20.0, 1.0, 5.0, 4.999).validate()


@pytest.mark.parametrize(
    "field,bad",
    [
        ("centerline_length_mm", 0.0),
        ("centerline_length_mm", -1.0),
        ("centerline_length_mm", float("nan")),
        ("centerline_length_mm", float("inf")),
        ("inner_diameter_mm", 0.0),
        ("inner_diameter_mm", float("nan")),
        ("required_min_bend_radius_mm", float("inf")),
        ("realized_min_bend_radius_mm", -1.0),
    ],
)
def test_nonpositive_or_nonfinite_geometry_fails_closed(field, bad):
    segment = WasteRouteGeometrySegment("s1", 20.0, 1.0, 4.0, 5.0)
    with pytest.raises(ValueError, match="finite and > 0"):
        replace(segment, **{field: bad}).validate()


@pytest.mark.parametrize(
    "field,bad",
    [
        ("centerline_length_mm", True),
        ("inner_diameter_mm", False),
        ("required_min_bend_radius_mm", True),
        ("realized_min_bend_radius_mm", False),
        ("centerline_length_mm", "20.0"),
    ],
)
def test_bool_and_text_numeric_aliases_fail_closed(field, bad):
    segment = WasteRouteGeometrySegment("s1", 20.0, 1.0, 4.0, 5.0)
    with pytest.raises(ValueError, match="exact built-in int or float"):
        replace(segment, **{field: bad}).validate()


def test_centerline_length_shorter_than_inner_diameter_is_rejected():
    with pytest.raises(ValueError, match="shorter than"):
        WasteRouteGeometrySegment("s1", 0.5, 1.0, 4.0, 5.0).validate()


def test_geometry_state_cannot_claim_measured_or_verified_geometry():
    with pytest.raises(ValueError, match="digital geometry only"):
        WasteRouteGeometrySegment("s1", 20.0, 1.0, 4.0, 5.0, geometry_state="MEASURED").validate()


def test_physical_performance_cannot_be_promoted_from_geometry():
    with pytest.raises(ValueError, match="cannot promote physical performance"):
        WasteRouteGeometrySegment(
            "s1", 20.0, 1.0, 4.0, 5.0, physical_performance_state="VERIFIED"
        ).validate()


def test_hostile_string_subclass_cannot_alias_segment_identity():
    with pytest.raises(ValueError, match="exact built-in"):
        WasteRouteGeometrySegment(LyingStr("s1"), 20.0, 1.0, 4.0, 5.0).validate()


def test_hostile_string_subclass_cannot_alias_route_manifest_sha():
    n = network(); g = ledger(n)
    with pytest.raises(ValueError, match="exact built-in"):
        replace(g, source_route_manifest_sha256=LyingStr(n.manifest_sha256())).validate(network=n)


def test_hostile_string_subclass_cannot_enter_geometry_mapping_namespace():
    n = network(); g = ledger(n); segments = dict(g.segments); item = segments.pop("s1"); segments[LyingStr("s1")] = item
    with pytest.raises(ValueError, match="exact built-in"):
        replace(g, segments=segments).validate(network=n)


def test_geometry_mapping_is_snapshotted_against_post_construction_mutation():
    n = network(); original = ledger(n); raw = dict(original.segments)
    g = WasteRouteGeometryLedger(original.source_route_manifest_sha256, raw)
    before = g.manifest_sha256(network=n)
    raw.pop("s1")
    raw["evil"] = WasteRouteGeometrySegment("evil", 20.0, 1.0, 4.0, 5.0)
    assert "s1" in g.segments
    assert "evil" not in g.segments
    assert g.manifest_sha256(network=n) == before


def test_network_contract_subclass_is_rejected_at_binding_boundary():
    class EvilNetwork(WasteRouteNetwork):
        pass

    n = network(); evil = EvilNetwork(n.source_waste_architecture_sha256, n.nodes, n.segments)
    with pytest.raises(ValueError, match="exact WasteRouteNetwork"):
        ledger(n).validate(network=evil)


def test_manifest_changes_when_controlled_route_geometry_changes():
    n = network(); g = ledger(n); before = g.manifest_sha256(network=n)
    segments = dict(g.segments); segments["s1"] = replace(segments["s1"], centerline_length_mm=25.0)
    after = replace(g, segments=segments).manifest_sha256(network=n)
    assert after != before
