from __future__ import annotations

"""Manual-A-owned structural, actuation-mount and retention/release CAD.

This module intentionally does not own exterior, fluid, electronics, HMI or thermal
geometry.  It binds to the released model as a source, realizes only Manual A
mechanics, and reports digital collision evidence without promoting it to physical
fit, force, comfort, fatigue or release-time validation.
"""

from dataclasses import dataclass
import hashlib
import json
import math

import cadquery as cq

from .authority import Authority, load_authority
from .model import Component, MasckOneModel, build_model
from .spatial import Point3


SCHEMA = "MASCK_ONE_MANUAL_A_MECHANICAL_STRUCTURE_V1"
CANONICAL_FRAME_ID = "MASCK_ONE_CANONICAL_XYZ"
DIGITAL_ONLY = "DIGITAL_CAD_ONLY_NOT_PHYSICAL_VALIDATION"

# Manual-A candidate dimensions.  These are not authority values and may move during
# DFM/tolerance convergence.  Product requirements continue to come from Authority.
FRAME_MEMBER_RADIAL_MM = 6.0
FRAME_DEPTH_MM = 2.4
FRAME_Z_REAR_MM = -4.0
HALO_OUTER_XY_MM = (162.0, 194.0)
HALO_MEMBER_RADIAL_MM = 4.0
HALO_DEPTH_MM = 4.0
HALO_Z_REAR_MM = -46.0
YOKE_X_MM = 77.0
YOKE_WIDTH_MM = 5.0
YOKE_HEIGHT_MM = 12.0

ACTUATOR_DIAMETER_MM = 10.2
ACTUATOR_LENGTH_MM = 18.7
ACTUATOR_MOUNT_OUTER_DIAMETER_MM = 12.6
ACTUATOR_MOUNT_INNER_DIAMETER_MM = 10.6
ACTUATOR_MOUNT_LENGTH_MM = 4.0
ACTUATOR_SHOE_XY_MM = 12.0
ACTUATOR_SHOE_DEPTH_MM = 4.0
ACTUATOR_SHOE_Z_MM = -2.5

# Candidate origins deliberately move the released development envelopes away from the
# central protected footprints while staying inside the authority-backed XY package.
ACTUATOR_ZONE_CANDIDATES = (
    ("ACTUATOR_ZONE_SUPERIOR_LEFT", Point3(-60.0, 66.0, 2.0), +1.0),
    ("ACTUATOR_ZONE_SUPERIOR_RIGHT", Point3(60.0, 66.0, 2.0), -1.0),
    ("ACTUATOR_ZONE_INFERIOR_LEFT", Point3(-58.0, -60.0, 2.0), +1.0),
    ("ACTUATOR_ZONE_INFERIOR_RIGHT", Point3(58.0, -60.0, 2.0), -1.0),
)

# Left side is a captive pivot reservation.  Right side is the unpowered release.
RELEASE_SOCKET_XYZ_MM = (12.0, 18.0, 13.0)
RELEASE_SOCKET_CENTER_Z_MM = -17.5
RELEASE_TONGUE_XYZ_MM = (4.6, 8.6, 14.0)
RELEASE_TONGUE_CENTER_Z_MM = -22.0
RELEASE_CHANNEL_XYZ_MM = (5.4, 9.4, 15.0)
RELEASE_DOG_RADIUS_MM = 1.5
RELEASE_BORE_RADIUS_MM = 1.8
RELEASE_DOG_LENGTH_MM = 18.0
RELEASE_DOG_Z_MM = -19.0
RELEASE_DOG_TRAVEL_MM = 14.0
RELEASE_GRIP_XYZ_MM = (7.0, 12.0, 8.0)
RELEASE_GRIP_CENTER_X_MM = 88.5
RELEASE_GUARD_XYZ_MM = (10.0, 3.0, 10.0)
RELEASE_GUARD_Y_MM = 8.5


class MechanicalStructureError(ValueError):
    pass


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise MechanicalStructureError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise MechanicalStructureError(f"{label} must be finite")
    return 0.0 if result == 0.0 else result


