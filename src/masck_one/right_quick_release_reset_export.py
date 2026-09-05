from __future__ import annotations

"""Deterministic release artifacts for the reset-capable Cell 3 right latch successor."""

import json
from pathlib import Path

import cadquery as cq

from .right_quick_release_latch import RELEASE_TRAVEL_MM, RightQuickReleaseLatch
from .right_quick_release_reset import RightQuickReleaseResetMechanics


def _export_step(path: Path, solid: cq.Workplane, label: str) -> Path:
    shape = solid.val()
    if not shape.isValid() or float(shape.Volume()) <= 0.0 or len(shape.Solids()) != 1:
        raise RuntimeError(f"{label} must be one valid positive-volume solid before STEP export")
    cq.exporters.export(solid, str(path))
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"failed to export STEP artifact for {label}")
    return path


def export_right_quick_release_reset(
    output_dir: str | Path,
    latch: RightQuickReleaseLatch,
    reset: RightQuickReleaseResetMechanics,
) -> tuple[Path, ...]:
    if reset.latch.package_sha256 != latch.package_sha256:
        raise RuntimeError("reset package is not bound to the supplied latch package")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    # Release-facing part set. The reset successor replaces only the flexure solid;
    # socket, tongue, guide, slider and withdrawal reservation stay source-bound to #71.
    release_parts = (
        ("right_latch_frame_socket.step", latch.socket.solid, latch.socket.part_id),
        ("right_latch_halo_tongue.step", latch.tongue.solid, latch.tongue.part_id),
        ("right_latch_captive_guide.step", latch.guide_capsule.solid, latch.guide_capsule.part_id),
        (
            "right_latch_flexure_cam_detent.step",
            reset.nominal_flexure.solid,
            reset.nominal_flexure.part_id,
        ),
        ("right_latch_captive_slider.step", latch.slider_and_grip.solid, latch.slider_and_grip.part_id),
        (
            "right_latch_continuous_withdrawal_sweep.step",
            latch.continuous_withdrawal_sweep.solid,
            latch.continuous_withdrawal_sweep.part_id,
        ),
    )
    for filename, solid, label in release_parts:
        paths.append(_export_step(root / filename, solid, label))

    released_slider = latch.slider_and_grip.solid.translate((RELEASE_TRAVEL_MM, 0.0, 0.0))
    paths.append(
        _export_step(
            root / "right_latch_captive_slider_released_state.step",
            released_slider,
            "RELEASED_RESET_REQUIRED slider state",
        )
    )

    for filename, part in (
        ("right_latch_reset_flexure_lifted.step", reset.lifted_flexure),
        ("right_latch_reset_deformation_envelope.step", reset.deformation_envelope),
        ("right_latch_reset_low_offset_translation_sweep.step", reset.low_offset_translation_sweep),
        ("right_latch_reset_high_offset_translation_sweep.step", reset.high_offset_translation_sweep),
    ):
        paths.append(_export_step(root / filename, part.solid, part.part_id))

    source_manifest = root / "right_quick_release_latch_manifest.json"
    source_manifest.write_text(
        json.dumps(latch.manifest(), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    paths.append(source_manifest)

    reset_manifest = root / "right_quick_release_reset_manifest.json"
    reset_manifest.write_text(
        json.dumps(reset.manifest(), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    paths.append(reset_manifest)
    return tuple(paths)
