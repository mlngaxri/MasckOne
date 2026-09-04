from __future__ import annotations

"""Manual-A-owned structural, actuation-mount and retention/release CAD.

This module owns only Manual A mechanics.  Exterior, fluid, electronics, HMI and
thermal geometry remain external dependencies.  The B-reps here are deterministic
candidate geometry and must never be promoted to physical fit, force, comfort,
fatigue or release-time evidence.
"""

from dataclasses import dataclass
import hashlib
import json
import math

import cadquery as cq

from .authority import Authority, load_authority
from .model import Component, MasckOneModel, build_model
from .spatial import Point3


SCHEMA = "MASCK_ONE_MANUAL_A_MECHANICAL_STRUCTURE_V2"
CANONICAL_FRAME_ID = "MASCK_ONE_CANONICAL_XYZ"
DIGITAL_ONLY = "DIGITAL_CAD_ONLY_NOT_PHYSICAL_VALIDATION"
KERNEL_ZERO_VOLUME_MM3 = 1e-8

# Manual-A design-candidate dimensions. These are not authority values.
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
ACTUATOR_ZONE_CANDIDATES = (
    ("ACTUATOR_ZONE_SUPERIOR_LEFT", Point3(-60.0, 66.0, 2.0), +1.0),
    ("ACTUATOR_ZONE_SUPERIOR_RIGHT", Point3(60.0, 66.0, 2.0), -1.0),
    ("ACTUATOR_ZONE_INFERIOR_LEFT", Point3(-58.0, -60.0, 2.0), +1.0),
    ("ACTUATOR_ZONE_INFERIOR_RIGHT", Point3(58.0, -60.0, 2.0), -1.0),
)

# Captive left pivot and separable right release.
PIVOT_BORE_RADIUS_MM = 1.8
PIVOT_PIN_RADIUS_MM = 1.5
PIVOT_PIN_LENGTH_MM = 18.0
PIVOT_Z_MM = -19.0

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


def _ring(outer_x_mm: float, outer_y_mm: float, radial_mm: float, depth_mm: float, z0_mm: float) -> cq.Workplane:
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


def _cylinder_x(radius_mm: float, total_length_mm: float, center: tuple[float, float, float]) -> cq.Workplane:
    # CadQuery both=True extrudes the requested distance in both directions, so half
    # the requested total length is supplied here.  This prevents a hidden 2x latch.
    half = _positive(total_length_mm, "x-cylinder total length") / 2.0
    return (
        cq.Workplane("XY")
        .circle(_positive(radius_mm, "x-cylinder radius"))
        .extrude(half, both=True)
        .rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 90.0)
        .translate(center)
    )


def _cylinder_y(radius_mm: float, total_length_mm: float, center: tuple[float, float, float]) -> cq.Workplane:
    half = _positive(total_length_mm, "y-cylinder total length") / 2.0
    return (
        cq.Workplane("XY")
        .circle(_positive(radius_mm, "y-cylinder radius"))
        .extrude(half, both=True)
        .rotate((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 90.0)
        .translate(center)
    )


def _actuator(origin: Point3, sign: float, angle_deg: float, diameter_mm: float = ACTUATOR_DIAMETER_MM, length_mm: float = ACTUATOR_LENGTH_MM) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .circle(_positive(diameter_mm, "actuator diameter") / 2.0)
        .extrude(_positive(length_mm, "actuator length"))
        .rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), _finite(sign, "axis sign") * _finite(angle_deg, "axis angle"))
        .translate(origin.as_tuple())
    )


def _mount_collar(origin: Point3, sign: float, angle_deg: float) -> cq.Workplane:
    outer = _actuator(origin, sign, angle_deg, ACTUATOR_MOUNT_OUTER_DIAMETER_MM, ACTUATOR_MOUNT_LENGTH_MM)
    inner = _actuator(origin, sign, angle_deg, ACTUATOR_MOUNT_INNER_DIAMETER_MM, ACTUATOR_MOUNT_LENGTH_MM + 1.0)
    return outer.cut(inner)


