from __future__ import annotations

"""Source-bound whole-product collision matrix V1.

Released finite B-reps receive exact solid-to-solid checks. Authority protected regions
receive their own 2.5D hard-envelope conflict class because their Z depth is intentionally
unresolved. Released mixed-waste centerlines are represented only by conservative service
AABBs, so any overlap involving those AABBs is review-required broad phase rather than
an exact route/product collision. Current candidate geometry is recorded but never consumed.

All outputs are digital engineering evidence only, never physical validation.
"""

from dataclasses import dataclass
from hashlib import sha256
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

SCHEMA = "MASCK_ONE_WHOLE_PRODUCT_COLLISION_MATRIX_V1"
SOURCE_MAIN_SHA = "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_BLOBS = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/protected_volumes.py", "ff2b9b288559f9b268e5d08a1d6c78335f745cf1"),
    ("src/masck_one/worn_pose.py", "9d4ed65246fbc92ac577ce38bceb95cd2253607b"),
    ("src/masck_one/realized_waste_backbone.py", "6aa79d9a613e278f32da85b4654c0e35cc09b7ca"),
)
# Exact heads observed during the final live Prompt-09 producer refresh. These are
# navigation/review context only. geometry_consumed=false is enforced in the manifest.
OBSERVED_CANDIDATES = (
    ("CELL2_EXTERIOR_PR70", 70, "a5fa95f9b7355e14e72c9dbfc9a81b26a5d966fc"),
    ("CELL3_RIGHT_RELEASE_PR71", 71, "0b5a619c6cea344038b0e8b8cc10a50e3d193390"),
    ("CELL4_CLEANSER_PR80", 80, "6e3e05812406620072b37f54827b8345ed55ccea"),
    ("CELL3_OCCIPITAL_PR83", 83, "8047fda9b835b00add1277868228ad6109779092"),
    ("CELL1_MECHANICAL_PR84", 84, "01c0d77049d19463544911e5e81df3065bea7bc3"),
    ("CELL4_WATER_PUMP_PR85", 85, "668727ad2676a7d41f095878ff5d9110c8f7a44a"),
    ("CELL3_RETENTION_FIT_PR87", 87, "bf7a199838986f00a84ad48be8c7b3a11401743c"),
    ("CELL1_WET_INGESTION_PR88", 88, "f3377e0b84e60e8a16b8132142d276bc5432b190"),
    ("CELL3_HAIR_PINCH_PR89", 89, "c900c42ac5f45ad0516b58e408454eb3295d172d"),
)

CATEGORY_RIGID = "RIGID_OR_PACKAGE_GEOMETRY"
CATEGORY_ROUTE = "ROUTE_SERVICE_RESERVATION"
METHOD_BREP = "EXACT_BREP_INTERSECTION_AND_DISTANCE"
METHOD_ROUTE = "CONSERVATIVE_ROUTE_SERVICE_AABB_BROAD_PHASE"
METHOD_PROTECTED = "AUTHORITY_2P5D_PROTECTED_XY_HARD_ENVELOPE_SCREEN"
METHOD_UNRESOLVED = "BLOCKED_NO_RELEASED_GEOMETRY"
CLEAR = "CLEAR_DIGITAL"
INTERFERENCE = "EXACT_BREP_INTERFERENCE_DETECTED"
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
    return tuple(float(v) for v in (box.xmin, box.xmax, box.ymin, box.ymax, box.zmin, box.zmax))


def _narrow_phase(left: cq.Workplane, right: cq.Workplane) -> tuple[float, float, str]:
    first, second = _shape(left), _shape(right)
    volume = abs(float(first.intersect(second).Volume()))
    distance = float(first.distance(second))
    if not math.isfinite(volume) or not math.isfinite(distance) or distance < 0.0:
        raise WholeProductCollisionMatrixError("collision metrics must be finite and nonnegative")
    volume = 0.0 if volume <= KERNEL_VOLUME_EPS_MM3 else volume
    distance = 0.0 if distance <= KERNEL_DISTANCE_EPS_MM else distance
    if volume > 0.0:
        return volume, distance, INTERFERENCE
    if distance == 0.0:
        return 0.0, 0.0, TOUCHING
    return 0.0, distance, CLEAR


