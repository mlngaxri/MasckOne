from __future__ import annotations

"""Whole-product cross-system collision matrix V1.

This Cell 1 integration layer consumes released geometry without reauthoring subsystem
solids. It computes exact B-rep interference where both sides exist, uses the released
mixed-waste service reservation as conservative route geometry, and emits explicit
blocked rows where no released geometry exists. Authority-derived facial protected
volumes remain 2.5D/unbounded in Z; for one finite solid, the narrow-phase check therefore
extrudes the exact protected XY footprint only across that solid's own Z extent.

All results are digital engineering evidence only. They are not fit, comfort, leakage,
service, wet-hand, anatomical, durability, hygiene, or other physical validation.
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
from .realized_waste_backbone import PHASE_MIXED_WASTE, RealizedWasteRoute
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

# Observed candidates are navigation/review context only. Their geometry is not consumed
# by this released-main matrix and cannot silently become collision evidence.
OBSERVED_CANDIDATES = (
    ("CELL2_EXTERIOR_PR70", 70, "d95b116c6ebf64bd315dd0ee69c7e5c160de69ff"),
    ("CELL3_RIGHT_RELEASE_PR71", 71, "0b5a619c6cea344038b0e8b8cc10a50e3d193390"),
    ("CELL4_CLEANSER_PR80", 80, "02e1bcd1b0fccacfec134423b9e5cf285108ec1b"),
    ("CELL1_MECHANICAL_PR84", 84, "01c0d77049d19463544911e5e81df3065bea7bc3"),
    ("CELL4_WATER_PUMP_PR85", 85, "03d82912490f46fc9ef6cbe4f3d2362266cb784c"),
    ("CELL1_WET_INGESTION_PR88", 88, "f3377e0b84e60e8a16b8132142d276bc5432b190"),
)

CATEGORY_RIGID = "RIGID_OR_PACKAGE_GEOMETRY"
CATEGORY_ROUTE = "ROUTE_SERVICE_RESERVATION"
CATEGORY_PROTECTED = "USER_ANATOMICAL_PROTECTED_REGION"
CATEGORY_UNRESOLVED = "UNRESOLVED_SYSTEM_GEOMETRY"

METHOD_BREP = "EXACT_BREP_INTERSECTION_AND_DISTANCE"
METHOD_PROTECTED = "EXACT_XY_PROTECTED_FOOTPRINT_OVER_FINITE_SOLID_Z_SPAN"
METHOD_UNRESOLVED = "BLOCKED_NO_RELEASED_GEOMETRY"

CLEAR = "CLEAR_DIGITAL"
INTERFERENCE = "INTERFERENCE_DETECTED"
TOUCHING = "TOUCHING_REVIEW_REQUIRED"
BLOCKED = "BLOCKED_UNRESOLVED_GEOMETRY"

KERNEL_VOLUME_EPS_MM3 = 1e-7
KERNEL_DISTANCE_EPS_MM = 1e-7
DIGITAL_ONLY = (
    "DIGITAL_COLLISION_AND_PROVENANCE_EVIDENCE_ONLY_NOT_FIT_COMFORT_ANATOMICAL_SERVICE_"
    "WET_HAND_LEAKAGE_HYGIENE_DURABILITY_OR_PHYSICAL_SAFETY_EVIDENCE"
)


class WholeProductCollisionMatrixError(ValueError):
    pass


def _require_text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise WholeProductCollisionMatrixError(f"{label} must be exact nonblank text")
    return value


def _git_sha(value: object, *, label: str) -> str:
    text = _require_text(value, label=label)
    if len(text) != 40 or any(char not in "0123456789abcdef" for char in text):
        raise WholeProductCollisionMatrixError(f"{label} must be lowercase 40-hex")
    return text


def _sha256(value: object, *, label: str) -> str:
    text = _require_text(value, label=label)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise WholeProductCollisionMatrixError(f"{label} must be lowercase SHA-256")
    return text


def _shape(workplane: cq.Workplane) -> cq.Shape:
    shape = workplane.val()
    if not shape.isValid() or not shape.Solids() or float(shape.Volume()) <= 0.0:
        raise WholeProductCollisionMatrixError("collision participant requires valid positive-volume B-rep")
    return shape


def _brep_sha256(workplane: cq.Workplane) -> str:
    shape = _shape(workplane)
    buffer = BytesIO()
    shape.exportBrep(buffer)
    payload = buffer.getvalue()
    if not payload:
        raise WholeProductCollisionMatrixError("B-rep serialization produced no bytes")
    return sha256(payload).hexdigest()


def _bounds(workplane: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = _shape(workplane).BoundingBox()
    return tuple(float(value) for value in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))


def _intersection_and_distance(
    left: cq.Workplane,
    right: cq.Workplane,
) -> tuple[float, float, str]:
    a = _shape(left)
    b = _shape(right)
    intersection = abs(float(a.intersect(b).Volume()))
    if not math.isfinite(intersection):
        raise WholeProductCollisionMatrixError("intersection volume must remain finite")
    if intersection <= KERNEL_VOLUME_EPS_MM3:
        intersection = 0.0
    distance = float(a.distance(b))
    if not math.isfinite(distance) or distance < 0.0:
        raise WholeProductCollisionMatrixError("minimum distance must be finite and nonnegative")
    if distance <= KERNEL_DISTANCE_EPS_MM:
        distance = 0.0
    if intersection > 0.0:
        return intersection, distance, INTERFERENCE
    if distance == 0.0:
        return 0.0, 0.0, TOUCHING
    return 0.0, distance, CLEAR


def _route_service_aabb(route: RealizedWasteRoute) -> cq.Workplane:
    route.validate()
    lower, upper = route.bounds_xyz_mm
    radius = route.service_envelope_radius_mm
    mins = tuple(float(value) - radius for value in lower)
    maxs = tuple(float(value) + radius for value in upper)
    sizes = tuple(maxs[index] - mins[index] for index in range(3))
    center = tuple((mins[index] + maxs[index]) / 2.0 for index in range(3))
    solid = cq.Workplane("XY").box(*sizes, centered=(True, True, True)).translate(center)
    _shape(solid)
    return solid


def _protected_prism(zone: PlanarProtectedZone, zmin: float, zmax: float) -> cq.Workplane:
    if not math.isfinite(zmin) or not math.isfinite(zmax) or zmax <= zmin:
        raise WholeProductCollisionMatrixError("protected-prism Z span must be finite and positive")
    depth = zmax - zmin
    base = cq.Workplane("XY").workplane(offset=zmin).center(zone.center.x, zone.center.y)
    if zone.shape == "CIRCLE":
        result = base.circle(zone.envelope_width_mm / 2.0).extrude(depth)
    elif zone.shape == "ELLIPSE":
        result = base.ellipse(zone.envelope_width_mm / 2.0, zone.envelope_height_mm / 2.0).extrude(depth)
    else:
        raise WholeProductCollisionMatrixError(f"unsupported protected-zone shape {zone.shape!r}")
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
        _git_sha(self.source_main_sha, label="source main")
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise WholeProductCollisionMatrixError("collision matrix is stale for its released-main source")
        if self.authority_revision != AUTHORITY_REVISION:
            raise WholeProductCollisionMatrixError("authority revision changed")
        if self.world_frame_id != WORLD_FRAME_ID:
            raise WholeProductCollisionMatrixError("collision matrix must use authority world frame")
        if self.source_blobs != SOURCE_BLOBS:
            raise WholeProductCollisionMatrixError("collision source blob set changed")
        for path, digest in self.source_blobs:
            if type(path) is not str or not path:
                raise WholeProductCollisionMatrixError("source path must be exact nonblank text")
            _git_sha(digest, label=f"source blob {path}")

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
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        _require_text(self.participant_id, label="participant ID")
        _require_text(self.category, label="participant category")
        _require_text(self.source_id, label="participant source ID")
        _require_text(self.evidence_status, label="participant evidence status")
        _shape(self.geometry)
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WholeProductCollisionMatrixError("digital collision participant cannot be physical evidence")

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
            ("check ID", self.check_id),
            ("left ID", self.left_id),
            ("right ID", self.right_id),
            ("method", self.method),
            ("status", self.status),
            ("evidence status", self.evidence_status),
        ):
            _require_text(value, label=label)
        if self.status not in {CLEAR, INTERFERENCE, TOUCHING, BLOCKED}:
            raise WholeProductCollisionMatrixError("collision status is uncontrolled")
        if self.status == BLOCKED:
            if self.intersection_volume_mm3 is not None or self.minimum_distance_mm is not None:
                raise WholeProductCollisionMatrixError("blocked collision row cannot invent geometry metrics")
        else:
            if self.intersection_volume_mm3 is None or self.minimum_distance_mm is None:
                raise WholeProductCollisionMatrixError("geometric collision row requires exact metrics")
            if self.intersection_volume_mm3 < 0.0 or self.minimum_distance_mm < 0.0:
                raise WholeProductCollisionMatrixError("collision metrics must be nonnegative")

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
    min_x_mm: float
    max_x_mm: float
    min_y_mm: float
    max_y_mm: float
    sampled_plane_min_z_mm: float
    sampled_plane_max_z_mm: float
    evidence_status: str

    def manifest(self) -> dict[str, object]:
        return {
            "zone_id": self.zone_id,
            "pose_count": self.pose_count,
            "aggregate_sampled_boundary_bounds_mm": [
                self.min_x_mm,
                self.max_x_mm,
                self.min_y_mm,
                self.max_y_mm,
                self.sampled_plane_min_z_mm,
                self.sampled_plane_max_z_mm,
            ],
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
        if len(ids) != len(set(ids)) or not ids:
            raise WholeProductCollisionMatrixError("participant IDs must be complete and unique")
        check_ids = tuple(item.check_id for item in self.checks)
        if len(check_ids) != len(set(check_ids)) or not check_ids:
            raise WholeProductCollisionMatrixError("collision check IDs must be complete and unique")
        known = set(ids)
        for check in self.checks:
            if check.status != BLOCKED and (check.left_id not in known or check.right_id not in known):
                raise WholeProductCollisionMatrixError("geometric collision row references unknown participant")
        unresolved_ids = tuple(item.interface_id for item in self.unresolved_interfaces)
        if len(unresolved_ids) != len(set(unresolved_ids)):
            raise WholeProductCollisionMatrixError("unresolved interface IDs cannot repeat")
        if self.observed_candidates != OBSERVED_CANDIDATES:
            raise WholeProductCollisionMatrixError("candidate navigation snapshot changed inside this frozen matrix")
        for _, number, head in self.observed_candidates:
            if type(number) is not int or number <= 0:
                raise WholeProductCollisionMatrixError("candidate PR number must be a positive integer")
            _git_sha(head, label="observed candidate head")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WholeProductCollisionMatrixError("collision matrix cannot become physical validation evidence")
        if self.evidence_status != DIGITAL_ONLY:
            raise WholeProductCollisionMatrixError("collision matrix evidence firewall changed")

    @property
    def exact_interference_count(self) -> int:
        return sum(item.status == INTERFERENCE for item in self.checks)

    @property
    def blocked_count(self) -> int:
        return sum(item.status == BLOCKED for item in self.checks)

    @property
    def review_required_count(self) -> int:
        return sum(item.status == TOUCHING for item in self.checks)

    @property
    def matrix_status(self) -> str:
        if self.exact_interference_count:
            return "DIGITAL_INTERFERENCE_PRESENT_RELEASE_BLOCKED"
        if self.review_required_count or self.blocked_count:
            return "NO_EXACT_INTERFERENCE_IN_CHECKED_PAIRS_BUT_MATRIX_INCOMPLETE"
        return "CHECKED_DIGITAL_PAIRS_CLEAR_PHYSICAL_VALIDATION_STILL_REQUIRED"

    @property
    def matrix_sha256(self) -> str:
        payload = self.manifest(include_sha=False)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
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
            "review_required_count": self.review_required_count,
            "blocked_count": self.blocked_count,
            "matrix_status": self.matrix_status,
            "physical_validation_eligible": False,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            payload["matrix_sha256"] = sha256(raw).hexdigest()
        return payload


def _participant(component: Component, *, participant_id: str | None = None) -> CollisionParticipant:
    return CollisionParticipant(
        participant_id=participant_id or component.name,
        category=CATEGORY_RIGID,
        source_id=f"model:{component.name}",
        geometry=component.solid,
        evidence_status=f"RELEASED_MAIN_COMPONENT_STATUS:{component.status}",
    )


def _exact_check(
    check_id: str,
    left: CollisionParticipant,
    right: CollisionParticipant,
    *,
    method: str = METHOD_BREP,
    evidence_status: str = "DIGITAL_BREP_NARROW_PHASE_ONLY",
) -> CollisionCheck:
    intersection, distance, status = _intersection_and_distance(left.geometry, right.geometry)
    return CollisionCheck(
        check_id,
        left.participant_id,
        right.participant_id,
        method,
        status,
        intersection,
        distance,
        evidence_status,
    )


def _protected_check(
    participant: CollisionParticipant,
    zone: PlanarProtectedZone,
) -> CollisionCheck:
    xmin, xmax, ymin, ymax, zmin, zmax = _bounds(participant.geometry)
    del xmin, xmax, ymin, ymax
    prism = CollisionParticipant(
        participant_id=f"PROTECTED:{zone.zone_id}:FOR:{participant.participant_id}",
        category=CATEGORY_PROTECTED,
        source_id=zone.zone_id,
        geometry=_protected_prism(zone, zmin, zmax),
        evidence_status=(
            "AUTHORITY_DERIVED_XY_HARD_ENVELOPE_EXTRUDED_ONLY_ACROSS_TESTED_SOLID_Z_SPAN;"
            "PROTECTED_VOLUME_Z_POLICY_REMAINS_UNBOUNDED"
        ),
    )
    intersection, distance, status = _intersection_and_distance(participant.geometry, prism.geometry)
    return CollisionCheck(
        check_id=f"PROTECTED::{participant.participant_id}::{zone.zone_id}",
        left_id=participant.participant_id,
        right_id=prism.participant_id,
        method=METHOD_PROTECTED,
        status=status,
        intersection_volume_mm3=intersection,
        minimum_distance_mm=distance,
        evidence_status=(
            "EXACT_FOR_CURRENT_SOLID_AGAINST_AUTHORITY_XY_FOOTPRINT;"
            "NOT_REGISTERED_DYNAMIC_3D_ANATOMY_OR_PHYSICAL_FIT_EVIDENCE"
        ),
    )


def _dynamic_screens(model: MasckOneModel) -> tuple[DynamicProtectedScreen, ...]:
    bounds = protected_zone_regression_bounds(
        model.protected_volumes,
        model.worn_pose_regression,
        boundary_samples=32,
    )
    result: list[DynamicProtectedScreen] = []
    for volume in model.protected_volumes.all:
        selected = tuple(item for item in bounds if item.zone_id == volume.zone.zone_id)
        if len(selected) != model.worn_pose_regression.pose_count:
            raise WholeProductCollisionMatrixError("worn-pose protected screen lost pose coverage")
        result.append(
            DynamicProtectedScreen(
                zone_id=volume.zone.zone_id,
                pose_count=len(selected),
                min_x_mm=min(item.min_x_mm for item in selected),
                max_x_mm=max(item.max_x_mm for item in selected),
                min_y_mm=min(item.min_y_mm for item in selected),
                max_y_mm=max(item.max_y_mm for item in selected),
                sampled_plane_min_z_mm=min(item.min_z_mm for item in selected),
                sampled_plane_max_z_mm=max(item.max_z_mm for item in selected),
                evidence_status=(
                    "DETERMINISTIC_DISCRETE_WORN_POSE_BOUNDARY_SCREEN_ONLY;"
                    "SOURCE_PROTECTED_Z_EXTENT_UNBOUNDED_AND_MEASURED_DONNING_DISTRIBUTION_UNAVAILABLE"
                ),
            )
        )
    return tuple(result)


def _blocked_rows() -> tuple[CollisionCheck, ...]:
    definitions = (
        (
            "BLOCKED::RIGHT_RELEASE_OPERATIONAL_MOTION::WHOLE_PRODUCT",
            "RIGHT_RELEASE_OPERATIONAL_MOTION",
            "WHOLE_PRODUCT_RELEASED_GEOMETRY",
            "Cell 3 / Cell 1 mechanism candidate exists but is not released on current main",
        ),
        (
            "BLOCKED::RIGHT_RELEASE_FACTORY_MOTION::WHOLE_PRODUCT",
            "RIGHT_RELEASE_FACTORY_MOTION",
            "WHOLE_PRODUCT_RELEASED_GEOMETRY",
            "factory motion B-rep is candidate-only and cannot be promoted into released collision truth",
        ),
        (
            "BLOCKED::HARNESS::WET_SYSTEM_AND_MECHANISM",
            "HARNESS",
            "WET_SYSTEM_AND_MECHANISM",
            "no current released harness centerline, bundle diameter, strain-relief or flex envelope",
        ),
        (
            "BLOCKED::CARTRIDGE_SERVICE_MOTION::WHOLE_PRODUCT",
            "CARTRIDGE_SERVICE_MOTION",
            "WHOLE_PRODUCT_RELEASED_GEOMETRY",
            "released cartridge architecture leaves insertion/removal trajectory and service clearance unresolved",
        ),
        (
            "BLOCKED::USER_HAND_SERVICE_KEEP_OUT::HMI_RELEASE_CARTRIDGE",
            "USER_HAND_SERVICE_KEEP_OUT",
            "HMI_RELEASE_CARTRIDGE",
            "no authority-backed hand anthropometry, wet grip envelope or service hand trajectory is released",
        ),
        (
            "BLOCKED::PHYSICAL_HMI::WET_ROUTE_AND_USER_HAND",
            "PHYSICAL_HMI",
            "WET_ROUTE_AND_USER_HAND",
            "physical HMI geometry is not released and legacy Manual-B geometry is not authority",
        ),
    )
    return tuple(
        CollisionCheck(
            check_id=check_id,
            left_id=left,
            right_id=right,
            method=METHOD_UNRESOLVED,
            status=BLOCKED,
            intersection_volume_mm3=None,
            minimum_distance_mm=None,
            evidence_status=reason,
        )
        for check_id, left, right, reason in definitions
    )


def _unresolved_interfaces() -> tuple[UnresolvedInterface, ...]:
    return (
        UnresolvedInterface(
            "RIGHT_RELEASE_OPERATIONAL_MOTION",
            "retention/emergency release",
            "PR71 + Cell1 PR84 exact observed heads only",
            ("protected regions", "mixed-waste routes", "shell", "actuators", "water", "cartridge", "battery"),
            "candidate B-reps are not released on main",
        ),
        UnresolvedInterface(
            "HARNESS",
            "power/electrical harness",
            None,
            ("wet routes", "service motions", "retention mechanism", "protected regions", "shell"),
            "no released routed harness geometry or flex/service envelope",
        ),
        UnresolvedInterface(
            "CARTRIDGE_SERVICE_MOTION",
            "waste cartridge service",
            None,
            ("shell", "routes", "harness", "user hand", "retention"),
            "cartridge insertion/removal trajectory and clearance remain explicitly unresolved",
        ),
        UnresolvedInterface(
            "USER_HAND_SERVICE_KEEP_OUT",
            "user service / wet one-hand interaction",
            None,
            ("physical HMI", "quick release", "cartridge service", "wet routes"),
            "no controlled hand anthropometry or service trajectory source exists",
        ),
        UnresolvedInterface(
            "PHYSICAL_HMI",
            "physical HMI",
            None,
            ("user hand", "wet routes", "harness", "shell"),
            "no current released HMI geometry; legacy PR64 is source material only",
        ),
    )


def build_whole_product_collision_matrix(
    model: MasckOneModel | None = None,
) -> WholeProductCollisionMatrix:
    model = model or build_model()
    if type(model) is not MasckOneModel:
        raise WholeProductCollisionMatrixError("collision matrix requires exact MasckOneModel")
    if str(model.authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise WholeProductCollisionMatrixError("model authority revision is stale")

    rigid = (
        _participant(model.shell),
        *tuple(_participant(item) for item in model.actuator_envelopes),
        _participant(model.water_reservoir_envelope),
        _participant(model.waste_cartridge_envelope),
        _participant(model.battery_reference_envelope),
    )

    release = build_current_cell4_waste_backbone_release()
    route_participants = tuple(
        CollisionParticipant(
            participant_id=f"WASTE_ROUTE_SERVICE::{route.route_id}",
            category=CATEGORY_ROUTE,
            source_id=route.route_id,
            geometry=_route_service_aabb(route),
            evidence_status=(
                "CONSERVATIVE_AABB_FROM_RELEASED_ROUTE_BOUNDS_PLUS_ROUTE_OWNED_SERVICE_ENVELOPE_RADIUS;"
                "NOT_SELECTED_TUBING_CHANNEL_OR_PHYSICAL_SERVICE_CLEARANCE"
            ),
        )
        for route in release.realization.routes
    )
    participants = rigid + route_participants

    checks: list[CollisionCheck] = []
    # Package/package exact narrow phase. Shell-to-package and package-to-package collisions
    # are not exempted; detected interference is surfaced rather than normalized away.
    for left_index, left in enumerate(rigid):
        for right in rigid[left_index + 1 :]:
            checks.append(_exact_check(f"BREP::{left.participant_id}::{right.participant_id}", left, right))

    # Route service reservations against all current rigid/package geometry.
    for route in route_participants:
        for obstacle in rigid:
            checks.append(
                _exact_check(
                    f"ROUTE::{route.participant_id}::{obstacle.participant_id}",
                    route,
                    obstacle,
                    evidence_status=(
                        "CONSERVATIVE_ROUTE_SERVICE_AABB_VS_RELEASED_BREP;"
                        "CLEARANCE_RESULT_IS_DIGITAL_RESERVATION_ONLY"
                    ),
                )
            )

    # Rigid/package and route reservations against the authority-derived protected XY
    # hard envelopes. Each generated prism is temporary check geometry and is not a new
    # product participant/source of truth.
    protected_targets = rigid + route_participants
    for participant in protected_targets:
        for volume in model.protected_volumes.all:
            checks.append(_protected_check(participant, volume.zone))

    checks.extend(_blocked_rows())

    matrix = WholeProductCollisionMatrix(
        binding=SourceBinding(
            SOURCE_MAIN_SHA,
            AUTHORITY_REVISION,
            WORLD_FRAME_ID,
            SOURCE_BLOBS,
        ),
        participants=participants,
        checks=tuple(checks),
        dynamic_protected_screens=_dynamic_screens(model),
        unresolved_interfaces=_unresolved_interfaces(),
        observed_candidates=OBSERVED_CANDIDATES,
    )
    matrix.validate()
    return matrix


def _review_protected_prisms(
    protected: ProtectedVolumeSet,
    participants: tuple[CollisionParticipant, ...],
) -> tuple[cq.Workplane, ...]:
    zmins = []
    zmaxs = []
    for item in participants:
        *_, zmin, zmax = _bounds(item.geometry)
        zmins.append(zmin)
        zmaxs.append(zmax)
    zmin = min(zmins)
    zmax = max(zmaxs)
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

    rigid_shapes = [
        item.geometry.val()
        for item in matrix.participants
        if item.category == CATEGORY_RIGID
    ]
    route_shapes = [
        item.geometry.val()
        for item in matrix.participants
        if item.category == CATEGORY_ROUTE
    ]
    protected_shapes = [item.val() for item in _review_protected_prisms(model.protected_volumes, matrix.participants)]

    for name, shapes in (
        ("whole_product_collision_rigid_package_reference.step", rigid_shapes),
        ("whole_product_collision_waste_service_aabbs_reference.step", route_shapes),
        ("whole_product_collision_protected_prisms_reference.step", protected_shapes),
    ):
        if not shapes:
            raise WholeProductCollisionMatrixError(f"{name} requires review geometry")
        path = output / name
        cq.exporters.export(cq.Compound.makeCompound(shapes), str(path))
        paths.append(path)

    manifest_path = output / "whole_product_collision_matrix_v1.json"
    manifest_path.write_text(json.dumps(matrix.manifest(), indent=2) + "\n", encoding="utf-8")
    paths.append(manifest_path)
    return tuple(paths)
