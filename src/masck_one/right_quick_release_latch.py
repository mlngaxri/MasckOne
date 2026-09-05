from __future__ import annotations

"""Cell 3 right-side quick-release latch CAD.

Explicit transverse capture replaces friction-implied retention. The package has
hard-stopped captive slider motion, a connected flexure cam detent, reset-required
released state, exact world-frame collision checks and dimensionally consistent
tolerance arithmetic. Geometry is digital-only; release force/time, wet usability,
fatigue, fit and physical safety remain validation gates.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority, load_authority
from .mechanism_tolerance import ClearanceStack, ScalarTolerance
from .model import Component, MasckOneModel, build_model

SCHEMA = "MASCK_ONE_CELL3_RIGHT_QUICK_RELEASE_LATCH_V3"
SOURCE_MAIN_SHA = "628ec5f5766937433b1bdf8f30edc372924cf41e"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
DIGITAL_ONLY = "DIGITAL_MECHANISM_GEOMETRY_ONLY_NOT_PHYSICAL_VALIDATION"
KERNEL_ZERO_MM3 = 1e-8

LATCH_CENTER_X_MM = 77.0
LATCH_AXIS_Z_MM = -19.0
SOCKET_XYZ_MM = (12.0, 18.0, 13.0)
SOCKET_CENTER_Z_MM = -17.5
TONGUE_CHANNEL_XYZ_MM = (5.4, 9.4, 15.0)
TONGUE_XYZ_MM = (4.6, 8.6, 14.0)
TONGUE_CENTER_Z_MM = -22.0
BORE_RADIUS_MM = 1.8
PIN_RADIUS_MM = 1.5
PIN_LENGTH_MM = 7.0
RELEASE_TRAVEL_MM = 7.3

CAPSULE_XYZ_MM = (11.4, 7.4, 7.4)
CAPSULE_CENTER_X_MM = 85.7
CAVITY_XYZ_MM = (9.6, 5.4, 5.4)
CAVITY_CENTER_X_MM = 86.0
SPOOL_START_X_MM = 81.2
SPOOL_LEFT_RADIUS_MM = 2.4
SPOOL_LEFT_LENGTH_MM = 0.7
SPOOL_NECK_RADIUS_MM = 1.2
SPOOL_NECK_LENGTH_MM = 0.9
SPOOL_RIGHT_RADIUS_MM = 2.4
SPOOL_RIGHT_LENGTH_MM = 0.7
SLIDER_JOIN_OVERLAP_MM = 0.10
GRIP_XYZ_MM = (1.2, 10.0, 7.0)
GRIP_CENTER_X_MM = 92.1

DETENT_TOOTH_X_MIN_MM = 81.95
DETENT_TOOTH_X_MAX_MM = 82.75
DETENT_TOOTH_BOTTOM_LEFT_Z_MM = -17.70
DETENT_TOOTH_BOTTOM_RIGHT_Z_MM = -16.90
DETENT_TOOTH_TOP_Z_MM = -15.90
DETENT_TOOTH_WIDTH_Y_MM = 2.4
DETENT_NECK_RADIAL_CLEARANCE_MM = 0.10
FLEXURE_BEAM_XYZ_MM = (8.0, 2.4, 0.8)
FLEXURE_BEAM_CENTER_MM = (84.5, 0.0, -15.8)
FLEXURE_ANCHOR_XYZ_MM = (2.0, 4.2, 1.6)
FLEXURE_ANCHOR_CENTER_MM = (88.5, 0.0, -15.8)
DETENT_DIGITAL_ESCAPE_LIFT_MM = 1.30
DETENT_RIGID_PULL_PROBE_MM = 0.40

CHANNEL_SIZE_TOL_MM = 0.08
TONGUE_SIZE_TOL_MM = 0.08
BORE_RADIUS_TOL_MM = 0.05
PIN_RADIUS_TOL_MM = 0.05
TRAVEL_TOL_MM = 0.10
PIN_LENGTH_TOL_MM = 0.06
SPOOL_RADIUS_TOL_MM = 0.05
CAVITY_END_TOL_MM = 0.06
DETENT_POSITION_TOL_MM = 0.05


class RightQuickReleaseLatchError(ValueError):
    pass


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise RightQuickReleaseLatchError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise RightQuickReleaseLatchError(f"{label} must be finite")
    return 0.0 if result == 0.0 else result


def _positive(value: object, label: str) -> float:
    result = _finite(value, label)
    if result <= 0.0:
        raise RightQuickReleaseLatchError(f"{label} must be positive")
    return result


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> cq.Workplane:
    return cq.Workplane("XY").box(
        *tuple(_positive(value, "box dimension") for value in size),
        centered=(True, True, True),
    ).translate(tuple(_finite(value, "box center") for value in center))


def _cylinder_x(radius_mm: float, length_mm: float, center: tuple[float, float, float]) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .circle(_positive(radius_mm, "cylinder radius"))
        .extrude(_positive(length_mm, "cylinder length") / 2.0, both=True)
        .rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 90.0)
        .translate(tuple(_finite(value, "cylinder center") for value in center))
    )


def _wedge_prism_y(
    points_xz: tuple[tuple[float, float], ...],
    width_y_mm: float,
) -> cq.Workplane:
    if len(points_xz) < 3:
        raise RightQuickReleaseLatchError("wedge requires at least three XZ points")
    wp = cq.Workplane("XZ").moveTo(
        _finite(points_xz[0][0], "wedge x"),
        _finite(points_xz[0][1], "wedge z"),
    )
    for x, z in points_xz[1:]:
        wp = wp.lineTo(_finite(x, "wedge x"), _finite(z, "wedge z"))
    return wp.close().extrude(_positive(width_y_mm, "wedge width") / 2.0, both=True)


def _intersection_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise RightQuickReleaseLatchError("intersection volume must be finite and nonnegative")
    return 0.0 if value < KERNEL_ZERO_MM3 else value


def _bbox(solid: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = solid.val().BoundingBox()
    return tuple(float(v) for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))


def _continuous_translation_aabb(solid: cq.Workplane, travel_x_mm: float) -> cq.Workplane:
    travel = _positive(travel_x_mm, "release travel")
    xmin, xmax, ymin, ymax, zmin, zmax = _bbox(solid)
    return _box(
        ((xmax - xmin) + travel, ymax - ymin, zmax - zmin),
        ((xmin + xmax + travel) / 2.0, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0),
    )


def _component_signature(component: Component) -> dict[str, object]:
    shape = component.solid.val()
    bb = shape.BoundingBox()
    return {
        "name": component.name,
        "status": component.status,
        "volume_mm3": round(float(shape.Volume()), 6),
        "bounds_mm": [
            round(float(v), 6)
            for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
        ],
    }


def _source_model_sha(model: MasckOneModel) -> str:
    payload = {
        "shell": _component_signature(model.shell),
        "actuators": [_component_signature(part) for part in model.actuator_envelopes],
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _protected_solid(model: MasckOneModel, index: int) -> tuple[str, cq.Workplane]:
    zone = model.protected_volumes.all[index].zone
    wp = cq.Workplane("XY").workplane(offset=-60.0).center(zone.center.x, zone.center.y)
    if zone.shape == "CIRCLE":
        solid = wp.circle(zone.envelope_width_mm / 2.0).extrude(120.0)
    else:
        solid = wp.ellipse(
            zone.envelope_width_mm / 2.0,
            zone.envelope_height_mm / 2.0,
        ).extrude(120.0)
    if zone.angle_deg:
        solid = solid.rotate(
            (zone.center.x, zone.center.y, 0.0),
            (zone.center.x, zone.center.y, 1.0),
            zone.angle_deg,
        )
    return zone.zone_id, solid


@dataclass(frozen=True, slots=True)
class LatchPart:
    part_id: str
    role: str
    solid: cq.Workplane
    status: str = DIGITAL_ONLY

    def __post_init__(self) -> None:
        if type(self.part_id) is not str or not self.part_id.strip():
            raise RightQuickReleaseLatchError("part_id must be exact nonblank text")
        shape = self.solid.val()
        if not shape.isValid() or float(shape.Volume()) <= 0.0:
            raise RightQuickReleaseLatchError(
                f"{self.part_id} must be a valid positive-volume solid"
            )
        if len(shape.Solids()) != 1:
            raise RightQuickReleaseLatchError(
                f"{self.part_id} must be one connected solid, not a compound of disconnected bodies"
            )

    def manifest(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "role": self.role,
            "status": self.status,
            "solid_count": len(self.solid.val().Solids()),
            "volume_mm3": float(self.solid.val().Volume()),
            "bounds_mm": list(_bbox(self.solid)),
        }


@dataclass(frozen=True, slots=True)
class CollisionCheck:
    check_id: str
    obstacle_id: str
    intersection_volume_mm3: float

    @property
    def passes(self) -> bool:
        return self.intersection_volume_mm3 == 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "obstacle_id": self.obstacle_id,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "passes": self.passes,
        }


@dataclass(frozen=True, slots=True)
class RightQuickReleaseLatch:
    source_main_sha: str
    source_authority_revision: str
    source_model_sha256: str
    geometry_sha256: str
    socket: LatchPart
    tongue: LatchPart
    guide_capsule: LatchPart
    flexure_detent: LatchPart
    slider_and_grip: LatchPart
    continuous_withdrawal_sweep: LatchPart
    collision_checks: tuple[CollisionCheck, ...]
    tolerance_stacks: tuple[ClearanceStack, ...]
    tolerance_values_mm: tuple[tuple[str, float], ...]

    @property
    def all_required_clear(self) -> bool:
        return all(check.passes for check in self.collision_checks)

    @property
    def package_sha256(self) -> str:
        return sha256(
            json.dumps(
                self.manifest(include_sha=False),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode()
        ).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        pin_xmin = LATCH_CENTER_X_MM - PIN_LENGTH_MM / 2.0
        pin_xmax = LATCH_CENTER_X_MM + PIN_LENGTH_MM / 2.0
        tongue_xmin = LATCH_CENTER_X_MM - TONGUE_XYZ_MM[0] / 2.0
        tongue_xmax = LATCH_CENTER_X_MM + TONGUE_XYZ_MM[0] / 2.0
        cavity_xmin = CAVITY_CENTER_X_MM - CAVITY_XYZ_MM[0] / 2.0
        cavity_xmax = CAVITY_CENTER_X_MM + CAVITY_XYZ_MM[0] / 2.0
        spool_xmax = (
            SPOOL_START_X_MM
            + SPOOL_LEFT_LENGTH_MM
            + SPOOL_NECK_LENGTH_MM
            + SPOOL_RIGHT_LENGTH_MM
        )
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": self.source_main_sha,
            "source_authority_revision": self.source_authority_revision,
            "source_model_sha256": self.source_model_sha256,
            "geometry_sha256": self.geometry_sha256,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "parts": [
                part.manifest()
                for part in (
                    self.socket,
                    self.tongue,
                    self.guide_capsule,
                    self.flexure_detent,
                    self.slider_and_grip,
                    self.continuous_withdrawal_sweep,
                )
            ],
            "capture_path": [
                "HALO_SIDE_TONGUE",
                "TRANSVERSE_SLIDER_PIN",
                "FRAME_SIDE_SOCKET",
                "FRAME_RETENTION_INTERFACE",
            ],
            "latched_state": {
                "state_id": "LATCHED",
                "slider_offset_mm": 0.0,
                "pin_spans_tongue_x_mm": [pin_xmin, pin_xmax],
                "tongue_x_mm": [tongue_xmin, tongue_xmax],
                "positive_capture": pin_xmin < tongue_xmin and pin_xmax > tongue_xmax,
                "flexure_cam_tooth_in_spool_neck": True,
                "detent_neck_radial_clearance_mm": DETENT_NECK_RADIAL_CLEARANCE_MM,
                "inboard_hard_stop_x_mm": cavity_xmin,
                "spool_inboard_face_x_mm": SPOOL_START_X_MM,
                "reset_required": False,
            },
            "release_transition": {
                "action": "ONE_HAND_WET_UNPOWERED_PULL_PLUS_X",
                "cam_surface": "SLOPED_FLEXURE_TOOTH_UNDERSIDE",
                "rigid_pull_probe_mm": DETENT_RIGID_PULL_PROBE_MM,
                "rigid_pull_blocked_by_positive_geometry": True,
                "digital_escape_lift_mm_candidate": DETENT_DIGITAL_ESCAPE_LIFT_MM,
                "digital_escape_lift_is_material_model": False,
                "continuous_translation_sweep_kind": (
                    "CONSERVATIVE_AABB_OF_ALL_PURE_TRANSLATION_POSITIONS"
                ),
                "travel_mm": RELEASE_TRAVEL_MM,
                "power_dependency": None,
                "firmware_dependency": None,
                "app_dependency": None,
            },
            "released_state": {
                "state_id": "RELEASED_RESET_REQUIRED",
                "slider_offset_mm": RELEASE_TRAVEL_MM,
                "pin_released_xmin_mm": pin_xmin + RELEASE_TRAVEL_MM,
                "tongue_xmax_mm": tongue_xmax,
                "tongue_clearance_nominal_mm": pin_xmin + RELEASE_TRAVEL_MM - tongue_xmax,
                "outboard_hard_stop_x_mm": cavity_xmax,
                "spool_outboard_face_x_mm": spool_xmax + RELEASE_TRAVEL_MM,
                "tongue_capture": False,
                "slider_captive": True,
                "reset_required": True,
            },
            "reset_transition": {
                "action": "MANUAL_PUSH_MINUS_X_TO_LATCHED_HARD_STOP_AND_DETENT",
                "automatic_or_firmware_reset": False,
            },
            "tolerance_basis": {
                "tongue_channel": "LIMITING_HALF_DIMENSION_BOUNDARY_CLEARANCE",
                "pin_bore": "RADIUS_TO_RADIUS_CLEARANCE",
                "released_tongue": "TRAVEL_MINUS_PIN_HALF_LENGTH_MINUS_TONGUE_HALF_WIDTH",
                "hard_stop": "LIMITING_CAVITY_END_TO_CAPSULE_END_CLEARANCE",
                "detent": "FLANGE_RADIUS_MINUS_NECK_RADIUS_MINUS_TOOTH_CLEARANCE",
            },
            "tolerance_results_mm": dict(self.tolerance_values_mm),
            "tolerance_stack_sha256": {
                stack.stack_id: stack.provenance_sha256 for stack in self.tolerance_stacks
            },
            "collision_checks": [check.manifest() for check in self.collision_checks],
            "all_required_clear": self.all_required_clear,
            "actuation_compatibility": {
                "required_independent_zone_count": 4,
                "actuator_geometry_changed": False,
            },
            "physical_gates": {
                "release_force_target_N": [5.0, 12.0],
                "release_force_measured_N": None,
                "release_time_requirement_s": 2.0,
                "release_time_measured_s": None,
                "wet_one_hand_validation": "OPEN_PHYSICAL_GATE",
                "flexure_material_strain_fatigue": "OPEN_PHYSICAL_GATE",
                "cam_contact_wear_and_jam_margin": "OPEN_PHYSICAL_GATE",
                "accidental_release_margin": "OPEN_PHYSICAL_GATE",
                "whole_head_removal_after_release": "OPEN_PENDING_RETENTION_HEADFORM_SWEEP",
            },
            "evidence_status": DIGITAL_ONLY,
            "physical_validation_eligible": False,
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def _definition_sha() -> str:
    payload = {
        "schema": SCHEMA,
        "source_main_sha": SOURCE_MAIN_SHA,
        "world_frame": WORLD_FRAME_ID,
        "center": [LATCH_CENTER_X_MM, 0.0, LATCH_AXIS_Z_MM],
        "socket": [SOCKET_XYZ_MM, SOCKET_CENTER_Z_MM],
        "channel": TONGUE_CHANNEL_XYZ_MM,
        "tongue": [TONGUE_XYZ_MM, TONGUE_CENTER_Z_MM],
        "bore_radius": BORE_RADIUS_MM,
        "pin": [PIN_RADIUS_MM, PIN_LENGTH_MM],
        "travel": RELEASE_TRAVEL_MM,
        "capsule": [CAPSULE_XYZ_MM, CAPSULE_CENTER_X_MM],
        "cavity": [CAVITY_XYZ_MM, CAVITY_CENTER_X_MM],
        "spool": [
            SPOOL_START_X_MM,
            SPOOL_LEFT_RADIUS_MM,
            SPOOL_LEFT_LENGTH_MM,
            SPOOL_NECK_RADIUS_MM,
            SPOOL_NECK_LENGTH_MM,
            SPOOL_RIGHT_RADIUS_MM,
            SPOOL_RIGHT_LENGTH_MM,
        ],
        "slider_join_overlap": SLIDER_JOIN_OVERLAP_MM,
        "grip": [GRIP_XYZ_MM, GRIP_CENTER_X_MM],
        "detent_tooth_xz": [
            [DETENT_TOOTH_X_MIN_MM, DETENT_TOOTH_BOTTOM_LEFT_Z_MM],
            [DETENT_TOOTH_X_MAX_MM, DETENT_TOOTH_BOTTOM_RIGHT_Z_MM],
            [DETENT_TOOTH_X_MAX_MM, DETENT_TOOTH_TOP_Z_MM],
            [DETENT_TOOTH_X_MIN_MM, DETENT_TOOTH_TOP_Z_MM],
        ],
        "detent_width_y": DETENT_TOOTH_WIDTH_Y_MM,
        "flexure_beam": [FLEXURE_BEAM_XYZ_MM, FLEXURE_BEAM_CENTER_MM],
        "flexure_anchor": [FLEXURE_ANCHOR_XYZ_MM, FLEXURE_ANCHOR_CENTER_MM],
        "detent_escape_lift": DETENT_DIGITAL_ESCAPE_LIFT_MM,
        "detent_rigid_pull_probe": DETENT_RIGID_PULL_PROBE_MM,
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _tolerance_stacks(geometry_sha: str) -> tuple[ClearanceStack, ...]:
    side_axis = min(
        (0, 1),
        key=lambda axis: (
            TONGUE_CHANNEL_XYZ_MM[axis] - TONGUE_XYZ_MM[axis]
        ) / 2.0,
    )
    side_clearance = (
        TONGUE_CHANNEL_XYZ_MM[side_axis] - TONGUE_XYZ_MM[side_axis]
    ) / 2.0
    released_clearance = (
        RELEASE_TRAVEL_MM - PIN_LENGTH_MM / 2.0 - TONGUE_XYZ_MM[0] / 2.0
    )
    captive_margin = SPOOL_LEFT_RADIUS_MM - BORE_RADIUS_MM
    capsule_xmin = CAPSULE_CENTER_X_MM - CAPSULE_XYZ_MM[0] / 2.0
    capsule_xmax = CAPSULE_CENTER_X_MM + CAPSULE_XYZ_MM[0] / 2.0
    cavity_xmin = CAVITY_CENTER_X_MM - CAVITY_XYZ_MM[0] / 2.0
    cavity_xmax = CAVITY_CENTER_X_MM + CAVITY_XYZ_MM[0] / 2.0
    inboard_wall = cavity_xmin - capsule_xmin
    outboard_wall = capsule_xmax - cavity_xmax
    stop_wall_margin = min(inboard_wall, outboard_wall)
    detent_engagement = (
        SPOOL_LEFT_RADIUS_MM
        - SPOOL_NECK_RADIUS_MM
        - DETENT_NECK_RADIAL_CLEARANCE_MM
    )

    if inboard_wall <= outboard_wall:
        hard_stop_terms = (
            (
                "CAVITY_INBOARD_END",
                ScalarTolerance(cavity_xmin, CAVITY_END_TOL_MM, CAVITY_END_TOL_MM),
                1,
            ),
            (
                "CAPSULE_INBOARD_END",
                ScalarTolerance(capsule_xmin, 0.0, 0.0),
                -1,
            ),
        )
    else:
        hard_stop_terms = (
            (
                "CAPSULE_OUTBOARD_END",
                ScalarTolerance(capsule_xmax, 0.0, 0.0),
                1,
            ),
            (
                "CAVITY_OUTBOARD_END",
                ScalarTolerance(cavity_xmax, CAVITY_END_TOL_MM, CAVITY_END_TOL_MM),
                -1,
            ),
        )

    return (
        ClearanceStack(
            "LATCH_TONGUE_CHANNEL_CLEARANCE",
            WORLD_FRAME_ID,
            geometry_sha,
            side_clearance,
            (
                (
                    "CHANNEL_HALF_SIZE",
                    ScalarTolerance(
                        TONGUE_CHANNEL_XYZ_MM[side_axis] / 2.0,
                        CHANNEL_SIZE_TOL_MM / 2.0,
                        CHANNEL_SIZE_TOL_MM / 2.0,
                    ),
                    1,
                ),
                (
                    "TONGUE_HALF_SIZE",
                    ScalarTolerance(
                        TONGUE_XYZ_MM[side_axis] / 2.0,
                        TONGUE_SIZE_TOL_MM / 2.0,
                        TONGUE_SIZE_TOL_MM / 2.0,
                    ),
                    -1,
                ),
            ),
        ),
        ClearanceStack(
            "LATCH_PIN_BORE_RADIAL_CLEARANCE",
            WORLD_FRAME_ID,
            geometry_sha,
            BORE_RADIUS_MM - PIN_RADIUS_MM,
            (
                (
                    "BORE_RADIUS",
                    ScalarTolerance(
                        BORE_RADIUS_MM, BORE_RADIUS_TOL_MM, BORE_RADIUS_TOL_MM
                    ),
                    1,
                ),
                (
                    "PIN_RADIUS",
                    ScalarTolerance(
                        PIN_RADIUS_MM, PIN_RADIUS_TOL_MM, PIN_RADIUS_TOL_MM
                    ),
                    -1,
                ),
            ),
        ),
        ClearanceStack(
            "LATCH_RELEASED_TONGUE_CLEARANCE",
            WORLD_FRAME_ID,
            geometry_sha,
            released_clearance,
            (
                (
                    "TRAVEL",
                    ScalarTolerance(RELEASE_TRAVEL_MM, TRAVEL_TOL_MM, TRAVEL_TOL_MM),
                    1,
                ),
                (
                    "PIN_HALF_LENGTH",
                    ScalarTolerance(
                        PIN_LENGTH_MM / 2.0,
                        PIN_LENGTH_TOL_MM / 2.0,
                        PIN_LENGTH_TOL_MM / 2.0,
                    ),
                    -1,
                ),
                (
                    "TONGUE_HALF_WIDTH",
                    ScalarTolerance(
                        TONGUE_XYZ_MM[0] / 2.0,
                        TONGUE_SIZE_TOL_MM / 2.0,
                        TONGUE_SIZE_TOL_MM / 2.0,
                    ),
                    -1,
                ),
            ),
        ),
        ClearanceStack(
            "LATCH_CAPTIVE_RADIAL_MARGIN",
            WORLD_FRAME_ID,
            geometry_sha,
            captive_margin,
            (
                (
                    "SPOOL_RADIUS",
                    ScalarTolerance(
                        SPOOL_LEFT_RADIUS_MM, SPOOL_RADIUS_TOL_MM, SPOOL_RADIUS_TOL_MM
                    ),
                    1,
                ),
                (
                    "EXIT_BORE_RADIUS",
                    ScalarTolerance(
                        BORE_RADIUS_MM, BORE_RADIUS_TOL_MM, BORE_RADIUS_TOL_MM
                    ),
                    -1,
                ),
            ),
        ),
        ClearanceStack(
            "LATCH_HARD_STOP_WALL_MARGIN",
            WORLD_FRAME_ID,
            geometry_sha,
            stop_wall_margin,
            hard_stop_terms,
        ),
        ClearanceStack(
            "LATCH_DETENT_ENGAGEMENT_MARGIN",
            WORLD_FRAME_ID,
            geometry_sha,
            detent_engagement,
            (
                (
                    "SPOOL_FLANGE_RADIUS",
                    ScalarTolerance(
                        SPOOL_LEFT_RADIUS_MM, SPOOL_RADIUS_TOL_MM, SPOOL_RADIUS_TOL_MM
                    ),
                    1,
                ),
                (
                    "SPOOL_NECK_RADIUS",
                    ScalarTolerance(
                        SPOOL_NECK_RADIUS_MM, SPOOL_RADIUS_TOL_MM, SPOOL_RADIUS_TOL_MM
                    ),
                    -1,
                ),
                (
                    "TOOTH_RADIAL_CLEARANCE",
                    ScalarTolerance(
                        DETENT_NECK_RADIAL_CLEARANCE_MM,
                        DETENT_POSITION_TOL_MM,
                        DETENT_POSITION_TOL_MM,
                    ),
                    -1,
                ),
            ),
        ),
    )


def build_right_quick_release_latch(
    authority: Authority | None = None,
    model: MasckOneModel | None = None,
) -> RightQuickReleaseLatch:
    authority = authority or load_authority()
    model = model or build_model(authority)
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise RightQuickReleaseLatchError(
            "authority revision changed; rebind latch geometry before use"
        )
    if int(authority.number("actuation", "count")) != 4 or len(model.actuator_envelopes) != 4:
        raise RightQuickReleaseLatchError(
            "four independently controllable actuator zones must be preserved"
        )
    if authority.get("safety", "quick_release", "one_hand_wet_unpowered") is not True:
        raise RightQuickReleaseLatchError(
            "quick release must remain one-hand wet and unpowered"
        )
    if not math.isclose(
        float(authority.number("safety", "quick_release", "time_max_s")),
        2.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise RightQuickReleaseLatchError("quick-release time authority changed; rebind")
    force_target = tuple(
        float(v) for v in authority.get("safety", "quick_release", "force_target_N")
    )
    if force_target != (5.0, 12.0):
        raise RightQuickReleaseLatchError("quick-release force authority changed; rebind")

    release_bore = _cylinder_x(
        BORE_RADIUS_MM, 30.0, (LATCH_CENTER_X_MM, 0.0, LATCH_AXIS_Z_MM)
    )
    socket_outer = _box(
        SOCKET_XYZ_MM, (LATCH_CENTER_X_MM, 0.0, SOCKET_CENTER_Z_MM)
    )
    tongue_channel = _box(
        TONGUE_CHANNEL_XYZ_MM, (LATCH_CENTER_X_MM, 0.0, SOCKET_CENTER_Z_MM)
    )
    spool_service = _box(
        (4.2, CAVITY_XYZ_MM[1], CAVITY_XYZ_MM[2]),
        (82.0, 0.0, LATCH_AXIS_Z_MM),
    )
    socket_solid = socket_outer.cut(tongue_channel).cut(release_bore).cut(spool_service)
    tongue_solid = _box(
        TONGUE_XYZ_MM, (LATCH_CENTER_X_MM, 0.0, TONGUE_CENTER_Z_MM)
    ).cut(release_bore)

    capsule_outer = _box(
        CAPSULE_XYZ_MM, (CAPSULE_CENTER_X_MM, 0.0, LATCH_AXIS_Z_MM)
    )
    cavity = _box(CAVITY_XYZ_MM, (CAVITY_CENTER_X_MM, 0.0, LATCH_AXIS_Z_MM))
    stem_bore = _cylinder_x(
        BORE_RADIUS_MM,
        CAPSULE_XYZ_MM[0] + 2.0,
        (CAPSULE_CENTER_X_MM, 0.0, LATCH_AXIS_Z_MM),
    )
    tooth_window = _box(
        (1.6, 3.2, 4.5),
        ((DETENT_TOOTH_X_MIN_MM + DETENT_TOOTH_X_MAX_MM) / 2.0, 0.0, -16.6),
    )
    capsule_solid = capsule_outer.cut(cavity).cut(stem_bore).cut(tooth_window)

    pin = _cylinder_x(
        PIN_RADIUS_MM, PIN_LENGTH_MM, (LATCH_CENTER_X_MM, 0.0, LATCH_AXIS_Z_MM)
    )
    pin_xmax = LATCH_CENTER_X_MM + PIN_LENGTH_MM / 2.0
    left_center = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM / 2.0
    neck_center = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM + SPOOL_NECK_LENGTH_MM / 2.0
    right_center = (
        SPOOL_START_X_MM
        + SPOOL_LEFT_LENGTH_MM
        + SPOOL_NECK_LENGTH_MM
        + SPOOL_RIGHT_LENGTH_MM / 2.0
    )
    spool = _cylinder_x(
        SPOOL_LEFT_RADIUS_MM,
        SPOOL_LEFT_LENGTH_MM,
        (left_center, 0.0, LATCH_AXIS_Z_MM),
    )
    spool = spool.union(
        _cylinder_x(
            SPOOL_NECK_RADIUS_MM,
            SPOOL_NECK_LENGTH_MM,
            (neck_center, 0.0, LATCH_AXIS_Z_MM),
        )
    )
    spool = spool.union(
        _cylinder_x(
            SPOOL_RIGHT_RADIUS_MM,
            SPOOL_RIGHT_LENGTH_MM,
            (right_center, 0.0, LATCH_AXIS_Z_MM),
        )
    )
    spool_end = (
        SPOOL_START_X_MM
        + SPOOL_LEFT_LENGTH_MM
        + SPOOL_NECK_LENGTH_MM
        + SPOOL_RIGHT_LENGTH_MM
    )

    bridge_start = pin_xmax - SLIDER_JOIN_OVERLAP_MM
    bridge_end = SPOOL_START_X_MM + SLIDER_JOIN_OVERLAP_MM
    bridge = _cylinder_x(
        PIN_RADIUS_MM,
        bridge_end - bridge_start,
        ((bridge_start + bridge_end) / 2.0, 0.0, LATCH_AXIS_Z_MM),
    )
    grip_min_x = GRIP_CENTER_X_MM - GRIP_XYZ_MM[0] / 2.0
    outer_stem_start = spool_end - SLIDER_JOIN_OVERLAP_MM
    outer_stem = _cylinder_x(
        PIN_RADIUS_MM,
        grip_min_x - outer_stem_start,
        ((outer_stem_start + grip_min_x) / 2.0, 0.0, LATCH_AXIS_Z_MM),
    )
    grip = _box(GRIP_XYZ_MM, (GRIP_CENTER_X_MM, 0.0, LATCH_AXIS_Z_MM))
    slider_solid = pin.union(bridge).union(spool).union(outer_stem).union(grip)

    tooth = _wedge_prism_y(
        (
            (DETENT_TOOTH_X_MIN_MM, DETENT_TOOTH_BOTTOM_LEFT_Z_MM),
            (DETENT_TOOTH_X_MAX_MM, DETENT_TOOTH_BOTTOM_RIGHT_Z_MM),
            (DETENT_TOOTH_X_MAX_MM, DETENT_TOOTH_TOP_Z_MM),
            (DETENT_TOOTH_X_MIN_MM, DETENT_TOOTH_TOP_Z_MM),
        ),
        DETENT_TOOTH_WIDTH_Y_MM,
    )
    beam = _box(FLEXURE_BEAM_XYZ_MM, FLEXURE_BEAM_CENTER_MM)
    anchor = _box(FLEXURE_ANCHOR_XYZ_MM, FLEXURE_ANCHOR_CENTER_MM)
    flexure_solid = tooth.union(beam).union(anchor)

    socket = LatchPart(
        "RIGHT_LATCH_FRAME_SOCKET",
        "frame-side tongue socket with explicit transverse capture bore",
        socket_solid,
    )
    tongue = LatchPart(
        "RIGHT_LATCH_HALO_TONGUE",
        "halo-side tongue positively blocked by transverse pin while latched",
        tongue_solid,
    )
    capsule = LatchPart(
        "RIGHT_LATCH_CAPTIVE_GUIDE",
        "guide capsule with internal spool cavity and axial hard-stop walls",
        capsule_solid,
    )
    flexure = LatchPart(
        "RIGHT_LATCH_FLEXURE_CAM_DETENT",
        "connected fixed leaf with sloped cam tooth seated in spool neck; material response unvalidated",
        flexure_solid,
    )
    slider = LatchPart(
        "RIGHT_LATCH_CAPTIVE_SLIDER",
        "single connected transverse pin, bridge, captive spool, pull stem and wet grip",
        slider_solid,
    )
    sweep = LatchPart(
        "RIGHT_LATCH_CONTINUOUS_WITHDRAWAL_SWEEP",
        "conservative continuous pure-translation AABB",
        _continuous_translation_aabb(slider_solid, RELEASE_TRAVEL_MM),
    )

    if _intersection_mm3(socket.solid, tongue.solid) != 0.0:
        raise RightQuickReleaseLatchError(
            "tongue must occupy socket channel without material penetration"
        )
    if (
        _intersection_mm3(slider.solid, socket.solid) != 0.0
        or _intersection_mm3(slider.solid, tongue.solid) != 0.0
    ):
        raise RightQuickReleaseLatchError(
            "latched slider must occupy controlled bores without material penetration"
        )
    if (
        _intersection_mm3(slider.solid, capsule.solid) != 0.0
        or _intersection_mm3(slider.solid, flexure.solid) != 0.0
    ):
        raise RightQuickReleaseLatchError(
            "latched slider must sit in guide and detent neck without solid penetration"
        )
    if _intersection_mm3(capsule.solid, socket.solid) <= 0.0:
        raise RightQuickReleaseLatchError(
            "captive guide must attach positively to frame socket"
        )
    if _intersection_mm3(flexure.solid, capsule.solid) <= 0.0:
        raise RightQuickReleaseLatchError(
            "flexure anchor must attach positively to guide capsule"
        )

    rigid_attempt = slider.solid.translate((DETENT_RIGID_PULL_PROBE_MM, 0.0, 0.0))
    if _intersection_mm3(rigid_attempt, flexure.solid) <= 0.0:
        raise RightQuickReleaseLatchError(
            "rigid pull must be blocked by positive cam-detent geometry"
        )
    digital_escape = flexure.solid.translate((0.0, 0.0, DETENT_DIGITAL_ESCAPE_LIFT_MM))
    if _intersection_mm3(rigid_attempt, digital_escape) != 0.0:
        raise RightQuickReleaseLatchError(
            "digital detent escape state is insufficient to permit deliberate withdrawal"
        )

    cavity_xmin = CAVITY_CENTER_X_MM - CAVITY_XYZ_MM[0] / 2.0
    cavity_xmax = CAVITY_CENTER_X_MM + CAVITY_XYZ_MM[0] / 2.0
    spool_xmax = (
        SPOOL_START_X_MM
        + SPOOL_LEFT_LENGTH_MM
        + SPOOL_NECK_LENGTH_MM
        + SPOOL_RIGHT_LENGTH_MM
    )
    if not math.isclose(SPOOL_START_X_MM, cavity_xmin, rel_tol=0.0, abs_tol=1e-12):
        raise RightQuickReleaseLatchError(
            "latched spool must terminate at the inboard hard stop"
        )
    if not math.isclose(
        spool_xmax + RELEASE_TRAVEL_MM, cavity_xmax, rel_tol=0.0, abs_tol=1e-12
    ):
        raise RightQuickReleaseLatchError(
            "released spool must terminate at the outboard hard stop"
        )

    released_slider = slider.solid.translate((RELEASE_TRAVEL_MM, 0.0, 0.0))
    if _intersection_mm3(released_slider, tongue.solid) != 0.0:
        raise RightQuickReleaseLatchError("released slider still captures tongue")
    if _intersection_mm3(released_slider, capsule.solid) != 0.0:
        raise RightQuickReleaseLatchError(
            "released slider penetrates guide hard-stop walls"
        )

    geometry_sha = _definition_sha()
    stacks = _tolerance_stacks(geometry_sha)
    values = tuple(
        (
            stack.stack_id,
            stack.assert_positive_clearance(
                current_geometry_sha256=geometry_sha,
                coordinate_frame_id=WORLD_FRAME_ID,
            ),
        )
        for stack in stacks
    )

    checks: list[CollisionCheck] = [
        CollisionCheck(
            "WITHDRAWAL_SWEEP_VS_CURRENT_MAIN_SHELL",
            "RIGID_SHELL",
            _intersection_mm3(sweep.solid, model.shell.solid),
        )
    ]
    for index in range(len(model.protected_volumes.all)):
        zone_id, protected = _protected_solid(model, index)
        checks.append(
            CollisionCheck(
                f"WITHDRAWAL_SWEEP_VS_{zone_id}",
                zone_id,
                _intersection_mm3(sweep.solid, protected),
            )
        )

    result = RightQuickReleaseLatch(
        SOURCE_MAIN_SHA,
        AUTHORITY_REVISION,
        _source_model_sha(model),
        geometry_sha,
        socket,
        tongue,
        capsule,
        flexure,
        slider,
        sweep,
        tuple(checks),
        stacks,
        values,
    )
    if not result.all_required_clear:
        raise RightQuickReleaseLatchError(
            "continuous withdrawal sweep intersects current shell or protected anatomy"
        )
    return result
