from __future__ import annotations

"""Tactile refinement of the historical right quick-release donor.

The current retention graph deliberately keeps closed PR #71 as a historical donor.
This module preserves that evidence boundary: it does not relabel the old branch as
released or close whole-head removal. Instead it reconstructs the useful 7.3 mm
captive-slider topology as a new owner-local candidate and fixes the main tactile
failure modes before any future graph promotion.

Refinements:
- four integral low-friction bearing lands inside the spool cavity reduce radial float
  while leaving open corner debris paths;
- a shallow integral rib/slot makes the slider one-DOF instead of allowing free axial
  rotation;
- the detent underside uses a dense quintic-smoothstep approximation rather than one
  abrupt planar ramp, with separate manufactured-free and installed references for a
  small anti-chatter preload seed;
- mechanically keyed elastomer stop rings engage only in the last 0.04 mm at both end
  states, while the original rigid hard-stop planes remain the abuse limits;
- the exposed grip keeps the donor envelope but uses a rounded user-touch profile.

All force, strain, wet use, fatigue, friction, rebound, acoustics and subjective feel
remain physical validation. This file does not claim integrated retention safety.
"""

from dataclasses import dataclass, field
from hashlib import sha256
import json
import math

import cadquery as cq

from .mechanical_interface_graph import build_mechanical_interface_graph

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V1"
HISTORICAL_DONOR_PR = 71
HISTORICAL_DONOR_HEAD_SHA = "0b5a619c6cea344038b0e8b8cc10a50e3d193390"
OWNER_BRANCH = "sol-high/retention-quick-release-20260909"
OWNER_HEAD_AT_REFINEMENT_START = "ad8be3911614da025a064138c748d1be4abdfeac"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
TOL_MM3 = 1e-7

LATCH_CENTER_X_MM = 77.0
LATCH_AXIS_Z_MM = -19.0
SOCKET_XYZ_MM = (12.0, 18.0, 13.0)
SOCKET_CENTER_Z_MM = -17.5
TONGUE_CHANNEL_XYZ_MM = (5.4, 9.4, 15.0)
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
FLEXURE_BEAM_XYZ_MM = (8.0, 2.4, 0.8)
FLEXURE_BEAM_CENTER_MM = (84.5, 0.0, -15.8)
FLEXURE_ANCHOR_XYZ_MM = (2.0, 4.2, 1.6)
FLEXURE_ANCHOR_CENTER_MM = (88.5, 0.0, -15.8)
DETENT_DIGITAL_ESCAPE_LIFT_MM = 1.30
DETENT_RIGID_PULL_PROBE_MM = 0.40
DETENT_FREE_PRELOAD_INTRUSION_SEED_MM = 0.12
DETENT_NOMINAL_INTERFERENCE_SEED_MM = 0.02
CAM_SEGMENTS = 16

# Integral spool rails. Donor square cavity half-width 2.70 vs 2.40 mm flange radius
# leaves 0.30 mm radial float. The new lands leave 0.03 mm nominal radial clearance.
SPOOL_RAIL_RADIAL_CLEARANCE_MM = 0.03
MAX_SPOOL_RAIL_RADIAL_CLEARANCE_MM = 0.05
SPOOL_RAIL_INNER_RADIUS_MM = SPOOL_LEFT_RADIUS_MM + SPOOL_RAIL_RADIAL_CLEARANCE_MM
SPOOL_RAIL_ROOT_MM = 0.10
SPOOL_RAIL_TANGENTIAL_WIDTH_MM = 1.10
SPOOL_RAIL_X_MARGIN_MM = 0.18

# One-DOF anti-rotation key on the bottom of the outer stem.
ANTI_ROTATION_RIB_WIDTH_Y_MM = 0.44
ANTI_ROTATION_RIB_DEPTH_Z_MM = 0.20
ANTI_ROTATION_RIB_ROOT_OVERLAP_MM = 0.08
ANTI_ROTATION_SLOT_WIDTH_Y_MM = 0.54
ANTI_ROTATION_SLOT_DEPTH_Z_MM = 0.30
ANTI_ROTATION_SIDE_CLEARANCE_MM = (
    ANTI_ROTATION_SLOT_WIDTH_Y_MM - ANTI_ROTATION_RIB_WIDTH_Y_MM
) / 2.0
MAX_ANTI_ROTATION_SIDE_CLEARANCE_MM = 0.06

