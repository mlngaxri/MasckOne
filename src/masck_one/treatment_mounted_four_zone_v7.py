from __future__ import annotations

"""Mounted four-zone V7: encapsulated, phased C2 preload spring inserts.

V6 proved the value of independent parallel-leaf spring cassettes but still modeled a
0.01 mm root-cage clearance. That is not a strong production-intent way to obtain a
quiet precision mount from molded parts. V7 removes that dependency by treating the
preload spring as an insert-molded / encapsulated second material:

- the spring has a wide dog-bone root bridge and wide tip bridge;
- carrier polymer surrounds the root bridge after subtracting the exact spring volume;
- preload-shoe polymer surrounds the tip bridge after subtracting the spring volume;
- the two free leaf spans pass through explicit relief and never overlap carrier
  polymer at nominal geometry;
- root/tip capture is therefore geometric even though there is no tiny running fit;
- spring X/Z geometry is independently tuned to the robust 0.40 N C2 candidate;
- X terminal take-up is phased ahead of Z to reduce coincident cam-force peaking;
- rigid master datums, not spring leaves, carry normal 40 Hz reaction;
- lossy backup then rigid overload stop remain abnormal-load functions.

The CAD represents a candidate material partition, not proof that insert molding is
the selected process. Alloy, forming, polymer/metal adhesion, mechanical interlock,
fatigue, corrosion, wet chemistry, friction, damping and acoustics remain open.
"""

import json
import math
from pathlib import Path

import cadquery as cq

from studies.treatment_buttery_terminal_profile_v2 import (
    ENTRY_OVERCLOSURE_MM,
    LEAF_PAIR_GAP_MM,
    LEAF_THICKNESS_MM,
    LEAF_WIDTH_MM,
    PRELOAD_TARGET_N,
    axis_design,
)

from .model import MasckOneModel, build_model
from .structural_frame_actuator_mates import (
    StructuralFrameActuatorMateArchitecture,
    build_structural_frame_actuator_mates,
)
from .structural_frame_actuator_reactions import (
    StructuralFrameActuatorReactionArchitecture,
    build_structural_frame_actuator_reactions,
)
from .treatment_carrier_counterpart import TreatmentCarrierCounterpartArchitecture
from .treatment_mounted_four_zone import (
    SERVICE_WITHDRAWAL_MM,
    MountedFourZoneArchitecture,
    MountedTreatmentStation,
    TreatmentMountedFourZoneError,
    _iv,
    _protected_targets,
    _source_targets,
    _translation_envelope,
)
from .treatment_mounted_four_zone_v2 import build_mounted_four_zone_architecture_v2
from .treatment_terminal_datum_preload_v2 import (
    SOURCE_CELL6_HEAD_SHA,
    TerminalDatumPreloadV2Architecture,
    build_terminal_datum_preload_v2_architecture,
)

SCHEMA_V7 = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V7"
SOURCE_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
SOURCE_PROFILE_PARENT_SHA = "11635aadb79f7be1ced5c747f7f6a98769366ec6"
SOURCE_DATUM_V2_PARENT_SHA = "987851e712d7e576d245a1cbecb9897a3650936f"

ROOT_HEAD_TRANSVERSE_MM = 2.20
ROOT_HEAD_LENGTH_Y_MM = 0.78
TIP_HEAD_TRANSVERSE_MM = 2.00
TIP_HEAD_LENGTH_Y_MM = 0.48
HEAD_SHEET_DEPTH_MM = LEAF_THICKNESS_MM
ROOT_TO_LEAF_OVERLAP_MM = 0.08
LEAF_TO_TIP_OVERLAP_MM = 0.10

ROOT_OVERMOLD_TRANSVERSE_MM = 2.80
ROOT_OVERMOLD_LENGTH_Y_MM = 1.25
ROOT_OVERMOLD_DEPTH_MM = 0.95
ROOT_OVERMOLD_SIDE_COVER_MM = (ROOT_OVERMOLD_TRANSVERSE_MM - ROOT_HEAD_TRANSVERSE_MM) / 2.0
ROOT_PULL_OUT_PROBE_MM = 0.22