def _positive(value: object, label: str) -> float:
    result = _finite(value, label)
    if result <= 0.0:
        raise MechanicalStructureError(f"{label} must be positive")
    return result


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value.strip() or value != value.strip():
        raise MechanicalStructureError(f"{label} must be exact nonblank text")
    return value


def _box(x_mm: float, y_mm: float, z_mm: float, center: tuple[float, float, float]) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(_positive(x_mm, "box x"), _positive(y_mm, "box y"), _positive(z_mm, "box z"), centered=(True, True, True))
        .translate(center)
    )


def _elliptic_ring(outer_x_mm: float, outer_y_mm: float, radial_mm: float, depth_mm: float, z0_mm: float) -> cq.Workplane:
    outer_x = _positive(outer_x_mm, "ring outer x")
    outer_y = _positive(outer_y_mm, "ring outer y")
    radial = _positive(radial_mm, "ring radial")
    depth = _positive(depth_mm, "ring depth")
    inner_x = outer_x - 2.0 * radial
    inner_y = outer_y - 2.0 * radial
    if inner_x <= 0.0 or inner_y <= 0.0:
        raise MechanicalStructureError("ring member consumes aperture")
    outer = cq.Workplane("XY").workplane(offset=z0_mm).ellipse(outer_x / 2.0, outer_y / 2.0).extrude(depth)
    cutter = cq.Workplane("XY").workplane(offset=z0_mm - 0.5).ellipse(inner_x / 2.0, inner_y / 2.0).extrude(depth + 1.0)
    return outer.cut(cutter)


def _cylinder_x(radius_mm: float, length_mm: float, center: tuple[float, float, float]) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .circle(_positive(radius_mm, "x-cylinder radius"))
        .extrude(_positive(length_mm, "x-cylinder length"), both=True)
        .rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 90.0)
        .translate(center)
    )


def _actuator_solid(origin: Point3, sign: float, angle_deg: float, *, diameter_mm: float = ACTUATOR_DIAMETER_MM, length_mm: float = ACTUATOR_LENGTH_MM) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .circle(_positive(diameter_mm, "actuator diameter") / 2.0)
        .extrude(_positive(length_mm, "actuator length"))
        .rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), _finite(sign, "actuator sign") * _finite(angle_deg, "actuator angle"))
        .translate(origin.as_tuple())
    )


def _actuator_mount_collar(origin: Point3, sign: float, angle_deg: float) -> cq.Workplane:
    outer = _actuator_solid(
        origin,
        sign,
        angle_deg,
        diameter_mm=ACTUATOR_MOUNT_OUTER_DIAMETER_MM,
        length_mm=ACTUATOR_MOUNT_LENGTH_MM,
    )
    inner = _actuator_solid(
        origin,
        sign,
        angle_deg,
        diameter_mm=ACTUATOR_MOUNT_INNER_DIAMETER_MM,
        length_mm=ACTUATOR_MOUNT_LENGTH_MM + 1.0,
    )
    return outer.cut(inner)


def _intersection_volume_mm3(a: cq.Workplane, b: cq.Workplane) -> float:
    volume = float(a.val().intersect(b.val()).Volume())
    if not math.isfinite(volume) or volume < 0.0:
        raise MechanicalStructureError("intersection volume must be finite and nonnegative")
    return 0.0 if volume < 1e-8 else volume


def _shape_signature(component: Component) -> dict[str, object]:
    solid = component.solid.val()
    bb = solid.BoundingBox()
    return {
        "name": component.name,
        "status": component.status,
        "volume_mm3": round(float(solid.Volume()), 6),
        "bounds_mm": [
            round(float(bb.xmin), 6), round(float(bb.xmax), 6),
            round(float(bb.ymin), 6), round(float(bb.ymax), 6),
            round(float(bb.zmin), 6), round(float(bb.zmax), 6),
        ],
    }


