from dataclasses import replace

import pytest

from masck_one.waste_pump_binding import WastePumpPackageRef, WastePumpRouteBinding
from masck_one.waste_routes import WasteNode, WasteNodeKind, WasteRouteNetwork, WasteRouteSegment

SOURCE = "a" * 64
PACKAGE = "b" * 64


def network():
    nodes = {
        "acq": WasteNode("acq", WasteNodeKind.REGIONAL_ACQUISITION, True),
        "pump_in": WasteNode("pump_in", WasteNodeKind.PUMP_INLET),
        "pump_out": WasteNode("pump_out", WasteNodeKind.PUMP_OUTLET),
        "barrier": WasteNode("barrier", WasteNodeKind.PASSIVE_BACKFLOW_BARRIER),
        "cart_in": WasteNode("cart_in", WasteNodeKind.CARTRIDGE_INLET),
        "retention": WasteNode("retention", WasteNodeKind.CARTRIDGE_RETENTION),
    }
    segments = (
        WasteRouteSegment("s1", "acq", "pump_in", True),
        WasteRouteSegment("s2", "pump_out", "barrier", True),
        WasteRouteSegment("s3", "barrier", "cart_in", True),
        WasteRouteSegment("s4", "cart_in", "retention", True),
    )
    return WasteRouteNetwork(SOURCE, nodes, segments)


def pump():
    return WastePumpPackageRef("waste-pump-a", "r1", PACKAGE)


def test_binding_is_deterministic_and_current():
    n = network(); p = pump()
    binding = WastePumpRouteBinding.from_network(n, p)
    binding.validate_current(network=n, pump=p)
    assert binding.manifest_sha256() == binding.manifest_sha256()


def test_substituted_pump_component_is_rejected_as_stale():
    n = network(); p = pump(); binding = WastePumpRouteBinding.from_network(n, p)
    substituted = replace(p, component_id="waste-pump-b")
    with pytest.raises(ValueError, match="stale"):
        binding.validate_current(network=n, pump=substituted)


def test_substituted_pump_package_manifest_is_rejected_as_stale():
    n = network(); p = pump(); binding = WastePumpRouteBinding.from_network(n, p)
    with pytest.raises(ValueError, match="stale"):
        binding.validate_current(network=n, pump=replace(p, package_manifest_sha256="c" * 64))


def test_route_topology_change_invalidates_binding():
    n = network(); p = pump(); binding = WastePumpRouteBinding.from_network(n, p)
    nodes = dict(n.nodes); nodes["buffer"] = WasteNode("buffer", WasteNodeKind.TRANSIENT_BUFFER)
    segments = tuple(s for s in n.segments if s.segment_id != "s1") + (
        WasteRouteSegment("s1a", "acq", "buffer", True),
        WasteRouteSegment("s1b", "buffer", "pump_in", True),
    )
    changed = replace(n, nodes=nodes, segments=segments)
    with pytest.raises(ValueError, match="stale"):
        binding.validate_current(network=changed, pump=p)


def test_pump_identity_cannot_claim_measured_hydraulic_performance():
    with pytest.raises(ValueError, match="cannot promote"):
        replace(pump(), hydraulic_performance_state="VERIFIED").validate()


@pytest.mark.parametrize("field,value", [
    ("component_id", " Waste-Pump-A "),
    ("package_revision", "R1"),
    ("package_manifest_sha256", "B" * 64),
    ("package_manifest_sha256", True),
])
def test_noncanonical_pump_provenance_fails_closed(field, value):
    with pytest.raises(ValueError, match="canonical"):
        replace(pump(), **{field: value}).validate()


def test_wrong_object_types_fail_closed():
    with pytest.raises(ValueError, match="WasteRouteNetwork"):
        WastePumpRouteBinding.from_network(object(), pump())
    binding = WastePumpRouteBinding.from_network(network(), pump())
    with pytest.raises(ValueError, match="WastePumpPackageRef"):
        replace(binding, pump=object()).validate()
