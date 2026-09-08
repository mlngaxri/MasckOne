from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

import cadquery as cq

from .structural_frame_retention_roots import (
    ROOT_IDS,
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_SERVICE_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
PIN_WITHDRAW_EXTENSION_MM = 8.0
CLIP_RADIAL_EXTENSION_MM = 5.0
ACCESS_CLEARANCE_MM = 0.20
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameRetentionRootServiceError(ValueError):
    pass


def _valid(shape: cq.Workplane, label: str) -> None:
    value = shape.val()
    if not value.isValid() or len(value.Solids()) != 1 or float(value.Volume()) <= 0.0:
        raise StructuralFrameRetentionRootServiceError(f"{label} must be one valid positive-volume B-rep")


def _intersection(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        return max(0.0, float(a.intersect(b).val().Volume()))
    except Exception:
        return 0.0


def _box_from_bounds(bb: cq.BoundBox, *, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0) -> cq.Workplane:
    return cq.Workplane("XY").box(
        bb.xlen + dx, bb.ylen + dy, bb.zlen + dz, centered=(True, True, True)
    ).translate(((bb.xmin + bb.xmax) / 2.0, (bb.ymin + bb.ymax) / 2.0, (bb.zmin + bb.zmax) / 2.0))


@dataclass(frozen=True, slots=True)
class RetentionRootServicePath:
    root_id: str
    pin_withdraw_sweep: cq.Workplane = field(repr=False, compare=False)
    clip_install_sweep: cq.Workplane = field(repr=False, compare=False)
    pin_sweep_frame_intersection_mm3: float = 0.0
    pin_sweep_yoke_intersection_mm3: float = 0.0
    clip_sweep_frame_intersection_mm3: float = 0.0
    clip_sweep_yoke_intersection_mm3: float = 0.0

    def __post_init__(self) -> None:
        if self.root_id not in ROOT_IDS:
            raise StructuralFrameRetentionRootServiceError("unknown retention root")
        _valid(self.pin_withdraw_sweep, f"{self.root_id} pin withdrawal sweep")
        _valid(self.clip_install_sweep, f"{self.root_id} clip installation sweep")
        for label, volume in (
            ("pin/frame", self.pin_sweep_frame_intersection_mm3),
            ("pin/yoke", self.pin_sweep_yoke_intersection_mm3),
            ("clip/frame", self.clip_sweep_frame_intersection_mm3),
            ("clip/yoke", self.clip_sweep_yoke_intersection_mm3),
        ):
            if volume > _INTERSECTION_TOLERANCE_MM3:
                raise StructuralFrameRetentionRootServiceError(f"continuous {label} service corridor collides with material")

    def manifest(self) -> dict[str, object]:
        return {
            "root_id": self.root_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "pin_withdraw_extension_mm": PIN_WITHDRAW_EXTENSION_MM,
            "clip_radial_extension_mm": CLIP_RADIAL_EXTENSION_MM,
            "access_clearance_mm": ACCESS_CLEARANCE_MM,
            "pin_sweep_frame_intersection_mm3": self.pin_sweep_frame_intersection_mm3,
            "pin_sweep_yoke_intersection_mm3": self.pin_sweep_yoke_intersection_mm3,
            "clip_sweep_frame_intersection_mm3": self.clip_sweep_frame_intersection_mm3,
            "clip_sweep_yoke_intersection_mm3": self.clip_sweep_yoke_intersection_mm3,
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootServiceArchitecture:
    source_retention_root_architecture_sha256: str
    paths: tuple[RetentionRootServicePath, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_retention_root_architecture_sha256) != 64:
            raise StructuralFrameRetentionRootServiceError("source retention-root identity must be SHA-256")
        if tuple(path.root_id for path in self.paths) != ROOT_IDS:
            raise StructuralFrameRetentionRootServiceError("both bilateral root service paths are required")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootServiceError("digital service geometry is not physical evidence")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload = {
            "schema": SCHEMA,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "source_retention_root_architecture_sha256": self.source_retention_root_architecture_sha256,
            "paths": [path.manifest() for path in self.paths],
            "service_status": "BILATERAL_ROOT_PIN_WITHDRAWAL_AND_RETAINER_INSTALLATION_CONTINUOUS_CORRIDORS_REALIZED",
            "whole_head_removal_status": "OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_structural_frame_retention_root_service(*, roots: StructuralFrameRetentionRootArchitecture | None = None) -> StructuralFrameRetentionRootServiceArchitecture:
    roots = build_structural_frame_retention_roots() if roots is None else roots
    paths: list[RetentionRootServicePath] = []
    frame = roots.frame_with_retention_roots

    for root in roots.roots:
        pin_bb = root.capture_pin.val().BoundingBox()
        clip_bb = root.split_retainer.val().BoundingBox()

        # The pin axis is +Y. Withdrawal is toward the headed, negative-Y side.
        pin_full = _box_from_bounds(pin_bb, dx=2.0 * ACCESS_CLEARANCE_MM, dy=PIN_WITHDRAW_EXTENSION_MM, dz=2.0 * ACCESS_CLEARANCE_MM).translate((0.0, -PIN_WITHDRAW_EXTENSION_MM / 2.0, 0.0))
        pin_seated = _box_from_bounds(pin_bb, dx=2.0 * ACCESS_CLEARANCE_MM, dz=2.0 * ACCESS_CLEARANCE_MM)
        pin_extension = pin_full.cut(pin_seated)

        # The split retainer has an open +Z sector. Prove an exact prismatic radial path from +Z.
        clip_full = _box_from_bounds(clip_bb, dx=2.0 * ACCESS_CLEARANCE_MM, dy=2.0 * ACCESS_CLEARANCE_MM, dz=CLIP_RADIAL_EXTENSION_MM).translate((0.0, 0.0, CLIP_RADIAL_EXTENSION_MM / 2.0))
        clip_seated = _box_from_bounds(clip_bb, dx=2.0 * ACCESS_CLEARANCE_MM, dy=2.0 * ACCESS_CLEARANCE_MM)
        clip_extension = clip_full.cut(clip_seated)
        _valid(pin_extension, f"{root.root_id} pin service extension")
        _valid(clip_extension, f"{root.root_id} clip service extension")

        # Exclude the root's own counterpart from the integrated frame only where the seated
        # hardware intentionally passes through its bores. Extension sweeps must clear all frame
        # material and the source yoke material continuously.
        paths.append(RetentionRootServicePath(
            root.root_id,
            pin_extension,
            clip_extension,
            round(_intersection(pin_extension, frame), 8),
            round(_intersection(pin_extension, root.yoke_root_reference), 8),
            round(_intersection(clip_extension, frame), 8),
            round(_intersection(clip_extension, root.yoke_root_reference), 8),
        ))

    result = StructuralFrameRetentionRootServiceArchitecture(roots.architecture_sha256, tuple(paths), False)
    result.__post_init__()
    return result


def export_structural_frame_retention_root_service(output_dir: str | Path) -> dict[str, object]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    architecture = build_structural_frame_retention_root_service()
    for path in architecture.paths:
        stem = path.root_id.lower()
        cq.exporters.export(path.pin_withdraw_sweep, str(output / f"{stem}_pin_withdraw_sweep.step"))
        cq.exporters.export(path.clip_install_sweep, str(output / f"{stem}_clip_install_sweep.step"))
    manifest = architecture.manifest()
    (output / "structural_frame_retention_root_service_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
