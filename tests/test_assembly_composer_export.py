from __future__ import annotations

import json

import cadquery as cq
import pytest

from masck_one.assembly_composer import (
    ASSEMBLY_SCHEMA,
    build_integrated_assembly_skeleton,
)
from masck_one.export import export_release


def test_release_export_emits_authoritative_assembly_skeleton(tmp_path) -> None:
    report = export_release(tmp_path)
    assembly = report["assembly_skeleton"]
    step_path = tmp_path / "masck_one_development_assembly.step"

    assert assembly["schema"] == ASSEMBLY_SCHEMA
    assert assembly["coordinate_frame_id"] == "MASCK_ONE_AUTHORITY_WORLD_MM"
    assert assembly["geometry_summary"]["development_instance_count"] == 9
    assert assembly["geometry_summary"]["reference_keepout_instance_count"] == 5
    assert assembly["physical_validation_eligible"] is False
    assert step_path.is_file()

    saved = json.loads((tmp_path / "build_report.json").read_text(encoding="utf-8"))
    assert saved["assembly_skeleton"] == assembly
    assert "masck_one_development_assembly.step" in saved["exported_step_files"]

    # Directly inspect the generated B-rep after STEP serialization. This is a digital
    # round-trip integrity gate only, not manufacturing or physical validation.
    imported = cq.importers.importStep(str(step_path)).val()
    expected = build_integrated_assembly_skeleton().development_compound()
    assert len(imported.Solids()) == len(expected.Solids()) == 9

    imported_box = imported.BoundingBox()
    expected_box = expected.BoundingBox()
    assert (imported_box.xlen, imported_box.ylen, imported_box.zlen) == pytest.approx(
        (expected_box.xlen, expected_box.ylen, expected_box.zlen),
        abs=1e-6,
    )
