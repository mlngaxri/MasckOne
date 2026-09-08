from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Vec

from .model import MasckOneModel, build_model
from .structural_frame_actuator_mates import (
    CARRIER_PAD_THICKNESS_MM,
    SHOULDER_GAP_MM,
    SHOULDER_HEIGHT_MM,
    SHOULDER_THICKNESS_MM,
    SHOULDER_WIDTH_MM,
    StructuralFrameActuatorMateArchitecture,
    build_structural_frame_actuator_mates,
)
from .structural_frame_actuator_reactions import (
    REACTION_IDS,
    StructuralFrameActuatorReactionArchitecture,
    build_structural_frame_actuator_reactions,
)
from .structural_frame_carrier_detent import build_structural_frame_carrier_detent
from .structural_frame_carrier_interfaces import build_structural_frame_carrier_interfaces
from .structural_frame_carrier_landing import build_structural_frame_carrier_landing
from .structural_frame_carrier_preload import build_structural_frame_carrier_preload
from .structural_frame_realization import _protected_zone_solid
from .treatment_carrier_counterpart import (
    TreatmentCarrierCounterpartArchitecture,
    build_treatment_carrier_counterparts,
)

SCHEMA = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

SOURCE_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
SOURCE_CELL6_HEAD_SHA = "3e840d52d641b429669928ab9e4c207f08086ca1"
SOURCE_TREATMENT_HEAD_SHA = "2bcdba02e9ee30e86baa74e7cecc9095e8bf4a71"

TREATMENT_AXIS_DEG = 61.0
STATION_CENTERS_MM = {
    "ACTUATOR_REACTION_SUPERIOR_LEFT": (-36.0, 70.0, 7.0),
    "ACTUATOR_REACTION_SUPERIOR_RIGHT": (36.0, 70.0, 7.0),
    "ACTUATOR_REACTION_INFERIOR_LEFT": (-52.0, -45.0, 3.0),
    "ACTUATOR_REACTION_INFERIOR_RIGHT": (52.0, -45.0, 3.0),
}
STATION_AXIS_DEG = {
    "ACTUATOR_REACTION_SUPERIOR_LEFT": -TREATMENT_AXIS_DEG,
    "ACTUATOR_REACTION_SUPERIOR_RIGHT": TREATMENT_AXIS_DEG,
    "ACTUATOR_REACTION_INFERIOR_LEFT": -TREATMENT_AXIS_DEG,
    "ACTUATOR_REACTION_INFERIOR_RIGHT": TREATMENT_AXIS_DEG,
}

SERVICE_WITHDRAWAL_MM = 32.0
OPERATIONAL_HALF_STROKE_MM = 0.26

# Rigid shoulder bypass. The Cell 6 rail/preload/landing/detent guide service motion,
# while this treatment-owned open yoke reacts working dynamic load directly into the
# rigid Cell 6 shoulder/keyed mate, bypassing its intentionally compliant bridge.
YOKE_X_CLEARANCE_MM = 0.16
YOKE_Z_CLEARANCE_MM = 0.12
YOKE_WALL_MM = 0.50
YOKE_BACK_GAP_MM = 0.08
YOKE_BACK_WALL_MM = 0.55
YOKE_OPEN_EXTENSION_MM = 0.50
YOKE_LIP_INSET_MM = 1.15
YOKE_SHOE_LINK_LENGTH_MM = 0.90
YOKE_SHOE_LINK_OVERLAP_MM = 0.20

# Two-chord posterior reaction truss. This replaces the previous bending-dominated
# 4.8 x 2.0 x 0.35 mm hollow cantilever study.
TRUSS_CHORD_RADIUS_MM = 1.10
TRUSS_BRACE_RADIUS_MM = 0.70
TRUSS_REAR_ANCHOR_RADIUS_MM = 2.50
TRUSS_REAR_ANCHOR_LOCAL_Z_MM = -8.90
TRUSS_CONSERVATIVE_MOMENT_ARM_MM = 4.0
TRUSS_POLYMER_SCREEN_E_MPA = 2500.0
CONTINUOUS_FORCE_REFERENCE_N = 0.20
TRANSIENT_FORCE_REFERENCE_N = 0.60

_INTERSECTION_TOLERANCE_MM3 = 1e-7


class TreatmentMountedFourZoneError(ValueError):
    pass


def _box(x: float, y: float, z: float, center: tuple[float, float, float]) -> cq.Shape:
    if min(x, y, z) <= 0.0:
        raise TreatmentMountedFourZoneError("box dimensions must be positive")
    return cq.Workplane("XY").box(x, y, z).translate(center).val()


def _cylinder(r: float, z0: float, z1: float) -> cq.Shape:
    if r <= 0.0 or z1 <= z0:
        raise TreatmentMountedFourZoneError("cylinder dimensions must be positive")
    return cq.Workplane("XY").circle(r).extrude(z1 - z0).translate((0.0, 0.0, z0)).val()