TIP_POLYMER_COVER_MM = 0.06
TIP_PULL_OUT_PROBE_MM = 0.16
FREE_SPAN_RELIEF_MARGIN_MM = 0.08
FREE_SPAN_RELIEF_DEPTH_MM = 0.72
SUPPORT_RIB_THICKNESS_MM = 0.32
SUPPORT_RIB_TRANSVERSE_MM = 0.34

_INTERSECTION_TOLERANCE_MM3 = 1e-7


class TreatmentMountedFourZoneV7Error(TreatmentMountedFourZoneError):
    pass


def _box(x: float, y: float, z: float, center: tuple[float, float, float]) -> cq.Shape:
    if min(x, y, z) <= 0.0:
        raise TreatmentMountedFourZoneV7Error("V7 box dimensions must be positive")
    return cq.Workplane("XY").box(x, y, z).translate(center).val()


def _join(shapes: list[cq.Shape]) -> cq.Shape:
    if not shapes:
        raise TreatmentMountedFourZoneV7Error("cannot join empty V7 shape list")
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    result = result.clean()
    if not result.isValid() or not result.Solids():
        raise TreatmentMountedFourZoneV7Error("V7 joined geometry must remain valid")
    return result


def _leaf_x(
    *,
    root_x: float,
    tip_x: float,
    root_y: float,
    tip_y: float,
    z_center: float,
) -> cq.Shape:
    dx = tip_x - root_x
    dy = tip_y - root_y
    length = math.hypot(dx, dy)
    angle = -math.degrees(math.atan2(dx, dy))
    shape = cq.Workplane("XY").box(LEAF_THICKNESS_MM, length, LEAF_WIDTH_MM).val()
    shape = shape.rotate((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), angle)
    return shape.translate(((root_x + tip_x) / 2.0, (root_y + tip_y) / 2.0, z_center))


def _leaf_z(
    *,
    root_z: float,
    tip_z: float,
    root_y: float,
    tip_y: float,
    x_center: float,
) -> cq.Shape:
    dz = tip_z - root_z
    dy = tip_y - root_y
    length = math.hypot(dz, dy)
    angle = math.degrees(math.atan2(dz, dy))
    shape = cq.Workplane("XY").box(LEAF_WIDTH_MM, length, LEAF_THICKNESS_MM).val()
    shape = shape.rotate((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), angle)
    return shape.translate((x_center, (root_y + tip_y) / 2.0, (root_z + tip_z) / 2.0))


def _pair_offset() -> float:
    return LEAF_PAIR_GAP_MM / 2.0 + LEAF_WIDTH_MM / 2.0


def _support_to_backbone_x(
    *,
    root_x: float,
    root_y: float,
    root_z: float,
    tip_y: float,
) -> cq.Shape:
    # Two narrow polymer side ribs connect the root overmold forward while remaining
    # outside the 1.80 mm spring-pair envelope. They are later fused into the existing
    # treatment backbone and relieved around the free leaf span.
    dz = ROOT_OVERMOLD_TRANSVERSE_MM / 2.0 - SUPPORT_RIB_TRANSVERSE_MM / 2.0
    length_y = max(ROOT_OVERMOLD_LENGTH_Y_MM, tip_y - root_y)
    center_y = root_y + length_y / 2.0
    ribs = [
        _box(
            SUPPORT_RIB_THICKNESS_MM,
            length_y,
            SUPPORT_RIB_TRANSVERSE_MM,
            (root_x, center_y, root_z - dz),
        ),
        _box(
            SUPPORT_RIB_THICKNESS_MM,
            length_y,
            SUPPORT_RIB_TRANSVERSE_MM,
            (root_x, center_y, root_z + dz),
        ),
    ]
    return _join(ribs)


def _support_to_backbone_z(
    *,
    root_x: float,
    root_y: float,
    root_z: float,
    tip_y: float,
) -> cq.Shape:
    dx = ROOT_OVERMOLD_TRANSVERSE_MM / 2.0 - SUPPORT_RIB_TRANSVERSE_MM / 2.0
    length_y = max(ROOT_OVERMOLD_LENGTH_Y_MM, tip_y - root_y)
    center_y = root_y + length_y / 2.0
    ribs = [
        _box(
            SUPPORT_RIB_TRANSVERSE_MM,
            length_y,
            SUPPORT_RIB_THICKNESS_MM,
            (root_x - dx, center_y, root_z),
        ),
        _box(
            SUPPORT_RIB_TRANSVERSE_MM,
            length_y,
            SUPPORT_RIB_THICKNESS_MM,
            (root_x + dx, center_y, root_z),
        ),
    ]
    return _join(ribs)


