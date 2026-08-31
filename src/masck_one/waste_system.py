"""Evidence-bounded waste and cartridge architecture.

This module deliberately separates package geometry from retained-volume evidence.
It is a digital architecture contract, not proof of mixed-phase recovery, capacity,
or orientation performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import math
import re
from types import MappingProxyType
from typing import Mapping


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_CAPACITY_EPSILON_ML = 1e-9


def _require_finite_positive(value: float, *, name: str) -> None:
    """Reject NaN/infinity before any ordering or conservation comparison."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite numeric value")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def _require_nonblank_text(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value


class EvidenceState(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    VALIDATION_GATED = "VALIDATION_GATED"
    VERIFIED = "VERIFIED"


class Orientation(str, Enum):
    UPRIGHT = "upright"
    RECLINED = "reclined"
    LEFT_SIDE = "left_side"
    RIGHT_SIDE = "right_side"
    FACE_UP = "face_up"
    FACE_DOWN = "face_down"
    TRANSITION = "transition"


REQUIRED_ORIENTATIONS = frozenset(Orientation)
REQUIRED_MIXED_PHASE_FAULTS = frozenset({
    "pump_off_power_loss", "gas_ingestion", "liquid_slugging", "foam_ingestion",
    "route_occlusion", "backflow", "cartridge_missing", "cartridge_misinstalled",
    "cartridge_full_or_reduced_retention", "protected_region_pooling",
})


@dataclass(frozen=True)
class EvidenceReference:
    """Cryptographic identity for evidence eligible to support VERIFIED state."""
    evidence_id: str
    revision: str
    artifact_sha256: str

    def validate(self) -> None:
        _require_nonblank_text(self.evidence_id, name="verified evidence id")
        _require_nonblank_text(self.revision, name="verified evidence revision")
        if not isinstance(self.artifact_sha256, str) or not _SHA256_RE.fullmatch(self.artifact_sha256):
            raise ValueError("verified evidence artifact_sha256 must be lowercase 64-hex")


@dataclass(frozen=True)
class CartridgeEnvelope:
    x_mm: float
    y_mm: float
    z_mm: float
    authority_status: str

    def validate(self) -> None:
        _require_finite_positive(self.x_mm, name="cartridge envelope x_mm")
        _require_finite_positive(self.y_mm, name="cartridge envelope y_mm")
        _require_finite_positive(self.z_mm, name="cartridge envelope z_mm")
        _require_nonblank_text(self.authority_status, name="cartridge envelope authority_status")

    @property
    def bounding_volume_ml(self) -> float:
        """Rectangular package bounding volume only, never usable capacity."""
        self.validate()
        volume = self.x_mm * self.y_mm * self.z_mm / 1000.0
        if not math.isfinite(volume):
            raise ValueError("cartridge external bounding volume must be finite")
        return volume


@dataclass(frozen=True)
class CapacityContract:
    retained_capacity_target_ml: float
    target_status: str
    usable_capacity_ml: float | None = None
    usable_capacity_state: EvidenceState = EvidenceState.UNRESOLVED
    evidence: EvidenceReference | None = None
    credits_absorbent_media_volume: bool = False

    def validate(self) -> None:
        _require_finite_positive(self.retained_capacity_target_ml, name="retained capacity target")
        _require_nonblank_text(self.target_status, name="retained capacity target status")
        if not isinstance(self.usable_capacity_state, EvidenceState):
            raise ValueError("usable capacity state must be an EvidenceState")
        if type(self.credits_absorbent_media_volume) is not bool:
            raise ValueError("credits_absorbent_media_volume must be a literal bool")
        if self.credits_absorbent_media_volume:
            raise ValueError("absorbent/media volume credit requires separate physical evidence and is not allowed in the digital baseline")
        if self.usable_capacity_ml is None:
            if self.usable_capacity_state is EvidenceState.VERIFIED or self.evidence is not None:
                raise ValueError("usable capacity cannot be verified without a numeric result and evidence")
            return
        _require_finite_positive(self.usable_capacity_ml, name="usable capacity")
        if self.usable_capacity_state is not EvidenceState.VERIFIED or self.evidence is None:
            raise ValueError("numeric usable capacity is blocked until it is VERIFIED with cryptographic evidence")
        if not isinstance(self.evidence, EvidenceReference):
            raise ValueError("usable capacity evidence must be an EvidenceReference")
        self.evidence.validate()


@dataclass(frozen=True)
class OrientationCase:
    orientation: Orientation
    pickup_assumption: str
    air_location_assumption: str
    drainage_or_capillary_assumption: str
    pump_inlet_assumption: str
    cartridge_assumption: str
    backflow_assumption: str
    evidence_state: EvidenceState = EvidenceState.VALIDATION_GATED
    evidence: EvidenceReference | None = None

    def validate(self) -> None:
        if not isinstance(self.orientation, Orientation):
            raise ValueError("orientation case must use an Orientation value")
        for name, value in (
            ("pickup assumption", self.pickup_assumption),
            ("air-location assumption", self.air_location_assumption),
            ("drainage/capillary assumption", self.drainage_or_capillary_assumption),
            ("pump-inlet assumption", self.pump_inlet_assumption),
            ("cartridge assumption", self.cartridge_assumption),
            ("backflow assumption", self.backflow_assumption),
        ):
            _require_nonblank_text(value, name=f"orientation {self.orientation.value} {name}")
        if not isinstance(self.evidence_state, EvidenceState):
            raise ValueError("orientation evidence state must be an EvidenceState")
        if self.evidence_state is EvidenceState.VERIFIED:
            if not isinstance(self.evidence, EvidenceReference):
                raise ValueError("verified orientation behavior requires cryptographic evidence")
            self.evidence.validate()
        elif self.evidence is not None:
            raise ValueError("evidence may only be attached to VERIFIED orientation behavior")


@dataclass(frozen=True)
class WasteArchitecture:
    source_main_sha: str
    authority_revision: str
    envelope: CartridgeEnvelope
    capacity: CapacityContract
    faults: frozenset[str]
    orientation_cases: Mapping[Orientation, OrientationCase]

    def __post_init__(self) -> None:
        # Snapshot caller-owned mappings so a validated release object cannot change
        # topology/evidence semantics after construction through external mutation.
        if isinstance(self.orientation_cases, Mapping):
            object.__setattr__(self, "orientation_cases", MappingProxyType(dict(self.orientation_cases)))

    def validate(self) -> None:
        """Validate intrinsic integrity while preserving historical provenance."""
        if not isinstance(self.source_main_sha, str) or not _GIT_SHA_RE.fullmatch(self.source_main_sha):
            raise ValueError("source_main_sha must be a lowercase 40-character Git SHA")
        _require_nonblank_text(self.authority_revision, name="authority revision")
        if not isinstance(self.envelope, CartridgeEnvelope):
            raise ValueError("waste architecture envelope must be a CartridgeEnvelope")
        if not isinstance(self.capacity, CapacityContract):
            raise ValueError("waste architecture capacity must be a CapacityContract")
        self.envelope.validate()
        self.capacity.validate()

        # Geometry conservation is an absolute upper-bound check, not capacity evidence.
        # Any real usable/retained volume must be lower after walls, seals, venting,
        # media, contamination boundaries and other displaced package volume are known.
        bounding_volume_ml = self.envelope.bounding_volume_ml
        if self.capacity.retained_capacity_target_ml > bounding_volume_ml + _CAPACITY_EPSILON_ML:
            raise ValueError(
                "retained capacity target exceeds the cartridge external bounding-volume upper bound"
            )
        if (self.capacity.usable_capacity_ml is not None and
                self.capacity.usable_capacity_ml > bounding_volume_ml + _CAPACITY_EPSILON_ML):
            raise ValueError(
                "usable capacity exceeds the cartridge external bounding-volume upper bound"
            )

        if not isinstance(self.faults, frozenset) or not all(isinstance(fault, str) and fault for fault in self.faults):
            raise ValueError("mixed-phase faults must be an immutable frozenset of non-empty string identifiers")
        missing_faults = REQUIRED_MIXED_PHASE_FAULTS - self.faults
        if missing_faults:
            raise ValueError(f"mixed-phase fault registry incomplete: {sorted(missing_faults)}")
        if not isinstance(self.orientation_cases, Mapping):
            raise ValueError("orientation cases must be a mapping")
        supplied = frozenset(self.orientation_cases)
        if supplied != REQUIRED_ORIENTATIONS:
            missing = REQUIRED_ORIENTATIONS - supplied
            extra = supplied - REQUIRED_ORIENTATIONS
            raise ValueError(f"orientation registry mismatch; missing={sorted(x.value for x in missing)}, extra={sorted(str(x) for x in extra)}")
        for key, case in self.orientation_cases.items():
            if not isinstance(case, OrientationCase):
                raise ValueError("orientation mapping values must be OrientationCase records")
            if key is not case.orientation:
                raise ValueError("orientation mapping key does not match case orientation")
            case.validate()

    def validate_current_release(self, *, expected_main_sha: str, expected_authority_revision: str) -> None:
        """Validate intrinsic integrity plus freshness against the release context.

        Historical objects remain readable through validate(), but an object cannot be
        released as current merely because its recorded SHA/revision are syntactically valid.
        """
        self.validate()
        if not isinstance(expected_main_sha, str) or not _GIT_SHA_RE.fullmatch(expected_main_sha):
            raise ValueError("expected_main_sha must be a lowercase 40-character Git SHA")
        _require_nonblank_text(expected_authority_revision, name="expected_authority_revision")
        if self.source_main_sha != expected_main_sha:
            raise ValueError("waste architecture is stale for the expected upstream main SHA")
        if self.authority_revision != expected_authority_revision:
            raise ValueError("waste architecture is stale for the expected authority revision")

    def manifest_sha256(self) -> str:
        self.validate()

        def evidence_payload(evidence: EvidenceReference | None):
            return None if evidence is None else {
                "evidence_id": evidence.evidence_id,
                "revision": evidence.revision,
                "artifact_sha256": evidence.artifact_sha256,
            }

        payload = {
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "envelope": {"x_mm": self.envelope.x_mm, "y_mm": self.envelope.y_mm,
                         "z_mm": self.envelope.z_mm, "authority_status": self.envelope.authority_status},
            "capacity": {"retained_capacity_target_ml": self.capacity.retained_capacity_target_ml,
                         "target_status": self.capacity.target_status,
                         "usable_capacity_ml": self.capacity.usable_capacity_ml,
                         "usable_capacity_state": self.capacity.usable_capacity_state.value,
                         "evidence": evidence_payload(self.capacity.evidence),
                         "credits_absorbent_media_volume": self.capacity.credits_absorbent_media_volume},
            "faults": sorted(self.faults),
            "orientations": {orientation.value: {
                "pickup": case.pickup_assumption, "air": case.air_location_assumption,
                "drainage": case.drainage_or_capillary_assumption,
                "pump_inlet": case.pump_inlet_assumption, "cartridge": case.cartridge_assumption,
                "backflow": case.backflow_assumption, "evidence_state": case.evidence_state.value,
                "evidence": evidence_payload(case.evidence),
            } for orientation, case in sorted(self.orientation_cases.items(), key=lambda item: item[0].value)},
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return sha256(encoded).hexdigest()