def _route_service_aabb(route: RealizedWasteRoute) -> cq.Workplane:
    route.validate()
    lower, upper = route.bounds_xyz_mm
    radius = route.service_envelope_radius_mm
    mins = tuple(float(v) - radius for v in lower)
    maxs = tuple(float(v) + radius for v in upper)
    sizes = tuple(maxs[i] - mins[i] for i in range(3))
    center = tuple((mins[i] + maxs[i]) / 2.0 for i in range(3))
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
        result = result.rotate((zone.center.x, zone.center.y, 0.0), (zone.center.x, zone.center.y, 1.0), zone.angle_deg)
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
        for path, digest in self.source_blobs:
            _text(path, "source path")
            _git_sha(digest, f"source blob {path}")

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
    category: str
    source_id: str
    geometry: cq.Workplane
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.participant_id, "participant ID")
        _text(self.category, "participant category")
        _text(self.source_id, "participant source ID")
        _text(self.evidence_status, "participant evidence status")
        _shape(self.geometry)

    @property
    def brep_sha256(self) -> str:
        return _brep_sha256(self.geometry)

    def manifest(self) -> dict[str, object]:
        return {
            "participant_id": self.participant_id,
            "category": self.category,
            "source_id": self.source_id,
            "brep_sha256": self.brep_sha256,
            "bounds_xyz_mm": list(_bounds(self.geometry)),
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": False,
        }


