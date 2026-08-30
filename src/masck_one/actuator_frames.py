from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math

from .authority import Authority
from .structural_frame import StructuralFrameTopology, RESERVATION_ACTUATION


class ActuatorFrameError(ValueError):
    pass


ZONE_IDS = (
    "ACTUATOR_ZONE_SUPERIOR_LEFT",
    "ACTUATOR_ZONE_SUPERIOR_RIGHT",
    "ACTUATOR_ZONE_INFERIOR_LEFT",
    "ACTUATOR_ZONE_INFERIOR_RIGHT",
)


def _canonical_sha256(value: object) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ActuatorFrameError("Actuator architecture source identities must be lowercase canonical SHA-256 strings")


def _real_finite(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value))


def _nonblank_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


@dataclass(frozen=True, slots=True)
class ActuatorLocalFrame:
    zone_id: str
    origin_xyz_mm: tuple[float, float, float] | None
    axis_azimuth_deg: float | None
    axis_angle_baseline_deg: float
    axis_angle_doe_deg: tuple[float, ...]
    structural_mount_datum_id: str | None
    actuator_envelope_mm: tuple[float, float, float] | None
    origin_status: str
    axis_status: str
    mount_status: str
    envelope_status: str

    def __post_init__(self) -> None:
        if not isinstance(self.zone_id, str) or self.zone_id not in ZONE_IDS:
            raise ActuatorFrameError(f"Unknown actuator zone {self.zone_id!r}")
        if self.origin_xyz_mm is not None and (len(self.origin_xyz_mm) != 3 or not all(_real_finite(v) for v in self.origin_xyz_mm)):
            raise ActuatorFrameError("Actuator-frame origin must be a finite XYZ point with real numeric coordinates")
        if self.axis_azimuth_deg is not None and not _real_finite(self.axis_azimuth_deg):
            raise ActuatorFrameError("Actuator axis azimuth must be a real finite number when defined")
        if not _real_finite(self.axis_angle_baseline_deg) or not self.axis_angle_doe_deg or not all(_real_finite(v) for v in self.axis_angle_doe_deg):
            raise ActuatorFrameError("Actuator angle definition must contain real finite numerics and a non-empty DOE")
        baseline = float(self.axis_angle_baseline_deg)
        doe = tuple(float(v) for v in self.axis_angle_doe_deg)
        if tuple(sorted(set(doe))) != doe:
            raise ActuatorFrameError("Actuator angle DOE must be unique and ascending")
        if baseline not in doe:
            raise ActuatorFrameError("Actuator baseline angle must be represented in the DOE")
        if self.structural_mount_datum_id is not None and not _nonblank_text(self.structural_mount_datum_id):
            raise ActuatorFrameError("Structural mount datum identity must be a nonblank string when resolved")
        if self.actuator_envelope_mm is not None and (len(self.actuator_envelope_mm) != 3 or not all(_real_finite(v) and float(v) > 0 for v in self.actuator_envelope_mm)):
            raise ActuatorFrameError("Actuator envelope must contain three positive finite real dimensions")
        if not all(_nonblank_text(value) for value in (self.origin_status, self.axis_status, self.mount_status, self.envelope_status)):
            raise ActuatorFrameError("Actuator-frame status metadata must be explicit nonblank strings")

    @property
    def placement_resolved(self) -> bool:
        return self.origin_xyz_mm is not None and self.axis_azimuth_deg is not None

    def manifest(self) -> dict[str, object]:
        return {"zone_id": self.zone_id, "origin_xyz_mm": None if self.origin_xyz_mm is None else list(self.origin_xyz_mm), "axis_azimuth_deg": self.axis_azimuth_deg, "axis_angle_baseline_deg": self.axis_angle_baseline_deg, "axis_angle_doe_deg": list(self.axis_angle_doe_deg), "structural_mount_datum_id": self.structural_mount_datum_id, "actuator_envelope_mm": None if self.actuator_envelope_mm is None else list(self.actuator_envelope_mm), "origin_status": self.origin_status, "axis_status": self.axis_status, "mount_status": self.mount_status, "envelope_status": self.envelope_status, "placement_resolved": self.placement_resolved}


