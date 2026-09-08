from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math

import cadquery as cq

from .model import MasckOneModel, build_model
from .structural_frame_realization import (
    StructuralFrameRealization,
    build_structural_frame_realization,
)


SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_SHELL_JOINTS_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
JOINT_IDS = (
    "FRAME_SHELL_JOINT_SUPERIOR_LEFT",
    "FRAME_SHELL_JOINT_SUPERIOR_RIGHT",
    "FRAME_SHELL_JOINT_INFERIOR_LEFT",
    "FRAME_SHELL_JOINT_INFERIOR_RIGHT",
)

# Digital closure seeds only. They define a deterministic removable positive joint for
# the current CAD baseline and are not production tolerances, process capability, or a
# released fastener specification.
TENON_WIDTH_MM = 7.0
TENON_HEIGHT_MM = 6.0
TENON_FRAME_EMBED_MM = 1.0
TENON_SHELL_INSERT_MM = 3.0
MORTISE_CLEARANCE_MM = 0.15
PIN_DIAMETER_MM = 1.8
PIN_BORE_DIAMETER_MM = 2.0
PIN_HEAD_DIAMETER_MM = 3.4
PIN_HEAD_THICKNESS_MM = 0.8
PIN_OVERHANG_MM = 0.7
JOINT_X_FRACTION = 0.36
JOINT_Y_FRACTION = 0.31

_INTERSECTION_TOLERANCE_MM3 = 1e-7
_DISTANCE_TOLERANCE_MM = 1e-6


class StructuralFrameShellJointError(ValueError):
    pass


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StructuralFrameShellJointError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise StructuralFrameShellJointError(f"{label} must be finite")
    return number


def _volume(shape: cq.Workplane) -> float:
    return max(0.0, float(shape.val().Volume()))


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        return max(0.0, float(a.intersect(b).val().Volume()))
    except Exception:
        return 0.0


def _distance(a: cq.Workplane, b: cq.Workplane) -> float:
    return max(0.0, float(a.val().distance(b.val())))


def _valid_single_solid(shape: cq.Workplane, label: str) -> None:
    value = shape.val()
    if not value.isValid() or len(value.Solids()) != 1 or _volume(shape) <= 0.0:
        raise StructuralFrameShellJointError(f"{label} must be one valid positive-volume B-rep solid")


