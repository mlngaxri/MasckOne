from __future__ import annotations

"""Revised mounted four-zone reaction path for the Masck One treatment platform.

This successor keeps the Step-2 carrier/yoke/cassette architecture but replaces the
first posterior-truss route after a conservative frame-slab screen found that the
full-radius chord could graze the frame near its front anchor. The revised path uses
small front necks to rise anterior of the frame, routes the main two-chord truss above
the frame axial slab, then descends to rear-cage anchors only after reaching the
central opening. Digital architecture only; no physical stiffness/fatigue/comfort or
human-use claims.
"""

from dataclasses import replace
import json
import math
from pathlib import Path

import cadquery as cq
import numpy as np

from .structural_frame_actuator_mates import (
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
from .treatment_carrier_counterpart import (
    TreatmentCarrierCounterpartArchitecture,
    build_treatment_carrier_counterparts,
)
from .treatment_mounted_four_zone import (
    CONTINUOUS_FORCE_REFERENCE_N,
    OPERATIONAL_HALF_STROKE_MM,
    SERVICE_WITHDRAWAL_MM,
    SOURCE_CELL6_HEAD_SHA,
    SOURCE_MAIN_SHA,
    SOURCE_TREATMENT_HEAD_SHA,
    STATION_AXIS_DEG,
    STATION_CENTERS_MM,
    TRANSIENT_FORCE_REFERENCE_N,
    TRUSS_BRACE_RADIUS_MM,
    TRUSS_CHORD_RADIUS_MM,
    TRUSS_CONSERVATIVE_MOMENT_ARM_MM,
    TRUSS_POLYMER_SCREEN_E_MPA,
    MountedFourZoneArchitecture,
    MountedTreatmentStation,
    TreatmentMountedFourZoneError,
    YOKE_BACK_GAP_MM,
    YOKE_BACK_WALL_MM,
    YOKE_WALL_MM,
    YOKE_X_CLEARANCE_MM,
    _bar,
    _box,
    _iv,
    _join,
    _local_cassette_material,
    _moving_output_linkage,
    _pose,
    _pose_point,
    _protected_targets,
    _rigid_shoulder_yoke,
    _source_targets,
    _translation_envelope,
)
from .model import MasckOneModel, build_model

SCHEMA_V2 = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V2"

# Keep the high-frequency chord completely anterior of the Cell 6 frame slab until
# it has reached the inner/open region. With current frame zmax=-3.0 mm, this puts the
# 1.10 mm-radius chord centerline at -1.40 mm, retaining a 0.50 mm axial guard to the
# frame even at the chord's posterior tangent. This is a digital clearance seed, not
# production tolerance capability.
TRUSS_FRAME_GUARD_MM = 0.50
TRUSS_FRONT_NECK_RADIUS_MM = 0.35
TRUSS_REAR_ANCHOR_X_MM = 2.00
TRUSS_REAR_ANCHOR_Y_MM = 1.50
TRUSS_REAR_ANCHOR_LOCAL_Z_MM = -8.90

# Collision-informed centerline waypoints. The last planar gate is intentionally at
# the actual rear-anchor XY while still on the anterior routing plane; the final
# descent then occurs through the central frame opening rather than through the frame
# reaction band.
SUPERIOR_ROUTE_XY_ABS_MM = ((64.0, 59.0), (52.0, 66.0))
INFERIOR_ROUTE_XY_ABS_MM = ((62.0, -39.0), (50.0, -38.0))


def _rear_anchor_local_points(kind: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    # Put rear anchors on the side opposite the moving output arm: superior arm moves
    # toward +Y, inferior toward -Y. Both anchors remain exactly on the r=2.5 mm rear
    # fixed-cage ring used by the previous treatment strike.
    rear_y = -TRUSS_REAR_ANCHOR_Y_MM if kind == "superior" else TRUSS_REAR_ANCHOR_Y_MM
    return (
        (-TRUSS_REAR_ANCHOR_X_MM, rear_y, TRUSS_REAR_ANCHOR_LOCAL_Z_MM),
        (TRUSS_REAR_ANCHOR_X_MM, rear_y, TRUSS_REAR_ANCHOR_LOCAL_Z_MM),
    )


def _routing_centers(
    reaction_id: str,
    front_center: np.ndarray,
    rear_center: np.ndarray,
    routing_z: float,
) -> list[np.ndarray]:
    sign = -1.0 if "LEFT" in reaction_id else 1.0
    route = SUPERIOR_ROUTE_XY_ABS_MM if "SUPERIOR" in reaction_id else INFERIOR_ROUTE_XY_ABS_MM
    centers = [front_center.copy()]
    centers.extend(np.array((sign * abs(x), y, routing_z), dtype=float) for x, y in route)
    centers.append(np.array((rear_center[0], rear_center[1], routing_z), dtype=float))
    centers.append(rear_center.copy())
    centers[0][2] = routing_z
    return centers


def _posterior_truss_v2(
    reaction_id: str,
    center: tuple[float, float, float],
    angle_deg: float,
    yoke_backbone: cq.Shape,
    frame_zmax: float,
    reaction_xy: tuple[float, float],
) -> tuple[cq.Shape, dict[str, object]]:
    cx, cy = reaction_xy
    kind = "superior" if "SUPERIOR" in reaction_id else "inferior"
    side_x = SHOULDER_WIDTH_MM / 2.0 + YOKE_X_CLEARANCE_MM + YOKE_WALL_MM / 2.0
    front_y = cy + SHOULDER_HEIGHT_MM / 2.0 + YOKE_BACK_GAP_MM + YOKE_BACK_WALL_MM / 2.0
    shoulder_mid_z = frame_zmax + SHOULDER_GAP_MM + SHOULDER_THICKNESS_MM / 2.0
    front_offset = side_x + YOKE_WALL_MM / 2.0 + TRUSS_CHORD_RADIUS_MM - 0.15
    yoke_anchor_points = [
        np.array((cx - front_offset, front_y, shoulder_mid_z), dtype=float),
        np.array((cx + front_offset, front_y, shoulder_mid_z), dtype=float),
    ]

    routing_z = frame_zmax + TRUSS_CHORD_RADIUS_MM + TRUSS_FRAME_GUARD_MM
    front_chord_points = [
        np.array((point[0], point[1], routing_z), dtype=float) for point in yoke_anchor_points
    ]
    rear_anchors = [
        np.array(_pose_point(point, center, angle_deg), dtype=float)
        for point in _rear_anchor_local_points(kind)
    ]
    front_center = (front_chord_points[0] + front_chord_points[1]) / 2.0
    rear_center = (rear_anchors[0] + rear_anchors[1]) / 2.0
    centers = _routing_centers(reaction_id, front_center, rear_center, routing_z)

    planar_lengths = [
        math.dist(centers[index][:2], centers[index + 1][:2])
        for index in range(len(centers) - 2)
    ]
    cumulative = [0.0]
    for length in planar_lengths:
        cumulative.append(cumulative[-1] + length)
    planar_total = cumulative[-1] if cumulative[-1] > 0.0 else 1.0
    fractions = [value / planar_total for value in cumulative]

    chord_paths: list[list[tuple[float, float, float]]] = []
    for front, rear in zip(front_chord_points, rear_anchors, strict=True):
        front_offset_vector = front - front_center
        rear_offset_vector = rear - rear_center
        path: list[tuple[float, float, float]] = []
        for index, node in enumerate(centers):
            if index == len(centers) - 1:
                point = rear
            else:
                fraction = fractions[min(index, len(fractions) - 1)]
                offset = (1.0 - fraction) * front_offset_vector + fraction * rear_offset_vector
                point = node + offset
                point[2] = routing_z
            path.append(tuple(float(value) for value in point))
        chord_paths.append(path)

    material: list[cq.Shape] = []
    # Small necks make positive capture into the yoke without allowing the 1.10 mm
    # main chord radius to dip into the frame slab at the front anchor.
    for yoke_anchor, chord_front in zip(yoke_anchor_points, front_chord_points, strict=True):
        material.append(
            _bar(
                tuple(float(v) for v in yoke_anchor),
                tuple(float(v) for v in chord_front),
                TRUSS_FRONT_NECK_RADIUS_MM,
            )
        )
    for path in chord_paths:
        material.extend(
            _bar(a, b, TRUSS_CHORD_RADIUS_MM)
            for a, b in zip(path[:-1], path[1:], strict=True)
        )
    for index in range(1, len(chord_paths[0]) - 1):
        material.append(_bar(chord_paths[0][index], chord_paths[1][index], TRUSS_BRACE_RADIUS_MM))

    truss = _join(material)
    front_capture = _iv(truss, yoke_backbone)
    if front_capture <= 1e-7:
        raise TreatmentMountedFourZoneError(f"{reaction_id} revised truss lacks positive yoke capture")

    worst_chord_length = max(
        sum(math.dist(a, b) for a, b in zip(path[:-1], path[1:], strict=True))
        for path in chord_paths
    )
    rear_span = math.dist(rear_anchors[0], rear_anchors[1])
    load_span = math.dist(front_center, rear_center)
    moment_nominal = CONTINUOUS_FORCE_REFERENCE_N * load_span
    moment_transient = TRANSIENT_FORCE_REFERENCE_N * load_span
    area = math.pi * TRUSS_CHORD_RADIUS_MM**2
    second_moment = math.pi * TRUSS_CHORD_RADIUS_MM**4 / 4.0
    nominal_chord_force = moment_nominal / TRUSS_CONSERVATIVE_MOMENT_ARM_MM
    transient_chord_force = moment_transient / TRUSS_CONSERVATIVE_MOMENT_ARM_MM
    nominal_axial_deflection = nominal_chord_force * worst_chord_length / (TRUSS_POLYMER_SCREEN_E_MPA * area)
    transient_axial_deflection = transient_chord_force * worst_chord_length / (TRUSS_POLYMER_SCREEN_E_MPA * area)
    full_span_euler = math.pi**2 * TRUSS_POLYMER_SCREEN_E_MPA * second_moment / worst_chord_length**2

    return truss, {
        "revision": "V2_FRAME_SLAB_BYPASS",
        "routing_plane_z_mm": routing_z,
        "frame_zmax_mm": frame_zmax,
        "frame_guard_at_chord_tangent_mm": routing_z - TRUSS_CHORD_RADIUS_MM - frame_zmax,
        "front_neck_radius_mm": TRUSS_FRONT_NECK_RADIUS_MM,
        "front_yoke_anchor_mm": [point.tolist() for point in yoke_anchor_points],
        "front_chord_anchor_mm": [point.tolist() for point in front_chord_points],
        "rear_anchor_mm": [point.tolist() for point in rear_anchors],
        "rear_anchor_separation_mm": rear_span,
        "worst_chord_path_length_mm": worst_chord_length,
        "conservative_moment_arm_mm": TRUSS_CONSERVATIVE_MOMENT_ARM_MM,
        "continuous_moment_Nmm": moment_nominal,
        "transient_moment_Nmm": moment_transient,
        "positive_yoke_capture_mm3": front_capture,
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


def build_mounted_four_zone_architecture_v2(
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
    counterpart_map = {item.reaction_id: item for item in counterparts.counterparts}
    frame_zmax = float(reactions.frame_with_reaction_counterparts.val().BoundingBox().zmax)
    local_material, local_reference = _local_cassette_material()

    built: list[MountedTreatmentStation] = []
    for reaction_id in REACTION_IDS:
        center = STATION_CENTERS_MM[reaction_id]
        angle = STATION_AXIS_DEG[reaction_id]
        reaction_xy = counterpart_map[reaction_id].center_xy_mm
        shoe = counterpart_map[reaction_id].shoe.val()
        yoke_backbone = _rigid_shoulder_yoke(reaction_id, shoe, frame_zmax, reaction_xy)
        truss, truss_screen = _posterior_truss_v2(
            reaction_id, center, angle, yoke_backbone, frame_zmax, reaction_xy
        )

        posed = {name: _pose(shape, center, angle) for name, shape in local_material.items()}
        rear_capture = _iv(truss, posed["fixed_cage"])
        if rear_capture <= 1e-7:
            raise TreatmentMountedFourZoneError(f"{reaction_id} revised truss lacks positive rear-cage capture")
        truss_screen["positive_rear_cage_capture_mm3"] = rear_capture
        backbone = yoke_backbone.fuse(truss).fuse(posed.pop("fixed_cage")).clean()
        if not backbone.isValid() or len(backbone.Solids()) != 1:
            raise TreatmentMountedFourZoneError(f"{reaction_id} revised fixed backbone is not one solid")

        kind = "superior" if "SUPERIOR" in reaction_id else "inferior"
        moving_output = _moving_output_linkage(kind, center, angle)
        material = {"fixed_backbone": backbone, **posed, "moving_output_linkage": moving_output}
        references = {name: _pose(shape, center, angle) for name, shape in local_reference.items()}

        z_values = [
            value
            for shape in material.values()
            for value in (shape.BoundingBox().zmin, shape.BoundingBox().zmax)
        ]
        protected_targets = _protected_targets(model, min(z_values) - 1.0, max(z_values) + 1.0)
        material_compound = cq.Compound.makeCompound(list(material.values()))
        nominal_source = {name: round(_iv(material_compound, target), 8) for name, target in source_targets}
        nominal_protected = {name: round(_iv(material_compound, target), 8) for name, target in protected_targets}
        nominal_shell = round(_iv(material_compound, model.shell.solid.val()), 8)

        axis = np.array([math.sin(math.radians(angle)), 0.0, math.cos(math.radians(angle))])
        moving_names = ("moving_cup", "moving_rear_clamp", "moving_front_clamp", "moving_output_linkage")
        travel = tuple(float(2.0 * OPERATIONAL_HALF_STROKE_MM * value) for value in axis)
        operational_envelopes = []
        for name in moving_names:
            start = material[name].translate(tuple(float(-OPERATIONAL_HALF_STROKE_MM * value) for value in axis))
            operational_envelopes.append(_translation_envelope(start, travel))
        operational = cq.Compound.makeCompound(operational_envelopes)
        fixed_targets = cq.Compound.makeCompound(
            [
                material["fixed_backbone"],
                material["front_stop_ring"],
                material["front_buffer_inner"],
                material["front_buffer_outer"],
                material["rear_buffer"],
            ]
        )
        operational_fixed = round(_iv(operational, fixed_targets), 8)
        operational_source = round(sum(_iv(operational, target) for _name, target in source_targets), 8)
        operational_protected = round(sum(_iv(operational, target) for _name, target in protected_targets), 8)
        operational_shell = round(_iv(operational, model.shell.solid.val()), 8)

        service = cq.Compound.makeCompound(
            [_translation_envelope(shape, (0.0, SERVICE_WITHDRAWAL_MM, 0.0)) for shape in material.values()]
        )
        service_source = round(sum(_iv(service, target) for _name, target in source_targets), 8)
        service_protected = round(sum(_iv(service, target) for _name, target in protected_targets), 8)
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

    architecture = MountedFourZoneArchitecture(
        counterparts.architecture_sha256,
        reactions.architecture_sha256,
        mates.architecture_sha256,
        tuple(built),
        False,
    )
    architecture.__post_init__()
    return architecture


def manifest_v2(architecture: MountedFourZoneArchitecture) -> dict[str, object]:
    payload = architecture.manifest()
    payload["schema"] = SCHEMA_V2
    payload["source_main_sha"] = SOURCE_MAIN_SHA
    payload["source_cell6_head_sha"] = SOURCE_CELL6_HEAD_SHA
    payload["source_treatment_head_sha"] = SOURCE_TREATMENT_HEAD_SHA
    payload["mechanical_status"] = (
        "FOUR_MOUNTED_STATION_V2_CANDIDATES_WITH_RIGID_SHOULDER_BYPASS_"
        "ANTERIOR_FRAME_TRUSS_ROUTING_OPERATIONAL_SWEEP_AND_32MM_SERVICE_SWEEP_DIGITALLY_TESTED"
    )
    payload["supersedes"] = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V1_TRUSS_ROUTE"
    return payload


def export_mounted_four_zone_architecture_v2(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_mounted_four_zone_architecture_v2()
    for station in architecture.stations:
        slug = station.reaction_id.lower()
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.material_parts]),
            str(output_dir / f"{slug}_mounted_station_v2_material.step"),
        )
        cq.exporters.export(station.operational_sweep, str(output_dir / f"{slug}_operational_v2_sweep.step"))
        cq.exporters.export(station.service_sweep, str(output_dir / f"{slug}_service_v2_sweep.step"))
    manifest = manifest_v2(architecture)
    (output_dir / "treatment_mounted_four_zone_v2_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
