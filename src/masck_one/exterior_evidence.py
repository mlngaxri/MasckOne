from __future__ import annotations

"""Deterministic B-rep view evidence for the Cell 2 exterior candidate."""

import json
from pathlib import Path

import cadquery as cq

from .integrated_product import build_mvp_product_candidate, integrated_exterior_manifest
from .model import MasckOneModel


VIEW_DIRECTIONS: dict[str, tuple[float, float, float]] = {
    "front_near_orthographic": (0.0, -0.08, -1.0),
    "three_quarter_right": (-1.0, -0.35, -0.70),
    "three_quarter_left": (1.0, -0.35, -0.70),
    "right_side": (-1.0, 0.0, 0.0),
    "left_side": (1.0, 0.0, 0.0),
    "rear_wearer_side": (0.0, 0.0, 1.0),
    "top": (0.0, -1.0, 0.0),
    "bottom": (0.0, 1.0, 0.0),
}


def render_exterior_view_evidence(
    output_dir: str | Path,
    model: MasckOneModel | None = None,
) -> dict[str, object]:
    """Render actual candidate B-rep projections and return their geometry manifest."""
    candidate = model or build_mvp_product_candidate()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    shape = candidate.shell.solid.val()

    files: list[str] = []
    for view_name, projection_dir in VIEW_DIRECTIONS.items():
        svg = cq.exporters.getSVG(
            shape,
            opts={
                "width": 900,
                "height": 900,
                "projectionDir": projection_dir,
                "showAxes": False,
                "strokeWidth": 0.65,
            },
        )
        filename = f"cell2_exterior_{view_name}.svg"
        (output / filename).write_text(svg, encoding="utf-8")
        files.append(filename)

    bb = shape.BoundingBox()
    report: dict[str, object] = {
        "schema": "MASCK_ONE_CELL2_EXTERIOR_VIEW_EVIDENCE_V1",
        "surface": integrated_exterior_manifest(candidate.authority),
        "shell_valid": bool(shape.isValid()),
        "shell_volume_mm3": float(shape.Volume()),
        "bounding_box_mm": {
            "x": float(bb.xlen),
            "y": float(bb.ylen),
            "z": float(bb.zlen),
        },
        "view_files": files,
        "projection_directions": {
            name: list(direction) for name, direction in VIEW_DIRECTIONS.items()
        },
        "claim_boundary": (
            "Rendered B-rep geometry evidence only; not fit, comfort, seal, cleaning, "
            "material, manufacturing or physical-performance validation."
        ),
    }
    (output / "cell2_exterior_view_manifest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
