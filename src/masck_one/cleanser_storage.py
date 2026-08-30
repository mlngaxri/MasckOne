from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math

from .authority import Authority


class CleanserStorageError(ValueError):
    """Raised when cleanser storage, compatibility, purge or contamination semantics are invalid."""


CLEANser_ID = "MASCK_ONE-CLEANSER-RESERVOIR-PRIMARY"
PORT_REFILL = "CLEANSER-PORT-REFILL"
PORT_OUTLET = "CLEANSER-PORT-OUTLET"
PORT_PURGE = "CLEANSER-PORT-PURGE"
PORT_IDS = (PORT_REFILL, PORT_OUTLET, PORT_PURGE)


def _text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CleanserStorageError(f"{label} must be an exact nonblank string")
    return value


def _positive(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CleanserStorageError(f"{label} must be a positive finite real number")
    out = float(value)
    if not math.isfinite(out) or out <= 0.0:
        raise CleanserStorageError(f"{label} must be a positive finite real number")
    return out


@dataclass(frozen=True, slots=True)
class CleanserPort:
    port_id: str
    role: str
    fluid_identity: str
    geometry_status: str
    contamination_control_status: str
    service_status: str

    def __post_init__(self) -> None:
        if self.port_id not in PORT_IDS:
            raise CleanserStorageError(f"Unknown cleanser port {self.port_id!r}")
        if self.fluid_identity != "CLEANSER":
            raise CleanserStorageError("Cleanser ports must retain CLEANSER fluid identity")
        for label, value in (
            ("port role", self.role),
            ("geometry status", self.geometry_status),
            ("contamination-control status", self.contamination_control_status),
            ("service status", self.service_status),
        ):
            _text(value, label=label)

    def manifest(self) -> dict[str, object]:
        return {
            "port_id": self.port_id,
            "role": self.role,
            "fluid_identity": self.fluid_identity,
            "geometry_status": self.geometry_status,
            "contamination_control_status": self.contamination_control_status,
            "service_status": self.service_status,
        }


@dataclass(frozen=True, slots=True)
class CompatibilityEvidence:
    evidence_id: str
    cleanser_identity: str
    wetted_material_identity: str
    evidence_kind: str
    source_uri: str
    compatible: bool

    def __post_init__(self) -> None:
        for label, value in (
            ("evidence ID", self.evidence_id),
            ("cleanser identity", self.cleanser_identity),
            ("wetted material identity", self.wetted_material_identity),
            ("source URI", self.source_uri),
        ):
            _text(value, label=label)
        if self.evidence_kind not in {"SUPPLIER_DOCUMENT", "CONTROLLED_COUPON_TEST", "CONTROLLED_COMPONENT_TEST"}:
            raise CleanserStorageError("Compatibility evidence must have a controlled evidence kind")
        if type(self.compatible) is not bool:
            raise CleanserStorageError("Compatibility result must be an explicit boolean")


@dataclass(frozen=True, slots=True)
class CleanserStorageArchitecture:
    reservoir_id: str
    source_authority_revision: str
    nominal_cycle_dose_mL: float
    dose_status: str
    ports: tuple[CleanserPort, ...]
    cavity_classification: str
    service_architecture: str
    storage_capacity_mL: float | None
    dead_volume_mL: float | None
    purge_volume_mL: float | None
    backflow_architecture_status: str
    purge_architecture_status: str
    cleaning_path_status: str
    compatibility_evidence: tuple[CompatibilityEvidence, ...]
    compatibility_status: str
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.reservoir_id != CLEANser_ID:
            raise CleanserStorageError("Cleanser reservoir must retain its stable ID")
        _text(self.source_authority_revision, label="authority revision")
        dose = _positive(self.nominal_cycle_dose_mL, label="nominal cleanser dose")
        if tuple(port.port_id for port in self.ports) != PORT_IDS:
            raise CleanserStorageError("Cleanser reservoir must expose refill, outlet and purge ports in controlled order")
        if self.cavity_classification != "WET_REMOVABLE":
            raise CleanserStorageError("Selected cleanser service architecture requires WET_REMOVABLE classification")
        if any(value is not None for value in (self.storage_capacity_mL, self.dead_volume_mL, self.purge_volume_mL)):
            raise CleanserStorageError("Iteration 21 cannot invent cleanser capacity, dead volume or purge volume before controlled geometry")
        if self.compatibility_evidence and self.compatibility_status != "EVIDENCE_ATTACHED_REQUIRES_ENGINEERING_REVIEW":
            raise CleanserStorageError("Attached compatibility evidence cannot be silently promoted to a final compatibility claim")
        if not self.compatibility_evidence and "BLOCKED" not in self.compatibility_status:
            raise CleanserStorageError("Chemical compatibility must remain blocked when no evidence is attached")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise CleanserStorageError("Digital cleanser storage architecture cannot be physical validation evidence")
        for label, value in (
            ("dose status", self.dose_status),
            ("service architecture", self.service_architecture),
            ("backflow status", self.backflow_architecture_status),
            ("purge status", self.purge_architecture_status),
            ("cleaning status", self.cleaning_path_status),
            ("compatibility status", self.compatibility_status),
            ("evidence status", self.evidence_status),
        ):
            _text(value, label=label)
        object.__setattr__(self, "nominal_cycle_dose_mL", dose)

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def validate_current_authority(self, authority: Authority) -> None:
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise CleanserStorageError("Cleanser architecture is stale for current authority")
        if self.nominal_cycle_dose_mL != float(authority.get("fluid", "clean_cycle", "cleanser_mL")):
            raise CleanserStorageError("Nominal cleanser dose no longer matches authority")
        if self.dose_status != str(authority.get("fluid", "clean_cycle", "status")):
            raise CleanserStorageError("Cleanser dose status no longer matches authority")
        if self.cavity_classification not in tuple(authority.get("manufacturing", "hygiene_classes")):
            raise CleanserStorageError("Cleanser cavity classification is outside the frozen hygiene vocabulary")

    def with_compatibility_evidence(self, evidence: tuple[CompatibilityEvidence, ...]) -> "CleanserStorageArchitecture":
        if not evidence:
            raise CleanserStorageError("Compatibility evidence update requires at least one controlled record")
        return CleanserStorageArchitecture(
            reservoir_id=self.reservoir_id,
            source_authority_revision=self.source_authority_revision,
            nominal_cycle_dose_mL=self.nominal_cycle_dose_mL,
            dose_status=self.dose_status,
            ports=self.ports,
            cavity_classification=self.cavity_classification,
            service_architecture=self.service_architecture,
            storage_capacity_mL=self.storage_capacity_mL,
            dead_volume_mL=self.dead_volume_mL,
            purge_volume_mL=self.purge_volume_mL,
            backflow_architecture_status=self.backflow_architecture_status,
            purge_architecture_status=self.purge_architecture_status,
            cleaning_path_status=self.cleaning_path_status,
            compatibility_evidence=evidence,
            compatibility_status="EVIDENCE_ATTACHED_REQUIRES_ENGINEERING_REVIEW",
            physical_validation_eligible=False,
            evidence_status=self.evidence_status,
        )

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "reservoir_id": self.reservoir_id,
            "source_authority_revision": self.source_authority_revision,
            "nominal_cycle_dose_mL": self.nominal_cycle_dose_mL,
            "dose_status": self.dose_status,
            "ports": [port.manifest() for port in self.ports],
            "cavity_classification": self.cavity_classification,
            "service_architecture": self.service_architecture,
            "storage_capacity_mL": self.storage_capacity_mL,
            "dead_volume_mL": self.dead_volume_mL,
            "purge_volume_mL": self.purge_volume_mL,
            "backflow_architecture_status": self.backflow_architecture_status,
            "purge_architecture_status": self.purge_architecture_status,
            "cleaning_path_status": self.cleaning_path_status,
            "compatibility_evidence": [e.__dict__ if hasattr(e, "__dict__") else {"evidence_id": e.evidence_id, "cleanser_identity": e.cleanser_identity, "wetted_material_identity": e.wetted_material_identity, "evidence_kind": e.evidence_kind, "source_uri": e.source_uri, "compatible": e.compatible} for e in self.compatibility_evidence],
            "compatibility_status": self.compatibility_status,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_cleanser_storage_architecture(authority: Authority) -> CleanserStorageArchitecture:
    ports = (
        CleanserPort(PORT_REFILL, "user cleanser refill interface", "CLEANSER", "PORT_LOCATION_AND_DIMENSIONS_UNRESOLVED", "CLOSURE_AND_WRONG_FLUID_CONTAMINATION_CONTROL_REQUIRED", "WET_USER_REFILL_ACCESS_REQUIRED"),
        CleanserPort(PORT_OUTLET, "cleanser pickup/outlet to dedicated metering path", "CLEANSER", "PICKUP_GEOMETRY_UNRESOLVED", "CHECK_OR_ISOLATION_ELEMENT_REQUIRED_BACKFLOW_PERFORMANCE_UNVALIDATED", "OUTLET_MUST_REMAIN_PURGE_SERVICEABLE"),
        CleanserPort(PORT_PURGE, "controlled purge and cleaning discharge path", "CLEANSER", "PURGE_PATH_GEOMETRY_UNRESOLVED", "PURGE_MUST_NOT_BACKFLOW_INTO_FRESH_WATER_PATH", "USER_OR_SERVICE_PURGE_ACCESS_ARCHITECTURE_REQUIRED"),
    )
    architecture = CleanserStorageArchitecture(
        reservoir_id=CLEANser_ID,
        source_authority_revision=str(authority.get("project", "authority_revision")),
        nominal_cycle_dose_mL=float(authority.get("fluid", "clean_cycle", "cleanser_mL")),
        dose_status=str(authority.get("fluid", "clean_cycle", "status")),
        ports=ports,
        cavity_classification="WET_REMOVABLE",
        service_architecture="USER_REMOVABLE_REFILLABLE_DEDICATED_CLEANSER_MODULE",
        storage_capacity_mL=None,
        dead_volume_mL=None,
        purge_volume_mL=None,
        backflow_architecture_status="DEDICATED_FLUID_IDENTITY_AND_ISOLATION_INTENT_PHYSICAL_BACKFLOW_PERFORMANCE_UNVALIDATED",
        purge_architecture_status="PURGE_ROUTE_REQUIRED_VOLUME_AND_PRESSURE_UNRESOLVED_PENDING_ROUTING_AND_PUMP_ARCHITECTURE",
        cleaning_path_status="REMOVABLE_MODULE_AND_PURGE_ACCESS_INTENT_HYGIENE_PERFORMANCE_UNVALIDATED",
        compatibility_evidence=(),
        compatibility_status="BLOCKED_PENDING_SELECTED_CLEANSER_CHEMISTRY_WETTED_MATERIALS_AND_CONTROLLED_EVIDENCE",
        physical_validation_eligible=False,
        evidence_status="CLEANSER_STORAGE_REFILL_PURGE_BACKFLOW_AND_COMPATIBILITY_CONTRACT_ONLY_NOT_DOSING_CHEMISTRY_LEAK_OR_HYGIENE_PHYSICAL_EVIDENCE",
    )
    architecture.validate_current_authority(authority)
    return architecture
