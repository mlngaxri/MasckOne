from __future__ import annotations

"""Cell 3 bounded occipital retention-fit adjustment geometry.

This module is a stacked successor to the paired occipital yokes. It realizes a small
indexed mechanism range only; it does not define or claim an anthropometric or universal
fit range. Adjustment is permitted only while the product is unworn and unpowered.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path

import cadquery as cq

from .authority import Authority, load_authority
from .model import MasckOneModel, build_model
from .occipital_stabilizer import (
    AUTHORITY_REVISION,
    PAD_BACKER_XYZ_MM,
    PAD_CENTER_X_MM,
    PAD_CENTER_Y_MM,
    PAD_CENTER_Z_MM,
    RAIL_END_X_MM,
    RAIL_END_Z_MM,
    RAIL_LOWER_Y_MM,
    RAIL_RADIUS_MM,
    RAIL_UPPER_Y_MM,
    ROOT_BOSS_XYZ_MM,
    SOURCE_AUTHORITY_BLOB_SHA,
    SOURCE_MAIN_SHA,
    WORLD_FRAME_ID,
    OccipitalStabilizer,
    StabilizerPart,
    build_occipital_stabilizer,
)
from .realized_waste_backbone_release import build_current_cell4_waste_backbone_release

SCHEMA = "MASCK_ONE_CELL3_RETENTION_FIT_ADJUSTMENT_V1"
SOURCE_OCCIPITAL_GIT_BLOB_SHA = "1139b675c4758d8580cf5a18fa7a0b87b2d6ef99"
DIGITAL_ONLY = "DIGITAL_BOUNDED_RETENTION_ADJUSTMENT_NOT_FIT_OR_COMFORT_VALIDATION"
KERNEL_ZERO_MM3 = 1e-8

# Provisional Cell 3 mechanism dimensions. These are CAD seeds, not anthropometric,
# supplier, production-tolerance, comfort or validated fit dimensions.
INDEX_OFFSETS_MM = (-2.0, 0.0, 2.0)
HARD_STOP_TRAVEL_MM = 2.0
OVERTRAVEL_PROBE_MM = 0.05

TONGUE_LENGTH_MM = 12.0
TONGUE_Y_MM = 4.5
TONGUE_Z_MM = 6.0
TONGUE_CENTER_OUTBOARD_FROM_ROOT_MM = 8.0

HOUSING_CENTER_OUTBOARD_FROM_ROOT_MM = 10.5
HOUSING_X_MM = 7.0
CHANNEL_CLEARANCE_Y_MM = 0.25
CHANNEL_CLEARANCE_Z_MM = 0.25
HOUSING_WALL_Y_MM = 2.0
HOUSING_WALL_Z_MM = 2.0

STOP_PIN_X_OUTBOARD_FROM_ROOT_MM = 9.5
STOP_PIN_Z_MM = -32.35
STOP_PIN_RADIUS_MM = 0.95
STOP_PIN_BORE_RADIUS_MM = 1.10
STOP_SLOT_Z_MM = 2.15
STOP_PIN_HEAD_RADIUS_MM = 1.90
STOP_PIN_HEAD_LENGTH_MM = 1.20
STOP_PIN_GROOVE_RADIUS_MM = 0.72
STOP_PIN_GROOVE_LENGTH_MM = 0.80
STOP_PIN_TIP_LENGTH_MM = 0.80
STOP_CLIP_OUTER_RADIUS_MM = 1.70
STOP_CLIP_INNER_RADIUS_MM = 0.78
STOP_CLIP_THICKNESS_MM = 0.55
STOP_CLIP_GAP_MM = 1.40

INDEX_PIN_X_OUTBOARD_FROM_ROOT_MM = 11.5
INDEX_PIN_Z_MM = -29.55
INDEX_PIN_RADIUS_MM = 0.70
INDEX_PIN_BORE_RADIUS_MM = 0.82
INDEX_PIN_HEAD_RADIUS_MM = 1.80
INDEX_PIN_HEAD_LENGTH_MM = 1.40
INDEX_PIN_RETRACTION_MM = 8.10

SERVICE_SEQUENCE_ID = "MASK_REMOVED_UNPOWERED_INDEX_PIN_RETRACT_TRANSLATE_RESEAT"


class RetentionFitAdjustmentError(ValueError):
    pass


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise RetentionFitAdjustmentError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise RetentionFitAdjustmentError(f"{label} must be finite")
    return 0.0 if result == 0.0 else result


def _positive(value: object, label: str) -> float:
    result = _finite(value, label)
    if result <= 0.0:
        raise RetentionFitAdjustmentError(f"{label} must be positive")
    return result


def _single(solid: cq.Workplane, label: str) -> cq.Workplane:
    shape = solid.val()
    if not shape.isValid() or float(shape.Volume()) <= 0.0 or len(shape.Solids()) != 1:
        raise RetentionFitAdjustmentError(f"{label} must be one valid positive-volume solid")
    return solid


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> cq.Workplane:
    x, y, z = (_positive(value, "box dimension") for value in size)
    return cq.Workplane("XY").box(x, y, z, centered=(True, True, True)).translate(center)


def _cylinder(
    radius_mm: float,
    length_mm: float,
    center: tuple[float, float, float],
    axis_xyz: tuple[float, float, float],
) -> cq.Workplane:
    radius = _positive(radius_mm, "cylinder radius")
    length = _positive(length_mm, "cylinder length")
    ax, ay, az = (_finite(value, "cylinder axis") for value in axis_xyz)
    norm = math.sqrt(ax * ax + ay * ay + az * az)
    if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise RetentionFitAdjustmentError("cylinder axis must be unit length")
    cx, cy, cz = center
    start = (
        cx - ax * length / 2.0,
        cy - ay * length / 2.0,
        cz - az * length / 2.0,
    )
    shape = cq.Solid.makeCylinder(radius, length, cq.Vector(*start), cq.Vector(ax, ay, az))
    return cq.Workplane("XY").newObject([shape])


def _bbox(solid: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = solid.val().BoundingBox()
    return tuple(
        round(float(value), 6)
        for value in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    )


def _intersection_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise RetentionFitAdjustmentError("intersection volume must be finite and nonnegative")
    return 0.0 if value < KERNEL_ZERO_MM3 else value


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    return sha1(header + raw).hexdigest()


def _assert_occipital_source_blob() -> None:
    path = Path(__file__).with_name("occipital_stabilizer.py")
    observed = _git_blob_sha(path)
    if observed != SOURCE_OCCIPITAL_GIT_BLOB_SHA:
        raise RetentionFitAdjustmentError(
            "occipital source blob changed; retention-fit adjustment requires explicit rebind"
        )


def _datum_center(stabilizer: OccipitalStabilizer, datum_id: str) -> tuple[float, float, float]:
    for datum in stabilizer.datums:
        if datum.datum_id == datum_id:
            return tuple(float(value) for value in datum.center_xyz_mm)
    raise RetentionFitAdjustmentError(f"missing occipital source datum {datum_id}")


def _protected_solid(model: MasckOneModel, index: int) -> tuple[str, cq.Workplane]:
    volume = model.protected_volumes.all[index]
    zone = volume.zone
    wp = cq.Workplane("XY").workplane(offset=-80.0).center(zone.center.x, zone.center.y)
    if zone.shape == "CIRCLE":
        solid = wp.circle(zone.envelope_width_mm / 2.0).extrude(120.0)
    else:
        solid = wp.ellipse(zone.envelope_width_mm / 2.0, zone.envelope_height_mm / 2.0).extrude(120.0)
    if zone.angle_deg:
        solid = solid.rotate(
            (zone.center.x, zone.center.y, 0.0),
            (zone.center.x, zone.center.y, 1.0),
            zone.angle_deg,
        )
    return zone.zone_id, solid


def _route_service_aabb(route) -> cq.Workplane:
    bounds_min, bounds_max = route.bounds_xyz_mm
    radius = float(route.service_envelope_radius_mm)
    minimum = tuple(float(value) - radius for value in bounds_min)
    maximum = tuple(float(value) + radius for value in bounds_max)
    size = tuple(maximum[i] - minimum[i] for i in range(3))
    center = tuple((maximum[i] + minimum[i]) / 2.0 for i in range(3))
    return _single(_box(size, center), f"{route.route_id} service AABB")


def _housing_dimensions() -> tuple[float, float, float, float, float]:
    channel_y = TONGUE_Y_MM + 2.0 * CHANNEL_CLEARANCE_Y_MM
    channel_z = TONGUE_Z_MM + 2.0 * CHANNEL_CLEARANCE_Z_MM
    outer_y = channel_y + 2.0 * HOUSING_WALL_Y_MM
    outer_z = channel_z + 2.0 * HOUSING_WALL_Z_MM
    return channel_y, channel_z, HOUSING_X_MM, outer_y, outer_z


def _build_housing(side_sign: int, root: tuple[float, float, float]) -> cq.Workplane:
    root_x, root_y, root_z = root
    channel_y, channel_z, outer_x, outer_y, outer_z = _housing_dimensions()
    center = (
        root_x + side_sign * HOUSING_CENTER_OUTBOARD_FROM_ROOT_MM,
        root_y,
        root_z,
    )
    housing = _box((outer_x, outer_y, outer_z), center)
    through_channel = _box((outer_x + 2.0, channel_y, channel_z), center)
    housing = housing.cut(through_channel)

    stop_x = root_x + side_sign * STOP_PIN_X_OUTBOARD_FROM_ROOT_MM
    index_x = root_x + side_sign * INDEX_PIN_X_OUTBOARD_FROM_ROOT_MM
    housing = housing.cut(
        _cylinder(STOP_PIN_BORE_RADIUS_MM, outer_y + 2.0, (stop_x, root_y, STOP_PIN_Z_MM), (0.0, 1.0, 0.0))
    )
    housing = housing.cut(
        _cylinder(INDEX_PIN_BORE_RADIUS_MM, outer_y + 2.0, (index_x, root_y, INDEX_PIN_Z_MM), (0.0, 1.0, 0.0))
    )
    return _single(housing, "retention adjustment guide housing")


def _build_nominal_successor_yoke(
    source_part: StabilizerPart,
    side_sign: int,
    root: tuple[float, float, float],
) -> cq.Workplane:
    root_x, root_y, root_z = root
    tongue_center = (
        root_x + side_sign * TONGUE_CENTER_OUTBOARD_FROM_ROOT_MM,
        root_y,
        root_z,
    )
    tongue = _box((TONGUE_LENGTH_MM, TONGUE_Y_MM, TONGUE_Z_MM), tongue_center)

    stop_x = root_x + side_sign * STOP_PIN_X_OUTBOARD_FROM_ROOT_MM
    stop_slot_x = 2.0 * HARD_STOP_TRAVEL_MM + 2.0 * STOP_PIN_RADIUS_MM
    stop_slot = _box(
        (stop_slot_x, TONGUE_Y_MM + 2.0, STOP_SLOT_Z_MM),
        (stop_x, root_y, STOP_PIN_Z_MM),
    )
    tongue = tongue.cut(stop_slot)

    index_x = root_x + side_sign * INDEX_PIN_X_OUTBOARD_FROM_ROOT_MM
    for offset in INDEX_OFFSETS_MM:
        hole_x = index_x - side_sign * offset
        tongue = tongue.cut(
            _cylinder(
                INDEX_PIN_BORE_RADIUS_MM,
                TONGUE_Y_MM + 2.0,
                (hole_x, root_y, INDEX_PIN_Z_MM),
                (0.0, 1.0, 0.0),
            )
        )

    successor = source_part.solid.union(tongue)
    return _single(successor, f"{source_part.part_id} fit-adjustment successor")


def _build_stop_pin_body(root: tuple[float, float, float], side_sign: int) -> cq.Workplane:
    root_x, root_y, _ = root
    _, _, _, outer_y, _ = _housing_dimensions()
    x = root_x + side_sign * STOP_PIN_X_OUTBOARD_FROM_ROOT_MM

    main_start_y = root_y - outer_y / 2.0 - 1.70
    main_end_y = root_y + outer_y / 2.0 + 1.50
    groove_start_y = main_start_y - STOP_PIN_GROOVE_LENGTH_MM
    tip_start_y = groove_start_y - STOP_PIN_TIP_LENGTH_MM

    main = _cylinder(
        STOP_PIN_RADIUS_MM,
        main_end_y - main_start_y,
        (x, (main_end_y + main_start_y) / 2.0, STOP_PIN_Z_MM),
        (0.0, 1.0, 0.0),
    )
    groove = _cylinder(
        STOP_PIN_GROOVE_RADIUS_MM,
        STOP_PIN_GROOVE_LENGTH_MM,
        (x, (main_start_y + groove_start_y) / 2.0, STOP_PIN_Z_MM),
        (0.0, 1.0, 0.0),
    )
    tip = _cylinder(
        STOP_PIN_RADIUS_MM,
        STOP_PIN_TIP_LENGTH_MM,
        (x, (groove_start_y + tip_start_y) / 2.0, STOP_PIN_Z_MM),
        (0.0, 1.0, 0.0),
    )
    head = _cylinder(
        STOP_PIN_HEAD_RADIUS_MM,
        STOP_PIN_HEAD_LENGTH_MM,
        (x, main_end_y + STOP_PIN_HEAD_LENGTH_MM / 2.0, STOP_PIN_Z_MM),
        (0.0, 1.0, 0.0),
    )
    return _single(main.union(groove).union(tip).union(head), "permanent stop pin body")


def _build_stop_pin_clip(root: tuple[float, float, float], side_sign: int) -> cq.Workplane:
    root_x, root_y, _ = root
    _, _, _, outer_y, _ = _housing_dimensions()
    x = root_x + side_sign * STOP_PIN_X_OUTBOARD_FROM_ROOT_MM
    main_start_y = root_y - outer_y / 2.0 - 1.70
    groove_center_y = main_start_y - STOP_PIN_GROOVE_LENGTH_MM / 2.0

    ring = (
        cq.Workplane("XZ", origin=(x, groove_center_y, STOP_PIN_Z_MM))
        .circle(STOP_CLIP_OUTER_RADIUS_MM)
        .circle(STOP_CLIP_INNER_RADIUS_MM)
        .extrude(STOP_CLIP_THICKNESS_MM / 2.0, both=True)
    )
    gap = _box(
        (STOP_CLIP_GAP_MM, STOP_CLIP_THICKNESS_MM + 1.0, STOP_CLIP_OUTER_RADIUS_MM * 1.4),
        (x + side_sign * STOP_CLIP_OUTER_RADIUS_MM, groove_center_y, STOP_PIN_Z_MM),
    )
    return _single(ring.cut(gap), "stop-pin retaining C-clip")


def _build_index_pin(
    root: tuple[float, float, float],
    side_sign: int,
    *,
    retracted: bool,
) -> cq.Workplane:
    root_x, root_y, _ = root
    _, _, _, outer_y, _ = _housing_dimensions()
    x = root_x + side_sign * INDEX_PIN_X_OUTBOARD_FROM_ROOT_MM
    shift_y = INDEX_PIN_RETRACTION_MM if retracted else 0.0
    shaft_length = outer_y + 2.0
    shaft_center_y = root_y + shift_y
    shaft = _cylinder(
        INDEX_PIN_RADIUS_MM,
        shaft_length,
        (x, shaft_center_y, INDEX_PIN_Z_MM),
        (0.0, 1.0, 0.0),
    )
    head = _cylinder(
        INDEX_PIN_HEAD_RADIUS_MM,
        INDEX_PIN_HEAD_LENGTH_MM,
        (x, shaft_center_y + shaft_length / 2.0 + INDEX_PIN_HEAD_LENGTH_MM / 2.0, INDEX_PIN_Z_MM),
        (0.0, 1.0, 0.0),
    )
    return _single(shaft.union(head), "service index pin")


def _translated(solid: cq.Workplane, dx_mm: float) -> cq.Workplane:
    return _single(solid.translate((dx_mm, 0.0, 0.0)), "translated retention adjustment state")


def _box_from_bounds(
    minimum: tuple[float, float, float],
    maximum: tuple[float, float, float],
    label: str,
) -> cq.Workplane:
    size = tuple(maximum[i] - minimum[i] for i in range(3))
    center = tuple((minimum[i] + maximum[i]) / 2.0 for i in range(3))
    return _single(_box(size, center), label)


def _feature_translation_envelope(
    side_sign: int,
    root: tuple[float, float, float],
) -> cq.Workplane:
    """Conservative connected union of per-feature complete pure-X motion bounds.

    A single whole-yoke AABB would fill the empty space between the fork rails and can
    falsely collide with facial protected volumes. Each box here bounds one actual source
    feature for every translation in the closed +/-2 mm interval, and the boxes overlap
    through the real root/rail/pad/tongue connectivity. The union is therefore a
    conservative continuous-motion bound without inventing the large inter-feature voids.
    """

    root_x, root_y, root_z = root
    expand = HARD_STOP_TRAVEL_MM
    parts: list[cq.Workplane] = []

    root_half = tuple(float(value) / 2.0 for value in ROOT_BOSS_XYZ_MM)
    parts.append(
        _box_from_bounds(
            (root_x - root_half[0] - expand, root_y - root_half[1], root_z - root_half[2]),
            (root_x + root_half[0] + expand, root_y + root_half[1], root_z + root_half[2]),
            "root-boss complete translation bound",
        )
    )

    pad_center = (side_sign * PAD_CENTER_X_MM, PAD_CENTER_Y_MM, PAD_CENTER_Z_MM)
    pad_half = tuple(float(value) / 2.0 for value in PAD_BACKER_XYZ_MM)
    parts.append(
        _box_from_bounds(
            (
                pad_center[0] - pad_half[0] - expand,
                pad_center[1] - pad_half[1],
                pad_center[2] - pad_half[2],
            ),
            (
                pad_center[0] + pad_half[0] + expand,
                pad_center[1] + pad_half[1],
                pad_center[2] + pad_half[2],
            ),
            "contact-backer complete translation bound",
        )
    )

    for rail_name, rail_end_y in (("upper", RAIL_UPPER_Y_MM), ("lower", RAIL_LOWER_Y_MM)):
        end = (side_sign * RAIL_END_X_MM, rail_end_y, RAIL_END_Z_MM)
        minimum = (
            min(root_x, end[0]) - RAIL_RADIUS_MM - expand,
            min(root_y, end[1]) - RAIL_RADIUS_MM,
            min(root_z, end[2]) - RAIL_RADIUS_MM,
        )
        maximum = (
            max(root_x, end[0]) + RAIL_RADIUS_MM + expand,
            max(root_y, end[1]) + RAIL_RADIUS_MM,
            max(root_z, end[2]) + RAIL_RADIUS_MM,
        )
        parts.append(_box_from_bounds(minimum, maximum, f"{rail_name} rail complete translation bound"))

    tongue_center = (
        root_x + side_sign * TONGUE_CENTER_OUTBOARD_FROM_ROOT_MM,
        root_y,
        root_z,
    )
    parts.append(
        _box_from_bounds(
            (
                tongue_center[0] - TONGUE_LENGTH_MM / 2.0 - expand,
                tongue_center[1] - TONGUE_Y_MM / 2.0,
                tongue_center[2] - TONGUE_Z_MM / 2.0,
            ),
            (
                tongue_center[0] + TONGUE_LENGTH_MM / 2.0 + expand,
                tongue_center[1] + TONGUE_Y_MM / 2.0,
                tongue_center[2] + TONGUE_Z_MM / 2.0,
            ),
            "tongue complete translation bound",
        )
    )

    result = parts[0]
    for part in parts[1:]:
        result = result.union(part)
    return _single(result, "connected per-feature complete fit-adjustment translation envelope")


def _two_state_aabb(first: cq.Workplane, second: cq.Workplane, label: str) -> cq.Workplane:
    a = _bbox(first)
    b = _bbox(second)
    minimum = (min(a[0], b[0]), min(a[2], b[2]), min(a[4], b[4]))
    maximum = (max(a[1], b[1]), max(a[3], b[3]), max(a[5], b[5]))
    return _box_from_bounds(minimum, maximum, label)


@dataclass(frozen=True, slots=True)
class AdjustmentState:
    state_id: str
    side: str
    side_sign: int
    offset_mm: float
    world_dx_mm: float
    successor_yoke: cq.Workplane
    contact_backer_center_xyz_mm: tuple[float, float, float]

    def manifest(self) -> dict[str, object]:
        return {
            "state_id": self.state_id,
            "side": self.side,
            "offset_mm": self.offset_mm,
            "offset_semantics": "NEGATIVE_TOWARD_SAGITTAL_POSITIVE_OUTWARD",
            "world_dx_mm": self.world_dx_mm,
            "successor_yoke_bounds_mm": list(_bbox(self.successor_yoke)),
            "successor_yoke_volume_mm3": round(float(self.successor_yoke.val().Volume()), 6),
            "contact_backer_center_xyz_mm": list(self.contact_backer_center_xyz_mm),
        }


@dataclass(frozen=True, slots=True)
class AdjustmentSide:
    side: str
    side_sign: int
    root_xyz_mm: tuple[float, float, float]
    housing: cq.Workplane
    stop_pin: cq.Workplane
    stop_pin_clip: cq.Workplane
    index_pin_engaged: cq.Workplane
    index_pin_retracted: cq.Workplane
    index_pin_retraction_envelope: cq.Workplane
    nominal_successor_yoke: cq.Workplane
    complete_translation_envelope: cq.Workplane
    states: tuple[AdjustmentState, ...]

    def state_for_offset(self, offset_mm: float) -> AdjustmentState:
        for state in self.states:
            if math.isclose(state.offset_mm, float(offset_mm), rel_tol=0.0, abs_tol=1e-12):
                return state
        raise KeyError(offset_mm)

    def manifest(self) -> dict[str, object]:
        return {
            "side": self.side,
            "root_xyz_mm": list(self.root_xyz_mm),
            "housing_bounds_mm": list(_bbox(self.housing)),
            "housing_volume_mm3": round(float(self.housing.val().Volume()), 6),
            "stop_pin_bounds_mm": list(_bbox(self.stop_pin)),
            "stop_pin_clip_bounds_mm": list(_bbox(self.stop_pin_clip)),
            "index_pin_engaged_bounds_mm": list(_bbox(self.index_pin_engaged)),
            "index_pin_retracted_bounds_mm": list(_bbox(self.index_pin_retracted)),
            "index_pin_retraction_envelope_bounds_mm": list(_bbox(self.index_pin_retraction_envelope)),
            "complete_translation_envelope_bounds_mm": list(_bbox(self.complete_translation_envelope)),
            "states": [state.manifest() for state in self.states],
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
class RetentionFitAdjustment:
    source_occipital_package_sha256: str
    source_waste_release_sha256: str
    left: AdjustmentSide
    right: AdjustmentSide
    collision_checks: tuple[CollisionCheck, ...]

    def __post_init__(self) -> None:
        if any(not check.passes for check in self.collision_checks):
            failed = tuple(check.check_id for check in self.collision_checks if not check.passes)
            raise RetentionFitAdjustmentError(f"required fit-adjustment clearance failed: {failed}")

    @property
    def package_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def service_sequence(
        self,
        target_offset_mm: float,
        *,
        worn: bool,
        powered: bool,
    ) -> tuple[dict[str, object], ...]:
        target = _finite(target_offset_mm, "target_offset_mm")
        if target not in INDEX_OFFSETS_MM:
            raise RetentionFitAdjustmentError("target must be one of the three indexed CAD positions")
        if worn:
            raise RetentionFitAdjustmentError("fit adjustment is prohibited while worn")
        if powered:
            raise RetentionFitAdjustmentError("fit adjustment is prohibited while powered")
        return (
            {"step": 1, "action": "CONFIRM_MASK_REMOVED_AND_UNPOWERED"},
            {
                "step": 2,
                "action": "RETRACT_INDEX_PIN_POSITIVE_Y",
                "travel_mm": INDEX_PIN_RETRACTION_MM,
                "stop_pin_remains_installed": True,
            },
            {
                "step": 3,
                "action": "TRANSLATE_OCCIPITAL_YOKE_WITHIN_STOP_PIN_SLOT",
                "target_offset_mm": target,
                "hard_stop_travel_mm": HARD_STOP_TRAVEL_MM,
            },
            {"step": 4, "action": "ALIGN_INDEX_HOLE"},
            {
                "step": 5,
                "action": "REINSERT_INDEX_PIN_NEGATIVE_Y",
                "wear_eligible_only_after_full_reseat": True,
            },
        )

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": SOURCE_MAIN_SHA,
            "source_authority_blob_sha": SOURCE_AUTHORITY_BLOB_SHA,
            "source_authority_revision": AUTHORITY_REVISION,
            "source_occipital_git_blob_sha": SOURCE_OCCIPITAL_GIT_BLOB_SHA,
            "source_occipital_package_sha256": self.source_occipital_package_sha256,
            "source_waste_release_sha256": self.source_waste_release_sha256,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "adjustment_architecture": {
                "type": "BILATERAL_INDEXED_OCCIPITAL_ROOT_TONGUE_GUIDE",
                "index_offsets_mm": list(INDEX_OFFSETS_MM),
                "hard_stop_travel_mm": HARD_STOP_TRAVEL_MM,
                "index_offset_semantics": "NEGATIVE_TOWARD_SAGITTAL_POSITIVE_OUTWARD",
                "continuous_motion_primary_proof": "CONNECTED_UNION_OF_PER_FEATURE_ANALYTIC_TRANSLATION_BOUNDS",
                "sampled_waypoints_primary_proof": False,
                "retention_during_adjustment": "PERMANENT_STOP_PIN_REMAINS_IN_LONGITUDINAL_SLOT",
                "index_lock": "REMOVABLE_SERVICE_INDEX_PIN_THROUGH_DISCRETE_TONGUE_HOLES",
                "friction_only_lock_allowed": False,
            },
            "functional_separation": {
                "facial_reaction": "UNCHANGED_FRONT_REACTION_SYSTEM",
                "occipital_stabilization": "SOURCE_YOKES_GAIN_BOUNDED_ROOT_ADJUSTMENT",
                "crown_support": "SEPARATE_SOURCE_CORRIDOR_UNCHANGED",
            },
            "sides": [self.left.manifest(), self.right.manifest()],
            "service_logic": {
                "sequence_id": SERVICE_SEQUENCE_ID,
                "worn_adjustment_allowed": False,
                "powered_adjustment_allowed": False,
                "index_pin_must_be_fully_seated_before_wear": True,
                "stop_pin_removed_during_user_adjustment": False,
                "service_pin_wet_hand_usability_validated": False,
                "adjustment_time_validated": False,
            },
            "fit_claim_boundary": {
                "anthropometric_head_range_mm": None,
                "universal_fit_claim": False,
                "comfort_claim": False,
                "preload_N": None,
                "pressure_distribution": None,
                "hair_interaction": "UNVALIDATED",
                "meaning_of_index_range": "PACKAGE_CONSTRAINED_PROVISIONAL_CAD_RANGE_ONLY",
            },
            "collision_checks": [check.manifest() for check in self.collision_checks],
            "four_zone_actuation_preserved": True,
            "physical_validation_eligible": False,
            "unresolved_physical_gates": [
                "ANTHROPOMETRIC_FIT_RANGE_AND_POPULATION_COVERAGE",
                "RETENTION_PRELOAD_CONTACT_PRESSURE_COMFORT_AND_HAIR_INTERACTION",
                "STOP_PIN_INDEX_PIN_HOUSING_AND_TONGUE_STRENGTH_STIFFNESS_FATIGUE_WEAR_AND_JAM",
                "C_CLIP_MATERIAL_INSTALLATION_RETENTION_AND_DURABILITY",
                "FRAME_SIDE_HOUSING_ATTACHMENT_AND_LOAD_PATH",
                "WET_SERVICE_PIN_USABILITY",
                "EMERGENCY_RELEASE_FORCE_5_TO_12_N_AND_TIME_LE_2_S",
                "WHOLE_HEAD_POST_RELEASE_REMOVAL",
            ],
            "evidence_status": DIGITAL_ONLY,
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def _build_side(
    source_part: StabilizerPart,
    source_contact_center: tuple[float, float, float],
    root: tuple[float, float, float],
    side_sign: int,
) -> AdjustmentSide:
    side = "WEARER_RIGHT" if side_sign > 0 else "WEARER_LEFT"
    nominal = _build_nominal_successor_yoke(source_part, side_sign, root)
    housing = _build_housing(side_sign, root)
    stop_pin = _build_stop_pin_body(root, side_sign)
    stop_clip = _build_stop_pin_clip(root, side_sign)
    index_engaged = _build_index_pin(root, side_sign, retracted=False)
    index_retracted = _build_index_pin(root, side_sign, retracted=True)
    index_envelope = _two_state_aabb(index_engaged, index_retracted, "complete index-pin retraction envelope")
    motion_envelope = _feature_translation_envelope(side_sign, root)

    states: list[AdjustmentState] = []
    for offset in INDEX_OFFSETS_MM:
        dx = side_sign * float(offset)
        state_yoke = _translated(nominal, dx)
        contact = (
            source_contact_center[0] + dx,
            source_contact_center[1],
            source_contact_center[2],
        )
        state_id = (
            f"{side}_INDEX_TIGHT"
            if offset < 0.0
            else f"{side}_INDEX_LOOSE"
            if offset > 0.0
            else f"{side}_INDEX_NOMINAL"
        )
        states.append(AdjustmentState(state_id, side, side_sign, float(offset), dx, state_yoke, contact))

    # Exact-state checks plus analytic conditions for the complete pure-X interval.
    for state in states:
        if _intersection_mm3(state.successor_yoke, housing) != 0.0:
            raise RetentionFitAdjustmentError(f"{state.state_id} collides with fixed guide housing")
        if _intersection_mm3(state.successor_yoke, stop_pin) != 0.0:
            raise RetentionFitAdjustmentError(f"{state.state_id} collides with permanent stop pin")
        if _intersection_mm3(state.successor_yoke, index_engaged) != 0.0:
            raise RetentionFitAdjustmentError(f"{state.state_id} index pin does not align with a discrete hole")

    non_index_probe = _translated(nominal, side_sign * 1.0)
    if _intersection_mm3(non_index_probe, index_engaged) <= 0.0:
        raise RetentionFitAdjustmentError("index pin must geometrically reject non-indexed intermediate position")

    for signed_probe in (-HARD_STOP_TRAVEL_MM - OVERTRAVEL_PROBE_MM, HARD_STOP_TRAVEL_MM + OVERTRAVEL_PROBE_MM):
        probe = _translated(nominal, side_sign * signed_probe)
        if _intersection_mm3(probe, stop_pin) <= 0.0:
            raise RetentionFitAdjustmentError("permanent stop pin must block 0.05 mm overtravel on both ends")

    # The source yoke itself stays medial to the fixed housing over the entire interval,
    # while only the added tongue traverses the channel. This proves continuous guide
    # clearance without sampled-waypoint promotion.
    source_bounds = _bbox(source_part.solid)
    housing_bounds = _bbox(housing)
    if side_sign > 0:
        continuous_source_gap = housing_bounds[0] - (source_bounds[1] + HARD_STOP_TRAVEL_MM)
    else:
        continuous_source_gap = (source_bounds[0] - HARD_STOP_TRAVEL_MM) - housing_bounds[1]
    if continuous_source_gap < 1.0 - 1e-9:
        raise RetentionFitAdjustmentError("complete source-yoke motion lost required fixed-housing separation")

    channel_y, channel_z, _, _, _ = _housing_dimensions()
    if channel_y - TONGUE_Y_MM < 2.0 * CHANNEL_CLEARANCE_Y_MM - 1e-12:
        raise RetentionFitAdjustmentError("guide Y clearance arithmetic drifted")
    if channel_z - TONGUE_Z_MM < 2.0 * CHANNEL_CLEARANCE_Z_MM - 1e-12:
        raise RetentionFitAdjustmentError("guide Z clearance arithmetic drifted")

    return AdjustmentSide(
        side=side,
        side_sign=side_sign,
        root_xyz_mm=root,
        housing=housing,
        stop_pin=stop_pin,
        stop_pin_clip=stop_clip,
        index_pin_engaged=index_engaged,
        index_pin_retracted=index_retracted,
        index_pin_retraction_envelope=index_envelope,
        nominal_successor_yoke=nominal,
        complete_translation_envelope=motion_envelope,
        states=tuple(states),
    )


def build_retention_fit_adjustment(
    authority: Authority | None = None,
    model: MasckOneModel | None = None,
    occipital: OccipitalStabilizer | None = None,
) -> RetentionFitAdjustment:
    _assert_occipital_source_blob()
    authority = authority or load_authority()
    model = model or build_model(authority)
    occipital = occipital or build_occipital_stabilizer(authority, model)

    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise RetentionFitAdjustmentError("retention-fit adjustment is stale for current authority revision")
    if int(authority.number("actuation", "count")) != 4 or len(model.actuator_envelopes) != 4:
        raise RetentionFitAdjustmentError("four independently controllable actuation zones must be preserved")
    if not math.isclose(HARD_STOP_TRAVEL_MM, max(abs(value) for value in INDEX_OFFSETS_MM), rel_tol=0.0, abs_tol=1e-12):
        raise RetentionFitAdjustmentError("extreme indexed positions must coincide with digital hard-stop travel")

    left_root = _datum_center(occipital, "OCCIPITAL_ROOT_LEFT")
    right_root = _datum_center(occipital, "OCCIPITAL_ROOT_RIGHT")
    left_contact = _datum_center(occipital, "OCCIPITAL_CONTACT_BACKER_LEFT")
    right_contact = _datum_center(occipital, "OCCIPITAL_CONTACT_BACKER_RIGHT")

    left = _build_side(occipital.left, left_contact, left_root, -1)
    right = _build_side(occipital.right, right_contact, right_root, +1)

    # The fixed housing is kept inside the released 172 mm lateral design envelope.
    outer_width, _ = authority.pair("geometry", "outer_xy_envelope_mm")
    half_width = outer_width / 2.0
    if _bbox(left.housing)[0] < -half_width - 1e-9 or _bbox(right.housing)[1] > half_width + 1e-9:
        raise RetentionFitAdjustmentError("fixed adjustment housing exceeds released lateral design envelope")

    checks: list[CollisionCheck] = []

    def add(check_id: str, obstacle_id: str, moving: cq.Workplane, obstacle: cq.Workplane) -> None:
        checks.append(CollisionCheck(check_id, obstacle_id, _intersection_mm3(moving, obstacle)))

    moving_items = (
        ("LEFT_COMPLETE_TRANSLATION_ENVELOPE", left.complete_translation_envelope),
        ("RIGHT_COMPLETE_TRANSLATION_ENVELOPE", right.complete_translation_envelope),
        ("LEFT_INDEX_RETRACTION_ENVELOPE", left.index_pin_retraction_envelope),
        ("RIGHT_INDEX_RETRACTION_ENVELOPE", right.index_pin_retraction_envelope),
        ("LEFT_FIXED_HOUSING", left.housing),
        ("RIGHT_FIXED_HOUSING", right.housing),
        ("LEFT_STOP_PIN", left.stop_pin),
        ("RIGHT_STOP_PIN", right.stop_pin),
        ("LEFT_STOP_CLIP", left.stop_pin_clip),
        ("RIGHT_STOP_CLIP", right.stop_pin_clip),
    )

    for moving_id, moving in moving_items:
        add(f"CLEAR_{moving_id}_CENTRAL_REAR_PACKAGE", "CENTRAL_REAR_PACKAGE_KEEP_OUT", moving, occipital.central_rear_package_keepout)
        add(f"CLEAR_{moving_id}_CROWN_CORRIDOR", "CROWN_SUPPORT_CORRIDOR", moving, occipital.crown_support_corridor)
        for component in (
            model.shell,
            *model.actuator_envelopes,
            model.water_reservoir_envelope,
            model.waste_cartridge_envelope,
            model.battery_reference_envelope,
        ):
            add(f"CLEAR_{moving_id}_{component.name.upper()}", component.name.upper(), moving, component.solid)
        for index in range(len(model.protected_volumes.all)):
            zone_id, protected = _protected_solid(model, index)
            add(f"CLEAR_{moving_id}_{zone_id}", zone_id, moving, protected)

    add(
        "CLEAR_LEFT_RIGHT_COMPLETE_TRANSLATION_ENVELOPES",
        "RIGHT_COMPLETE_TRANSLATION_ENVELOPE",
        left.complete_translation_envelope,
        right.complete_translation_envelope,
    )

    waste_release = build_current_cell4_waste_backbone_release()
    for route in waste_release.realization.routes:
        route_bound = _route_service_aabb(route)
        for moving_id, moving in moving_items:
            add(
                f"CLEAR_{moving_id}_{route.route_id}_SERVICE_AABB",
                f"{route.route_id}_SERVICE_AABB",
                moving,
                route_bound,
            )

    result = RetentionFitAdjustment(
        source_occipital_package_sha256=occipital.package_sha256,
        source_waste_release_sha256=waste_release.manifest_sha256,
        left=left,
        right=right,
        collision_checks=tuple(checks),
    )

    # Preserve the Prompt 08 central package margin at the exact hard-stop extremes.
    central = _bbox(occipital.central_rear_package_keepout)
    left_env = _bbox(left.complete_translation_envelope)
    right_env = _bbox(right.complete_translation_envelope)
    left_gap = central[0] - left_env[1]
    right_gap = right_env[0] - central[1]
    if left_gap < 8.0 - 1e-9 or right_gap < 8.0 - 1e-9:
        raise RetentionFitAdjustmentError("hard-stop interval violates 8 mm central package margin")
    return result


def export_retention_fit_adjustment(
    output_dir: str | Path,
    adjustment: RetentionFitAdjustment,
) -> tuple[Path, ...]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    solids: list[tuple[str, cq.Workplane]] = []
    for side_name, side in (("left", adjustment.left), ("right", adjustment.right)):
        solids.extend(
            [
                (f"retention_fit_{side_name}_housing.step", side.housing),
                (f"retention_fit_{side_name}_stop_pin.step", side.stop_pin),
                (f"retention_fit_{side_name}_stop_pin_clip.step", side.stop_pin_clip),
                (f"retention_fit_{side_name}_index_pin_engaged.step", side.index_pin_engaged),
                (f"retention_fit_{side_name}_index_pin_retracted.step", side.index_pin_retracted),
                (f"retention_fit_{side_name}_complete_translation_envelope.step", side.complete_translation_envelope),
                (f"retention_fit_{side_name}_index_retraction_envelope.step", side.index_pin_retraction_envelope),
            ]
        )
        for state in side.states:
            offset_name = "tight" if state.offset_mm < 0 else "loose" if state.offset_mm > 0 else "nominal"
            solids.append((f"retention_fit_{side_name}_yoke_{offset_name}.step", state.successor_yoke))

    for name, solid in solids:
        _single(solid, name)
        path = root / name
        cq.exporters.export(solid, str(path))
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"failed to export {name}")
        outputs.append(path)

    manifest_path = root / "retention_fit_adjustment_manifest.json"
    manifest_path.write_text(
        json.dumps(adjustment.manifest(), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    outputs.append(manifest_path)
    return tuple(outputs)
