from __future__ import annotations

"""Axis-separated parallelogram preload spring cassettes for the treatment mount.

The manufactured spring is represented in its stress-free state. A separate installed
shape represents the elastically deflected occupied volume at full seat. The preload
shoe moves with the spring tip; only the root overmold/support is part of the fixed
carrier backbone.

Pair separation is deliberately along the commanded motion axis (X for the X shoe,
Z for the Z shoe). This is the geometric correction to the rejected V7 transverse
pair, which did not intrinsically constrain in-plane shoe rotation.

The root overmold is cut by the complete installed spring occupied volume, not merely
by the root-head block. The spring leaves intentionally overlap the head in Y to form
a connected spring, so cutting only the head leaves the first leaf segment buried in
polymer. The complete-volume cut creates explicit leaf exit windows while the
positive pull-out probe still proves geometric head capture. This changes the local
root pocket only; spring force, alloy, fatigue and insert-molding process remain
physical-validation work.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path

import cadquery as cq

from studies.treatment_terminal_mechanics_v2 import (
    GUIDE_PAIR_SEPARATION_MM,
    LEAF_THICKNESS_MM,
    LEAF_WIDTH_MM,
    axis_design,
)
from .structural_frame_actuator_reactions import REACTION_IDS
from .treatment_terminal_datum_preload_v3 import TerminalDatumPreloadV3Station

SCHEMA = "MASCK_ONE_TREATMENT_GUIDED_PRELOAD_SPRING_V1"

HEAD_END_OVERLAP_MM = 0.10
HEAD_MARGIN_MM = 0.10
ROOT_HEAD_LENGTH_Y_MM = 0.72
TIP_HEAD_LENGTH_Y_MM = 0.44
ROOT_CAPTURE_COVER_MM = 0.20
TIP_CAPTURE_COVER_MM = 0.18
TIP_CAPTURE_PROJECTION_MM = 0.34
ROOT_CAPTURE_LENGTH_Y_MM = 1.18
TIP_CAPTURE_LENGTH_Y_MM = 0.82
SUPPORT_RIB_THICKNESS_MM = 0.30
SUPPORT_RIB_CLEARANCE_MM = 0.10
ROOT_PULL_OUT_PROBE_MM = 0.22
TIP_PULL_OUT_PROBE_MM = 0.16
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class TreatmentGuidedPreloadSpringError(ValueError):
    pass


def _box(x: float, y: float, z: float, center: tuple[float, float, float]) -> cq.Shape:
    if min(x, y, z) <= 0.0:
        raise TreatmentGuidedPreloadSpringError("spring cassette box dimensions must be positive")
    return cq.Workplane("XY").box(x, y, z).translate(center).val()


def _join(shapes: list[cq.Shape]) -> cq.Shape:
    if not shapes:
        raise TreatmentGuidedPreloadSpringError("cannot join empty spring shape list")
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    result = result.clean()
    if not result.isValid() or not result.Solids():
        raise TreatmentGuidedPreloadSpringError("spring geometry must remain valid")
    return result


def _iv(a: cq.Shape, b: cq.Shape) -> float:
    aa, bb = a.BoundingBox(), b.BoundingBox()
    if aa.xmax < bb.xmin or bb.xmax < aa.xmin or aa.ymax < bb.ymin or bb.ymax < aa.ymin or aa.zmax < bb.zmin or bb.zmax < aa.zmin:
        return 0.0
    try:
        common = a.intersect(b)
    except Exception as exc:
        raise TreatmentGuidedPreloadSpringError("intersection kernel failure") from exc
    if not common.isValid():
        raise TreatmentGuidedPreloadSpringError("invalid spring intersection result")
    return sum(max(0.0, float(s.Volume())) for s in common.Solids())


def _leaf_x(root_x: float, tip_x: float, root_y: float, tip_y: float, z_center: float) -> cq.Shape:
    import math
    dx, dy = tip_x - root_x, tip_y - root_y
    length = math.hypot(dx, dy)
    angle = -math.degrees(math.atan2(dx, dy))
    shape = cq.Workplane("XY").box(LEAF_THICKNESS_MM, length, LEAF_WIDTH_MM).val()
    return shape.rotate((0, 0, 0), (0, 0, 1), angle).translate(((root_x + tip_x) / 2, (root_y + tip_y) / 2, z_center))


def _leaf_z(root_z: float, tip_z: float, root_y: float, tip_y: float, x_center: float) -> cq.Shape:
    import math
    dz, dy = tip_z - root_z, tip_y - root_y
    length = math.hypot(dz, dy)
    angle = math.degrees(math.atan2(dz, dy))
    shape = cq.Workplane("XY").box(LEAF_WIDTH_MM, length, LEAF_THICKNESS_MM).val()
    return shape.rotate((0, 0, 0), (1, 0, 0), angle).translate((x_center, (root_y + tip_y) / 2, (root_z + tip_z) / 2))


def _span() -> float:
    return GUIDE_PAIR_SEPARATION_MM + LEAF_THICKNESS_MM + 2.0 * HEAD_MARGIN_MM


@dataclass(frozen=True, slots=True)
class GuidedPreloadSpringStation:
    reaction_id: str
    installed_springs: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    free_springs: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    root_polymer: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    installed_shoes: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    free_shoes: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    capture_screen: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.reaction_id not in REACTION_IDS:
            raise TreatmentGuidedPreloadSpringError("unknown reaction id")
        for group in (self.installed_springs, self.free_springs, self.root_polymer, self.installed_shoes, self.free_shoes):
            for _name, shape in group:
                if not shape.isValid() or not shape.Solids() or float(shape.Volume()) <= 0.0:
                    raise TreatmentGuidedPreloadSpringError("guided spring part must be valid positive geometry")
        if min(self.capture_screen.values()) <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentGuidedPreloadSpringError("spring root/tip capture probe must be positive")

    def manifest(self) -> dict[str, object]:
        return {
            "reaction_id": self.reaction_id,
            "architecture": "AXIS_SEPARATED_TWO_LEAF_PARALLELOGRAM_WITH_CAPTIVE_ROOT_AND_MOVING_TIP_SHOE",
            "manufacturing_state": "FREE_SPRING_GEOMETRY_IS_THE_MANUFACTURED_PART_INSTALLED_SHAPE_IS_REFERENCE_OCCUPIED_VOLUME",
            "root_capture_geometry": "COMPLETE_INSTALLED_SPRING_VOLUME_CUT_CREATES_LEAF_EXIT_WINDOWS_WITH_POSITIVE_HEAD_PULL_OUT_CAPTURE",
            "guide_pair_separation_mm": GUIDE_PAIR_SEPARATION_MM,
            "leaf_width_mm": LEAF_WIDTH_MM,
            "leaf_thickness_mm": LEAF_THICKNESS_MM,
            "capture_screen": self.capture_screen,
            "physical_validation": "OPEN_SPRING_ALLOY_FORMING_INSERT_MOLDING_INTERLOCK_FATIGUE_RELAXATION_CORROSION_DAMPING_AND_ACOUSTICS",
        }


def _x_cassette(station: TerminalDatumPreloadV3Station) -> dict[str, cq.Shape]:
    shoe_outer = dict(station.preload_outer_parts)["preload_x_outer_v3"]
    bb = shoe_outer.BoundingBox()
    axis = axis_design("X")
    cx, _cy = station.center_xy_mm
    sign = 1.0 if cx > 0.0 else -1.0
    outer_face = bb.xmax if sign > 0 else bb.xmin
    tip_center_x = outer_face + sign * TIP_CAPTURE_PROJECTION_MM
    root_center_x = tip_center_x - sign * axis.installed_deflection_mm
    tip_y = bb.ymin + TIP_HEAD_LENGTH_Y_MM / 2.0 + 0.08
    root_y = tip_y - axis.effective_leaf_length_mm
    z_mid = 0.5 * (bb.zmin + bb.zmax)
    half_sep = GUIDE_PAIR_SEPARATION_MM / 2.0
    bridge_span = _span()

    def spring(installed: bool) -> tuple[cq.Shape, cq.Shape, cq.Shape]:
        deflection = sign * axis.installed_deflection_mm if installed else 0.0
        leaves = []
        for offset in (-half_sep, half_sep):
            rx = root_center_x + offset
            tx = rx + deflection
            leaves.append(_leaf_x(rx, tx, root_y, tip_y, z_mid))
        root_head = _box(bridge_span, ROOT_HEAD_LENGTH_Y_MM, LEAF_WIDTH_MM, (root_center_x, root_y - ROOT_HEAD_LENGTH_Y_MM / 2 + HEAD_END_OVERLAP_MM, z_mid))
        tip_center = root_center_x + deflection
        tip_head = _box(bridge_span, TIP_HEAD_LENGTH_Y_MM, LEAF_WIDTH_MM, (tip_center, tip_y, z_mid))
        return _join([root_head, *leaves, tip_head]), root_head, tip_head

    installed, root_head_i, tip_head_i = spring(True)
    free, _root_head_f, _tip_head_f = spring(False)
    root_capture_raw = _box(bridge_span + 2 * ROOT_CAPTURE_COVER_MM, ROOT_CAPTURE_LENGTH_Y_MM, LEAF_WIDTH_MM + 2 * ROOT_CAPTURE_COVER_MM, (root_center_x, root_y - ROOT_HEAD_LENGTH_Y_MM / 2 + HEAD_END_OVERLAP_MM, z_mid))
    # The leaves overlap the root head by design so the spring is one connected part.
    # Cut the complete installed spring occupancy, not only the head, to create true
    # leaf exit windows and prevent hidden spring/polymer interpenetration.
    root_capture = root_capture_raw.cut(installed).clean()

    installed_tip_center_x = root_center_x + sign * axis.installed_deflection_mm
    tip_capture_raw = _box(bridge_span + 2 * TIP_CAPTURE_COVER_MM, TIP_CAPTURE_LENGTH_Y_MM, LEAF_WIDTH_MM + 2 * TIP_CAPTURE_COVER_MM, (installed_tip_center_x, tip_y, z_mid))
    installed_shoe = shoe_outer.fuse(tip_capture_raw).cut(installed).clean()
    free_tip_center_x = root_center_x
    free_tip_capture_raw = _box(bridge_span + 2 * TIP_CAPTURE_COVER_MM, TIP_CAPTURE_LENGTH_Y_MM, LEAF_WIDTH_MM + 2 * TIP_CAPTURE_COVER_MM, (free_tip_center_x, tip_y, z_mid))
    free_shoe = shoe_outer.translate((-sign * axis.installed_deflection_mm, 0, 0)).fuse(free_tip_capture_raw).cut(free).clean()

    support_z = LEAF_WIDTH_MM / 2 + SUPPORT_RIB_CLEARANCE_MM + SUPPORT_RIB_THICKNESS_MM / 2
    support_y0 = root_y - ROOT_HEAD_LENGTH_Y_MM / 2
    support_y1 = bb.ymin + 0.04
    support_len = max(0.2, support_y1 - support_y0)
    support_cy = 0.5 * (support_y0 + support_y1)
    supports = _join([
        _box(bridge_span + 2 * ROOT_CAPTURE_COVER_MM, support_len, SUPPORT_RIB_THICKNESS_MM, (root_center_x, support_cy, z_mid - support_z)),
        _box(bridge_span + 2 * ROOT_CAPTURE_COVER_MM, support_len, SUPPORT_RIB_THICKNESS_MM, (root_center_x, support_cy, z_mid + support_z)),
    ])
    root_polymer = _join([root_capture, supports])
    return {"installed": installed, "free": free, "root_head": root_head_i, "tip_head": tip_head_i, "root_polymer": root_polymer, "installed_shoe": installed_shoe, "free_shoe": free_shoe}


def _z_cassette(station: TerminalDatumPreloadV3Station) -> dict[str, cq.Shape]:
    shoe_outer = dict(station.preload_outer_parts)["preload_z_outer_v3"]
    bb = shoe_outer.BoundingBox()
    axis = axis_design("Z")
    outer_face = bb.zmax
    tip_center_z = outer_face + TIP_CAPTURE_PROJECTION_MM
    root_center_z = tip_center_z - axis.installed_deflection_mm
    tip_y = bb.ymin + TIP_HEAD_LENGTH_Y_MM / 2.0 + 0.08
    root_y = tip_y - axis.effective_leaf_length_mm
    x_mid = 0.5 * (bb.xmin + bb.xmax)
    half_sep = GUIDE_PAIR_SEPARATION_MM / 2.0
    bridge_span = _span()

    def spring(installed: bool) -> tuple[cq.Shape, cq.Shape, cq.Shape]:
        deflection = axis.installed_deflection_mm if installed else 0.0
        leaves = []
        for offset in (-half_sep, half_sep):
            rz = root_center_z + offset
            tz = rz + deflection
            leaves.append(_leaf_z(rz, tz, root_y, tip_y, x_mid))
        root_head = _box(LEAF_WIDTH_MM, ROOT_HEAD_LENGTH_Y_MM, bridge_span, (x_mid, root_y - ROOT_HEAD_LENGTH_Y_MM / 2 + HEAD_END_OVERLAP_MM, root_center_z))
        tip_center = root_center_z + deflection
        tip_head = _box(LEAF_WIDTH_MM, TIP_HEAD_LENGTH_Y_MM, bridge_span, (x_mid, tip_y, tip_center))
        return _join([root_head, *leaves, tip_head]), root_head, tip_head

    installed, root_head_i, tip_head_i = spring(True)
    free, _root_head_f, _tip_head_f = spring(False)
    root_capture_raw = _box(LEAF_WIDTH_MM + 2 * ROOT_CAPTURE_COVER_MM, ROOT_CAPTURE_LENGTH_Y_MM, bridge_span + 2 * ROOT_CAPTURE_COVER_MM, (x_mid, root_y - ROOT_HEAD_LENGTH_Y_MM / 2 + HEAD_END_OVERLAP_MM, root_center_z))
    # Same complete-volume root-pocket rule as the X cassette.
    root_capture = root_capture_raw.cut(installed).clean()

    installed_tip_center_z = root_center_z + axis.installed_deflection_mm
    tip_capture_raw = _box(LEAF_WIDTH_MM + 2 * TIP_CAPTURE_COVER_MM, TIP_CAPTURE_LENGTH_Y_MM, bridge_span + 2 * TIP_CAPTURE_COVER_MM, (x_mid, tip_y, installed_tip_center_z))
    installed_shoe = shoe_outer.fuse(tip_capture_raw).cut(installed).clean()
    free_tip_center_z = root_center_z
    free_tip_capture_raw = _box(LEAF_WIDTH_MM + 2 * TIP_CAPTURE_COVER_MM, TIP_CAPTURE_LENGTH_Y_MM, bridge_span + 2 * TIP_CAPTURE_COVER_MM, (x_mid, tip_y, free_tip_center_z))
    free_shoe = shoe_outer.translate((0, 0, -axis.installed_deflection_mm)).fuse(free_tip_capture_raw).cut(free).clean()

    support_x = LEAF_WIDTH_MM / 2 + SUPPORT_RIB_CLEARANCE_MM + SUPPORT_RIB_THICKNESS_MM / 2
    support_y0 = root_y - ROOT_HEAD_LENGTH_Y_MM / 2
    support_y1 = bb.ymin + 0.04
    support_len = max(0.2, support_y1 - support_y0)
    support_cy = 0.5 * (support_y0 + support_y1)
    supports = _join([
        _box(SUPPORT_RIB_THICKNESS_MM, support_len, bridge_span + 2 * ROOT_CAPTURE_COVER_MM, (x_mid - support_x, support_cy, root_center_z)),
        _box(SUPPORT_RIB_THICKNESS_MM, support_len, bridge_span + 2 * ROOT_CAPTURE_COVER_MM, (x_mid + support_x, support_cy, root_center_z)),
    ])
    root_polymer = _join([root_capture, supports])
    return {"installed": installed, "free": free, "root_head": root_head_i, "tip_head": tip_head_i, "root_polymer": root_polymer, "installed_shoe": installed_shoe, "free_shoe": free_shoe}


def build_guided_preload_spring_station(station: TerminalDatumPreloadV3Station) -> GuidedPreloadSpringStation:
    x, z = _x_cassette(station), _z_cassette(station)
    # Pull-out probes establish geometric capture, not retention force.
    root_capture = {
        "X_root": _iv(x["root_head"].translate((0, ROOT_PULL_OUT_PROBE_MM, 0)), x["root_polymer"]),
        "Z_root": _iv(z["root_head"].translate((0, ROOT_PULL_OUT_PROBE_MM, 0)), z["root_polymer"]),
        "X_tip": _iv(x["tip_head"].translate((0, -TIP_PULL_OUT_PROBE_MM, 0)), x["installed_shoe"]),
        "Z_tip": _iv(z["tip_head"].translate((0, -TIP_PULL_OUT_PROBE_MM, 0)), z["installed_shoe"]),
    }
    # Positive material overlap at nominal installed state is prohibited.
    overlap = {
        "X_root": _iv(x["installed"], x["root_polymer"]),
        "Z_root": _iv(z["installed"], z["root_polymer"]),
        "X_tip": _iv(x["installed"], x["installed_shoe"]),
        "Z_tip": _iv(z["installed"], z["installed_shoe"]),
        "X_to_Z_spring": _iv(x["installed"], z["installed"]),
    }
    if max(overlap.values()) > _INTERSECTION_TOLERANCE_MM3:
        raise TreatmentGuidedPreloadSpringError(
            f"{station.reaction_id} spring/polymer material overlap: {overlap}"
        )
    result = GuidedPreloadSpringStation(
        station.reaction_id,
        (("terminal_x_spring_installed", x["installed"]), ("terminal_z_spring_installed", z["installed"])),
        (("terminal_x_spring_free", x["free"]), ("terminal_z_spring_free", z["free"])),
        (("terminal_x_root_polymer", x["root_polymer"]), ("terminal_z_root_polymer", z["root_polymer"])),
        (("terminal_x_preload_shoe", x["installed_shoe"]), ("terminal_z_preload_shoe", z["installed_shoe"])),
        (("terminal_x_preload_shoe_free", x["free_shoe"]), ("terminal_z_preload_shoe_free", z["free_shoe"])),
        {name: round(value, 8) for name, value in root_capture.items()},
    )
    result.__post_init__()
    return result


def export_guided_preload_spring_station(station: TerminalDatumPreloadV3Station, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result = build_guided_preload_spring_station(station)
    slug = station.reaction_id.lower()
    for name, shape in result.free_springs:
        cq.exporters.export(shape, str(output_dir / f"{slug}_{name}_MANUFACTURED.step"))
    for name, shape in result.installed_springs:
        cq.exporters.export(shape, str(output_dir / f"{slug}_{name}_REFERENCE.step"))
    for name, shape in result.installed_shoes + result.root_polymer:
        cq.exporters.export(shape, str(output_dir / f"{slug}_{name}.step"))
    manifest = {"schema": SCHEMA, **result.manifest()}
    (output_dir / f"{slug}_guided_preload_spring_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