def _ring(ri: float, ro: float, z0: float, z1: float) -> cq.Shape:
    return _cylinder(ro, z0, z1).cut(_cylinder(ri, z0 - 1.0, z1 + 1.0))


def _bar(a: tuple[float, float, float], b: tuple[float, float, float], r: float) -> cq.Shape:
    va, vb = cq.Vector(*a), cq.Vector(*b)
    direction = vb - va
    if direction.Length <= 0.0 or r <= 0.0:
        raise TreatmentMountedFourZoneError("bar requires positive span and radius")
    return cq.Solid.makeCylinder(r, direction.Length, va, direction.normalized())


def _join(shapes: list[cq.Shape]) -> cq.Shape:
    if not shapes:
        raise TreatmentMountedFourZoneError("cannot join empty shape list")
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    result = result.clean()
    if not result.isValid() or len(result.Solids()) != 1:
        raise TreatmentMountedFourZoneError("joined material must remain one valid solid")
    return result


def _iv(a: cq.Shape, b: cq.Shape) -> float:
    aa, bb = a.BoundingBox(), b.BoundingBox()
    if any(
        getattr(aa, axis + "max") < getattr(bb, axis + "min")
        or getattr(bb, axis + "max") < getattr(aa, axis + "min")
        for axis in "xyz"
    ):
        return 0.0
    try:
        common = a.intersect(b)
    except Exception as exc:
        raise TreatmentMountedFourZoneError("intersection kernel failure") from exc
    if not common.isValid():
        raise TreatmentMountedFourZoneError("invalid intersection result")
    volume = sum(max(0.0, float(s.Volume())) for s in common.Solids())
    if not math.isfinite(volume):
        raise TreatmentMountedFourZoneError("nonfinite intersection volume")
    return volume


def _pose(shape: cq.Shape, center: tuple[float, float, float], angle_deg: float) -> cq.Shape:
    return shape.rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), angle_deg).translate(center)


def _pose_point(
    point: tuple[float, float, float],
    center: tuple[float, float, float],
    angle_deg: float,
) -> tuple[float, float, float]:
    vertex = cq.Vertex.makeVertex(*point)
    out = _pose(vertex, center, angle_deg).Center()
    return (float(out.x), float(out.y), float(out.z))


def _translation_envelope(shape: cq.Shape, travel: tuple[float, float, float]) -> cq.Shape:
    pieces: list[cq.Shape] = [shape, shape.translate(travel)]
    for face in shape.Faces():
        prism = cq.Shape.cast(
            BRepPrimAPI_MakePrism(face.wrapped, gp_Vec(*travel)).Shape()
        )
        pieces.extend(prism.Solids())
    return _join(pieces)


def _spiral(z: float, hand: int, thickness: float = 0.05) -> cq.Shape:
    arms: list[cq.Shape] = []
    for phase in (0.0, 120.0, 240.0):
        s = np.linspace(0.0, 1.0, 81)
        radius = 6.95 + (2.85 - 6.95) * s
        theta = np.radians(phase + hand * 110.0 * s)
        points = np.column_stack((radius * np.cos(theta), radius * np.sin(theta)))
        tangent = np.gradient(points, axis=0)
        tangent /= np.linalg.norm(tangent, axis=1)[:, None]
        normal = np.column_stack((-tangent[:, 1], tangent[:, 0]))
        outline = np.vstack((points + 0.20 * normal, (points - 0.20 * normal)[::-1]))
        arm = (
            cq.Workplane("XY")
            .polyline(outline.tolist())
            .close()
            .extrude(thickness)
            .translate((0.0, 0.0, z - thickness / 2.0))
            .val()
        )
        ends = [
            _cylinder(0.20, z - thickness / 2.0, z + thickness / 2.0).translate(
                (float(point[0]), float(point[1]), 0.0)
            )
            for point in (points[0], points[-1])
        ]
        arms.append(_join([arm, *ends]))
    return _join(
        [
            _ring(1.60, 3.05, z - thickness / 2.0, z + thickness / 2.0),
            _ring(6.80, 7.60, z - thickness / 2.0, z + thickness / 2.0),
            *arms,
        ]
    )


def _cup_features(lo: float = 0.0, hi: float = 0.0) -> list[cq.Shape]:
    parts = [
        _ring(6.8, 7.6, -7.85 + lo, -7.525 + hi),
        _ring(1.6, 6.4, 6.8 + lo, 7.2 + hi),
        _ring(1.6, 2.8, 7.15 + lo, 7.975 + hi),
    ]
    for deg in (0.0, 120.0, 240.0):
        theta = math.radians(deg)
        x, y = 6.35 * math.cos(theta), 6.35 * math.sin(theta)
        parts.extend(
            [
                _cylinder(0.23, -7.65 + lo, 7.0 + hi).translate((x, y, 0.0)),
                _box(0.95, 0.40, 0.40 + hi - lo, (6.75, 0.0, -7.65 + (lo + hi) / 2.0)).rotate(
                    (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), deg
                ),
            ]
        )
    return parts


