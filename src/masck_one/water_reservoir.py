from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math

from .authority import Authority


class WaterReservoirError(ValueError):
    """Raised when the Iteration-20 water-storage architecture violates authority or evidence boundaries."""


WATER_RESERVOIR_ID = "MASCK_ONE-WATER-RESERVOIR-PRIMARY"
PORT_FILL = "WATER-PORT-FILL"
PORT_VENT = "WATER-PORT-VENT"
PORT_PICKUP = "WATER-PORT-PICKUP"
PORT_IDS = (PORT_FILL, PORT_VENT, PORT_PICKUP)
ORIENTATION_CASE_IDS = (
    "ORIENTATION_NEUTRAL",
    "ORIENTATION_PITCH_FORWARD",
    "ORIENTATION_PITCH_BACK",
    "ORIENTATION_ROLL_LEFT",
    "ORIENTATION_ROLL_RIGHT",
    "ORIENTATION_FACE_UP",
    "ORIENTATION_FACE_DOWN",
)


def _real(value: object, *, label: str, positive: bool = False, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WaterReservoirError(f"{label} must be a finite real number")
    out = float(value)
    if not math.isfinite(out):
        raise WaterReservoirError(f"{label} must be finite")
    if positive and out <= 0.0:
        raise WaterReservoirError(f"{label} must be positive")
    if nonnegative and out < 0.0:
        raise WaterReservoirError(f"{label} must be non-negative")
    return out


def _text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise WaterReservoirError(f"{label} must be an exact nonblank string")
    return value


@dataclass(frozen=True, slots=True)
class ReservoirPort:
    port_id: str
    role: str
    fluid_identity: str
    geometry_status: str
    sealing_status: str
    service_status: str

    def __post_init__(self) -> None:
        if self.port_id not in PORT_IDS:
            raise WaterReservoirError(f"Unknown water-reservoir port {self.port_id!r}")
        if self.fluid_identity != "FRESH_WATER":
            raise WaterReservoirError("Water-reservoir ports cannot silently change fluid identity")
        for label, value in (
            ("port role", self.role),
            ("geometry status", self.geometry_status),
            ("sealing status", self.sealing_status),
            ("service status", self.service_status),
        ):
            _text(value, label=label)

    def manifest(self) -> dict[str, object]:
        return {
            "port_id": self.port_id,
            "role": self.role,
            "fluid_identity": self.fluid_identity,
            "geometry_status": self.geometry_status,
            "sealing_status": self.sealing_status,
            "service_status": self.service_status,
        }


@dataclass(frozen=True, slots=True)
class ReservoirVolumeEvaluation:
    source_architecture_sha256: str
    computed_internal_volume_mL: float
    computed_dead_volume_mL: float
    computed_usable_volume_mL: float
    gross_target_mL: float
    minimum_usable_mL: float
    gross_target_met: bool
    minimum_usable_met: bool
    evidence_kind: str

    def __post_init__(self) -> None:
        if not isinstance(self.source_architecture_sha256, str) or len(self.source_architecture_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.source_architecture_sha256):
            raise WaterReservoirError("Volume evaluation requires a canonical architecture SHA-256")
        internal = _real(self.computed_internal_volume_mL, label="computed internal volume", positive=True)
        dead = _real(self.computed_dead_volume_mL, label="computed dead volume", nonnegative=True)
        usable = _real(self.computed_usable_volume_mL, label="computed usable volume", nonnegative=True)
        gross = _real(self.gross_target_mL, label="gross target", positive=True)
        minimum = _real(self.minimum_usable_mL, label="minimum usable volume", positive=True)
        if dead > internal:
            raise WaterReservoirError("Dead volume cannot exceed computed internal volume")
        if not math.isclose(usable, internal - dead, rel_tol=0.0, abs_tol=1e-12):
            raise WaterReservoirError("Computed usable volume must equal internal volume minus dead volume")
        if type(self.gross_target_met) is not bool or self.gross_target_met != (internal >= gross):
            raise WaterReservoirError("Gross-target result must be derived from computed geometry")
        if type(self.minimum_usable_met) is not bool or self.minimum_usable_met != (usable >= minimum):
            raise WaterReservoirError("Minimum-usable result must be derived from computed geometry")
        if self.evidence_kind != "DIGITAL_GEOMETRIC_VOLUME_ONLY":
            raise WaterReservoirError("Reservoir volume evaluation cannot be promoted beyond digital geometry")


@dataclass(frozen=True, slots=True)
class WaterReservoirArchitecture:
    reservoir_id: str
    source_authority_revision: str
    gross_target_mL: float
    minimum_usable_mL: float
    authority_status: str
    ports: tuple[ReservoirPort, ...]
    cavity_classification: str
    service_architecture: str
    orientation_case_ids: tuple[str, ...]
    pickup_geometry_status: str
    dead_volume_status: str
    drainability_status: str
    structural_interface_status: str
    leakage_boundary_status: str
    computed_internal_volume_mL: float | None
    computed_dead_volume_mL: float | None
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.reservoir_id != WATER_RESERVOIR_ID:
            raise WaterReservoirError("Water reservoir must retain its stable architecture ID")
        _text(self.source_authority_revision, label="authority revision")
        gross = _real(self.gross_target_mL, label="gross target", positive=True)
        usable = _real(self.minimum_usable_mL, label="minimum usable volume", positive=True)
        if usable > gross:
            raise WaterReservoirError("Minimum usable volume cannot exceed gross target")
        if tuple(port.port_id for port in self.ports) != PORT_IDS:
            raise WaterReservoirError("Water reservoir must expose exactly fill, vent and pickup ports in controlled order")
        if self.cavity_classification != "WET_REMOVABLE":
            raise WaterReservoirError("The selected Iteration-20 service architecture requires the reservoir cavity to be WET_REMOVABLE")
        if self.orientation_case_ids != ORIENTATION_CASE_IDS:
            raise WaterReservoirError("Water reservoir orientation handoff must retain the complete controlled case set")
        if self.computed_internal_volume_mL is not None or self.computed_dead_volume_mL is not None:
            raise WaterReservoirError("Iteration 20 cannot claim closed internal/dead volume before controlled storage geometry exists")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WaterReservoirError("Digital water-reservoir architecture cannot be physical validation evidence")
        for label, value in (
            ("authority status", self.authority_status),
            ("service architecture", self.service_architecture),
            ("pickup geometry status", self.pickup_geometry_status),
            ("dead-volume status", self.dead_volume_status),
            ("drainability status", self.drainability_status),
            ("structural-interface status", self.structural_interface_status),
            ("leakage-boundary status", self.leakage_boundary_status),
            ("evidence status", self.evidence_status),
        ):
            _text(value, label=label)
        object.__setattr__(self, "gross_target_mL", gross)
        object.__setattr__(self, "minimum_usable_mL", usable)

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def validate_current_authority(self, authority: Authority) -> None:
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise WaterReservoirError("Water-reservoir architecture is stale for current authority")
        if self.gross_target_mL != float(authority.get("fluid", "water_reservoir", "gross_mL")):
            raise WaterReservoirError("Water-reservoir gross target no longer matches authority")
        if self.minimum_usable_mL != float(authority.get("fluid", "water_reservoir", "minimum_usable_mL")):
            raise WaterReservoirError("Water-reservoir usable target no longer matches authority")
        if self.authority_status != str(authority.get("fluid", "water_reservoir", "status")):
            raise WaterReservoirError("Water-reservoir status no longer matches authority")
        allowed = tuple(authority.get("manufacturing", "hygiene_classes"))
        if self.cavity_classification not in allowed:
            raise WaterReservoirError("Reservoir cavity classification is not in the frozen hygiene vocabulary")

    def evaluate_generated_volume(self, *, internal_volume_mL: float, dead_volume_mL: float) -> ReservoirVolumeEvaluation:
        internal = _real(internal_volume_mL, label="computed internal volume", positive=True)
        dead = _real(dead_volume_mL, label="computed dead volume", nonnegative=True)
        if dead > internal:
            raise WaterReservoirError("Dead volume cannot exceed computed internal volume")
        usable = internal - dead
        return ReservoirVolumeEvaluation(
            source_architecture_sha256=self.architecture_sha256,
            computed_internal_volume_mL=internal,
            computed_dead_volume_mL=dead,
            computed_usable_volume_mL=usable,
            gross_target_mL=self.gross_target_mL,
            minimum_usable_mL=self.minimum_usable_mL,
            gross_target_met=internal >= self.gross_target_mL,
            minimum_usable_met=usable >= self.minimum_usable_mL,
            evidence_kind="DIGITAL_GEOMETRIC_VOLUME_ONLY",
        )

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "reservoir_id": self.reservoir_id,
            "source_authority_revision": self.source_authority_revision,
            "gross_target_mL": self.gross_target_mL,
            "minimum_usable_mL": self.minimum_usable_mL,
            "authority_status": self.authority_status,
            "ports": [port.manifest() for port in self.ports],
            "cavity_classification": self.cavity_classification,
            "service_architecture": self.service_architecture,
            "orientation_case_ids": list(self.orientation_case_ids),
            "pickup_geometry_status": self.pickup_geometry_status,
            "dead_volume_status": self.dead_volume_status,
            "drainability_status": self.drainability_status,
            "structural_interface_status": self.structural_interface_status,
            "leakage_boundary_status": self.leakage_boundary_status,
            "computed_internal_volume_mL": self.computed_internal_volume_mL,
            "computed_dead_volume_mL": self.computed_dead_volume_mL,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_water_reservoir_architecture(authority: Authority) -> WaterReservoirArchitecture:
    ports = (
        ReservoirPort(PORT_FILL, "user fill interface with closure/seal intent", "FRESH_WATER", "PORT_LOCATION_AND_DIMENSIONS_UNRESOLVED", "SEAL_ARCHITECTURE_REQUIRED_PHYSICAL_LEAKAGE_UNVALIDATED", "WET_USER_SERVICE_ACCESS_REQUIRED"),
        ReservoirPort(PORT_VENT, "controlled air replacement during fill and drawdown", "FRESH_WATER", "VENT_PATH_GEOMETRY_UNRESOLVED", "LIQUID_BARRIER_AND_INGRESS_BEHAVIOR_UNVALIDATED", "VENT_MUST_REMAIN_INSPECTABLE_OR_SERVICEABLE"),
        ReservoirPort(PORT_PICKUP, "fresh-water outlet pickup to metering pump", "FRESH_WATER", "PICKUP_LOCATION_AND_GEOMETRY_UNRESOLVED", "PORT_SEAL_AND_TUBING_INTERFACE_UNRESOLVED", "PICKUP_MUST_SUPPORT_PURGE_AND_SERVICE_ACCESS"),
    )
    architecture = WaterReservoirArchitecture(
        reservoir_id=WATER_RESERVOIR_ID,
        source_authority_revision=str(authority.get("project", "authority_revision")),
        gross_target_mL=float(authority.get("fluid", "water_reservoir", "gross_mL")),
        minimum_usable_mL=float(authority.get("fluid", "water_reservoir", "minimum_usable_mL")),
        authority_status=str(authority.get("fluid", "water_reservoir", "status")),
        ports=ports,
        cavity_classification="WET_REMOVABLE",
        service_architecture="USER_REMOVABLE_REFILLABLE_WATER_MODULE_DEVELOPMENT_ARCHITECTURE",
        orientation_case_ids=ORIENTATION_CASE_IDS,
        pickup_geometry_status="UNRESOLVED_PENDING_3D_RESERVOIR_GEOMETRY_AND_ORIENTATION_BENCH_DATA",
        dead_volume_status="BLOCKED_PENDING_GENERATED_INTERNAL_GEOMETRY_AND_PICKUP_DEFINITION",
        drainability_status="DESIGN_INTENT_FULL_USER_DRAIN_AND_DRY_PATH_PHYSICAL_PERFORMANCE_UNVALIDATED",
        structural_interface_status="FRAME_FRESH_FLUID_RESERVATION_CONSUMER_FINAL_MOUNT_GEOMETRY_UNRESOLVED",
        leakage_boundary_status="SEALED_BOUNDARY_INTENT_ONLY_EXTERNAL_LEAKAGE_REMAINS_PHYSICAL_VALIDATION_GATED",
        computed_internal_volume_mL=None,
        computed_dead_volume_mL=None,
        physical_validation_eligible=False,
        evidence_status="WATER_STORAGE_PORT_SERVICE_AND_VOLUME_CLOSURE_ARCHITECTURE_ONLY_NOT_USABLE_VOLUME_LEAK_OR_ORIENTATION_PHYSICAL_EVIDENCE",
    )
    architecture.validate_current_authority(authority)
    return architecture
