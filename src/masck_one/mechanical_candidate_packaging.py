"""Cross-package audit for the Manual A mechanical realization.

The Manual A realization introduces candidate structural, actuation and retention
geometry. This module checks that candidate against the released non-Manual-A package
envelopes without duplicating or altering the owning lanes' geometry.

The four Manual-A actuator candidates explicitly supersede the four released baseline
actuator placements for this candidate assembly. Baseline and candidate actuator solids
are therefore never treated as simultaneous parts.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority, load_authority
from .mechanical_integration import MechanicalRealization, RealizedPart, build_mechanical_realization
from .model import MasckOneModel, build_model


SCHEMA = "MASCK_ONE_MANUAL_A_CROSS_PACKAGE_AUDIT_V1"
KERNEL_ZERO_VOLUME_MM3 = 1e-9

ACTUATOR_SUPERSESSION = (
    ("ACTUATOR_1", "ACTUATOR-ZONE-A"),
    ("ACTUATOR_2", "ACTUATOR-ZONE-B"),
    ("ACTUATOR_3", "ACTUATOR-ZONE-C"),
    ("ACTUATOR_4", "ACTUATOR-ZONE-D"),
)

BASELINE_EXTERNAL_PACKAGE_IDS = (
    "WATER-RESERVOIR-ENVELOPE",
    "WASTE-CARTRIDGE-ENVELOPE",
    "BATTERY-REFERENCE-ENVELOPE",
)

CANDIDATE_REQUIRED_CLEAR_PREFIXES = (
    "FRAME-PERIMETER-REACTION",
    "ACTUATOR-ZONE-",
    "REACTION-ACTUATOR-ZONE-",
    "RETENTION-HALO-OCCIPITAL-CROWN",
    "RETENTION-YOKE-LEFT",
    "RETENTION-YOKE-RIGHT-FIXED",
    "QUICK-RELEASE-LATCH-MOVING",
    "LOWER-SERVICE-DOOR-ENVELOPE",
)


class MechanicalCandidatePackagingError(ValueError):
    pass


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise MechanicalCandidatePackagingError(f"{label} must be exact nonblank text")
    return value


def _intersection_volume_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise MechanicalCandidatePackagingError("intersection volume must be finite and non-negative")
    return 0.0 if value < KERNEL_ZERO_VOLUME_MM3 else value


@dataclass(frozen=True, slots=True)
class BaselineExternalPackage:
    package_id: str
    source_component_name: str
    solid: cq.Workplane
    geometry_status: str
    evidence_status: str

    def __post_init__(self) -> None:
        for label, value in (
            ("package_id", self.package_id),
            ("source_component_name", self.source_component_name),
            ("geometry_status", self.geometry_status),
            ("evidence_status", self.evidence_status),
        ):
            _text(value, label)
        shape = self.solid.val()
        if not shape.isValid() or float(shape.Volume()) <= 0.0:
            raise MechanicalCandidatePackagingError(f"{self.package_id} must be a valid positive-volume solid")

    def manifest(self) -> dict[str, object]:
        center = self.solid.val().Center()
        bb = self.solid.val().BoundingBox()
        return {
            "package_id": self.package_id,
            "source_component_name": self.source_component_name,
            "geometry_status": self.geometry_status,
            "evidence_status": self.evidence_status,
            "centroid_xyz_mm": [float(center.x), float(center.y), float(center.z)],
            "aabb_spans_mm": [float(bb.xlen), float(bb.ylen), float(bb.zlen)],
        }


@dataclass(frozen=True, slots=True)
class CrossPackageCheck:
    candidate_part_id: str
    baseline_package_id: str
    exact_intersection_mm3: float
    required_clear: bool
    status: str

    def __post_init__(self) -> None:
        _text(self.candidate_part_id, "candidate_part_id")
        _text(self.baseline_package_id, "baseline_package_id")
        if type(self.exact_intersection_mm3) not in (int, float):
            raise MechanicalCandidatePackagingError("exact_intersection_mm3 must be exact numeric")
        value = float(self.exact_intersection_mm3)
        if not math.isfinite(value) or value < 0.0:
            raise MechanicalCandidatePackagingError("exact_intersection_mm3 must be finite and non-negative")
        object.__setattr__(self, "exact_intersection_mm3", 0.0 if value < KERNEL_ZERO_VOLUME_MM3 else value)
        if type(self.required_clear) is not bool:
            raise MechanicalCandidatePackagingError("required_clear must be exact bool")
        _text(self.status, "status")

    @property
    def passes(self) -> bool:
        return not self.required_clear or self.exact_intersection_mm3 == 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "candidate_part_id": self.candidate_part_id,
            "baseline_package_id": self.baseline_package_id,
            "exact_intersection_mm3": self.exact_intersection_mm3,
            "required_clear": self.required_clear,
            "passes": self.passes,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class ActuatorSupersessionRecord:
    baseline_package_id: str
    candidate_part_id: str
    baseline_centroid_xyz_mm: tuple[float, float, float]
    candidate_centroid_xyz_mm: tuple[float, float, float]
    displacement_xyz_mm: tuple[float, float, float]
    displacement_magnitude_mm: float
    status: str

    def manifest(self) -> dict[str, object]:
        return {
            "baseline_package_id": self.baseline_package_id,
            "candidate_part_id": self.candidate_part_id,
            "baseline_centroid_xyz_mm": list(self.baseline_centroid_xyz_mm),
            "candidate_centroid_xyz_mm": list(self.candidate_centroid_xyz_mm),
            "displacement_xyz_mm": list(self.displacement_xyz_mm),
            "displacement_magnitude_mm": self.displacement_magnitude_mm,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class MechanicalCandidatePackageAudit:
    authority_revision: str
    realization_sha256: str
    baseline_external_packages: tuple[BaselineExternalPackage, ...]
    actuator_supersession: tuple[ActuatorSupersessionRecord, ...]
    cross_package_checks: tuple[CrossPackageCheck, ...]
    unresolved_external_classes: tuple[str, ...]
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.authority_revision, "authority_revision")
        _text(self.realization_sha256, "realization_sha256")
        if len(self.realization_sha256) != 64:
            raise MechanicalCandidatePackagingError("realization_sha256 must be a SHA-256 digest")
        if tuple(item.package_id for item in self.baseline_external_packages) != BASELINE_EXTERNAL_PACKAGE_IDS:
            raise MechanicalCandidatePackagingError("baseline external package order changed")
        if len(self.actuator_supersession) != 4:
            raise MechanicalCandidatePackagingError("candidate must explicitly supersede exactly four baseline actuators")
        if type(self.cross_package_checks) is not tuple or not self.cross_package_checks:
            raise MechanicalCandidatePackagingError("cross-package audit requires checks")
        if type(self.unresolved_external_classes) is not tuple or not self.unresolved_external_classes:
            raise MechanicalCandidatePackagingError("unresolved external classes must remain explicit")
        _text(self.evidence_status, "evidence_status")

    @property
    def required_clear_failures(self) -> tuple[CrossPackageCheck, ...]:
        return tuple(check for check in self.cross_package_checks if check.required_clear and not check.passes)

    @property
    def audit_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authority_revision": self.authority_revision,
            "realization_sha256": self.realization_sha256,
            "baseline_external_packages": [item.manifest() for item in self.baseline_external_packages],
            "actuator_supersession": [item.manifest() for item in self.actuator_supersession],
            "cross_package_checks": [item.manifest() for item in self.cross_package_checks],
            "required_clear_failures": [item.manifest() for item in self.required_clear_failures],
            "unresolved_external_classes": list(self.unresolved_external_classes),
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["audit_sha256"] = self.audit_sha256
        return payload


def _baseline_external_packages(model: MasckOneModel) -> tuple[BaselineExternalPackage, ...]:
    components = (
        model.water_reservoir_envelope,
        model.waste_cartridge_envelope,
        model.battery_reference_envelope,
    )
    return tuple(
        BaselineExternalPackage(
            package_id=component.name.upper().replace("_", "-"),
            source_component_name=component.name,
            solid=component.solid,
            geometry_status=component.status,
            evidence_status=component.notes or component.status,
        )
        for component in components
    )


def _candidate_required_clear(part: RealizedPart) -> bool:
    return any(part.part_id == prefix or part.part_id.startswith(prefix) for prefix in CANDIDATE_REQUIRED_CLEAR_PREFIXES)


def _cross_package_checks(
    realization: MechanicalRealization,
    external: tuple[BaselineExternalPackage, ...],
) -> tuple[CrossPackageCheck, ...]:
    checks: list[CrossPackageCheck] = []
    # LIVE-MAIN-RIGID-SHELL and SERVICE-STATE-SHELL are boundary states, not internal
    # packages. They are deliberately excluded from internal required-clear checks.
    for part in realization.realized_parts:
        if part.part_id in {"LIVE-MAIN-RIGID-SHELL", "SERVICE-STATE-SHELL"}:
            continue
        required_clear = _candidate_required_clear(part)
        for baseline in external:
            volume = _intersection_volume_mm3(part.solid, baseline.solid)
            checks.append(
                CrossPackageCheck(
                    candidate_part_id=part.part_id,
                    baseline_package_id=baseline.package_id,
                    exact_intersection_mm3=volume,
                    required_clear=required_clear,
                    status=(
                        "REQUIRED_CLEAR_CONFLICT_REQUIRES_REPACKAGING"
                        if required_clear and volume > 0.0
                        else "REQUIRED_CLEAR_EXACT_BREP_PASS_DIGITAL_ONLY"
                        if required_clear
                        else "RECORDED_INTERFACE_NOT_REQUIRED_CLEAR"
                    ),
                )
            )
    return tuple(checks)


def _actuator_supersession(
    model: MasckOneModel,
    realization: MechanicalRealization,
) -> tuple[ActuatorSupersessionRecord, ...]:
    candidate_parts = {part.part_id: part for part in realization.realized_parts}
    records: list[ActuatorSupersessionRecord] = []
    for index, (baseline_id, candidate_id) in enumerate(ACTUATOR_SUPERSESSION):
        baseline_shape = model.actuator_envelopes[index].solid.val()
        baseline_center = baseline_shape.Center()
        baseline_xyz = (float(baseline_center.x), float(baseline_center.y), float(baseline_center.z))
        candidate = candidate_parts.get(candidate_id)
        if candidate is None:
            raise MechanicalCandidatePackagingError(f"missing candidate actuator {candidate_id}")
        candidate_xyz = candidate.centroid_xyz_mm
        delta = tuple(candidate_xyz[i] - baseline_xyz[i] for i in range(3))
        magnitude = math.sqrt(sum(value * value for value in delta))
        records.append(
            ActuatorSupersessionRecord(
                baseline_package_id=baseline_id,
                candidate_part_id=candidate_id,
                baseline_centroid_xyz_mm=baseline_xyz,
                candidate_centroid_xyz_mm=candidate_xyz,
                displacement_xyz_mm=(delta[0], delta[1], delta[2]),
                displacement_magnitude_mm=magnitude,
                status=(
                    "MANUAL_A_REPACKAGING_CANDIDATE_TO_CLEAR_PROTECTED_REGIONS_"
                    "NOT_AUTHORITY_CHANGE_OR_PHYSICAL_VALIDATION"
                ),
            )
        )
    return tuple(records)


def build_mechanical_candidate_package_audit(
    authority: Authority | None = None,
) -> MechanicalCandidatePackageAudit:
    authority = authority or load_authority()
    model = build_model(authority)
    realization = build_mechanical_realization(authority)
    external = _baseline_external_packages(model)
    return MechanicalCandidatePackageAudit(
        authority_revision=str(authority.get("project", "authority_revision")),
        realization_sha256=realization.realization_sha256,
        baseline_external_packages=external,
        actuator_supersession=_actuator_supersession(model, realization),
        cross_package_checks=_cross_package_checks(realization, external),
        unresolved_external_classes=realization.remaining_blockers,
        evidence_status=(
            "MANUAL_A_CANDIDATE_VS_RELEASED_WATER_CARTRIDGE_BATTERY_EXACT_BREP_AUDIT_"
            "OTHER_LANE_UNRELEASED_GEOMETRY_REMAINS_BLOCKED_NOT_PHYSICAL_VALIDATION"
        ),
    )