def _local_cassette_material() -> tuple[dict[str, cq.Shape], dict[str, cq.Shape]]:
    material: dict[str, cq.Shape] = {}
    reference: dict[str, cq.Shape] = {}
    material["rear_spiral"] = _spiral(-7.50, 1)
    material["front_spiral"] = _spiral(8.00, -1)
    material["moving_cup"] = _join(_cup_features())
    material["moving_rear_clamp"] = _ring(6.8, 7.6, -7.475, -7.20)
    material["moving_front_clamp"] = _ring(1.6, 2.8, 8.025, 8.30)

    back = _ring(1.6, 3.0, -9.10, -8.70)
    fixed = [back, _ring(1.6, 2.8, -8.80, -7.525), _ring(6.8, 8.7, 8.025, 8.60)]
    for deg in (60.0, 180.0, 300.0):
        theta = math.radians(deg)
        x, y = 8.25 * math.cos(theta), 8.25 * math.sin(theta)
        fixed.extend(
            [
                _cylinder(0.40, -8.90, 8.40).translate((x, y, 0.0)),
                _bar((0.0, 0.0, -8.90), (x, y, -8.90), 0.30),
            ]
        )
    fixed_cage = _join(fixed)

    rear_stop = _join(
        [
            _ring(6.8, 7.6, -8.40, -8.30),
            *[
                _cylinder(0.22, -8.90, -8.30).translate(
                    (7.1 * math.cos(math.radians(deg)), 7.1 * math.sin(math.radians(deg)), 0.0)
                )
                for deg in (60.0, 180.0, 300.0)
            ],
        ]
    )
    material["rear_buffer"] = _ring(6.8, 7.6, -8.30, -8.20)
    material["fixed_cage"] = _join([fixed_cage, rear_stop])

    front_stop = _join(
        [
            _ring(3.1, 6.4, 7.78, 7.975),
            _ring(3.1, 3.6, 7.65, 7.78),
            _ring(6.0, 6.4, 7.65, 7.78),
            *[
                _bar(
                    (6.2 * math.cos(math.radians(deg)), 6.2 * math.sin(math.radians(deg)), 7.85),
                    (7.1 * math.cos(math.radians(deg)), 7.1 * math.sin(math.radians(deg)), 7.85),
                    0.12,
                )
                for deg in (60.0, 180.0, 300.0)
            ],
            _ring(6.8, 8.7, 7.70, 7.975),
        ]
    )
    material["front_stop_ring"] = front_stop
    material["front_buffer_inner"] = _ring(3.1, 3.6, 7.55, 7.65)
    material["front_buffer_outer"] = _ring(6.0, 6.4, 7.55, 7.65)
    material["rear_magnet_seating_spacer"] = _ring(1.6, 2.8, -7.20, -7.10)

    reference["supplier_total_package_bound"] = _cylinder(5.55, -7.10, 6.80)
    return material, reference


def _moving_output_linkage(
    station_kind: str,
    center: tuple[float, float, float],
    angle_deg: float,
) -> cq.Shape:
    dy = 10.0 if station_kind == "superior" else -10.0
    arm_z = (
        -6.6
        if station_kind == "superior"
        else -6.6 + (5.0 - center[2]) / math.cos(math.radians(TREATMENT_AXIS_DEG))
    )
    outer = _box(1.4, abs(dy) + 0.6, 1.0, (7.1, dy / 2.0, arm_z))
    inner = _box(1.0, abs(dy) + 1.0, 0.6, (7.1, dy / 2.0, arm_z))
    arm = outer.cut(inner)
    arm = _join(
        [
            arm,
            _cylinder(0.40, -7.40, arm_z + 0.50).translate((7.1, 0.0, 0.0)),
            _cylinder(0.40, arm_z - 0.50, arm_z + 0.50).translate((7.1, dy, 0.0)),
        ]
    )
    takeoff = _pose_point((7.1, dy, arm_z), center, angle_deg)
    shoe_center = (takeoff[0], takeoff[1], -6.30)
    return _join(
        [
            _pose(arm, center, angle_deg),
            _box(8.0, 10.0, 0.60, shoe_center),
            _bar(takeoff, (takeoff[0], takeoff[1], -6.20), 0.40),
        ]
    )


