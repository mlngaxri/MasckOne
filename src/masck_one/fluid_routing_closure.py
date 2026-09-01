"""Iteration 28 complete fresh/waste routing closure contract.

This module closes what can be closed digitally without inventing tubing geometry,
supplier bend-radius data, dead volume, or service clearances. It binds the current
fresh-pump, waste-pump and waste-cartridge architectures into one fail-closed route
ledger and makes every unresolved geometric/hydraulic/service quantity explicit.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from .fresh_pump_packaging import ROUTE_IDS as FRESH_ROUTE_IDS
from .waste_pump_packaging import ROUTE_IDS as WASTE_ROUTE_IDS


class FluidRoutingClosureError(ValueError):
    """Raised when the Iteration 28 routing evidence boundary is violated."""


ROUTE_IDS = tuple(FRESH_ROUTE_IDS) + tuple(WASTE_ROUTE_IDS)
ROUTING_STATUS = "TOPOLOGY_CLOSED_GEOMETRY_UNRESOLVED_PENDING_CONTROLLED_CENTERLINES"
BEND_RADIUS_STATUS = "UNRESOLVED_PENDING_CONTROLLED_TUBING_AND_ROUTE_GEOMETRY"
DEAD_VOLUME_STATUS = "UNRESOLVED_PENDING_CONTROLLED_INNER_DIAMETERS_AND_CENTERLINES"
SERVICE_CLEARANCE_STATUS = "UNRESOLVED_PENDING_ASSEMBLY_AND_SERVICE_TRAJECTORY_GEOMETRY"
HYDRAULIC_STATUS = "VALIDATION_GATED_PENDING_CONTROLLED_GEOMETRY_FLUID_PROPERTIES_AND_PUMP_CURVES"
ARCHITECTURE_EVIDENCE_STATUS = (
    "DIGITAL_FLUID_ROUTE_TOPOLOGY_CLOSURE_ONLY_NOT_BEND_RADIUS_DEAD_VOLUME_"
    "SERVICE_CLEARANCE_HYDRAULIC_OR_PHYSICAL_EVIDENCE"
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _sha(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise FluidRoutingClosureError(f"{label} must be canonical lowercase SHA-256")
    return value


def _digest(payload: object) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RouteClosure:
    route_id: str
    source_architecture_sha256: str
    centerline_length_mm: float | None = None
    tubing_inner_diameter_mm: float | None = None
    minimum_bend_radius_mm: float | None = None
    achieved_bend_radius_mm: float | None = None
    dead_volume_mL: float | None = None
    minimum_service_clearance_mm: float | None = None
    routing_status: str = ROUTING_STATUS
    bend_radius_status: str = BEND_RADIUS_STATUS
    dead_volume_status: str = DEAD_VOLUME_STATUS
    service_clearance_status: str = SERVICE_CLEARANCE_STATUS
    hydraulic_status: str = HYDRAULIC_STATUS

    def __post_init__(self) -> None:
        if type(self.route_id) is not str or self.route_id not in ROUTE_IDS:
            raise FluidRoutingClosureError(f"unknown controlled route {self.route_id!r}")
        _sha(self.source_architecture_sha256, label=f"{self.route_id} source architecture")
        unresolved = (
            self.centerline_length_mm,
            self.tubing_inner_diameter_mm,
            self.minimum_bend_radius_mm,
            self.achieved_bend_radius_mm,
            self.dead_volume_mL,
            self.minimum_service_clearance_mm,
        )
        if any(value is not None for value in unresolved):
            raise FluidRoutingClosureError(
                "Iteration 28 cannot invent route geometry, tubing dimensions, bend radius, dead volume, or service clearance"
            )
        expected = (
            (self.routing_status, ROUTING_STATUS),
            (self.bend_radius_status, BEND_RADIUS_STATUS),
            (self.dead_volume_status, DEAD_VOLUME_STATUS),
            (self.service_clearance_status, SERVICE_CLEARANCE_STATUS),
            (self.hydraulic_status, HYDRAULIC_STATUS),
        )
        if any(type(value) is not str or value != controlled for value, controlled in expected):
            raise FluidRoutingClosureError("route statuses must remain at their controlled unresolved/validation-gated states")

    def manifest(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class FluidRoutingClosure:
    fresh_architecture_sha256: str
    waste_pump_architecture_sha256: str
    waste_cartridge_architecture_sha256: str
    routes: tuple[RouteClosure, ...]
    architecture_evidence_status: str = ARCHITECTURE_EVIDENCE_STATUS

    def __post_init__(self) -> None:
        for label, value in (
            ("fresh architecture", self.fresh_architecture_sha256),
            ("waste-pump architecture", self.waste_pump_architecture_sha256),
            ("waste-cartridge architecture", self.waste_cartridge_architecture_sha256),
        ):
            _sha(value, label=label)
        if type(self.routes) is not tuple or len(self.routes) != len(ROUTE_IDS):
            raise FluidRoutingClosureError("routing closure must contain every controlled fresh and waste route exactly once")
        ids = tuple(route.route_id for route in self.routes)
        if len(set(ids)) != len(ids) or set(ids) != set(ROUTE_IDS):
            raise FluidRoutingClosureError("routing closure route identities must be unique and complete")
        if type(self.architecture_evidence_status) is not str or self.architecture_evidence_status != ARCHITECTURE_EVIDENCE_STATUS:
            raise FluidRoutingClosureError("routing closure cannot promote its evidence status")

    def manifest(self) -> dict[str, object]:
        payload = {
            "fresh_architecture_sha256": self.fresh_architecture_sha256,
            "waste_pump_architecture_sha256": self.waste_pump_architecture_sha256,
            "waste_cartridge_architecture_sha256": self.waste_cartridge_architecture_sha256,
            "routes": [route.manifest() for route in self.routes],
            "architecture_evidence_status": self.architecture_evidence_status,
        }
        payload["architecture_sha256"] = _digest(payload)
        return payload


def build_fluid_routing_closure(
    *, fresh_architecture_sha256: str, waste_pump_architecture_sha256: str, waste_cartridge_architecture_sha256: str
) -> FluidRoutingClosure:
    source_by_route = {
        **{route_id: fresh_architecture_sha256 for route_id in FRESH_ROUTE_IDS},
        **{route_id: waste_pump_architecture_sha256 for route_id in WASTE_ROUTE_IDS},
    }
    return FluidRoutingClosure(
        fresh_architecture_sha256=fresh_architecture_sha256,
        waste_pump_architecture_sha256=waste_pump_architecture_sha256,
        waste_cartridge_architecture_sha256=waste_cartridge_architecture_sha256,
        routes=tuple(RouteClosure(route_id=route_id, source_architecture_sha256=source_by_route[route_id]) for route_id in ROUTE_IDS),
    )