def _x_insert_and_overmold(datum_station) -> dict[str, cq.Shape | dict[str, float]]:
    shoe_outer = dict(datum_station.preload_outer_parts)["preload_x_outer_v2"]
    bb = shoe_outer.BoundingBox()
    axis = axis_design("X")
    cx, _cy = datum_station.center_xy_mm
    sign = 1.0 if cx > 0.0 else -1.0

    tip_x = (bb.xmax - TIP_POLYMER_COVER_MM) if sign > 0.0 else (bb.xmin + TIP_POLYMER_COVER_MM)
    root_x = tip_x - sign * axis.target_deflection_mm
    tip_y = bb.ymin + TIP_HEAD_LENGTH_Y_MM / 2.0 + 0.06
    root_y = tip_y - axis.effective_leaf_length_mm
    z_mid = 0.5 * (bb.zmin + bb.zmax)
    offset = _pair_offset()

    root_head = _box(
        HEAD_SHEET_DEPTH_MM,
        ROOT_HEAD_LENGTH_Y_MM,
        ROOT_HEAD_TRANSVERSE_MM,
        (root_x, root_y - ROOT_HEAD_LENGTH_Y_MM / 2.0 + ROOT_TO_LEAF_OVERLAP_MM, z_mid),
    )
    tip_head = _box(
        HEAD_SHEET_DEPTH_MM,
        TIP_HEAD_LENGTH_Y_MM,
        TIP_HEAD_TRANSVERSE_MM,
        (tip_x, tip_y, z_mid),
    )
    leaves = [
        _leaf_x(root_x=root_x, tip_x=tip_x, root_y=root_y, tip_y=tip_y, z_center=z_mid - offset),
        _leaf_x(root_x=root_x, tip_x=tip_x, root_y=root_y, tip_y=tip_y, z_center=z_mid + offset),
    ]
    spring = _join([root_head, *leaves, tip_head])

    root_center_y = root_y - ROOT_HEAD_LENGTH_Y_MM / 2.0 + ROOT_TO_LEAF_OVERLAP_MM
    root_overmold_raw = _box(
        ROOT_OVERMOLD_DEPTH_MM,
        ROOT_OVERMOLD_LENGTH_Y_MM,
        ROOT_OVERMOLD_TRANSVERSE_MM,
        (root_x, root_center_y, z_mid),
    )
    root_overmold = root_overmold_raw.cut(root_head).clean()
    if not root_overmold.isValid() or not root_overmold.Solids():
        raise TreatmentMountedFourZoneV7Error("X root overmold invalid after metal subtraction")

    support = _support_to_backbone_x(root_x=root_x, root_y=root_center_y, root_z=z_mid, tip_y=bb.ymin)
    leaf_envelope = _box(
        FREE_SPAN_RELIEF_DEPTH_MM,
        max(0.1, bb.ymin - (root_center_y + ROOT_HEAD_LENGTH_Y_MM / 2.0)),
        2.0 * offset + LEAF_WIDTH_MM + 2.0 * FREE_SPAN_RELIEF_MARGIN_MM,
        (
            root_x,
            0.5 * (bb.ymin + root_center_y + ROOT_HEAD_LENGTH_Y_MM / 2.0),
            z_mid,
        ),
    )
    support = support.cut(leaf_envelope).clean()

    shoe_polymer = shoe_outer.cut(spring).clean()
    if not shoe_polymer.isValid() or not shoe_polymer.Solids():
        raise TreatmentMountedFourZoneV7Error("X preload shoe invalid after spring-tip subtraction")

    return {
        "spring": spring,
        "root_head": root_head,
        "tip_head": tip_head,
        "root_overmold": root_overmold,
        "support": support,
        "shoe_polymer": shoe_polymer,
        "screen": axis.manifest(),
    }