# Rooted progressive end-state damping. The free ring protrudes 0.04 mm into the
# cavity; the installed reference is compressed flush with the original hard plane.
STOP_BUMPER_FREE_PROTRUSION_MM = 0.04
STOP_BUMPER_ROOT_DEPTH_MM = 0.12
STOP_BUMPER_ROOT_OD_MM = 4.86
STOP_BUMPER_NECK_OD_MM = 4.60
STOP_BUMPER_ID_MM = 3.18
STOP_BUMPER_ROOT_THICKNESS_MM = 0.07
STOP_BUMPER_TOTAL_THICKNESS_MM = (
    STOP_BUMPER_ROOT_DEPTH_MM + STOP_BUMPER_FREE_PROTRUSION_MM
)
MIN_FREE_BUMPER_INTERFERENCE_MM3 = 0.01

GRIP_CORNER_RADIUS_MM = 1.15


class RetentionQuickReleaseTactileError(ValueError):
    pass


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> cq.Workplane:
    return cq.Workplane("XY").box(*size, centered=(True, True, True)).translate(center)


def _cylinder_x(radius_mm: float, length_mm: float, center: tuple[float, float, float]) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .circle(radius_mm)
        .extrude(length_mm / 2.0, both=True)
        .rotate((0, 0, 0), (0, 1, 0), 90)
        .translate(center)
    )


def _ring_x(
    od_mm: float,
    id_mm: float,
    length_mm: float,
    center_x_mm: float,
) -> cq.Workplane:
    outer = _cylinder_x(od_mm / 2.0, length_mm, (center_x_mm, 0.0, LATCH_AXIS_Z_MM))
    inner = _cylinder_x(id_mm / 2.0, length_mm + 0.04, (center_x_mm, 0.0, LATCH_AXIS_Z_MM))
    ring = outer.cut(inner)
    if not ring.val().isValid() or len(ring.val().Solids()) != 1 or ring.val().Volume() <= 0.0:
        raise RetentionQuickReleaseTactileError("X-axis ring must be one valid solid")
    return ring