def _source_sha(model: MasckOneModel) -> str:
    payload = {
        "shell": _shape_signature(model.shell),
        "actuators": [_shape_signature(component) for component in model.actuator_envelopes],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _protected_keepout_solid(model: MasckOneModel, index: int) -> tuple[str, cq.Workplane]:
    volume = model.protected_volumes.all[index]
    zone = volume.zone
    wp = cq.Workplane("XY").workplane(offset=-60.0).center(zone.center.x, zone.center.y)
    if zone.shape == "CIRCLE":
        solid = wp.circle(zone.envelope_width_mm / 2.0).extrude(120.0)
    else:
        solid = wp.ellipse(zone.envelope_width_mm / 2.0, zone.envelope_height_mm / 2.0).extrude(120.0)
    if zone.angle_deg:
        solid = solid.rotate((zone.center.x, zone.center.y, 0.0), (zone.center.x, zone.center.y, 1.0), zone.angle_deg)
    return zone.zone_id, solid


@dataclass(frozen=True, slots=True)
class MechanicalPart:
    part_id: str
    solid: cq.Workplane
    role: str
    geometry_status: str
    evidence_status: str = DIGITAL_ONLY

    def __post_init__(self) -> None:
        _text(self.part_id, "part_id")
        _text(self.role, "role")
        _text(self.geometry_status, "geometry_status")
        _text(self.evidence_status, "evidence_status")
        solid = self.solid.val()
        if not solid.isValid() or float(solid.Volume()) <= 0.0:
            raise MechanicalStructureError(f"{self.part_id} must be a valid positive-volume B-rep")

    @property
    def volume_mm3(self) -> float:
        return float(self.solid.val().Volume())

    @property
    def centroid_xyz_mm(self) -> tuple[float, float, float]:
        c = self.solid.val().Center()
        return (float(c.x), float(c.y), float(c.z))

    def manifest(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "role": self.role,
            "geometry_status": self.geometry_status,
            "evidence_status": self.evidence_status,
            "volume_mm3": self.volume_mm3,
            "centroid_xyz_mm": list(self.centroid_xyz_mm),
            "mass_g": None,
            "mass_status": "UNRESOLVED_NO_CONTROLLED_MATERIAL_DENSITY_OR_SUPPLIER_PART_MASS",
        }


@dataclass(frozen=True, slots=True)
class ClearanceResult:
    check_id: str
    moving_id: str
    obstacle_id: str
    state: str
    intersection_volume_mm3: float
    required_clear: bool = True

    def __post_init__(self) -> None:
        for label, value in (("check_id", self.check_id), ("moving_id", self.moving_id), ("obstacle_id", self.obstacle_id), ("state", self.state)):
            _text(value, label)
        value = _finite(self.intersection_volume_mm3, "intersection volume")
        if value < 0.0:
            raise MechanicalStructureError("intersection volume cannot be negative")
        object.__setattr__(self, "intersection_volume_mm3", value)
        if type(self.required_clear) is not bool:
            raise MechanicalStructureError("required_clear must be bool")

    @property
    def passes(self) -> bool:
        return (not self.required_clear) or self.intersection_volume_mm3 == 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "moving_id": self.moving_id,
            "obstacle_id": self.obstacle_id,
            "state": self.state,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "required_clear": self.required_clear,
            "passes": self.passes,
        }


@dataclass(frozen=True, slots=True)
class ActuatorZone:
    zone_id: str
    origin_xyz_mm: tuple[float, float, float]
    sign: float
    angle_doe_deg: tuple[float, ...]
    actuator: MechanicalPart
    mount_collar: MechanicalPart
    reaction_shoe: MechanicalPart

    def manifest(self) -> dict[str, object]:
        return {
            "zone_id": self.zone_id,
            "origin_xyz_mm": list(self.origin_xyz_mm),
            "single_axis_semantics": "ONE_LINEAR_ACTUATOR_AXIS_PER_ZONE;ANGLE_DOE_ROTATES_THE_SAME_AXIS_NOT_A_SECOND_DOF",
            "axis_angle_doe_deg": list(self.angle_doe_deg),
            "actuator": self.actuator.manifest(),
            "mount_collar": self.mount_collar.manifest(),
            "reaction_shoe": self.reaction_shoe.manifest(),
        }


