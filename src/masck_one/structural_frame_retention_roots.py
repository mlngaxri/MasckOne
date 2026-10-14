from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from .model import MasckOneModel, build_model
from .structural_frame_actuator_reactions import (
    StructuralFrameActuatorReactionArchitecture,
    build_structural_frame_actuator_reactions,
)
from .structural_frame_realization import _protected_zone_solid

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOTS_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_OCCIPITAL_PR = 123
SOURCE_OCCIPITAL_HEAD_SHA = "25686766238b66ecf900009042d721c08e042592"
SOURCE_OCCIPITAL_BLOB_SHA = "1139b675c4758d8580cf5a18fa7a0b87b2d6ef99"

ROOT_IDS = (
    "RETENTION_ROOT_WEARER_LEFT",
    "RETENTION_ROOT_WEARER_RIGHT",
)
ROOT_X_MM = 72.0
ROOT_Y_MM = 10.0
ROOT_Z_MM = -31.0
YOKE_ROOT_BOSS_XYZ_MM = (7.0, 10.0, 6.0)
YOKE_ROOT_BORE_RADIUS_MM = 1.6
YOKE_ROOT_BORE_LENGTH_MM = 14.0

# Digital assembly seeds only. These are not production tolerances, strength values,
# material/process decisions or physical-service evidence.
CLEVIS_SIDE_CLEARANCE_MM = 0.25
CLEVIS_EAR_Y_THICKNESS_MM = 2.0
CLEVIS_EAR_X_MM = 8.0
CLEVIS_EAR_Z_MM = 8.0
CLEVIS_PIN_RADIUS_MM = 1.35
CLEVIS_PIN_HEAD_RADIUS_MM = 2.05
CLEVIS_PIN_HEAD_THICKNESS_MM = 1.0
CLEVIS_PIN_DISTAL_EXTENSION_MM = 2.0
CLEVIS_PIN_GROOVE_DEPTH_MM = 0.35
CLEVIS_PIN_GROOVE_WIDTH_MM = 0.75
CLEVIS_CLIP_RADIAL_THICKNESS_MM = 0.55
FRAME_STEM_X_MM = 8.0
FRAME_STEM_Y_MM = 4.0
FRAME_STEM_OVERLAP_MM = 1.0

_INTERSECTION_TOLERANCE_MM3 = 1e-7
_CLEARANCE_TOLERANCE_MM = 1e-6


class StructuralFrameRetentionRootError(ValueError):
    pass


def _single(shape: cq.Workplane, label: str) -> cq.Workplane:
    value = shape.val()
    if not value.isValid() or len(value.Solids()) != 1 or float(value.Volume()) <= 0.0:
        raise StructuralFrameRetentionRootError(
            f"{label} must be one valid positive-volume B-rep solid"
        )
    return shape


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        volume = float(a.intersect(b).val().Volume())
    except Exception:
        return 0.0
    if not math.isfinite(volume) or volume < 0.0:
        raise StructuralFrameRetentionRootError("intersection volume must be finite and nonnegative")
    return 0.0 if volume <= _INTERSECTION_TOLERANCE_MM3 else volume


