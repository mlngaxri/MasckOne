"""Topology and geometry bound waste-route volume accounting.

This module classifies controlled digital waste-route geometry into deterministic
pre-pump, post-pump, and cartridge-internal stages. The resulting volumes are
geometric accounting quantities only. They are not measured hydraulic dead volume,
prime volume, purge volume, mixed-phase recovery, backflow, leakage, or orientation
evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import math
import re

from .waste_route_geometry import WasteRouteGeometryLedger
from .waste_routes import WasteNodeKind, WasteRouteNetwork

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ACCOUNTING_STATE = "CONTROLLED_DIGITAL_ACCOUNTING_ONLY"
_PHYSICAL_STATE = "VALIDATION_GATED"


def _canonical_sha256(value: object, *, name: str) -> str:
    if type(value) is not str or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{name} must be exact built-in canonical lowercase SHA-256")
    return value


class WasteRouteVolumeStage(str, Enum):
    PRE_PUMP = "PRE_PUMP"
    POST_PUMP_TO_CARTRIDGE = "POST_PUMP_TO_CARTRIDGE"
    CARTRIDGE_INTERNAL = "CARTRIDGE_INTERNAL"


@dataclass(frozen=True)
class WasteRouteVolumeAccounting:
    """Deterministic stage accounting bound to exact route and geometry manifests."""

    source_route_manifest_sha256: str
    source_geometry_manifest_sha256: str
    accounting_state: str = _ACCOUNTING_STATE
    physical_performance_state: str = _PHYSICAL_STATE

    def _validate_sources(
        self,
        *,
        network: WasteRouteNetwork,
        geometry: WasteRouteGeometryLedger,
    ) -> None:
        if type(network) is not WasteRouteNetwork:
            raise ValueError("network must be an exact WasteRouteNetwork contract")
        if type(geometry) is not WasteRouteGeometryLedger:
            raise ValueError("geometry must be an exact WasteRouteGeometryLedger contract")
        network.validate()
        geometry.validate(network=network)
        _canonical_sha256(self.source_route_manifest_sha256, name="source route manifest SHA-256")
        _canonical_sha256(self.source_geometry_manifest_sha256, name="source geometry manifest SHA-256")
        if self.source_route_manifest_sha256 != network.manifest_sha256():
            raise ValueError("waste route volume accounting is stale for the supplied topology")
        if self.source_geometry_manifest_sha256 != geometry.manifest_sha256(network=network):
            raise ValueError("waste route volume accounting is stale for the supplied geometry")
        if type(self.accounting_state) is not str or self.accounting_state != _ACCOUNTING_STATE:
            raise ValueError("waste route volume accounting must remain controlled digital accounting only")
        if type(self.physical_performance_state) is not str or self.physical_performance_state != _PHYSICAL_STATE:
            raise ValueError("geometric route accounting cannot promote physical performance")

    def validate(
        self,
        *,
        network: WasteRouteNetwork,
        geometry: WasteRouteGeometryLedger,
    ) -> None:
        self._validate_sources(network=network, geometry=geometry)
        stage_ids = self._segment_ids_by_stage_unchecked(network=network)
        classified = tuple(segment_id for ids in stage_ids.values() for segment_id in ids)
        topology_ids = tuple(sorted(segment.segment_id for segment in network.segments))
        if tuple(sorted(classified)) != topology_ids or len(classified) != len(set(classified)):
            raise ValueError("every waste route segment must classify into exactly one volume stage")

        stage_total = math.fsum(
            self._geometric_volume_ml_unchecked(stage, stage_ids=stage_ids, geometry=geometry)
            for stage in WasteRouteVolumeStage
        )
        total = geometry.total_geometric_internal_volume_ml(network=network)
        if not math.isclose(stage_total, total, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("waste route stage accounting does not conserve geometric volume")

    @staticmethod
    def _graph(network: WasteRouteNetwork) -> dict[str, list[str]]:
        graph = {node_id: [] for node_id in network.nodes}
        for segment in network.segments:
            graph[segment.source_node_id].append(segment.target_node_id)
        return graph

    @staticmethod
    def _reachable(start: str, target: str, graph: dict[str, list[str]]) -> bool:
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

    def _segment_ids_by_stage_unchecked(
        self,
        *,
        network: WasteRouteNetwork,
    ) -> dict[WasteRouteVolumeStage, tuple[str, ...]]:
        graph = self._graph(network)
        pump_out = next(
            node.node_id for node in network.nodes.values() if node.kind is WasteNodeKind.PUMP_OUTLET
        )
        staged: dict[WasteRouteVolumeStage, list[str]] = {
            stage: [] for stage in WasteRouteVolumeStage
        }
        for segment in network.segments:
            source_kind = network.nodes[segment.source_node_id].kind
            target_kind = network.nodes[segment.target_node_id].kind
            if (
                source_kind is WasteNodeKind.CARTRIDGE_INLET
                or target_kind is WasteNodeKind.CARTRIDGE_RETENTION
            ):
                stage = WasteRouteVolumeStage.CARTRIDGE_INTERNAL
            elif self._reachable(pump_out, segment.source_node_id, graph):
                stage = WasteRouteVolumeStage.POST_PUMP_TO_CARTRIDGE
            else:
                stage = WasteRouteVolumeStage.PRE_PUMP
            staged[stage].append(segment.segment_id)
        return {
            stage: tuple(sorted(segment_ids))
            for stage, segment_ids in staged.items()
        }

    def segment_ids_by_stage(
        self,
        *,
        network: WasteRouteNetwork,
        geometry: WasteRouteGeometryLedger,
    ) -> dict[WasteRouteVolumeStage, tuple[str, ...]]:
        self.validate(network=network, geometry=geometry)
        return self._segment_ids_by_stage_unchecked(network=network)

    @staticmethod
    def _geometric_volume_ml_unchecked(
        stage: WasteRouteVolumeStage,
        *,
        stage_ids: dict[WasteRouteVolumeStage, tuple[str, ...]],
        geometry: WasteRouteGeometryLedger,
    ) -> float:
        return math.fsum(
            geometry.segments[segment_id].geometric_internal_volume_ml()
            for segment_id in stage_ids[stage]
        )

    def geometric_volume_ml(
        self,
        stage: WasteRouteVolumeStage,
        *,
        network: WasteRouteNetwork,
        geometry: WasteRouteGeometryLedger,
    ) -> float:
        if type(stage) is not WasteRouteVolumeStage:
            raise ValueError("stage must be an exact WasteRouteVolumeStage")
        self.validate(network=network, geometry=geometry)
        stage_ids = self._segment_ids_by_stage_unchecked(network=network)
        return self._geometric_volume_ml_unchecked(stage, stage_ids=stage_ids, geometry=geometry)

    def manifest_sha256(
        self,
        *,
        network: WasteRouteNetwork,
        geometry: WasteRouteGeometryLedger,
    ) -> str:
        self.validate(network=network, geometry=geometry)
        stage_ids = self._segment_ids_by_stage_unchecked(network=network)
        payload = {
            "source_route_manifest_sha256": self.source_route_manifest_sha256,
            "source_geometry_manifest_sha256": self.source_geometry_manifest_sha256,
            "accounting_state": self.accounting_state,
            "physical_performance_state": self.physical_performance_state,
            "stages": [
                {
                    "stage": stage.value,
                    "segment_ids": list(stage_ids[stage]),
                    "geometric_volume_ml": self._geometric_volume_ml_unchecked(
                        stage, stage_ids=stage_ids, geometry=geometry
                    ),
                }
                for stage in WasteRouteVolumeStage
            ],
            "total_geometric_volume_ml": geometry.total_geometric_internal_volume_ml(network=network),
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