def _z_insert_and_overmold(datum_station) -> dict[str, cq.Shape | dict[str, float]]:
    shoe_outer = dict(datum_station.preload_outer_parts)["preload_z_outer_v2"]
    bb = shoe_outer.BoundingBox()
    axis = axis_design("Z")

    tip_z = bb.zmax - TIP_POLYMER_COVER_MM
    root_z = tip_z - axis.target_deflection_mm
    tip_y = bb.ymin + TIP_HEAD_LENGTH_Y_MM / 2.0 + 0.06
    root_y = tip_y - axis.effective_leaf_length_mm
    x_mid = 0.5 * (bb.xmin + bb.xmax)
    offset = _pair_offset()

    root_head = _box(
        ROOT_HEAD_TRANSVERSE_MM,
        ROOT_HEAD_LENGTH_Y_MM,
        HEAD_SHEET_DEPTH_MM,
        (x_mid, root_y - ROOT_HEAD_LENGTH_Y_MM / 2.0 + ROOT_TO_LEAF_OVERLAP_MM, root_z),
    )
    tip_head = _box(
        TIP_HEAD_TRANSVERSE_MM,
        TIP_HEAD_LENGTH_Y_MM,
        HEAD_SHEET_DEPTH_MM,
        (x_mid, tip_y, tip_z),
    )
    leaves = [
        _leaf_z(root_z=root_z, tip_z=tip_z, root_y=root_y, tip_y=tip_y, x_center=x_mid - offset),
        _leaf_z(root_z=root_z, tip_z=tip_z, root_y=root_y, tip_y=tip_y, x_center=x_mid + offset),
    ]
    spring = _join([root_head, *leaves, tip_head])

    root_center_y = root_y - ROOT_HEAD_LENGTH_Y_MM / 2.0 + ROOT_TO_LEAF_OVERLAP_MM
    root_overmold_raw = _box(
        ROOT_OVERMOLD_TRANSVERSE_MM,
        ROOT_OVERMOLD_LENGTH_Y_MM,
        ROOT_OVERMOLD_DEPTH_MM,
        (x_mid, root_center_y, root_z),
    )
    root_overmold = root_overmold_raw.cut(root_head).clean()
    if not root_overmold.isValid() or not root_overmold.Solids():
        raise TreatmentMountedFourZoneV7Error("Z root overmold invalid after metal subtraction")

    support = _support_to_backbone_z(root_x=x_mid, root_y=root_center_y, root_z=root_z, tip_y=bb.ymin)
    leaf_envelope = _box(
        2.0 * offset + LEAF_WIDTH_MM + 2.0 * FREE_SPAN_RELIEF_MARGIN_MM,
        max(0.1, bb.ymin - (root_center_y + ROOT_HEAD_LENGTH_Y_MM / 2.0)),
        FREE_SPAN_RELIEF_DEPTH_MM,
        (
            x_mid,
            0.5 * (bb.ymin + root_center_y + ROOT_HEAD_LENGTH_Y_MM / 2.0),
            root_z,
        ),
    )
    support = support.cut(leaf_envelope).clean()

    shoe_polymer = shoe_outer.cut(spring).clean()
    if not shoe_polymer.isValid() or not shoe_polymer.Solids():
        raise TreatmentMountedFourZoneV7Error("Z preload shoe invalid after spring-tip subtraction")

    return {
        "spring": spring,
        "root_head": root_head,
        "tip_head": tip_head,
        "root_overmold": root_overmold,
        "support": support,
        "shoe_polymer": shoe_polymer,
        "screen": axis.manifest(),
    }


