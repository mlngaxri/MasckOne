"""Exact-shape interference audit for the currently released whole-product package.

The package registry in :mod:`whole_product_package` is intentionally broad-phase.
This module refines every broad-phase candidate with OpenCascade B-rep intersection,
adds conservative authority-derived rigid protected-region screens, and evaluates
sampled service sweeps against the actual released package shapes.

A reported overlap is evidence of a digital geometry conflict or an interface that
still requires classification. A reported clearance is only digital CAD evidence and
must not be promoted to fit, safety, seal, comfort, durability or physical validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority
from .model import Component, MasckOneModel
from .whole_product_package import (
    DIGITAL_EVIDENCE,
    KNOWN_PACKAGE_IDS,
    Aabb,
    WholeProductPackage,
    WholeProductPackageError,
    build_whole_product_package,
)


SCHEMA = "MASCK_ONE_WHOLE_PRODUCT_INTERFERENCE_V1"
KERNEL_ZERO_VOLUME_MM3 = 1e-9
PROTECTED_SCREEN_Z_MIN_MM = -20.0
PROTECTED_SCREEN_Z_MAX_MM = 50.0


class WholeProductInterferenceError(ValueError):
    """Raised when exact-shape package evidence is malformed or inconsistent."""


def _exact_nonblank(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise WholeProductInterferenceError(f"{label} must be exact nonblank text")
    return value


def _finite_nonnegative(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise WholeProductInterferenceError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise WholeProductInterferenceError(f"{label} must be finite and non-negative")
    return 0.0 if result == 0.0 else result


def exact_intersection_volume_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    """Return exact B-rep common volume with a numerical-kernel zero floor.

    ``KERNEL_ZERO_VOLUME_MM3`` is numerical bookkeeping only. It is not a product
    clearance, tolerance, acceptance criterion or manufacturing allowance.
    """
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise WholeProductInterferenceError("B-rep intersection volume must be finite and non-negative")
    return 0.0 if value < KERNEL_ZERO_VOLUME_MM3 else value


@dataclass(frozen=True, slots=True)
class ExactInterferenceRecord:
    first_id: str
    second_id: str
    broad_phase_overlap_mm3: float
    exact_intersection_mm3: float
    interface_semantics: str
    status: str

    def __post_init__(self) -> None:
        _exact_nonblank(self.first_id, "first_id")
        _exact_nonblank(self.second_id, "second_id")
        object.__setattr__(
            self,
            "broad_phase_overlap_mm3",
            _finite_nonnegative(self.broad_phase_overlap_mm3, "broad_phase_overlap_mm3"),
        )
        object.__setattr__(
            self,
            "exact_intersection_mm3",
            _finite_nonnegative(self.exact_intersection_mm3, "exact_intersection_mm3"),
        )
        _exact_nonblank(self.interface_semantics, "interface_semantics")
        _exact_nonblank(self.status, "status")
        if self.broad_phase_overlap_mm3 == 0.0 and self.exact_intersection_mm3 > 0.0:
            raise WholeProductInterferenceError("exact intersection cannot exist outside disjoint AABBs")

    @property
    def exact_overlap(self) -> bool:
        return self.exact_intersection_mm3 > 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "first_id": self.first_id,
            "second_id": self.second_id,
            "broad_phase_overlap_mm3": self.broad_phase_overlap_mm3,
            "exact_intersection_mm3": self.exact_intersection_mm3,
            "interface_semantics": self.interface_semantics,
            "status": self.status,
            "exact_overlap": self.exact_overlap,
        }


@dataclass(frozen=True, slots=True)
class ProtectedScreen:
    screen_id: str
    source_region: str
    solid: cq.Workplane
    evidence_status: str

    def __post_init__(self) -> None:
        _exact_nonblank(self.screen_id, "screen_id")
        _exact_nonblank(self.source_region, "source_region")
        _exact_nonblank(self.evidence_status, "evidence_status")
        shape = self.solid.val()
        if not shape.isValid() or float(shape.Volume()) <= 0.0:
            raise WholeProductInterferenceError(f"{self.screen_id} must be a valid positive-volume screen")

    def manifest(self) -> dict[str, object]:
        bb = self.solid.val().BoundingBox()
        return {
            "screen_id": self.screen_id,
            "source_region": self.source_region,
            "z_screen_mm": [PROTECTED_SCREEN_Z_MIN_MM, PROTECTED_SCREEN_Z_MAX_MM],
            "aabb_mm": {
                "min": [float(bb.xmin), float(bb.ymin), float(bb.zmin)],
                "max": [float(bb.xmax), float(bb.ymax), float(bb.zmax)],
            },
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class ProtectedIntrusionRecord:
    package_id: str
    screen_id: str
    intersection_mm3: float
    status: str

    def __post_init__(self) -> None:
        _exact_nonblank(self.package_id, "package_id")
        _exact_nonblank(self.screen_id, "screen_id")
        object.__setattr__(self, "intersection_mm3", _finite_nonnegative(self.intersection_mm3, "intersection_mm3"))
        _exact_nonblank(self.status, "status")

    @property
    def intrudes(self) -> bool:
        return self.intersection_mm3 > 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "package_id": self.package_id,
            "screen_id": self.screen_id,
            "intersection_mm3": self.intersection_mm3,
            "status": self.status,
            "intrudes": self.intrudes,
        }


@dataclass(frozen=True, slots=True)
class ServiceSweepShapeRecord:
    motion_id: str
    moving_package_id: str
    obstacle_package_id: str
    sample_intersection_mm3: tuple[float, ...]
    status: str

    def __post_init__(self) -> None:
        _exact_nonblank(self.motion_id, "motion_id")
        _exact_nonblank(self.moving_package_id, "moving_package_id")
        _exact_nonblank(self.obstacle_package_id, "obstacle_package_id")
        if type(self.sample_intersection_mm3) is not tuple or not self.sample_intersection_mm3:
            raise WholeProductInterferenceError("service sweep shape record needs exact sampled volumes")
        object.__setattr__(
            self,
            "sample_intersection_mm3",
            tuple(_finite_nonnegative(value, "sample_intersection_mm3") for value in self.sample_intersection_mm3),
        )
        _exact_nonblank(self.status, "status")

    @property
    def has_interference(self) -> bool:
        return any(value > 0.0 for value in self.sample_intersection_mm3)

    def manifest(self) -> dict[str, object]:
        return {
            "motion_id": self.motion_id,
            "moving_package_id": self.moving_package_id,
            "obstacle_package_id": self.obstacle_package_id,
            "sample_intersection_mm3": list(self.sample_intersection_mm3),
            "has_interference": self.has_interference,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class WholeProductInterferenceAudit:
    authority_revision: str
    package_sha256: str
    package_pairs: tuple[ExactInterferenceRecord, ...]
    protected_screens: tuple[ProtectedScreen, ...]
    protected_intrusions: tuple[ProtectedIntrusionRecord, ...]
    service_sweep_records: tuple[ServiceSweepShapeRecord, ...]
    evidence_status: str

    def __post_init__(self) -> None:
        _exact_nonblank(self.authority_revision, "authority_revision")
        _exact_nonblank(self.package_sha256, "package_sha256")
        if len(self.package_sha256) != 64:
            raise WholeProductInterferenceError("package_sha256 must be a canonical SHA-256 digest")
        if type(self.package_pairs) is not tuple or not self.package_pairs:
            raise WholeProductInterferenceError("package_pairs must be a non-empty exact tuple")
        if type(self.protected_screens) is not tuple or not self.protected_screens:
            raise WholeProductInterferenceError("protected_screens must be a non-empty exact tuple")
        if type(self.protected_intrusions) is not tuple or not self.protected_intrusions:
            raise WholeProductInterferenceError("protected_intrusions must be a non-empty exact tuple")
        if type(self.service_sweep_records) is not tuple or not self.service_sweep_records:
            raise WholeProductInterferenceError("service_sweep_records must be a non-empty exact tuple")
        _exact_nonblank(self.evidence_status, "evidence_status")

    @property
    def exact_package_overlap_pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple((record.first_id, record.second_id) for record in self.package_pairs if record.exact_overlap)

    @property
    def protected_intrusion_pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple((record.package_id, record.screen_id) for record in self.protected_intrusions if record.intrudes)

    @property
    def service_interference_pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (record.motion_id, record.obstacle_package_id)
            for record in self.service_sweep_records
            if record.has_interference
        )

    @property
    def audit_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authority_revision": self.authority_revision,
            "package_sha256": self.package_sha256,
            "package_pairs": [record.manifest() for record in self.package_pairs],
            "protected_screens": [screen.manifest() for screen in self.protected_screens],
            "protected_intrusions": [record.manifest() for record in self.protected_intrusions],
            "service_sweep_records": [record.manifest() for record in self.service_sweep_records],
            "summary": {
                "exact_package_overlap_pairs": [list(pair) for pair in self.exact_package_overlap_pairs],
                "protected_intrusion_pairs": [list(pair) for pair in self.protected_intrusion_pairs],
                "service_interference_pairs": [list(pair) for pair in self.service_interference_pairs],
            },
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["audit_sha256"] = self.audit_sha256
        return payload


def _component_map(model: MasckOneModel) -> dict[str, Component]:
    if type(model) is not MasckOneModel:
        raise TypeError("model must be exact MasckOneModel")
    return {
        "RIGID_SHELL": model.shell,
        "NASAL_INTERFACE_REFERENCE": model.nasal_interface,
        "ACTUATOR_1": model.actuator_envelopes[0],
        "ACTUATOR_2": model.actuator_envelopes[1],
        "ACTUATOR_3": model.actuator_envelopes[2],
        "ACTUATOR_4": model.actuator_envelopes[3],
        "WATER_RESERVOIR_ENVELOPE": model.water_reservoir_envelope,
        "WASTE_CARTRIDGE_ENVELOPE": model.waste_cartridge_envelope,
        "BATTERY_REFERENCE_ENVELOPE": model.battery_reference_envelope,
    }


def _interface_semantics(first_id: str, second_id: str) -> str:
    pair = frozenset((first_id, second_id))
    if pair == frozenset(("RIGID_SHELL", "NASAL_INTERFACE_REFERENCE")):
        return "INTENDED_SHELL_TO_SOFT_INTERFACE_RELATIONSHIP_REQUIRES_FINAL_INTERFACE_CLASSIFICATION"
    if "RIGID_SHELL" in pair:
        return "SHELL_BOUNDARY_PENETRATION_OR_CONTACT_REQUIRES_MECHANICAL_INTERFACE_REVIEW"
    return "INTERNAL_PACKAGE_PAIR_SHOULD_NOT_OCCUPY_COMMON_SOLID_VOLUME_UNLESS_EXPLICITLY_CLASSIFIED"


def _record_status(first_id: str, second_id: str, exact_volume: float) -> str:
    if exact_volume == 0.0:
        return "EXACT_BREP_CLEAR_DIGITAL_ONLY"
    if frozenset((first_id, second_id)) == frozenset(("RIGID_SHELL", "NASAL_INTERFACE_REFERENCE")):
        return "EXACT_OVERLAP_REQUIRES_INTENDED_INTERFACE_CLASSIFICATION"
    return "EXACT_INTERFERENCE_REQUIRES_RESOLUTION_OR_EXPLICIT_INTERFACE_CLASSIFICATION"


def _package_pair_records(
    package: WholeProductPackage,
    components: dict[str, Component],
) -> tuple[ExactInterferenceRecord, ...]:
    broad = {
        frozenset((record.first_id, record.second_id)): record
        for record in package.collision_records
    }
    records: list[ExactInterferenceRecord] = []
    for first_index, first_id in enumerate(KNOWN_PACKAGE_IDS):
        for second_id in KNOWN_PACKAGE_IDS[first_index + 1 :]:
            broad_record = broad[frozenset((first_id, second_id))]
            broad_overlap = broad_record.aabb_overlap_volume_mm3
            exact = 0.0
            if broad_overlap > 0.0:
                exact = exact_intersection_volume_mm3(
                    components[first_id].solid,
                    components[second_id].solid,
                )
            records.append(
                ExactInterferenceRecord(
                    first_id=first_id,
                    second_id=second_id,
                    broad_phase_overlap_mm3=broad_overlap,
                    exact_intersection_mm3=exact,
                    interface_semantics=_interface_semantics(first_id, second_id),
                    status=_record_status(first_id, second_id, exact),
                )
            )
    return tuple(records)


def _ellipse_screen(width: float, height: float, center_xy: tuple[float, float], clearance: float) -> cq.Workplane:
    depth = PROTECTED_SCREEN_Z_MAX_MM - PROTECTED_SCREEN_Z_MIN_MM
    return (
        cq.Workplane("XY")
        .workplane(offset=PROTECTED_SCREEN_Z_MIN_MM)
        .center(*center_xy)
        .ellipse((width + 2.0 * clearance) / 2.0, (height + 2.0 * clearance) / 2.0)
        .extrude(depth)
    )


def _circle_screen(diameter: float, center_xy: tuple[float, float], clearance: float) -> cq.Workplane:
    depth = PROTECTED_SCREEN_Z_MAX_MM - PROTECTED_SCREEN_Z_MIN_MM
    return (
        cq.Workplane("XY")
        .workplane(offset=PROTECTED_SCREEN_Z_MIN_MM)
        .center(*center_xy)
        .circle((diameter + 2.0 * clearance) / 2.0)
        .extrude(depth)
    )


def _protected_screens(authority: Authority) -> tuple[ProtectedScreen, ...]:
    eye_w, eye_h = authority.pair("geometry", "eye", "visual_aperture_wh_mm")
    eye_clear = authority.number("geometry", "eye", "rigid_dynamic_keepout_clearance_mm")
    eye_centers = authority.get("geometry", "eye", "centers_mm")
    mouth_w, mouth_h = authority.pair("geometry", "mouth", "visual_aperture_wh_mm")
    mouth_clear = authority.number("geometry", "mouth", "rigid_dynamic_keepout_clearance_mm")
    mouth_center = authority.get("geometry", "mouth", "center_mm")
    nostril_clear = authority.number("geometry", "nostrils", "rigid_dynamic_keepout_clearance_mm")
    nostril_centers = authority.get("geometry", "nostrils", "centers_mm")
    minimum_area = authority.number("geometry", "nostrils", "minimum_deformed_area_each_mm2")
    minimum_local = authority.number("geometry", "nostrils", "minimum_local_opening_dimension_mm")
    nostril_diameter = max(minimum_local, math.sqrt(4.0 * minimum_area * 1.02 / math.pi))
    status = (
        "CONSERVATIVE_AUTHORITY_XY_RIGID_KEEPOUT_EXTRUSION_FOR_DIGITAL_SCREEN_ONLY_"
        "NOT_REGISTERED_3D_ANATOMY_OR_PHYSICAL_FIT_EVIDENCE"
    )
    return (
        ProtectedScreen("PROTECTED-SCREEN-EYE-LEFT", "EYE_LEFT", _ellipse_screen(eye_w, eye_h, tuple(eye_centers["left"]), eye_clear), status),
        ProtectedScreen("PROTECTED-SCREEN-EYE-RIGHT", "EYE_RIGHT", _ellipse_screen(eye_w, eye_h, tuple(eye_centers["right"]), eye_clear), status),
        ProtectedScreen("PROTECTED-SCREEN-MOUTH", "MOUTH", _ellipse_screen(mouth_w, mouth_h, tuple(mouth_center), mouth_clear), status),
        ProtectedScreen("PROTECTED-SCREEN-NOSTRIL-LEFT", "NOSTRIL_LEFT", _circle_screen(nostril_diameter, tuple(nostril_centers["left"]), nostril_clear), status),
        ProtectedScreen("PROTECTED-SCREEN-NOSTRIL-RIGHT", "NOSTRIL_RIGHT", _circle_screen(nostril_diameter, tuple(nostril_centers["right"]), nostril_clear), status),
    )


def _protected_intrusions(
    components: dict[str, Component],
    screens: tuple[ProtectedScreen, ...],
) -> tuple[ProtectedIntrusionRecord, ...]:
    records: list[ProtectedIntrusionRecord] = []
    # The shell intentionally bounds the facial openings and the nasal reference is a
    # soft-interface development reference. Screen rigid/internal package candidates.
    rigid_package_ids = (
        "ACTUATOR_1",
        "ACTUATOR_2",
        "ACTUATOR_3",
        "ACTUATOR_4",
        "WATER_RESERVOIR_ENVELOPE",
        "WASTE_CARTRIDGE_ENVELOPE",
        "BATTERY_REFERENCE_ENVELOPE",
    )
    for package_id in rigid_package_ids:
        for screen in screens:
            volume = exact_intersection_volume_mm3(components[package_id].solid, screen.solid)
            records.append(
                ProtectedIntrusionRecord(
                    package_id=package_id,
                    screen_id=screen.screen_id,
                    intersection_mm3=volume,
                    status=(
                        "RIGID_PACKAGE_INTRUDES_CONSERVATIVE_PROTECTED_SCREEN_REQUIRES_REPACKAGING"
                        if volume > 0.0
                        else "CLEAR_OF_CONSERVATIVE_PROTECTED_SCREEN_DIGITAL_ONLY"
                    ),
                )
            )
    return tuple(records)


def _translated(solid: cq.Workplane, offset_xyz_mm: tuple[float, float, float]) -> cq.Workplane:
    return solid.translate(offset_xyz_mm)


def _service_sweep_records(
    package: WholeProductPackage,
    components: dict[str, Component],
) -> tuple[ServiceSweepShapeRecord, ...]:
    records: list[ServiceSweepShapeRecord] = []
    for motion in package.service_motions:
        moving = components[motion.package_id]
        offsets = motion.sample_offsets_mm()
        for obstacle_id in KNOWN_PACKAGE_IDS:
            if obstacle_id == motion.package_id:
                continue
            obstacle = components[obstacle_id]
            volumes = tuple(
                exact_intersection_volume_mm3(_translated(moving.solid, offset), obstacle.solid)
                for offset in offsets
            )
            records.append(
                ServiceSweepShapeRecord(
                    motion_id=motion.motion_id,
                    moving_package_id=motion.package_id,
                    obstacle_package_id=obstacle_id,
                    sample_intersection_mm3=volumes,
                    status=(
                        "SAMPLED_SERVICE_SWEEP_INTERFERENCE_REQUIRES_REAL_OPENING_OR_REPACKAGING"
                        if any(value > 0.0 for value in volumes)
                        else "SAMPLED_SERVICE_SWEEP_CLEAR_DIGITAL_ONLY_CONTINUOUS_SWEEP_NOT_PROVEN"
                    ),
                )
            )
    return tuple(records)


def build_whole_product_interference_audit(model: MasckOneModel) -> WholeProductInterferenceAudit:
    if type(model) is not MasckOneModel:
        raise TypeError("model must be exact MasckOneModel")
    package = build_whole_product_package(model)
    components = _component_map(model)
    if tuple(components) != KNOWN_PACKAGE_IDS:
        raise WholeProductInterferenceError("component map no longer matches controlled package registry order")
    screens = _protected_screens(model.authority)
    return WholeProductInterferenceAudit(
        authority_revision=str(model.authority.get("project", "authority_revision")),
        package_sha256=package.package_sha256,
        package_pairs=_package_pair_records(package, components),
        protected_screens=screens,
        protected_intrusions=_protected_intrusions(components, screens),
        service_sweep_records=_service_sweep_records(package, components),
        evidence_status=(
            "EXACT_BREP_PACKAGE_AND_SAMPLED_SERVICE_INTERFERENCE_AUDIT_"
            "WITH_CONSERVATIVE_XY_PROTECTED_SCREENS_NOT_PHYSICAL_VALIDATION"
        ),
    )
