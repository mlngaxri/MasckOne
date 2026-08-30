"""Provenance binding between waste-route topology and a future physical pump package.

This contract does not select a pump or claim hydraulic performance. It prevents a
validated route topology from later being paired with a different pump package
without changing the deterministic release identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from masck_one.waste_routes import WasteRouteNetwork

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _canonical_id(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} must be canonical lowercase identifier text")
    return value


def _canonical_sha256(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{name} must be canonical lowercase SHA-256")
    return value


@dataclass(frozen=True)
class WastePumpPackageRef:
    """Identity-only reference to a controlled pump packaging definition."""

    component_id: str
    package_revision: str
    package_manifest_sha256: str
    hydraulic_performance_state: str = "VALIDATION_GATED"

    def validate(self) -> None:
        _canonical_id(self.component_id, name="pump component_id")
        _canonical_id(self.package_revision, name="pump package_revision")
        _canonical_sha256(self.package_manifest_sha256, name="pump package manifest")
        if self.hydraulic_performance_state != "VALIDATION_GATED":
            raise ValueError("pump package identity cannot promote hydraulic performance")

    def identity_sha256(self) -> str:
        self.validate()
        payload = {
            "component_id": self.component_id,
            "package_revision": self.package_revision,
            "package_manifest_sha256": self.package_manifest_sha256,
            "hydraulic_performance_state": self.hydraulic_performance_state,
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class WastePumpRouteBinding:
    """Exact binding of one validated route manifest to one pump package identity."""

    route_manifest_sha256: str
    pump: WastePumpPackageRef
    pump_inlet_node_id: str
    pump_outlet_node_id: str

    @classmethod
    def from_network(cls, network: WasteRouteNetwork, pump: WastePumpPackageRef) -> "WastePumpRouteBinding":
        if not isinstance(network, WasteRouteNetwork):
            raise ValueError("network must be a WasteRouteNetwork")
        network.validate()
        pump.validate()
        pump_inlets = [n.node_id for n in network.nodes.values() if n.kind.value == "PUMP_INLET"]
        pump_outlets = [n.node_id for n in network.nodes.values() if n.kind.value == "PUMP_OUTLET"]
        return cls(network.manifest_sha256(), pump, pump_inlets[0], pump_outlets[0])

    def validate(self) -> None:
        _canonical_sha256(self.route_manifest_sha256, name="route manifest")
        if not isinstance(self.pump, WastePumpPackageRef):
            raise ValueError("pump must be a WastePumpPackageRef")
        self.pump.validate()
        _canonical_id(self.pump_inlet_node_id, name="pump inlet node_id")
        _canonical_id(self.pump_outlet_node_id, name="pump outlet node_id")
        if self.pump_inlet_node_id == self.pump_outlet_node_id:
            raise ValueError("pump inlet and outlet identities must be distinct")

    def validate_current(self, *, network: WasteRouteNetwork, pump: WastePumpPackageRef) -> None:
        self.validate()
        if not isinstance(network, WasteRouteNetwork):
            raise ValueError("network must be a WasteRouteNetwork")
        network.validate()
        pump.validate()
        expected = WastePumpRouteBinding.from_network(network, pump)
        if self != expected:
            raise ValueError("waste pump binding is stale for current route topology or pump package")

    def manifest_sha256(self) -> str:
        self.validate()
        payload = {
            "route_manifest_sha256": self.route_manifest_sha256,
            "pump_identity_sha256": self.pump.identity_sha256(),
            "pump_inlet_node_id": self.pump_inlet_node_id,
            "pump_outlet_node_id": self.pump_outlet_node_id,
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
