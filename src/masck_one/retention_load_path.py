from __future__ import annotations

"""Cell 3 retention load-path attachment geometry.

This module realizes compact bilateral carrier geometry that positively captures the
fixed Prompt 09 adjustment housings and provides real crown/facial-reaction handoff
features. It does not pretend the still-unrealized crown member or front perimeter
frame counterpart exists. Load-carrying attachment, contact and clearance semantics
are therefore kept separate in the deterministic graph.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path

import cadquery as cq

from .authority import Authority, load_authority
from .hair_pinch_keepouts import HairPinchKeepoutPackage, build_hair_pinch_keepouts
from .model import MasckOneModel, build_model
from .occipital_stabilizer import (
    AUTHORITY_REVISION,
    SOURCE_AUTHORITY_BLOB_SHA,
    WORLD_FRAME_ID,
)
from .realized_waste_backbone_release import build_current_cell4_waste_backbone_release
from .retention_fit_adjustment import (
    AdjustmentSide,
    RetentionFitAdjustment,
    build_retention_fit_adjustment,
)
from .structural_frame import RESERVATION_RETENTION

SCHEMA = "MASCK_ONE_CELL3_RETENTION_LOAD_PATH_V1"
SOURCE_CURRENT_MAIN_SHA = "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30"
SOURCE_PROMPT10_HEAD_SHA = "c900c42ac5f45ad0516b58e408454eb3295d172d"
SOURCE_RETENTION_FIT_GIT_BLOB_SHA = "4d4583d3df7c86151fd7761fbc05e6f93328d338"
SOURCE_HAIR_PINCH_GIT_BLOB_SHA = "04ba87a6f8c6dbd103dae0f19869446b064e2057"
SOURCE_STRUCTURAL_FRAME_GIT_BLOB_SHA = "bda5ba87d232c0e6a22e200975a80414a10c9a83"
DIGITAL_ONLY = "DIGITAL_LOAD_PATH_ATTACHMENT_GEOMETRY_NOT_STRUCTURAL_VALIDATION"
KERNEL_ZERO_MM3 = 1e-8

# Provisional Cell 3 attachment CAD seeds. These dimensions are not supplier,
# anthropometric, strength, fatigue or production-tolerance evidence.
HOUSING_BOSS_XYZ_MM = (6.0, 5.6, 3.0)
HOUSING_BOSS_POSTERIOR_EXTENSION_MM = 3.0
CAPTURE_PIN_X_OFFSETS_MM = (-1.6, 1.6)
CAPTURE_PIN_RADIUS_MM = 0.60
CAPTURE_BORE_RADIUS_MM = 0.75
CAPTURE_PIN_RADIAL_CLEARANCE_MM = CAPTURE_BORE_RADIUS_MM - CAPTURE_PIN_RADIUS_MM
CAPTURE_PIN_HEAD_RADIUS_MM = 1.30
CAPTURE_PIN_HEAD_LENGTH_MM = 0.80
CAPTURE_PIN_GROOVE_RADIUS_MM = 0.46
CAPTURE_PIN_GROOVE_LENGTH_MM = 0.60
CAPTURE_PIN_TIP_LENGTH_MM = 0.70
CAPTURE_CLIP_OUTER_RADIUS_MM = 1.18
CAPTURE_CLIP_INNER_RADIUS_MM = 0.52
CAPTURE_CLIP_THICKNESS_MM = 0.50
CAPTURE_CLIP_GAP_MM = 0.90
CAPTURE_PIN_SERVICE_WITHDRAWAL_MM = 14.0

CARRIER_BACKPLATE_XYZ_MM = (10.0, 12.0, 2.5)
CARRIER_EAR_XYZ_MM = (7.0, 2.0, 4.5)
CARRIER_LINK_RADIUS_MM = 2.0
CARRIER_BOSS_POSTERIOR_GAP_MM = 0.50
CARRIER_HOUSING_FACE_GAP_MM = 0.15
CLEVIS_SIDE_GAP_MM = 0.20

CROWN_LUG_CENTER_ABS_X_MM = 60.0
CROWN_LUG_CENTER_Y_MM = 60.0
CROWN_LUG_CENTER_Z_MM = -47.0
CROWN_LUG_XYZ_MM = (8.0, 8.0, 6.0)
CROWN_LUG_BORE_RADIUS_MM = 1.20
CROWN_CLEARANCE_RADIUS_MM = 2.50
CROWN_CLEARANCE_LENGTH_MM = 14.0

FACIAL_HANDOFF_CENTER_ABS_X_MM = 74.0
FACIAL_HANDOFF_CENTER_Y_MM = 28.0
FACIAL_HANDOFF_CENTER_Z_MM = -22.0
FACIAL_HANDOFF_XYZ_MM = (7.0, 8.0, 6.0)
FACIAL_HANDOFF_BORE_RADIUS_MM = 1.20
FACIAL_CLEARANCE_RADIUS_MM = 2.50
FACIAL_CLEARANCE_LENGTH_MM = 14.0
FACIAL_LINK_ELBOW_ABS_X_MM = 78.0
FACIAL_LINK_ELBOW_Y_MM = 20.0

ATTACHMENT_INTEGRAL = "INTEGRAL_MATERIAL_CONTINUITY"
ATTACHMENT_PINNED = "PINNED_POSITIVE_CAPTURE"
ATTACHMENT_FEATURE_OPEN = "POSITIVE_ATTACHMENT_FEATURE_COUNTERPART_UNRESOLVED"
ATTACHMENT_CONTACT = "CONTACT_ONLY_NOT_POSITIVE_ATTACHMENT"
ATTACHMENT_CLEARANCE = "CLEARANCE_ONLY_DOES_NOT_CARRY_LOAD"


class RetentionLoadPathError(ValueError):
    pass


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise RetentionLoadPathError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise RetentionLoadPathError(f"{label} must be finite")
    return 0.0 if result == 0.0 else result


def _positive(value: object, label: str) -> float:
    result = _finite(value, label)
    if result <= 0.0:
        raise RetentionLoadPathError(f"{label} must be positive")
    return result


def _single(solid: cq.Workplane, label: str) -> cq.Workplane:
    shape = solid.val()
    if not shape.isValid() or float(shape.Volume()) <= 0.0 or len(shape.Solids()) != 1:
        raise RetentionLoadPathError(f"{label} must be one valid positive-volume solid")
    return solid


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> cq.Workplane:
    dims = tuple(_positive(v, "box dimension") for v in size)
    ctr = tuple(_finite(v, "box center") for v in center)
    return cq.Workplane("XY").box(*dims, centered=(True, True, True)).translate(ctr)


def _cylinder(
    radius_mm: float,
    length_mm: float,
    center: tuple[float, float, float],
    axis_xyz: tuple[float, float, float],
) -> cq.Workplane:
    radius = _positive(radius_mm, "cylinder radius")
    length = _positive(length_mm, "cylinder length")
    ax, ay, az = tuple(_finite(v, "cylinder axis") for v in axis_xyz)
    norm = math.sqrt(ax * ax + ay * ay + az * az)
    if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise RetentionLoadPathError("cylinder axis must be unit length")
    cx, cy, cz = center
    start = (
        cx - ax * length / 2.0,
        cy - ay * length / 2.0,
        cz - az * length / 2.0,
    )
    shape = cq.Solid.makeCylinder(radius, length, cq.Vector(*start), cq.Vector(ax, ay, az))
    return cq.Workplane("XY").newObject([shape])


def _full_sphere(radius_mm: float, center: tuple[float, float, float]) -> cq.Workplane:
    shape = cq.Solid.makeSphere(
        _positive(radius_mm, "sphere radius"),
        cq.Vector(*center),
        cq.Vector(0.0, 0.0, 1.0),
        -90.0,
        90.0,
        360.0,
    )
    return cq.Workplane("XY").newObject([shape])


def _capsule_between(
    start_xyz: tuple[float, float, float],
    end_xyz: tuple[float, float, float],
    radius_mm: float,
) -> cq.Workplane:
    dx, dy, dz = tuple(end_xyz[i] - start_xyz[i] for i in range(3))
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length <= 0.0:
        raise RetentionLoadPathError("capsule endpoints cannot coincide")
    cylinder = cq.Solid.makeCylinder(
        _positive(radius_mm, "capsule radius"),
        length,
        cq.Vector(*start_xyz),
        cq.Vector(dx / length, dy / length, dz / length),
    )
    result = cq.Workplane("XY").newObject([cylinder])
    result = result.union(_full_sphere(radius_mm, start_xyz))
    result = result.union(_full_sphere(radius_mm, end_xyz))
    return _single(result, "load-path capsule")


def _bbox(solid: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = solid.val().BoundingBox()
    return tuple(
        round(float(v), 6)
        for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    )


def _intersection_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise RetentionLoadPathError("intersection volume must be finite and nonnegative")
    return 0.0 if value < KERNEL_ZERO_MM3 else value


def _distance_mm(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().distance(second.val()))
    if not math.isfinite(value) or value < 0.0:
        raise RetentionLoadPathError("shape distance must be finite and nonnegative")
    return 0.0 if value < 1e-9 else value


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    return sha1(header + raw).hexdigest()


def _assert_source_blobs() -> None:
    sources = {
        "retention_fit_adjustment.py": SOURCE_RETENTION_FIT_GIT_BLOB_SHA,
        "hair_pinch_keepouts.py": SOURCE_HAIR_PINCH_GIT_BLOB_SHA,
        "structural_frame.py": SOURCE_STRUCTURAL_FRAME_GIT_BLOB_SHA,
    }
    for name, expected in sources.items():
        observed = _git_blob_sha(Path(__file__).with_name(name))
        if observed != expected:
            raise RetentionLoadPathError(
                f"{name} changed; retention load-path package requires explicit rebind"
            )


def _protected_solid(model: MasckOneModel, index: int) -> tuple[str, cq.Workplane]:
    volume = model.protected_volumes.all[index]
    zone = volume.zone
    wp = cq.Workplane("XY").workplane(offset=-80.0).center(zone.center.x, zone.center.y)
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


def _route_service_aabb(route) -> cq.Workplane:
    bounds_min, bounds_max = route.bounds_xyz_mm
    radius = float(route.service_envelope_radius_mm)
    minimum = tuple(float(bounds_min[i]) - radius for i in range(3))
    maximum = tuple(float(bounds_max[i]) + radius for i in range(3))
    size = tuple(maximum[i] - minimum[i] for i in range(3))
    center = tuple((maximum[i] + minimum[i]) / 2.0 for i in range(3))
    return _single(_box(size, center), f"{route.route_id} service AABB")


def _two_state_aabb(
    first: cq.Workplane,
    second: cq.Workplane,
    label: str,
) -> cq.Workplane:
    a = _bbox(first)
    b = _bbox(second)
    minimum = (min(a[0], b[0]), min(a[2], b[2]), min(a[4], b[4]))
    maximum = (max(a[1], b[1]), max(a[3], b[3]), max(a[5], b[5]))
    size = tuple(maximum[i] - minimum[i] for i in range(3))
    center = tuple((maximum[i] + minimum[i]) / 2.0 for i in range(3))
    return _single(_box(size, center), label)


@dataclass(frozen=True, slots=True)
class LoadPathPart:
    part_id: str
    side: str
    role: str
    solid: cq.Workplane
    geometry_status: str
    product_material: bool

    def __post_init__(self) -> None:
        _single(self.solid, self.part_id)
        if self.side not in {"WEARER_LEFT", "WEARER_RIGHT"}:
            raise RetentionLoadPathError("part side must use controlled wearer-relative vocabulary")

    def manifest(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "side": self.side,
            "role": self.role,
            "bounds_mm": list(_bbox(self.solid)),
            "volume_mm3": round(float(self.solid.val().Volume()), 6),
            "geometry_status": self.geometry_status,
            "product_material": self.product_material,
            "material": None,
            "mass_g": None,
        }


@dataclass(frozen=True, slots=True)
class LoadPathNode:
    node_id: str
    function: str
    geometry_id: str | None
    geometry_status: str

    def manifest(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "function": self.function,
            "geometry_id": self.geometry_id,
            "geometry_status": self.geometry_status,
        }


@dataclass(frozen=True, slots=True)
class LoadPathEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    attachment_class: str
    positive_attachment: bool
    clearance_only: bool
    load_transfer_digitally_closed: bool
    evidence: str

    def __post_init__(self) -> None:
        allowed = {
            ATTACHMENT_INTEGRAL,
            ATTACHMENT_PINNED,
            ATTACHMENT_FEATURE_OPEN,
            ATTACHMENT_CONTACT,
            ATTACHMENT_CLEARANCE,
        }
        if self.attachment_class not in allowed:
            raise RetentionLoadPathError("unsupported load-path attachment class")
        if self.positive_attachment and self.clearance_only:
            raise RetentionLoadPathError("positive attachment cannot also be clearance-only")
        if self.clearance_only and self.load_transfer_digitally_closed:
            raise RetentionLoadPathError("clearance-only relation cannot close a load path")
        if self.attachment_class == ATTACHMENT_FEATURE_OPEN and self.load_transfer_digitally_closed:
            raise RetentionLoadPathError("unrealized counterpart cannot close a load path")

    def manifest(self) -> dict[str, object]:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "attachment_class": self.attachment_class,
            "positive_attachment": self.positive_attachment,
            "clearance_only": self.clearance_only,
            "load_transfer_digitally_closed": self.load_transfer_digitally_closed,
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True)
class ClearanceCheck:
    check_id: str
    moving_id: str
    obstacle_id: str
    intersection_volume_mm3: float
    minimum_distance_mm: float | None = None

    @property
    def passes(self) -> bool:
        return self.intersection_volume_mm3 == 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "moving_id": self.moving_id,
            "obstacle_id": self.obstacle_id,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "minimum_distance_mm": self.minimum_distance_mm,
            "relation_class": ATTACHMENT_CLEARANCE,
            "load_transfer_allowed": False,
            "passes": self.passes,
        }


@dataclass(frozen=True, slots=True)
class RetentionLoadPathSide:
    side: str
    side_sign: int
    source_housing: cq.Workplane
    attachment_boss: LoadPathPart
    successor_housing: LoadPathPart
    carrier: LoadPathPart
    capture_pins: tuple[LoadPathPart, LoadPathPart]
    capture_clips: tuple[LoadPathPart, LoadPathPart]
    capture_pin_withdrawal_envelopes: tuple[cq.Workplane, cq.Workplane]
    crown_clearance_reference: cq.Workplane
    facial_clearance_reference: cq.Workplane
    crown_lug_center_xyz_mm: tuple[float, float, float]
    facial_handoff_center_xyz_mm: tuple[float, float, float]

    def manifest(self) -> dict[str, object]:
        return {
            "side": self.side,
            "attachment_boss": self.attachment_boss.manifest(),
            "successor_housing": self.successor_housing.manifest(),
            "carrier": self.carrier.manifest(),
            "capture_pins": [item.manifest() for item in self.capture_pins],
            "capture_clips": [item.manifest() for item in self.capture_clips],
            "capture_pin_withdrawal_envelope_bounds_mm": [
                list(_bbox(item)) for item in self.capture_pin_withdrawal_envelopes
            ],
            "crown_lug_center_xyz_mm": list(self.crown_lug_center_xyz_mm),
            "facial_handoff_center_xyz_mm": list(self.facial_handoff_center_xyz_mm),
            "crown_clearance_reference_bounds_mm": list(_bbox(self.crown_clearance_reference)),
            "facial_clearance_reference_bounds_mm": list(_bbox(self.facial_clearance_reference)),
        }


@dataclass(frozen=True, slots=True)
class RetentionLoadPathPackage:
    source_retention_fit_package_sha256: str
    source_hair_pinch_package_sha256: str
    source_waste_release_sha256: str
    left: RetentionLoadPathSide
    right: RetentionLoadPathSide
    nodes: tuple[LoadPathNode, ...]
    edges: tuple[LoadPathEdge, ...]
    clearance_checks: tuple[ClearanceCheck, ...]

    def __post_init__(self) -> None:
        node_ids = tuple(node.node_id for node in self.nodes)
        if len(node_ids) != len(set(node_ids)):
            raise RetentionLoadPathError("load-path node IDs cannot repeat")
        node_set = set(node_ids)
        edge_ids = tuple(edge.edge_id for edge in self.edges)
        if len(edge_ids) != len(set(edge_ids)):
            raise RetentionLoadPathError("load-path edge IDs cannot repeat")
        for edge in self.edges:
            if edge.source_node_id not in node_set or edge.target_node_id not in node_set:
                raise RetentionLoadPathError("load-path edge references missing node")
        if any(not check.passes for check in self.clearance_checks):
            failed = tuple(check.check_id for check in self.clearance_checks if not check.passes)
            raise RetentionLoadPathError(f"required retention load-path clearance failed: {failed}")

    @property
    def package_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def service_sequence(self, *, worn: bool, powered: bool) -> tuple[dict[str, object], ...]:
        if worn:
            raise RetentionLoadPathError("carrier pin service is prohibited while worn")
        if powered:
            raise RetentionLoadPathError("carrier pin service is prohibited while powered")
        return (
            {"step": 1, "action": "REMOVE_REAR_SERVICE_COVER_OR_EXTERNAL_CARRIER_COVER_IF_PRESENT"},
            {"step": 2, "action": "REMOVE_BOTH_LOW_PROFILE_CAPTURE_C_CLIPS"},
            {
                "step": 3,
                "action": "WITHDRAW_BOTH_CAPTURE_PINS_POSITIVE_Y",
                "travel_mm": CAPTURE_PIN_SERVICE_WITHDRAWAL_MM,
            },
            {
                "step": 4,
                "action": "SEPARATE_CARRIER_POSTERIORLY_FROM_HOUSING_BOSS",
                "friction_only_retention": False,
            },
            {"step": 5, "action": "REASSEMBLE_REVERSE_AND_RESEAT_BOTH_C_CLIPS"},
        )

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        positive_closed = tuple(
            edge.edge_id for edge in self.edges if edge.load_transfer_digitally_closed
        )
        open_edges = tuple(
            edge.edge_id for edge in self.edges if not edge.load_transfer_digitally_closed
        )
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_current_main_sha": SOURCE_CURRENT_MAIN_SHA,
            "source_prompt10_head_sha": SOURCE_PROMPT10_HEAD_SHA,
            "source_authority_blob_sha": SOURCE_AUTHORITY_BLOB_SHA,
            "source_authority_revision": AUTHORITY_REVISION,
            "source_retention_fit_git_blob_sha": SOURCE_RETENTION_FIT_GIT_BLOB_SHA,
            "source_hair_pinch_git_blob_sha": SOURCE_HAIR_PINCH_GIT_BLOB_SHA,
            "source_structural_frame_git_blob_sha": SOURCE_STRUCTURAL_FRAME_GIT_BLOB_SHA,
            "source_retention_fit_package_sha256": self.source_retention_fit_package_sha256,
            "source_hair_pinch_package_sha256": self.source_hair_pinch_package_sha256,
            "source_waste_release_sha256": self.source_waste_release_sha256,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "source_frame_retention_reservation_id": RESERVATION_RETENTION,
            "sides": [self.left.manifest(), self.right.manifest()],
            "load_path_graph": {
                "nodes": [node.manifest() for node in self.nodes],
                "edges": [edge.manifest() for edge in self.edges],
                "digitally_closed_edge_ids": list(positive_closed),
                "open_or_nonload_edge_ids": list(open_edges),
                "occipital_to_local_carrier_positive_path_closed": True,
                "crown_to_head_path_closed": False,
                "facial_reaction_to_front_perimeter_path_closed": False,
                "whole_retention_load_path_closed": False,
            },
            "attachment_geometry": {
                "housing_to_carrier": "DUAL_Y_AXIS_PIN_CLEVIS_WITH_HEAD_AND_C_CLIP_RETENTION",
                "capture_pin_radius_mm": CAPTURE_PIN_RADIUS_MM,
                "capture_bore_radius_mm": CAPTURE_BORE_RADIUS_MM,
                "capture_pin_radial_clearance_mm": CAPTURE_PIN_RADIAL_CLEARANCE_MM,
                "clevis_side_gap_mm": CLEVIS_SIDE_GAP_MM,
                "friction_only_attachment_allowed": False,
                "crown_lug_bore_realized": True,
                "crown_counterpart_realized": False,
                "facial_handoff_bore_realized": True,
                "front_perimeter_counterpart_realized": False,
            },
            "clearance_checks": [check.manifest() for check in self.clearance_checks],
            "service_sequence": list(self.service_sequence(worn=False, powered=False)),
            "four_zone_actuation_preserved": True,
            "assembly_in_development_compound": False,
            "assembly_exclusion_reason": (
                "FRONT_PERIMETER_FRAME_COUNTERPART_AND_CROWN_MEMBER_REMAIN_UNREALIZED"
            ),
            "unresolved_digital_requirements": [
                "FRONT_PERIMETER_REACTION_FRAME_3D_COUNTERPART_AT_FACIAL_HANDOFF_LUGS",
                "CROWN_SUPPORT_MEMBER_AND_MATING_EYELET_AT_CROWN_LUGS",
                "PROTECTIVE_GUARD_SHROUD_OR_EDGE_TREATMENT_PRODUCT_GEOMETRY",
                "RIGHT_QUICK_RELEASE_FINAL_INTEGRATION_WITH_RETENTION_CARRIER",
            ],
            "physical_validation_eligible": False,
            "unresolved_physical_gates": [
                "RETENTION_LOAD_CAPACITY_STIFFNESS_AND_STRUCTURAL_MARGIN",
                "PIN_BEARING_SHEAR_FATIGUE_AND_WEAR",
                "CROWN_SUPPORT_LOAD_SHARE_AND_CONTACT_COMFORT",
                "OCCIPITAL_CONTACT_PRESSURE_FIT_AND_HAIR_INTERACTION",
                "WET_ONE_HAND_RELEASE_FORCE_5_TO_12_N_AND_TIME_LE_2_S",
                "WHOLE_HEAD_REMOVAL_AFTER_RELEASE",
            ],
            "evidence_status": DIGITAL_ONLY,
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def _build_clip(
    x_mm: float,
    groove_center_y_mm: float,
    z_mm: float,
    side_sign: int,
) -> cq.Workplane:
    ring = (
        cq.Workplane("XZ", origin=(x_mm, groove_center_y_mm, z_mm))
        .circle(CAPTURE_CLIP_OUTER_RADIUS_MM)
        .circle(CAPTURE_CLIP_INNER_RADIUS_MM)
        .extrude(CAPTURE_CLIP_THICKNESS_MM / 2.0, both=True)
    )
    gap = _box(
        (
            CAPTURE_CLIP_GAP_MM,
            CAPTURE_CLIP_THICKNESS_MM + 0.8,
            CAPTURE_CLIP_OUTER_RADIUS_MM * 1.5,
        ),
        (
            x_mm + side_sign * CAPTURE_CLIP_OUTER_RADIUS_MM,
            groove_center_y_mm,
            z_mm,
        ),
    )
    return _single(ring.cut(gap), "capture C-clip")


def _build_capture_pin(
    x_mm: float,
    root_y_mm: float,
    z_mm: float,
) -> tuple[cq.Workplane, cq.Workplane, cq.Workplane]:
    shaft_ymin = root_y_mm - 5.5
    shaft_ymax = root_y_mm + 5.0
    shaft = _cylinder(
        CAPTURE_PIN_RADIUS_MM,
        shaft_ymax - shaft_ymin,
        (x_mm, (shaft_ymin + shaft_ymax) / 2.0, z_mm),
        (0.0, 1.0, 0.0),
    )
    head = _cylinder(
        CAPTURE_PIN_HEAD_RADIUS_MM,
        CAPTURE_PIN_HEAD_LENGTH_MM,
        (
            x_mm,
            shaft_ymax + CAPTURE_PIN_HEAD_LENGTH_MM / 2.0,
            z_mm,
        ),
        (0.0, 1.0, 0.0),
    )
    groove_center_y = shaft_ymin - CAPTURE_PIN_GROOVE_LENGTH_MM / 2.0
    groove = _cylinder(
        CAPTURE_PIN_GROOVE_RADIUS_MM,
        CAPTURE_PIN_GROOVE_LENGTH_MM,
        (x_mm, groove_center_y, z_mm),
        (0.0, 1.0, 0.0),
    )
    tip = _cylinder(
        CAPTURE_PIN_RADIUS_MM,
        CAPTURE_PIN_TIP_LENGTH_MM,
        (
            x_mm,
            groove_center_y
            - CAPTURE_PIN_GROOVE_LENGTH_MM / 2.0
            - CAPTURE_PIN_TIP_LENGTH_MM / 2.0,
            z_mm,
        ),
        (0.0, 1.0, 0.0),
    )
    pin = _single(shaft.union(head).union(groove).union(tip), "capture pin")
    withdrawn = _single(
        pin.translate((0.0, CAPTURE_PIN_SERVICE_WITHDRAWAL_MM, 0.0)),
        "withdrawn capture pin",
    )
    envelope = _two_state_aabb(pin, withdrawn, "capture pin complete service withdrawal bound")
    return pin, withdrawn, envelope


def _build_side(side: AdjustmentSide) -> RetentionLoadPathSide:
    sign = side.side_sign
    hb = _bbox(side.housing)
    housing_x = (hb[0] + hb[1]) / 2.0
    root_y = float(side.root_xyz_mm[1])
    housing_posterior_z = hb[4]

    boss_center = (
        housing_x,
        root_y,
        housing_posterior_z - HOUSING_BOSS_POSTERIOR_EXTENSION_MM / 2.0,
    )
    boss = _single(_box(HOUSING_BOSS_XYZ_MM, boss_center), f"{side.side} attachment boss")
    successor_housing = _single(side.housing.union(boss), f"{side.side} successor fixed housing")

    pin_centers = tuple(
        (housing_x + offset, root_y, boss_center[2]) for offset in CAPTURE_PIN_X_OFFSETS_MM
    )
    for center in pin_centers:
        successor_housing = _single(
            successor_housing.cut(
                _cylinder(
                    CAPTURE_BORE_RADIUS_MM,
                    HOUSING_BOSS_XYZ_MM[1] + 2.0,
                    center,
                    (0.0, 1.0, 0.0),
                )
            ),
            f"{side.side} bored successor housing",
        )

    boss_min_z = boss_center[2] - HOUSING_BOSS_XYZ_MM[2] / 2.0
    plate_center = (
        housing_x,
        root_y,
        boss_min_z - CARRIER_BOSS_POSTERIOR_GAP_MM - CARRIER_BACKPLATE_XYZ_MM[2] / 2.0,
    )
    plate = _box(CARRIER_BACKPLATE_XYZ_MM, plate_center)

    ear_center_z = (
        housing_posterior_z
        - CARRIER_HOUSING_FACE_GAP_MM
        - CARRIER_EAR_XYZ_MM[2] / 2.0
    )
    ear_y_offset = (hb[3] - hb[2]) / 2.0 - 0.5
    ear_a = _box(
        CARRIER_EAR_XYZ_MM,
        (housing_x, root_y - ear_y_offset, ear_center_z),
    )
    ear_b = _box(
        CARRIER_EAR_XYZ_MM,
        (housing_x, root_y + ear_y_offset, ear_center_z),
    )
    carrier = _single(plate.union(ear_a).union(ear_b), f"{side.side} carrier clevis body")

    link_start = (
        housing_x - sign * 2.5,
        root_y + 4.0,
        plate_center[2],
    )
    crown_center = (
        sign * CROWN_LUG_CENTER_ABS_X_MM,
        CROWN_LUG_CENTER_Y_MM,
        CROWN_LUG_CENTER_Z_MM,
    )
    facial_elbow = (
        sign * FACIAL_LINK_ELBOW_ABS_X_MM,
        FACIAL_LINK_ELBOW_Y_MM,
        plate_center[2],
    )
    facial_center = (
        sign * FACIAL_HANDOFF_CENTER_ABS_X_MM,
        FACIAL_HANDOFF_CENTER_Y_MM,
        FACIAL_HANDOFF_CENTER_Z_MM,
    )
    carrier = _single(
        carrier
        .union(_capsule_between(link_start, crown_center, CARRIER_LINK_RADIUS_MM))
        .union(_capsule_between(link_start, facial_elbow, CARRIER_LINK_RADIUS_MM))
        .union(_capsule_between(facial_elbow, facial_center, CARRIER_LINK_RADIUS_MM))
        .union(_box(CROWN_LUG_XYZ_MM, crown_center))
        .union(_box(FACIAL_HANDOFF_XYZ_MM, facial_center)),
        f"{side.side} connected load-path carrier before bores",
    )

    for center in pin_centers:
        carrier = _single(
            carrier.cut(
                _cylinder(
                    CAPTURE_BORE_RADIUS_MM,
                    CARRIER_BACKPLATE_XYZ_MM[1] + 2.0,
                    center,
                    (0.0, 1.0, 0.0),
                )
            ),
            f"{side.side} carrier with capture-pin bores",
        )
    carrier = _single(
        carrier.cut(
            _cylinder(
                CROWN_LUG_BORE_RADIUS_MM,
                CROWN_LUG_XYZ_MM[0] + 2.0,
                crown_center,
                (1.0, 0.0, 0.0),
            )
        ),
        f"{side.side} carrier with crown attachment bore",
    )
    carrier = _single(
        carrier.cut(
            _cylinder(
                FACIAL_HANDOFF_BORE_RADIUS_MM,
                FACIAL_HANDOFF_XYZ_MM[1] + 2.0,
                facial_center,
                (0.0, 1.0, 0.0),
            )
        ),
        f"{side.side} carrier with facial handoff bore",
    )

    pin_parts: list[LoadPathPart] = []
    clip_parts: list[LoadPathPart] = []
    envelopes: list[cq.Workplane] = []
    for index, center in enumerate(pin_centers, start=1):
        pin, _, envelope = _build_capture_pin(center[0], root_y, center[2])
        clip_center_y = root_y - 5.5 - CAPTURE_PIN_GROOVE_LENGTH_MM / 2.0
        clip = _build_clip(center[0], clip_center_y, center[2], sign)
        prefix = "RIGHT" if sign > 0 else "LEFT"
        pin_parts.append(
            LoadPathPart(
                f"RETENTION_{prefix}_HOUSING_CAPTURE_PIN_{index}",
                side.side,
                "dual-pin positive housing-to-carrier shear/capture member",
                pin,
                "CELL3_PROVISIONAL_PIN_GEOMETRY_MATERIAL_AND_LOAD_CAPACITY_UNVALIDATED",
                True,
            )
        )
        clip_parts.append(
            LoadPathPart(
                f"RETENTION_{prefix}_HOUSING_CAPTURE_CLIP_{index}",
                side.side,
                "low-profile axial pin retainer; friction is not the retention mechanism",
                clip,
                "CELL3_PROVISIONAL_CLIP_GEOMETRY_MATERIAL_AND_RETENTION_FORCE_UNVALIDATED",
                True,
            )
        )
        envelopes.append(envelope)

    prefix = "RIGHT" if sign > 0 else "LEFT"
    boss_part = LoadPathPart(
        f"RETENTION_{prefix}_FIXED_HOUSING_ATTACHMENT_BOSS",
        side.side,
        "integral posterior successor boss carrying two positive capture bores",
        boss,
        "CELL3_PROVISIONAL_ATTACHMENT_BOSS",
        True,
    )
    housing_part = LoadPathPart(
        f"RETENTION_{prefix}_FIXED_HOUSING_LOAD_PATH_SUCCESSOR",
        side.side,
        "Prompt 09 fixed guide housing plus integral posterior dual-pin attachment boss",
        successor_housing,
        "CELL3_PROVISIONAL_LOAD_PATH_SUCCESSOR_OF_PROMPT09_FIXED_HOUSING",
        True,
    )
    carrier_part = LoadPathPart(
        f"RETENTION_{prefix}_LOCAL_REACTION_CARRIER",
        side.side,
        (
            "compact posterior carrier joining housing clevis, crown attachment lug and "
            "facial-reaction handoff lug"
        ),
        carrier,
        "CELL3_PROVISIONAL_LOCAL_REACTION_CARRIER_MATERIAL_AND_STRENGTH_UNVALIDATED",
        True,
    )

    crown_clearance = _single(
        _cylinder(
            CROWN_CLEARANCE_RADIUS_MM,
            CROWN_CLEARANCE_LENGTH_MM,
            crown_center,
            (1.0, 0.0, 0.0),
        ),
        f"{side.side} crown counterpart clearance reference",
    )
    facial_clearance = _single(
        _cylinder(
            FACIAL_CLEARANCE_RADIUS_MM,
            FACIAL_CLEARANCE_LENGTH_MM,
            facial_center,
            (0.0, 1.0, 0.0),
        ),
        f"{side.side} facial counterpart clearance reference",
    )
    return RetentionLoadPathSide(
        side=side.side,
        side_sign=sign,
        source_housing=side.housing,
        attachment_boss=boss_part,
        successor_housing=housing_part,
        carrier=carrier_part,
        capture_pins=(pin_parts[0], pin_parts[1]),
        capture_clips=(clip_parts[0], clip_parts[1]),
        capture_pin_withdrawal_envelopes=(envelopes[0], envelopes[1]),
        crown_clearance_reference=crown_clearance,
        facial_clearance_reference=facial_clearance,
        crown_lug_center_xyz_mm=crown_center,
        facial_handoff_center_xyz_mm=facial_center,
    )


def _graph(left: RetentionLoadPathSide, right: RetentionLoadPathSide) -> tuple[
    tuple[LoadPathNode, ...], tuple[LoadPathEdge, ...]
]:
    nodes: list[LoadPathNode] = [
        LoadPathNode(
            "FRONT_PERIMETER_REACTION_LOOP",
            "FACIAL_REACTION",
            None,
            "RELEASED_STRUCTURAL_FRAME_TOPOLOGY_ONLY_3D_COUNTERPART_UNREALIZED",
        ),
        LoadPathNode(
            "CROWN_SUPPORT_MEMBER",
            "CROWN_SUPPORT",
            None,
            "CROWN_MEMBER_UNREALIZED_ATTACHMENT_LUGS_ONLY",
        ),
    ]
    edges: list[LoadPathEdge] = []
    for item in (left, right):
        prefix = "RIGHT" if item.side_sign > 0 else "LEFT"
        yoke = f"{prefix}_OCCIPITAL_YOKE_AND_TONGUE"
        housing = f"{prefix}_FIXED_ADJUSTMENT_HOUSING"
        carrier = f"{prefix}_LOCAL_REACTION_CARRIER"
        crown = f"{prefix}_CROWN_ATTACHMENT_LUG"
        facial = f"{prefix}_FACIAL_REACTION_HANDOFF_LUG"
        nodes.extend(
            (
                LoadPathNode(
                    yoke,
                    "OCCIPITAL_STABILIZATION",
                    f"OCCIPITAL_STABILIZER_{prefix}_YOKE",
                    "PROMPT09_SUCCESSOR_YOKE_WITH_INTEGRAL_INDEXED_TONGUE",
                ),
                LoadPathNode(
                    housing,
                    "OCCIPITAL_STABILIZATION_TO_STRUCTURE",
                    item.successor_housing.part_id,
                    "ACTUAL_FIXED_HOUSING_SUCCESSOR_WITH_DUAL_PIN_ATTACHMENT_BOSS",
                ),
                LoadPathNode(
                    carrier,
                    "LOCAL_RETENTION_REACTION_DISTRIBUTION",
                    item.carrier.part_id,
                    "ACTUAL_CONNECTED_CARRIER_GEOMETRY",
                ),
                LoadPathNode(
                    crown,
                    "CROWN_SUPPORT_HANDOFF",
                    item.carrier.part_id,
                    "ACTUAL_CARRIER_LUG_AND_THROUGH_BORE_COUNTERPART_UNREALIZED",
                ),
                LoadPathNode(
                    facial,
                    "FACIAL_REACTION_HANDOFF",
                    item.carrier.part_id,
                    "ACTUAL_CARRIER_LUG_AND_THROUGH_BORE_COUNTERPART_UNREALIZED",
                ),
            )
        )
        edges.extend(
            (
                LoadPathEdge(
                    f"{prefix}_YOKE_TO_FIXED_HOUSING",
                    yoke,
                    housing,
                    ATTACHMENT_PINNED,
                    True,
                    False,
                    True,
                    "Prompt 09 permanent stop pin plus engaged index pin; no friction-only retention",
                ),
                LoadPathEdge(
                    f"{prefix}_FIXED_HOUSING_TO_LOCAL_CARRIER",
                    housing,
                    carrier,
                    ATTACHMENT_PINNED,
                    True,
                    False,
                    True,
                    "new dual Y-axis retained capture pins through successor boss and carrier clevis",
                ),
                LoadPathEdge(
                    f"{prefix}_LOCAL_CARRIER_TO_CROWN_LUG",
                    carrier,
                    crown,
                    ATTACHMENT_INTEGRAL,
                    True,
                    False,
                    True,
                    "crown lug is integral material in the connected carrier B-rep",
                ),
                LoadPathEdge(
                    f"{prefix}_CROWN_LUG_TO_CROWN_MEMBER",
                    crown,
                    "CROWN_SUPPORT_MEMBER",
                    ATTACHMENT_FEATURE_OPEN,
                    True,
                    False,
                    False,
                    "real bore/clearance exists but crown member and mating eyelet are not realized",
                ),
                LoadPathEdge(
                    f"{prefix}_LOCAL_CARRIER_TO_FACIAL_HANDOFF",
                    carrier,
                    facial,
                    ATTACHMENT_INTEGRAL,
                    True,
                    False,
                    True,
                    "facial handoff lug is integral material in the connected carrier B-rep",
                ),
                LoadPathEdge(
                    f"{prefix}_FACIAL_HANDOFF_TO_FRONT_REACTION_LOOP",
                    facial,
                    "FRONT_PERIMETER_REACTION_LOOP",
                    ATTACHMENT_FEATURE_OPEN,
                    True,
                    False,
                    False,
                    "real bore/clearance exists but front perimeter 3D mating counterpart remains topology-only",
                ),
            )
        )
    return tuple(nodes), tuple(edges)


def build_retention_load_path(
    authority: Authority | None = None,
    model: MasckOneModel | None = None,
    fit_adjustment: RetentionFitAdjustment | None = None,
    hair_pinch: HairPinchKeepoutPackage | None = None,
) -> RetentionLoadPathPackage:
    _assert_source_blobs()
    authority = authority or load_authority()
    model = model or build_model(authority)
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise RetentionLoadPathError("retention load path is stale for current authority revision")
    if int(authority.number("actuation", "count")) != 4 or len(model.actuator_envelopes) != 4:
        raise RetentionLoadPathError("four independently controllable actuation zones must be preserved")
    if str(authority.get("coordinate_system", "x_positive")) != "wearer_right":
        raise RetentionLoadPathError("authority X axis changed")
    if str(authority.get("coordinate_system", "y_positive")) != "superior":
        raise RetentionLoadPathError("authority Y axis changed")
    if str(authority.get("coordinate_system", "z_positive")) != "anterior":
        raise RetentionLoadPathError("authority Z axis changed")

    fit = fit_adjustment or build_retention_fit_adjustment(authority, model)
    hair = hair_pinch or build_hair_pinch_keepouts(authority, model, fit)

    left = _build_side(fit.left)
    right = _build_side(fit.right)
    nodes, edges = _graph(left, right)

    if not math.isclose(
        CAPTURE_PIN_RADIAL_CLEARANCE_MM,
        0.15,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise RetentionLoadPathError("capture-pin radial clearance contract changed")
    if CAPTURE_PIN_HEAD_RADIUS_MM <= CAPTURE_BORE_RADIUS_MM:
        raise RetentionLoadPathError("capture pin head must positively exceed bore radius")
    if CAPTURE_CLIP_INNER_RADIUS_MM >= CAPTURE_PIN_RADIUS_MM:
        raise RetentionLoadPathError("capture clip must be trapped behind pin shank shoulder")
    if CAPTURE_CLIP_INNER_RADIUS_MM <= CAPTURE_PIN_GROOVE_RADIUS_MM:
        raise RetentionLoadPathError("capture clip must clear the groove root")
    if min(abs(a - b) for a in CAPTURE_PIN_X_OFFSETS_MM for b in CAPTURE_PIN_X_OFFSETS_MM if a != b) <= 2.0 * CAPTURE_BORE_RADIUS_MM:
        raise RetentionLoadPathError("dual capture bores must remain geometrically independent")

    checks: list[ClearanceCheck] = []

    def add(
        check_id: str,
        moving_id: str,
        moving: cq.Workplane,
        obstacle_id: str,
        obstacle: cq.Workplane,
        *,
        include_distance: bool = False,
    ) -> None:
        checks.append(
            ClearanceCheck(
                check_id,
                moving_id,
                obstacle_id,
                _intersection_mm3(moving, obstacle),
                _distance_mm(moving, obstacle) if include_distance else None,
            )
        )

    for side in (left, right):
        add(
            f"CLEAR_{side.side}_SUCCESSOR_HOUSING_FROM_CARRIER_MATERIAL",
            side.successor_housing.part_id,
            side.successor_housing.solid,
            side.carrier.part_id,
            side.carrier.solid,
            include_distance=True,
        )
        for pin in side.capture_pins:
            add(
                f"CLEAR_{pin.part_id}_SUCCESSOR_HOUSING",
                pin.part_id,
                pin.solid,
                side.successor_housing.part_id,
                side.successor_housing.solid,
            )
            add(
                f"CLEAR_{pin.part_id}_CARRIER",
                pin.part_id,
                pin.solid,
                side.carrier.part_id,
                side.carrier.solid,
            )
        for clip, pin in zip(side.capture_clips, side.capture_pins):
            add(
                f"CLEAR_{clip.part_id}_{pin.part_id}",
                clip.part_id,
                clip.solid,
                pin.part_id,
                pin.solid,
            )
            add(
                f"CLEAR_{clip.part_id}_SUCCESSOR_HOUSING",
                clip.part_id,
                clip.solid,
                side.successor_housing.part_id,
                side.successor_housing.solid,
            )
            add(
                f"CLEAR_{clip.part_id}_CARRIER",
                clip.part_id,
                clip.solid,
                side.carrier.part_id,
                side.carrier.solid,
            )

        physical_parts = (
            side.successor_housing,
            side.carrier,
            *side.capture_pins,
            *side.capture_clips,
        )
        for part in physical_parts:
            for component in (
                model.shell,
                *model.actuator_envelopes,
                model.water_reservoir_envelope,
                model.waste_cartridge_envelope,
                model.battery_reference_envelope,
            ):
                add(
                    f"CLEAR_{part.part_id}_{component.name.upper()}",
                    part.part_id,
                    part.solid,
                    component.name.upper(),
                    component.solid,
                )
            for index in range(len(model.protected_volumes.all)):
                zone_id, protected = _protected_solid(model, index)
                add(
                    f"CLEAR_{part.part_id}_{zone_id}",
                    part.part_id,
                    part.solid,
                    zone_id,
                    protected,
                )

        # Prompt 10 hazard/access regions are reference-only no-load space. Screen only
        # newly added material, not the inherited source housing that intentionally borders
        # the guide-nip hazard volumes.
        new_material_parts = (
            side.attachment_boss,
            side.carrier,
            *side.capture_pins,
            *side.capture_clips,
        )
        for part in new_material_parts:
            for region in hair.hazard_regions:
                add(
                    f"CLEAR_{part.part_id}_{region.region_id}",
                    part.part_id,
                    part.solid,
                    region.region_id,
                    region.solid,
                )
            for region in hair.access_regions:
                add(
                    f"CLEAR_{part.part_id}_{region.region_id}",
                    part.part_id,
                    part.solid,
                    region.region_id,
                    region.solid,
                )

        for envelope_index, envelope in enumerate(
            side.capture_pin_withdrawal_envelopes, start=1
        ):
            for region in hair.access_regions:
                add(
                    f"CLEAR_{side.side}_PIN_{envelope_index}_SERVICE_{region.region_id}",
                    f"{side.side}_CAPTURE_PIN_{envelope_index}_SERVICE_ENVELOPE",
                    envelope,
                    region.region_id,
                    region.solid,
                )

    waste_release = build_current_cell4_waste_backbone_release()
    for route in waste_release.realization.routes:
        service = _route_service_aabb(route)
        for side in (left, right):
            for part in (
                side.successor_housing,
                side.carrier,
                *side.capture_pins,
                *side.capture_clips,
            ):
                add(
                    f"CLEAR_{part.part_id}_{route.route_id}_SERVICE_AABB",
                    part.part_id,
                    part.solid,
                    f"{route.route_id}_SERVICE_AABB",
                    service,
                )

    return RetentionLoadPathPackage(
        source_retention_fit_package_sha256=fit.package_sha256,
        source_hair_pinch_package_sha256=hair.package_sha256,
        source_waste_release_sha256=waste_release.manifest_sha256,
        left=left,
        right=right,
        nodes=nodes,
        edges=edges,
        clearance_checks=tuple(checks),
    )


def export_retention_load_path(
    output_dir: str | Path,
    package: RetentionLoadPathPackage,
) -> tuple[Path, ...]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    entries: list[tuple[str, cq.Workplane]] = []
    for side in (package.left, package.right):
        prefix = "right" if side.side_sign > 0 else "left"
        entries.extend(
            (
                (f"retention_load_path_{prefix}_successor_housing.step", side.successor_housing.solid),
                (f"retention_load_path_{prefix}_carrier.step", side.carrier.solid),
                (f"retention_load_path_{prefix}_capture_pin_1.step", side.capture_pins[0].solid),
                (f"retention_load_path_{prefix}_capture_pin_2.step", side.capture_pins[1].solid),
                (f"retention_load_path_{prefix}_capture_clip_1.step", side.capture_clips[0].solid),
                (f"retention_load_path_{prefix}_capture_clip_2.step", side.capture_clips[1].solid),
                (
                    f"retention_load_path_{prefix}_capture_pin_1_service_envelope_reference.step",
                    side.capture_pin_withdrawal_envelopes[0],
                ),
                (
                    f"retention_load_path_{prefix}_capture_pin_2_service_envelope_reference.step",
                    side.capture_pin_withdrawal_envelopes[1],
                ),
                (
                    f"retention_load_path_{prefix}_crown_counterpart_clearance_reference.step",
                    side.crown_clearance_reference,
                ),
                (
                    f"retention_load_path_{prefix}_facial_counterpart_clearance_reference.step",
                    side.facial_clearance_reference,
                ),
            )
        )
    for name, solid in entries:
        _single(solid, name)
        path = root / name
        cq.exporters.export(solid, str(path))
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"failed to export {name}")
        outputs.append(path)

    manifest_path = root / "retention_load_path_manifest.json"
    manifest_path.write_text(
        json.dumps(package.manifest(), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    outputs.append(manifest_path)
    return tuple(outputs)
