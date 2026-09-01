"""Iteration 25 facial waste acquisition and transient-buffer architecture.

This module defines topology and evidence semantics only. It deliberately does not
invent gutter dimensions, capillary geometry, buffer capacity, suction pressure,
recovery performance, residual-liquid performance, or mixed-phase transport claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from .authority import Authority
from .distribution_geometry import DistributionGeometryArchitecture


class WasteAcquisitionError(ValueError):
    """Raised when waste-acquisition evidence boundaries are violated."""


PHASE_MIXED_WASTE = "MIXED_AIR_LIQUID_FOAM_CONTAMINANT"
HYGIENE_WET_DRAINABLE = "WET_DRAINABLE"
GEOMETRY_UNRESOLVED = "GEOMETRY_UNRESOLVED_REQUIRES_REGISTERED_SKIN_FACING_SURFACE"
BUFFER_UNRESOLVED = "TRANSIENT_CAPACITY_UNRESOLVED_REQUIRES_MIXED_PHASE_BENCH_EVIDENCE"
ROUTE_DESTINATION = "WASTE_PUMP_INLET_ITERATION_26_INTERFACE"
EVIDENCE_STATUS = "DIGITAL_WASTE_ACQUISITION_TOPOLOGY_ONLY_NOT_RECOVERY_RESIDUAL_LEAKAGE_HYGIENE_OR_PHYSICAL_EVIDENCE"
REGIONS = ("FOREHEAD", "LEFT_CHEEK", "RIGHT_CHEEK", "NOSE_T_ZONE", "CHIN_PERIORAL")
_SHA_RE = re.compile(r"[0-9a-f]{64}\Z")


def _exact(value: object, expected: str, label: str) -> str:
    if type(value) is not str or value != expected:
        raise WasteAcquisitionError(f"{label} must use its controlled exact state")
    return value


def _sha(value: object, label: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise WasteAcquisitionError(f"{label} must be canonical lowercase SHA-256")
    return value


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class WasteRegionIntent:
    region_id: str
    phase_semantics: str
    hygiene_class: str
    gutter_geometry_status: str
    capillary_geometry_status: str
    transient_buffer_status: str
    destination: str
    gutter_width_mm: None = None
    gutter_depth_mm: None = None
    transient_buffer_capacity_mL: None = None

    def __post_init__(self) -> None:
        if type(self.region_id) is not str or self.region_id not in REGIONS:
            raise WasteAcquisitionError("waste region must use controlled region identity")
        _exact(self.phase_semantics, PHASE_MIXED_WASTE, "waste phase semantics")
        _exact(self.hygiene_class, HYGIENE_WET_DRAINABLE, "waste hygiene class")
        _exact(self.gutter_geometry_status, GEOMETRY_UNRESOLVED, "gutter geometry status")
        _exact(self.capillary_geometry_status, GEOMETRY_UNRESOLVED, "capillary geometry status")
        _exact(self.transient_buffer_status, BUFFER_UNRESOLVED, "transient buffer status")
        _exact(self.destination, ROUTE_DESTINATION, "waste destination")
        if any(value is not None for value in (self.gutter_width_mm, self.gutter_depth_mm, self.transient_buffer_capacity_mL)):
            raise WasteAcquisitionError("Iteration 25 cannot invent waste gutter or buffer dimensions/capacity")

    def manifest(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class WasteAcquisitionArchitecture:
    source_distribution_sha256: str
    authority_revision: str
    recovery_ratio_min: float
    residual_free_liquid_max_uL: float
    regions: tuple[WasteRegionIntent, ...]
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        _sha(self.source_distribution_sha256, "source distribution architecture")
        if type(self.authority_revision) is not str or not self.authority_revision or self.authority_revision != self.authority_revision.strip():
            raise WasteAcquisitionError("authority revision must be exact built-in nonblank text")
        if type(self.recovery_ratio_min) not in (int, float) or not 0.0 < float(self.recovery_ratio_min) <= 1.0:
            raise WasteAcquisitionError("recovery ratio must be a bounded authority value")
        if type(self.residual_free_liquid_max_uL) not in (int, float) or float(self.residual_free_liquid_max_uL) < 0.0:
            raise WasteAcquisitionError("residual free-liquid limit must be non-negative")
        if type(self.regions) is not tuple or tuple(item.region_id for item in self.regions) != REGIONS:
            raise WasteAcquisitionError("waste acquisition must contain the complete canonical region set in order")
        if any(type(item) is not WasteRegionIntent for item in self.regions):
            raise WasteAcquisitionError("waste regions must be exact WasteRegionIntent records")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WasteAcquisitionError("Iteration 25 topology is not physical validation evidence")
        _exact(self.evidence_status, EVIDENCE_STATUS, "architecture evidence status")

    def manifest(self) -> dict[str, object]:
        return {
            "source_distribution_sha256": self.source_distribution_sha256,
            "authority_revision": self.authority_revision,
            "recovery_ratio_min": self.recovery_ratio_min,
            "residual_free_liquid_max_uL": self.residual_free_liquid_max_uL,
            "regions": [item.manifest() for item in self.regions],
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }

    def sha256(self) -> str:
        return _digest(self.manifest())


def build_waste_acquisition_architecture(
    authority: Authority,
    distribution: DistributionGeometryArchitecture,
) -> WasteAcquisitionArchitecture:
    """Build a fail-closed Iteration 25 topology from current controlled inputs."""
    if type(authority) is not Authority:
        raise WasteAcquisitionError("authority must be the exact Authority type")
    if type(distribution) is not DistributionGeometryArchitecture:
        raise WasteAcquisitionError("distribution must be the exact Iteration 24 architecture type")
    fluid = authority.raw.get("fluid")
    if type(fluid) is not dict or type(fluid.get("waste")) is not dict:
        raise WasteAcquisitionError("authority fluid.waste block is required")
    waste = fluid["waste"]
    if waste.get("status") != "VALIDATION_GATED":
        raise WasteAcquisitionError("waste performance authority must remain validation-gated")
    recovery = waste.get("recovery_ratio_min")
    residual = waste.get("residual_free_liquid_max_uL")
    if type(recovery) not in (int, float) or type(residual) not in (int, float):
        raise WasteAcquisitionError("waste authority values must be exact numeric scalars")
    regions = tuple(
        WasteRegionIntent(
            region_id=region,
            phase_semantics=PHASE_MIXED_WASTE,
            hygiene_class=HYGIENE_WET_DRAINABLE,
            gutter_geometry_status=GEOMETRY_UNRESOLVED,
            capillary_geometry_status=GEOMETRY_UNRESOLVED,
            transient_buffer_status=BUFFER_UNRESOLVED,
            destination=ROUTE_DESTINATION,
        )
        for region in REGIONS
    )
    return WasteAcquisitionArchitecture(
        source_distribution_sha256=distribution.sha256(),
        authority_revision=authority.revision,
        recovery_ratio_min=float(recovery),
        residual_free_liquid_max_uL=float(residual),
        regions=regions,
        physical_validation_eligible=False,
        evidence_status=EVIDENCE_STATUS,
    )
