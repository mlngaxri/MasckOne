"""Evidence-bounded cleanser storage, refill, and purge architecture.

Iteration 21 defines fluid identity, service topology, and the compatibility-evidence
boundary. It deliberately does not invent storage capacity, route dead volume, purge
volume, chemical compatibility, or physical hygiene performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from .authority import Authority


class CleanserStorageError(ValueError):
    """Raised when cleanser-storage semantics fail closed."""


CLEANSER_STORAGE_ID = "MASCK_ONE-CLEANSER-RESERVOIR-PRIMARY"
PORT_REFILL = "CLEANSER-PORT-REFILL"
PORT_OUTLET = "CLEANSER-PORT-OUTLET"
PORT_PURGE = "CLEANSER-PORT-PURGE"
PORT_IDS = (PORT_REFILL, PORT_OUTLET, PORT_PURGE)
COMPATIBILITY_EVIDENCE_KINDS = frozenset({
    "SUPPLIER_DOCUMENT",
    "CONTROLLED_COUPON_TEST",
    "CONTROLLED_COMPONENT_TEST",
})

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise CleanserStorageError(f"{label} must be exact built-in nonblank text")
    return value


def _nonnegative(value: object, *, label: str) -> float:
    if type(value) not in (int, float):
        raise CleanserStorageError(f"{label} must be an exact finite nonnegative number")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise CleanserStorageError(f"{label} must be finite and nonnegative")
    return result


def _sha256(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise CleanserStorageError(f"{label} must be a canonical lowercase SHA-256")
    return value


@dataclass(frozen=True, slots=True)
class CleanserPort:
    port_id: str
    role: str
    fluid_identity: str
    geometry_status: str
    contamination_control_status: str
    service_status: str

    def __post_init__(self) -> None:
        if type(self.port_id) is not str or self.port_id not in PORT_IDS:
            raise CleanserStorageError(f"unknown cleanser port {self.port_id!r}")
        if type(self.fluid_identity) is not str or self.fluid_identity != "CLEANSER":
            raise CleanserStorageError("cleanser ports must retain exact CLEANSER fluid identity")
        for label, value in (
            ("port role", self.role),
            ("port geometry status", self.geometry_status),
            ("contamination-control status", self.contamination_control_status),
            ("port service status", self.service_status),
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
    """One immutable evidence artifact submitted for engineering review."""

    evidence_id: str
    revision: str
    cleanser_identity: str
    wetted_material_identity: str
    evidence_kind: str
    artifact_sha256: str
    compatible: bool

    def __post_init__(self) -> None:
        for label, value in (
            ("evidence ID", self.evidence_id),
            ("evidence revision", self.revision),
            ("cleanser identity", self.cleanser_identity),
            ("wetted-material identity", self.wetted_material_identity),
        ):
            _text(value, label=label)
        if type(self.evidence_kind) is not str or self.evidence_kind not in COMPATIBILITY_EVIDENCE_KINDS:
            raise CleanserStorageError("compatibility evidence must use a controlled evidence kind")
        _sha256(self.artifact_sha256, label="compatibility artifact")
        if type(self.compatible) is not bool:
            raise CleanserStorageError("compatibility result must be an exact boolean")

    def manifest(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "revision": self.revision,
            "cleanser_identity": self.cleanser_identity,
            "wetted_material_identity": self.wetted_material_identity,
            "evidence_kind": self.evidence_kind,
            "artifact_sha256": self.artifact_sha256,
            "compatible": self.compatible,
        }


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
        if type(self.reservoir_id) is not str or self.reservoir_id != CLEANSER_STORAGE_ID:
            raise CleanserStorageError("cleanser reservoir must retain its stable architecture ID")
        _text(self.source_authority_revision, label="source authority revision")
        object.__setattr__(
            self,
            "nominal_cycle_dose_mL",
            _nonnegative(self.nominal_cycle_dose_mL, label="nominal cleanser dose"),
        )
        if type(self.ports) is not tuple or tuple(type(port) for port in self.ports) != (
            CleanserPort,
            CleanserPort,
            CleanserPort,
        ):
            raise CleanserStorageError("cleanser ports must be an exact immutable three-port tuple")
        if tuple(port.port_id for port in self.ports) != PORT_IDS:
            raise CleanserStorageError("cleanser reservoir requires refill, outlet, and purge ports in controlled order")
        if type(self.cavity_classification) is not str or self.cavity_classification != "WET_REMOVABLE":
            raise CleanserStorageError("selected cleanser service architecture requires WET_REMOVABLE classification")
        if any(value is not None for value in (
            self.storage_capacity_mL,
            self.dead_volume_mL,
            self.purge_volume_mL,
        )):
            raise CleanserStorageError(
                "Iteration 21 cannot invent cleanser capacity, dead volume, or purge volume before controlled geometry"
            )
        if type(self.compatibility_evidence) is not tuple or any(
            type(item) is not CompatibilityEvidence for item in self.compatibility_evidence
        ):
            raise CleanserStorageError("compatibility evidence must be an immutable tuple of controlled records")
        evidence_ids = tuple(item.evidence_id for item in self.compatibility_evidence)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise CleanserStorageError("compatibility evidence IDs cannot repeat")
        if self.compatibility_evidence:
            if type(self.compatibility_status) is not str or self.compatibility_status != "EVIDENCE_ATTACHED_REQUIRES_ENGINEERING_REVIEW":
                raise CleanserStorageError("attached compatibility evidence cannot auto-promote compatibility")
        elif type(self.compatibility_status) is not str or "BLOCKED" not in self.compatibility_status:
            raise CleanserStorageError("chemical compatibility must remain blocked without evidence")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise CleanserStorageError("digital cleanser storage architecture cannot be physical validation evidence")
        for label, value in (
            ("dose status", self.dose_status),
            ("service architecture", self.service_architecture),
            ("backflow status", self.backflow_architecture_status),
            ("purge status", self.purge_architecture_status),
            ("cleaning status", self.cleaning_path_status),
            ("evidence status", self.evidence_status),
        ):
            _text(value, label=label)

    def validate_current_authority(self, authority: Authority) -> None:
        if type(authority) is not Authority:
            raise CleanserStorageError("authority must be an exact Authority contract")
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise CleanserStorageError("cleanser architecture is stale for current authority")
        if self.nominal_cycle_dose_mL != float(authority.get("fluid", "clean_cycle", "cleanser_mL")):
            raise CleanserStorageError("nominal cleanser dose no longer matches authority")
        if self.dose_status != str(authority.get("fluid", "clean_cycle", "status")):
            raise CleanserStorageError("cleanser dose status no longer matches authority")
        allowed = tuple(authority.get("manufacturing", "hygiene_classes"))
        if self.cavity_classification not in allowed:
            raise CleanserStorageError("cleanser cavity classification is outside the frozen hygiene vocabulary")

    def with_compatibility_evidence(
        self,
        evidence: tuple[CompatibilityEvidence, ...],
    ) -> "CleanserStorageArchitecture":
        if type(evidence) is not tuple or not evidence or any(type(item) is not CompatibilityEvidence for item in evidence):
            raise CleanserStorageError("compatibility evidence update requires controlled immutable records")
        return CleanserStorageArchitecture(
            reservoir_id=self.reservoir_id,
            source_authority_revision=self.source_authority_revision,
            nominal_cycle_dose_mL=self.nominal_cycle_dose_mL,
            dose_status=self.dose_status,
            ports=self.ports,
            cavity_classification=self.cavity_classification,
            service_architecture=self.service_architecture,
            storage_capacity_mL=None,
            dead_volume_mL=None,
            purge_volume_mL=None,
            backflow_architecture_status=self.backflow_architecture_status,
            purge_architecture_status=self.purge_architecture_status,
            cleaning_path_status=self.cleaning_path_status,
            compatibility_evidence=evidence,
            compatibility_status="EVIDENCE_ATTACHED_REQUIRES_ENGINEERING_REVIEW",
            physical_validation_eligible=False,
            evidence_status=self.evidence_status,
        )

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()

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
            "compatibility_evidence": [item.manifest() for item in self.compatibility_evidence],
            "compatibility_status": self.compatibility_status,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_cleanser_storage_architecture(authority: Authority) -> CleanserStorageArchitecture:
    if type(authority) is not Authority:
        raise CleanserStorageError("authority must be an exact Authority contract")
    ports = (
        CleanserPort(
            PORT_REFILL,
            "user cleanser refill interface",
            "CLEANSER",
            "PORT_LOCATION_AND_DIMENSIONS_UNRESOLVED",
            "CLOSURE_AND_WRONG_FLUID_CONTAMINATION_CONTROL_REQUIRED",
            "WET_USER_REFILL_ACCESS_REQUIRED",
        ),
        CleanserPort(
            PORT_OUTLET,
            "cleanser pickup to dedicated metering path",
            "CLEANSER",
            "PICKUP_GEOMETRY_UNRESOLVED",
            "ISOLATION_ELEMENT_REQUIRED_BACKFLOW_PERFORMANCE_UNVALIDATED",
            "OUTLET_MUST_REMAIN_PURGE_SERVICEABLE",
        ),
        CleanserPort(
            PORT_PURGE,
            "controlled purge and cleaning discharge path",
            "CLEANSER",
            "PURGE_PATH_GEOMETRY_UNRESOLVED",
            "PURGE_MUST_NOT_BACKFLOW_INTO_FRESH_WATER_PATH",
            "USER_OR_SERVICE_PURGE_ACCESS_ARCHITECTURE_REQUIRED",
        ),
    )
    architecture = CleanserStorageArchitecture(
        reservoir_id=CLEANSER_STORAGE_ID,
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