@dataclass(frozen=True, slots=True)
class ReleaseGeometry:
    left_frame_yoke: MechanicalPart
    left_rear_yoke: MechanicalPart
    right_frame_yoke_socket: MechanicalPart
    right_rear_yoke_tongue: MechanicalPart
    dog_and_grip_latched: MechanicalPart
    guard: MechanicalPart
    dog_travel_mm: float
    tongue_channel_clearance_xy_mm: tuple[float, float]
    dog_radial_clearance_mm: float

    def manifest(self) -> dict[str, object]:
        return {
            "left_frame_yoke": self.left_frame_yoke.manifest(),
            "left_rear_yoke": self.left_rear_yoke.manifest(),
            "right_frame_yoke_socket": self.right_frame_yoke_socket.manifest(),
            "right_rear_yoke_tongue": self.right_rear_yoke_tongue.manifest(),
            "dog_and_grip_latched": self.dog_and_grip_latched.manifest(),
            "guard": self.guard.manifest(),
            "dog_travel_mm": self.dog_travel_mm,
            "tongue_channel_clearance_xy_mm": list(self.tongue_channel_clearance_xy_mm),
            "dog_radial_clearance_mm": self.dog_radial_clearance_mm,
            "power_dependency": None,
            "firmware_dependency": None,
            "release_force_N": None,
            "release_time_s": None,
            "release_force_status": "PHYSICAL_VALIDATION_GATE_5_TO_12_N_NOT_MEASURED",
            "release_time_status": "PHYSICAL_VALIDATION_GATE_LE_2_S_NOT_MEASURED",
            "whole_head_removal_status": "BLOCKED_PENDING_COMPLIANT_RETENTION_AND_REPRESENTATIVE_HEADFORM_SWEEP",
        }


