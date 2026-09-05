from __future__ import annotations

"""Deterministic B-rep view evidence for the Cell 2 MVP exterior candidate."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cadquery as cq
from cadquery import exporters

from .exterior_surface import exterior_surface_manifest
from .integrated_product import build_mvp_product_candidate


VIEW_PROJECTIONS: tuple[tuple[str, tuple[float, float, float]], ...] = (
    ("front", (0.0, 0.0, -1.0)),
    ("front_three_quarter_right", (-0.72, 0.0, -1.0)),
    ("front_three_quarter_left", (0.72, 0.0, -1.0)),
    ("right", (-1.0, 0.0, 0.0)),
    ("left", (1.0, 0.0, 0.0)),
    ("rear", (0.0, 0.0, 1.0)),
    ("top", (0.0, -1.0, 0.0)),
    ("bottom", (0.0, 1.0, 0.0)),
)

SECTION_SPECS: tuple[tuple[str, str, tuple[float, float, float]], ...] = (
    ("section_yz_center", "YZ", (-1.0, 0.0, 0.0)),
    ("section_xz_center", "XZ", (0.0, -1.0, 0.0)),
)

EVIDENCE_STATUS = "DIGITAL_BREP_PROJECTION_ONLY_NOT_PHYSICAL_APPEARANCE_FIT_OR_MANUFACTURING_EVIDENCE"


def _svg(shape: cq.Shape, projection: tuple[float, float, float]) -> str:
    return exporters.getSVG(
        shape,
        {
            "width": 720,
            "height": 720,
            "marginLeft": 24,
            "marginTop": 24,
            "projectionDir": projection,
            "showAxes": False,
            "showHidden": False,
            "strokeWidth": 1.0,
        },
    )


def _section(shape: cq.Shape, plane: str) -> cq.Shape:
    section = cq.Workplane(plane).newObject([shape]).section()
    if section.size() == 0:
        raise ValueError(f"Exterior {plane} center section is empty")
    return section.val()


def generate_exterior_multiview(output_dir: str | Path) -> dict[str, object]:
    """Render actual exterior-candidate B-rep views and return a digest-bound manifest."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    model = build_mvp_product_candidate()
    shape = model.shell.solid.val()
    if not shape.isValid() or model.shell.solid.solids().size() != 1:
        raise ValueError("Multiview source must be one valid exterior B-rep solid")

    files: list[dict[str, object]] = []
    for view_id, projection in VIEW_PROJECTIONS:
        svg = _svg(shape, projection)
        filename = f"{view_id}.svg"
        (output / filename).write_text(svg, encoding="utf-8")
        files.append(
            {
                "view_id": view_id,
                "kind": "ORTHOGRAPHIC_BREP_PROJECTION",
                "projection_dir": list(projection),
                "file": filename,
                "sha256": sha256(svg.encode("utf-8")).hexdigest(),
            }
        )

    for view_id, plane, projection in SECTION_SPECS:
        svg = _svg(_section(shape, plane), projection)
        filename = f"{view_id}.svg"
        (output / filename).write_text(svg, encoding="utf-8")
        files.append(
            {
                "view_id": view_id,
                "kind": "CENTER_SECTION_BREP_PROJECTION",
                "section_plane": plane,
                "projection_dir": list(projection),
                "file": filename,
                "sha256": sha256(svg.encode("utf-8")).hexdigest(),
            }
        )

    manifest = {
        "schema": "MASCK_ONE_CELL2_EXTERIOR_MULTIVIEW_V1",
        "coordinate_frame": "MASCK_ONE_CANONICAL_WORLD_X_WEARER_RIGHT_Y_SUPERIOR_Z_ANTERIOR",
        "source": "build_mvp_product_candidate().shell",
        "views": files,
        "exterior_surface": exterior_surface_manifest(model.authority),
        "evidence_status": EVIDENCE_STATUS,
        "physical_validation_eligible": False,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Cell 2 actual-CAD exterior multiview evidence")
    parser.add_argument("--output", default="generated/cell2-exterior-multiview")
    args = parser.parse_args(argv)
    generate_exterior_multiview(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