@dataclass(frozen=True, slots=True)
class CollisionCheck:
    check_id: str
    left_id: str
    right_id: str
    method: str
    status: str
    intersection_volume_mm3: float | None
    minimum_distance_mm: float | None
    evidence_status: str

    def __post_init__(self) -> None:
        for label, value in (
            ("check ID", self.check_id), ("left ID", self.left_id), ("right ID", self.right_id),
            ("method", self.method), ("status", self.status), ("evidence status", self.evidence_status),
        ):
            _text(value, label)
        if self.status not in {CLEAR, INTERFERENCE, PROTECTED_CONFLICT, TOUCHING, REVIEW, BLOCKED}:
            raise WholeProductCollisionMatrixError("collision status is uncontrolled")
        if self.status == BLOCKED:
            if self.intersection_volume_mm3 is not None or self.minimum_distance_mm is not None:
                raise WholeProductCollisionMatrixError("blocked row cannot invent metrics")
        else:
            if self.intersection_volume_mm3 is None or self.minimum_distance_mm is None:
                raise WholeProductCollisionMatrixError("geometric row requires metrics")
            if self.intersection_volume_mm3 < 0.0 or self.minimum_distance_mm < 0.0:
                raise WholeProductCollisionMatrixError("collision metrics must be nonnegative")
        if self.status == INTERFERENCE and self.method != METHOD_BREP:
            raise WholeProductCollisionMatrixError("exact interference status requires finite B-rep pair")
        if self.status == PROTECTED_CONFLICT and self.method != METHOD_PROTECTED:
            raise WholeProductCollisionMatrixError("protected conflict status requires protected-envelope method")
        if self.status == REVIEW and self.method not in {METHOD_ROUTE, METHOD_PROTECTED}:
            raise WholeProductCollisionMatrixError("conservative review status used by exact B-rep row")

    def manifest(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
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
    candidate_context: str | None
    required_against: tuple[str, ...]
    blocker: str

    def manifest(self) -> dict[str, object]:
        return {
            "interface_id": self.interface_id,
            "subsystem": self.subsystem,
            "candidate_context": self.candidate_context,
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
    observed_candidates: tuple[tuple[str, int, str], ...]
    evidence_status: str = DIGITAL_ONLY
    physical_validation_eligible: bool = False

    def validate(self) -> None:
        self.binding.validate()
        ids = tuple(item.participant_id for item in self.participants)
        if not ids or len(ids) != len(set(ids)):
            raise WholeProductCollisionMatrixError("participant IDs must be nonempty and unique")
        check_ids = tuple(item.check_id for item in self.checks)
        if not check_ids or len(check_ids) != len(set(check_ids)):
            raise WholeProductCollisionMatrixError("check IDs must be nonempty and unique")
        known = set(ids)
        for check in self.checks:
            if check.status == BLOCKED:
                continue
            if check.left_id not in known:
                raise WholeProductCollisionMatrixError("geometric row references unknown left participant")
            if check.method == METHOD_PROTECTED:
                if not check.right_id.startswith("PROTECTED:"):
                    raise WholeProductCollisionMatrixError("protected row must identify ephemeral prism")
            elif check.right_id not in known:
                raise WholeProductCollisionMatrixError("geometric row references unknown right participant")
        unresolved_ids = tuple(item.interface_id for item in self.unresolved_interfaces)
        if len(unresolved_ids) != len(set(unresolved_ids)):
            raise WholeProductCollisionMatrixError("unresolved interface IDs cannot repeat")
        if self.observed_candidates != OBSERVED_CANDIDATES:
            raise WholeProductCollisionMatrixError("candidate snapshot changed inside frozen matrix")
        for _, number, head in self.observed_candidates:
            if type(number) is not int or number <= 0:
                raise WholeProductCollisionMatrixError("candidate PR number must be positive integer")
            _git_sha(head, "observed candidate head")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WholeProductCollisionMatrixError("matrix cannot become physical evidence")
        if self.evidence_status != DIGITAL_ONLY:
            raise WholeProductCollisionMatrixError("collision evidence firewall changed")

    @property
    def exact_interference_count(self) -> int:
        return sum(item.status == INTERFERENCE for item in self.checks)

    @property
    def protected_conflict_count(self) -> int:
        return sum(item.status == PROTECTED_CONFLICT for item in self.checks)

    @property
    def review_required_count(self) -> int:
        return sum(item.status in {TOUCHING, REVIEW} for item in self.checks)

    @property
    def blocked_count(self) -> int:
        return sum(item.status == BLOCKED for item in self.checks)

    @property
    def matrix_status(self) -> str:
        if self.exact_interference_count or self.protected_conflict_count:
            return "DIGITAL_CONFLICT_PRESENT_RELEASE_BLOCKED"
        if self.review_required_count or self.blocked_count:
            return "NO_RELEASED_CONFLICT_IN_CHECKED_PAIRS_BUT_MATRIX_INCOMPLETE"
        return "CHECKED_DIGITAL_PAIRS_CLEAR_PHYSICAL_VALIDATION_STILL_REQUIRED"

    @property
    def matrix_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
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
            "observed_candidates": [
                {"label": label, "pr": number, "head_sha": head, "geometry_consumed": False}
                for label, number, head in self.observed_candidates
            ],
            "exact_interference_count": self.exact_interference_count,
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
    return CollisionParticipant(component.name, CATEGORY_RIGID, f"model:{component.name}", component.solid, f"RELEASED_MAIN_COMPONENT_STATUS:{component.status}")


def _exact_check(check_id: str, left: CollisionParticipant, right: CollisionParticipant, evidence: str) -> CollisionCheck:
    volume, distance, status = _narrow_phase(left.geometry, right.geometry)
    return CollisionCheck(check_id, left.participant_id, right.participant_id, METHOD_BREP, status, volume, distance, evidence)


def _route_check(route: CollisionParticipant, obstacle: CollisionParticipant) -> CollisionCheck:
    volume, distance, raw = _narrow_phase(route.geometry, obstacle.geometry)
    status = REVIEW if raw in {INTERFERENCE, TOUCHING} else CLEAR
    return CollisionCheck(
        f"ROUTE::{route.participant_id}::{obstacle.participant_id}", route.participant_id, obstacle.participant_id,
        METHOD_ROUTE, status, volume, distance,
        "CONSERVATIVE_ROUTE_SERVICE_AABB_VS_RELEASED_BREP;OVERLAP_REQUIRES_NARROW_PHASE_ROUTE_GEOMETRY_NOT_PRODUCT_INTERFERENCE_CLAIM",
    )


def _protected_check(participant: CollisionParticipant, zone: PlanarProtectedZone) -> CollisionCheck:
    *_, zmin, zmax = _bounds(participant.geometry)
    volume, distance, raw = _narrow_phase(participant.geometry, _protected_prism(zone, zmin, zmax))
    if participant.category == CATEGORY_ROUTE:
        status = REVIEW if raw in {INTERFERENCE, TOUCHING} else CLEAR
        evidence = (
            "CONSERVATIVE_ROUTE_SERVICE_AABB_VS_AUTHORITY_2P5D_XY_HARD_ENVELOPE;"
            "OVERLAP_REQUIRES_NARROW_PHASE_ROUTE_GEOMETRY;NOT_REGISTERED_DYNAMIC_3D_ANATOMY"
        )
    else:
        status = PROTECTED_CONFLICT if raw == INTERFERENCE else raw
        evidence = (
            "CURRENT_FINITE_BREP_VS_AUTHORITY_2P5D_XY_HARD_ENVELOPE;"
            "SOURCE_PROTECTED_Z_POLICY_REMAINS_UNBOUNDED;NOT_REGISTERED_DYNAMIC_3D_ANATOMY_OR_PHYSICAL_FIT_EVIDENCE"
        )
    return CollisionCheck(
        f"PROTECTED::{participant.participant_id}::{zone.zone_id}", participant.participant_id,
        f"PROTECTED:{zone.zone_id}:FOR:{participant.participant_id}", METHOD_PROTECTED, status, volume, distance, evidence,
    )


def _dynamic_screens(model: MasckOneModel) -> tuple[DynamicProtectedScreen, ...]:
    all_bounds = protected_zone_regression_bounds(model.protected_volumes, model.worn_pose_regression, boundary_samples=32)
    result: list[DynamicProtectedScreen] = []
    for volume in model.protected_volumes.all:
        selected = tuple(item for item in all_bounds if item.zone_id == volume.zone.zone_id)
        if len(selected) != model.worn_pose_regression.pose_count:
            raise WholeProductCollisionMatrixError("worn-pose screen lost pose coverage")
        result.append(DynamicProtectedScreen(
            volume.zone.zone_id, len(selected),
            (
                min(item.min_x_mm for item in selected), max(item.max_x_mm for item in selected),
                min(item.min_y_mm for item in selected), max(item.max_y_mm for item in selected),
                min(item.min_z_mm for item in selected), max(item.max_z_mm for item in selected),
            ),
            "DETERMINISTIC_DISCRETE_WORN_POSE_BOUNDARY_SCREEN_ONLY;SOURCE_Z_EXTENT_UNBOUNDED_AND_MEASURED_DONNING_DISTRIBUTION_UNAVAILABLE",
        ))
    return tuple(result)


def _blocked_rows() -> tuple[CollisionCheck, ...]:
    rows = (
        ("RIGHT_RELEASE_OPERATIONAL_MOTION", "WHOLE_PRODUCT_RELEASED_GEOMETRY", "right-release B-rep is candidate-only on PR71/PR84"),
        ("RIGHT_RELEASE_FACTORY_MOTION", "WHOLE_PRODUCT_RELEASED_GEOMETRY", "factory motion B-rep is candidate-only on PR71/PR84"),
        ("RETENTION_OCCIPITAL_AND_FIT_MOTION", "WHOLE_PRODUCT_RELEASED_GEOMETRY", "occipital and bounded-fit motion remains unmerged on PR83/PR87"),
        ("RETENTION_HAIR_PINCH_KEEP_OUTS", "WHOLE_PRODUCT_RELEASED_GEOMETRY", "hair/pinch and emergency-access references remain unmerged on PR89"),
        ("HARNESS", "WET_SYSTEM_AND_MECHANISM", "no released harness centerline, bundle diameter, strain-relief or flex envelope"),
        ("CARTRIDGE_SERVICE_MOTION", "WHOLE_PRODUCT_RELEASED_GEOMETRY", "released cartridge insertion/removal trajectory and clearance are unresolved"),
        ("USER_HAND_SERVICE_KEEP_OUT", "HMI_RELEASE_CARTRIDGE", "no authority-backed hand anthropometry, wet grip envelope or service trajectory is released"),
        ("PHYSICAL_HMI", "WET_ROUTE_AND_USER_HAND", "physical HMI geometry is not released; legacy Manual-B is not authority"),
    )
    return tuple(CollisionCheck(f"BLOCKED::{left}::{right}", left, right, METHOD_UNRESOLVED, BLOCKED, None, None, reason) for left, right, reason in rows)


def _unresolved_interfaces() -> tuple[UnresolvedInterface, ...]:
    return (
        UnresolvedInterface("RIGHT_RELEASE_OPERATIONAL_MOTION", "retention/emergency release", "PR71 + PR84 observed only", ("protected regions", "routes", "shell", "actuators", "water", "cartridge", "battery"), "candidate B-reps are not released on main"),
        UnresolvedInterface("RETENTION_OCCIPITAL_AND_FIT_MOTION", "occipital stabilization / fit adjustment", "PR83 + PR87 observed only", ("shell", "routes", "rear package", "protected regions", "service access"), "stacked candidate B-reps are not released and frame-side positive capture remains unresolved"),
        UnresolvedInterface("RETENTION_HAIR_PINCH_KEEP_OUTS", "hair/pinch hazard and emergency access", "PR89 observed only", ("retention motion", "right release", "user access", "rear package"), "candidate reference geometry is not released and physical guard is explicitly unrealized"),
        UnresolvedInterface("HARNESS", "power/electrical harness", None, ("wet routes", "service motions", "retention", "protected regions", "shell"), "no released routed harness geometry or flex/service envelope"),
        UnresolvedInterface("CARTRIDGE_SERVICE_MOTION", "waste cartridge service", None, ("shell", "routes", "harness", "user hand", "retention"), "insertion/removal trajectory and clearance remain explicitly unresolved"),
        UnresolvedInterface("USER_HAND_SERVICE_KEEP_OUT", "user wet/service interaction", "PR89 has candidate emergency-access corridor but no hand anthropometry", ("physical HMI", "quick release", "cartridge service", "wet routes"), "no controlled hand anthropometry or service trajectory source exists"),
        UnresolvedInterface("PHYSICAL_HMI", "physical HMI", None, ("user hand", "wet routes", "harness", "shell"), "no current released HMI geometry"),
    )


def build_whole_product_collision_matrix(model: MasckOneModel | None = None) -> WholeProductCollisionMatrix:
    model = model or build_model()
    if type(model) is not MasckOneModel:
        raise WholeProductCollisionMatrixError("matrix requires exact MasckOneModel")
    if str(model.authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise WholeProductCollisionMatrixError("model authority revision is stale")
    rigid = (
        _participant(model.shell), *tuple(_participant(item) for item in model.actuator_envelopes),
        _participant(model.water_reservoir_envelope), _participant(model.waste_cartridge_envelope),
        _participant(model.battery_reference_envelope),
    )
    release = build_current_cell4_waste_backbone_release()
    routes = tuple(CollisionParticipant(
        f"WASTE_ROUTE_SERVICE::{route.route_id}", CATEGORY_ROUTE, route.route_id, _route_service_aabb(route),
        "CONSERVATIVE_AABB_FROM_RELEASED_ROUTE_BOUNDS_PLUS_ROUTE_SERVICE_RADIUS;NOT_SELECTED_TUBING_CHANNEL_OR_PHYSICAL_SERVICE_CLEARANCE",
    ) for route in release.realization.routes)
    participants = rigid + routes
    checks: list[CollisionCheck] = []
    for index, left in enumerate(rigid):
        for right in rigid[index + 1:]:
            checks.append(_exact_check(f"BREP::{left.participant_id}::{right.participant_id}", left, right, "DIGITAL_FINITE_BREP_NARROW_PHASE_ONLY"))
    for route in routes:
        for obstacle in rigid:
            checks.append(_route_check(route, obstacle))
    for participant in participants:
        for volume in model.protected_volumes.all:
            checks.append(_protected_check(participant, volume.zone))
    checks.extend(_blocked_rows())
    matrix = WholeProductCollisionMatrix(
        SourceBinding(SOURCE_MAIN_SHA, AUTHORITY_REVISION, WORLD_FRAME_ID, SOURCE_BLOBS),
        participants, tuple(checks), _dynamic_screens(model), _unresolved_interfaces(), OBSERVED_CANDIDATES,
    )
    matrix.validate()
    return matrix


def _review_protected_prisms(protected: ProtectedVolumeSet, participants: tuple[CollisionParticipant, ...]) -> tuple[cq.Workplane, ...]:
    spans = tuple(_bounds(item.geometry) for item in participants)
    zmin, zmax = min(item[4] for item in spans), max(item[5] for item in spans)
    return tuple(_protected_prism(volume.zone, zmin, zmax) for volume in protected.all)


def export_whole_product_collision_review(output_dir: str | Path, matrix: WholeProductCollisionMatrix | None = None, model: MasckOneModel | None = None) -> tuple[Path, ...]:
    model = model or build_model()
    matrix = matrix or build_whole_product_collision_matrix(model)
    matrix.validate()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    groups = (
        ("whole_product_collision_rigid_package_reference.step", [item.geometry.val() for item in matrix.participants if item.category == CATEGORY_RIGID]),
        ("whole_product_collision_waste_service_aabbs_reference.step", [item.geometry.val() for item in matrix.participants if item.category == CATEGORY_ROUTE]),
        ("whole_product_collision_protected_prisms_reference.step", [item.val() for item in _review_protected_prisms(model.protected_volumes, matrix.participants)]),
    )
    for name, shapes in groups:
        if not shapes:
            raise WholeProductCollisionMatrixError(f"{name} requires review geometry")
        path = output / name
        cq.exporters.export(cq.Compound.makeCompound(shapes), str(path))
        paths.append(path)
    manifest_path = output / "whole_product_collision_matrix_v1.json"
    manifest_path.write_text(json.dumps(matrix.manifest(), indent=2) + "\n", encoding="utf-8")
    paths.append(manifest_path)
    return tuple(paths)