def _rigid_shoulder_yoke(
    reaction_id: str,
    shoe: cq.Shape,
    frame_zmax: float,
    reaction_xy: tuple[float, float],
) -> cq.Shape:
    cx, cy = reaction_xy
    shoulder_z0 = frame_zmax + SHOULDER_GAP_MM
    shoulder_z1 = shoulder_z0 + SHOULDER_THICKNESS_MM
    y_min = cy - SHOULDER_HEIGHT_MM / 2.0 - YOKE_OPEN_EXTENSION_MM
    y_max = cy + SHOULDER_HEIGHT_MM / 2.0 + YOKE_BACK_GAP_MM + YOKE_BACK_WALL_MM
    z_min = shoulder_z0 - YOKE_Z_CLEARANCE_MM - YOKE_WALL_MM
    z_max = shoulder_z1 + YOKE_Z_CLEARANCE_MM + YOKE_WALL_MM
    side_x = SHOULDER_WIDTH_MM / 2.0 + YOKE_X_CLEARANCE_MM + YOKE_WALL_MM / 2.0

    parts = [
        _box(YOKE_WALL_MM, y_max - y_min, z_max - z_min, (cx - side_x, (y_min + y_max) / 2.0, (z_min + z_max) / 2.0)),
        _box(YOKE_WALL_MM, y_max - y_min, z_max - z_min, (cx + side_x, (y_min + y_max) / 2.0, (z_min + z_max) / 2.0)),
        _box(
            2.0 * side_x + YOKE_WALL_MM,
            YOKE_BACK_WALL_MM,
            z_max - z_min,
            (cx, cy + SHOULDER_HEIGHT_MM / 2.0 + YOKE_BACK_GAP_MM + YOKE_BACK_WALL_MM / 2.0, (z_min + z_max) / 2.0),
        ),
    ]
    for sign in (-1.0, 1.0):
        lip_x = cx + sign * (SHOULDER_WIDTH_MM / 2.0 - YOKE_LIP_INSET_MM / 2.0)
        parts.extend(
            [
                _box(YOKE_LIP_INSET_MM, y_max - y_min, YOKE_WALL_MM, (lip_x, (y_min + y_max) / 2.0, shoulder_z1 + YOKE_Z_CLEARANCE_MM + YOKE_WALL_MM / 2.0)),
                _box(YOKE_LIP_INSET_MM, y_max - y_min, YOKE_WALL_MM, (lip_x, (y_min + y_max) / 2.0, shoulder_z0 - YOKE_Z_CLEARANCE_MM - YOKE_WALL_MM / 2.0)),
            ]
        )
    yoke = _join(parts)

    sbb = shoe.BoundingBox()
    link_y = sbb.ymax - YOKE_SHOE_LINK_LENGTH_MM / 2.0
    linked = shoe.fuse(yoke)
    for sign in (-1.0, 1.0):
        shoe_outer = sbb.xmin if sign < 0.0 else sbb.xmax
        yoke_outer = cx + sign * (side_x + YOKE_WALL_MM / 2.0)
        xa = shoe_outer - sign * YOKE_SHOE_LINK_OVERLAP_MM
        wing = _box(
            abs(yoke_outer - xa),
            YOKE_SHOE_LINK_LENGTH_MM,
            0.65,
            ((yoke_outer + xa) / 2.0, link_y, sbb.zmin + 0.325),
        )
        link_z0 = z_max - 0.10
        link_z1 = sbb.zmin + 0.30
        vertical = _box(
            YOKE_WALL_MM,
            YOKE_SHOE_LINK_LENGTH_MM,
            link_z1 - link_z0,
            (cx + sign * side_x, link_y, (link_z0 + link_z1) / 2.0),
        )
        linked = linked.fuse(wing).fuse(vertical)
    linked = linked.clean()
    if not linked.isValid() or len(linked.Solids()) != 1:
        raise TreatmentMountedFourZoneError(f"{reaction_id} yoke/shoe backbone is not one solid")
    return linked


