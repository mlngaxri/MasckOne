"""Topology-bound digital geometry ledger for mixed-phase waste routes.

This module deliberately separates route connectivity from route geometry. Topology
remains authoritative in :mod:`waste_routes`; this ledger binds one immutable geometry
record to every topology segment without duplicating source/target truth.

Derived internal volume is a geometric accounting quantity only. It is not hydraulic,
priming, purge, recovery, backflow, leakage, or orientation evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re
from types import MappingProxyType
from typing import Mapping

from .waste_routes import WasteRouteNetwork

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_GEOMETRY_STATE = "CONTROLLED_DIGITAL_GEOMETRY_ONLY"
_PHYSICAL_STATE = "VALIDATION_GATED"


def _canonical_id(value: object, *, name: str) -> str:
    if type(value) is not str or not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} must be exact built-in canonical lowercase identifier text")
    return value


def _canonical_sha256(value: object, *, name: str) -> str:
    if type(value) is not str or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{name} must be exact built-in canonical lowercase SHA-256")
    return value


def _positive_finite_number(value: object, *, name: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise ValueError(f"{name} must be an exact built-in int or float")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0.0:
        raise ValueError(f"{name} must be finite and > 0")
    return numeric


@dataclass(frozen=True)
class WasteRouteGeometrySegment:
    """One route segment's controlled digital tube/path geometry.

    ``required_min_bend_radius_mm`` is a design constraint. ``realized_min_bend_radius_mm``
    is the minimum radius found in the controlled digital path. Passing the comparison
    does not prove manufacturability, kink resistance, mixed-phase transport, or life.
    """

    segment_id: str
    centerline_length_mm: float
    inner_diameter_mm: float
    required_min_bend_radius_mm: float
    realized_min_bend_radius_mm: float
    geometry_state: str = _GEOMETRY_STATE
    physical_performance_state: str = _PHYSICAL_STATE

    def validate(self) -> None:
        _canonical_id(self.segment_id, name="waste geometry segment_id")
        length = _positive_finite_number(self.centerline_length_mm, name="centerline_length_mm")
        diameter = _positive_finite_number(self.inner_diameter_mm, name="inner_diameter_mm")
        required_radius = _positive_finite_number(
            self.required_min_bend_radius_mm, name="required_min_bend_radius_mm"
        )
        realized_radius = _positive_finite_number(
            self.realized_min_bend_radius_mm, name="realized_min_bend_radius_mm"
        )
        if type(self.geometry_state) is not str or self.geometry_state != _GEOMETRY_STATE:
            raise ValueError("waste route geometry must remain controlled digital geometry only")
        if type(self.physical_performance_state) is not str or self.physical_performance_state != _PHYSICAL_STATE:
            raise ValueError("waste route geometry cannot promote physical performance")
        if realized_radius < required_radius:
            raise ValueError("realized waste-route bend radius violates the required minimum")
        # Guard against nonsensical geometry that can otherwise create tiny, numerically valid ledgers.
        if length < diameter:
            raise ValueError("waste route centerline length cannot be shorter than its inner diameter")

    def geometric_internal_volume_mm3(self) -> float:
        self.validate()
        diameter = float(self.inner_diameter_mm)
        length = float(self.centerline_length_mm)
        return math.pi * (diameter * 0.5) ** 2 * length

    def geometric_internal_volume_ml(self) -> float:
        return self.geometric_internal_volume_mm3() / 1000.0


@dataclass(frozen=True)
class WasteRouteGeometryLedger:
    """Immutable one-to-one geometry binding for a validated waste topology."""

    source_route_manifest_sha256: str
    segments: Mapping[str, WasteRouteGeometrySegment]

    def __post_init__(self) -> None:
        if isinstance(self.segments, Mapping):
            object.__setattr__(self, "segments", MappingProxyType(dict(self.segments)))

    def validate(self, *, network: WasteRouteNetwork) -> None:
        if type(network) is not WasteRouteNetwork:
            raise ValueError("network must be an exact WasteRouteNetwork contract")
        network.validate()
        _canonical_sha256(self.source_route_manifest_sha256, name="source route manifest SHA-256")
        if self.source_route_manifest_sha256 != network.manifest_sha256():
            raise ValueError("waste route geometry ledger is stale for the supplied route topology")
        if not isinstance(self.segments, Mapping) or not self.segments:
            raise ValueError("waste route geometry ledger requires segment geometry")

        topology_ids = {segment.segment_id for segment in network.segments}
        geometry_ids: set[str] = set()
        for key, segment in self.segments.items():
            _canonical_id(key, name="waste geometry mapping key")
            if type(segment) is not WasteRouteGeometrySegment:
                raise ValueError("waste geometry mapping must contain exact WasteRouteGeometrySegment values")
            segment.validate()
            if key != segment.segment_id:
                raise ValueError("waste geometry mapping key must equal segment_id")
            if segment.segment_id in geometry_ids:
                raise ValueError("duplicate waste geometry segment identity")
            geometry_ids.add(segment.segment_id)

        missing = topology_ids - geometry_ids
        extra = geometry_ids - topology_ids
        if missing or extra:
            raise ValueError(
                "waste route geometry must bind exactly one record to every topology segment"
            )

    def total_geometric_internal_volume_ml(self, *, network: WasteRouteNetwork) -> float:
        self.validate(network=network)
        return math.fsum(segment.geometric_internal_volume_ml() for segment in self.segments.values())

    def manifest_sha256(self, *, network: WasteRouteNetwork) -> str:
        self.validate(network=network)
        payload = {
            "source_route_manifest_sha256": self.source_route_manifest_sha256,
            "geometry_state": _GEOMETRY_STATE,
            "physical_performance_state": _PHYSICAL_STATE,
            "segments": [
                {
                    "segment_id": segment.segment_id,
                    "centerline_length_mm": float(segment.centerline_length_mm),
                    "inner_diameter_mm": float(segment.inner_diameter_mm),
                    "required_min_bend_radius_mm": float(segment.required_min_bend_radius_mm),
                    "realized_min_bend_radius_mm": float(segment.realized_min_bend_radius_mm),
                    "geometric_internal_volume_ml": segment.geometric_internal_volume_ml(),
                }
                for segment in sorted(self.segments.values(), key=lambda item: item.segment_id)
            ],
            "total_geometric_internal_volume_ml": self.total_geometric_internal_volume_ml(network=network),
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
