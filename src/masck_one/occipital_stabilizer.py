from __future__ import annotations

"""Cell 3 lateral occipital-stabilization geometry.

This module deliberately separates three retention functions that legacy halo geometry
conflated: facial reaction remains on the front structural loop, occipital stabilization
is realized here as two lateral rear yokes, and crown support remains a separate superior
interface corridor. Geometry is digital-only. Head fit, comfort, preload, hair interaction,
material response and structural capacity remain physical evidence gates.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path

import cadquery as cq

from .authority import Authority, load_authority
from .model import Component, MasckOneModel, build_model
from .realized_waste_backbone_release import build_current_cell4_waste_backbone_release
from .structural_frame import RESERVATION_RETENTION

SCHEMA = "MASCK_ONE_CELL3_OCCIPITAL_STABILIZER_V1"
SOURCE_MAIN_SHA = "628ec5f5766937433b1bdf8f30edc372924cf41e"
SOURCE_AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
DIGITAL_ONLY = "DIGITAL_OCCIPITAL_GEOMETRY_ONLY_NOT_PHYSICAL_VALIDATION"
KERNEL_ZERO_MM3 = 1e-8

# Cell 3 provisional geometry seeds, not anthropometric or supplier dimensions.
ROOT_X_INSET_FROM_FRAME_SIDE_MM = 5.5
ROOT_Y_MM = 10.0
ROOT_Z_MM = -31.0
ROOT_BOSS_XYZ_MM = (7.0, 10.0, 6.0)
ROOT_CAPTURE_BORE_RADIUS_MM = 1.6
ROOT_CAPTURE_BORE_LENGTH_MM = 14.0

PAD_CENTER_X_MM = 52.0
PAD_CENTER_Y_MM = -5.0
PAD_CENTER_Z_MM = -51.0
PAD_BACKER_XYZ_MM = (16.0, 30.0, 3.0)
PAD_CORNER_RADIUS_MM = 3.0
PAD_CONTACT_FACE_Z_MM = PAD_CENTER_Z_MM + PAD_BACKER_XYZ_MM[2] / 2.0

RAIL_END_X_MM = 58.0
RAIL_UPPER_Y_MM = 8.0
RAIL_LOWER_Y_MM = -18.0
RAIL_END_Z_MM = -49.5
RAIL_RADIUS_MM = 1.8

# Explicit central rear packaging reservation. This is a Cell 3 interface keepout, not
# selected electronics hardware. It conservatively contains the stale Manual-B dry-bay
# source candidate (62 x 96 x 16 mm centered at Z=-34 mm) without consuming it as truth.
CENTRAL_REAR_PACKAGE_KEEP_OUT_XYZ_MM = (68.0, 104.0, 24.0)
CENTRAL_REAR_PACKAGE_KEEP_OUT_CENTER_MM = (0.0, 0.0, -36.0)

# Crown support is intentionally not the same geometry as occipital stabilization.
CROWN_SUPPORT_CORRIDOR_XYZ_MM = (136.0, 34.0, 14.0)
CROWN_SUPPORT_CORRIDOR_CENTER_MM = (0.0, 73.0, -47.0)


class OccipitalStabilizerError(ValueError):
    pass


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise OccipitalStabilizerError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise OccipitalStabilizerError(f"{label} must be finite")
    return 0.0 if result == 0.0 else result


def _positive(value: object, label: str) -> float:
    result = _finite(value, label)
    if result <= 0.0:
        raise OccipitalStabilizerError(f"{label} must be positive")
    return result


def _single(solid: cq.Workplane, label: str) -> cq.Workplane:
    shape = solid.val()
    if not shape.isValid() or float(shape.Volume()) <= 0.0 or len(shape.Solids()) != 1:
        raise OccipitalStabilizerError(f"{label} must be one valid positive-volume solid")
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
        raise OccipitalStabilizerError("cylinder axis must be unit length")
    cx, cy, cz = center
    start = (
        cx - ax * length / 2.0,
        cy - ay * length / 2.0,
        cz - az * length / 2.0,
    )
    shape = cq.Solid.makeCylinder(
        radius,
        length,
        cq.Vector(*start),
        cq.Vector(ax, ay, az),
    )
    return cq.Workplane("XY").newObject([shape])


def _capsule_between(
    start_xyz: tuple[float, float, float],
    end_xyz: tuple[float, float, float],
    radius_mm: float,
) -> cq.Workplane:
    sx, sy, sz = start_xyz
    ex, ey, ez = end_xyz
    dx, dy, dz = ex - sx, ey - sy, ez - sz
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length <= 0.0:
        raise OccipitalStabilizerError("rail span cannot have zero length")
    direction = cq.Vector(dx / length, dy / length, dz / length)
    cylinder = cq.Solid.makeCylinder(
        _positive(radius_mm, "rail radius"),
        length,
        cq.Vector(sx, sy, sz),
        direction,
    )
    first = cq.Solid.makeSphere(radius_mm, cq.Vector(sx, sy, sz))
    second = cq.Solid.makeSphere(radius_mm, cq.Vector(ex, ey, ez))
    result = cq.Workplane("XY").newObject([cylinder])
    result = result.union(cq.Workplane("XY").newObject([first]))
    result = result.union(cq.Workplane("XY").newObject([second]))
    return _single(result, "fork rail capsule")


def _rounded_pad(center: tuple[float, float, float]) -> cq.Workplane:
    pad = _box(PAD_BACKER_XYZ_MM, center)
    return _single(pad.edges("|Z").fillet(PAD_CORNER_RADIUS_MM), "occipital pad backer")


def _bbox(solid: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = solid.val().BoundingBox()
    return tuple(
        round(float(value), 6)
        for value in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    )


def _intersection_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise OccipitalStabilizerError("intersection volume must be finite and nonnegative")
    return 0.0 if value < KERNEL_ZERO_MM3 else value


def _component_signature(component: Component) -> dict[str, object]:
    return {
        "name": component.name,
        "status": component.status,
        "bounds_mm": list(_bbox(component.solid)),
        "volume_mm3": round(float(component.solid.val().Volume()), 6),
    }


def _source_model_sha(model: MasckOneModel) -> str:
    components = (
        model.shell,
        *model.actuator_envelopes,
        model.water_reservoir_envelope,
        model.waste_cartridge_envelope,
        model.battery_reference_envelope,
    )
    raw = json.dumps(
        [_component_signature(component) for component in components],
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


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


@dataclass(frozen=True, slots=True)
class StabilizerDatum:
    datum_id: str
    center_xyz_mm: tuple[float, float, float]
    role: str
    geometry_status: str

    def manifest(self) -> dict[str, object]:
        return {
            "datum_id": self.datum_id,
            "center_xyz_mm": [float(value) for value in self.center_xyz_mm],
            "role": self.role,
            "geometry_status": self.geometry_status,
        }


@dataclass(frozen=True, slots=True)
class StabilizerPart:
    part_id: str
    side: str
    role: str
    solid: cq.Workplane
    geometry_status: str

    def __post_init__(self) -> None:
        _single(self.solid, self.part_id)
        if self.side not in {"WEARER_LEFT", "WEARER_RIGHT"}:
            raise OccipitalStabilizerError("stabilizer side must use controlled wearer-relative vocabulary")

    def manifest(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "side": self.side,
            "role": self.role,
            "bounds_mm": list(_bbox(self.solid)),
            "volume_mm3": round(float(self.solid.val().Volume()), 6),
            "geometry_status": self.geometry_status,
            "material": None,
            "mass_g": None,
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
class OccipitalStabilizer:
    source_model_sha256: str
    source_waste_release_sha256: str
    left: StabilizerPart
    right: StabilizerPart
    central_rear_package_keepout: cq.Workplane
    crown_support_corridor: cq.Workplane
    root_capture_bores: tuple[cq.Workplane, cq.Workplane]
    datums: tuple[StabilizerDatum, ...]
    collision_checks: tuple[CollisionCheck, ...]

    def __post_init__(self) -> None:
        for solid, label in (
            (self.central_rear_package_keepout, "central rear package keepout"),
            (self.crown_support_corridor, "crown support corridor"),
        ):
            _single(solid, label)
        if any(not check.passes for check in self.collision_checks):
            failed = tuple(check.check_id for check in self.collision_checks if not check.passes)
            raise OccipitalStabilizerError(f"required occipital clearance failed: {failed}")

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
            "source_model_sha256": self.source_model_sha256,
            "source_waste_release_sha256": self.source_waste_release_sha256,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "source_frame_retention_reservation_id": RESERVATION_RETENTION,
            "functional_separation": {
                "facial_reaction": "FRONT_STRUCTURAL_REACTION_LOOP_UNCHANGED_BY_THIS_INCREMENT",
                "occipital_stabilization": "PAIRED_LATERAL_FORK_YOKES_REALIZED",
                "crown_support": "SEPARATE_SUPERIOR_CORRIDOR_RESERVED_NO_CROWN_MEMBER_REALIZED_HERE",
                "functions_conflated_into_single_halo_ring": False,
            },
            "parts": [self.left.manifest(), self.right.manifest()],
            "datums": [datum.manifest() for datum in self.datums],
            "root_capture_interface": {
                "positive_capture_bore_realized": True,
                "bore_radius_mm": ROOT_CAPTURE_BORE_RADIUS_MM,
                "frame_side_pin_or_clevis_realized": False,
                "friction_only_attachment_allowed": False,
                "closure_status": "BLOCKED_PENDING_REALIZED_FRAME_SIDE_POSITIVE_CAPTURE_COUNTERPART",
            },
            "nominal_contact_geometry": {
                "backer_face_z_mm": PAD_CONTACT_FACE_Z_MM,
                "backer_xyz_mm": list(PAD_BACKER_XYZ_MM),
                "contact_layer_material": None,
                "preload_N": None,
                "fit_range_mm": None,
                "hair_interaction": "UNVALIDATED",
                "headform_status": "NO_REPRESENTATIVE_3D_HEADFORM_AUTHORITY;NOMINAL_DIGITAL_BACKER_PLACEMENT_ONLY",
            },
            "central_rear_package_keepout": {
                "bounds_mm": list(_bbox(self.central_rear_package_keepout)),
                "role": "PROVISIONAL_REAR_PACKAGING_WINDOW_NOT_SELECTED_ELECTRONICS_HARDWARE",
                "minimum_lateral_gap_to_occipital_material_mm": min(
                    abs(_bbox(self.left.solid)[1] - _bbox(self.central_rear_package_keepout)[0]),
                    abs(_bbox(self.right.solid)[0] - _bbox(self.central_rear_package_keepout)[1]),
                ),
            },
            "crown_support_corridor": {
                "bounds_mm": list(_bbox(self.crown_support_corridor)),
                "physical_member_realized": False,
                "role": "RESERVED_SEPARATE_VERTICAL_SUPPORT_PATH",
            },
            "collision_checks": [check.manifest() for check in self.collision_checks],
            "four_zone_actuation_preserved": True,
            "visual_intent": "TWO_LATERAL_REAR_YOKES_NO_CENTRAL_HELMET_RING_NO_EXTERNAL_ROUND_PODS",
            "physical_validation_eligible": False,
            "unresolved_physical_gates": [
                "OCCIPITAL_CONTACT_PRESSURE_FIT_COMFORT_PRELOAD_AND_HAIR_INTERACTION",
                "OCCIPITAL_YOKE_MATERIAL_STRENGTH_STIFFNESS_FATIGUE_AND_IMPACT",
                "ROOT_CAPTURE_COUNTERPART_ASSEMBLY_AND_BEARING_STRENGTH",
                "CROWN_SUPPORT_MEMBER_AND_VERTICAL_LOAD_SHARE",
                "RETENTION_ANTHROPOMETRIC_RANGE_AND_WHOLE_HEAD_REMOVAL",
                "EMERGENCY_RELEASE_FORCE_5_TO_12_N_AND_TIME_LE_2_S",
            ],
            "evidence_status": DIGITAL_ONLY,
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def _build_yoke(side_sign: int, frame_width_mm: float) -> tuple[StabilizerPart, cq.Workplane, tuple[float, float, float]]:
    if side_sign not in {-1, 1}:
        raise OccipitalStabilizerError("side sign must be -1 or +1")
    root_x = side_sign * (frame_width_mm / 2.0 - ROOT_X_INSET_FROM_FRAME_SIDE_MM)
    root = (root_x, ROOT_Y_MM, ROOT_Z_MM)
    upper = (side_sign * RAIL_END_X_MM, RAIL_UPPER_Y_MM, RAIL_END_Z_MM)
    lower = (side_sign * RAIL_END_X_MM, RAIL_LOWER_Y_MM, RAIL_END_Z_MM)
    pad_center = (side_sign * PAD_CENTER_X_MM, PAD_CENTER_Y_MM, PAD_CENTER_Z_MM)

    root_boss = _box(ROOT_BOSS_XYZ_MM, root)
    pad = _rounded_pad(pad_center)
    upper_rail = _capsule_between(root, upper, RAIL_RADIUS_MM)
    lower_rail = _capsule_between(root, lower, RAIL_RADIUS_MM)
    raw = _single(root_boss.union(upper_rail).union(lower_rail).union(pad), "connected occipital yoke")
    bore = _cylinder(
        ROOT_CAPTURE_BORE_RADIUS_MM,
        ROOT_CAPTURE_BORE_LENGTH_MM,
        root,
        (0.0, 1.0, 0.0),
    )
    final = _single(raw.cut(bore), "bored occipital yoke")
    if _intersection_mm3(final, bore) != 0.0:
        raise OccipitalStabilizerError("root positive-capture bore is not fully open")

    side = "WEARER_RIGHT" if side_sign > 0 else "WEARER_LEFT"
    part = StabilizerPart(
        f"OCCIPITAL_STABILIZER_{'RIGHT' if side_sign > 0 else 'LEFT'}_YOKE",
        side,
        "lateral occipital contact-backer carrier with forked reaction link and positive-capture root bore",
        final,
        "CELL3_PROVISIONAL_OCCIPITAL_GEOMETRY_MATERIAL_AND_FIT_UNVALIDATED",
    )
    return part, bore, root


def build_occipital_stabilizer(
    authority: Authority | None = None,
    model: MasckOneModel | None = None,
) -> OccipitalStabilizer:
    authority = authority or load_authority()
    canonical = build_model(authority)
    model = model or canonical

    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise OccipitalStabilizerError("occipital geometry is stale for current authority revision")
    if str(authority.get("coordinate_system", "x_positive")) != "wearer_right":
        raise OccipitalStabilizerError("authority X axis no longer matches wearer-right convention")
    if str(authority.get("coordinate_system", "y_positive")) != "superior":
        raise OccipitalStabilizerError("authority Y axis no longer matches superior convention")
    if str(authority.get("coordinate_system", "z_positive")) != "anterior":
        raise OccipitalStabilizerError("authority Z axis no longer matches anterior convention")
    if int(authority.number("actuation", "count")) != 4 or len(model.actuator_envelopes) != 4:
        raise OccipitalStabilizerError("four independently controllable actuation zones must be preserved")

    canonical_sha = _source_model_sha(canonical)
    model_sha = _source_model_sha(model)
    if model_sha != canonical_sha:
        raise OccipitalStabilizerError("supplied model does not match current-main canonical package geometry")

    frame_width, _ = authority.pair("geometry", "functional_frame_xy_mm")
    left, left_bore, left_root = _build_yoke(-1, frame_width)
    right, right_bore, right_root = _build_yoke(+1, frame_width)
    central_keepout = _single(
        _box(CENTRAL_REAR_PACKAGE_KEEP_OUT_XYZ_MM, CENTRAL_REAR_PACKAGE_KEEP_OUT_CENTER_MM),
        "central rear package keepout",
    )
    crown_corridor = _single(
        _box(CROWN_SUPPORT_CORRIDOR_XYZ_MM, CROWN_SUPPORT_CORRIDOR_CENTER_MM),
        "crown support corridor",
    )

    checks: list[CollisionCheck] = []

    def add(check_id: str, obstacle_id: str, moving: cq.Workplane, obstacle: cq.Workplane) -> None:
        checks.append(CollisionCheck(check_id, obstacle_id, _intersection_mm3(moving, obstacle)))

    for part in (left, right):
        add(f"CLEAR_{part.part_id}_CENTRAL_REAR_PACKAGE", "CENTRAL_REAR_PACKAGE_KEEP_OUT", part.solid, central_keepout)
        add(f"CLEAR_{part.part_id}_CROWN_CORRIDOR", "CROWN_SUPPORT_CORRIDOR", part.solid, crown_corridor)
        for component in (
            model.shell,
            *model.actuator_envelopes,
            model.water_reservoir_envelope,
            model.waste_cartridge_envelope,
            model.battery_reference_envelope,
        ):
            add(f"CLEAR_{part.part_id}_{component.name.upper()}", component.name.upper(), part.solid, component.solid)
        for index in range(len(model.protected_volumes.all)):
            zone_id, protected = _protected_solid(model, index)
            add(f"CLEAR_{part.part_id}_{zone_id}", zone_id, part.solid, protected)

    add("CLEAR_LEFT_RIGHT_OCCIPITAL_YOKES", right.part_id, left.solid, right.solid)

    waste_release = build_current_cell4_waste_backbone_release()
    for route in waste_release.realization.routes:
        route_bound = _route_service_aabb(route)
        for part in (left, right):
            add(
                f"CLEAR_{part.part_id}_{route.route_id}_SERVICE_AABB",
                f"{route.route_id}_SERVICE_AABB",
                part.solid,
                route_bound,
            )

    datums = (
        StabilizerDatum("OCCIPITAL_ROOT_LEFT", left_root, "future frame-side positive-capture root", "ACTUAL_YOKE_BORE_FRAME_COUNTERPART_UNRESOLVED"),
        StabilizerDatum("OCCIPITAL_ROOT_RIGHT", right_root, "future frame-side positive-capture root", "ACTUAL_YOKE_BORE_FRAME_COUNTERPART_UNRESOLVED"),
        StabilizerDatum("OCCIPITAL_CONTACT_BACKER_LEFT", (-PAD_CENTER_X_MM, PAD_CENTER_Y_MM, PAD_CONTACT_FACE_Z_MM), "nominal wearer-facing backer plane center", "NOMINAL_DIGITAL_CONTACT_BACKER_NOT_FIT_EVIDENCE"),
        StabilizerDatum("OCCIPITAL_CONTACT_BACKER_RIGHT", (PAD_CENTER_X_MM, PAD_CENTER_Y_MM, PAD_CONTACT_FACE_Z_MM), "nominal wearer-facing backer plane center", "NOMINAL_DIGITAL_CONTACT_BACKER_NOT_FIT_EVIDENCE"),
        StabilizerDatum("CROWN_SUPPORT_INTERFACE_LEFT", (-RAIL_END_X_MM, 58.0, -47.0), "separate future crown-support handoff", "RESERVATION_ONLY_NO_CROWN_MEMBER"),
        StabilizerDatum("CROWN_SUPPORT_INTERFACE_RIGHT", (RAIL_END_X_MM, 58.0, -47.0), "separate future crown-support handoff", "RESERVATION_ONLY_NO_CROWN_MEMBER"),
        StabilizerDatum("FACIAL_REACTION_REFERENCE", (0.0, 0.0, 0.0), "front structural reaction system remains independent", "REFERENCE_ONLY_NO_GEOMETRY_CHANGE"),
    )

    result = OccipitalStabilizer(
        source_model_sha256=model_sha,
        source_waste_release_sha256=waste_release.manifest_sha256,
        left=left,
        right=right,
        central_rear_package_keepout=central_keepout,
        crown_support_corridor=crown_corridor,
        root_capture_bores=(left_bore, right_bore),
        datums=datums,
        collision_checks=tuple(checks),
    )

    central_bounds = _bbox(central_keepout)
    left_bounds = _bbox(left.solid)
    right_bounds = _bbox(right.solid)
    if central_bounds[0] < left_bounds[1] or central_bounds[1] > right_bounds[0]:
        raise OccipitalStabilizerError("central packaging window lost bilateral lateral separation")
    if right_bounds[0] - central_bounds[1] < 8.0 or central_bounds[0] - left_bounds[1] < 8.0:
        raise OccipitalStabilizerError("occipital material must preserve at least 8 mm lateral package-window margin")
    return result


def export_occipital_stabilizer(
    output_dir: str | Path,
    stabilizer: OccipitalStabilizer,
) -> tuple[Path, ...]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    solids = (
        ("occipital_stabilizer_left_yoke.step", stabilizer.left.solid),
        ("occipital_stabilizer_right_yoke.step", stabilizer.right.solid),
        ("occipital_central_rear_package_keepout_reference.step", stabilizer.central_rear_package_keepout),
        ("occipital_crown_support_corridor_reference.step", stabilizer.crown_support_corridor),
    )
    for name, solid in solids:
        _single(solid, name)
        path = root / name
        cq.exporters.export(solid, str(path))
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"failed to export {name}")
        outputs.append(path)

    manifest_path = root / "occipital_stabilizer_manifest.json"
    manifest_path.write_text(
        json.dumps(stabilizer.manifest(), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    outputs.append(manifest_path)
    return tuple(outputs)
