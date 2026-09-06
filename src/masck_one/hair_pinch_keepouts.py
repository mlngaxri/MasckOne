from __future__ import annotations

"""Cell 3 hair-path, pinch-hazard and access keepout geometry.

The solids in this module are deterministic reference geometry, not physical guards and
not evidence that hair entrapment or finger pinch risk has been eliminated. They make the
known moving-interface hazard regions explicit so future frame covers, retention hardware,
exterior closure and service tooling cannot silently occupy them.
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
    ROOT_CAPTURE_BORE_RADIUS_MM,
    SOURCE_AUTHORITY_BLOB_SHA,
    SOURCE_MAIN_SHA,
    WORLD_FRAME_ID,
)
from .realized_waste_backbone_release import build_current_cell4_waste_backbone_release
from .retention_fit_adjustment import (
    CHANNEL_CLEARANCE_Y_MM,
    CHANNEL_CLEARANCE_Z_MM,
    TONGUE_Y_MM,
    TONGUE_Z_MM,
    AdjustmentSide,
    RetentionFitAdjustment,
    build_retention_fit_adjustment,
)

SCHEMA = "MASCK_ONE_CELL3_HAIR_PINCH_KEEPOUTS_V1"
SOURCE_RETENTION_FIT_GIT_BLOB_SHA = "4d4583d3df7c86151fd7761fbc05e6f93328d338"
SOURCE_RIGHT_LATCH_HEAD_SHA = "0b5a619c6cea344038b0e8b8cc10a50e3d193390"
SOURCE_RIGHT_LATCH_GIT_BLOB_SHA = "11d90a75eb108c53f5a1621abdace7271bf5cac5"
DIGITAL_ONLY = "DIGITAL_HAZARD_AND_ACCESS_REFERENCE_GEOMETRY_NOT_PHYSICAL_SAFETY_VALIDATION"
KERNEL_ZERO_MM3 = 1e-8

# Provisional Cell 3 reservation margins. They are intentionally packaging dimensions,
# not hair-diameter, finger-size, pinch-force, skin-compression or injury thresholds.
HAIR_PATH_RADIUS_MM = 4.0
GUIDE_NIP_AXIAL_HALF_WIDTH_MM = 1.25
GUIDE_NIP_RADIAL_MARGIN_MM = 1.50
PIN_HAZARD_MARGIN_MM = 1.50
ROOT_CAPTURE_HAZARD_RADIAL_MARGIN_MM = 2.00
ROOT_CAPTURE_HAZARD_LENGTH_MM = 18.0

# Candidate-only right quick-release overlay. These bounds are copied from the exact
# PR #71 source head identified above and are never promoted to released-main authority.
RIGHT_LATCH_OPERATIONAL_BOUNDS_MM = (73.5, 100.0, -5.0, 5.0, -22.5, -15.5)
RIGHT_LATCH_PINCH_MARGIN_MM = 1.50
RIGHT_LATCH_DETENT_BOUNDS_MM = (81.0, 90.0, -3.5, 3.5, -18.8, -13.5)
RIGHT_LATCH_ACCESS_BOUNDS_MM = (91.0, 104.0, -7.0, 7.0, -25.0, -13.0)
RIGHT_LATCH_GRIP_CLOSED_BOUNDS_MM = (91.5, 92.7, -5.0, 5.0, -22.5, -15.5)
RIGHT_LATCH_GRIP_RELEASED_BOUNDS_MM = (98.8, 100.0, -5.0, 5.0, -22.5, -15.5)
RIGHT_LATCH_GRIP_COMPLETE_TRANSLATION_BOUNDS_MM = (91.5, 100.0, -5.0, 5.0, -22.5, -15.5)
RIGHT_LATCH_CANDIDATE_CONTRACT_SHA256 = "3a32222a49e6b58916901a6cc4ef42d2e448a478b728355b5072b1a094bbba0f"


class HairPinchKeepoutError(ValueError):
    pass


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise HairPinchKeepoutError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise HairPinchKeepoutError(f"{label} must be finite")
    return 0.0 if result == 0.0 else result


def _positive(value: object, label: str) -> float:
    result = _finite(value, label)
    if result <= 0.0:
        raise HairPinchKeepoutError(f"{label} must be positive")
    return result


def _single(solid: cq.Workplane, label: str) -> cq.Workplane:
    shape = solid.val()
    if not shape.isValid() or float(shape.Volume()) <= 0.0 or len(shape.Solids()) != 1:
        raise HairPinchKeepoutError(f"{label} must be one valid positive-volume solid")
    return solid


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> cq.Workplane:
    dims = tuple(_positive(value, "box dimension") for value in size)
    ctr = tuple(_finite(value, "box center") for value in center)
    return cq.Workplane("XY").box(*dims, centered=(True, True, True)).translate(ctr)


def _box_from_bounds(bounds: tuple[float, float, float, float, float, float]) -> cq.Workplane:
    xmin, xmax, ymin, ymax, zmin, zmax = tuple(_finite(value, "box bound") for value in bounds)
    if not (xmax > xmin and ymax > ymin and zmax > zmin):
        raise HairPinchKeepoutError("box bounds must have positive extent")
    return _box(
        (xmax - xmin, ymax - ymin, zmax - zmin),
        ((xmin + xmax) / 2.0, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0),
    )


def _cylinder(
    radius_mm: float,
    length_mm: float,
    center: tuple[float, float, float],
    axis_xyz: tuple[float, float, float],
) -> cq.Workplane:
    radius = _positive(radius_mm, "cylinder radius")
    length = _positive(length_mm, "cylinder length")
    ax, ay, az = tuple(_finite(value, "cylinder axis") for value in axis_xyz)
    norm = math.sqrt(ax * ax + ay * ay + az * az)
    if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise HairPinchKeepoutError("cylinder axis must be unit length")
    cx, cy, cz = tuple(_finite(value, "cylinder center") for value in center)
    start = (cx - ax * length / 2.0, cy - ay * length / 2.0, cz - az * length / 2.0)
    shape = cq.Solid.makeCylinder(radius, length, cq.Vector(*start), cq.Vector(ax, ay, az))
    return cq.Workplane("XY").newObject([shape])


def _capsule_axis(
    start_xyz: tuple[float, float, float],
    end_xyz: tuple[float, float, float],
    radius_mm: float,
) -> cq.Workplane:
    start = cq.Vector(*tuple(_finite(value, "capsule start") for value in start_xyz))
    end = cq.Vector(*tuple(_finite(value, "capsule end") for value in end_xyz))
    delta = end - start
    length = float(delta.Length)
    if length <= 0.0:
        raise HairPinchKeepoutError("capsule endpoints must differ")
    direction = delta.normalized()
    radius = _positive(radius_mm, "capsule radius")
    cylinder = cq.Solid.makeCylinder(radius, length, start, direction)
    full_sphere_axis = cq.Vector(0.0, 0.0, 1.0)
    start_sphere = cq.Solid.makeSphere(
        radius, start, full_sphere_axis, -90.0, 90.0, 360.0
    )
    end_sphere = cq.Solid.makeSphere(
        radius, end, full_sphere_axis, -90.0, 90.0, 360.0
    )
    fused = cylinder.fuse(start_sphere).fuse(end_sphere)
    return _single(cq.Workplane("XY").newObject([fused]), "hair approach capsule")


def _bbox(solid: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = solid.val().BoundingBox()
    return tuple(
        round(float(value), 6)
        for value in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    )


def _intersection_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise HairPinchKeepoutError("intersection volume must be finite and nonnegative")
    return 0.0 if value < KERNEL_ZERO_MM3 else value


def _expanded_bounds(
    bounds: tuple[float, float, float, float, float, float],
    margin_mm: float,
) -> tuple[float, float, float, float, float, float]:
    margin = _positive(margin_mm, "AABB expansion margin")
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    return (
        xmin - margin,
        xmax + margin,
        ymin - margin,
        ymax + margin,
        zmin - margin,
        zmax + margin,
    )


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    return sha1(header + raw).hexdigest()


def _assert_retention_fit_source_blob() -> None:
    path = Path(__file__).with_name("retention_fit_adjustment.py")
    observed = _git_blob_sha(path)
    if observed != SOURCE_RETENTION_FIT_GIT_BLOB_SHA:
        raise HairPinchKeepoutError(
            "retention-fit source blob changed; hair/pinch keepouts require explicit rebind"
        )


def _right_latch_contract_payload() -> dict[str, object]:
    return {
        "source_head_sha": SOURCE_RIGHT_LATCH_HEAD_SHA,
        "source_latch_git_blob_sha": SOURCE_RIGHT_LATCH_GIT_BLOB_SHA,
        "operational_bounds_mm": list(RIGHT_LATCH_OPERATIONAL_BOUNDS_MM),
        "detent_bounds_mm": list(RIGHT_LATCH_DETENT_BOUNDS_MM),
        "emergency_pull_access_bounds_mm": list(RIGHT_LATCH_ACCESS_BOUNDS_MM),
        "grip_closed_bounds_mm": list(RIGHT_LATCH_GRIP_CLOSED_BOUNDS_MM),
        "grip_released_bounds_mm": list(RIGHT_LATCH_GRIP_RELEASED_BOUNDS_MM),
        "grip_complete_translation_bounds_mm": list(RIGHT_LATCH_GRIP_COMPLETE_TRANSLATION_BOUNDS_MM),
    }


def _assert_right_latch_candidate_contract() -> None:
    raw = json.dumps(
        _right_latch_contract_payload(),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    observed = sha256(raw).hexdigest()
    if observed != RIGHT_LATCH_CANDIDATE_CONTRACT_SHA256:
        raise HairPinchKeepoutError(
            "right-latch candidate source/bounds changed; explicit hazard-access revalidation required"
        )


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
    return _single(
        _box_from_bounds((minimum[0], maximum[0], minimum[1], maximum[1], minimum[2], maximum[2])),
        f"{route.route_id} service AABB",
    )


@dataclass(frozen=True, slots=True)
class HazardRegion:
    region_id: str
    side: str
    hazard_types: tuple[str, ...]
    source_interface: str
    solid: cq.Workplane
    occupancy_semantics: str
    physical_guard_realized: bool = False

    def __post_init__(self) -> None:
        if not self.region_id or not self.source_interface or not self.occupancy_semantics:
            raise HairPinchKeepoutError("hazard-region identifiers and semantics must be nonblank")
        if not self.hazard_types or len(set(self.hazard_types)) != len(self.hazard_types):
            raise HairPinchKeepoutError("hazard types must be nonempty and unique")
        _single(self.solid, self.region_id)
        if self.physical_guard_realized:
            raise HairPinchKeepoutError("Prompt 10 reference regions must not masquerade as guards")

    def manifest(self) -> dict[str, object]:
        return {
            "region_id": self.region_id,
            "side": self.side,
            "hazard_types": list(self.hazard_types),
            "source_interface": self.source_interface,
            "bounds_mm": list(_bbox(self.solid)),
            "volume_mm3": round(float(self.solid.val().Volume()), 6),
            "occupancy_semantics": self.occupancy_semantics,
            "physical_guard_realized": self.physical_guard_realized,
        }


@dataclass(frozen=True, slots=True)
class AccessRegion:
    region_id: str
    side: str
    purpose: str
    solid: cq.Workplane
    source_status: str

    def __post_init__(self) -> None:
        _single(self.solid, self.region_id)

    def manifest(self) -> dict[str, object]:
        return {
            "region_id": self.region_id,
            "side": self.side,
            "purpose": self.purpose,
            "bounds_mm": list(_bbox(self.solid)),
            "volume_mm3": round(float(self.solid.val().Volume()), 6),
            "source_status": self.source_status,
        }


@dataclass(frozen=True, slots=True)
class ClearanceCheck:
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
class HairPinchKeepoutPackage:
    source_retention_fit_package_sha256: str
    source_waste_release_sha256: str
    hazard_regions: tuple[HazardRegion, ...]
    access_regions: tuple[AccessRegion, ...]
    clearance_checks: tuple[ClearanceCheck, ...]

    def __post_init__(self) -> None:
        if any(not check.passes for check in self.clearance_checks):
            failed = tuple(check.check_id for check in self.clearance_checks if not check.passes)
            raise HairPinchKeepoutError(f"required hazard/access keepout clearance failed: {failed}")
        ids = [region.region_id for region in self.hazard_regions] + [region.region_id for region in self.access_regions]
        if len(ids) != len(set(ids)):
            raise HairPinchKeepoutError("hazard/access region ids must be unique")

    @property
    def package_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": SOURCE_MAIN_SHA,
            "source_authority_blob_sha": SOURCE_AUTHORITY_BLOB_SHA,
            "source_authority_revision": AUTHORITY_REVISION,
            "source_retention_fit_git_blob_sha": SOURCE_RETENTION_FIT_GIT_BLOB_SHA,
            "source_retention_fit_package_sha256": self.source_retention_fit_package_sha256,
            "source_waste_release_sha256": self.source_waste_release_sha256,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "hazard_regions": [region.manifest() for region in self.hazard_regions],
            "access_regions": [region.manifest() for region in self.access_regions],
            "right_latch_candidate_overlay": {
                "source_pr": 71,
                "source_head_sha": SOURCE_RIGHT_LATCH_HEAD_SHA,
                "source_latch_git_blob_sha": SOURCE_RIGHT_LATCH_GIT_BLOB_SHA,
                "candidate_contract_sha256": RIGHT_LATCH_CANDIDATE_CONTRACT_SHA256,
                "authority_status": "NON_AUTHORITATIVE_UNMERGED_CANDIDATE_OVERLAY",
                "runtime_source_imported": False,
                "promotion_requires_live_head_revalidation": True,
                "operational_bounds_mm": list(RIGHT_LATCH_OPERATIONAL_BOUNDS_MM),
                "grip_closed_bounds_mm": list(RIGHT_LATCH_GRIP_CLOSED_BOUNDS_MM),
                "grip_released_bounds_mm": list(RIGHT_LATCH_GRIP_RELEASED_BOUNDS_MM),
                "grip_complete_translation_bounds_mm": list(RIGHT_LATCH_GRIP_COMPLETE_TRANSLATION_BOUNDS_MM),
                "emergency_pull_access_contains_complete_grip_translation": True,
                "physical_release_performance_promoted": False,
            },
            "adjustment_hazard_semantics": {
                "guide_nip_regions_cover_both_channel_entrances": True,
                "continuous_yoke_translation_range_inherited_from_prompt09_mm": [-2.0, 2.0],
                "index_pin_hazard_is_service_only": True,
                "adjustment_while_worn_allowed": False,
                "permanent_stop_pin_remains_installed_during_adjustment": True,
            },
            "retention_root_semantics": {
                "future_root_capture_hazard_reserved": True,
                "frame_side_pin_or_clevis_realized": False,
                "pivot_motion_claimed": False,
            },
            "design_use": {
                "future_hard_material_may_fill_hazard_region_without_review": False,
                "future_guard_may_block_emergency_release_access": False,
                "reference_solids_are_product_material": False,
                "reference_solids_are_physical_guards": False,
            },
            "unresolved_digital_requirements": [
                "PROTECTIVE_GUARD_SHROUD_OR_EDGE_TREATMENT_PRODUCT_GEOMETRY",
                "FRAME_SIDE_RETENTION_ROOT_CAPTURE_COUNTERPART_GEOMETRY",
                "RIGHT_LATCH_CANDIDATE_OVERLAY_RELEASE_RECONCILIATION",
            ],
            "clearance_checks": [check.manifest() for check in self.clearance_checks],
            "four_zone_actuation_preserved": True,
            "hair_model": {
                "strand_diameter_mm": None,
                "hair_density": None,
                "hair_friction": None,
                "hair_tension_N": None,
                "representative_head_hair_geometry": None,
            },
            "pinch_model": {
                "finger_dimension_mm": None,
                "pinch_force_N": None,
                "pinch_pressure_kPa": None,
                "injury_threshold": None,
            },
            "physical_validation_eligible": False,
            "unresolved_physical_gates": [
                "HAIR_ENTRAPMENT_AND_PULLING_WITH_REPRESENTATIVE_HAIR_TYPES",
                "FINGER_AND_SKIN_PINCH_ACCESS_DURING_REAL_USE_AND_SERVICE",
                "FRAME_SIDE_RETENTION_ROOT_CAPTURE_LOAD_CAPACITY",
                "RIGHT_LATCH_HAIR_PINCH_PHYSICAL_VALIDATION",
                "WET_ONE_HAND_RELEASE_FORCE_5_TO_12_N_AND_TIME_LE_2_S",
                "WHOLE_HEAD_REMOVAL_AFTER_RELEASE",
            ],
            "evidence_status": DIGITAL_ONLY,
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def _side_regions(side: AdjustmentSide) -> tuple[tuple[HazardRegion, ...], tuple[AccessRegion, ...]]:
    hb = _bbox(side.housing)
    channel_y = TONGUE_Y_MM + 2.0 * CHANNEL_CLEARANCE_Y_MM
    channel_z = TONGUE_Z_MM + 2.0 * CHANNEL_CLEARANCE_Z_MM
    nip_y = channel_y + 2.0 * GUIDE_NIP_RADIAL_MARGIN_MM
    nip_z = channel_z + 2.0 * GUIDE_NIP_RADIAL_MARGIN_MM

    if side.side_sign > 0:
        medial_face_x = hb[0]
        outboard_face_x = hb[1]
    else:
        medial_face_x = hb[1]
        outboard_face_x = hb[0]

    medial_nip = _single(
        _box(
            (2.0 * GUIDE_NIP_AXIAL_HALF_WIDTH_MM, nip_y, nip_z),
            (medial_face_x, side.root_xyz_mm[1], side.root_xyz_mm[2]),
        ),
        f"{side.side} medial guide nip keepout",
    )
    outboard_nip = _single(
        _box(
            (2.0 * GUIDE_NIP_AXIAL_HALF_WIDTH_MM, nip_y, nip_z),
            (outboard_face_x, side.root_xyz_mm[1], side.root_xyz_mm[2]),
        ),
        f"{side.side} outboard guide nip keepout",
    )

    index_pin_keepout = _single(
        _box_from_bounds(_expanded_bounds(_bbox(side.index_pin_retraction_envelope), PIN_HAZARD_MARGIN_MM)),
        f"{side.side} index pin insertion keepout",
    )

    stop_bounds = _bbox(side.stop_pin)
    clip_bounds = _bbox(side.stop_pin_clip)
    combined = (
        min(stop_bounds[0], clip_bounds[0]),
        max(stop_bounds[1], clip_bounds[1]),
        min(stop_bounds[2], clip_bounds[2]),
        max(stop_bounds[3], clip_bounds[3]),
        min(stop_bounds[4], clip_bounds[4]),
        max(stop_bounds[5], clip_bounds[5]),
    )
    stop_keepout = _single(
        _box_from_bounds(_expanded_bounds(combined, PIN_HAZARD_MARGIN_MM)),
        f"{side.side} stop pin clip hair keepout",
    )

    root_capture = _single(
        _cylinder(
            ROOT_CAPTURE_BORE_RADIUS_MM + ROOT_CAPTURE_HAZARD_RADIAL_MARGIN_MM,
            ROOT_CAPTURE_HAZARD_LENGTH_MM,
            side.root_xyz_mm,
            (0.0, 1.0, 0.0),
        ),
        f"{side.side} root capture future pinch keepout",
    )

    nominal = side.state_for_offset(0.0)
    hair_path = _capsule_axis(
        nominal.contact_backer_center_xyz_mm,
        side.root_xyz_mm,
        HAIR_PATH_RADIUS_MM,
    )

    prefix = "RIGHT" if side.side_sign > 0 else "LEFT"
    hazards = (
        HazardRegion(
            f"{prefix}_ADJUSTMENT_MEDIAL_GUIDE_NIP",
            side.side,
            ("PINCH_NIP", "HAIR_ENTRAPMENT"),
            "PROMPT09_MOVING_TONGUE_TO_FIXED_GUIDE_MEDIAL_FACE",
            medial_nip,
            "NO_NEW_HARD_MATERIAL_OR_OPEN_HAIR_PATH_WITHOUT_EXPLICIT_GUARD_REVIEW",
        ),
        HazardRegion(
            f"{prefix}_ADJUSTMENT_OUTBOARD_GUIDE_NIP",
            side.side,
            ("PINCH_NIP", "HAIR_ENTRAPMENT"),
            "PROMPT09_MOVING_TONGUE_TO_FIXED_GUIDE_OUTBOARD_FACE",
            outboard_nip,
            "NO_NEW_HARD_MATERIAL_OR_OPEN_HAIR_PATH_WITHOUT_EXPLICIT_GUARD_REVIEW",
        ),
        HazardRegion(
            f"{prefix}_INDEX_PIN_SERVICE_PATH",
            side.side,
            ("PINCH_INSERTION", "HAIR_ENTRAPMENT"),
            "PROMPT09_RETRACTABLE_INDEX_PIN_COMPLETE_SERVICE_TRAVEL",
            index_pin_keepout,
            "SERVICE_ONLY_HAZARD_ZONE_KEEP_CLEAR_WHILE_INDEX_PIN_TRAVELS",
        ),
        HazardRegion(
            f"{prefix}_STOP_PIN_CLIP_REGION",
            side.side,
            ("HAIR_SNAG", "EDGE_CONTACT"),
            "PROMPT09_PERMANENT_STOP_PIN_HEAD_GROOVE_AND_CLIP",
            stop_keepout,
            "RESERVE_FOR_FUTURE_COVER_OR_EDGE_TREATMENT_WITHOUT_REMOVING_STOP_CAPTIVITY",
        ),
        HazardRegion(
            f"{prefix}_ROOT_CAPTURE_FUTURE_PINCH_REGION",
            side.side,
            ("PINCH_ROTATION_OR_CAPTURE", "HAIR_ENTRAPMENT"),
            "PROMPT08_ROOT_CAPTURE_BORE_FRAME_COUNTERPART_UNRESOLVED",
            root_capture,
            "FUTURE_FRAME_PIN_CLEVIS_OR_CLOSURE_MUST_REVIEW_THIS_VOLUME_BEFORE_REALIZATION",
        ),
        HazardRegion(
            f"{prefix}_SCALP_HAIR_APPROACH_CORRIDOR",
            side.side,
            ("HAIR_PRESENCE_PATH",),
            "OCCIPITAL_CONTACT_BACKER_TO_RETENTION_ROOT",
            hair_path,
            "REFERENCE_CORRIDOR_FOR_HAIR_PRESENCE_NOT_A_SOLID_HAIR_MODEL",
        ),
    )

    access = (
        AccessRegion(
            f"{prefix}_INDEX_PIN_SERVICE_ACCESS",
            side.side,
            "MASK_REMOVED_UNPOWERED_INDEX_PIN_RETRACTION_AND_RESEAT_ACCESS",
            index_pin_keepout,
            "PROMPT09_REALIZED_SERVICE_MOTION_REFERENCE",
        ),
    )

    # Hazard regions must actually cover the interfaces they describe. This is not a
    # safety pass; it prevents disconnected decorative keepouts.
    for region in (medial_nip, outboard_nip):
        if _intersection_mm3(region, side.complete_translation_envelope) <= 0.0:
            raise HairPinchKeepoutError("guide nip keepout lost the moving yoke translation envelope")
    if _intersection_mm3(index_pin_keepout, side.index_pin_retraction_envelope) <= 0.0:
        raise HairPinchKeepoutError("index-pin hazard keepout lost the service motion")
    if _intersection_mm3(stop_keepout, side.stop_pin) <= 0.0:
        raise HairPinchKeepoutError("stop-pin hair keepout lost the stop pin")
    if _intersection_mm3(root_capture, side.nominal_successor_yoke) <= 0.0:
        raise HairPinchKeepoutError("future root-capture hazard keepout lost the retention root")
    if _intersection_mm3(hair_path, side.nominal_successor_yoke) <= 0.0:
        raise HairPinchKeepoutError("hair approach corridor lost the occipital carrier path")

    return hazards, access


def _right_latch_candidate_regions() -> tuple[tuple[HazardRegion, ...], tuple[AccessRegion, ...]]:
    operational = _box_from_bounds(_expanded_bounds(RIGHT_LATCH_OPERATIONAL_BOUNDS_MM, RIGHT_LATCH_PINCH_MARGIN_MM))
    detent = _box_from_bounds(_expanded_bounds(RIGHT_LATCH_DETENT_BOUNDS_MM, RIGHT_LATCH_PINCH_MARGIN_MM))
    combined = _single(operational.union(detent), "right latch candidate hair pinch keepout")
    access = _single(_box_from_bounds(RIGHT_LATCH_ACCESS_BOUNDS_MM), "right latch release access corridor")
    grip_sweep = _single(
        _box_from_bounds(RIGHT_LATCH_GRIP_COMPLETE_TRANSLATION_BOUNDS_MM),
        "right latch copied complete grip translation bound",
    )
    outside_access_mm3 = float(grip_sweep.val().cut(access.val()).Volume())
    if not math.isfinite(outside_access_mm3) or outside_access_mm3 > KERNEL_ZERO_MM3:
        raise HairPinchKeepoutError(
            "emergency pull access no longer contains the copied complete right-latch grip translation"
        )
    return (
        (
            HazardRegion(
                "RIGHT_LATCH_CANDIDATE_HAIR_PINCH_REGION",
                "WEARER_RIGHT",
                ("PINCH_TRANSLATION", "HAIR_ENTRAPMENT", "DETENT_NIP"),
                "PR71_EXACT_HEAD_OPERATIONAL_SLIDER_SWEEP_AND_DETENT_OVERLAY",
                combined,
                "CANDIDATE_OVERLAY_ONLY_DO_NOT_FILL_WITH_GUARD_MATERIAL_WITHOUT_EXACT_LATCH_REVIEW",
            ),
        ),
        (
            AccessRegion(
                "RIGHT_LATCH_EMERGENCY_PULL_ACCESS",
                "WEARER_RIGHT",
                "PRESERVE_PLUS_X_ONE_HAND_EMERGENCY_RELEASE_GRIP_AND_PULL_CORRIDOR",
                access,
                "PR71_NONAUTHORITATIVE_CANDIDATE_OVERLAY_REVALIDATE_BEFORE_PROMOTION",
            ),
        ),
    )


def build_hair_pinch_keepouts(
    authority: Authority | None = None,
    model: MasckOneModel | None = None,
    adjustment: RetentionFitAdjustment | None = None,
) -> HairPinchKeepoutPackage:
    _assert_retention_fit_source_blob()
    _assert_right_latch_candidate_contract()
    authority = authority or load_authority()
    model = model or build_model(authority)
    adjustment = adjustment or build_retention_fit_adjustment(authority, model)

    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise HairPinchKeepoutError("hair/pinch keepouts are stale for current authority revision")
    if int(authority.number("actuation", "count")) != 4 or len(model.actuator_envelopes) != 4:
        raise HairPinchKeepoutError("four independently controllable actuation zones must be preserved")

    left_hazards, left_access = _side_regions(adjustment.left)
    right_hazards, right_access = _side_regions(adjustment.right)
    latch_hazards, latch_access = _right_latch_candidate_regions()
    hazards = left_hazards + right_hazards + latch_hazards
    access = left_access + right_access + latch_access

    checks: list[ClearanceCheck] = []

    def add(check_id: str, obstacle_id: str, moving: cq.Workplane, obstacle: cq.Workplane) -> None:
        checks.append(ClearanceCheck(check_id, obstacle_id, _intersection_mm3(moving, obstacle)))

    # Reference regions are allowed to intersect the mechanism interface they describe,
    # but must remain clear of unrelated released-main packages and protected regions.
    for region in hazards + access:
        for component in (
            model.shell,
            *model.actuator_envelopes,
            model.water_reservoir_envelope,
            model.waste_cartridge_envelope,
            model.battery_reference_envelope,
        ):
            add(
                f"CLEAR_{region.region_id}_{component.name.upper()}",
                component.name.upper(),
                region.solid,
                component.solid,
            )
        for index in range(len(model.protected_volumes.all)):
            zone_id, protected = _protected_solid(model, index)
            add(f"CLEAR_{region.region_id}_{zone_id}", zone_id, region.solid, protected)

    # Central rear package and crown reservations come from the controlled Prompt 08
    # source path so they remain independent of the hazard-reference solids.
    from .occipital_stabilizer import build_occipital_stabilizer

    source_occipital = build_occipital_stabilizer(authority, model)
    for region in hazards + access:
        add(
            f"CLEAR_{region.region_id}_CENTRAL_REAR_PACKAGE",
            "CENTRAL_REAR_PACKAGE_KEEP_OUT",
            region.solid,
            source_occipital.central_rear_package_keepout,
        )
        add(
            f"CLEAR_{region.region_id}_CROWN_CORRIDOR",
            "CROWN_SUPPORT_CORRIDOR",
            region.solid,
            source_occipital.crown_support_corridor,
        )

    waste_release = build_current_cell4_waste_backbone_release()
    for route in waste_release.realization.routes:
        route_bound = _route_service_aabb(route)
        for region in hazards + access:
            add(
                f"CLEAR_{region.region_id}_{route.route_id}_SERVICE_AABB",
                f"{route.route_id}_SERVICE_AABB",
                region.solid,
                route_bound,
            )

    # The candidate latch reserve must stay separated from the Prompt 09 adjustment
    # package so future guards do not merge two independent moving interfaces.
    latch_hazard = next(region for region in latch_hazards if region.region_id == "RIGHT_LATCH_CANDIDATE_HAIR_PINCH_REGION")
    latch_pull = next(region for region in latch_access if region.region_id == "RIGHT_LATCH_EMERGENCY_PULL_ACCESS")
    for item_id, item in (
        ("RIGHT_ADJUSTMENT_COMPLETE_TRANSLATION", adjustment.right.complete_translation_envelope),
        ("RIGHT_ADJUSTMENT_HOUSING", adjustment.right.housing),
        ("RIGHT_ADJUSTMENT_INDEX_RETRACTION", adjustment.right.index_pin_retraction_envelope),
    ):
        add(f"CLEAR_RIGHT_LATCH_HAZARD_{item_id}", item_id, latch_hazard.solid, item)
        add(f"CLEAR_RIGHT_LATCH_PULL_ACCESS_{item_id}", item_id, latch_pull.solid, item)

    return HairPinchKeepoutPackage(
        source_retention_fit_package_sha256=adjustment.package_sha256,
        source_waste_release_sha256=waste_release.manifest_sha256,
        hazard_regions=hazards,
        access_regions=access,
        clearance_checks=tuple(checks),
    )


def export_hair_pinch_keepouts(
    output_dir: str | Path,
    package: HairPinchKeepoutPackage,
) -> tuple[Path, ...]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    for region in package.hazard_regions:
        filename = f"hair_pinch_{region.region_id.lower()}.step"
        path = root / filename
        cq.exporters.export(region.solid, str(path))
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"failed to export {filename}")
        outputs.append(path)

    for region in package.access_regions:
        filename = f"hair_pinch_{region.region_id.lower()}.step"
        path = root / filename
        cq.exporters.export(region.solid, str(path))
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"failed to export {filename}")
        outputs.append(path)

    manifest_path = root / "hair_pinch_keepouts_manifest.json"
    manifest_path.write_text(
        json.dumps(package.manifest(), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    outputs.append(manifest_path)
    return tuple(outputs)