@dataclass(frozen=True, slots=True)
class ManualAMechanicalStructure:
    source_authority_revision: str
    source_model_sha256: str
    frame: MechanicalPart
    halo: MechanicalPart
    actuator_zones: tuple[ActuatorZone, ...]
    release: ReleaseGeometry
    clearance_results: tuple[ClearanceResult, ...]
    unresolved_physical_gates: tuple[str, ...]

    @property
    def all_required_clear(self) -> bool:
        return all(item.passes for item in self.clearance_results if item.required_clear)

    @property
    def conflict_ids(self) -> tuple[str, ...]:
        return tuple(item.check_id for item in self.clearance_results if item.required_clear and not item.passes)

    @property
    def package_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def validate_current_sources(self, *, authority: Authority, model: MasckOneModel) -> None:
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise MechanicalStructureError("mechanical structure is stale for current authority revision")
        if self.source_model_sha256 != _source_sha(model):
            raise MechanicalStructureError("mechanical structure is stale for current released shell/actuator references")
        if int(authority.number("actuation", "count")) != len(self.actuator_zones):
            raise MechanicalStructureError("actuator zone count no longer matches authority")

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "coordinate_frame_id": CANONICAL_FRAME_ID,
            "source_authority_revision": self.source_authority_revision,
            "source_model_sha256": self.source_model_sha256,
            "frame": self.frame.manifest(),
            "halo": self.halo.manifest(),
            "actuator_zones": [zone.manifest() for zone in self.actuator_zones],
            "release": self.release.manifest(),
            "clearance_results": [item.manifest() for item in self.clearance_results],
            "all_required_clear": self.all_required_clear,
            "conflict_ids": list(self.conflict_ids),
            "unresolved_physical_gates": list(self.unresolved_physical_gates),
            "physical_validation_eligible": False,
            "evidence_status": "DIGITAL_MECHANICAL_GEOMETRY_COLLISION_AND_CONNECTIVITY_ONLY",
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def _build_release(frame: MechanicalPart, halo: MechanicalPart) -> ReleaseGeometry:
    # Left side remains captive.  It is split into front and rear members so later
    # removal can be represented about a real pivot interface rather than a fake rigid
    # bridge.  Pivot kinematics remain a separate unresolved headform/compliance gate.
    left_front = MechanicalPart(
        "RETENTION_LEFT_FRAME_YOKE",
        _box(12.0, YOKE_HEIGHT_MM, 12.0, (-YOKE_X_MM, 0.0, -8.0)),
        "frame-side left retention member and captive-pivot support",
        "MANUAL_A_CANDIDATE",
    )
    left_rear = MechanicalPart(
        "RETENTION_LEFT_REAR_YOKE",
        _box(YOKE_WIDTH_MM, YOKE_HEIGHT_MM, 20.0, (-YOKE_X_MM, 0.0, -36.0)),
        "halo-side left retention member; pivot lug detail remains bounded reservation",
        "MANUAL_A_CANDIDATE",
    )

    # Right frame-side socket and rear tongue form the actual separable interface.
    front_yoke = _box(YOKE_WIDTH_MM, YOKE_HEIGHT_MM, 12.0, (YOKE_X_MM, 0.0, -8.0))
    socket_outer = _box(*RELEASE_SOCKET_XYZ_MM, (YOKE_X_MM, 0.0, RELEASE_SOCKET_CENTER_Z_MM))
    tongue_channel = _box(*RELEASE_CHANNEL_XYZ_MM, (YOKE_X_MM, 0.0, RELEASE_SOCKET_CENTER_Z_MM))
    bore = _cylinder_x(RELEASE_BORE_RADIUS_MM, 30.0, (YOKE_X_MM, 0.0, RELEASE_DOG_Z_MM))
    socket = front_yoke.union(socket_outer.cut(tongue_channel).cut(bore))
    right_front = MechanicalPart(
        "RETENTION_RIGHT_FRAME_YOKE_SOCKET",
        socket,
        "frame-side right yoke with open tongue channel and transverse release bore",
        "MANUAL_A_CANDIDATE",
    )

    rear_yoke = _box(YOKE_WIDTH_MM, YOKE_HEIGHT_MM, 18.0, (YOKE_X_MM, 0.0, -36.0))
    tongue_raw = _box(*RELEASE_TONGUE_XYZ_MM, (YOKE_X_MM, 0.0, RELEASE_TONGUE_CENTER_Z_MM))
    tongue = tongue_raw.cut(bore)
    right_rear = MechanicalPart(
        "RETENTION_RIGHT_REAR_YOKE_TONGUE",
        rear_yoke.union(tongue),
        "halo-side right yoke with captured tongue and transverse release bore",
        "MANUAL_A_CANDIDATE",
    )

    dog = _cylinder_x(RELEASE_DOG_RADIUS_MM, RELEASE_DOG_LENGTH_MM, (YOKE_X_MM, 0.0, RELEASE_DOG_Z_MM))
    grip = _box(*RELEASE_GRIP_XYZ_MM, (RELEASE_GRIP_CENTER_X_MM, 0.0, RELEASE_DOG_Z_MM))
    dog_grip = MechanicalPart(
        "QUICK_RELEASE_DOG_AND_WET_GRIP",
        dog.union(grip),
        "unpowered transverse capture dog with deliberately external wet-finger grip",
        "MANUAL_A_CANDIDATE",
    )
    upper_guard = _box(*RELEASE_GUARD_XYZ_MM, (87.5, RELEASE_GUARD_Y_MM, RELEASE_DOG_Z_MM))
    lower_guard = _box(*RELEASE_GUARD_XYZ_MM, (87.5, -RELEASE_GUARD_Y_MM, RELEASE_DOG_Z_MM))
    guard = MechanicalPart(
        "QUICK_RELEASE_ACCIDENTAL_ACTUATION_GUARD",
        upper_guard.union(lower_guard),
        "paired guard rails recess the grip without covering its wet-finger access faces",
        "MANUAL_A_CANDIDATE",
    )

    # Geometric connectivity checks are intentionally weaker than load validation.
    if _intersection_volume_mm3(left_front.solid, frame.solid) <= 0.0:
        raise MechanicalStructureError("left frame yoke is not geometrically attached to reaction frame")
    if _intersection_volume_mm3(left_rear.solid, halo.solid) <= 0.0:
        raise MechanicalStructureError("left rear yoke is not geometrically attached to halo")
    if _intersection_volume_mm3(right_front.solid, frame.solid) <= 0.0:
        raise MechanicalStructureError("right frame yoke is not geometrically attached to reaction frame")
    if _intersection_volume_mm3(right_rear.solid, halo.solid) <= 0.0:
        raise MechanicalStructureError("right rear yoke is not geometrically attached to halo")
    if _intersection_volume_mm3(right_front.solid, right_rear.solid) != 0.0:
        raise MechanicalStructureError("right tongue must fit socket without material penetration")
    if _intersection_volume_mm3(dog_grip.solid, right_front.solid) != 0.0 or _intersection_volume_mm3(dog_grip.solid, right_rear.solid) != 0.0:
        raise MechanicalStructureError("release dog must occupy aligned bores without material penetration")

    return ReleaseGeometry(
        left_front,
        left_rear,
        right_front,
        right_rear,
        dog_grip,
        guard,
        RELEASE_DOG_TRAVEL_MM,
        (
            RELEASE_CHANNEL_XYZ_MM[0] - RELEASE_TONGUE_XYZ_MM[0],
            RELEASE_CHANNEL_XYZ_MM[1] - RELEASE_TONGUE_XYZ_MM[1],
        ),
        RELEASE_BORE_RADIUS_MM - RELEASE_DOG_RADIUS_MM,
    )


