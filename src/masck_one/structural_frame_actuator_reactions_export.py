from __future__ import annotations

import json
from pathlib import Path

import cadquery as cq

from .structural_frame_actuator_reactions import build_structural_frame_actuator_reactions


def export_structural_frame_actuator_reactions(output_dir: str | Path) -> dict[str, object]:
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    architecture = build_structural_frame_actuator_reactions()
    step_name = "structural_frame_with_four_actuator_reaction_counterparts.step"
    manifest_name = "structural_frame_actuator_reactions_manifest.json"

    cq.exporters.export(
        architecture.frame_with_reaction_counterparts,
        str(output / step_name),
    )
    manifest = architecture.manifest()
    with (output / manifest_name).open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")

    return {
        "step_file": step_name,
        "manifest_file": manifest_name,
        "architecture_sha256": architecture.architecture_sha256,
    }
