"""Deterministic mixed-phase waste-route topology.

This module models connectivity, provenance and fail-safe architecture only. It does
not claim pressure-flow, recovery, orientation, leakage or backflow performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Mapping

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class WasteNodeKind(str, Enum):
    REGIONAL_ACQUISITION = "REGIONAL_ACQUISITION"
    TRANSIENT_BUFFER = "TRANSIENT_BUFFER"
    PUMP_INLET = "PUMP_INLET"
    PUMP_OUTLET = "PUMP_OUTLET"
    PASSIVE_BACKFLOW_BARRIER = "PASSIVE_BACKFLOW_BARRIER"
    CARTRIDGE_INLET = "CARTRIDGE_INLET"
    CARTRIDGE_RETENTION = "CARTRIDGE_RETENTION"


@dataclass(frozen=True)
class WasteNode:
    node_id: str
    kind: WasteNodeKind
    protected_region_adjacent: bool = False

    def validate(self) -> None:
        if not isinstance(self.node_id, str) or not self.node_id.strip():
            raise ValueError("waste node_id is required")
        if not isinstance(self.kind, WasteNodeKind):
            raise ValueError("waste node kind must be a WasteNodeKind")
        if not isinstance(self.protected_region_adjacent, bool):
            raise ValueError("protected_region_adjacent must be a literal bool")


@dataclass(frozen=True)
class WasteRouteSegment:
    segment_id: str
    source_node_id: str
    target_node_id: str
    mixed_phase: bool
    physical_performance_state: str = "VALIDATION_GATED"

    def validate(self) -> None:
        identities = (self.segment_id, self.source_node_id, self.target_node_id)
        if any(not isinstance(value, str) or not value.strip() for value in identities):
            raise ValueError("waste route segment identities are required")
        if self.source_node_id == self.target_node_id:
            raise ValueError("waste route segment cannot self-loop")
        if self.mixed_phase is not True:
            raise ValueError("waste route segments must explicitly preserve mixed-phase semantics")
        if self.physical_performance_state != "VALIDATION_GATED":
            raise ValueError("digital waste routes cannot promote physical performance")


@dataclass(frozen=True)
class WasteRouteNetwork:
    source_waste_architecture_sha256: str
    nodes: Mapping[str, WasteNode]
    segments: tuple[WasteRouteSegment, ...]

    def validate(self) -> None:
        if not isinstance(self.source_waste_architecture_sha256, str) or not _SHA256_RE.fullmatch(self.source_waste_architecture_sha256):
            raise ValueError("source waste architecture SHA-256 must be canonical lowercase 64-hex")
        if not isinstance(self.nodes, Mapping) or not self.nodes:
            raise ValueError("waste route network requires nodes")
        if not isinstance(self.segments, tuple):
            raise ValueError("waste route segments must be an immutable tuple")
        for key, node in self.nodes.items():
            if not isinstance(key, str) or not isinstance(node, WasteNode):
                raise ValueError("waste node mapping must contain string IDs and WasteNode values")
            node.validate()
            if key != node.node_id:
                raise ValueError("waste node mapping key must equal node_id")
        segment_ids: set[str] = set()
        directed: dict[str, list[str]] = {node_id: [] for node_id in self.nodes}
        for segment in self.segments:
            if not isinstance(segment, WasteRouteSegment):
                raise ValueError("waste route segments must be WasteRouteSegment values")
            segment.validate()
            if segment.segment_id in segment_ids:
                raise ValueError("duplicate waste route segment_id")
            segment_ids.add(segment.segment_id)
            if segment.source_node_id not in self.nodes or segment.target_node_id not in self.nodes:
                raise ValueError("waste route segment references unknown node")
            directed[segment.source_node_id].append(segment.target_node_id)

        kinds: dict[WasteNodeKind, list[str]] = {kind: [] for kind in WasteNodeKind}
        for node in self.nodes.values():
            kinds[node.kind].append(node.node_id)
        if len(kinds[WasteNodeKind.PUMP_INLET]) != 1 or len(kinds[WasteNodeKind.PUMP_OUTLET]) != 1:
            raise ValueError("waste network requires exactly one pump inlet and one pump outlet")
        if len(kinds[WasteNodeKind.PASSIVE_BACKFLOW_BARRIER]) < 1:
            raise ValueError("pump-off architecture requires a passive backflow barrier")
        if len(kinds[WasteNodeKind.CARTRIDGE_INLET]) != 1 or len(kinds[WasteNodeKind.CARTRIDGE_RETENTION]) != 1:
            raise ValueError("waste network requires exactly one cartridge inlet and retention node")
        acquisitions = kinds[WasteNodeKind.REGIONAL_ACQUISITION]
        if not acquisitions:
            raise ValueError("waste network requires regional acquisition")

        pump_in = kinds[WasteNodeKind.PUMP_INLET][0]
        pump_out = kinds[WasteNodeKind.PUMP_OUTLET][0]
        cartridge_in = kinds[WasteNodeKind.CARTRIDGE_INLET][0]
        retention = kinds[WasteNodeKind.CARTRIDGE_RETENTION][0]
        barriers = set(kinds[WasteNodeKind.PASSIVE_BACKFLOW_BARRIER])

        for acquisition in acquisitions:
            if not self._reachable(acquisition, pump_in, directed):
                raise ValueError(f"regional acquisition {acquisition} has no route to pump inlet")
            # The pump is an explicit stage boundary. A graph edge cannot silently create
            # a passive acquisition-to-discharge or acquisition-to-cartridge bypass around it.
            for forbidden_target in (pump_out, cartridge_in, retention):
                if self._reachable(acquisition, forbidden_target, directed):
                    raise ValueError("regional acquisition has a route that bypasses the pump stage boundary")
        if not self._reachable(pump_out, cartridge_in, directed):
            raise ValueError("pump outlet has no route to cartridge inlet")
        if not self._reachable(cartridge_in, retention, directed):
            raise ValueError("cartridge inlet has no route to retention volume")
        if not any(
            self._reachable(pump_out, barrier, directed) and self._reachable(barrier, cartridge_in, directed)
            for barrier in barriers
        ):
            raise ValueError("cartridge path must place a passive backflow barrier downstream of pump outlet")
        if self._reachable_avoiding(pump_out, cartridge_in, directed, forbidden=barriers):
            raise ValueError("pump outlet has a cartridge path that bypasses all passive backflow barriers")

        # Retention is a terminal topology sink. A return edge can otherwise create a
        # digitally valid cycle that defeats containment semantics without any physical evidence.
        if directed[retention]:
            raise ValueError("cartridge retention must be a terminal waste-route sink")
        if self._reachable(cartridge_in, pump_in, directed) or self._reachable(cartridge_in, pump_out, directed):
            raise ValueError("cartridge path cannot cycle back into the pump stage")

        for node in self.nodes.values():
            if node.protected_region_adjacent and node.kind is WasteNodeKind.REGIONAL_ACQUISITION:
                if not directed[node.node_id]:
                    raise ValueError("protected-region-adjacent acquisition cannot be a dead end")

    @staticmethod
    def _reachable(start: str, target: str, graph: Mapping[str, list[str]]) -> bool:
        pending = [start]
        visited: set[str] = set()
        while pending:
            current = pending.pop()
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)
            pending.extend(graph.get(current, ()))
        return False

    @staticmethod
    def _reachable_avoiding(start: str, target: str, graph: Mapping[str, list[str]], *, forbidden: set[str]) -> bool:
        if start in forbidden or target in forbidden:
            return False
        pending = [start]
        visited: set[str] = set()
        while pending:
            current = pending.pop()
            if current == target:
                return True
            if current in visited or current in forbidden:
                continue
            visited.add(current)
            pending.extend(next_id for next_id in graph.get(current, ()) if next_id not in forbidden)
        return False

    def validate_current_source(self, *, expected_waste_architecture_sha256: str) -> None:
        self.validate()
        if not isinstance(expected_waste_architecture_sha256, str) or not _SHA256_RE.fullmatch(expected_waste_architecture_sha256):
            raise ValueError("expected waste architecture SHA-256 must be canonical lowercase 64-hex")
        if self.source_waste_architecture_sha256 != expected_waste_architecture_sha256:
            raise ValueError("waste route network is stale for the expected waste architecture")

    def manifest_sha256(self) -> str:
        self.validate()
        payload = {
            "source_waste_architecture_sha256": self.source_waste_architecture_sha256,
            "nodes": [
                {"node_id": n.node_id, "kind": n.kind.value, "protected_region_adjacent": n.protected_region_adjacent}
                for n in sorted(self.nodes.values(), key=lambda x: x.node_id)
            ],
            "segments": [
                {"segment_id": s.segment_id, "source": s.source_node_id, "target": s.target_node_id, "mixed_phase": s.mixed_phase, "physical_performance_state": s.physical_performance_state}
                for s in sorted(self.segments, key=lambda x: x.segment_id)
            ],
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