def build_manual_a_mechanical_structure(
    authority: Authority | None = None,
    model: MasckOneModel | None = None,
) -> ManualAMechanicalStructure:
    authority = authority or load_authority()
    model = model or build_model(authority)
    count = int(authority.number("actuation", "count"))
    if count != 4 or len(model.actuator_envelopes) != 4:
        raise MechanicalStructureError("Manual A structure requires the controlled four-zone actuation architecture")
    angle_doe = tuple(float(value) for value in authority.get("actuation", "clean", "axis_angle_doe_deg"))
    baseline = float(authority.get("actuation", "clean", "axis_angle_baseline_deg"))
    if tuple(sorted(set(angle_doe))) != angle_doe or baseline not in angle_doe:
        raise MechanicalStructureError("actuator angle DOE must be deterministic, unique and contain baseline")

    frame_w, frame_h = authority.pair("geometry", "functional_frame_xy_mm")
    frame = MechanicalPart(
        "FRAME_PERIMETER_REACTION_MEMBER",
        _elliptic_ring(frame_w, frame_h, FRAME_MEMBER_RADIAL_MM, FRAME_DEPTH_MM, FRAME_Z_REAR_MM),
        "closed digital structural member receiving actuator and retention reactions",
        "MANUAL_A_CANDIDATE_CROSS_SECTION_MATERIAL_AND_LOAD_CAPACITY_UNVALIDATED",
    )
    halo = MechanicalPart(
        "RETENTION_HALO_OCCIPITAL_CROWN_MEMBER",
        _elliptic_ring(HALO_OUTER_XY_MM[0], HALO_OUTER_XY_MM[1], HALO_MEMBER_RADIAL_MM, HALO_DEPTH_MM, HALO_Z_REAR_MM),
        "light continuous occipital/crown retention member with bilateral side interfaces",
        "MANUAL_A_CANDIDATE_FIT_COMFORT_PRELOAD_AND_MATERIAL_UNVALIDATED",
    )

    zones: list[ActuatorZone] = []
    for zone_id, origin, sign in ACTUATOR_ZONE_CANDIDATES:
        actuator = MechanicalPart(
            f"{zone_id}_ENVELOPE",
            _actuator_solid(origin, sign, baseline),
            "supplier-size development envelope at Manual-A candidate world datum",
            "MANUAL_A_PACKAGE_CANDIDATE_PRODUCTION_ACTUATOR_NOT_FROZEN",
        )
        collar = MechanicalPart(
            f"{zone_id}_MOUNT_COLLAR",
            _actuator_mount_collar(origin, sign, baseline),
            "coaxial removable mount collar preserving single-axis actuator semantics",
            "MANUAL_A_CANDIDATE",
        )
        shoe = MechanicalPart(
            f"{zone_id}_REACTION_SHOE",
            _box(ACTUATOR_SHOE_XY_MM, ACTUATOR_SHOE_XY_MM, ACTUATOR_SHOE_DEPTH_MM, (origin.x, origin.y, ACTUATOR_SHOE_Z_MM)),
            "local reaction shoe overlapping the perimeter reaction member",
            "MANUAL_A_CANDIDATE_MATERIAL_DEFLECTION_FATIGUE_UNVALIDATED",
        )
        if _intersection_volume_mm3(shoe.solid, frame.solid) <= 0.0:
            raise MechanicalStructureError(f"{zone_id} reaction shoe does not connect to perimeter frame")
        zones.append(ActuatorZone(zone_id, origin.as_tuple(), sign, angle_doe, actuator, collar, shoe))

    release = _build_release(frame, halo)
    keepouts = tuple(_protected_keepout_solid(model, index) for index in range(len(model.protected_volumes.all)))
    results: list[ClearanceResult] = []

    # Full authority angle DOE, not only nominal.  Each state is a fresh B-rep at the
    # same single-axis origin/sign semantics.
    for zone, (_, origin, sign) in zip(zones, ACTUATOR_ZONE_CANDIDATES):
        for angle in angle_doe:
            sweep = _actuator_solid(origin, sign, angle)
            state = f"ANGLE_{angle:g}_DEG"
            for keepout_id, keepout in keepouts:
                results.append(ClearanceResult(
                    f"CLEAR_{zone.zone_id}_{state}_{keepout_id}",
                    zone.zone_id,
                    keepout_id,
                    state,
                    _intersection_volume_mm3(sweep, keepout),
                ))
            results.append(ClearanceResult(
                f"CLEAR_{zone.zone_id}_{state}_RIGID_SHELL",
                zone.zone_id,
                "RIGID_SHELL",
                state,
                _intersection_volume_mm3(sweep, model.shell.solid),
            ))

    # Static Manual-A structure must not enter authority-derived protected XY prisms.
    static_parts = (
        frame,
        halo,
        *(zone.mount_collar for zone in zones),
        *(zone.reaction_shoe for zone in zones),
        release.left_frame_yoke,
        release.left_rear_yoke,
        release.right_frame_yoke_socket,
        release.right_rear_yoke_tongue,
        release.guard,
    )
    for part in static_parts:
        for keepout_id, keepout in keepouts:
            results.append(ClearanceResult(
                f"CLEAR_{part.part_id}_{keepout_id}",
                part.part_id,
                keepout_id,
                "STATIC",
                _intersection_volume_mm3(part.solid, keepout),
            ))

    # Dog/grip sweep is explicitly sampled through the full authored hard-stop travel.
    # The bore is modeled at real diameter, so material intersection with either capture
    # participant is a geometry defect rather than an allowed symbolic overlap.
    for index, offset in enumerate((0.0, 3.5, 7.0, 10.5, RELEASE_DOG_TRAVEL_MM)):
        moving = release.dog_and_grip_latched.solid.translate((offset, 0.0, 0.0))
        state = f"DOG_X_PLUS_{offset:g}_MM"
        for participant in (release.right_frame_yoke_socket, release.right_rear_yoke_tongue):
            results.append(ClearanceResult(
                f"CLEAR_RELEASE_{state}_{participant.part_id}",
                release.dog_and_grip_latched.part_id,
                participant.part_id,
                state,
                _intersection_volume_mm3(moving, participant.solid),
            ))
        for keepout_id, keepout in keepouts:
            results.append(ClearanceResult(
                f"CLEAR_RELEASE_{state}_{keepout_id}",
                release.dog_and_grip_latched.part_id,
                keepout_id,
                state,
                _intersection_volume_mm3(moving, keepout),
            ))

    structure = ManualAMechanicalStructure(
        source_authority_revision=str(authority.get("project", "authority_revision")),
        source_model_sha256=_source_sha(model),
        frame=frame,
        halo=halo,
        actuator_zones=tuple(zones),
        release=release,
        clearance_results=tuple(results),
        unresolved_physical_gates=(
            "FRAME_MATERIAL_DEFLECTION_FIRST_MODE_FATIGUE_AND_LOCAL_BEARING",
            "RETENTION_FIT_COMFORT_PRELOAD_HAIR_INTERACTION_AND_ANTHROPOMETRIC_RANGE",
            "EMERGENCY_RELEASE_FORCE_5_TO_12_N_AND_REMOVAL_TIME_LE_2_S",
            "WHOLE_RETENTION_HEADFORM_REMOVAL_SWEEP_AFTER_DOG_RELEASE",
            "ACTUATOR_FORCE_FATIGUE_ACOUSTIC_AND_LIFETIME",
            "MANUAL_B_EXTERIOR_CANDIDATE_COMPATIBILITY_UNTIL_THAT_GEOMETRY_IS_MERGED",
        ),
    )
    structure.validate_current_sources(authority=authority, model=model)
    return structure
