from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from .model import MasckOneModel, build_model
from .structural_frame_actuator_reactions import StructuralFrameActuatorReactionArchitecture, build_structural_frame_actuator_reactions
from .structural_frame_realization import _protected_zone_solid

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_DRY_PACKAGE_SUPPORTS_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SUPPORT_IDS = ("BATTERY_LEFT_SUPPORT", "BATTERY_RIGHT_SUPPORT")
ROOT_BOSS_WIDTH_MM = 7.0
ROOT_BOSS_HEIGHT_MM = 8.0
ROOT_BOSS_DEPTH_MM = 3.2
ROOT_FRAME_CAPTURE_MM = 0.45
ROOT_SOCKET_WIDTH_MM = 3.8
ROOT_SOCKET_HEIGHT_MM = 4.8
ROOT_SOCKET_DEPTH_MM = 3.3
ROOT_SOCKET_FRAME_PENETRATION_MM = 0.10
ROOT_KEY_CLEARANCE_MM = 0.15
ROOT_SHOULDER_GAP_MM = 0.15
ROOT_SHOULDER_THICKNESS_MM = 0.9
POST_WIDTH_MM = 3.0
POST_Y_MM = 3.0
ARM_Y_MM = 3.0
ARM_Z_MM = 2.0
BATTERY_SIDE_CLEARANCE_MM = 0.35
SIDE_RAIL_THICKNESS_MM = 1.5
SIDE_RAIL_Y_OVERHANG_MM = 1.8
SIDE_RAIL_Z_OVERHANG_MM = 1.2
STOP_PROBE_MM = 0.50
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameDryPackageSupportError(ValueError):
    pass


