from __future__ import annotations

"""Deterministic B-rep view evidence for the Cell 2 exterior candidate."""

from hashlib import sha256
import json
from pathlib import Path

import cadquery as cq

from .integrated_product import build_mvp_product_candidate, integrated_exterior_manifest
from .model import MasckOneModel


VIEW_DIRECTIONS: dict[str, tuple[float, float, float]] = {
    "front": (0.0, 0.0, -1.0),
    "three_quarter_right": (-0.72, 0.0, -1.0),
    "three_quarter_left": (0.72, 0.0, -1.0),
    "right_side": (-1.0, 0.0, 0.0),
    "left_side": (1.0, 0.0, 0.0),
    "rear_wearer_side": (0.0, 0.0, 1.0),
    "top": (0.0, -1.0, 0.0),
    "bottom": (0.0, 1.0, 0.0),
}

SECTION_SPECS: dict[str, tuple[str, tuple[float, float, float]]] = {
    "section_yz_center": ("YZ", (-1.0, 0.0, 0.0)),
    "section_xz_center": ("XZ", (0.0, -1.0, 0.0)),
}


def _render_svg(shape: cq.Shape, projection_dir: tuple[float, float, float]) -> str:
    return cq.exporters.getSVG(
        shape,
        opts={
            "width": 900,
            "height": 900,
            "projectionDir": projection_dir,
            "showAxes": False,
            "showHidden": False,
            "strokeWidth": 0.65,
        },
    )


def _center_section(shape: cq.Shape, plane: str) -> cq.Shape:
    section = cq.Workplane(plane).newObject([shape]).section()
    if section.size() == 0:
        raise ValueError(f"Exterior {plane} center section is empty")
    return section.val()


def render_exterior_view_evidence(
    output_dir: str | Path,
    model: MasckOneModel | None = None,
) -> dict[str, object]:
    """Render actual candidate B-rep projections and return their geometry manifest."""
    candidate = model or build_mvp_product_candidate()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    shape = candidate.shell.solid.val()
    if not shape.isValid() or candidate.shell.solid.solids().size() != 1:
        raise ValueError("Exterior evidence source must be one valid B-rep solid")

    view_files: list[str] = []
    section_files: list[str] = []
    file_sha256: dict[str, str] = {}

    for view_name, projection_dir in VIEW_DIRECTIONS.items():
        svg = _render_svg(shape, projection_dir)
        filename = f"cell2_exterior_{view_name}.svg"
        (output / filename).write_text(svg, encoding="utf-8")
        view_files.append(filename)
        file_sha256[filename] = sha256(svg.encode("utf-8")).hexdigest()

    for view_name, (plane, projection_dir) in SECTION_SPECS.items():
        svg = _render_svg(_center_section(shape, plane), projection_dir)
        filename = f"cell2_exterior_{view_name}.svg"
        (output / filename).write_text(svg, encoding="utf-8")
        section_files.append(filename)
        file_sha256[filename] = sha256(svg.encode("utf-8")).hexdigest()

    bb = shape.BoundingBox()
    report: dict[str, object] = {
        "schema": "MASCK_ONE_CELL2_EXTERIOR_VIEW_EVIDENCE_V2",
        "coordinate_frame": "MASCK_ONE_CANONICAL_WORLD_X_WEARER_RIGHT_Y_SUPERIOR_Z_ANTERIOR",
        "surface": integrated_exterior_manifest(candidate.authority),
        "shell_valid": bool(shape.isValid()),
        "shell_solid_count": int(candidate.shell.solid.solids().size()),
        "shell_volume_mm3": float(shape.Volume()),
        "bounding_box_mm": {
            "x": float(bb.xlen),
            "y": float(bb.ylen),
            "z": float(bb.zlen),
        },
        "view_files": view_files,
        "section_files": section_files,
        "file_sha256": file_sha256,
        "projection_directions": {
            name: list(direction) for name, direction in VIEW_DIRECTIONS.items()
        },
        "section_specs": {
            name: {"plane": plane, "projection_direction": list(direction)}
            for name, (plane, direction) in SECTION_SPECS.items()
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
