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
from typing import Mapping


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
    "pump_off_power_loss",
    "gas_ingestion",
    "liquid_slugging",
    "foam_ingestion",
    "route_occlusion",
    "backflow",
    "cartridge_missing",
    "cartridge_misinstalled",
    "cartridge_full_or_reduced_retention",
    "protected_region_pooling",
})


@dataclass(frozen=True)
class CartridgeEnvelope:
    x_mm: float
    y_mm: float
    z_mm: float
    authority_status: str

    @property
    def bounding_volume_ml(self) -> float:
        """Rectangular package bounding volume only, never usable capacity."""
        return self.x_mm * self.y_mm * self.z_mm / 1000.0


@dataclass(frozen=True)
class CapacityContract:
    retained_capacity_target_ml: float
    target_status: str
    usable_capacity_ml: float | None = None
    usable_capacity_state: EvidenceState = EvidenceState.UNRESOLVED
    evidence_id: str | None = None
    credits_absorbent_media_volume: bool = False

    def validate(self) -> None:
        if self.retained_capacity_target_ml <= 0:
            raise ValueError("retained capacity target must be positive")
        if self.credits_absorbent_media_volume:
            raise ValueError("absorbent/media volume credit requires separate physical evidence and is not allowed in the digital baseline")
        if self.usable_capacity_ml is None:
            if self.usable_capacity_state is EvidenceState.VERIFIED or self.evidence_id is not None:
                raise ValueError("usable capacity cannot be verified without a numeric result and evidence")
            return
        if self.usable_capacity_ml <= 0:
            raise ValueError("usable capacity must be positive")
        if self.usable_capacity_state is not EvidenceState.VERIFIED or not self.evidence_id:
            raise ValueError("numeric usable capacity is blocked until it is VERIFIED with evidence_id")


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
    evidence_id: str | None = None

    def validate(self) -> None:
        for value in (
            self.pickup_assumption,
            self.air_location_assumption,
            self.drainage_or_capillary_assumption,
            self.pump_inlet_assumption,
            self.cartridge_assumption,
            self.backflow_assumption,
        ):
            if not value.strip():
                raise ValueError(f"orientation {self.orientation.value} has an empty assumption")
        if self.evidence_state is EvidenceState.VERIFIED and not self.evidence_id:
            raise ValueError("verified orientation behavior requires evidence_id")
        if self.evidence_state is not EvidenceState.VERIFIED and self.evidence_id:
            raise ValueError("evidence_id may only be attached to VERIFIED orientation behavior")


@dataclass(frozen=True)
class WasteArchitecture:
    source_main_sha: str
    authority_revision: str
    envelope: CartridgeEnvelope
    capacity: CapacityContract
    faults: frozenset[str]
    orientation_cases: Mapping[Orientation, OrientationCase]

    def validate(self) -> None:
        if len(self.source_main_sha) != 40 or any(c not in "0123456789abcdef" for c in self.source_main_sha):
            raise ValueError("source_main_sha must be a lowercase 40-character Git SHA")
        if not self.authority_revision.strip():
            raise ValueError("authority revision is required")
        if min(self.envelope.x_mm, self.envelope.y_mm, self.envelope.z_mm) <= 0:
            raise ValueError("cartridge envelope dimensions must be positive")
        self.capacity.validate()
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

    def manifest_sha256(self) -> str:
        self.validate()
        payload = {
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "envelope": {
                "x_mm": self.envelope.x_mm,
                "y_mm": self.envelope.y_mm,
                "z_mm": self.envelope.z_mm,
                "authority_status": self.envelope.authority_status,
            },
            "capacity": {
                "retained_capacity_target_ml": self.capacity.retained_capacity_target_ml,
                "target_status": self.capacity.target_status,
                "usable_capacity_ml": self.capacity.usable_capacity_ml,
                "usable_capacity_state": self.capacity.usable_capacity_state.value,
                "evidence_id": self.capacity.evidence_id,
                "credits_absorbent_media_volume": self.capacity.credits_absorbent_media_volume,
            },
            "faults": sorted(self.faults),
            "orientations": {
                orientation.value: {
                    "pickup": case.pickup_assumption,
                    "air": case.air_location_assumption,
                    "drainage": case.drainage_or_capillary_assumption,
                    "pump_inlet": case.pump_inlet_assumption,
                    "cartridge": case.cartridge_assumption,
                    "backflow": case.backflow_assumption,
                    "evidence_state": case.evidence_state.value,
                    "evidence_id": case.evidence_id,
                }
                for orientation, case in sorted(self.orientation_cases.items(), key=lambda item: item[0].value)
            },
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return sha256(encoded).hexdigest()