def _ivol(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        return max(0.0, float(a.intersect(b).val().Volume()))
    except Exception:
        return 0.0


def _single(shape: cq.Workplane, label: str) -> None:
    solids = shape.solids().vals()
    if len(solids) != 1 or not solids[0].isValid() or float(solids[0].Volume()) <= 0.0:
        raise StructuralFrameDryPackageSupportError(f"{label} must be one valid positive B-rep solid")


@dataclass(frozen=True, slots=True)
class BatterySupportRail:
    support_id: str
    side_sign: float
    root_center_xyz_mm: tuple[float, float, float]
    package_side_x_mm: float
    frame_intersection_mm3: float
    package_intersection_mm3: float
    protected_intersection_mm3: float
    hostile_package_stop_intersection_mm3: float
    rail: cq.Workplane = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.support_id not in SUPPORT_IDS or self.side_sign not in (-1.0, 1.0):
            raise StructuralFrameDryPackageSupportError("invalid battery support identity")
        if len(self.root_center_xyz_mm) != 3 or not all(math.isfinite(float(v)) for v in self.root_center_xyz_mm):
            raise StructuralFrameDryPackageSupportError("battery support root datum must be finite world XYZ")
        _single(self.rail, self.support_id)
        if self.frame_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameDryPackageSupportError("removable battery rail intersects frame material")
        if self.package_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameDryPackageSupportError("nominal battery rail intersects battery package envelope")
        if self.protected_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameDryPackageSupportError("battery support intersects hard protected geometry")
        if self.hostile_package_stop_intersection_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameDryPackageSupportError("battery support lacks a real lateral package stop")

    def manifest(self) -> dict[str, object]:
        return {
            "support_id": self.support_id,
            "side_sign": self.side_sign,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "root_center_xyz_mm": list(self.root_center_xyz_mm),
            "package_side_x_mm": self.package_side_x_mm,
            "interface_semantics": "POSTERIOR_INSERTABLE_KEYED_FRAME_RAIL_WITH_LATERAL_BATTERY_STOP",
            "measured": {
                "frame_intersection_mm3": self.frame_intersection_mm3,
                "package_intersection_mm3": self.package_intersection_mm3,
                "protected_intersection_mm3": self.protected_intersection_mm3,
                "hostile_package_stop_intersection_mm3": self.hostile_package_stop_intersection_mm3,
            },
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameDryPackageSupportArchitecture:
    source_reaction_architecture_sha256: str
    frame_with_support_counterparts: cq.Workplane = field(repr=False, compare=False)
    supports: tuple[BatterySupportRail, ...] = ()
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_reaction_architecture_sha256) != 64:
            raise StructuralFrameDryPackageSupportError("source reaction architecture identity must be SHA-256")
        _single(self.frame_with_support_counterparts, "frame with dry-package counterparts")
        if tuple(s.support_id for s in self.supports) != SUPPORT_IDS:
            raise StructuralFrameDryPackageSupportError("bilateral battery supports must exist in controlled order")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameDryPackageSupportError("digital package supports are not physical-validation evidence")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_reaction_architecture_sha256": self.source_reaction_architecture_sha256,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "package_source": "model.battery_reference_envelope",
            "package_status": "PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE",
            "root_socket_semantics": "BLIND_GEOMETRY_FORBIDDEN_SOCKET_OPENS_POSTERIOR_AND_PENETRATES_FRAME_SIDE_STOP_WALL",
            "supports": [s.manifest() for s in self.supports],
            "assembly_sequence": [
                "place battery reference envelope between bilateral open supports",
                "insert each support key continuously from posterior through its open frame-side socket",
                "seat each shoulder against the boss rear face as positive insertion stop",
                "reverse insertion independently for service removal",
            ],
            "production_tolerance_status": "NOMINAL_DIGITAL_CLEARANCE_SEEDS_ONLY",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def _boss_and_socket(cx: float, zmin: float) -> tuple[cq.Workplane, cq.Workplane, float, float]:
    boss_cz = zmin - (ROOT_BOSS_DEPTH_MM - ROOT_FRAME_CAPTURE_MM) / 2.0
    boss = cq.Workplane("XY").box(ROOT_BOSS_WIDTH_MM, ROOT_BOSS_HEIGHT_MM, ROOT_BOSS_DEPTH_MM, centered=(True, True, True)).translate((cx, 0.0, boss_cz))
    boss_back_z = boss_cz - ROOT_BOSS_DEPTH_MM / 2.0
    socket_front_z = zmin + ROOT_SOCKET_FRAME_PENETRATION_MM
    socket_cz = socket_front_z - ROOT_SOCKET_DEPTH_MM / 2.0
    socket = cq.Workplane("XY").box(ROOT_SOCKET_WIDTH_MM, ROOT_SOCKET_HEIGHT_MM, ROOT_SOCKET_DEPTH_MM, centered=(True, True, True)).translate((cx, 0.0, socket_cz))
    if socket_cz - ROOT_SOCKET_DEPTH_MM / 2.0 >= boss_back_z:
        raise StructuralFrameDryPackageSupportError("battery support root socket is blind on its posterior insertion side")
    return boss, socket, socket_cz, boss_back_z


def _rail(side_sign: float, root_x: float, socket_cz: float, boss_back_z: float, battery_box: cq.BoundBox) -> cq.Workplane:
    key_w = ROOT_SOCKET_WIDTH_MM - 2.0 * ROOT_KEY_CLEARANCE_MM
    key_h = ROOT_SOCKET_HEIGHT_MM - 2.0 * ROOT_KEY_CLEARANCE_MM
    key_front_z = socket_cz + ROOT_SOCKET_DEPTH_MM / 2.0 - ROOT_KEY_CLEARANCE_MM
    shoulder_front_z = boss_back_z - ROOT_SHOULDER_GAP_MM
    key_back_z = shoulder_front_z - 0.10
    key_d = key_front_z - key_back_z
    key = cq.Workplane("XY").box(key_w, key_h, key_d, centered=(True, True, True)).translate((root_x, 0.0, (key_front_z + key_back_z) / 2.0))
    shoulder_z = shoulder_front_z - ROOT_SHOULDER_THICKNESS_MM / 2.0
    shoulder = cq.Workplane("XY").box(ROOT_BOSS_WIDTH_MM, ROOT_BOSS_HEIGHT_MM, ROOT_SHOULDER_THICKNESS_MM, centered=(True, True, True)).translate((root_x, 0.0, shoulder_z))
    battery_cz = (battery_box.zmin + battery_box.zmax) / 2.0
    post_height = abs(shoulder_z - battery_cz) + ARM_Z_MM
    post = cq.Workplane("XY").box(POST_WIDTH_MM, POST_Y_MM, post_height, centered=(True, True, True)).translate((root_x, 0.0, (shoulder_z + battery_cz) / 2.0))
    package_side_x = battery_box.xmax if side_sign > 0.0 else battery_box.xmin
    rail_center_x = package_side_x + side_sign * (BATTERY_SIDE_CLEARANCE_MM + SIDE_RAIL_THICKNESS_MM / 2.0)
    arm_center_x = (root_x + rail_center_x) / 2.0
    arm_len = abs(root_x - rail_center_x) + POST_WIDTH_MM
    arm = cq.Workplane("XY").box(arm_len, ARM_Y_MM, ARM_Z_MM, centered=(True, True, True)).translate((arm_center_x, 0.0, battery_cz))
    rail_y = (battery_box.ymax - battery_box.ymin) + 2.0 * SIDE_RAIL_Y_OVERHANG_MM
    rail_z = (battery_box.zmax - battery_box.zmin) + 2.0 * SIDE_RAIL_Z_OVERHANG_MM
    side_rail = cq.Workplane("XY").box(SIDE_RAIL_THICKNESS_MM, rail_y, rail_z, centered=(True, True, True)).translate((rail_center_x, (battery_box.ymin + battery_box.ymax) / 2.0, battery_cz))
    return key.union(shoulder).union(post).union(arm).union(side_rail)


def build_structural_frame_dry_package_supports(*, model: MasckOneModel | None = None, reactions: StructuralFrameActuatorReactionArchitecture | None = None) -> StructuralFrameDryPackageSupportArchitecture:
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    base_frame = reactions.frame_with_reaction_counterparts
    frame_box = base_frame.val().BoundingBox()
    battery = model.battery_reference_envelope.solid
    battery_box = battery.val().BoundingBox()
    root_abs_x = min(abs(float(frame_box.xmin)), abs(float(frame_box.xmax))) - ROOT_BOSS_WIDTH_MM / 2.0
    frame = base_frame
    root_data: list[tuple[float, float, float]] = []
    for side_sign in (-1.0, 1.0):
        root_x = side_sign * root_abs_x
        boss, socket, socket_cz, boss_back_z = _boss_and_socket(root_x, float(frame_box.zmin))
        before = float(frame.val().Volume())
        fused = frame.union(boss)
        if float(fused.val().Volume()) >= before + float(boss.val().Volume()) - _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameDryPackageSupportError("dry-package root boss lacks positive frame capture")
        frame = fused.cut(socket)
        root_data.append((root_x, socket_cz, boss_back_z))
    _single(frame, "frame with bilateral dry-package sockets")

    supports: list[BatterySupportRail] = []
    for index, (side_sign, (root_x, socket_cz, boss_back_z)) in enumerate(zip((-1.0, 1.0), root_data, strict=True)):
        rail = _rail(side_sign, root_x, socket_cz, boss_back_z, battery_box)
        _single(rail, SUPPORT_IDS[index])
        protected = 0.0
        rail_box = rail.val().BoundingBox()
        for item in model.protected_volumes.all:
            zone = item.zone
            keepout = _protected_zone_solid(center_x_mm=zone.center.x, center_y_mm=zone.center.y, envelope_width_mm=zone.envelope_width_mm, envelope_height_mm=zone.envelope_height_mm, angle_deg=zone.angle_deg, z_min_mm=float(rail_box.zmin) - 1.0, z_max_mm=float(rail_box.zmax) + 1.0)
            protected += _ivol(rail, keepout)
        hostile = rail.translate((-side_sign * STOP_PROBE_MM, 0.0, 0.0))
        supports.append(BatterySupportRail(
            support_id=SUPPORT_IDS[index],
            side_sign=side_sign,
            root_center_xyz_mm=(root_x, 0.0, socket_cz),
            package_side_x_mm=float(battery_box.xmin if side_sign < 0.0 else battery_box.xmax),
            frame_intersection_mm3=round(_ivol(rail, frame), 8),
            package_intersection_mm3=round(_ivol(rail, battery), 8),
            protected_intersection_mm3=round(protected, 8),
            hostile_package_stop_intersection_mm3=round(_ivol(hostile, battery), 8),
            rail=rail,
        ))
    return StructuralFrameDryPackageSupportArchitecture(source_reaction_architecture_sha256=reactions.architecture_sha256, frame_with_support_counterparts=frame, supports=tuple(supports), physical_validation_eligible=False)


def export_structural_frame_dry_package_supports(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_structural_frame_dry_package_supports()
    cq.exporters.export(architecture.frame_with_support_counterparts, str(output_dir / "structural_frame_with_battery_support_counterparts.step"))
    for support in architecture.supports:
        cq.exporters.export(support.rail, str(output_dir / f"{support.support_id.lower()}.step"))
    manifest = architecture.manifest()
    (output_dir / "structural_frame_dry_package_supports_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return manifest