@dataclass(frozen=True, slots=True)
class ActuatorFrameArchitecture:
    source_structural_frame_sha256: str
    source_registered_mesh_sha256: str
    source_authority_revision: str
    frames: tuple[ActuatorLocalFrame, ...]
    independent_zone_count: int
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        _canonical_sha256(self.source_structural_frame_sha256); _canonical_sha256(self.source_registered_mesh_sha256)
        if not _nonblank_text(self.source_authority_revision): raise ActuatorFrameError("Authority revision must be an explicit nonblank string")
        if tuple(frame.zone_id for frame in self.frames) != ZONE_IDS: raise ActuatorFrameError("Actuator frames must preserve the controlled four-zone order")
        if isinstance(self.independent_zone_count, bool) or not isinstance(self.independent_zone_count, int) or self.independent_zone_count != len(ZONE_IDS): raise ActuatorFrameError("Actuator architecture must preserve four independent zones")
        if not isinstance(self.physical_validation_eligible, bool): raise ActuatorFrameError("Physical-validation eligibility must be an explicit boolean")
        if self.physical_validation_eligible: raise ActuatorFrameError("Digital actuator mount/frame topology cannot be physical evidence")
        if not _nonblank_text(self.evidence_status): raise ActuatorFrameError("Actuator architecture evidence status must be an explicit nonblank string")

    @property
    def architecture_sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    @property
    def sweep_ready(self) -> bool:
        return all(frame.placement_resolved and frame.actuator_envelope_mm is not None and frame.structural_mount_datum_id is not None for frame in self.frames)

    def require_sweep_ready(self, *, structural_frame: StructuralFrameTopology, authority: Authority) -> None:
        self.validate_current_sources(structural_frame=structural_frame, authority=authority)
        if not self.sweep_ready: raise ActuatorFrameError("Continuous actuator sweep/collision analysis is blocked until all local-frame origins, axis azimuths, structural mount datums, and actuator envelopes are resolved")

    def validate_current_sources(self, *, structural_frame: StructuralFrameTopology, authority: Authority) -> None:
        if self.source_structural_frame_sha256 != structural_frame.topology_sha256: raise ActuatorFrameError("Actuator architecture is stale for the current structural-frame topology")
        if self.source_registered_mesh_sha256 != structural_frame.source_registered_mesh_sha256: raise ActuatorFrameError("Actuator architecture registered-mesh provenance is stale")
        if self.source_authority_revision != str(authority.get("project", "authority_revision")): raise ActuatorFrameError("Actuator architecture authority revision is stale")
        if self.independent_zone_count != int(authority.number("actuation", "count")): raise ActuatorFrameError("Actuator zone count no longer matches authority")

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload = {"source_structural_frame_sha256": self.source_structural_frame_sha256, "source_registered_mesh_sha256": self.source_registered_mesh_sha256, "source_authority_revision": self.source_authority_revision, "frames": [frame.manifest() for frame in self.frames], "independent_zone_count": self.independent_zone_count, "sweep_ready": self.sweep_ready, "physical_validation_eligible": self.physical_validation_eligible, "evidence_status": self.evidence_status}
        if include_sha: payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_actuator_frame_architecture(authority: Authority, structural_frame: StructuralFrameTopology) -> ActuatorFrameArchitecture:
    reservation = next((r for r in structural_frame.reservations if r.reservation_id == RESERVATION_ACTUATION), None)
    if reservation is None: raise ActuatorFrameError("Structural frame lacks the controlled actuation reservation")
    count = int(authority.number("actuation", "count"))
    if reservation.interface_count != count or count != len(ZONE_IDS): raise ActuatorFrameError("Structural actuation reservation does not match the frozen four-zone architecture")
    baseline = float(authority.get("actuation", "clean", "axis_angle_baseline_deg")); doe = tuple(float(v) for v in authority.get("actuation", "clean", "axis_angle_doe_deg"))
    frames = tuple(ActuatorLocalFrame(zone_id=zone_id, origin_xyz_mm=None, axis_azimuth_deg=None, axis_angle_baseline_deg=baseline, axis_angle_doe_deg=doe, structural_mount_datum_id=None, actuator_envelope_mm=None, origin_status="UNRESOLVED_NO_AUTHORITY_OR_REGISTERED_3D_MOUNT_PLACEMENT", axis_status="ANGLE_DOE_AUTHORITY_BOUND_AZIMUTH_UNRESOLVED", mount_status="STRUCTURAL_RESERVATION_BOUND_FINAL_MOUNT_DATUM_UNRESOLVED", envelope_status="PRODUCTION_ACTUATOR_NOT_FROZEN_SUPPLIER_ENVELOPE_UNRESOLVED") for zone_id in ZONE_IDS)
    architecture = ActuatorFrameArchitecture(source_structural_frame_sha256=structural_frame.topology_sha256, source_registered_mesh_sha256=structural_frame.source_registered_mesh_sha256, source_authority_revision=str(authority.get("project", "authority_revision")), frames=frames, independent_zone_count=count, physical_validation_eligible=False, evidence_status="DIGITAL_ACTUATOR_FRAME_AND_MOUNT_INTERFACE_CONTRACT_ONLY_NOT_PLACEMENT_COLLISION_FORCE_FATIGUE_OR_PHYSICAL_EVIDENCE")
    architecture.validate_current_sources(structural_frame=structural_frame, authority=authority)
    return architecture
