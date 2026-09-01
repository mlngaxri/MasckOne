"""Iteration 27 waste-cartridge insertion, sealing, capacity and service architecture.

The cartridge external envelope and retained-capacity target are controlled design
inputs. They are not physical evidence of usable internal volume, retained liquid,
seal leakage, insertion robustness, service clearance or hygiene performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from .authority import Authority
from .distribution_geometry import DistributionGeometryArchitecture
from .structural_frame import StructuralFrameTopology
from .waste_acquisition import PHASE_MIXED_WASTE, WasteAcquisitionArchitecture
from .waste_pump_packaging import (
    INTERFACE_CARTRIDGE_INLET_I27,
    WastePumpPackagingArchitecture,
    WastePumpPackagingError,
)


class WasteCartridgeError(ValueError):
    """Raised when the Iteration 27 cartridge evidence boundary is violated."""


CARTRIDGE_ID = "WASTE-CARTRIDGE-I27"
RETENTION_REGION_ID = "WASTE-CARTRIDGE-RETENTION-REGION-I27"
INTERFACE_KEY = "WASTE-CARTRIDGE-KEYED-INSERTION-I27"
INTERFACE_SEAL = "WASTE-CARTRIDGE-REMOVABLE-SEAL-I27"
INTERFACE_SERVICE = "WASTE-CARTRIDGE-SERVICE-TRAJECTORY-I27"

EXTERNAL_ENVELOPE_STATUS = "ENGINEERING_BASELINE"
RETAINED_CAPACITY_STATUS = "VALIDATION_GATED"
SERVICE_CYCLES_STATUS = "VALIDATION_GATED"

KEYING_STATUS = "KEYED_INSERTION_TOPOLOGY_ONLY_KEY_GEOMETRY_AND_MISINSERTION_EVIDENCE_UNRESOLVED"
SEALING_STATUS = "REMOVABLE_WET_BOUNDARY_INTERFACE_ONLY_SEAL_GEOMETRY_COMPRESSION_AND_LEAKAGE_UNRESOLVED"
SERVICE_STATUS = "USER_REMOVAL_SERVICE_INTERFACE_ONLY_INSERTION_REMOVAL_AND_CLEARANCE_GEOMETRY_UNRESOLVED"
CAPACITY_STATUS = "RETENTION_REQUIREMENT_ONLY_USABLE_INTERNAL_CAPACITY_AND_MEDIA_BEHAVIOR_UNVERIFIED"
ARCHITECTURE_EVIDENCE_STATUS = (
    "DIGITAL_WASTE_CARTRIDGE_ARCHITECTURE_ONLY_NOT_USABLE_CAPACITY_RETENTION_SEAL_LEAKAGE_"
    "INSERTION_SERVICE_HYGIENE_OR_PHYSICAL_EVIDENCE"
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_EPSILON_ML = 1e-9


def _exact(value: object, expected: str, *, label: str) -> None:
    if type(value) is not str or value != expected:
        raise WasteCartridgeError(f"{label} must use its controlled exact state")


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise WasteCartridgeError(f"{label} must be exact built-in nonblank text")
    return value


def _sha(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise WasteCartridgeError(f"{label} must be canonical lowercase SHA-256")
    return value


def _real(value: object, *, label: str, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise WasteCartridgeError(f"{label} must be an exact finite numeric scalar")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise WasteCartridgeError(f"{label} must be representable as a finite float") from exc
    if not math.isfinite(result):
        raise WasteCartridgeError(f"{label} must be finite")
    if result == 0.0:
        result = 0.0
    if positive and result <= 0.0:
        raise WasteCartridgeError(f"{label} must be positive")
    return result


def _positive_int(value: object, *, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise WasteCartridgeError(f"{label} must be an exact positive integer")
    return value


def _triple(value: object, *, label: str) -> tuple[float, float, float]:
    if type(value) is not list or len(value) != 3:
        raise WasteCartridgeError(f"{label} must be an exact three-item list")
    result = tuple(_real(item, label=f"{label}[{index}]", positive=True) for index, item in enumerate(value))
    return result[0], result[1], result[2]


def _digest(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class CartridgeExternalEnvelope:
    x_mm: float
    y_mm: float
    z_mm: float
    authority_status: str

    def __post_init__(self) -> None:
        self.validate_invariants()

    def validate_invariants(self) -> None:
        x = _real(self.x_mm, label="cartridge external envelope x", positive=True)
        y = _real(self.y_mm, label="cartridge external envelope y", positive=True)
        z = _real(self.z_mm, label="cartridge external envelope z", positive=True)
        _exact(self.authority_status, EXTERNAL_ENVELOPE_STATUS, label="cartridge external envelope status")
        object.__setattr__(self, "x_mm", x)
        object.__setattr__(self, "y_mm", y)
        object.__setattr__(self, "z_mm", z)

    @property
    def bounding_volume_mL(self) -> float:
        self.validate_invariants()
        value = self.x_mm * self.y_mm * self.z_mm / 1000.0
        if not math.isfinite(value):
            raise WasteCartridgeError("cartridge external bounding volume must remain finite")
        return value

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "x_mm": self.x_mm,
            "y_mm": self.y_mm,
            "z_mm": self.z_mm,
            "authority_status": self.authority_status,
            "bounding_volume_mL": self.bounding_volume_mL,
            "bounding_volume_semantics": "EXTERNAL_RECTANGULAR_PACKAGE_UPPER_BOUND_NOT_USABLE_CAPACITY",
        }


@dataclass(frozen=True, slots=True)
class CartridgeCapacityReservation:
    retained_capacity_min_mL: float
    retained_capacity_status: str
    service_cycles_baseline: int
    service_cycles_status: str
    usable_internal_capacity_mL: float | None
    usable_capacity_evidence_sha256: str | None
    credits_absorbent_or_media_volume: bool
    capacity_status: str

    def __post_init__(self) -> None:
        self.validate_invariants()

    def validate_invariants(self) -> None:
        retained = _real(
            self.retained_capacity_min_mL,
            label="cartridge retained-capacity requirement",
            positive=True,
        )
        cycles = _positive_int(self.service_cycles_baseline, label="cartridge service-cycle baseline")
        _exact(self.retained_capacity_status, RETAINED_CAPACITY_STATUS, label="retained-capacity status")
        _exact(self.service_cycles_status, SERVICE_CYCLES_STATUS, label="service-cycle status")
        if self.usable_internal_capacity_mL is not None or self.usable_capacity_evidence_sha256 is not None:
            raise WasteCartridgeError(
                "Iteration 27 cannot promote or invent usable internal capacity before controlled physical capacity evidence"
            )
        if type(self.credits_absorbent_or_media_volume) is not bool:
            raise WasteCartridgeError("absorbent/media credit flag must be a literal bool")
        if self.credits_absorbent_or_media_volume:
            raise WasteCartridgeError(
                "Iteration 27 cannot credit absorbent or media volume toward retained capacity without physical evidence"
            )
        _exact(self.capacity_status, CAPACITY_STATUS, label="cartridge capacity evidence status")
        object.__setattr__(self, "retained_capacity_min_mL", retained)
        object.__setattr__(self, "service_cycles_baseline", cycles)

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "retained_capacity_min_mL": self.retained_capacity_min_mL,
            "retained_capacity_status": self.retained_capacity_status,
            "service_cycles_baseline": self.service_cycles_baseline,
            "service_cycles_status": self.service_cycles_status,
            "usable_internal_capacity_mL": self.usable_internal_capacity_mL,
            "usable_capacity_evidence_sha256": self.usable_capacity_evidence_sha256,
            "credits_absorbent_or_media_volume": self.credits_absorbent_or_media_volume,
            "capacity_status": self.capacity_status,
        }


@dataclass(frozen=True, slots=True)
class CartridgeInsertionSealServiceReservation:
    inlet_interface_id: str
    key_interface_id: str
    seal_interface_id: str
    service_interface_id: str
    retention_region_id: str
    phase_semantics: str
    key_geometry_mm: tuple[float, ...] | None
    allowed_insertion_axis_xyz: tuple[float, float, float] | None
    seal_gland_geometry_mm: tuple[float, ...] | None
    seal_compression_percent: float | None
    insertion_trajectory_xyz_mm: tuple[tuple[float, float, float], ...] | None
    removal_trajectory_xyz_mm: tuple[tuple[float, float, float], ...] | None
    service_clearance_mm: float | None
    retention_force_N: float | None
    keying_status: str
    sealing_status: str
    service_status: str

    def __post_init__(self) -> None:
        self.validate_invariants()

    def validate_invariants(self) -> None:
        _exact(self.inlet_interface_id, INTERFACE_CARTRIDGE_INLET_I27, label="cartridge inlet interface")
        _exact(self.key_interface_id, INTERFACE_KEY, label="cartridge key interface")
        _exact(self.seal_interface_id, INTERFACE_SEAL, label="cartridge seal interface")
        _exact(self.service_interface_id, INTERFACE_SERVICE, label="cartridge service interface")
        _exact(self.retention_region_id, RETENTION_REGION_ID, label="cartridge retention region")
        _exact(self.phase_semantics, PHASE_MIXED_WASTE, label="cartridge phase semantics")
        unresolved_geometry = (
            self.key_geometry_mm,
            self.allowed_insertion_axis_xyz,
            self.seal_gland_geometry_mm,
            self.seal_compression_percent,
            self.insertion_trajectory_xyz_mm,
            self.removal_trajectory_xyz_mm,
            self.service_clearance_mm,
            self.retention_force_N,
        )
        if any(value is not None for value in unresolved_geometry):
            raise WasteCartridgeError(
                "Iteration 27 cannot invent key, seal, trajectory, clearance, compression, or retention-force geometry"
            )
        _exact(self.keying_status, KEYING_STATUS, label="cartridge keying status")
        _exact(self.sealing_status, SEALING_STATUS, label="cartridge sealing status")
        _exact(self.service_status, SERVICE_STATUS, label="cartridge service status")

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "inlet_interface_id": self.inlet_interface_id,
            "key_interface_id": self.key_interface_id,
            "seal_interface_id": self.seal_interface_id,
            "service_interface_id": self.service_interface_id,
            "retention_region_id": self.retention_region_id,
            "phase_semantics": self.phase_semantics,
            "key_geometry_mm": self.key_geometry_mm,
            "allowed_insertion_axis_xyz": self.allowed_insertion_axis_xyz,
            "seal_gland_geometry_mm": self.seal_gland_geometry_mm,
            "seal_compression_percent": self.seal_compression_percent,
            "insertion_trajectory_xyz_mm": self.insertion_trajectory_xyz_mm,
            "removal_trajectory_xyz_mm": self.removal_trajectory_xyz_mm,
            "service_clearance_mm": self.service_clearance_mm,
            "retention_force_N": self.retention_force_N,
            "keying_status": self.keying_status,
            "sealing_status": self.sealing_status,
            "service_status": self.service_status,
        }


@dataclass(frozen=True, slots=True)
class WasteCartridgeArchitecture:
    cartridge_id: str
    source_waste_pump_sha256: str
    source_authority_revision: str
    phase_semantics: str
    envelope: CartridgeExternalEnvelope
    capacity: CartridgeCapacityReservation
    interfaces: CartridgeInsertionSealServiceReservation
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        self.validate_invariants()

    def validate_invariants(self) -> None:
        _exact(self.cartridge_id, CARTRIDGE_ID, label="cartridge ID")
        _sha(self.source_waste_pump_sha256, label="source waste-pump architecture")
        _text(self.source_authority_revision, label="source authority revision")
        _exact(self.phase_semantics, PHASE_MIXED_WASTE, label="cartridge phase semantics")
        if type(self.envelope) is not CartridgeExternalEnvelope:
            raise WasteCartridgeError("cartridge envelope must use the exact external-envelope type")
        if type(self.capacity) is not CartridgeCapacityReservation:
            raise WasteCartridgeError("cartridge capacity must use the exact capacity-reservation type")
        if type(self.interfaces) is not CartridgeInsertionSealServiceReservation:
            raise WasteCartridgeError("cartridge interfaces must use the exact insertion/seal/service type")
        self.envelope.validate_invariants()
        self.capacity.validate_invariants()
        self.interfaces.validate_invariants()
        if self.capacity.retained_capacity_min_mL > self.envelope.bounding_volume_mL + _EPSILON_ML:
            raise WasteCartridgeError(
                "retained-capacity requirement exceeds the external package bounding-volume upper bound"
            )
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WasteCartridgeError("Iteration 27 digital architecture is not physical validation evidence")
        _exact(self.evidence_status, ARCHITECTURE_EVIDENCE_STATUS, label="cartridge architecture evidence status")

    def validate_current_sources(
        self,
        *,
        authority: Authority,
        pump: WastePumpPackagingArchitecture,
        acquisition: WasteAcquisitionArchitecture,
        distribution: DistributionGeometryArchitecture,
        frame: StructuralFrameTopology,
    ) -> None:
        self.validate_invariants()
        if type(authority) is not Authority:
            raise WasteCartridgeError("authority must be the exact Authority type")
        if type(pump) is not WastePumpPackagingArchitecture:
            raise WasteCartridgeError("pump must be the exact Iteration 26 architecture type")
        if type(acquisition) is not WasteAcquisitionArchitecture:
            raise WasteCartridgeError("acquisition must be the exact Iteration 25 architecture type")
        if type(distribution) is not DistributionGeometryArchitecture:
            raise WasteCartridgeError("distribution must be the exact Iteration 24 architecture type")
        if type(frame) is not StructuralFrameTopology:
            raise WasteCartridgeError("frame must be the exact structural-frame topology type")
        try:
            pump.validate_current_sources(
                authority=authority,
                acquisition=acquisition,
                distribution=distribution,
                frame=frame,
            )
        except WastePumpPackagingError as exc:
            raise WasteCartridgeError("Iteration 26 waste-pump architecture is stale for current sources") from exc
        if self.source_waste_pump_sha256 != pump.architecture_sha256:
            raise WasteCartridgeError("cartridge architecture is stale for current Iteration 26 waste-pump architecture")
        if pump.routes[-1].target_interface_id != self.interfaces.inlet_interface_id:
            raise WasteCartridgeError("cartridge inlet no longer matches the Iteration 26 downstream handoff")
        if pump.station.phase_semantics != self.phase_semantics:
            raise WasteCartridgeError("cartridge mixed-phase semantics disagree with Iteration 26")

        revision = _text(authority.get("project", "authority_revision"), label="current authority revision")
        if self.source_authority_revision != revision:
            raise WasteCartridgeError("cartridge architecture is stale for current authority revision")
        cartridge = authority.get("fluid", "cartridge")
        if type(cartridge) is not dict:
            raise WasteCartridgeError("cartridge authority must be an exact mapping")
        envelope = _triple(cartridge.get("external_envelope_mm"), label="authority cartridge external envelope")
        _exact(cartridge.get("external_envelope_status"), EXTERNAL_ENVELOPE_STATUS, label="authority cartridge envelope status")
        retained = _real(
            cartridge.get("retained_capacity_min_mL"),
            label="authority retained-capacity requirement",
            positive=True,
        )
        _exact(cartridge.get("retained_capacity_status"), RETAINED_CAPACITY_STATUS, label="authority retained-capacity status")
        cycles = _positive_int(cartridge.get("service_cycles_baseline"), label="authority cartridge service cycles")
        _exact(cartridge.get("service_cycles_status"), SERVICE_CYCLES_STATUS, label="authority cartridge service-cycle status")
        current_envelope = (self.envelope.x_mm, self.envelope.y_mm, self.envelope.z_mm)
        if current_envelope != envelope:
            raise WasteCartridgeError("cartridge external envelope is stale for current authority")
        if self.capacity.retained_capacity_min_mL != retained:
            raise WasteCartridgeError("cartridge retained-capacity requirement is stale")
        if self.capacity.service_cycles_baseline != cycles:
            raise WasteCartridgeError("cartridge service-cycle baseline is stale")

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.validate_invariants()
        payload: dict[str, object] = {
            "cartridge_id": self.cartridge_id,
            "source_waste_pump_sha256": self.source_waste_pump_sha256,
            "source_authority_revision": self.source_authority_revision,
            "phase_semantics": self.phase_semantics,
            "envelope": self.envelope.manifest(),
            "capacity": self.capacity.manifest(),
            "interfaces": self.interfaces.manifest(),
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload

    @property
    def architecture_sha256(self) -> str:
        return _digest(self.manifest(include_sha=False))


def build_waste_cartridge_architecture(
    authority: Authority,
    pump: WastePumpPackagingArchitecture,
    acquisition: WasteAcquisitionArchitecture,
    distribution: DistributionGeometryArchitecture,
    frame: StructuralFrameTopology,
) -> WasteCartridgeArchitecture:
    if type(authority) is not Authority:
        raise WasteCartridgeError("authority must be the exact Authority type")
    if type(pump) is not WastePumpPackagingArchitecture:
        raise WasteCartridgeError("pump must be the exact Iteration 26 architecture type")
    if type(acquisition) is not WasteAcquisitionArchitecture:
        raise WasteCartridgeError("acquisition must be the exact Iteration 25 architecture type")
    if type(distribution) is not DistributionGeometryArchitecture:
        raise WasteCartridgeError("distribution must be the exact Iteration 24 architecture type")
    if type(frame) is not StructuralFrameTopology:
        raise WasteCartridgeError("frame must be the exact structural-frame topology type")
    try:
        pump.validate_current_sources(
            authority=authority,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )
    except WastePumpPackagingError as exc:
        raise WasteCartridgeError("Iteration 26 waste-pump architecture is stale for current sources") from exc

    cartridge = authority.get("fluid", "cartridge")
    if type(cartridge) is not dict:
        raise WasteCartridgeError("cartridge authority must be an exact mapping")
    envelope_xyz = _triple(cartridge.get("external_envelope_mm"), label="authority cartridge external envelope")
    _exact(cartridge.get("external_envelope_status"), EXTERNAL_ENVELOPE_STATUS, label="authority cartridge envelope status")
    retained = _real(
        cartridge.get("retained_capacity_min_mL"),
        label="authority retained-capacity requirement",
        positive=True,
    )
    _exact(cartridge.get("retained_capacity_status"), RETAINED_CAPACITY_STATUS, label="authority retained-capacity status")
    cycles = _positive_int(cartridge.get("service_cycles_baseline"), label="authority cartridge service cycles")
    _exact(cartridge.get("service_cycles_status"), SERVICE_CYCLES_STATUS, label="authority cartridge service-cycle status")
    revision = _text(authority.get("project", "authority_revision"), label="authority revision")

    architecture = WasteCartridgeArchitecture(
        cartridge_id=CARTRIDGE_ID,
        source_waste_pump_sha256=pump.architecture_sha256,
        source_authority_revision=revision,
        phase_semantics=PHASE_MIXED_WASTE,
        envelope=CartridgeExternalEnvelope(
            x_mm=envelope_xyz[0],
            y_mm=envelope_xyz[1],
            z_mm=envelope_xyz[2],
            authority_status=EXTERNAL_ENVELOPE_STATUS,
        ),
        capacity=CartridgeCapacityReservation(
            retained_capacity_min_mL=retained,
            retained_capacity_status=RETAINED_CAPACITY_STATUS,
            service_cycles_baseline=cycles,
            service_cycles_status=SERVICE_CYCLES_STATUS,
            usable_internal_capacity_mL=None,
            usable_capacity_evidence_sha256=None,
            credits_absorbent_or_media_volume=False,
            capacity_status=CAPACITY_STATUS,
        ),
        interfaces=CartridgeInsertionSealServiceReservation(
            inlet_interface_id=INTERFACE_CARTRIDGE_INLET_I27,
            key_interface_id=INTERFACE_KEY,
            seal_interface_id=INTERFACE_SEAL,
            service_interface_id=INTERFACE_SERVICE,
            retention_region_id=RETENTION_REGION_ID,
            phase_semantics=PHASE_MIXED_WASTE,
            key_geometry_mm=None,
            allowed_insertion_axis_xyz=None,
            seal_gland_geometry_mm=None,
            seal_compression_percent=None,
            insertion_trajectory_xyz_mm=None,
            removal_trajectory_xyz_mm=None,
            service_clearance_mm=None,
            retention_force_N=None,
            keying_status=KEYING_STATUS,
            sealing_status=SEALING_STATUS,
            service_status=SERVICE_STATUS,
        ),
        physical_validation_eligible=False,
        evidence_status=ARCHITECTURE_EVIDENCE_STATUS,
    )
    architecture.validate_current_sources(
        authority=authority,
        pump=pump,
        acquisition=acquisition,
        distribution=distribution,
        frame=frame,
    )
    return architecture
