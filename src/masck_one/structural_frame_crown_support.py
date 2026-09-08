from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from .model import MasckOneModel, build_model
from .structural_frame_realization import _protected_zone_solid
from .structural_frame_retention_roots import (
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_CROWN_SUPPORT_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_RETENTION_PR = 92
SOURCE_RETENTION_HEAD_SHA = "88a88bed01fd3b3acfb38ff5f6f3ae3d5bbf54fe"
SOURCE_RETENTION_LOAD_PATH_BLOB_SHA = "9647405b36642105c929a3fdd0617d03bfe68c98"

CROWN_LUG_CENTER_ABS_X_MM = 60.0
CROWN_LUG_CENTER_Y_MM = 60.0
CROWN_LUG_CENTER_Z_MM = -47.0
CROWN_LUG_XYZ_MM = (8.0, 8.0, 6.0)
CROWN_LUG_BORE_RADIUS_MM = 1.20
CROWN_LUG_BORE_AXIS = "X"

# Digital geometry seeds only. They are not production tolerances, strength values,
# anthropometric fit claims, pressure limits, or physical service evidence.
CROWN_APEX_Y_MM = 96.0
CROWN_APEX_HALF_X_MM = 34.0
CROWN_MEMBER_RADIUS_MM = 2.0
EYELET_X_THICKNESS_MM = 2.0
EYELET_Y_MM = 7.0
EYELET_Z_MM = 6.0
EYELET_LUG_SIDE_GAP_MM = 0.25
CAPTURE_PIN_RADIUS_MM = 1.00
CAPTURE_PIN_HEAD_RADIUS_MM = 1.75
CAPTURE_PIN_HEAD_THICKNESS_MM = 0.90
CAPTURE_PIN_DISTAL_EXTENSION_MM = 2.0
CAPTURE_PIN_GROOVE_DEPTH_MM = 0.25
CAPTURE_PIN_GROOVE_WIDTH_MM = 0.65
CAPTURE_CLIP_RADIAL_THICKNESS_MM = 0.45

_INTERSECTION_TOLERANCE_MM3 = 1e-7
_CLEARANCE_TOLERANCE_MM = 1e-6


class StructuralFrameCrownSupportError(ValueError):
    pass


def _single(shape: cq.Workplane, label: str) -> cq.Workplane:
    value = shape.val()
    if not value.isValid() or len(value.Solids()) != 1 or float(value.Volume()) <= 0.0:
        raise StructuralFrameCrownSupportError(f"{label} must be one valid positive-volume B-rep")
    return shape


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> cq.Workplane:
    return cq.Workplane("XY").box(*size, centered=(True, True, True)).translate(center)


def _cylinder_x(radius: float, length: float, center: tuple[float, float, float]) -> cq.Workplane:
    x, y, z = center
    start = cq.Vector(x - length / 2.0, y, z)
    solid = cq.Solid.makeCylinder(radius, length, start, cq.Vector(1.0, 0.0, 0.0))
    return cq.Workplane("XY").newObject([solid])


def _sphere(radius: float, center: tuple[float, float, float]) -> cq.Workplane:
    return cq.Workplane("XY").newObject([
        cq.Solid.makeSphere(radius, cq.Vector(*center), cq.Vector(0.0, 0.0, 1.0), -90.0, 90.0, 360.0)
    ])


def _capsule(start: tuple[float, float, float], end: tuple[float, float, float], radius: float) -> cq.Workplane:
    dx, dy, dz = (end[i] - start[i] for i in range(3))
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length <= 0.0:
        raise StructuralFrameCrownSupportError("crown capsule endpoints must differ")
    body = cq.Workplane("XY").newObject([
        cq.Solid.makeCylinder(radius, length, cq.Vector(*start), cq.Vector(dx / length, dy / length, dz / length))
    ])
    return _single(body.union(_sphere(radius, start)).union(_sphere(radius, end)), "crown capsule")


def _intersection(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        volume = float(a.intersect(b).val().Volume())
    except Exception:
        return 0.0
    if not math.isfinite(volume) or volume < 0.0:
        raise StructuralFrameCrownSupportError("intersection volume must be finite and nonnegative")
    return 0.0 if volume <= _INTERSECTION_TOLERANCE_MM3 else volume


def _lug_reference(side_sign: float) -> tuple[cq.Workplane, cq.Workplane]:
    center = (side_sign * CROWN_LUG_CENTER_ABS_X_MM, CROWN_LUG_CENTER_Y_MM, CROWN_LUG_CENTER_Z_MM)
    material = _box(CROWN_LUG_XYZ_MM, center)
    bore = _cylinder_x(CROWN_LUG_BORE_RADIUS_MM, CROWN_LUG_XYZ_MM[0] + 2.0, center)
    return _single(material.cut(bore), "source crown lug material reference"), _single(bore, "source crown bore reference")


def _split_clip(center: tuple[float, float, float]) -> cq.Workplane:
    inner = CAPTURE_PIN_RADIUS_MM - CAPTURE_PIN_GROOVE_DEPTH_MM + 0.06
    outer = CAPTURE_PIN_RADIUS_MM + CAPTURE_CLIP_RADIAL_THICKNESS_MM
    ring = _cylinder_x(outer, CAPTURE_PIN_GROOVE_WIDTH_MM, center).cut(
        _cylinder_x(inner, CAPTURE_PIN_GROOVE_WIDTH_MM + 0.2, center)
    )
    split = _box((CAPTURE_PIN_GROOVE_WIDTH_MM + 0.4, outer * 0.9, outer * 2.5), (center[0], center[1] + outer, center[2]))
    return _single(ring.cut(split), "crown capture split clip")


@dataclass(frozen=True, slots=True)
class CrownAttachment:
    side: str
    lug_center_xyz_mm: tuple[float, float, float]
    pin_bore_radial_clearance_mm: float
    eyelet_lug_material_intersection_mm3: float
    pin_lug_material_intersection_mm3: float
    protected_intersection_mm3: float
    eyelet: cq.Workplane = field(repr=False, compare=False)
    capture_pin: cq.Workplane = field(repr=False, compare=False)
    split_retainer: cq.Workplane = field(repr=False, compare=False)
    source_lug_reference: cq.Workplane = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.side not in {"WEARER_LEFT", "WEARER_RIGHT"}:
            raise StructuralFrameCrownSupportError("invalid crown side")
        for label, shape in (("eyelet", self.eyelet), ("capture pin", self.capture_pin), ("split retainer", self.split_retainer), ("source lug", self.source_lug_reference)):
            _single(shape, label)
        if self.pin_bore_radial_clearance_mm <= _CLEARANCE_TOLERANCE_MM:
            raise StructuralFrameCrownSupportError("crown capture pin requires positive radial clearance")
        if self.eyelet_lug_material_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCrownSupportError("crown eyelet must not overlap source lug material")
        if self.pin_lug_material_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCrownSupportError("crown pin must pass through source lug bore, not material")
        if self.protected_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCrownSupportError("crown attachment intersects hard protected envelope")

    def manifest(self) -> dict[str, object]:
        return {
            "side": self.side,
            "lug_center_xyz_mm": list(self.lug_center_xyz_mm),
            "interface_semantics": "SOURCE_LUG_X_AXIS_BORE_TO_SEPARATE_CROWN_EYELET_WITH_POSITIVE_PIN_AND_RADIAL_SPLIT_RETAINER",
            "measured": {
                "pin_bore_radial_clearance_mm": self.pin_bore_radial_clearance_mm,
                "eyelet_lug_material_intersection_mm3": self.eyelet_lug_material_intersection_mm3,
                "pin_lug_material_intersection_mm3": self.pin_lug_material_intersection_mm3,
                "protected_intersection_mm3": self.protected_intersection_mm3,
            },
            "assembly_sequence": [
                "place crown eyelet outboard of source carrier lug with coaxial X-axis bores",
                "insert single-headed capture pin continuously from outboard toward wearer midline",
                "install split retainer radially in distal groove",
                "reverse retainer then pin operations for crown separation",
            ],
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameCrownSupportArchitecture:
    source_retention_root_architecture_sha256: str
    crown_support: cq.Workplane = field(repr=False, compare=False)
    attachments: tuple[CrownAttachment, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_retention_root_architecture_sha256) != 64:
            raise StructuralFrameCrownSupportError("source retention-root architecture SHA-256 is invalid")
        _single(self.crown_support, "crown support member")
        if tuple(a.side for a in self.attachments) != ("WEARER_LEFT", "WEARER_RIGHT"):
            raise StructuralFrameCrownSupportError("bilateral crown attachments required in controlled order")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameCrownSupportError("digital crown geometry is not physical validation evidence")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "source_retention_root_architecture_sha256": self.source_retention_root_architecture_sha256,
            "source_retention_pr": SOURCE_RETENTION_PR,
            "source_retention_head_sha": SOURCE_RETENTION_HEAD_SHA,
            "source_retention_load_path_blob_sha": SOURCE_RETENTION_LOAD_PATH_BLOB_SHA,
            "source_crown_lug_contract": {
                "center_abs_x_mm": CROWN_LUG_CENTER_ABS_X_MM,
                "center_y_mm": CROWN_LUG_CENTER_Y_MM,
                "center_z_mm": CROWN_LUG_CENTER_Z_MM,
                "lug_xyz_mm": list(CROWN_LUG_XYZ_MM),
                "bore_radius_mm": CROWN_LUG_BORE_RADIUS_MM,
                "bore_axis": CROWN_LUG_BORE_AXIS,
            },
            "crown_route_xyz_mm": [
                [-CROWN_LUG_CENTER_ABS_X_MM - CROWN_LUG_XYZ_MM[0] / 2.0 - EYELET_LUG_SIDE_GAP_MM - EYELET_X_THICKNESS_MM / 2.0, CROWN_LUG_CENTER_Y_MM, CROWN_LUG_CENTER_Z_MM],
                [-CROWN_APEX_HALF_X_MM, CROWN_APEX_Y_MM, CROWN_LUG_CENTER_Z_MM],
                [CROWN_APEX_HALF_X_MM, CROWN_APEX_Y_MM, CROWN_LUG_CENTER_Z_MM],
                [CROWN_LUG_CENTER_ABS_X_MM + CROWN_LUG_XYZ_MM[0] / 2.0 + EYELET_LUG_SIDE_GAP_MM + EYELET_X_THICKNESS_MM / 2.0, CROWN_LUG_CENTER_Y_MM, CROWN_LUG_CENTER_Z_MM],
            ],
            "attachments": [a.manifest() for a in self.attachments],
            "load_path_status": "BILATERAL_CARRIER_CROWN_LUG_TO_ONE_PIECE_CROWN_SUPPORT_POSITIVE_ATTACHMENT_REALIZED",
            "service_status": "CROWN_PIN_AND_RETAINER_LOCAL_SEPARATION_REALIZED_WHOLE_HEAD_CONTINUOUS_REMOVAL_OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_structural_frame_crown_support(*, model: MasckOneModel | None = None, roots: StructuralFrameRetentionRootArchitecture | None = None, pin_radius_mm: float = CAPTURE_PIN_RADIUS_MM) -> StructuralFrameCrownSupportArchitecture:
    model = build_model() if model is None else model
    roots = build_structural_frame_retention_roots(model=model) if roots is None else roots
    if type(model) is not MasckOneModel or type(roots) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameCrownSupportError("exact model and retention-root architecture types required")
    if not math.isfinite(pin_radius_mm) or pin_radius_mm <= 0.0:
        raise StructuralFrameCrownSupportError("capture pin radius must be positive")

    attachments: list[CrownAttachment] = []
    eyelets: list[cq.Workplane] = []
    for side, sign in (("WEARER_LEFT", -1.0), ("WEARER_RIGHT", 1.0)):
        lug_center = (sign * CROWN_LUG_CENTER_ABS_X_MM, CROWN_LUG_CENTER_Y_MM, CROWN_LUG_CENTER_Z_MM)
        lug_material, _ = _lug_reference(sign)
        eyelet_center_x = sign * (CROWN_LUG_CENTER_ABS_X_MM + CROWN_LUG_XYZ_MM[0] / 2.0 + EYELET_LUG_SIDE_GAP_MM + EYELET_X_THICKNESS_MM / 2.0)
        eyelet_center = (eyelet_center_x, CROWN_LUG_CENTER_Y_MM, CROWN_LUG_CENTER_Z_MM)
        eyelet = _single(
            _box((EYELET_X_THICKNESS_MM, EYELET_Y_MM, EYELET_Z_MM), eyelet_center).cut(
                _cylinder_x(CROWN_LUG_BORE_RADIUS_MM, EYELET_X_THICKNESS_MM + 1.0, eyelet_center)
            ),
            f"{side} crown eyelet",
        )

        stack = CROWN_LUG_XYZ_MM[0] + EYELET_LUG_SIDE_GAP_MM + EYELET_X_THICKNESS_MM
        total = stack + CAPTURE_PIN_HEAD_THICKNESS_MM + CAPTURE_PIN_DISTAL_EXTENSION_MM
        pin_center_x = sign * (CROWN_LUG_CENTER_ABS_X_MM + (EYELET_LUG_SIDE_GAP_MM + EYELET_X_THICKNESS_MM - CAPTURE_PIN_DISTAL_EXTENSION_MM + CAPTURE_PIN_HEAD_THICKNESS_MM) / 2.0)
        shaft = _cylinder_x(pin_radius_mm, total - CAPTURE_PIN_HEAD_THICKNESS_MM, (pin_center_x - sign * CAPTURE_PIN_HEAD_THICKNESS_MM / 2.0, CROWN_LUG_CENTER_Y_MM, CROWN_LUG_CENTER_Z_MM))
        head_x = eyelet_center_x + sign * (EYELET_X_THICKNESS_MM / 2.0 + CAPTURE_PIN_HEAD_THICKNESS_MM / 2.0)
        head = _cylinder_x(CAPTURE_PIN_HEAD_RADIUS_MM, CAPTURE_PIN_HEAD_THICKNESS_MM, (head_x, CROWN_LUG_CENTER_Y_MM, CROWN_LUG_CENTER_Z_MM))
        pin = _single(shaft.union(head), f"{side} crown capture pin")
        groove_x = sign * (CROWN_LUG_CENTER_ABS_X_MM - CROWN_LUG_XYZ_MM[0] / 2.0 - CAPTURE_PIN_DISTAL_EXTENSION_MM / 2.0)
        clip = _split_clip((groove_x, CROWN_LUG_CENTER_Y_MM, CROWN_LUG_CENTER_Z_MM))

        protected_intersection = 0.0
        for protected in model.protected_volumes.all:
            protected_solid = _protected_zone_solid(protected)
            protected_intersection += _intersection(eyelet, protected_solid)
            protected_intersection += _intersection(pin, protected_solid)
            protected_intersection += _intersection(clip, protected_solid)

        attachments.append(CrownAttachment(
            side=side,
            lug_center_xyz_mm=lug_center,
            pin_bore_radial_clearance_mm=CROWN_LUG_BORE_RADIUS_MM - pin_radius_mm,
            eyelet_lug_material_intersection_mm3=_intersection(eyelet, lug_material),
            pin_lug_material_intersection_mm3=_intersection(pin, lug_material),
            protected_intersection_mm3=protected_intersection,
            eyelet=eyelet,
            capture_pin=pin,
            split_retainer=clip,
            source_lug_reference=lug_material,
        ))
        eyelets.append(eyelet)

    left_center = (-(CROWN_LUG_CENTER_ABS_X_MM + CROWN_LUG_XYZ_MM[0] / 2.0 + EYELET_LUG_SIDE_GAP_MM + EYELET_X_THICKNESS_MM / 2.0), CROWN_LUG_CENTER_Y_MM, CROWN_LUG_CENTER_Z_MM)
    right_center = (-left_center[0], CROWN_LUG_CENTER_Y_MM, CROWN_LUG_CENTER_Z_MM)
    left_apex = (-CROWN_APEX_HALF_X_MM, CROWN_APEX_Y_MM, CROWN_LUG_CENTER_Z_MM)
    right_apex = (CROWN_APEX_HALF_X_MM, CROWN_APEX_Y_MM, CROWN_LUG_CENTER_Z_MM)
    crown = _single(
        eyelets[0]
        .union(_capsule(left_center, left_apex, CROWN_MEMBER_RADIUS_MM))
        .union(_capsule(left_apex, right_apex, CROWN_MEMBER_RADIUS_MM))
        .union(_capsule(right_apex, right_center, CROWN_MEMBER_RADIUS_MM))
        .union(eyelets[1]),
        "one-piece bilateral crown support",
    )

    for protected in model.protected_volumes.all:
        if _intersection(crown, _protected_zone_solid(protected)) > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCrownSupportError("crown support intersects a hard protected envelope")

    return StructuralFrameCrownSupportArchitecture(
        source_retention_root_architecture_sha256=roots.architecture_sha256,
        crown_support=crown,
        attachments=tuple(attachments),
    )


def export_structural_frame_crown_support(output_dir: str | Path, architecture: StructuralFrameCrownSupportArchitecture | None = None) -> tuple[Path, ...]:
    architecture = build_structural_frame_crown_support() if architecture is None else architecture
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    crown_path = output / "structural_frame_crown_support.step"
    cq.exporters.export(architecture.crown_support, str(crown_path))
    paths.append(crown_path)
    for attachment in architecture.attachments:
        slug = attachment.side.lower()
        for suffix, solid in (("capture_pin", attachment.capture_pin), ("split_retainer", attachment.split_retainer)):
            path = output / f"structural_frame_crown_{slug}_{suffix}.step"
            cq.exporters.export(solid, str(path))
            paths.append(path)
    manifest_path = output / "structural_frame_crown_support_manifest.json"
    manifest_path.write_text(json.dumps(architecture.manifest(), sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    paths.append(manifest_path)
    return tuple(paths)
