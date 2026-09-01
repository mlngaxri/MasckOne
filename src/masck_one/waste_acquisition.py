"""Iteration 25 facial waste acquisition and transient-buffer architecture.

Topology and evidence semantics only. No gutter dimensions, capillary geometry,
buffer capacity, suction pressure, recovery, residual-liquid, or mixed-phase
transport performance is invented here.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from .authority import Authority
from .cleanser_storage import CleanserStorageArchitecture
from .coverage import FacialCoverageMesh
from .distribution_geometry import (
    DistributionGeometryArchitecture,
    DistributionGeometryError,
)
from .distribution_manifold import DistributionManifoldArchitecture
from .fresh_pump_packaging import FreshPumpPackagingArchitecture
from .iteration25_source_integrity import (
    Iteration25SourceIntegrityError,
    validate_iteration25_source_graph,
)
from .protected_volumes import ProtectedVolumeSet
from .structural_frame import StructuralFrameTopology
from .water_reservoir import WaterReservoirArchitecture


class WasteAcquisitionError(ValueError):
    """Raised when Iteration 25 topology or evidence boundaries are violated."""


PHASE_MIXED_WASTE = "MIXED_AIR_LIQUID_FOAM_CONTAMINANT"
HYGIENE_WET_DRAINABLE = "WET_DRAINABLE"
GEOMETRY_UNRESOLVED = "GEOMETRY_UNRESOLVED_REQUIRES_REGISTERED_SKIN_FACING_SURFACE"
BUFFER_UNRESOLVED = "TRANSIENT_CAPACITY_UNRESOLVED_REQUIRES_MIXED_PHASE_BENCH_EVIDENCE"
ROUTE_DESTINATION = "WASTE_PUMP_INLET_ITERATION_26_INTERFACE"
EVIDENCE_STATUS = (
    "DIGITAL_WASTE_ACQUISITION_TOPOLOGY_ONLY_NOT_RECOVERY_RESIDUAL_LEAKAGE_"
    "HYGIENE_OR_PHYSICAL_EVIDENCE"
)
REGIONS = ("FOREHEAD", "LEFT_CHEEK", "RIGHT_CHEEK", "NOSE_T_ZONE", "CHIN_PERIORAL")
_SHA_RE = re.compile(r"[0-9a-f]{64}\Z")


def _exact(value: object, expected: str, label: str) -> None:
    if type(value) is not str or value != expected:
        raise WasteAcquisitionError(f"{label} must use its controlled exact state")


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise WasteAcquisitionError(f"{label} must be exact built-in nonblank text")
    return value


def _sha(value: object, label: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise WasteAcquisitionError(f"{label} must be canonical lowercase SHA-256")
    return value


def _real(
    value: object,
    label: str,
    *,
    positive: bool = False,
    nonnegative: bool = False,
    at_most: float | None = None,
) -> float:
    if type(value) not in (int, float):
        raise WasteAcquisitionError(f"{label} must be an exact finite numeric scalar")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise WasteAcquisitionError(f"{label} must be representable as a finite float") from exc
    if not math.isfinite(result):
        raise WasteAcquisitionError(f"{label} must be finite")
    if result == 0.0:
        result = 0.0
    if positive and result <= 0.0:
        raise WasteAcquisitionError(f"{label} must be positive")
    if nonnegative and result < 0.0:
        raise WasteAcquisitionError(f"{label} must be non-negative")
    if at_most is not None and result > at_most:
        raise WasteAcquisitionError(f"{label} must be <= {at_most}")
    return result


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


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
        self.validate_invariants()

    def validate_invariants(self) -> None:
        if type(self.region_id) is not str or self.region_id not in REGIONS:
            raise WasteAcquisitionError("waste region must use controlled region identity")
        _exact(self.phase_semantics, PHASE_MIXED_WASTE, "waste phase semantics")
        _exact(self.hygiene_class, HYGIENE_WET_DRAINABLE, "waste hygiene class")
        _exact(self.gutter_geometry_status, GEOMETRY_UNRESOLVED, "gutter geometry status")
        _exact(self.capillary_geometry_status, GEOMETRY_UNRESOLVED, "capillary geometry status")
        _exact(self.transient_buffer_status, BUFFER_UNRESOLVED, "transient buffer status")
        _exact(self.destination, ROUTE_DESTINATION, "waste destination")
        if any(
            value is not None
            for value in (
                self.gutter_width_mm,
                self.gutter_depth_mm,
                self.transient_buffer_capacity_mL,
            )
        ):
            raise WasteAcquisitionError(
                "Iteration 25 cannot invent waste gutter or buffer dimensions/capacity"
            )

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "region_id": self.region_id,
            "phase_semantics": self.phase_semantics,
            "hygiene_class": self.hygiene_class,
            "gutter_geometry_status": self.gutter_geometry_status,
            "capillary_geometry_status": self.capillary_geometry_status,
            "transient_buffer_status": self.transient_buffer_status,
            "destination": self.destination,
            "gutter_width_mm": self.gutter_width_mm,
            "gutter_depth_mm": self.gutter_depth_mm,
            "transient_buffer_capacity_mL": self.transient_buffer_capacity_mL,
        }


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
        self.validate_invariants()

    def validate_invariants(self) -> None:
        _sha(self.source_distribution_sha256, "source distribution architecture")
        _text(self.authority_revision, "authority revision")
        recovery = _real(
            self.recovery_ratio_min,
            "recovery ratio",
            positive=True,
            at_most=1.0,
        )
        residual = _real(
            self.residual_free_liquid_max_uL,
            "residual free-liquid limit",
            nonnegative=True,
        )
        if (
            type(self.regions) is not tuple
            or any(type(item) is not WasteRegionIntent for item in self.regions)
            or tuple(item.region_id for item in self.regions) != REGIONS
        ):
            raise WasteAcquisitionError(
                "waste acquisition must contain the complete canonical region set in order"
            )
        for item in self.regions:
            item.validate_invariants()
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WasteAcquisitionError("Iteration 25 topology is not physical validation evidence")
        _exact(self.evidence_status, EVIDENCE_STATUS, "architecture evidence status")
        object.__setattr__(self, "recovery_ratio_min", recovery)
        object.__setattr__(self, "residual_free_liquid_max_uL", residual)

    def validate_current_sources(
        self,
        *,
        authority: Authority,
        distribution: DistributionGeometryArchitecture,
        manifold: DistributionManifoldArchitecture,
        pump: FreshPumpPackagingArchitecture,
        water: WaterReservoirArchitecture,
        cleanser: CleanserStorageArchitecture,
        frame: StructuralFrameTopology,
        coverage: FacialCoverageMesh,
        protected: ProtectedVolumeSet,
    ) -> None:
        """Fail closed when any direct or inherited Iteration 25 source is stale."""
        self.validate_invariants()
        if type(authority) is not Authority:
            raise WasteAcquisitionError("authority must be the exact Authority type")
        if type(distribution) is not DistributionGeometryArchitecture:
            raise WasteAcquisitionError(
                "distribution must be the exact Iteration 24 architecture type"
            )

        try:
            validate_iteration25_source_graph(
                authority=authority,
                water=water,
                cleanser=cleanser,
                frame=frame,
                pump=pump,
                manifold=manifold,
                coverage=coverage,
                protected=protected,
                distribution=distribution,
            )
        except Iteration25SourceIntegrityError as exc:
            raise WasteAcquisitionError(
                "waste acquisition inherited source graph is not canonical current"
            ) from exc

        try:
            distribution.validate_current_sources(
                authority=authority,
                manifold=manifold,
                pump=pump,
                water=water,
                cleanser=cleanser,
                frame=frame,
                coverage=coverage,
                protected=protected,
            )
        except DistributionGeometryError as exc:
            raise WasteAcquisitionError(
                "waste acquisition inherited Iteration 24 source chain is stale"
            ) from exc

        if self.source_distribution_sha256 != distribution.architecture_sha256:
            raise WasteAcquisitionError("waste acquisition is stale for current distribution geometry")

        current_revision = _text(
            authority.get("project", "authority_revision"),
            "current authority revision",
        )
        if self.authority_revision != current_revision:
            raise WasteAcquisitionError("waste acquisition is stale for current authority revision")

        waste = authority.get("fluid", "waste")
        if type(waste) is not dict:
            raise WasteAcquisitionError("waste authority must be an exact mapping")
        _exact(waste.get("status"), "VALIDATION_GATED", "waste performance authority status")
        expected_recovery = _real(
            waste.get("recovery_ratio_min"),
            "waste authority recovery ratio",
            positive=True,
            at_most=1.0,
        )
        expected_residual = _real(
            waste.get("residual_free_liquid_max_uL"),
            "waste authority residual free-liquid limit",
            nonnegative=True,
        )
        if self.recovery_ratio_min != expected_recovery:
            raise WasteAcquisitionError("waste acquisition recovery requirement is stale")
        if self.residual_free_liquid_max_uL != expected_residual:
            raise WasteAcquisitionError("waste acquisition residual-liquid requirement is stale")

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "source_distribution_sha256": self.source_distribution_sha256,
            "authority_revision": self.authority_revision,
            "recovery_ratio_min": self.recovery_ratio_min,
            "residual_free_liquid_max_uL": self.residual_free_liquid_max_uL,
            "regions": [item.manifest() for item in self.regions],
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }

    @property
    def architecture_sha256(self) -> str:
        return _digest(self.manifest())


def build_waste_acquisition_architecture(
    authority: Authority,
    distribution: DistributionGeometryArchitecture,
    manifold: DistributionManifoldArchitecture,
    pump: FreshPumpPackagingArchitecture,
    water: WaterReservoirArchitecture,
    cleanser: CleanserStorageArchitecture,
    frame: StructuralFrameTopology,
    coverage: FacialCoverageMesh,
    protected: ProtectedVolumeSet,
) -> WasteAcquisitionArchitecture:
    if type(authority) is not Authority:
        raise WasteAcquisitionError("authority must be the exact Authority type")
    if type(distribution) is not DistributionGeometryArchitecture:
        raise WasteAcquisitionError("distribution must be the exact Iteration 24 architecture type")

    waste = authority.get("fluid", "waste")
    if type(waste) is not dict:
        raise WasteAcquisitionError("waste authority must be an exact mapping")
    _exact(waste.get("status"), "VALIDATION_GATED", "waste performance authority status")
    recovery = _real(
        waste.get("recovery_ratio_min"),
        "waste authority recovery ratio",
        positive=True,
        at_most=1.0,
    )
    residual = _real(
        waste.get("residual_free_liquid_max_uL"),
        "waste authority residual free-liquid limit",
        nonnegative=True,
    )
    revision = _text(
        authority.get("project", "authority_revision"),
        "authority revision",
    )
    regions = tuple(
        WasteRegionIntent(
            region_id,
            PHASE_MIXED_WASTE,
            HYGIENE_WET_DRAINABLE,
            GEOMETRY_UNRESOLVED,
            GEOMETRY_UNRESOLVED,
            BUFFER_UNRESOLVED,
            ROUTE_DESTINATION,
        )
        for region_id in REGIONS
    )
    architecture = WasteAcquisitionArchitecture(
        distribution.architecture_sha256,
        revision,
        recovery,
        residual,
        regions,
        False,
        EVIDENCE_STATUS,
    )
    architecture.validate_current_sources(
        authority=authority,
        distribution=distribution,
        manifold=manifold,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=coverage,
        protected=protected,
    )
    return architecture