def _intersection(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise RetentionQuickReleaseTactileError("invalid intersection volume")
    return 0.0 if value < TOL_MM3 else value


def _rounded_grip() -> cq.Workplane:
    # Extrude the donor-sized YZ rectangle, then fillet only the four edges parallel
    # to X. This preserves the exact donor X/Y/Z envelope while rounding the touch
    # corners with CadQuery 2.8's supported 3-D fillet operation.
    grip = (
        cq.Workplane("YZ")
        .rect(GRIP_XYZ_MM[1], GRIP_XYZ_MM[2])
        .extrude(GRIP_XYZ_MM[0] / 2.0, both=True)
        .edges("|X")
        .fillet(GRIP_CORNER_RADIUS_MM)
        .translate((GRIP_CENTER_X_MM, 0.0, LATCH_AXIS_Z_MM))
    )
    if not grip.val().isValid() or len(grip.val().Solids()) != 1 or grip.val().Volume() <= 0.0:
        raise RetentionQuickReleaseTactileError("rounded quick-release grip is invalid")
    bb = grip.val().BoundingBox()
    expected = (
        GRIP_CENTER_X_MM - GRIP_XYZ_MM[0] / 2.0,
        GRIP_CENTER_X_MM + GRIP_XYZ_MM[0] / 2.0,
        -GRIP_XYZ_MM[1] / 2.0,
        GRIP_XYZ_MM[1] / 2.0,
        LATCH_AXIS_Z_MM - GRIP_XYZ_MM[2] / 2.0,
        LATCH_AXIS_Z_MM + GRIP_XYZ_MM[2] / 2.0,
    )
    actual = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    if any(abs(value - target) > 1e-9 for value, target in zip(actual, expected)):
        raise RetentionQuickReleaseTactileError("rounded grip changed donor package envelope")
    return grip


def _smooth_cam_tooth(preload: bool) -> cq.Workplane:
    z_offset = -DETENT_FREE_PRELOAD_INTRUSION_SEED_MM if preload else 0.0
    underside: list[tuple[float, float]] = []
    for index in range(CAM_SEGMENTS + 1):
        t = index / CAM_SEGMENTS
        s = 10.0 * t**3 - 15.0 * t**4 + 6.0 * t**5
        x = DETENT_TOOTH_X_MIN_MM + (DETENT_TOOTH_X_MAX_MM - DETENT_TOOTH_X_MIN_MM) * t
        z = (
            DETENT_TOOTH_BOTTOM_LEFT_Z_MM
            + (DETENT_TOOTH_BOTTOM_RIGHT_Z_MM - DETENT_TOOTH_BOTTOM_LEFT_Z_MM) * s
            + z_offset
        )
        underside.append((x, z))
    points = tuple(underside) + (
        (DETENT_TOOTH_X_MAX_MM, DETENT_TOOTH_TOP_Z_MM),
        (DETENT_TOOTH_X_MIN_MM, DETENT_TOOTH_TOP_Z_MM),
    )
    wp = cq.Workplane("XZ").moveTo(*points[0])
    for x, z in points[1:]:
        wp = wp.lineTo(x, z)
    tooth = wp.close().extrude(DETENT_TOOTH_WIDTH_Y_MM / 2.0, both=True)
    if not tooth.val().isValid() or len(tooth.val().Solids()) != 1 or tooth.val().Volume() <= 0.0:
        raise RetentionQuickReleaseTactileError("progressive cam tooth is invalid")
    return tooth


def _flexure(preload: bool) -> cq.Workplane:
    tooth = _smooth_cam_tooth(preload)
    beam = _box(FLEXURE_BEAM_XYZ_MM, FLEXURE_BEAM_CENTER_MM)
    anchor = _box(FLEXURE_ANCHOR_XYZ_MM, FLEXURE_ANCHOR_CENTER_MM)
    flexure = tooth.union(beam).union(anchor)
    if not flexure.val().isValid() or len(flexure.val().Solids()) != 1 or flexure.val().Volume() <= 0.0:
        raise RetentionQuickReleaseTactileError("flexure must remain one connected solid")
    return flexure


def _slider() -> cq.Workplane:
    pin = _cylinder_x(PIN_RADIUS_MM, PIN_LENGTH_MM, (LATCH_CENTER_X_MM, 0.0, LATCH_AXIS_Z_MM))
    pin_xmax = LATCH_CENTER_X_MM + PIN_LENGTH_MM / 2.0
    left_center = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM / 2.0
    neck_center = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM + SPOOL_NECK_LENGTH_MM / 2.0
    right_center = (
        SPOOL_START_X_MM
        + SPOOL_LEFT_LENGTH_MM
        + SPOOL_NECK_LENGTH_MM
        + SPOOL_RIGHT_LENGTH_MM / 2.0
    )
    spool = _cylinder_x(SPOOL_LEFT_RADIUS_MM, SPOOL_LEFT_LENGTH_MM, (left_center, 0.0, LATCH_AXIS_Z_MM))
    spool = spool.union(_cylinder_x(SPOOL_NECK_RADIUS_MM, SPOOL_NECK_LENGTH_MM, (neck_center, 0.0, LATCH_AXIS_Z_MM)))
    spool = spool.union(_cylinder_x(SPOOL_RIGHT_RADIUS_MM, SPOOL_RIGHT_LENGTH_MM, (right_center, 0.0, LATCH_AXIS_Z_MM)))
    spool_end = SPOOL_START_X_MM + SPOOL_LEFT_LENGTH_MM + SPOOL_NECK_LENGTH_MM + SPOOL_RIGHT_LENGTH_MM
    bridge_start = pin_xmax - SLIDER_JOIN_OVERLAP_MM
    bridge_end = SPOOL_START_X_MM + SLIDER_JOIN_OVERLAP_MM
    bridge = _cylinder_x(PIN_RADIUS_MM, bridge_end - bridge_start, ((bridge_start + bridge_end) / 2.0, 0.0, LATCH_AXIS_Z_MM))
    grip_min_x = GRIP_CENTER_X_MM - GRIP_XYZ_MM[0] / 2.0
    outer_stem_start = spool_end - SLIDER_JOIN_OVERLAP_MM
    outer_stem = _cylinder_x(PIN_RADIUS_MM, grip_min_x - outer_stem_start, ((outer_stem_start + grip_min_x) / 2.0, 0.0, LATCH_AXIS_Z_MM))

    rib_x0 = outer_stem_start + 0.08
    rib_x1 = grip_min_x - 0.04
    rib = _box(
        (rib_x1 - rib_x0, ANTI_ROTATION_RIB_WIDTH_Y_MM, ANTI_ROTATION_RIB_DEPTH_Z_MM + ANTI_ROTATION_RIB_ROOT_OVERLAP_MM),
        (
            (rib_x0 + rib_x1) / 2.0,
            0.0,
            LATCH_AXIS_Z_MM - PIN_RADIUS_MM - ANTI_ROTATION_RIB_DEPTH_Z_MM / 2.0 + ANTI_ROTATION_RIB_ROOT_OVERLAP_MM / 2.0,
        ),
    )
    slider = pin.union(bridge).union(spool).union(outer_stem).union(rib).union(_rounded_grip())
    if not slider.val().isValid() or len(slider.val().Solids()) != 1 or slider.val().Volume() <= 0.0:
        raise RetentionQuickReleaseTactileError("keyed slider must be one connected manufactured solid")
    return slider


def _guide_base() -> cq.Workplane:
    outer = _box(CAPSULE_XYZ_MM, (CAPSULE_CENTER_X_MM, 0.0, LATCH_AXIS_Z_MM))
    cavity = _box(CAVITY_XYZ_MM, (CAVITY_CENTER_X_MM, 0.0, LATCH_AXIS_Z_MM))
    stem_bore = _cylinder_x(BORE_RADIUS_MM, CAPSULE_XYZ_MM[0] + 2.0, (CAPSULE_CENTER_X_MM, 0.0, LATCH_AXIS_Z_MM))
    tooth_window = _box((1.6, 3.2, 4.5), ((DETENT_TOOTH_X_MIN_MM + DETENT_TOOTH_X_MAX_MM) / 2.0, 0.0, -16.6))
    guide = outer.cut(cavity).cut(stem_bore).cut(tooth_window)

    # Add four integral bearing lands in the cavity. Open corners remain debris paths.
    cavity_half = CAVITY_XYZ_MM[1] / 2.0
    intrusion = cavity_half - SPOOL_RAIL_INNER_RADIUS_MM
    rail_depth = intrusion + SPOOL_RAIL_ROOT_MM
    rail_x = CAVITY_XYZ_MM[0] - 2.0 * SPOOL_RAIL_X_MARGIN_MM
    for side in (-1.0, 1.0):
        y_rail = _box(
            (rail_x, rail_depth, SPOOL_RAIL_TANGENTIAL_WIDTH_MM),
            (
                CAVITY_CENTER_X_MM,
                side * (cavity_half - intrusion / 2.0 + SPOOL_RAIL_ROOT_MM / 2.0),
                LATCH_AXIS_Z_MM,
            ),
        )
        z_rail = _box(
            (rail_x, SPOOL_RAIL_TANGENTIAL_WIDTH_MM, rail_depth),
            (
                CAVITY_CENTER_X_MM,
                0.0,
                LATCH_AXIS_Z_MM + side * (cavity_half - intrusion / 2.0 + SPOOL_RAIL_ROOT_MM / 2.0),
            ),
        )
        guide = guide.union(y_rail).union(z_rail)

    # Slot is only material-critical at the outboard wall; extending the cutter through
    # the cavity keeps the release sweep simple and avoids a hidden rubbing edge.
    slot = _box(
        (
            CAPSULE_XYZ_MM[0] + 0.20,
            ANTI_ROTATION_SLOT_WIDTH_Y_MM,
            ANTI_ROTATION_SLOT_DEPTH_Z_MM,
        ),
        (
            CAPSULE_CENTER_X_MM,
            0.0,
            LATCH_AXIS_Z_MM - PIN_RADIUS_MM - ANTI_ROTATION_SLOT_DEPTH_Z_MM / 2.0 + 0.03,
        ),
    )
    guide = guide.cut(slot)
    return guide


def _stop_bumper(free: bool, inboard: bool) -> cq.Workplane:
    wall_x = CAVITY_CENTER_X_MM - CAVITY_XYZ_MM[0] / 2.0 if inboard else CAVITY_CENTER_X_MM + CAVITY_XYZ_MM[0] / 2.0
    direction = 1.0 if inboard else -1.0
    if free:
        center_x = wall_x + direction * (STOP_BUMPER_FREE_PROTRUSION_MM - STOP_BUMPER_ROOT_DEPTH_MM) / 2.0
        neck = _ring_x(
            STOP_BUMPER_NECK_OD_MM,
            STOP_BUMPER_ID_MM,
            STOP_BUMPER_TOTAL_THICKNESS_MM,
            center_x,
        )
        root_center = wall_x - direction * (STOP_BUMPER_ROOT_DEPTH_MM - STOP_BUMPER_ROOT_THICKNESS_MM / 2.0)
        root = _ring_x(STOP_BUMPER_ROOT_OD_MM, STOP_BUMPER_ID_MM, STOP_BUMPER_ROOT_THICKNESS_MM, root_center)
        return neck.union(root)
    center_x = wall_x - direction * STOP_BUMPER_ROOT_DEPTH_MM / 2.0
    return _ring_x(STOP_BUMPER_NECK_OD_MM, STOP_BUMPER_ID_MM, STOP_BUMPER_ROOT_DEPTH_MM, center_x)


def _guide_with_bumper_pockets() -> tuple[cq.Workplane, tuple[cq.Workplane, cq.Workplane]]:
    guide = _guide_base()
    free = (_stop_bumper(True, True), _stop_bumper(True, False))
    before = float(guide.val().Volume())
    for bumper in free:
        guide = guide.cut(bumper)
    if not guide.val().isValid() or len(guide.val().Solids()) != 1 or guide.val().Volume() <= 0.0:
        raise RetentionQuickReleaseTactileError("bumper pockets invalidated guide")
    if before - float(guide.val().Volume()) <= 0.0:
        raise RetentionQuickReleaseTactileError("bumper roots must remove positive guide material")
    return guide, free


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactile:
    slider: cq.Workplane
    guide: cq.Workplane
    flexure_free: cq.Workplane
    flexure_installed_reference: cq.Workplane
    bumper_free_regions: tuple[cq.Workplane, cq.Workplane] = field(repr=False)
    bumper_installed_references: tuple[cq.Workplane, cq.Workplane] = field(repr=False)
    rail_radial_clearance_mm: float = 0.0
    anti_rotation_side_clearance_mm: float = 0.0
    flexure_free_slider_interference_mm3: float = 0.0
    flexure_installed_slider_interference_mm3: float = 0.0
    inboard_bumper_free_interference_mm3: float = 0.0
    outboard_bumper_free_interference_mm3: float = 0.0
    inboard_bumper_installed_interference_mm3: float = 0.0
    outboard_bumper_installed_interference_mm3: float = 0.0
    rigid_inboard_overtravel_intersection_mm3: float = 0.0
    rigid_outboard_overtravel_intersection_mm3: float = 0.0
    physical_validation_eligible: bool = False

    def validate(self) -> "RetentionQuickReleaseTactile":
        graph = build_mechanical_interface_graph()
        donor = next(source for source in graph.sources if source.source_id == "QUICK_RELEASE_V1")
        if donor.status != "HISTORICAL_DONOR" or donor.head_sha != HISTORICAL_DONOR_HEAD_SHA:
            raise RetentionQuickReleaseTactileError("historical quick-release donor identity changed")
        if self.physical_validation_eligible:
            raise RetentionQuickReleaseTactileError("digital quick-release candidate is not physical validation")
        if not (0.0 < self.rail_radial_clearance_mm <= MAX_SPOOL_RAIL_RADIAL_CLEARANCE_MM):
            raise RetentionQuickReleaseTactileError("spool rail clearance outside low-play seed")
        if not (0.0 < self.anti_rotation_side_clearance_mm <= MAX_ANTI_ROTATION_SIDE_CLEARANCE_MM):
            raise RetentionQuickReleaseTactileError("anti-rotation slot clearance outside bounded seed")
        if self.flexure_free_slider_interference_mm3 <= 0.0:
            raise RetentionQuickReleaseTactileError("free flexure lost deliberate anti-chatter preload seed")
        if self.flexure_installed_slider_interference_mm3 > TOL_MM3:
            raise RetentionQuickReleaseTactileError("installed flexure reference rigidly overlaps slider")
        if min(self.inboard_bumper_free_interference_mm3, self.outboard_bumper_free_interference_mm3) < MIN_FREE_BUMPER_INTERFERENCE_MM3:
            raise RetentionQuickReleaseTactileError("free end bumper does not engage before hard wall")
        if max(self.inboard_bumper_installed_interference_mm3, self.outboard_bumper_installed_interference_mm3) > TOL_MM3:
            raise RetentionQuickReleaseTactileError("installed bumper reference overlaps endpoint slider")
        if min(self.rigid_inboard_overtravel_intersection_mm3, self.rigid_outboard_overtravel_intersection_mm3) <= 0.0:
            raise RetentionQuickReleaseTactileError("independent rigid hard-stop overtravel probes lost")
        for shape in (self.slider, self.guide, self.flexure_free, self.flexure_installed_reference):
            if not shape.val().isValid() or len(shape.val().Solids()) != 1 or shape.val().Volume() <= 0.0:
                raise RetentionQuickReleaseTactileError("quick-release material/reference must be one valid solid")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "owner_branch": OWNER_BRANCH,
            "owner_head_at_refinement_start": OWNER_HEAD_AT_REFINEMENT_START,
            "historical_donor_pr": HISTORICAL_DONOR_PR,
            "historical_donor_head_sha": HISTORICAL_DONOR_HEAD_SHA,
            "graph_promotion_status": "NOT_PROMOTED_HISTORICAL_DONOR_REMAINS_REFERENCE_UNTIL_OWNER_INTEGRATION",
            "release_travel_mm": RELEASE_TRAVEL_MM,
            "guidance": {
                "legacy_flange_to_cavity_radial_float_mm": CAVITY_XYZ_MM[1] / 2.0 - SPOOL_LEFT_RADIUS_MM,
                "new_integral_rail_radial_clearance_mm": self.rail_radial_clearance_mm,
                "open_corner_debris_paths": 4,
                "anti_rotation_rib_integral_to_slider": True,
                "anti_rotation_side_clearance_mm": self.anti_rotation_side_clearance_mm,
            },
            "detent": {
                "cam_profile": f"{CAM_SEGMENTS}_SEGMENT_QUINTIC_SMOOTHSTEP_APPROXIMATION",
                "manufactured_free_preload_intrusion_seed_mm": DETENT_FREE_PRELOAD_INTRUSION_SEED_MM,
                "nominal_interference_seed_mm": DETENT_NOMINAL_INTERFERENCE_SEED_MM,
                "free_slider_interference_mm3": self.flexure_free_slider_interference_mm3,
                "installed_rigid_interference_mm3": self.flexure_installed_slider_interference_mm3,
                "force_validated": False,
            },
            "end_state_damping": {
                "free_protrusion_mm": STOP_BUMPER_FREE_PROTRUSION_MM,
                "mechanically_keyed_root_depth_mm": STOP_BUMPER_ROOT_DEPTH_MM,
                "inboard_free_interference_mm3": self.inboard_bumper_free_interference_mm3,
                "outboard_free_interference_mm3": self.outboard_bumper_free_interference_mm3,
                "installed_interference_mm3": [
                    self.inboard_bumper_installed_interference_mm3,
                    self.outboard_bumper_installed_interference_mm3,
                ],
                "rigid_hard_stops_preserved": True,
            },
            "user_touch": {
                "grip_envelope_preserved": True,
                "profile": "ROUNDED_RECTANGLE_FINE_SATIN_QUALITY_ENGINEERING_POLYMER",
                "surface_direction": "SHELL_MATCHED_PREMIUM_TOUCH_FINISH_NO_RUBBERIZED_DEGRADABLE_COATING",
            },
            "interaction_sequence": (
                "LOW_PLAY_KEYED_GUIDANCE -> PROGRESSIVE_CAM_FORCE_BUILD -> DECISIVE_RELEASE -> "
                "LOW_FRICTION_WITHDRAWAL -> PROGRESSIVE_END_BUMPER -> RIGID_ABUSE_STOP"
            ),
            "cost_rule": (
                "INTEGRAL_GUIDE_RAILS_AND_ANTI_ROTATION_RIB_PLUS_TWO_SMALL_OVERMOLDED_STOP_RINGS; "
                "NO_BEARINGS_NO_MACHINED_CARRIER_NO_EXTRA_ADJUSTER"
            ),
            "tactile_reference_rule": "S_T_DUPONT_LIGNE_2_PRECISION_FEEL_ONLY_NOT_SOUND_OR_MECHANISM_COPY",
            "whole_head_removal": "UNRESOLVED",
            "physical_validation_eligible": False,
            "physical_validation": (
                "OPEN_RELEASE_FORCE_RELEASE_TIME_WET_ONE_HAND_USE_CAM_FLEXURE_STRAIN_FATIGUE_GUIDE_FRICTION_"
                "WEAR_DEBRIS_JAM_MARGIN_BUMPER_DUROMETER_COMPRESSION_SET_REBOUND_NOISE_ACCIDENTAL_RELEASE_"
                "RETENTION_FIT_WHOLE_HEAD_REMOVAL_LIFETIME_AND_SUBJECTIVE_FEEL"
            ),
        }
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile() -> RetentionQuickReleaseTactile:
    slider = _slider()
    guide, bumpers_free = _guide_with_bumper_pockets()
    flexure_free = _flexure(True)
    flexure_installed = _flexure(False)

    # Installed material path uses the deformed reference for collision screening.
    installed_slider_flex = _intersection(slider, flexure_installed)
    free_slider_flex = _intersection(slider, flexure_free)

    released = slider.translate((RELEASE_TRAVEL_MM, 0.0, 0.0))
    bumpers_installed = (_stop_bumper(False, True), _stop_bumper(False, False))
    in_free = _intersection(slider, bumpers_free[0])
    out_free = _intersection(released, bumpers_free[1])
    in_inst = _intersection(slider, bumpers_installed[0])
    out_inst = _intersection(released, bumpers_installed[1])

    # Guide body excludes the compliant bumper roots. Endpoint slider should otherwise
    # remain clear; 0.05 mm beyond each hard plane must hit positive guide material.
    if _intersection(slider, guide) > TOL_MM3 or _intersection(released, guide) > TOL_MM3:
        raise RetentionQuickReleaseTactileError("slider intersects rigid guide at a nominal endpoint")
    in_probe = slider.translate((-0.05, 0.0, 0.0))
    out_probe = released.translate((0.05, 0.0, 0.0))
    in_hard = _intersection(in_probe, guide)
    out_hard = _intersection(out_probe, guide)

    result = RetentionQuickReleaseTactile(
        slider,
        guide,
        flexure_free,
        flexure_installed,
        bumpers_free,
        bumpers_installed,
        SPOOL_RAIL_RADIAL_CLEARANCE_MM,
        ANTI_ROTATION_SIDE_CLEARANCE_MM,
        round(free_slider_flex, 9),
        round(installed_slider_flex, 9),
        round(in_free, 9),
        round(out_free, 9),
        round(in_inst, 9),
        round(out_inst, 9),
        round(in_hard, 9),
        round(out_hard, 9),
        False,
    )
    return result.validate()