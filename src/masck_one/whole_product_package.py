"""Whole-product mechanical packaging and evidence-bounded integration.

This layer does not replace subsystem ownership. It binds the geometry that is
actually present on the selected Masck One model into one deterministic package
registry, performs conservative collision bookkeeping, and refuses to promote
mass/CG or service closure while required geometry or mass provenance is missing.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from .authority import Authority
from .model import Component, MasckOneModel


CANONICAL_FRAME_ID = "MASCK_ONE_CANONICAL_XYZ"
DIGITAL_EVIDENCE = "DIGITAL_GEOMETRY_ONLY_NOT_PHYSICAL_VALIDATION"

KNOWN_PACKAGE_IDS = (
    "RIGID_SHELL",
    "NASAL_INTERFACE_REFERENCE",
    "ACTUATOR_1",
    "ACTUATOR_2",
    "ACTUATOR_3",
    "ACTUATOR_4",
    "WATER_RESERVOIR_ENVELOPE",
    "WASTE_CARTRIDGE_ENVELOPE",
    "BATTERY_REFERENCE_ENVELOPE",
)

REQUIRED_UNRESOLVED_CLASSES = (
    "STRUCTURAL_FRAME_3D_MEMBERS",
    "RETENTION_AND_EMERGENCY_RELEASE",
    "CLEANSER_STORAGE_REALIZED_GEOMETRY",
    "FRESH_FLUID_REALIZED_CENTERLINES",
    "WASTE_FLUID_REALIZED_CENTERLINES_AND_BACKFLOW_DEVICE",
    "CARTRIDGE_KEY_SEAL_DOOR_AND_SERVICE_OPENING",
    "PCB_DRY_BAY_AND_HARNESS",
    "PHYSICAL_HMI",
    "WARM_HARDWARE",
    "COOL_RESERVATION",
    "SEALS_DOORS_LATCHES",
)


class WholeProductPackageError(ValueError):
    """Raised when whole-product integration data would become ambiguous or unsafe."""


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise WholeProductPackageError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise WholeProductPackageError(f"{label} must be finite")
    return 0.0 if result == 0.0 else result


def _nonnegative(value: object, label: str) -> float:
    result = _finite(value, label)
    if result < 0.0:
        raise WholeProductPackageError(f"{label} must be non-negative")
    return result


@dataclass(frozen=True, slots=True)
class Aabb:
    xmin_mm: float
    xmax_mm: float
    ymin_mm: float
    ymax_mm: float
    zmin_mm: float
    zmax_mm: float

    def __post_init__(self) -> None:
        values = tuple(
            _finite(value, label)
            for value, label in (
                (self.xmin_mm, "xmin_mm"),
                (self.xmax_mm, "xmax_mm"),
                (self.ymin_mm, "ymin_mm"),
                (self.ymax_mm, "ymax_mm"),
                (self.zmin_mm, "zmin_mm"),
                (self.zmax_mm, "zmax_mm"),
            )
        )
        if values[1] < values[0] or values[3] < values[2] or values[5] < values[4]:
            raise WholeProductPackageError("AABB maxima must not be below minima")
        for field_name, value in zip(
            ("xmin_mm", "xmax_mm", "ymin_mm", "ymax_mm", "zmin_mm", "zmax_mm"),
            values,
        ):
            object.__setattr__(self, field_name, value)

    @property
    def center_mm(self) -> tuple[float, float, float]:
        return (
            (self.xmin_mm + self.xmax_mm) / 2.0,
            (self.ymin_mm + self.ymax_mm) / 2.0,
            (self.zmin_mm + self.zmax_mm) / 2.0,
        )

    @property
    def spans_mm(self) -> tuple[float, float, float]:
        return (
            self.xmax_mm - self.xmin_mm,
            self.ymax_mm - self.ymin_mm,
            self.zmax_mm - self.zmin_mm,
        )

    @property
    def volume_mm3(self) -> float:
        x, y, z = self.spans_mm
        return x * y * z

    def translated(self, dx_mm: float, dy_mm: float, dz_mm: float) -> "Aabb":
        dx = _finite(dx_mm, "dx_mm")
        dy = _finite(dy_mm, "dy_mm")
        dz = _finite(dz_mm, "dz_mm")
        return Aabb(
            self.xmin_mm + dx,
            self.xmax_mm + dx,
            self.ymin_mm + dy,
            self.ymax_mm + dy,
            self.zmin_mm + dz,
            self.zmax_mm + dz,
        )

    def expanded(self, clearance_mm: float) -> "Aabb":
        c = _nonnegative(clearance_mm, "clearance_mm")
        return Aabb(
            self.xmin_mm - c,
            self.xmax_mm + c,
            self.ymin_mm - c,
            self.ymax_mm + c,
            self.zmin_mm - c,
            self.zmax_mm + c,
        )

    def overlap_volume_mm3(self, other: "Aabb") -> float:
        if type(other) is not Aabb:
            raise TypeError("other must be exact Aabb")
        x = max(0.0, min(self.xmax_mm, other.xmax_mm) - max(self.xmin_mm, other.xmin_mm))
        y = max(0.0, min(self.ymax_mm, other.ymax_mm) - max(self.ymin_mm, other.ymin_mm))
        z = max(0.0, min(self.zmax_mm, other.zmax_mm) - max(self.zmin_mm, other.zmin_mm))
        return x * y * z

    def minimum_axis_gap_mm(self, other: "Aabb") -> float:
        """Return conservative AABB separation; zero means touch/overlap in all axes."""
        if type(other) is not Aabb:
            raise TypeError("other must be exact Aabb")
        gaps = (
            max(0.0, other.xmin_mm - self.xmax_mm, self.xmin_mm - other.xmax_mm),
            max(0.0, other.ymin_mm - self.ymax_mm, self.ymin_mm - other.ymax_mm),
            max(0.0, other.zmin_mm - self.zmax_mm, self.zmin_mm - other.zmax_mm),
        )
        return math.sqrt(sum(gap * gap for gap in gaps))

    def manifest(self) -> dict[str, object]:
        return {
            "min_mm": [self.xmin_mm, self.ymin_mm, self.zmin_mm],
            "max_mm": [self.xmax_mm, self.ymax_mm, self.zmax_mm],
            "center_mm": list(self.center_mm),
            "spans_mm": list(self.spans_mm),
            "bounding_volume_mm3": self.volume_mm3,
        }


def aabb_from_component(component: Component) -> Aabb:
    if type(component) is not Component:
        raise TypeError("component must be exact Component")
    bb = component.solid.val().BoundingBox()
    return Aabb(
        float(bb.xmin),
        float(bb.xmax),
        float(bb.ymin),
        float(bb.ymax),
        float(bb.zmin),
        float(bb.zmax),
    )


@dataclass(frozen=True, slots=True)
class PackageItem:
    package_id: str
    component_name: str
    source_status: str
    aabb: Aabb
    mass_g: float | None
    mass_provenance: str
    geometry_provenance: str
    evidence_status: str = DIGITAL_EVIDENCE

    def __post_init__(self) -> None:
        if type(self.package_id) is not str or self.package_id not in KNOWN_PACKAGE_IDS:
            raise WholeProductPackageError(f"unknown package ID {self.package_id!r}")
        for label, value in (
            ("component_name", self.component_name),
            ("source_status", self.source_status),
            ("mass_provenance", self.mass_provenance),
            ("geometry_provenance", self.geometry_provenance),
            ("evidence_status", self.evidence_status),
        ):
            if type(value) is not str or not value.strip():
                raise WholeProductPackageError(f"{label} must be exact nonblank text")
        if type(self.aabb) is not Aabb:
            raise TypeError("aabb must be exact Aabb")
        if self.mass_g is not None:
            object.__setattr__(self, "mass_g", _nonnegative(self.mass_g, "mass_g"))

    @property
    def mass_is_closed(self) -> bool:
        return self.mass_g is not None

    def manifest(self) -> dict[str, object]:
        return {
            "package_id": self.package_id,
            "component_name": self.component_name,
            "source_status": self.source_status,
            "aabb": self.aabb.manifest(),
            "mass_g": self.mass_g,
            "mass_provenance": self.mass_provenance,
            "geometry_provenance": self.geometry_provenance,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class CollisionRecord:
    first_id: str
    second_id: str
    minimum_aabb_gap_mm: float
    aabb_overlap_volume_mm3: float
    status: str

    def manifest(self) -> dict[str, object]:
        return {
            "first_id": self.first_id,
            "second_id": self.second_id,
            "minimum_aabb_gap_mm": self.minimum_aabb_gap_mm,
            "aabb_overlap_volume_mm3": self.aabb_overlap_volume_mm3,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class ServiceMotion:
    motion_id: str
    package_id: str
    axis_xyz: tuple[int, int, int]
    travel_mm: float
    steps: int
    access_status: str
    trajectory_status: str

    def __post_init__(self) -> None:
        if type(self.motion_id) is not str or not self.motion_id.strip():
            raise WholeProductPackageError("motion_id must be exact nonblank text")
        if self.package_id not in KNOWN_PACKAGE_IDS:
            raise WholeProductPackageError("service motion package ID is unknown")
        if type(self.axis_xyz) is not tuple or len(self.axis_xyz) != 3:
            raise WholeProductPackageError("axis_xyz must be an exact 3-tuple")
        if any(type(value) is not int or value not in (-1, 0, 1) for value in self.axis_xyz):
            raise WholeProductPackageError("service axis components must be -1, 0, or 1")
        if sum(abs(value) for value in self.axis_xyz) != 1:
            raise WholeProductPackageError("service motion must follow one canonical axis")
        object.__setattr__(self, "travel_mm", _nonnegative(self.travel_mm, "travel_mm"))
        if type(self.steps) is not int or self.steps < 2:
            raise WholeProductPackageError("service motion requires at least two samples")
        for label, value in (
            ("access_status", self.access_status),
            ("trajectory_status", self.trajectory_status),
        ):
            if type(value) is not str or not value.strip():
                raise WholeProductPackageError(f"{label} must be exact nonblank text")

    def sample_offsets_mm(self) -> tuple[tuple[float, float, float], ...]:
        result: list[tuple[float, float, float]] = []
        for index in range(self.steps + 1):
            distance = self.travel_mm * index / self.steps
            result.append(tuple(float(axis) * distance for axis in self.axis_xyz))
        return tuple(result)

    def swept_aabbs(self, start: Aabb) -> tuple[Aabb, ...]:
        if type(start) is not Aabb:
            raise TypeError("start must be exact Aabb")
        return tuple(start.translated(*offset) for offset in self.sample_offsets_mm())

    def manifest(self) -> dict[str, object]:
        return {
            "motion_id": self.motion_id,
            "package_id": self.package_id,
            "axis_xyz": list(self.axis_xyz),
            "travel_mm": self.travel_mm,
            "steps": self.steps,
            "access_status": self.access_status,
            "trajectory_status": self.trajectory_status,
        }


@dataclass(frozen=True, slots=True)
class MassCgLedger:
    known_mass_g: float
    known_cg_mm: tuple[float, float, float] | None
    known_pitch_moment_Nm: float | None
    dry_total_g: float | None
    loaded_total_g: float | None
    dry_target_max_g: float
    loaded_absolute_max_g: float
    cg_z_max_mm: float
    pitch_torque_max_Nm: float
    unresolved_mass_package_ids: tuple[str, ...]
    unresolved_loaded_mass_terms: tuple[str, ...]
    status: str

    def manifest(self) -> dict[str, object]:
        return {
            "known_mass_g": self.known_mass_g,
            "known_cg_mm": None if self.known_cg_mm is None else list(self.known_cg_mm),
            "known_pitch_moment_Nm": self.known_pitch_moment_Nm,
            "dry_total_g": self.dry_total_g,
            "loaded_total_g": self.loaded_total_g,
            "targets": {
                "dry_target_max_g": self.dry_target_max_g,
                "loaded_absolute_max_g": self.loaded_absolute_max_g,
                "cg_z_max_mm": self.cg_z_max_mm,
                "pitch_torque_max_Nm": self.pitch_torque_max_Nm,
            },
            "unresolved_mass_package_ids": list(self.unresolved_mass_package_ids),
            "unresolved_loaded_mass_terms": list(self.unresolved_loaded_mass_terms),
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class WholeProductPackage:
    coordinate_frame_id: str
    authority_revision: str
    packages: tuple[PackageItem, ...]
    collision_records: tuple[CollisionRecord, ...]
    service_motions: tuple[ServiceMotion, ...]
    unresolved_classes: tuple[str, ...]
    mass_cg: MassCgLedger
    evidence_status: str = DIGITAL_EVIDENCE

    def __post_init__(self) -> None:
        if self.coordinate_frame_id != CANONICAL_FRAME_ID:
            raise WholeProductPackageError("whole-product package must use the canonical XYZ frame")
        if tuple(item.package_id for item in self.packages) != KNOWN_PACKAGE_IDS:
            raise WholeProductPackageError("package registry must follow controlled order")
        if self.unresolved_classes != REQUIRED_UNRESOLVED_CLASSES:
            raise WholeProductPackageError("unresolved package classes must remain explicit and ordered")

    @property
    def package_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": "MASCK_ONE_WHOLE_PRODUCT_PACKAGE_V1",
            "coordinate_frame_id": self.coordinate_frame_id,
            "authority_revision": self.authority_revision,
            "packages": [item.manifest() for item in self.packages],
            "collision_records": [item.manifest() for item in self.collision_records],
            "service_motions": [item.manifest() for item in self.service_motions],
            "unresolved_classes": list(self.unresolved_classes),
            "mass_cg": self.mass_cg.manifest(),
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def _package_item(package_id: str, component: Component, *, mass_g: float | None, mass_provenance: str) -> PackageItem:
    return PackageItem(
        package_id=package_id,
        component_name=component.name,
        source_status=component.status,
        aabb=aabb_from_component(component),
        mass_g=mass_g,
        mass_provenance=mass_provenance,
        geometry_provenance="CURRENT_MODEL_COMPONENT_BREP_BOUNDING_BOX",
    )


def _collision_records(packages: tuple[PackageItem, ...]) -> tuple[CollisionRecord, ...]:
    records: list[CollisionRecord] = []
    for first_index, first in enumerate(packages):
        for second in packages[first_index + 1 :]:
            overlap = first.aabb.overlap_volume_mm3(second.aabb)
            gap = first.aabb.minimum_axis_gap_mm(second.aabb)
            records.append(
                CollisionRecord(
                    first_id=first.package_id,
                    second_id=second.package_id,
                    minimum_aabb_gap_mm=gap,
                    aabb_overlap_volume_mm3=overlap,
                    status=(
                        "AABB_OVERLAP_REQUIRES_SHAPE_LEVEL_REVIEW"
                        if overlap > 0.0
                        else "AABB_CLEAR_DIGITAL_BROAD_PHASE_ONLY"
                    ),
                )
            )
    return tuple(records)


def _mass_cg(authority: Authority, packages: tuple[PackageItem, ...]) -> MassCgLedger:
    known = tuple(item for item in packages if item.mass_g is not None and item.mass_g > 0.0)
    known_mass = sum(float(item.mass_g) for item in known)
    if known_mass > 0.0:
        weighted = [
            sum(float(item.mass_g) * item.aabb.center_mm[axis] for item in known) / known_mass
            for axis in range(3)
        ]
        known_cg = (weighted[0], weighted[1], weighted[2])
        known_pitch = known_mass / 1000.0 * 9.80665 * abs(known_cg[2]) / 1000.0
    else:
        known_cg = None
        known_pitch = None

    unresolved = tuple(item.package_id for item in packages if item.mass_g is None)
    loaded_terms = (
        "WATER_FILL_MASS_DENSITY_OR_MEASURED_MASS_UNRESOLVED",
        "CLEANSER_FILL_MASS_UNRESOLVED",
        "WASTE_LOAD_MASS_UNRESOLVED",
    )
    return MassCgLedger(
        known_mass_g=known_mass,
        known_cg_mm=known_cg,
        known_pitch_moment_Nm=known_pitch,
        dry_total_g=None if unresolved else known_mass,
        loaded_total_g=None,
        dry_target_max_g=float(authority.get("mass", "dry_target_max_g")),
        loaded_absolute_max_g=float(authority.get("mass", "loaded_absolute_max_g")),
        cg_z_max_mm=float(authority.get("mass", "cg_z_max_mm")),
        pitch_torque_max_Nm=float(authority.get("mass", "pitch_torque_max_Nm")),
        unresolved_mass_package_ids=unresolved,
        unresolved_loaded_mass_terms=loaded_terms,
        status="BLOCKED_INCOMPLETE_CONTROLLED_MASS_LEDGER",
    )


def build_whole_product_package(model: MasckOneModel) -> WholeProductPackage:
    if type(model) is not MasckOneModel:
        raise TypeError("model must be exact MasckOneModel")
    authority = model.authority
    battery_mass = float(authority.get("battery_reference", "mass_g"))

    components = (
        ("RIGID_SHELL", model.shell, None, "UNRESOLVED_MATERIAL_DENSITY_OR_PART_MASS"),
        ("NASAL_INTERFACE_REFERENCE", model.nasal_interface, None, "UNRESOLVED_MATERIAL_DENSITY_OR_PART_MASS"),
        ("ACTUATOR_1", model.actuator_envelopes[0], None, "SUPPLIER_ENVELOPE_PRESENT_MASS_NOT_CONTROLLED_IN_AUTHORITY"),
        ("ACTUATOR_2", model.actuator_envelopes[1], None, "SUPPLIER_ENVELOPE_PRESENT_MASS_NOT_CONTROLLED_IN_AUTHORITY"),
        ("ACTUATOR_3", model.actuator_envelopes[2], None, "SUPPLIER_ENVELOPE_PRESENT_MASS_NOT_CONTROLLED_IN_AUTHORITY"),
        ("ACTUATOR_4", model.actuator_envelopes[3], None, "SUPPLIER_ENVELOPE_PRESENT_MASS_NOT_CONTROLLED_IN_AUTHORITY"),
        ("WATER_RESERVOIR_ENVELOPE", model.water_reservoir_envelope, None, "PART_MASS_AND_CONTROLLED_MATERIAL_DENSITY_UNRESOLVED"),
        ("WASTE_CARTRIDGE_ENVELOPE", model.waste_cartridge_envelope, None, "PART_MASS_AND_MEDIA_MASS_UNRESOLVED"),
        (
            "BATTERY_REFERENCE_ENVELOPE",
            model.battery_reference_envelope,
            battery_mass,
            "AUTHORITY_SUPPLIER_PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE",
        ),
    )
    packages = tuple(
        _package_item(package_id, component, mass_g=mass_g, mass_provenance=mass_provenance)
        for package_id, component, mass_g, mass_provenance in components
    )

    service_motions = (
        ServiceMotion(
            motion_id="WASTE_CARTRIDGE_SERVICE_NEGATIVE_Y",
            package_id="WASTE_CARTRIDGE_ENVELOPE",
            axis_xyz=(0, -1, 0),
            travel_mm=60.0,
            steps=12,
            access_status="BLOCKED_SHELL_SERVICE_OPENING_KEY_SEAL_AND_LATCH_NOT_REALIZED",
            trajectory_status="CANDIDATE_WORLD_COORDINATE_SWEEP_NOT_RELEASED_SERVICE_GEOMETRY",
        ),
        ServiceMotion(
            motion_id="WATER_REFILL_MODULE_SERVICE_POSITIVE_Y",
            package_id="WATER_RESERVOIR_ENVELOPE",
            axis_xyz=(0, 1, 0),
            travel_mm=45.0,
            steps=9,
            access_status="BLOCKED_REFILL_PORT_DOOR_SEAL_AND_GRIP_GEOMETRY_NOT_REALIZED",
            trajectory_status="CANDIDATE_WORLD_COORDINATE_SWEEP_NOT_RELEASED_SERVICE_GEOMETRY",
        ),
        ServiceMotion(
            motion_id="BATTERY_SERVICE_NEGATIVE_Z",
            package_id="BATTERY_REFERENCE_ENVELOPE",
            axis_xyz=(0, 0, -1),
            travel_mm=20.0,
            steps=8,
            access_status="BLOCKED_DRY_BAY_DOOR_CONNECTOR_HARNESS_AND_RETENTION_NOT_REALIZED",
            trajectory_status="BENCHMARK_ONLY_NOT_PRODUCTION_BATTERY_SERVICE_RELEASE",
        ),
    )

    return WholeProductPackage(
        coordinate_frame_id=CANONICAL_FRAME_ID,
        authority_revision=str(authority.get("project", "authority_revision")),
        packages=packages,
        collision_records=_collision_records(packages),
        service_motions=service_motions,
        unresolved_classes=REQUIRED_UNRESOLVED_CLASSES,
        mass_cg=_mass_cg(authority, packages),
    )


def service_motion_blockers(
    package: WholeProductPackage,
    motion_id: str,
    *,
    clearance_mm: float = 0.0,
) -> tuple[str, ...]:
    """Return package IDs whose broad-phase AABBs intersect a sampled service sweep.

    The shell is intentionally included. A shell collision is not waived merely because
    a future door is intended; it remains a blocker until an actual opening/door geometry
    removes the interference.
    """
    if type(package) is not WholeProductPackage:
        raise TypeError("package must be exact WholeProductPackage")
    matches = tuple(motion for motion in package.service_motions if motion.motion_id == motion_id)
    if len(matches) != 1:
        raise WholeProductPackageError(f"unknown or duplicate service motion {motion_id!r}")
    motion = matches[0]
    moving = next(item for item in package.packages if item.package_id == motion.package_id)
    sampled = motion.swept_aabbs(moving.aabb.expanded(clearance_mm))
    blockers: list[str] = []
    for other in package.packages:
        if other.package_id == moving.package_id:
            continue
        if any(sample.overlap_volume_mm3(other.aabb) > 0.0 for sample in sampled):
            blockers.append(other.package_id)
    return tuple(blockers)