@dataclass(frozen=True, slots=True)
class ShellJoint:
    joint_id: str
    center_xy_mm: tuple[float, float]
    tenon: cq.Workplane = field(repr=False, compare=False)
    mortise_tool: cq.Workplane = field(repr=False, compare=False)
    pin: cq.Workplane = field(repr=False, compare=False)
    pin_bore_tool: cq.Workplane = field(repr=False, compare=False)
    frame_tenon_union: cq.Workplane = field(repr=False, compare=False)
    shell_with_mortise_and_pin_bore: cq.Workplane = field(repr=False, compare=False)
    frame_capture_volume_mm3: float
    shell_socket_removed_volume_mm3: float
    nominal_tenon_shell_intersection_mm3: float
    nominal_pin_frame_intersection_mm3: float
    nominal_pin_shell_intersection_mm3: float

    def __post_init__(self) -> None:
        if self.joint_id not in JOINT_IDS:
            raise StructuralFrameShellJointError(f"unknown shell joint {self.joint_id!r}")
        if len(self.center_xy_mm) != 2 or not all(math.isfinite(float(v)) for v in self.center_xy_mm):
            raise StructuralFrameShellJointError("joint center must be finite XY")
        for label, shape in (
            ("tenon", self.tenon),
            ("mortise tool", self.mortise_tool),
            ("capture pin", self.pin),
            ("pin bore", self.pin_bore_tool),
            ("frame with tenon", self.frame_tenon_union),
            ("shell counterpart", self.shell_with_mortise_and_pin_bore),
        ):
            _valid_single_solid(shape, label)
        if _finite(self.frame_capture_volume_mm3, "frame capture volume") <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameShellJointError("tenon must have positive integral capture into the frame")
        if _finite(self.shell_socket_removed_volume_mm3, "shell socket removed volume") <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameShellJointError("mortise must remove real shell material")
        if _finite(self.nominal_tenon_shell_intersection_mm3, "tenon shell intersection") > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameShellJointError("nominal tenon must not collide with the cut shell counterpart")
        if _finite(self.nominal_pin_frame_intersection_mm3, "pin frame intersection") > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameShellJointError("capture pin must clear the frame-side bore")
        if _finite(self.nominal_pin_shell_intersection_mm3, "pin shell intersection") > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameShellJointError("capture pin must clear the shell-side bore")

    def manifest(self) -> dict[str, object]:
        return {
            "joint_id": self.joint_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xy_mm": list(self.center_xy_mm),
            "interface_semantics": "POSITIVE_TENON_MORTISE_WITH_REMOVABLE_TRANSVERSE_CAPTURE_PIN",
            "assembly_sequence": [
                "translate frame tenon into shell mortise along +Z",
                "insert transverse headed capture pin after mortise seating",
                "remove capture pin before frame separation",
                "translate frame away from shell along -Z",
            ],
            "geometry_seed_status": "DIGITAL_MVP_CLOSURE_SEEDS_NOT_PRODUCTION_TOLERANCE_OR_FASTENER_RELEASE",
            "dimensions_mm": {
                "tenon_width": TENON_WIDTH_MM,
                "tenon_height": TENON_HEIGHT_MM,
                "tenon_frame_embed": TENON_FRAME_EMBED_MM,
                "tenon_shell_insert": TENON_SHELL_INSERT_MM,
                "mortise_clearance": MORTISE_CLEARANCE_MM,
                "pin_diameter": PIN_DIAMETER_MM,
                "pin_bore_diameter": PIN_BORE_DIAMETER_MM,
                "pin_head_diameter": PIN_HEAD_DIAMETER_MM,
                "pin_head_thickness": PIN_HEAD_THICKNESS_MM,
            },
            "measured": {
                "frame_capture_volume_mm3": self.frame_capture_volume_mm3,
                "shell_socket_removed_volume_mm3": self.shell_socket_removed_volume_mm3,
                "nominal_tenon_shell_intersection_mm3": self.nominal_tenon_shell_intersection_mm3,
                "nominal_pin_frame_intersection_mm3": self.nominal_pin_frame_intersection_mm3,
                "nominal_pin_shell_intersection_mm3": self.nominal_pin_shell_intersection_mm3,
            },
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameShellJointArchitecture:
    source_frame_geometry_sha256: str
    source_shell_status: str
    joints: tuple[ShellJoint, ...]
    assembled_frame: cq.Workplane = field(repr=False, compare=False)
    modified_shell: cq.Workplane = field(repr=False, compare=False)
    frame_shell_nominal_intersection_mm3: float
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_frame_geometry_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.source_frame_geometry_sha256):
            raise StructuralFrameShellJointError("source frame geometry identity must be canonical SHA-256")
        if not isinstance(self.source_shell_status, str) or not self.source_shell_status.strip():
            raise StructuralFrameShellJointError("source shell status must be explicit")
        if tuple(j.joint_id for j in self.joints) != JOINT_IDS:
            raise StructuralFrameShellJointError("all four shell joints must exist in controlled order")
        _valid_single_solid(self.assembled_frame, "four-joint frame")
        _valid_single_solid(self.modified_shell, "four-joint shell counterpart")
        if self.frame_shell_nominal_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameShellJointError("assembled frame and modified shell have forbidden nominal material collision")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameShellJointError("digital joint geometry is not physical validation evidence")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_frame_geometry_sha256": self.source_frame_geometry_sha256,
            "source_shell_status": self.source_shell_status,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "joint_count": len(self.joints),
            "joints": [joint.manifest() for joint in self.joints],
            "frame_shell_nominal_intersection_mm3": self.frame_shell_nominal_intersection_mm3,
            "service_status": "REMOVABLE_AFTER_FOUR_CAPTURE_PINS_ARE_WITHDRAWN",
            "load_path_status": "POSITIVE_GEOMETRIC_COUNTERPARTS_REALIZED_STRENGTH_AND_FATIGUE_NOT_VALIDATED",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def _joint_centers(model: MasckOneModel) -> tuple[tuple[float, float], ...]:
    outer_w, outer_h = (float(v) for v in model.authority.pair("geometry", "outer_xy_envelope_mm"))
    x = outer_w * JOINT_X_FRACTION
    y = outer_h * JOINT_Y_FRACTION
    return ((-x, y), (x, y), (-x, -y), (x, -y))


def _box_at(center_x: float, center_y: float, z_center: float, width: float, height: float, depth: float) -> cq.Workplane:
    return cq.Workplane("XY").box(width, height, depth, centered=(True, True, True)).translate((center_x, center_y, z_center))


