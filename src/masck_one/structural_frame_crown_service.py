from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from .structural_frame_crown_support import (
    StructuralFrameCrownSupportArchitecture,
    build_structural_frame_crown_support,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_CROWN_SERVICE_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
PIN_WITHDRAW_EXTENSION_MM = 8.0
CLIP_RADIAL_EXTENSION_MM = 5.0
ACCESS_CLEARANCE_MM = 0.20
_TOL_MM3 = 1e-7


class StructuralFrameCrownServiceError(ValueError):
    pass


def _valid(shape: cq.Workplane, label: str) -> None:
    value = shape.val()
    if not value.isValid() or len(value.Solids()) != 1 or float(value.Volume()) <= 0.0:
        raise StructuralFrameCrownServiceError(f"{label} must be one valid positive-volume B-rep")


def _intersection(a: cq.Workplane, b: cq.Workplane, *, label: str) -> float:
    """Return positive common volume, failing closed if the kernel cannot prove it."""
    try:
        common = a.intersect(b).val()
        if not common.isValid():
            raise StructuralFrameCrownServiceError(f"{label} intersection result is invalid")
        volume = float(common.Volume())
        if not math.isfinite(volume) or volume < 0.0:
            raise StructuralFrameCrownServiceError(
                f"{label} intersection volume must be finite and nonnegative"
            )
        return volume
    except StructuralFrameCrownServiceError:
        raise
    except Exception as exc:
        raise StructuralFrameCrownServiceError(
            f"{label} intersection proof failed; collision-free status cannot be claimed"
        ) from exc


def _box_from_bounds(bb: cq.BoundBox, *, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0) -> cq.Workplane:
    return cq.Workplane("XY").box(bb.xlen + dx, bb.ylen + dy, bb.zlen + dz, centered=(True, True, True)).translate(((bb.xmin + bb.xmax) / 2.0, (bb.ymin + bb.ymax) / 2.0, (bb.zmin + bb.zmax) / 2.0))


@dataclass(frozen=True, slots=True)
class CrownServicePath:
    side: str
    pin_withdraw_sweep: cq.Workplane = field(repr=False, compare=False)
    clip_install_sweep: cq.Workplane = field(repr=False, compare=False)
    pin_sweep_crown_intersection_mm3: float = 0.0
    pin_sweep_lug_intersection_mm3: float = 0.0
    clip_sweep_crown_intersection_mm3: float = 0.0
    clip_sweep_lug_intersection_mm3: float = 0.0

    def __post_init__(self) -> None:
        if self.side not in {"WEARER_LEFT", "WEARER_RIGHT"}:
            raise StructuralFrameCrownServiceError("invalid crown side")
        _valid(self.pin_withdraw_sweep, f"{self.side} pin withdrawal sweep")
        _valid(self.clip_install_sweep, f"{self.side} clip installation sweep")
        measured = (
            self.pin_sweep_crown_intersection_mm3,
            self.pin_sweep_lug_intersection_mm3,
            self.clip_sweep_crown_intersection_mm3,
            self.clip_sweep_lug_intersection_mm3,
        )
        if any(not math.isfinite(v) or v < 0.0 for v in measured):
            raise StructuralFrameCrownServiceError("crown service intersection evidence must be finite and nonnegative")
        if any(v > _TOL_MM3 for v in measured):
            raise StructuralFrameCrownServiceError("continuous crown service corridor collides with material")

    def manifest(self) -> dict[str, object]:
        return {"side": self.side, "coordinate_frame_id": WORLD_FRAME_ID, "pin_withdraw_extension_mm": PIN_WITHDRAW_EXTENSION_MM, "clip_radial_extension_mm": CLIP_RADIAL_EXTENSION_MM, "access_clearance_mm": ACCESS_CLEARANCE_MM, "pin_sweep_crown_intersection_mm3": self.pin_sweep_crown_intersection_mm3, "pin_sweep_lug_intersection_mm3": self.pin_sweep_lug_intersection_mm3, "clip_sweep_crown_intersection_mm3": self.clip_sweep_crown_intersection_mm3, "clip_sweep_lug_intersection_mm3": self.clip_sweep_lug_intersection_mm3}


@dataclass(frozen=True, slots=True)
class StructuralFrameCrownServiceArchitecture:
    source_crown_architecture_sha256: str
    paths: tuple[CrownServicePath, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        source_sha = self.source_crown_architecture_sha256
        if len(source_sha) != 64 or any(c not in "0123456789abcdef" for c in source_sha):
            raise StructuralFrameCrownServiceError("source crown identity must be a lowercase SHA-256 digest")
        if tuple(p.side for p in self.paths) != ("WEARER_LEFT", "WEARER_RIGHT"):
            raise StructuralFrameCrownServiceError("bilateral crown service paths required")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameCrownServiceError("digital service geometry is not physical evidence")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload = {"schema": SCHEMA, "coordinate_frame_id": WORLD_FRAME_ID, "source_crown_architecture_sha256": self.source_crown_architecture_sha256, "paths": [p.manifest() for p in self.paths], "service_status": "BILATERAL_CROWN_PIN_WITHDRAWAL_AND_RETAINER_INSTALLATION_CONTINUOUS_CORRIDORS_REALIZED", "whole_head_removal_status": "OPEN", "physical_validation_eligible": self.physical_validation_eligible}
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_structural_frame_crown_service(*, crown: StructuralFrameCrownSupportArchitecture | None = None) -> StructuralFrameCrownServiceArchitecture:
    crown = build_structural_frame_crown_support() if crown is None else crown
    paths: list[CrownServicePath] = []
    for attachment in crown.attachments:
        sign = -1.0 if attachment.side == "WEARER_LEFT" else 1.0
        pin_bb = attachment.capture_pin.val().BoundingBox()
        clip_bb = attachment.split_retainer.val().BoundingBox()
        pin_full = _box_from_bounds(pin_bb, dx=PIN_WITHDRAW_EXTENSION_MM, dy=2.0 * ACCESS_CLEARANCE_MM, dz=2.0 * ACCESS_CLEARANCE_MM).translate((sign * PIN_WITHDRAW_EXTENSION_MM / 2.0, 0.0, 0.0))
        pin_seated = _box_from_bounds(pin_bb, dy=2.0 * ACCESS_CLEARANCE_MM, dz=2.0 * ACCESS_CLEARANCE_MM)
        pin_extension = pin_full.cut(pin_seated)
        clip_full = _box_from_bounds(clip_bb, dx=2.0 * ACCESS_CLEARANCE_MM, dy=2.0 * ACCESS_CLEARANCE_MM, dz=CLIP_RADIAL_EXTENSION_MM).translate((0.0, 0.0, CLIP_RADIAL_EXTENSION_MM / 2.0))
        clip_seated = _box_from_bounds(clip_bb, dx=2.0 * ACCESS_CLEARANCE_MM, dy=2.0 * ACCESS_CLEARANCE_MM)
        clip_extension = clip_full.cut(clip_seated)
        _valid(pin_extension, f"{attachment.side} pin service extension")
        _valid(clip_extension, f"{attachment.side} clip service extension")
        paths.append(CrownServicePath(
            attachment.side,
            pin_extension,
            clip_extension,
            round(_intersection(pin_extension, crown.crown_support, label=f"{attachment.side} pin/crown"), 8),
            round(_intersection(pin_extension, attachment.source_lug_reference, label=f"{attachment.side} pin/lug"), 8),
            round(_intersection(clip_extension, crown.crown_support, label=f"{attachment.side} clip/crown"), 8),
            round(_intersection(clip_extension, attachment.source_lug_reference, label=f"{attachment.side} clip/lug"), 8),
        ))
    result = StructuralFrameCrownServiceArchitecture(crown.architecture_sha256, tuple(paths), False)
    result.__post_init__()
    return result


def export_structural_frame_crown_service(output_dir: str | Path) -> dict[str, object]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    architecture = build_structural_frame_crown_service()
    for path in architecture.paths:
        stem = path.side.lower()
        cq.exporters.export(path.pin_withdraw_sweep, str(output / f"crown_{stem}_pin_withdraw_sweep.step"))
        cq.exporters.export(path.clip_install_sweep, str(output / f"crown_{stem}_clip_install_sweep.step"))
    manifest = architecture.manifest()
    (output / "structural_frame_crown_service_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest