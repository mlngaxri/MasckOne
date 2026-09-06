from __future__ import annotations

"""Current-main whole-product collision matrix V2.

The matrix separates four evidence classes:
- exact finite B-rep checks,
- authority-derived protected hard-envelope checks,
- conservative released route-service reservations,
- blocked rows where released geometry does not yet exist.

Finite package/reference envelopes remain collision participants, but overlap with one of
those envelopes is never mislabeled as realized-material interference. All outputs are
digital engineering evidence only and never physical validation.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
from io import BytesIO
import json
import math
from pathlib import Path

import cadquery as cq

from .model import Component, MasckOneModel, build_model
from .protected_volumes import PlanarProtectedZone, ProtectedVolumeSet
from .realized_waste_backbone import RealizedWasteRoute
from .realized_waste_backbone_release import build_current_cell4_waste_backbone_release
from .worn_pose import protected_zone_regression_bounds

SCHEMA = "MASCK_ONE_WHOLE_PRODUCT_COLLISION_MATRIX_V2"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

SOURCE_BLOBS = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/protected_volumes.py", "ff2b9b288559f9b268e5d08a1d6c78335f745cf1"),
    ("src/masck_one/worn_pose.py", "9d4ed65246fbc92ac577ce38bceb95cd2253607b"),
    ("src/masck_one/realized_waste_backbone.py", "6aa79d9a613e278f32da85b4654c0e35cc09b7ca"),
    ("src/masck_one/actuator_frames.py", "4c2013f994bdc9e084fe227eb5e166f973500ebb"),
    ("src/masck_one/actuator_coupling.py", "d56160304190c030e3bc389803eaa456aaab5af0"),
    ("src/masck_one/fresh_pump_packaging.py", "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4"),
    ("src/masck_one/distribution_manifold.py", "8f2a6c784b51734aba4d1f3809015707fc328405"),
    ("src/masck_one/distribution_geometry.py", "d2dd8b47bb6a2aa1edf57ac0632778228add7997"),
    ("src/masck_one/waste_cartridge_dfm.py", "f9788cce30c14600c8a624509153596e46c1e478"),
)

ROLE_MATERIAL = "PHYSICAL_MATERIAL"
ROLE_PACKAGE = "CONTROLLED_PACKAGE_OR_DEVELOPMENT_REFERENCE"
ROLE_BENCHMARK = "PACKAGING_BENCHMARK_REFERENCE"
CATEGORY_ROUTE = "ROUTE_SERVICE_RESERVATION"
FINITE_ROLE_BY_ID = {
    "rigid_shell": ROLE_MATERIAL,
    "actuator_envelope_1": ROLE_PACKAGE,
    "actuator_envelope_2": ROLE_PACKAGE,
    "actuator_envelope_3": ROLE_PACKAGE,
    "actuator_envelope_4": ROLE_PACKAGE,
    "water_reservoir_envelope": ROLE_PACKAGE,
    "waste_cartridge_envelope": ROLE_PACKAGE,
    "battery_reference_envelope": ROLE_BENCHMARK,
}

ROW_EXACT = "EXACT"
ROW_PROTECTED = "PROTECTED"
ROW_CONSERVATIVE = "CONSERVATIVE"
ROW_BLOCKED = "BLOCKED"

METHOD_BREP = "EXACT_BREP_INTERSECTION_AND_DISTANCE"
METHOD_ROUTE = "CONSERVATIVE_ROUTE_SERVICE_AABB_BROAD_PHASE"
METHOD_PROTECTED = "AUTHORITY_2P5D_PROTECTED_XY_HARD_ENVELOPE_SCREEN"
METHOD_UNRESOLVED = "BLOCKED_NO_RELEASED_GEOMETRY"

CLEAR = "CLEAR_DIGITAL"
MATERIAL_INTERFERENCE = "EXACT_MATERIAL_INTERFERENCE_DETECTED"
REFERENCE_OVERLAP = "EXACT_REFERENCE_OR_PACKAGE_OVERLAP_REVIEW_REQUIRED"
PROTECTED_CONFLICT = "PROTECTED_HARD_ENVELOPE_CONFLICT"
TOUCHING = "TOUCHING_REVIEW_REQUIRED"
REVIEW = "CONSERVATIVE_RESERVATION_OVERLAP_REVIEW_REQUIRED"
BLOCKED = "BLOCKED_UNRESOLVED_GEOMETRY"

KERNEL_VOLUME_EPS_MM3 = 1e-7
KERNEL_DISTANCE_EPS_MM = 1e-7
DIGITAL_ONLY = (
    "DIGITAL_COLLISION_AND_PROVENANCE_EVIDENCE_ONLY_NOT_FIT_COMFORT_ANATOMICAL_SERVICE_"
    "WET_HAND_LEAKAGE_HYGIENE_DURABILITY_OR_PHYSICAL_SAFETY_EVIDENCE"
)
_REPO_ROOT = Path(__file__).resolve().parents[2]


class WholeProductCollisionMatrixError(ValueError):
    pass


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise WholeProductCollisionMatrixError(f"{label} must be exact nonblank text")
    return value


def _git_sha(value: object, label: str) -> str:
    text = _text(value, label)
    if len(text) != 40 or any(char not in "0123456789abcdef" for char in text):
        raise WholeProductCollisionMatrixError(f"{label} must be lowercase 40-hex")
    return text


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    return sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def _require_sources_current() -> None:
    for relative_path, expected in SOURCE_BLOBS:
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise WholeProductCollisionMatrixError(f"collision source file is missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise WholeProductCollisionMatrixError(
                f"collision source moved at {relative_path}; expected {expected}, got {actual}"
            )


def _shape(workplane: cq.Workplane) -> cq.Shape:
    shape = workplane.val()
    if not shape.isValid() or not shape.Solids() or float(shape.Volume()) <= 0.0:
        raise WholeProductCollisionMatrixError("collision participant requires valid positive-volume B-rep")
    return shape


def _brep_sha256(workplane: cq.Workplane) -> str:
    buffer = BytesIO()
    _shape(workplane).exportBrep(buffer)
    payload = buffer.getvalue()
    if not payload:
        raise WholeProductCollisionMatrixError("B-rep serialization produced no bytes")
    return sha256(payload).hexdigest()


def _bounds(workplane: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    box = _shape(workplane).BoundingBox()
    return tuple(float(value) for value in (box.xmin, box.xmax, box.ymin, box.ymax, box.zmin, box.zmax))


def _narrow_phase(left: cq.Workplane, right: cq.Workplane) -> tuple[float, float, str]:
    first, second = _shape(left), _shape(right)
    volume = abs(float(first.intersect(second).Volume()))
    distance = float(first.distance(second))
    if not math.isfinite(volume) or not math.isfinite(distance) or distance < 0.0:
        raise WholeProductCollisionMatrixError("collision metrics must be finite and nonnegative")
    volume = 0.0 if volume <= KERNEL_VOLUME_EPS_MM3 else volume
    distance = 0.0 if distance <= KERNEL_DISTANCE_EPS_MM else distance
    if volume > 0.0:
        return volume, distance, "OVERLAP"
    if distance == 0.0:
        return 0.0, 0.0, "TOUCHING"
    return 0.0, distance, "CLEAR"


def _route_service_aabb(route: RealizedWasteRoute) -> cq.Workplane:
    route.validate()
    lower, upper = route.bounds_xyz_mm
    radius = route.service_envelope_radius_mm
    mins = tuple(float(value) - radius for value in lower)
    maxs = tuple(float(value) + radius for value in upper)
    sizes = tuple(maxs[index] - mins[index] for index in range(3))
    center = tuple((mins[index] + maxs[index]) / 2.0 for index in range(3))
    result = cq.Workplane("XY").box(*sizes, centered=(True, True, True)).translate(center)
    _shape(result)
    return result


def _protected_prism(zone: PlanarProtectedZone, zmin: float, zmax: float) -> cq.Workplane:
    if not math.isfinite(zmin) or not math.isfinite(zmax) or zmax <= zmin:
        raise WholeProductCollisionMatrixError("protected prism requires finite positive Z span")
    base = cq.Workplane("XY").workplane(offset=zmin).center(zone.center.x, zone.center.y)
    depth = zmax - zmin
    if zone.shape == "CIRCLE":
        result = base.circle(zone.envelope_width_mm / 2.0).extrude(depth)
    elif zone.shape == "ELLIPSE":
        result = base.ellipse(zone.envelope_width_mm / 2.0, zone.envelope_height_mm / 2.0).extrude(depth)
    else:
        raise WholeProductCollisionMatrixError(f"unsupported protected shape {zone.shape!r}")
    if zone.angle_deg:
        result = result.rotate(
            (zone.center.x, zone.center.y, 0.0),
            (zone.center.x, zone.center.y, 1.0),
            zone.angle_deg,
        )
    _shape(result)
    return result


@dataclass(frozen=True, slots=True)
class SourceBinding:
    source_main_sha: str
    authority_revision: str
    world_frame_id: str
    source_blobs: tuple[tuple[str, str], ...]

    def validate(self) -> None:
        if _git_sha(self.source_main_sha, "source main") != SOURCE_MAIN_SHA:
            raise WholeProductCollisionMatrixError("matrix is stale for released main")
        if self.authority_revision != AUTHORITY_REVISION or self.world_frame_id != WORLD_FRAME_ID:
            raise WholeProductCollisionMatrixError("authority revision or world frame changed")
        if self.source_blobs != SOURCE_BLOBS:
            raise WholeProductCollisionMatrixError("collision source blob set changed")
        _require_sources_current()

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "world_frame_id": self.world_frame_id,
            "source_blobs": [list(item) for item in self.source_blobs],
        }


@dataclass(frozen=True, slots=True)
class CollisionParticipant:
    participant_id: str
    geometry_role: str
    source_id: str
    geometry: cq.Workplane
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.participant_id, "participant ID")
        if self.geometry_role not in {ROLE_MATERIAL, ROLE_PACKAGE, ROLE_BENCHMARK, CATEGORY_ROUTE}:
            raise WholeProductCollisionMatrixError("collision participant role is uncontrolled")
        _text(self.source_id, "participant source ID")
        _text(self.evidence_status, "participant evidence status")
        _shape(self.geometry)

    @property
    def brep_sha256(self) -> str:
        return _brep_sha256(self.geometry)

    def manifest(self) -> dict[str, object]:
        return {
            "participant_id": self.participant_id,
            "geometry_role": self.geometry_role,
            "source_id": self.source_id,
            "brep_sha256": self.brep_sha256,
            "bounds_xyz_mm": list(_bounds(self.geometry)),
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": False,
        }


@dataclass(frozen=True, slots=True)
class CollisionCheck:
    check_id: str
    row_class: str
    left_id: str
    right_id: str
    method: str
    status: str
    intersection_volume_mm3: float | None
    minimum_distance_mm: float | None
    evidence_status: str

    def __post_init__(self) -> None:
        for label, value in (
            ("check ID", self.check_id),
            ("left ID", self.left_id),
            ("right ID", self.right_id),
            ("method", self.method),
            ("status", self.status),
            ("evidence status", self.evidence_status),
        ):
            _text(value, label)
        if self.row_class not in {ROW_EXACT, ROW_PROTECTED, ROW_CONSERVATIVE, ROW_BLOCKED}:
            raise WholeProductCollisionMatrixError("row class is uncontrolled")
        if self.status not in {
            CLEAR, MATERIAL_INTERFERENCE, REFERENCE_OVERLAP, PROTECTED_CONFLICT, TOUCHING, REVIEW, BLOCKED
        }:
            raise WholeProductCollisionMatrixError("collision status is uncontrolled")
        if self.status == BLOCKED:
            if self.row_class != ROW_BLOCKED or self.method != METHOD_UNRESOLVED:
                raise WholeProductCollisionMatrixError("blocked row has incorrect class or method")
            if self.intersection_volume_mm3 is not None or self.minimum_distance_mm is not None:
                raise WholeProductCollisionMatrixError("blocked row cannot invent metrics")
        else:
            if self.intersection_volume_mm3 is None or self.minimum_distance_mm is None:
                raise WholeProductCollisionMatrixError("geometric row requires metrics")
            if (
                not math.isfinite(float(self.intersection_volume_mm3))
                or not math.isfinite(float(self.minimum_distance_mm))
                or self.intersection_volume_mm3 < 0.0
                or self.minimum_distance_mm < 0.0
            ):
                raise WholeProductCollisionMatrixError("collision metrics must be finite and nonnegative")
        if self.status in {MATERIAL_INTERFERENCE, REFERENCE_OVERLAP}:
            if self.row_class != ROW_EXACT or self.method != METHOD_BREP:
                raise WholeProductCollisionMatrixError("exact overlap requires exact B-rep row")
        if self.status == PROTECTED_CONFLICT and self.row_class != ROW_PROTECTED:
            raise WholeProductCollisionMatrixError("protected conflict requires protected row")
        if self.status == REVIEW and self.row_class not in {ROW_CONSERVATIVE, ROW_PROTECTED}:
            raise WholeProductCollisionMatrixError("conservative review status used by nonconservative row")

    def manifest(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "row_class": self.row_class,
            "left_id": self.left_id,
            "right_id": self.right_id,
            "method": self.method,
            "status": self.status,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "minimum_distance_mm": self.minimum_distance_mm,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class DynamicProtectedScreen:
    zone_id: str
    pose_count: int
    bounds_mm: tuple[float, float, float, float, float, float]
    evidence_status: str

    def manifest(self) -> dict[str, object]:
        return {
            "zone_id": self.zone_id,
            "pose_count": self.pose_count,
            "aggregate_sampled_boundary_bounds_mm": list(self.bounds_mm),
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class UnresolvedInterface:
    interface_id: str
    subsystem: str
    required_against: tuple[str, ...]
    blocker: str

    def manifest(self) -> dict[str, object]:
        return {
            "interface_id": self.interface_id,
            "subsystem": self.subsystem,
            "required_against": list(self.required_against),
            "blocker": self.blocker,
            "geometry_consumed": False,
        }


@dataclass(frozen=True, slots=True)
class WholeProductCollisionMatrix:
    binding: SourceBinding
    participants: tuple[CollisionParticipant, ...]
    checks: tuple[CollisionCheck, ...]
    dynamic_protected_screens: tuple[DynamicProtectedScreen, ...]
    unresolved_interfaces: tuple[UnresolvedInterface, ...]
    evidence_status: str = DIGITAL_ONLY
    physical_validation_eligible: bool = False

    def validate(self) -> None:
        self.binding.validate()
        ids = tuple(item.participant_id for item in self.participants)
        if not ids or len(ids) != len(set(ids)):
            raise WholeProductCollisionMatrixError("participant IDs must be nonempty and unique")
        finite = tuple(item for item in self.participants if item.geometry_role != CATEGORY_ROUTE)
        role_map = {item.participant_id: item.geometry_role for item in finite}
        if role_map != FINITE_ROLE_BY_ID:
            raise WholeProductCollisionMatrixError("finite participant role map moved or was spoofed")
        check_ids = tuple(item.check_id for item in self.checks)
        if not check_ids or len(check_ids) != len(set(check_ids)):
            raise WholeProductCollisionMatrixError("check IDs must be nonempty and unique")
        known = set(ids)
        for check in self.checks:
            if check.status == BLOCKED:
                continue
            if check.left_id not in known:
                raise WholeProductCollisionMatrixError("geometric row references unknown left participant")
            if check.row_class == ROW_PROTECTED:
                if not check.right_id.startswith("PROTECTED:"):
                    raise WholeProductCollisionMatrixError("protected row must identify ephemeral protected prism")
            elif check.right_id not in known:
                raise WholeProductCollisionMatrixError("geometric row references unknown right participant")
        blocked_ids = {item.left_id for item in self.checks if item.status == BLOCKED}
        unresolved_ids = {item.interface_id for item in self.unresolved_interfaces}
        if blocked_ids != unresolved_ids or len(blocked_ids) != len(self.unresolved_interfaces):
            raise WholeProductCollisionMatrixError("blocked rows and unresolved interfaces must correspond exactly")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WholeProductCollisionMatrixError("matrix cannot become physical evidence")
        if self.evidence_status != DIGITAL_ONLY:
            raise WholeProductCollisionMatrixError("collision evidence firewall changed")

    @property
    def row_class_counts(self) -> dict[str, int]:
        return {
            row_class: sum(item.row_class == row_class for item in self.checks)
            for row_class in (ROW_EXACT, ROW_PROTECTED, ROW_CONSERVATIVE, ROW_BLOCKED)
        }

    @property
    def exact_overlap_count(self) -> int:
        return sum(item.status in {MATERIAL_INTERFERENCE, REFERENCE_OVERLAP} for item in self.checks)

    @property
    def material_interference_count(self) -> int:
        return sum(item.status == MATERIAL_INTERFERENCE for item in self.checks)

    @property
    def reference_overlap_count(self) -> int:
        return sum(item.status == REFERENCE_OVERLAP for item in self.checks)

    @property
    def protected_conflict_count(self) -> int:
        return sum(item.status == PROTECTED_CONFLICT for item in self.checks)

    @property
    def review_required_count(self) -> int:
        return sum(item.status in {REFERENCE_OVERLAP, TOUCHING, REVIEW} for item in self.checks)

    @property
    def blocked_count(self) -> int:
        return sum(item.status == BLOCKED for item in self.checks)

    @property
    def matrix_status(self) -> str:
        if self.exact_overlap_count or self.protected_conflict_count:
            return "DIGITAL_CONFLICT_PRESENT_RELEASE_BLOCKED"
        if self.review_required_count or self.blocked_count:
            return "NO_RELEASED_CONFLICT_IN_CHECKED_PAIRS_BUT_MATRIX_INCOMPLETE"
        return "CHECKED_DIGITAL_PAIRS_CLEAR_PHYSICAL_VALIDATION_STILL_REQUIRED"

    @property
    def matrix_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.validate()
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "binding": self.binding.manifest(),
            "participants": [item.manifest() for item in self.participants],
            "checks": [item.manifest() for item in self.checks],
            "dynamic_protected_screens": [item.manifest() for item in self.dynamic_protected_screens],
            "unresolved_interfaces": [item.manifest() for item in self.unresolved_interfaces],
            "row_class_counts": self.row_class_counts,
            "row_count": len(self.checks),
            "exact_overlap_count": self.exact_overlap_count,
            "material_interference_count": self.material_interference_count,
            "reference_overlap_count": self.reference_overlap_count,
            "protected_conflict_count": self.protected_conflict_count,
            "review_required_count": self.review_required_count,
            "blocked_count": self.blocked_count,
            "matrix_status": self.matrix_status,
            "physical_validation_eligible": False,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            payload["matrix_sha256"] = sha256(raw).hexdigest()
        return payload


def _participant(component: Component) -> CollisionParticipant:
    try:
        role = FINITE_ROLE_BY_ID[component.name]
    except KeyError as exc:
        raise WholeProductCollisionMatrixError(
            f"uncontrolled finite collision participant {component.name!r}"
        ) from exc
    return CollisionParticipant(
        component.name,
        role,
        f"model:{component.name}",
        component.solid,
        f"RELEASED_MAIN_COMPONENT_STATUS:{component.status}",
    )


def _exact_check(left: CollisionParticipant, right: CollisionParticipant) -> CollisionCheck:
    volume, distance, raw = _narrow_phase(left.geometry, right.geometry)
    if raw == "OVERLAP":
        status = (
            MATERIAL_INTERFERENCE
            if left.geometry_role == ROLE_MATERIAL and right.geometry_role == ROLE_MATERIAL
            else REFERENCE_OVERLAP
        )
    elif raw == "TOUCHING":
        status = TOUCHING
    else:
        status = CLEAR
    evidence = (
        "EXACT_FINITE_BREP_NARROW_PHASE;"
        f"LEFT_ROLE={left.geometry_role};RIGHT_ROLE={right.geometry_role};"
        "REFERENCE_OR_PACKAGE_OVERLAP_IS_NOT_REALIZED_MATERIAL_INTERFERENCE"
    )
    return CollisionCheck(
        f"BREP::{left.participant_id}::{right.participant_id}",
        ROW_EXACT,
        left.participant_id,
        right.participant_id,
        METHOD_BREP,
        status,
        volume,
        distance,
        evidence,
    )


def _route_check(route: CollisionParticipant, obstacle: CollisionParticipant) -> CollisionCheck:
    volume, distance, raw = _narrow_phase(route.geometry, obstacle.geometry)
    status = REVIEW if raw in {"OVERLAP", "TOUCHING"} else CLEAR
    return CollisionCheck(
        f"ROUTE::{route.participant_id}::{obstacle.participant_id}",
        ROW_CONSERVATIVE,
        route.participant_id,
        obstacle.participant_id,
        METHOD_ROUTE,
        status,
        volume,
        distance,
        "CONSERVATIVE_ROUTE_SERVICE_AABB_VS_FINITE_BREP;OVERLAP_REQUIRES_NARROW_PHASE_ROUTE_GEOMETRY_NOT_PRODUCT_INTERFERENCE_CLAIM",
    )


def _protected_check(participant: CollisionParticipant, zone: PlanarProtectedZone) -> CollisionCheck:
    *_, zmin, zmax = _bounds(participant.geometry)
    volume, distance, raw = _narrow_phase(participant.geometry, _protected_prism(zone, zmin, zmax))
    if participant.geometry_role == CATEGORY_ROUTE:
        status = REVIEW if raw in {"OVERLAP", "TOUCHING"} else CLEAR
        evidence = (
            "CONSERVATIVE_ROUTE_SERVICE_AABB_VS_AUTHORITY_2P5D_XY_HARD_ENVELOPE;"
            "OVERLAP_REQUIRES_NARROW_PHASE_ROUTE_GEOMETRY;NOT_REGISTERED_DYNAMIC_3D_ANATOMY"
        )
    else:
        status = PROTECTED_CONFLICT if raw == "OVERLAP" else TOUCHING if raw == "TOUCHING" else CLEAR
        evidence = (
            f"FINITE_BREP_ROLE={participant.geometry_role}_VS_AUTHORITY_2P5D_XY_HARD_ENVELOPE;"
            "SOURCE_PROTECTED_Z_POLICY_REMAINS_UNBOUNDED;"
            "NOT_REGISTERED_DYNAMIC_3D_ANATOMY_OR_PHYSICAL_FIT_EVIDENCE"
        )
    return CollisionCheck(
        f"PROTECTED::{participant.participant_id}::{zone.zone_id}",
        ROW_PROTECTED,
        participant.participant_id,
        f"PROTECTED:{zone.zone_id}:FOR:{participant.participant_id}",
        METHOD_PROTECTED,
        status,
        volume,
        distance,
        evidence,
    )


def _dynamic_screens(model: MasckOneModel) -> tuple[DynamicProtectedScreen, ...]:
    all_bounds = protected_zone_regression_bounds(
        model.protected_volumes, model.worn_pose_regression, boundary_samples=32
    )
    result: list[DynamicProtectedScreen] = []
    for volume in model.protected_volumes.all:
        selected = tuple(item for item in all_bounds if item.zone_id == volume.zone.zone_id)
        if len(selected) != model.worn_pose_regression.pose_count:
            raise WholeProductCollisionMatrixError("worn-pose screen lost pose coverage")
        result.append(
            DynamicProtectedScreen(
                volume.zone.zone_id,
                len(selected),
                (
                    min(item.min_x_mm for item in selected),
                    max(item.max_x_mm for item in selected),
                    min(item.min_y_mm for item in selected),
                    max(item.max_y_mm for item in selected),
                    min(item.min_z_mm for item in selected),
                    max(item.max_z_mm for item in selected),
                ),
                "DETERMINISTIC_DISCRETE_WORN_POSE_BOUNDARY_SCREEN_ONLY;SOURCE_Z_EXTENT_UNBOUNDED_AND_MEASURED_DONNING_DISTRIBUTION_UNAVAILABLE",
            )
        )
    return tuple(result)


_UNRESOLVED = (
    (
        "RIGHT_RELEASE_OPERATIONAL_MOTION",
        "retention/emergency release",
        ("protected regions", "routes", "shell", "actuators", "water", "cartridge", "battery"),
        "no released right-release operational sweep B-rep exists on current main",
    ),
    (
        "RIGHT_RELEASE_FACTORY_MOTION",
        "retention/emergency release",
        ("shell", "actuators", "packages", "routes"),
        "no released right-release factory assembly sweep B-rep exists on current main",
    ),
    (
        "RETENTION_OCCIPITAL_AND_FIT_MOTION",
        "occipital stabilization / fit adjustment",
        ("shell", "routes", "rear package", "protected regions", "service access"),
        "current main has no released occipital or bounded-fit moving B-rep",
    ),
    (
        "RETENTION_HAIR_PINCH_KEEP_OUTS",
        "hair/pinch hazard and emergency access",
        ("retention motion", "right release", "user access", "rear package"),
        "current main has no released hair/pinch hazard or emergency-access keepout geometry",
    ),
    (
        "HARNESS",
        "power/electrical harness",
        ("wet routes", "service motions", "retention", "protected regions", "shell"),
        "no released harness centerline, bundle diameter, strain-relief or flex/service envelope",
    ),
    (
        "CARTRIDGE_SERVICE_MOTION",
        "waste cartridge service",
        ("shell", "routes", "harness", "user hand", "retention"),
        "cartridge insertion/removal trajectory and clearance remain explicitly unresolved",
    ),
    (
        "USER_HAND_SERVICE_KEEP_OUT",
        "user wet/service interaction",
        ("physical HMI", "quick release", "cartridge service", "wet routes"),
        "no authority-backed hand anthropometry, wet grip envelope or service trajectory is released",
    ),
    (
        "PHYSICAL_HMI",
        "physical HMI",
        ("user hand", "wet routes", "harness", "shell"),
        "no current released physical HMI geometry exists",
    ),
    (
        "ACTUATOR_OPERATIONAL_SWEEP_AND_FINAL_STOPS",
        "actuation mechanics",
        ("shell", "protected regions", "frame", "neighbor actuators", "packages", "routes"),
        "released actuator-frame architecture has unresolved origins/azimuths/mount datums/envelopes and is not sweep-ready; final stop geometry is unresolved",
    ),
    (
        "ACTUATOR_CARRIER_REACTION_AND_SERVICE_GEOMETRY",
        "actuation mechanics",
        ("frame", "shell", "protected regions", "packages", "routes", "service access"),
        "released coupling architecture has no realized carrier, reaction-path, retention or service B-rep",
    ),
    (
        "FRESH_FLUID_ROUTE_CENTERLINES_AND_CROSS_SECTIONS",
        "fresh water and cleanser routing",
        ("shell", "frame", "actuators", "packages", "harness", "service motions", "protected regions"),
        "four controlled fresh routes exist but released centerlines and tube/channel cross-sections do not",
    ),
    (
        "FRESH_MANIFOLD_BODY_BRANCH_AND_JOIN_GEOMETRY",
        "fresh water and cleanser manifold",
        ("shell", "frame", "actuators", "routes", "harness", "service motions", "protected regions"),
        "two controlled manifold branches exist but body/branch/join B-reps do not",
    ),
    (
        "DISTRIBUTION_GROOVE_AND_OUTLET_PATH_GEOMETRY",
        "skin-facing distribution",
        ("shell", "interface", "actuators", "fresh manifold", "protected regions"),
        "24 distribution outlet/groove intents exist but dimensioned groove and skin-facing path geometry remain unresolved",
    ),
)


def _blocked_rows() -> tuple[CollisionCheck, ...]:
    return tuple(
        CollisionCheck(
            f"BLOCKED::{interface_id}::CURRENT_MAIN",
            ROW_BLOCKED,
            interface_id,
            "CURRENT_MAIN",
            METHOD_UNRESOLVED,
            BLOCKED,
            None,
            None,
            blocker,
        )
        for interface_id, _, _, blocker in _UNRESOLVED
    )


def _unresolved_interfaces() -> tuple[UnresolvedInterface, ...]:
    return tuple(
        UnresolvedInterface(interface_id, subsystem, required_against, blocker)
        for interface_id, subsystem, required_against, blocker in _UNRESOLVED
    )


def build_whole_product_collision_matrix(model: MasckOneModel | None = None) -> WholeProductCollisionMatrix:
    model = model or build_model()
    if type(model) is not MasckOneModel:
        raise WholeProductCollisionMatrixError("matrix requires exact MasckOneModel")
    if str(model.authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise WholeProductCollisionMatrixError("model authority revision is stale")

    finite = (
        _participant(model.shell),
        *tuple(_participant(item) for item in model.actuator_envelopes),
        _participant(model.water_reservoir_envelope),
        _participant(model.waste_cartridge_envelope),
        _participant(model.battery_reference_envelope),
    )
    release = build_current_cell4_waste_backbone_release()
    routes = tuple(
        CollisionParticipant(
            f"WASTE_ROUTE_SERVICE::{route.route_id}",
            CATEGORY_ROUTE,
            route.route_id,
            _route_service_aabb(route),
            "CONSERVATIVE_AABB_FROM_RELEASED_ROUTE_BOUNDS_PLUS_ROUTE_SERVICE_RADIUS;NOT_SELECTED_TUBING_CHANNEL_OR_PHYSICAL_SERVICE_CLEARANCE",
        )
        for route in release.realization.routes
    )
    participants = finite + routes

    checks: list[CollisionCheck] = []
    for index, left in enumerate(finite):
        for right in finite[index + 1:]:
            checks.append(_exact_check(left, right))
    for route in routes:
        for obstacle in finite:
            checks.append(_route_check(route, obstacle))
    for participant in participants:
        for volume in model.protected_volumes.all:
            checks.append(_protected_check(participant, volume.zone))
    checks.extend(_blocked_rows())

    matrix = WholeProductCollisionMatrix(
        SourceBinding(SOURCE_MAIN_SHA, AUTHORITY_REVISION, WORLD_FRAME_ID, SOURCE_BLOBS),
        participants,
        tuple(checks),
        _dynamic_screens(model),
        _unresolved_interfaces(),
    )
    matrix.validate()
    return matrix


def _review_protected_prisms(
    protected: ProtectedVolumeSet,
    participants: tuple[CollisionParticipant, ...],
) -> tuple[cq.Workplane, ...]:
    spans = tuple(_bounds(item.geometry) for item in participants)
    zmin, zmax = min(item[4] for item in spans), max(item[5] for item in spans)
    return tuple(_protected_prism(volume.zone, zmin, zmax) for volume in protected.all)


def export_whole_product_collision_review(
    output_dir: str | Path,
    matrix: WholeProductCollisionMatrix | None = None,
    model: MasckOneModel | None = None,
) -> tuple[Path, ...]:
    model = model or build_model()
    matrix = matrix or build_whole_product_collision_matrix(model)
    matrix.validate()

    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    groups = (
        (
            "whole_product_collision_finite_reference.step",
            [item.geometry.val() for item in matrix.participants if item.geometry_role != CATEGORY_ROUTE],
        ),
        (
            "whole_product_collision_waste_service_aabbs_reference.step",
            [item.geometry.val() for item in matrix.participants if item.geometry_role == CATEGORY_ROUTE],
        ),
        (
            "whole_product_collision_protected_prisms_reference.step",
            [item.val() for item in _review_protected_prisms(model.protected_volumes, matrix.participants)],
        ),
    )
    for name, shapes in groups:
        if not shapes:
            raise WholeProductCollisionMatrixError(f"{name} requires review geometry")
        path = output / name
        cq.exporters.export(cq.Compound.makeCompound(shapes), str(path))
        paths.append(path)

    manifest_path = output / "whole_product_collision_matrix_v2.json"
    manifest_path.write_text(json.dumps(matrix.manifest(), indent=2) + "\n", encoding="utf-8")
    paths.append(manifest_path)
    return tuple(paths)
