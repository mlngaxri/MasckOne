"""Device-side wet/dry route backbone.

This module owns route identity and interface continuity outside the cartridge body.
Dimensions and performance not present in released authority remain deliberately open.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json


class WetDryRouteError(ValueError):
    """Raised when wet/dry route topology fails closed."""


ROUTE_ORDER = (
    "FRESH_WATER",
    "CLEANSER",
    "MIXED_WASTE_ACQUISITION",
    "MIXED_WASTE_PUMP",
    "PASSIVE_BACKFLOW",
    "DEVICE_CARTRIDGE_DISCONNECT",
)


@dataclass(frozen=True, slots=True)
class RouteInterface:
    interface_id: str
    fluid_identity: str
    upstream: str
    downstream: str
    side: str
    geometry_status: str = "PHYSICAL_GEOMETRY_OPEN"
    performance_status: str = "PHYSICAL_VALIDATION_OPEN"

    def __post_init__(self) -> None:
        for value in (self.interface_id, self.fluid_identity, self.upstream, self.downstream):
            if type(value) is not str or not value.strip():
                raise WetDryRouteError("route interface text must be nonblank")
        if self.side not in {"WET", "DRY_BULKHEAD"}:
            raise WetDryRouteError("route interface must declare WET or DRY_BULKHEAD side")
        if self.upstream == self.downstream:
            raise WetDryRouteError("route interface may not teleport onto one endpoint")
        if self.performance_status != "PHYSICAL_VALIDATION_OPEN":
            raise WetDryRouteError("unmeasured route performance must remain validation-open")

    def manifest(self) -> dict[str, str]:
        return {
            "interface_id": self.interface_id,
            "fluid_identity": self.fluid_identity,
            "upstream": self.upstream,
            "downstream": self.downstream,
            "side": self.side,
            "geometry_status": self.geometry_status,
            "performance_status": self.performance_status,
        }


@dataclass(frozen=True, slots=True)
class WetDryRouteBackbone:
    source_release_sha: str
    interfaces: tuple[RouteInterface, ...]
    sequence: tuple[str, ...] = ROUTE_ORDER
    cartridge_body_owner: str = "EXTERNAL_CARTRIDGE_OWNER"
    removed_state_closure_status: str = "PHYSICAL_VALIDATION_OPEN"

    def __post_init__(self) -> None:
        if len(self.source_release_sha) != 40 or any(c not in "0123456789abcdef" for c in self.source_release_sha):
            raise WetDryRouteError("source release must be a canonical git SHA")
        if self.sequence != ROUTE_ORDER:
            raise WetDryRouteError("fluid order must preserve acquisition -> waste pump -> passive backflow -> cartridge disconnect")
        ids = [item.interface_id for item in self.interfaces]
        if len(ids) != len(set(ids)):
            raise WetDryRouteError("route interface IDs must be unique")
        if self.cartridge_body_owner != "EXTERNAL_CARTRIDGE_OWNER":
            raise WetDryRouteError("support lane may not claim cartridge-body ownership")
        if self.removed_state_closure_status != "PHYSICAL_VALIDATION_OPEN":
            raise WetDryRouteError("removed-state closure performance remains physical-validation-open")

    def manifest(self) -> dict[str, object]:
        payload = {
            "source_release_sha": self.source_release_sha,
            "sequence": list(self.sequence),
            "interfaces": [item.manifest() for item in self.interfaces],
            "cartridge_body_owner": self.cartridge_body_owner,
            "removed_state_closure_status": self.removed_state_closure_status,
            "explicitly_unclaimed": [
                "pump_performance",
                "seal_performance",
                "leakage_performance",
                "dead_volume",
                "condensation_behaviour",
                "cartridge_body_closure",
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        payload["manifest_sha256"] = sha256(canonical).hexdigest()
        return payload


def released_backbone() -> WetDryRouteBackbone:
    """Return the topology bound to the current released integration baseline."""
    return WetDryRouteBackbone(
        source_release_sha="45b5eb63e2fc5feaaffbe056d0645be1e31a9021",
        interfaces=(
            RouteInterface("WD-FRESH-01", "WATER", "FRESH_STORAGE", "WATER_MANIFOLD", "WET"),
            RouteInterface("WD-CLEANSER-01", "CLEANSER", "CLEANSER_STORAGE", "CLEANSER_MANIFOLD", "WET"),
            RouteInterface("WD-WASTE-ACQ-01", "MIXED_WASTE", "TREATMENT_RECOVERY", "WASTE_PUMP", "WET"),
            RouteInterface("WD-WASTE-PUMP-01", "MIXED_WASTE", "WASTE_PUMP", "PASSIVE_BACKFLOW", "WET"),
            RouteInterface("WD-WASTE-CART-01", "MIXED_WASTE", "PASSIVE_BACKFLOW", "DEVICE_CARTRIDGE_DISCONNECT", "WET"),
            RouteInterface("WD-BULKHEAD-01", "ELECTRICAL_DRY", "DRY_HARNESS", "WET_DRY_BULKHEAD", "DRY_BULKHEAD"),
        ),
    )
