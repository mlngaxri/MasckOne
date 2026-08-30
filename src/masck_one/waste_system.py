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
        if not self.evidence_id.strip() or not self.revision.strip():
            raise ValueError("verified evidence requires non-empty id and revision")
        if not _SHA256_RE.fullmatch(self.artifact_sha256):
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
        if not self.authority_status.strip():
            raise ValueError("cartridge envelope authority_status is required")

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
        if not self.target_status.strip():
            raise ValueError("retained capacity target status is required")
        if self.credits_absorbent_media_volume:
            raise ValueError("absorbent/media volume credit requires separate physical evidence and is not allowed in the digital baseline")
        if self.usable_capacity_ml is None:
            if self.usable_capacity_state is EvidenceState.VERIFIED or self.evidence is not None:
                raise ValueError("usable capacity cannot be verified without a numeric result and evidence")
            return
        _require_finite_positive(self.usable_capacity_ml, name="usable capacity")
        if self.usable_capacity_state is not EvidenceState.VERIFIED or self.evidence is None:
            raise ValueError("numeric usable capacity is blocked until it is VERIFIED with cryptographic evidence")
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
        for value in (self.pickup_assumption, self.air_location_assumption,
                      self.drainage_or_capillary_assumption, self.pump_inlet_assumption,
                      self.cartridge_assumption, self.backflow_assumption):
            if not value.strip():
                raise ValueError(f"orientation {self.orientation.value} has an empty assumption")
        if self.evidence_state is EvidenceState.VERIFIED:
            if self.evidence is None:
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

    def validate(self) -> None:
        """Validate intrinsic integrity while preserving historical provenance."""
        if not _GIT_SHA_RE.fullmatch(self.source_main_sha):
            raise ValueError("source_main_sha must be a lowercase 40-character Git SHA")
        if not self.authority_revision.strip():
            raise ValueError("authority revision is required")
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

        missing_faults = REQUIRED_MIXED_PHASE_FAULTS - self.faults
        if missing_faults:
            raise ValueError(f"mixed-phase fault registry incomplete: {sorted(missing_faults)}")
        supplied = frozenset(self.orientation_cases)
        if supplied != REQUIRED_ORIENTATIONS:
            missing = REQUIRED_ORIENTATIONS - supplied
            extra = supplied - REQUIRED_ORIENTATIONS
            raise ValueError(f"orientation registry mismatch; missing={sorted(x.value for x in missing)}, extra={sorted(str(x) for x in extra)}")
        for key, case in self.orientation_cases.items():
            if key is not case.orientation:
                raise ValueError("orientation mapping key does not match case orientation")
            case.validate()

    def validate_current_release(self, *, expected_main_sha: str, expected_authority_revision: str) -> None:
        """Validate intrinsic integrity plus freshness against the release context.

        Historical objects remain readable through validate(), but an object cannot be
        released as current merely because its recorded SHA/revision are syntactically valid.
        """
        self.validate()
        if not _GIT_SHA_RE.fullmatch(expected_main_sha):
            raise ValueError("expected_main_sha must be a lowercase 40-character Git SHA")
        if not expected_authority_revision.strip():
            raise ValueError("expected_authority_revision is required")
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