def _centerline_nodes(
    reaction_id: str,
    front_center: tuple[float, float, float],
    rear_center: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    sign = -1.0 if "LEFT" in reaction_id else 1.0
    if "SUPERIOR" in reaction_id:
        xy = [
            front_center[:2],
            (sign * 64.0, 59.0),
            (sign * 56.0, 66.0),
            rear_center[:2],
        ]
        fractions = (0.0, 0.35, 0.65, 1.0)
    else:
        xy = [
            front_center[:2],
            (sign * 63.0, -39.0),
            (rear_center[0], -39.0),
            rear_center[:2],
        ]
        fractions = (0.0, 0.35, 0.70, 1.0)
    return [
        (float(px), float(py), front_center[2] * (1.0 - f) + rear_center[2] * f)
        for (px, py), f in zip(xy, fractions, strict=True)
    ]


def _posterior_truss(
    reaction_id: str,
    center: tuple[float, float, float],
    angle_deg: float,
    yoke_backbone: cq.Shape,
    frame_zmax: float,
    reaction_xy: tuple[float, float],
) -> tuple[cq.Shape, dict[str, object]]:
    cx, cy = reaction_xy
    side_x = SHOULDER_WIDTH_MM / 2.0 + YOKE_X_CLEARANCE_MM + YOKE_WALL_MM / 2.0
    front_y = cy + SHOULDER_HEIGHT_MM / 2.0 + YOKE_BACK_GAP_MM + YOKE_BACK_WALL_MM / 2.0
    shoulder_mid_z = frame_zmax + SHOULDER_GAP_MM + SHOULDER_THICKNESS_MM / 2.0
    front_offset = side_x + YOKE_WALL_MM / 2.0 + TRUSS_CHORD_RADIUS_MM - 0.15
    front_anchors = [
        (cx - front_offset, front_y, shoulder_mid_z),
        (cx + front_offset, front_y, shoulder_mid_z),
    ]
    rear_anchors = [
        _pose_point((-TRUSS_REAR_ANCHOR_RADIUS_MM, 0.0, TRUSS_REAR_ANCHOR_LOCAL_Z_MM), center, angle_deg),
        _pose_point((TRUSS_REAR_ANCHOR_RADIUS_MM, 0.0, TRUSS_REAR_ANCHOR_LOCAL_Z_MM), center, angle_deg),
    ]
    front_center = tuple(sum(p[i] for p in front_anchors) / 2.0 for i in range(3))
    rear_center = tuple(sum(p[i] for p in rear_anchors) / 2.0 for i in range(3))
    center_nodes = _centerline_nodes(reaction_id, front_center, rear_center)

    planar_lengths = [
        math.dist(center_nodes[i][:2], center_nodes[i + 1][:2])
        for i in range(len(center_nodes) - 1)
    ]
    cumulative = [0.0]
    for length in planar_lengths:
        cumulative.append(cumulative[-1] + length)
    fractions = [value / cumulative[-1] for value in cumulative]

    chord_paths: list[list[tuple[float, float, float]]] = []
    for front, rear in zip(front_anchors, rear_anchors, strict=True):
        front_offset_vector = np.array(front) - np.array(front_center)
        rear_offset_vector = np.array(rear) - np.array(rear_center)
        path = []
        for node, fraction in zip(center_nodes, fractions, strict=True):
            offset = (1.0 - fraction) * front_offset_vector + fraction * rear_offset_vector
            path.append(tuple(float(v) for v in np.array(node) + offset))
        chord_paths.append(path)

    material: list[cq.Shape] = []
    for path in chord_paths:
        material.extend(
            _bar(a, b, TRUSS_CHORD_RADIUS_MM)
            for a, b in zip(path[:-1], path[1:], strict=True)
        )
    for index in range(1, len(center_nodes) - 1):
        material.append(_bar(chord_paths[0][index], chord_paths[1][index], TRUSS_BRACE_RADIUS_MM))
    truss = _join(material)
    if _iv(truss, yoke_backbone) <= _INTERSECTION_TOLERANCE_MM3:
        raise TreatmentMountedFourZoneError(f"{reaction_id} truss lacks positive front capture")

    rear_span = math.dist(rear_anchors[0], rear_anchors[1])
    worst_chord_length = max(
        sum(math.dist(a, b) for a, b in zip(path[:-1], path[1:], strict=True))
        for path in chord_paths
    )
    moment_nominal = CONTINUOUS_FORCE_REFERENCE_N * math.dist(front_center, rear_center)
    moment_transient = TRANSIENT_FORCE_REFERENCE_N * math.dist(front_center, rear_center)
    area = math.pi * TRUSS_CHORD_RADIUS_MM**2
    second_moment = math.pi * TRUSS_CHORD_RADIUS_MM**4 / 4.0
    nominal_chord_force = moment_nominal / TRUSS_CONSERVATIVE_MOMENT_ARM_MM
    transient_chord_force = moment_transient / TRUSS_CONSERVATIVE_MOMENT_ARM_MM
    nominal_axial_deflection = (
        nominal_chord_force * worst_chord_length / (TRUSS_POLYMER_SCREEN_E_MPA * area)
    )
    transient_axial_deflection = (
        transient_chord_force * worst_chord_length / (TRUSS_POLYMER_SCREEN_E_MPA * area)
    )
    full_span_euler = (
        math.pi**2 * TRUSS_POLYMER_SCREEN_E_MPA * second_moment / worst_chord_length**2
    )
    return truss, {
        "front_anchor_mm": [list(p) for p in front_anchors],
        "rear_anchor_mm": [list(p) for p in rear_anchors],
        "rear_anchor_separation_mm": rear_span,
        "worst_chord_path_length_mm": worst_chord_length,
        "conservative_moment_arm_mm": TRUSS_CONSERVATIVE_MOMENT_ARM_MM,
        "continuous_moment_Nmm": moment_nominal,
        "transient_moment_Nmm": moment_transient,
        "2p5GPa_screen": {
            "nominal_chord_force_N": nominal_chord_force,
            "transient_chord_force_N": transient_chord_force,
            "nominal_axial_deflection_mm": nominal_axial_deflection,
            "transient_axial_deflection_mm": transient_axial_deflection,
            "full_span_euler_buckling_N": full_span_euler,
            "transient_buckling_ratio": full_span_euler / transient_chord_force,
        },
        "screen_status": "AXIAL_COUPLE_AND_FULL_SPAN_EULER_SCREEN_ONLY_JOINT_STIFFNESS_CREEP_DAMPING_FEA_PHYSICAL_OPEN",
    }


def _source_targets(
    reactions: StructuralFrameActuatorReactionArchitecture,
    mates: StructuralFrameActuatorMateArchitecture,
):
    interfaces = build_structural_frame_carrier_interfaces(mates=mates)
    preload = build_structural_frame_carrier_preload(interfaces=interfaces)
    landing = build_structural_frame_carrier_landing(interfaces=interfaces)
    detent = build_structural_frame_carrier_detent(interfaces=interfaces)
    targets: list[tuple[str, cq.Shape]] = [
        ("structural_frame", reactions.frame_with_reaction_counterparts.val())
    ]
    targets.extend((f"mate:{x.reaction_id}", x.mate.val()) for x in mates.mates)
    targets.extend((f"rail:{x.reaction_id}", x.interface.val()) for x in interfaces.interfaces)
    targets.extend((f"preload:{x.reaction_id}", x.preload_feature.val()) for x in preload.features)
    targets.extend((f"landing:{x.reaction_id}", x.landing_feature.val()) for x in landing.features)
    targets.extend((f"detent:{x.reaction_id}", x.detent_feature.val()) for x in detent.features)
    return interfaces, preload, landing, detent, targets


def _protected_targets(model: MasckOneModel, zmin: float, zmax: float) -> list[tuple[str, cq.Shape]]:
    targets = []
    for item in model.protected_volumes.all:
        zone = item.zone
        shape = _protected_zone_solid(
            center_x_mm=zone.center.x,
            center_y_mm=zone.center.y,
            envelope_width_mm=zone.envelope_width_mm,
            envelope_height_mm=zone.envelope_height_mm,
            angle_deg=zone.angle_deg,
            z_min_mm=zmin,
            z_max_mm=zmax,
        ).val()
        targets.append((zone.zone_id, shape))
    return targets


@dataclass(frozen=True, slots=True)
class MountedTreatmentStation:
    reaction_id: str
    treatment_center_mm: tuple[float, float, float]
    axis_angle_deg: float
    material_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    reference_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    operational_sweep: cq.Shape = field(repr=False, compare=False)
    service_sweep: cq.Shape = field(repr=False, compare=False)
    nominal_source_intersections_mm3: dict[str, float]
    nominal_protected_intersections_mm3: dict[str, float]
    nominal_shell_intersection_mm3: float
    operational_fixed_intersection_mm3: float
    operational_source_intersection_mm3: float
    operational_protected_intersection_mm3: float
    operational_shell_intersection_mm3: float
    service_source_intersection_mm3: float
    service_protected_intersection_mm3: float
    service_shell_intersection_mm3: float
    truss_screen: dict[str, object]

    def __post_init__(self) -> None:
        if self.reaction_id not in REACTION_IDS:
            raise TreatmentMountedFourZoneError("unknown station reaction id")
        if tuple(name for name, _ in self.material_parts).count("fixed_backbone") != 1:
            raise TreatmentMountedFourZoneError("station must contain one fixed backbone")
        for name, shape in self.material_parts:
            if not shape.isValid() or not shape.Solids() or shape.Volume() <= 0.0:
                raise TreatmentMountedFourZoneError(f"invalid station material {name}")
        if max(self.nominal_source_intersections_mm3.values(), default=0.0) > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentMountedFourZoneError("mounted station intersects Cell 6 source material")
        if max(self.nominal_protected_intersections_mm3.values(), default=0.0) > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentMountedFourZoneError("mounted station intersects protected anatomy")
        for value, label in (
            (self.nominal_shell_intersection_mm3, "nominal shell"),
            (self.operational_fixed_intersection_mm3, "operational fixed"),
            (self.operational_source_intersection_mm3, "operational source"),
            (self.operational_protected_intersection_mm3, "operational protected"),
            (self.operational_shell_intersection_mm3, "operational shell"),
            (self.service_source_intersection_mm3, "service source"),
            (self.service_protected_intersection_mm3, "service protected"),
            (self.service_shell_intersection_mm3, "service shell"),
        ):
            if value > _INTERSECTION_TOLERANCE_MM3:
                raise TreatmentMountedFourZoneError(f"{self.reaction_id} {label} collision: {value} mm3")

    def manifest(self) -> dict[str, object]:
        return {
            "reaction_id": self.reaction_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "treatment_center_mm": list(self.treatment_center_mm),
            "axis_angle_deg": self.axis_angle_deg,
            "axis_unit_vector": [
                math.sin(math.radians(self.axis_angle_deg)),
                0.0,
                math.cos(math.radians(self.axis_angle_deg)),
            ],
            "material_parts": [name for name, _ in self.material_parts],
            "reference_parts": [name for name, _ in self.reference_parts],
            "service_withdrawal_mm": SERVICE_WITHDRAWAL_MM,
            "operational_half_stroke_mm": OPERATIONAL_HALF_STROKE_MM,
            "measured": {
                "nominal_source_intersections_mm3": self.nominal_source_intersections_mm3,
                "nominal_protected_intersections_mm3": self.nominal_protected_intersections_mm3,
                "nominal_shell_intersection_mm3": self.nominal_shell_intersection_mm3,
                "operational_fixed_intersection_mm3": self.operational_fixed_intersection_mm3,
                "operational_source_intersection_mm3": self.operational_source_intersection_mm3,
                "operational_protected_intersection_mm3": self.operational_protected_intersection_mm3,
                "operational_shell_intersection_mm3": self.operational_shell_intersection_mm3,
                "service_source_intersection_mm3": self.service_source_intersection_mm3,
                "service_protected_intersection_mm3": self.service_protected_intersection_mm3,
                "service_shell_intersection_mm3": self.service_shell_intersection_mm3,
            },
            "reaction_architecture": "OPEN_SHOULDER_YOKE_PLUS_TWO_CHORD_POSTERIOR_TRUSS_BYPASSES_CELL6_COMPLIANT_BRIDGE_FOR_WORKING_LOAD",
            "truss_screen": self.truss_screen,
            "physical_validation": "OPEN_FORCE_STIFFNESS_CREEP_FATIGUE_DAMPING_WEAR_ACOUSTICS_INSERTION_FORCE",
        }


@dataclass(frozen=True, slots=True)
class MountedFourZoneArchitecture:
    source_counterpart_sha256: str
    source_reaction_sha256: str
    source_mate_sha256: str
    stations: tuple[MountedTreatmentStation, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if tuple(x.reaction_id for x in self.stations) != REACTION_IDS:
            raise TreatmentMountedFourZoneError("all four mounted stations must exist in controlled order")
        if self.physical_validation_eligible:
            raise TreatmentMountedFourZoneError("digital station architecture is not physical validation")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        payload = {
            "schema": SCHEMA,
            "source_main_sha": SOURCE_MAIN_SHA,
            "source_cell6_head_sha": SOURCE_CELL6_HEAD_SHA,
            "source_treatment_head_sha": SOURCE_TREATMENT_HEAD_SHA,
            "source_counterpart_sha256": self.source_counterpart_sha256,
            "source_reaction_sha256": self.source_reaction_sha256,
            "source_mate_sha256": self.source_mate_sha256,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "stations": [x.manifest() for x in self.stations],
            "mechanical_status": "FOUR_MOUNTED_STATION_CANDIDATES_WITH_RIGID_REACTION_BYPASS_OPERATIONAL_SWEEP_AND_32MM_SERVICE_SWEEP_DIGITALLY_TESTED",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_mounted_four_zone_architecture(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
    mates: StructuralFrameActuatorMateArchitecture | None = None,
    counterparts: TreatmentCarrierCounterpartArchitecture | None = None,
) -> MountedFourZoneArchitecture:
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    mates = build_structural_frame_actuator_mates(model=model, reactions=reactions) if mates is None else mates
    interfaces, preload, landing, detent, source_targets = _source_targets(reactions, mates)
    counterparts = (
        build_treatment_carrier_counterparts(
            interfaces=interfaces,
            preload=preload,
            landing=landing,
            detent=detent,
        )
        if counterparts is None
        else counterparts
    )
    counterpart_map = {x.reaction_id: x for x in counterparts.counterparts}
    frame_zmax = float(reactions.frame_with_reaction_counterparts.val().BoundingBox().zmax)
    local_material, local_reference = _local_cassette_material()

    built: list[MountedTreatmentStation] = []
    for reaction_id in REACTION_IDS:
        center = STATION_CENTERS_MM[reaction_id]
        angle = STATION_AXIS_DEG[reaction_id]
        reaction_xy = counterpart_map[reaction_id].center_xy_mm
        shoe = counterpart_map[reaction_id].shoe.val()
        yoke_backbone = _rigid_shoulder_yoke(reaction_id, shoe, frame_zmax, reaction_xy)
        truss, truss_screen = _posterior_truss(
            reaction_id, center, angle, yoke_backbone, frame_zmax, reaction_xy
        )

        posed = {name: _pose(shape, center, angle) for name, shape in local_material.items()}
        rear_capture = _iv(truss, posed["fixed_cage"])
        if rear_capture <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentMountedFourZoneError(f"{reaction_id} truss lacks positive rear cage capture")
        backbone = yoke_backbone.fuse(truss).fuse(posed.pop("fixed_cage")).clean()
        if not backbone.isValid() or len(backbone.Solids()) != 1:
            raise TreatmentMountedFourZoneError(f"{reaction_id} fixed backbone is not one solid")

        kind = "superior" if "SUPERIOR" in reaction_id else "inferior"
        moving_output = _moving_output_linkage(kind, center, angle)
        material = {"fixed_backbone": backbone, **posed, "moving_output_linkage": moving_output}
        references = {
            name: _pose(shape, center, angle) for name, shape in local_reference.items()
        }

        z_values = [
            value
            for shape in material.values()
            for value in (shape.BoundingBox().zmin, shape.BoundingBox().zmax)
        ]
        protected_targets = _protected_targets(model, min(z_values) - 1.0, max(z_values) + 1.0)
        material_compound = cq.Compound.makeCompound(list(material.values()))

        nominal_source = {
            name: round(_iv(material_compound, target), 8)
            for name, target in source_targets
        }
        nominal_protected = {
            name: round(_iv(material_compound, target), 8)
            for name, target in protected_targets
        }
        nominal_shell = round(_iv(material_compound, model.shell.solid.val()), 8)

        axis = np.array(
            [math.sin(math.radians(angle)), 0.0, math.cos(math.radians(angle))]
        )
        moving_names = (
            "moving_cup",
            "moving_rear_clamp",
            "moving_front_clamp",
            "moving_output_linkage",
        )
        moving = cq.Compound.makeCompound([material[name] for name in moving_names])
        operational_start = moving.translate(tuple(float(-OPERATIONAL_HALF_STROKE_MM * v) for v in axis))
        operational = _translation_envelope(
            operational_start,
            tuple(float(2.0 * OPERATIONAL_HALF_STROKE_MM * v) for v in axis),
        )
        fixed_collision_names = (
            "fixed_backbone",
            "front_stop_ring",
            "front_buffer_inner",
            "front_buffer_outer",
            "rear_buffer",
        )
        fixed_targets = cq.Compound.makeCompound(
            [material[name] for name in fixed_collision_names]
        )
        operational_fixed = round(_iv(operational, fixed_targets), 8)
        operational_source = round(
            sum(_iv(operational, target) for _name, target in source_targets), 8
        )
        operational_protected = round(
            sum(_iv(operational, target) for _name, target in protected_targets), 8
        )
        operational_shell = round(_iv(operational, model.shell.solid.val()), 8)

        service_envelopes = [
            _translation_envelope(shape, (0.0, SERVICE_WITHDRAWAL_MM, 0.0))
            for shape in material.values()
        ]
        service = cq.Compound.makeCompound(service_envelopes)
        service_source = round(
            sum(_iv(service, target) for _name, target in source_targets), 8
        )
        service_protected = round(
            sum(_iv(service, target) for _name, target in protected_targets), 8
        )
        service_shell = round(_iv(service, model.shell.solid.val()), 8)

        built.append(
            MountedTreatmentStation(
                reaction_id,
                center,
                angle,
                tuple(material.items()),
                tuple(references.items()),
                operational,
                service,
                nominal_source,
                nominal_protected,
                nominal_shell,
                operational_fixed,
                operational_source,
                operational_protected,
                operational_shell,
                service_source,
                service_protected,
                service_shell,
                truss_screen,
            )
        )

    result = MountedFourZoneArchitecture(
        counterparts.architecture_sha256,
        reactions.architecture_sha256,
        mates.architecture_sha256,
        tuple(built),
        False,
    )
    result.__post_init__()
    return result


def export_mounted_four_zone_architecture(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_mounted_four_zone_architecture()
    for station in architecture.stations:
        slug = station.reaction_id.lower()
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.material_parts]),
            str(output_dir / f"{slug}_mounted_station_material.step"),
        )
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.reference_parts]),
            str(output_dir / f"{slug}_mounted_station_reference.step"),
        )
        cq.exporters.export(station.operational_sweep, str(output_dir / f"{slug}_operational_sweep.step"))
        cq.exporters.export(station.service_sweep, str(output_dir / f"{slug}_service_sweep.step"))
    manifest = architecture.manifest()
    (output_dir / "treatment_mounted_four_zone_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