def _pin_geometry(center_x: float, center_y: float, z_center: float, length: float) -> tuple[cq.Workplane, cq.Workplane]:
    # Pins run along X for the left/right symmetric joint pairs. The shaft is captured
    # by heads on both ends; each head extrudes away from the joint so the enlarged
    # head never intrudes back into frame or shell material after the shaft bore cut.
    shaft = cq.Workplane("YZ").circle(PIN_DIAMETER_MM / 2.0).extrude(length, both=True).translate((center_x, center_y, z_center))
    head_left = cq.Workplane("YZ").circle(PIN_HEAD_DIAMETER_MM / 2.0).extrude(-PIN_HEAD_THICKNESS_MM).translate((center_x - length, center_y, z_center))
    head_right = cq.Workplane("YZ").circle(PIN_HEAD_DIAMETER_MM / 2.0).extrude(PIN_HEAD_THICKNESS_MM).translate((center_x + length, center_y, z_center))
    pin = shaft.union(head_left).union(head_right)
    bore = cq.Workplane("YZ").circle(PIN_BORE_DIAMETER_MM / 2.0).extrude(length + 2.0 * PIN_OVERHANG_MM, both=True).translate((center_x, center_y, z_center))
    return pin, bore


def build_structural_frame_shell_joints(
    *,
    model: MasckOneModel | None = None,
    frame: StructuralFrameRealization | None = None,
) -> StructuralFrameShellJointArchitecture:
    model = build_model() if model is None else model
    frame = build_structural_frame_realization(model=model) if frame is None else frame
    if type(model) is not MasckOneModel or type(frame) is not StructuralFrameRealization:
        raise StructuralFrameShellJointError("exact model and frame realization types are required")

    frame_shape = frame.solid
    shell_shape = model.shell.solid
    frame_bounds = frame_shape.val().BoundingBox()
    frame_top = float(frame_bounds.zmax)

    assembled_frame = frame_shape
    modified_shell = shell_shape
    joint_records: list[ShellJoint] = []

    for joint_id, (cx, cy) in zip(JOINT_IDS, _joint_centers(model), strict=True):
        tenon_z_min = frame_top - TENON_FRAME_EMBED_MM
        tenon_z_max = frame_top + TENON_SHELL_INSERT_MM
        tenon_depth = tenon_z_max - tenon_z_min
        tenon = _box_at(cx, cy, (tenon_z_min + tenon_z_max) / 2.0, TENON_WIDTH_MM, TENON_HEIGHT_MM, tenon_depth)
        frame_capture = _intersection_volume(frame_shape, tenon)
        if frame_capture <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameShellJointError(f"{joint_id} does not positively embed into the source frame")

        mortise = _box_at(
            cx,
            cy,
            (frame_top + tenon_z_max) / 2.0,
            TENON_WIDTH_MM + 2.0 * MORTISE_CLEARANCE_MM,
            TENON_HEIGHT_MM + 2.0 * MORTISE_CLEARANCE_MM,
            TENON_SHELL_INSERT_MM + 2.0 * MORTISE_CLEARANCE_MM,
        )
        removed = _intersection_volume(modified_shell, mortise)
        if removed <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameShellJointError(f"{joint_id} mortise does not cut current shell material")

        pin_z = frame_top + 0.65 * TENON_SHELL_INSERT_MM
        pin, bore = _pin_geometry(cx, cy, pin_z, TENON_WIDTH_MM / 2.0 + PIN_OVERHANG_MM)

        joint_frame = assembled_frame.union(tenon).cut(bore)
        joint_shell = modified_shell.cut(mortise).cut(bore)
        _valid_single_solid(joint_frame, f"{joint_id} frame union")
        _valid_single_solid(joint_shell, f"{joint_id} shell counterpart")

        record = ShellJoint(
            joint_id=joint_id,
            center_xy_mm=(cx, cy),
            tenon=tenon,
            mortise_tool=mortise,
            pin=pin,
            pin_bore_tool=bore,
            frame_tenon_union=joint_frame,
            shell_with_mortise_and_pin_bore=joint_shell,
            frame_capture_volume_mm3=round(frame_capture, 8),
            shell_socket_removed_volume_mm3=round(removed, 8),
            nominal_tenon_shell_intersection_mm3=round(_intersection_volume(tenon.cut(bore), joint_shell), 8),
            nominal_pin_frame_intersection_mm3=round(_intersection_volume(pin, joint_frame), 8),
            nominal_pin_shell_intersection_mm3=round(_intersection_volume(pin, joint_shell), 8),
        )
        record.__post_init__()
        assembled_frame = joint_frame
        modified_shell = joint_shell
        joint_records.append(record)

    architecture = StructuralFrameShellJointArchitecture(
        source_frame_geometry_sha256=frame.geometry_sha256,
        source_shell_status=model.shell.status,
        joints=tuple(joint_records),
        assembled_frame=assembled_frame,
        modified_shell=modified_shell,
        frame_shell_nominal_intersection_mm3=round(_intersection_volume(assembled_frame, modified_shell), 8),
        physical_validation_eligible=False,
    )
    architecture.__post_init__()
    return architecture