def build_mounted_four_zone_architecture_v7(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
    mates: StructuralFrameActuatorMateArchitecture | None = None,
    counterparts: TreatmentCarrierCounterpartArchitecture | None = None,
    terminal_datums: TerminalDatumPreloadV2Architecture | None = None,
) -> tuple[MountedFourZoneArchitecture, TerminalDatumPreloadV2Architecture]:
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    mates = build_structural_frame_actuator_mates(model=model, reactions=reactions) if mates is None else mates
    base = build_mounted_four_zone_architecture_v2(
        model=model,
        reactions=reactions,
        mates=mates,
        counterparts=counterparts,
    )
    terminal_datums = (
        build_terminal_datum_preload_v2_architecture(model=model, reactions=reactions, mates=mates)
        if terminal_datums is None
        else terminal_datums
    )
    datum_map = {item.reaction_id: item for item in terminal_datums.stations}
    _interfaces, _preload, _landing, _detent, source_targets = _source_targets(reactions, mates)

    built: list[MountedTreatmentStation] = []
    for station in base.stations:
        datum = datum_map[station.reaction_id]
        material = dict(station.material_parts)
        reference = dict(station.reference_parts)
        backbone = material["fixed_backbone"]

        for _name, shape in datum.master_parts + datum.rigid_backup_parts:
            backbone = backbone.fuse(shape)

        x = _x_insert_and_overmold(datum)
        z = _z_insert_and_overmold(datum)
        for axis_result in (x, z):
            backbone = backbone.fuse(axis_result["root_overmold"]).fuse(axis_result["support"])
        backbone = backbone.clean()
        if not backbone.isValid() or len(backbone.Solids()) != 1:
            raise TreatmentMountedFourZoneV7Error(
                f"{station.reaction_id} V7 backbone/overmold does not resolve to one solid"
            )

        # Distinct positive material domains. Coincident contact boundaries are
        # allowed; positive material/material overlap is not.
        spring_x = x["spring"]
        spring_z = z["spring"]
        shoe_x = x["shoe_polymer"]
        shoe_z = z["shoe_polymer"]
        material_domains = {
            "fixed_backbone": backbone,
            "terminal_x_spring_insert": spring_x,
            "terminal_z_spring_insert": spring_z,
            "terminal_x_preload_shoe_polymer": shoe_x,
            "terminal_z_preload_shoe_polymer": shoe_z,
        }
        for name, shape in material.items():
            if name != "fixed_backbone":
                material_domains[name] = shape

        overlap_checks = {
            "x_spring_to_backbone": _iv(spring_x, backbone),
            "z_spring_to_backbone": _iv(spring_z, backbone),
            "x_spring_to_shoe_polymer": _iv(spring_x, shoe_x),
            "z_spring_to_shoe_polymer": _iv(spring_z, shoe_z),
            "x_to_z_spring": _iv(spring_x, spring_z),
        }
        if max(overlap_checks.values()) > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentMountedFourZoneV7Error(
                f"{station.reaction_id} V7 material partition contains positive overlap"
            )

        # Root and tip bridges are wider than their exits. Translating them in the
        # withdrawal direction must hit surrounding polymer, proving geometric
        # capture without relying on a tiny clearance fit.
        root_pullout = {
            "X": _iv(x["root_head"].translate((0.0, ROOT_PULL_OUT_PROBE_MM, 0.0)), backbone),
            "Z": _iv(z["root_head"].translate((0.0, ROOT_PULL_OUT_PROBE_MM, 0.0)), backbone),
        }
        tip_pullout = {
            "X": _iv(x["tip_head"].translate((0.0, -TIP_PULL_OUT_PROBE_MM, 0.0)), shoe_x),
            "Z": _iv(z["tip_head"].translate((0.0, -TIP_PULL_OUT_PROBE_MM, 0.0)), shoe_z),
        }
        if min(root_pullout.values()) <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentMountedFourZoneV7Error(f"{station.reaction_id} V7 root is not mechanically trapped")
        if min(tip_pullout.values()) <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentMountedFourZoneV7Error(f"{station.reaction_id} V7 tip is not mechanically trapped")

        material = material_domains
        for name, shape in datum.lossy_backup_references:
            reference[f"terminal_{name}"] = shape

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

        operational = station.operational_sweep
        moving_names = {"moving_cup", "moving_rear_clamp", "moving_front_clamp", "moving_output_linkage"}
        fixed_targets = cq.Compound.makeCompound(
            [shape for name, shape in material.items() if name not in moving_names]
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

        truss_screen = dict(station.truss_screen)
        truss_screen["terminal_datum_preload_v2"] = datum.manifest()
        truss_screen["encapsulated_parallel_spring_v7"] = {
            "preload_target_N_per_axis": PRELOAD_TARGET_N,
            "entry_overclosure_mm": ENTRY_OVERCLOSURE_MM,
            "leaf_width_mm": LEAF_WIDTH_MM,
            "leaf_thickness_mm": LEAF_THICKNESS_MM,
            "leaf_pair_gap_mm": LEAF_PAIR_GAP_MM,
            "X": x["screen"],
            "Z": z["screen"],
            "material_overlap_mm3": {name: round(value, 8) for name, value in overlap_checks.items()},
            "root_pullout_probe_mm": ROOT_PULL_OUT_PROBE_MM,
            "root_pullout_intersections_mm3": {name: round(value, 8) for name, value in root_pullout.items()},
            "tip_pullout_probe_mm": TIP_PULL_OUT_PROBE_MM,
            "tip_pullout_intersections_mm3": {name: round(value, 8) for name, value in tip_pullout.items()},
            "capture_rule": (
                "SPRING_ROOT_AND_TIP_BRIDGES_ARE_ENCAPSULATED_BY_SURROUNDING_POLYMER; "
                "FREE_LEAVES_HAVE_EXPLICIT_RELIEF; NO_TINY_RUNNING_FIT_SETS_PRELOAD"
            ),
            "working_reaction_rule": (
                "SPRING_ONLY_MAINTAINS_CONTACT; RIGID_MASTER_DATUMS_CARRY_NORMAL_40HZ_REACTION"
            ),
            "physical_validation": (
                "OPEN_INSERT_MOLDING_PROCESS_SPRING_ALLOY_FORMING_RESIDUAL_STRESS_INTERLOCK_"
                "FATIGUE_CORROSION_WET_CHEMICAL_FRICTION_DAMPING_ACOUSTICS_FORCE_TRAVEL_AND_TOLERANCE"
            ),
        }

        built.append(
            MountedTreatmentStation(
                station.reaction_id,
                station.treatment_center_mm,
                station.axis_angle_deg,
                tuple(material.items()),
                tuple(reference.items()),
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
        base.source_counterpart_sha256,
        reactions.architecture_sha256,
        mates.architecture_sha256,
        tuple(built),
        False,
    )
    architecture.__post_init__()
    return architecture, terminal_datums


def manifest_v7(
    architecture: MountedFourZoneArchitecture,
    datums: TerminalDatumPreloadV2Architecture,
) -> dict[str, object]:
    payload = architecture.manifest()
    payload["schema"] = SCHEMA_V7
    payload["source_main_sha"] = SOURCE_MAIN_SHA
    payload["source_cell6_head_sha"] = SOURCE_CELL6_HEAD_SHA
    payload["source_profile_parent_sha"] = SOURCE_PROFILE_PARENT_SHA
    payload["source_datum_v2_parent_sha"] = SOURCE_DATUM_V2_PARENT_SHA
    payload["terminal_datum_v2_architecture_sha256"] = datums.architecture_sha256
    payload["selected_buttery_candidate"] = (
        "LOW_DRAG_RAIL -> PHASED_X_THEN_Z_C2_TERMINAL_TAKEUP -> ENCAPSULATED_AXIS_TUNED_"
        "PARALLEL_SPRING_INSERTS -> RIGID_MASTER_DATUMS -> ONE_MUTED_AXIAL_EVENT -> "
        "LOSSY_BACKUP -> RIGID_OVERLOAD_STOP"
    )
    payload["manufacturing_intent"] = (
        "SPRING_INSERT_ROOT_AND_TIP_GEOMETRICALLY_ENCAPSULATED; FREE_LEAF_SPAN_RELIEVED; "
        "NO_0P01MM_MOLDED_RUNNING_CLEARANCE_REQUIRED_FOR_NO_RATTLE_CAPTURE"
    )
    payload["physical_validation_eligible"] = False
    payload["physical_validation"] = (
        "OPEN_EXACT_SPRING_ALLOY_INSERT_MOLDING_FORMING_INTERLOCK_FATIGUE_CORROSION_WET_CHEMICAL_"
        "CAM_FRICTION_CONTACT_PRESSURE_DAMPING_ACOUSTICS_FORCE_TRAVEL_TOLERANCE_AND_SUBJECTIVE_FEEL"
    )
    payload["supersedes_as_current_v1_mount_candidate"] = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V6"
    return payload


def export_mounted_four_zone_architecture_v7(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture, datums = build_mounted_four_zone_architecture_v7()
    for station in architecture.stations:
        slug = station.reaction_id.lower()
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.material_parts]),
            str(output_dir / f"{slug}_mounted_station_v7_material.step"),
        )
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.reference_parts]),
            str(output_dir / f"{slug}_mounted_station_v7_reference.step"),
        )
        cq.exporters.export(station.service_sweep, str(output_dir / f"{slug}_service_v7_sweep.step"))
    manifest = manifest_v7(architecture, datums)
    (output_dir / "treatment_mounted_four_zone_v7_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
