from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json

import cadquery as cq

from .structural_frame_shell_joints import (
    JOINT_IDS,
    StructuralFrameShellJointArchitecture,
    build_structural_frame_shell_joints,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_SHELL_JOINT_SERVICE_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
PIN_WITHDRAW_EXTENSION_MM = 8.0
CLIP_RADIAL_EXTENSION_MM = 5.0
ACCESS_CLEARANCE_MM = 0.20
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameShellJointServiceError(ValueError):
    pass


def _valid(shape: cq.Workplane, label: str) -> None:
    value = shape.val()
    if not value.isValid() or len(value.Solids()) != 1 or float(value.Volume()) <= 0.0:
        raise StructuralFrameShellJointServiceError(f"{label} must be one valid positive-volume B-rep")


def _intersection(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        return max(0.0, float(a.intersect(b).val().Volume()))
    except Exception:
        return 0.0


@dataclass(frozen=True, slots=True)
class ShellJointServicePath:
    joint_id: str
    pin_withdraw_sweep: cq.Workplane = field(repr=False, compare=False)
    clip_install_sweep: cq.Workplane = field(repr=False, compare=False)
    pin_sweep_shell_intersection_mm3: float = 0.0
    clip_sweep_shell_intersection_mm3: float = 0.0

    def __post_init__(self) -> None:
        if self.joint_id not in JOINT_IDS:
            raise StructuralFrameShellJointServiceError("unknown shell joint")
        _valid(self.pin_withdraw_sweep, f"{self.joint_id} pin sweep")
        _valid(self.clip_install_sweep, f"{self.joint_id} clip sweep")
        if self.pin_sweep_shell_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameShellJointServiceError("continuous pin withdrawal corridor intersects shell material")
        if self.clip_sweep_shell_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameShellJointServiceError("continuous retainer installation corridor intersects shell material")

    def manifest(self) -> dict[str, object]:
        return {
            "joint_id": self.joint_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "pin_withdraw_extension_mm": PIN_WITHDRAW_EXTENSION_MM,
            "clip_radial_extension_mm": CLIP_RADIAL_EXTENSION_MM,
            "access_clearance_mm": ACCESS_CLEARANCE_MM,
            "pin_sweep_shell_intersection_mm3": self.pin_sweep_shell_intersection_mm3,
            "clip_sweep_shell_intersection_mm3": self.clip_sweep_shell_intersection_mm3,
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameShellJointServiceArchitecture:
    source_shell_joint_architecture_sha256: str
    paths: tuple[ShellJointServicePath, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_shell_joint_architecture_sha256) != 64:
            raise StructuralFrameShellJointServiceError("source shell-joint identity must be SHA-256")
        if tuple(p.joint_id for p in self.paths) != JOINT_IDS:
            raise StructuralFrameShellJointServiceError("all four service paths must exist in controlled order")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameShellJointServiceError("digital service geometry is not physical evidence")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload = {
            "schema": SCHEMA,
            "source_shell_joint_architecture_sha256": self.source_shell_joint_architecture_sha256,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "paths": [p.manifest() for p in self.paths],
            "service_status": "CONTINUOUS_PIN_WITHDRAWAL_AND_RADIAL_RETAINER_ACCESS_CORRIDORS_REALIZED",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def _expanded_box(bb: cq.BoundBox, dx: float, dy: float, dz: float) -> cq.Workplane:
    return cq.Workplane("XY").box(
        bb.xlen + dx,
        bb.ylen + dy,
        bb.zlen + dz,
        centered=(True, True, True),
    ).translate(((bb.xmin + bb.xmax) / 2.0, (bb.ymin + bb.ymax) / 2.0, (bb.zmin + bb.zmax) / 2.0))


def build_structural_frame_shell_joint_service(*, joints: StructuralFrameShellJointArchitecture | None = None) -> StructuralFrameShellJointServiceArchitecture:
    joints = build_structural_frame_shell_joints() if joints is None else joints
    paths: list[ShellJointServicePath] = []
    shell = joints.modified_shell
    for joint in joints.joints:
        pin_bb = joint.pin.val().BoundingBox()
        clip_bb = joint.retainer_clip.val().BoundingBox()

        # Exact prismatic swept volume for withdrawal from the pin-head side.
        pin_sweep = _expanded_box(pin_bb, PIN_WITHDRAW_EXTENSION_MM, 2.0 * ACCESS_CLEARANCE_MM, 2.0 * ACCESS_CLEARANCE_MM)
        pin_sweep = pin_sweep.translate((-PIN_WITHDRAW_EXTENSION_MM / 2.0, 0.0, 0.0))

        # Exact prismatic radial corridor from the open clip slot side to the seated clip.
        clip_sweep = _expanded_box(clip_bb, 2.0 * ACCESS_CLEARANCE_MM, CLIP_RADIAL_EXTENSION_MM, 2.0 * ACCESS_CLEARANCE_MM)
        clip_sweep = clip_sweep.translate((0.0, CLIP_RADIAL_EXTENSION_MM / 2.0, 0.0))

        # The seated hardware occupies intentional shell bores. Test only the extension beyond
        # the nominal hardware bounding box so intended bore occupancy is not mislabeled collision.
        pin_extension = pin_sweep.cut(_expanded_box(pin_bb, 0.0, 2.0 * ACCESS_CLEARANCE_MM, 2.0 * ACCESS_CLEARANCE_MM))
        clip_extension = clip_sweep.cut(_expanded_box(clip_bb, 2.0 * ACCESS_CLEARANCE_MM, 0.0, 2.0 * ACCESS_CLEARANCE_MM))
        _valid(pin_extension, f"{joint.joint_id} pin extension sweep")
        _valid(clip_extension, f"{joint.joint_id} clip extension sweep")
        paths.append(ShellJointServicePath(
            joint.joint_id,
            pin_extension,
            clip_extension,
            round(_intersection(pin_extension, shell), 8),
            round(_intersection(clip_extension, shell), 8),
        ))
    result = StructuralFrameShellJointServiceArchitecture(joints.architecture_sha256, tuple(paths), False)
    result.__post_init__()
    return result


def export_structural_frame_shell_joint_service(output_dir) -> dict[str, object]:
    from pathlib import Path
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_structural_frame_shell_joint_service()
    for path in architecture.paths:
        stem = path.joint_id.lower()
        cq.exporters.export(path.pin_withdraw_sweep, str(output_dir / f"{stem}_pin_withdraw_sweep.step"))
        cq.exporters.export(path.clip_install_sweep, str(output_dir / f"{stem}_clip_install_sweep.step"))
    manifest = architecture.manifest()
    (output_dir / "structural_frame_shell_joint_service_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
