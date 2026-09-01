"""Iteration 28 fresh/waste routing closure without invented physical dimensions.

This module closes the digital accounting contract for routing properties that are
only meaningful when controlled route geometry and supplier tubing limits exist.
Unknown bend radius, dead volume, and service clearance remain validation-gated.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class RoutingClosureError(ValueError):
    """Raised when routing closure attempts to cross an evidence boundary."""


def _sha(value: object, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise RoutingClosureError(f"{label} must be canonical lowercase SHA-256")
    return value


def _positive(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise RoutingClosureError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise RoutingClosureError(f"{label} must be finite and positive")
    return result


def _optional_positive(value: object, label: str) -> float | None:
    return None if value is None else _positive(value, label)


def _digest(payload: object) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RouteEvidence:
    route_id: str
    phase: str
    source_interface_id: str
    sink_interface_id: str
    source_architecture_sha256: str
    centerline_length_mm: float | None = None
    tube_inner_diameter_mm: float | None = None
    minimum_bend_radius_mm: float | None = None
    supplier_minimum_bend_radius_mm: float | None = None
    minimum_service_clearance_mm: float | None = None
    required_service_clearance_mm: float | None = None

    def __post_init__(self) -> None:
        for label, value in (("route_id", self.route_id), ("phase", self.phase),
                             ("source_interface_id", self.source_interface_id),
                             ("sink_interface_id", self.sink_interface_id)):
            if type(value) is not str or not value or value != value.strip():
                raise RoutingClosureError(f"{label} must be exact nonblank text")
        _sha(self.source_architecture_sha256, "source architecture SHA")
        for label in ("centerline_length_mm", "tube_inner_diameter_mm", "minimum_bend_radius_mm",
                      "supplier_minimum_bend_radius_mm", "minimum_service_clearance_mm",
                      "required_service_clearance_mm"):
            object.__setattr__(self, label, _optional_positive(getattr(self, label), label))

    @property
    def dead_volume_mL(self) -> float | None:
        if self.centerline_length_mm is None or self.tube_inner_diameter_mm is None:
            return None
        radius = self.tube_inner_diameter_mm / 2.0
        return math.pi * radius * radius * self.centerline_length_mm / 1000.0

    @property
    def bend_radius_status(self) -> str:
        if self.minimum_bend_radius_mm is None or self.supplier_minimum_bend_radius_mm is None:
            return "VALIDATION_GATED"
        return "DIGITAL_PASS" if self.minimum_bend_radius_mm >= self.supplier_minimum_bend_radius_mm else "DIGITAL_FAIL"

    @property
    def service_clearance_status(self) -> str:
        if self.minimum_service_clearance_mm is None or self.required_service_clearance_mm is None:
            return "VALIDATION_GATED"
        return "DIGITAL_PASS" if self.minimum_service_clearance_mm >= self.required_service_clearance_mm else "DIGITAL_FAIL"

    def manifest(self) -> dict[str, object]:
        return {
            "route_id": self.route_id, "phase": self.phase,
            "source_interface_id": self.source_interface_id, "sink_interface_id": self.sink_interface_id,
            "source_architecture_sha256": self.source_architecture_sha256,
            "centerline_length_mm": self.centerline_length_mm,
            "tube_inner_diameter_mm": self.tube_inner_diameter_mm,
            "dead_volume_mL": self.dead_volume_mL,
            "minimum_bend_radius_mm": self.minimum_bend_radius_mm,
            "supplier_minimum_bend_radius_mm": self.supplier_minimum_bend_radius_mm,
            "bend_radius_status": self.bend_radius_status,
            "minimum_service_clearance_mm": self.minimum_service_clearance_mm,
            "required_service_clearance_mm": self.required_service_clearance_mm,
            "service_clearance_status": self.service_clearance_status,
        }


@dataclass(frozen=True, slots=True)
class RoutingClosure:
    waste_cartridge_architecture_sha256: str
    routes: tuple[RouteEvidence, ...]

    def __post_init__(self) -> None:
        _sha(self.waste_cartridge_architecture_sha256, "Iteration 27 architecture SHA")
        if type(self.routes) is not tuple or not self.routes:
            raise RoutingClosureError("routes must be a nonempty exact tuple")
        ids = [route.route_id for route in self.routes]
        if len(ids) != len(set(ids)):
            raise RoutingClosureError("route IDs must be unique")

    @property
    def total_known_dead_volume_mL(self) -> float:
        return sum(v for route in self.routes if (v := route.dead_volume_mL) is not None)

    @property
    def dead_volume_status(self) -> str:
        return "DIGITAL_ACCOUNTED" if all(route.dead_volume_mL is not None for route in self.routes) else "VALIDATION_GATED"

    @property
    def architecture_sha256(self) -> str:
        return _digest(self.manifest(include_sha=False))

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload = {
            "iteration": 28,
            "evidence_status": "DIGITAL_ROUTING_ACCOUNTING_ONLY_NOT_PHYSICAL_FLOW_SERVICE_OR_DURABILITY_EVIDENCE",
            "waste_cartridge_architecture_sha256": self.waste_cartridge_architecture_sha256,
            "routes": [route.manifest() for route in self.routes],
            "total_known_dead_volume_mL": self.total_known_dead_volume_mL,
            "dead_volume_status": self.dead_volume_status,
        }
        if include_sha:
            payload["architecture_sha256"] = _digest(payload)
        return payload