def _intersection(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise MechanicalStructureError("intersection volume must be finite and nonnegative")
    return 0.0 if value < KERNEL_ZERO_VOLUME_MM3 else value


def _component_signature(component: Component) -> dict[str, object]:
    shape = component.solid.val()
    bb = shape.BoundingBox()
    return {
        "name": component.name,
        "status": component.status,
        "volume_mm3": round(float(shape.Volume()), 6),
        "bounds_mm": [
            round(float(bb.xmin), 6), round(float(bb.xmax), 6),
            round(float(bb.ymin), 6), round(float(bb.ymax), 6),
            round(float(bb.zmin), 6), round(float(bb.zmax), 6),
        ],
    }


def _source_sha(model: MasckOneModel) -> str:
    raw = json.dumps(
        {
            "shell": _component_signature(model.shell),
            "actuators": [_component_signature(component) for component in model.actuator_envelopes],
        },
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _protected_solid(model: MasckOneModel, index: int) -> tuple[str, cq.Workplane]:
    protected = model.protected_volumes.all[index]
    zone = protected.zone
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
        for label, value in (("part_id", self.part_id), ("role", self.role), ("geometry_status", self.geometry_status), ("evidence_status", self.evidence_status)):
            _text(value, label)
        shape = self.solid.val()
        if not shape.isValid() or float(shape.Volume()) <= 0.0:
            raise MechanicalStructureError(f"{self.part_id} must be a valid positive-volume B-rep")

    @property
    def volume_mm3(self) -> float:
        return float(self.solid.val().Volume())

    @property
    def centroid_xyz_mm(self) -> tuple[float, float, float]:
        center = self.solid.val().Center()
        return float(center.x), float(center.y), float(center.z)

    def manifest(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "role": self.role,
            "geometry_status": self.geometry_status,
            "evidence_status": self.evidence_status,
            "volume_mm3": self.volume_mm3,
            "centroid_xyz_mm": list(self.centroid_xyz_mm),
            "mass_g": None,
            "mass_status": "UNRESOLVED_NO_CONTROLLED_MATERIAL_DENSITY_OR_PART_MASS",
        }


@dataclass(frozen=True, slots=True)
class ClearanceResult:
    check_id: str
    moving_id: str
    obstacle_id: str
    state: str
    intersection_volume_mm3: float

    def __post_init__(self) -> None:
        for label, value in (("check_id", self.check_id), ("moving_id", self.moving_id), ("obstacle_id", self.obstacle_id), ("state", self.state)):
            _text(value, label)
        volume = _finite(self.intersection_volume_mm3, "intersection volume")
        if volume < 0.0:
            raise MechanicalStructureError("intersection volume cannot be negative")
        object.__setattr__(self, "intersection_volume_mm3", volume)

    @property
    def passes(self) -> bool:
        return self.intersection_volume_mm3 == 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "moving_id": self.moving_id,
            "obstacle_id": self.obstacle_id,
            "state": self.state,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "passes": self.passes,
        }


@dataclass(frozen=True, slots=True)
class ActuatorZone:
    zone_id: str
    origin_xyz_mm: tuple[float, float, float]
    sign: float
    angle_doe_deg: tuple[float, ...]
    envelope: MechanicalPart
    mount_collar: MechanicalPart
    reaction_shoe: MechanicalPart

    def manifest(self) -> dict[str, object]:
        return {
            "zone_id": self.zone_id,
            "origin_xyz_mm": list(self.origin_xyz_mm),
            "axis_angle_doe_deg": list(self.angle_doe_deg),
            "single_axis_semantics": "ONE_LINEAR_AXIS_PER_ZONE;DOE_ROTATES_THE_SAME_AXIS_NOT_A_SECOND_DOF",
            "envelope": self.envelope.manifest(),
            "mount_collar": self.mount_collar.manifest(),
            "reaction_shoe": self.reaction_shoe.manifest(),
            "hard_stop_status": "BLOCKED_UNTIL_PRODUCTION_MOVING_ELEMENT_AND_ENDSTOP_INTERFACE_ARE_CONTROLLED",
            "replaceability_status": "COLLAR_AND_SHOE_GEOMETRY_DIGITALLY_REMOVABLE;FASTENER_DETAIL_DFM_PENDING",
        }


@dataclass(frozen=True, slots=True)
class ReleaseGeometry:
    left_frame_clevis: MechanicalPart
    left_rear_lug: MechanicalPart
    left_pivot_pin: MechanicalPart
    right_frame_socket: MechanicalPart
    right_rear_tongue: MechanicalPart
    dog_and_grip: MechanicalPart
    guard: MechanicalPart
    dog_travel_mm: float
    tongue_clearance_xy_mm: tuple[float, float]
    dog_radial_clearance_mm: float
    dog_final_clears_tongue: bool

    def manifest(self) -> dict[str, object]:
        return {
            "left_frame_clevis": self.left_frame_clevis.manifest(),
            "left_rear_lug": self.left_rear_lug.manifest(),
            "left_pivot_pin": self.left_pivot_pin.manifest(),
            "right_frame_socket": self.right_frame_socket.manifest(),
            "right_rear_tongue": self.right_rear_tongue.manifest(),
            "dog_and_grip": self.dog_and_grip.manifest(),
            "guard": self.guard.manifest(),
            "dog_travel_mm": self.dog_travel_mm,
            "tongue_clearance_xy_mm": list(self.tongue_clearance_xy_mm),
            "dog_radial_clearance_mm": self.dog_radial_clearance_mm,
            "dog_final_clears_tongue": self.dog_final_clears_tongue,
            "power_dependency": None,
            "firmware_dependency": None,
            "release_force_N": None,
            "release_time_s": None,
            "release_force_status": "PHYSICAL_GATE_5_TO_12_N_NOT_MEASURED",
            "release_time_status": "PHYSICAL_GATE_LE_2_S_NOT_MEASURED",
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
    def conflict_ids(self) -> tuple[str, ...]:
        return tuple(item.check_id for item in self.clearance_results if not item.passes)

    @property
    def all_required_clear(self) -> bool:
        return not self.conflict_ids

    @property
    def package_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def validate_current_sources(self, authority: Authority, model: MasckOneModel) -> None:
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise MechanicalStructureError("mechanical structure is stale for current authority revision")
        if self.source_model_sha256 != _source_sha(model):
            raise MechanicalStructureError("mechanical structure is stale for current released shell/actuator references")
        if int(authority.number("actuation", "count")) != len(self.actuator_zones):
            raise MechanicalStructureError("actuator zone count no longer matches authority")

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
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
            "evidence_status": "DIGITAL_MECHANICAL_GEOMETRY_COLLISION_AND_CAPTURE_ONLY",
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def _release(frame: MechanicalPart, halo: MechanicalPart) -> ReleaseGeometry:
    # Left captive pivot: frame-side clevis, halo-side lug and retained pin.  The slot
    # and pin bores are real voids, not material-overlap proxies for a hinge.
    left_front = _box(12.0, YOKE_HEIGHT_MM, 12.0, (-YOKE_X_MM, 0.0, -8.0))
    clevis_outer = _box(12.0, 18.0, 13.0, (-YOKE_X_MM, 0.0, -17.5))
    clevis_slot = _box(10.0, 5.4, 15.0, (-YOKE_X_MM, 0.0, -17.5))
    pivot_bore = _cylinder_y(PIVOT_BORE_RADIUS_MM, 24.0, (-YOKE_X_MM, 0.0, PIVOT_Z_MM))
    left_clevis = MechanicalPart(
        "RETENTION_LEFT_FRAME_CLEVIS",
        left_front.union(clevis_outer.cut(clevis_slot).cut(pivot_bore)),
        "frame-side captive-pivot clevis",
        "MANUAL_A_CANDIDATE",
    )
    left_rear = _box(YOKE_WIDTH_MM, YOKE_HEIGHT_MM, 18.0, (-YOKE_X_MM, 0.0, -36.0))
    left_lug_raw = _box(8.0, 4.6, 14.0, (-YOKE_X_MM, 0.0, -22.0))
    left_lug = MechanicalPart(
        "RETENTION_LEFT_REAR_PIVOT_LUG",
        left_rear.union(left_lug_raw.cut(pivot_bore)),
        "halo-side pivot lug captured by permanent pin",
        "MANUAL_A_CANDIDATE",
    )
    left_pin = MechanicalPart(
        "RETENTION_LEFT_CAPTIVE_PIVOT_PIN",
        _cylinder_y(PIVOT_PIN_RADIUS_MM, PIVOT_PIN_LENGTH_MM, (-YOKE_X_MM, 0.0, PIVOT_Z_MM)),
        "captive unpowered left pivot pin",
        "MANUAL_A_CANDIDATE_PIN_RETENTION_DETAIL_DFM_PENDING",
    )

    # Right separable interface: frame socket, halo tongue and transverse dog.
    right_front = _box(YOKE_WIDTH_MM, YOKE_HEIGHT_MM, 12.0, (YOKE_X_MM, 0.0, -8.0))
    socket_outer = _box(*RELEASE_SOCKET_XYZ_MM, (YOKE_X_MM, 0.0, RELEASE_SOCKET_CENTER_Z_MM))
    channel = _box(*RELEASE_CHANNEL_XYZ_MM, (YOKE_X_MM, 0.0, RELEASE_SOCKET_CENTER_Z_MM))
    release_bore = _cylinder_x(RELEASE_BORE_RADIUS_MM, 30.0, (YOKE_X_MM, 0.0, RELEASE_DOG_Z_MM))
    right_socket = MechanicalPart(
        "RETENTION_RIGHT_FRAME_SOCKET",
        right_front.union(socket_outer.cut(channel).cut(release_bore)),
        "frame-side separable tongue socket with transverse dog bore",
        "MANUAL_A_CANDIDATE",
    )
    right_rear = _box(YOKE_WIDTH_MM, YOKE_HEIGHT_MM, 18.0, (YOKE_X_MM, 0.0, -36.0))
    tongue_raw = _box(*RELEASE_TONGUE_XYZ_MM, (YOKE_X_MM, 0.0, RELEASE_TONGUE_CENTER_Z_MM))
    right_tongue = MechanicalPart(
        "RETENTION_RIGHT_REAR_TONGUE",
        right_rear.union(tongue_raw.cut(release_bore)),
        "halo-side captured tongue with transverse release bore",
        "MANUAL_A_CANDIDATE",
    )
    dog_only = _cylinder_x(RELEASE_DOG_RADIUS_MM, RELEASE_DOG_LENGTH_MM, (YOKE_X_MM, 0.0, RELEASE_DOG_Z_MM))
    grip = _box(*RELEASE_GRIP_XYZ_MM, (RELEASE_GRIP_CENTER_X_MM, 0.0, RELEASE_DOG_Z_MM))
    dog_grip = MechanicalPart(
        "QUICK_RELEASE_DOG_AND_WET_GRIP",
        dog_only.union(grip),
        "transverse unpowered capture dog with external wet-finger grip",
        "MANUAL_A_CANDIDATE",
    )
    guard = MechanicalPart(
        "QUICK_RELEASE_ACCIDENTAL_ACTUATION_GUARD",
        _box(*RELEASE_GUARD_XYZ_MM, (87.5, RELEASE_GUARD_Y_MM, RELEASE_DOG_Z_MM)).union(
            _box(*RELEASE_GUARD_XYZ_MM, (87.5, -RELEASE_GUARD_Y_MM, RELEASE_DOG_Z_MM))
        ),
        "paired guard rails recessing the grip while retaining bilateral finger access",
        "MANUAL_A_CANDIDATE",
    )

    if _intersection(left_clevis.solid, frame.solid) <= 0.0:
        raise MechanicalStructureError("left clevis does not attach to frame")
    if _intersection(left_lug.solid, halo.solid) <= 0.0:
        raise MechanicalStructureError("left pivot lug does not attach to halo")
    if _intersection(right_socket.solid, frame.solid) <= 0.0:
        raise MechanicalStructureError("right socket does not attach to frame")
    if _intersection(right_tongue.solid, halo.solid) <= 0.0:
        raise MechanicalStructureError("right tongue does not attach to halo")
    if _intersection(left_clevis.solid, left_lug.solid) != 0.0:
        raise MechanicalStructureError("left pivot lug penetrates clevis material")
    if _intersection(left_pin.solid, left_clevis.solid) != 0.0 or _intersection(left_pin.solid, left_lug.solid) != 0.0:
        raise MechanicalStructureError("left pivot pin must occupy aligned bores without material penetration")
    if _intersection(right_socket.solid, right_tongue.solid) != 0.0:
        raise MechanicalStructureError("right tongue penetrates socket material")
    if _intersection(dog_grip.solid, right_socket.solid) != 0.0 or _intersection(dog_grip.solid, right_tongue.solid) != 0.0:
        raise MechanicalStructureError("release dog must occupy aligned bores without material penetration")

    final_dog = dog_only.translate((RELEASE_DOG_TRAVEL_MM, 0.0, 0.0)).val().BoundingBox()
    tongue_bb = right_tongue.solid.val().BoundingBox()
    dog_clears = float(final_dog.xmin) > float(tongue_bb.xmax) + KERNEL_ZERO_VOLUME_MM3
    if not dog_clears:
        raise MechanicalStructureError("authored dog travel does not fully clear right tongue")

    return ReleaseGeometry(
        left_clevis,
        left_lug,
        left_pin,
        right_socket,
        right_tongue,
        dog_grip,
        guard,
        RELEASE_DOG_TRAVEL_MM,
        (RELEASE_CHANNEL_XYZ_MM[0] - RELEASE_TONGUE_XYZ_MM[0], RELEASE_CHANNEL_XYZ_MM[1] - RELEASE_TONGUE_XYZ_MM[1]),
        RELEASE_BORE_RADIUS_MM - RELEASE_DOG_RADIUS_MM,
        dog_clears,
    )


def build_manual_a_mechanical_structure(authority: Authority | None = None, model: MasckOneModel | None = None) -> ManualAMechanicalStructure:
    authority = authority or load_authority()
    model = model or build_model(authority)
    if int(authority.number("actuation", "count")) != 4 or len(model.actuator_envelopes) != 4:
        raise MechanicalStructureError("controlled architecture must contain four independent actuator zones")
    angle_doe = tuple(float(value) for value in authority.get("actuation", "clean", "axis_angle_doe_deg"))
    baseline = float(authority.get("actuation", "clean", "axis_angle_baseline_deg"))
    if tuple(sorted(set(angle_doe))) != angle_doe or baseline not in angle_doe:
        raise MechanicalStructureError("actuator angle DOE must be unique, ascending and contain baseline")

    frame_w, frame_h = authority.pair("geometry", "functional_frame_xy_mm")
    frame = MechanicalPart(
        "FRAME_PERIMETER_REACTION_MEMBER",
        _ring(frame_w, frame_h, FRAME_MEMBER_RADIAL_MM, FRAME_DEPTH_MM, FRAME_Z_REAR_MM),
        "closed digital perimeter receiving actuator and retention reactions",
        "MANUAL_A_CANDIDATE_MATERIAL_DEFLECTION_MODAL_FATIGUE_UNVALIDATED",
    )
    halo = MechanicalPart(
        "RETENTION_HALO_OCCIPITAL_CROWN_MEMBER",
        _ring(*HALO_OUTER_XY_MM, HALO_MEMBER_RADIAL_MM, HALO_DEPTH_MM, HALO_Z_REAR_MM),
        "continuous visually light occipital/crown member with bilateral side interfaces",
        "MANUAL_A_CANDIDATE_FIT_COMFORT_PRELOAD_MATERIAL_UNVALIDATED",
    )

    zones: list[ActuatorZone] = []
    for zone_id, origin, sign in ACTUATOR_ZONE_CANDIDATES:
        envelope = MechanicalPart(
            f"{zone_id}_ENVELOPE",
            _actuator(origin, sign, baseline),
            "supplier-size envelope at Manual-A world datum",
            "MANUAL_A_PACKAGE_CANDIDATE_PRODUCTION_ACTUATOR_NOT_FROZEN",
        )
        collar = MechanicalPart(
            f"{zone_id}_MOUNT_COLLAR",
            _mount_collar(origin, sign, baseline),
            "coaxial removable mount collar preserving single-axis semantics",
            "MANUAL_A_CANDIDATE",
        )
        shoe = MechanicalPart(
            f"{zone_id}_REACTION_SHOE",
            _box(ACTUATOR_SHOE_XY_MM, ACTUATOR_SHOE_XY_MM, ACTUATOR_SHOE_DEPTH_MM, (origin.x, origin.y, ACTUATOR_SHOE_Z_MM)),
            "local reaction shoe attaching mount region to perimeter frame",
            "MANUAL_A_CANDIDATE_MATERIAL_DEFLECTION_FATIGUE_UNVALIDATED",
        )
        if _intersection(shoe.solid, frame.solid) <= 0.0:
            raise MechanicalStructureError(f"{zone_id} reaction shoe does not attach to perimeter frame")
        if _intersection(collar.solid, shoe.solid) <= 0.0:
            raise MechanicalStructureError(f"{zone_id} mount collar does not engage its reaction shoe")
        zones.append(ActuatorZone(zone_id, origin.as_tuple(), sign, angle_doe, envelope, collar, shoe))

    release = _release(frame, halo)
    keepouts = tuple(_protected_solid(model, index) for index in range(len(model.protected_volumes.all)))
    checks: list[ClearanceResult] = []

    # Full authority DOE at a single axis/origin per zone.
    for zone, (_, origin, sign) in zip(zones, ACTUATOR_ZONE_CANDIDATES):
        for angle in angle_doe:
            moving = _actuator(origin, sign, angle)
            state = f"ANGLE_{angle:g}_DEG"
            for keepout_id, keepout in keepouts:
                checks.append(ClearanceResult(
                    f"CLEAR_{zone.zone_id}_{state}_{keepout_id}", zone.zone_id, keepout_id, state, _intersection(moving, keepout)
                ))
            checks.append(ClearanceResult(
                f"CLEAR_{zone.zone_id}_{state}_RIGID_SHELL", zone.zone_id, "RIGID_SHELL", state, _intersection(moving, model.shell.solid)
            ))

    # Static structure and moving release stay out of protected anatomy.
    static_parts = (
        frame,
        halo,
        *(zone.mount_collar for zone in zones),
        *(zone.reaction_shoe for zone in zones),
        release.left_frame_clevis,
        release.left_rear_lug,
        release.left_pivot_pin,
        release.right_frame_socket,
        release.right_rear_tongue,
        release.guard,
    )
    for part in static_parts:
        for keepout_id, keepout in keepouts:
            checks.append(ClearanceResult(
                f"CLEAR_{part.part_id}_{keepout_id}", part.part_id, keepout_id, "STATIC", _intersection(part.solid, keepout)
            ))

    for offset in (0.0, 3.5, 7.0, 10.5, RELEASE_DOG_TRAVEL_MM):
        moving = release.dog_and_grip.solid.translate((offset, 0.0, 0.0))
        state = f"DOG_X_PLUS_{offset:g}_MM"
        for participant in (release.right_frame_socket, release.right_rear_tongue, release.guard):
            checks.append(ClearanceResult(
                f"CLEAR_RELEASE_{state}_{participant.part_id}", release.dog_and_grip.part_id, participant.part_id, state, _intersection(moving, participant.solid)
            ))
        checks.append(ClearanceResult(
            f"CLEAR_RELEASE_{state}_RIGID_SHELL", release.dog_and_grip.part_id, "RIGID_SHELL", state, _intersection(moving, model.shell.solid)
        ))
        for keepout_id, keepout in keepouts:
            checks.append(ClearanceResult(
                f"CLEAR_RELEASE_{state}_{keepout_id}", release.dog_and_grip.part_id, keepout_id, state, _intersection(moving, keepout)
            ))

    result = ManualAMechanicalStructure(
        source_authority_revision=str(authority.get("project", "authority_revision")),
        source_model_sha256=_source_sha(model),
        frame=frame,
        halo=halo,
        actuator_zones=tuple(zones),
        release=release,
        clearance_results=tuple(checks),
        unresolved_physical_gates=(
            "FRAME_MATERIAL_DEFLECTION_FIRST_MODE_FATIGUE_AND_LOCAL_BEARING",
            "RETENTION_FIT_COMFORT_PRELOAD_HAIR_INTERACTION_AND_ANTHROPOMETRIC_RANGE",
            "EMERGENCY_RELEASE_FORCE_5_TO_12_N_AND_REMOVAL_TIME_LE_2_S",
            "WHOLE_RETENTION_HEADFORM_REMOVAL_SWEEP_AFTER_DOG_RELEASE",
            "ACTUATOR_FORCE_FATIGUE_ACOUSTIC_LIFETIME_AND_FINAL_HARD_STOP",
            "MANUAL_B_EXTERIOR_CANDIDATE_COMPATIBILITY_UNTIL_MERGED",
        ),
    )
    result.validate_current_sources(authority, model)
    return result