def _distance(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        distance = float(a.val().distance(b.val()))
    except Exception as exc:
        raise StructuralFrameRetentionRootError("B-rep clearance query failed") from exc
    if not math.isfinite(distance) or distance < 0.0:
        raise StructuralFrameRetentionRootError("B-rep clearance must be finite and nonnegative")
    return distance


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> cq.Workplane:
    return cq.Workplane("XY").box(*size, centered=(True, True, True)).translate(center)


def _cylinder_y(radius: float, length: float, center: tuple[float, float, float]) -> cq.Workplane:
    x, y, z = center
    start = cq.Vector(x, y - length / 2.0, z)
    solid = cq.Solid.makeCylinder(radius, length, start, cq.Vector(0.0, 1.0, 0.0))
    return cq.Workplane("XY").newObject([solid])


def _yoke_root_reference(side_sign: float) -> tuple[cq.Workplane, cq.Workplane]:
    center = (side_sign * ROOT_X_MM, ROOT_Y_MM, ROOT_Z_MM)
    material = _box(YOKE_ROOT_BOSS_XYZ_MM, center)
    bore = _cylinder_y(YOKE_ROOT_BORE_RADIUS_MM, YOKE_ROOT_BORE_LENGTH_MM, center)
    return _single(material.cut(bore), "yoke root reference material"), _single(bore, "yoke root bore reference")


def _clip_for_pin(
    *,
    center_x: float,
    groove_center_y: float,
    center_z: float,
) -> cq.Workplane:
    inner = CLEVIS_PIN_RADIUS_MM - CLEVIS_PIN_GROOVE_DEPTH_MM
    outer = CLEVIS_PIN_RADIUS_MM + CLEVIS_CLIP_RADIAL_THICKNESS_MM
    full = _cylinder_y(outer, CLEVIS_PIN_GROOVE_WIDTH_MM, (center_x, groove_center_y, center_z))
    hole = _cylinder_y(inner + 0.08, CLEVIS_PIN_GROOVE_WIDTH_MM + 0.2, (center_x, groove_center_y, center_z))
    ring = full.cut(hole)
    # Remove a radial sector to make the retainer independently radially installable.
    split = _box(
        (outer * 2.5, CLEVIS_PIN_GROOVE_WIDTH_MM + 0.4, outer * 0.9),
        (center_x, groove_center_y, center_z + outer),
    )
    return _single(ring.cut(split), "split retention-root pin clip")


@dataclass(frozen=True, slots=True)
class RetentionRootCounterpart:
    root_id: str
    center_xyz_mm: tuple[float, float, float]
    frame_capture_volume_mm3: float
    yoke_material_intersection_mm3: float
    pin_yoke_material_intersection_mm3: float
    protected_intersection_volume_mm3: float
    pin_bore_radial_clearance_mm: float
    frame_counterpart: cq.Workplane = field(repr=False, compare=False)
    capture_pin: cq.Workplane = field(repr=False, compare=False)
    split_retainer: cq.Workplane = field(repr=False, compare=False)
    yoke_root_reference: cq.Workplane = field(repr=False, compare=False)
    yoke_bore_reference: cq.Workplane = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.root_id not in ROOT_IDS:
            raise StructuralFrameRetentionRootError(f"unknown retention root {self.root_id!r}")
        if len(self.center_xyz_mm) != 3 or not all(math.isfinite(float(v)) for v in self.center_xyz_mm):
            raise StructuralFrameRetentionRootError("retention root center must be finite XYZ")
        for label, shape in (
            ("frame retention counterpart", self.frame_counterpart),
            ("retention root capture pin", self.capture_pin),
            ("retention root split retainer", self.split_retainer),
            ("yoke root reference", self.yoke_root_reference),
            ("yoke root bore reference", self.yoke_bore_reference),
        ):
            _single(shape, label)
        if self.frame_capture_volume_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionRootError("retention root counterpart must have positive integral frame capture")
        if self.yoke_material_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionRootError("frame clevis must not intersect nominal yoke root material")
        if self.pin_yoke_material_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionRootError("capture pin must pass through the yoke bore, not yoke material")
        if self.protected_intersection_volume_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionRootError("retention root counterpart intersects a hard protected envelope")
        if self.pin_bore_radial_clearance_mm <= _CLEARANCE_TOLERANCE_MM:
            raise StructuralFrameRetentionRootError("capture pin requires positive radial clearance in yoke bore")

    def manifest(self) -> dict[str, object]:
        return {
            "root_id": self.root_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xyz_mm": list(self.center_xyz_mm),
            "interface_semantics": "FRAME_INTEGRAL_CLEVIS_WITH_TRANSVERSE_POSITIVE_CAPTURE_PIN_AND_RADIAL_SPLIT_RETAINER",
            "mating_contract": {
                "source_pr": SOURCE_OCCIPITAL_PR,
                "source_head_sha": SOURCE_OCCIPITAL_HEAD_SHA,
                "source_occipital_blob_sha": SOURCE_OCCIPITAL_BLOB_SHA,
                "yoke_root_boss_xyz_mm": list(YOKE_ROOT_BOSS_XYZ_MM),
                "yoke_root_bore_radius_mm": YOKE_ROOT_BORE_RADIUS_MM,
                "yoke_root_bore_axis": "+Y",
            },
            "digital_geometry_seeds_mm": {
                "clevis_side_clearance": CLEVIS_SIDE_CLEARANCE_MM,
                "clevis_ear_y_thickness": CLEVIS_EAR_Y_THICKNESS_MM,
                "capture_pin_radius": CLEVIS_PIN_RADIUS_MM,
                "capture_pin_head_radius": CLEVIS_PIN_HEAD_RADIUS_MM,
                "capture_pin_groove_depth": CLEVIS_PIN_GROOVE_DEPTH_MM,
                "capture_pin_groove_width": CLEVIS_PIN_GROOVE_WIDTH_MM,
            },
            "measured": {
                "frame_capture_volume_mm3": self.frame_capture_volume_mm3,
                "yoke_material_intersection_mm3": self.yoke_material_intersection_mm3,
                "pin_yoke_material_intersection_mm3": self.pin_yoke_material_intersection_mm3,
                "protected_intersection_volume_mm3": self.protected_intersection_volume_mm3,
                "pin_bore_radial_clearance_mm": self.pin_bore_radial_clearance_mm,
            },
            "assembly_sequence": [
                "place yoke root between clevis ears",
                "insert single-headed capture pin continuously along +Y through aligned bores",
                "install split retainer radially into distal groove",
                "reverse clip then pin operations for root separation",
            ],
            "physical_validation_eligible": False,
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootArchitecture:
    source_frame_reaction_architecture_sha256: str
    roots: tuple[RetentionRootCounterpart, ...]
    frame_with_retention_roots: cq.Workplane = field(repr=False, compare=False)
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_frame_reaction_architecture_sha256) != 64:
            raise StructuralFrameRetentionRootError("source frame reaction architecture SHA-256 is invalid")
        if tuple(root.root_id for root in self.roots) != ROOT_IDS:
            raise StructuralFrameRetentionRootError("both bilateral retention roots must exist in controlled order")
        _single(self.frame_with_retention_roots, "frame with bilateral retention roots")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootError("digital retention-root geometry is not physical validation evidence")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "source_frame_reaction_architecture_sha256": self.source_frame_reaction_architecture_sha256,
            "source_occipital_pr": SOURCE_OCCIPITAL_PR,
            "source_occipital_head_sha": SOURCE_OCCIPITAL_HEAD_SHA,
            "root_count": len(self.roots),
            "roots": [root.manifest() for root in self.roots],
            "load_path_status": "BILATERAL_POSITIVE_FRAME_TO_YOKE_ROOT_COUNTERPARTS_REALIZED_CROWN_AND_FULL_RETENTION_LOAD_PATH_OPEN",
            "service_status": "ROOT_PIN_INSERTION_AND_LOCAL_SEPARATION_GEOMETRY_REALIZED_WHOLE_HEAD_CONTINUOUS_REMOVAL_OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_structural_frame_retention_roots(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
) -> StructuralFrameRetentionRootArchitecture:
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    if type(model) is not MasckOneModel or type(reactions) is not StructuralFrameActuatorReactionArchitecture:
        raise StructuralFrameRetentionRootError("exact model and frame reaction architecture types are required")

    current_frame = reactions.frame_with_reaction_counterparts
    bb = current_frame.val().BoundingBox()
    frame_z_min = float(bb.zmin)
    frame_z_max = float(bb.zmax)

    roots: list[RetentionRootCounterpart] = []
    for root_id, side_sign in zip(ROOT_IDS, (-1.0, 1.0), strict=True):
        x = side_sign * ROOT_X_MM
        root_center = (x, ROOT_Y_MM, ROOT_Z_MM)
        yoke_material, yoke_bore = _yoke_root_reference(side_sign)

        root_half_y = YOKE_ROOT_BOSS_XYZ_MM[1] / 2.0
        ear_offset = root_half_y + CLEVIS_SIDE_CLEARANCE_MM + CLEVIS_EAR_Y_THICKNESS_MM / 2.0
        ear_centers_y = (ROOT_Y_MM - ear_offset, ROOT_Y_MM + ear_offset)
        ears = [
            _box((CLEVIS_EAR_X_MM, CLEVIS_EAR_Y_THICKNESS_MM, CLEVIS_EAR_Z_MM), (x, ear_y, ROOT_Z_MM))
            for ear_y in ear_centers_y
        ]

        # Close the clevis around the nominal yoke without putting frame material through
        # the yoke boss. Candidate bridges approach from above and below the root; the
        # released counterpart deterministically selects a valid, yoke-clear candidate that
        # positively captures the current source frame. If neither side reaches the frame,
        # geometry remains blocked rather than being represented by disconnected solids.
        bridge_z_thickness = FRAME_STEM_OVERLAP_MM
        bridge_y_span = 2.0 * ear_offset + CLEVIS_EAR_Y_THICKNESS_MM
        candidates: list[tuple[float, float, cq.Workplane, float]] = []
        for approach_sign in (1.0, -1.0):
            bridge_center_z = ROOT_Z_MM + approach_sign * (
                YOKE_ROOT_BOSS_XYZ_MM[2] / 2.0
                + CLEVIS_SIDE_CLEARANCE_MM
                + bridge_z_thickness / 2.0
            )
            bridge = _box(
                (CLEVIS_EAR_X_MM, bridge_y_span, bridge_z_thickness),
                (x, ROOT_Y_MM, bridge_center_z),
            )

            if approach_sign > 0.0:
                stem_z_low = bridge_center_z
                stem_z_high = max(
                    bridge_center_z + bridge_z_thickness / 2.0,
                    frame_z_max + FRAME_STEM_OVERLAP_MM,
                )
            else:
                stem_z_low = min(
                    frame_z_min - FRAME_STEM_OVERLAP_MM,
                    bridge_center_z - bridge_z_thickness / 2.0,
                )
                stem_z_high = bridge_center_z
            stem_depth = stem_z_high - stem_z_low
            if stem_depth <= 0.0:
                continue
            stem_center_z = (stem_z_low + stem_z_high) / 2.0
            stem = _box(
                (FRAME_STEM_X_MM, FRAME_STEM_Y_MM, stem_depth),
                (x, ROOT_Y_MM, stem_center_z),
            )

            try:
                candidate = _single(
                    bridge.union(stem).union(ears[0]).union(ears[1]),
                    f"{root_id} clevis/bridge/stem candidate",
                )
            except StructuralFrameRetentionRootError:
                continue
            yoke_overlap = _intersection_volume(candidate, yoke_material)
            if yoke_overlap > _INTERSECTION_TOLERANCE_MM3:
                continue
            candidate_capture = _intersection_volume(current_frame, candidate)
            if candidate_capture <= _INTERSECTION_TOLERANCE_MM3:
                continue
            candidates.append((candidate_capture, approach_sign, candidate, yoke_overlap))

        if not candidates:
            raise StructuralFrameRetentionRootError(
                f"{root_id} has no connected yoke-clear clevis path that positively captures source frame"
            )
        capture, _approach_sign, local_counterpart, yoke_intersection = max(
            candidates,
            key=lambda item: (item[0], item[1]),
        )

        pin_stack_y = YOKE_ROOT_BOSS_XYZ_MM[1] + 2.0 * (CLEVIS_SIDE_CLEARANCE_MM + CLEVIS_EAR_Y_THICKNESS_MM)
        pin_total_length = pin_stack_y + CLEVIS_PIN_HEAD_THICKNESS_MM + CLEVIS_PIN_DISTAL_EXTENSION_MM
        pin_center_y = ROOT_Y_MM + (CLEVIS_PIN_HEAD_THICKNESS_MM - CLEVIS_PIN_DISTAL_EXTENSION_MM) / 2.0
        shaft = _cylinder_y(CLEVIS_PIN_RADIUS_MM, pin_total_length - CLEVIS_PIN_HEAD_THICKNESS_MM, (x, pin_center_y - CLEVIS_PIN_HEAD_THICKNESS_MM / 2.0, ROOT_Z_MM))
        head_y = ROOT_Y_MM - pin_stack_y / 2.0 - CLEVIS_PIN_HEAD_THICKNESS_MM / 2.0
        head = _cylinder_y(CLEVIS_PIN_HEAD_RADIUS_MM, CLEVIS_PIN_HEAD_THICKNESS_MM, (x, head_y, ROOT_Z_MM))
        raw_pin = _single(shaft.union(head), f"{root_id} raw capture pin")
        distal_y = ROOT_Y_MM + pin_stack_y / 2.0 + CLEVIS_PIN_DISTAL_EXTENSION_MM / 2.0
        groove_center_y = distal_y - CLEVIS_PIN_GROOVE_WIDTH_MM / 2.0
        groove_outer = _cylinder_y(
            CLEVIS_PIN_RADIUS_MM,
            CLEVIS_PIN_GROOVE_WIDTH_MM,
            (x, groove_center_y, ROOT_Z_MM),
        )
        groove_inner = _cylinder_y(
            CLEVIS_PIN_RADIUS_MM - CLEVIS_PIN_GROOVE_DEPTH_MM,
            CLEVIS_PIN_GROOVE_WIDTH_MM + 0.02,
            (x, groove_center_y, ROOT_Z_MM),
        )
        groove_annulus = _single(
            groove_outer.cut(groove_inner),
            f"{root_id} annular capture-pin groove cutter",
        )
        capture_pin = _single(
            raw_pin.cut(groove_annulus),
            f"{root_id} grooved capture pin",
        )
        split_retainer = _clip_for_pin(center_x=x, groove_center_y=groove_center_y, center_z=ROOT_Z_MM)

        pin_yoke_intersection = _intersection_volume(capture_pin, yoke_material)
        pin_bore_clearance = YOKE_ROOT_BORE_RADIUS_MM - CLEVIS_PIN_RADIUS_MM

        protected_intersection = 0.0
        for protected in model.protected_volumes.all:
            zone = protected.zone
            keepout = _protected_zone_solid(
                center_x_mm=zone.center.x,
                center_y_mm=zone.center.y,
                envelope_width_mm=zone.envelope_width_mm,
                envelope_height_mm=zone.envelope_height_mm,
                angle_deg=zone.angle_deg,
                z_min_mm=min(ROOT_Z_MM - 10.0, frame_z_min - 2.0),
                z_max_mm=max(ROOT_Z_MM + 10.0, frame_z_max + 2.0),
            )
            protected_intersection += _intersection_volume(local_counterpart, keepout)

        integrated = _single(current_frame.union(local_counterpart), f"{root_id} integrated frame root")
        root = RetentionRootCounterpart(
            root_id=root_id,
            center_xyz_mm=root_center,
            frame_capture_volume_mm3=round(capture, 8),
            yoke_material_intersection_mm3=round(yoke_intersection, 8),
            pin_yoke_material_intersection_mm3=round(pin_yoke_intersection, 8),
            protected_intersection_volume_mm3=round(protected_intersection, 8),
            pin_bore_radial_clearance_mm=round(pin_bore_clearance, 8),
            frame_counterpart=local_counterpart,
            capture_pin=capture_pin,
            split_retainer=split_retainer,
            yoke_root_reference=yoke_material,
            yoke_bore_reference=yoke_bore,
        )
        root.__post_init__()
        current_frame = integrated
        roots.append(root)

    result = StructuralFrameRetentionRootArchitecture(
        source_frame_reaction_architecture_sha256=reactions.architecture_sha256,
        roots=tuple(roots),
        frame_with_retention_roots=current_frame,
        physical_validation_eligible=False,
    )
    result.__post_init__()
    return result


def export_retention_root_counterparts(output_dir: str | Path) -> dict[str, object]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    architecture = build_structural_frame_retention_roots()
    cq.exporters.export(
        architecture.frame_with_retention_roots,
        str(output / "structural_frame_with_bilateral_retention_roots.step"),
    )
    for root in architecture.roots:
        token = root.root_id.lower()
        cq.exporters.export(root.capture_pin, str(output / f"{token}_capture_pin.step"))
        cq.exporters.export(root.split_retainer, str(output / f"{token}_split_retainer.step"))
    manifest = architecture.manifest()
    manifest_path = output / "structural_frame_retention_roots_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest