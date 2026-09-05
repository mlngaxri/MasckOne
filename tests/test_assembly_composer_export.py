from __future__ import annotations

import json

from masck_one.assembly_composer import ASSEMBLY_SCHEMA
from masck_one.export import export_release


def test_release_export_emits_authoritative_assembly_skeleton(tmp_path) -> None:
    report = export_release(tmp_path)
    assembly = report["assembly_skeleton"]

    assert assembly["schema"] == ASSEMBLY_SCHEMA
    assert assembly["coordinate_frame_id"] == "MASCK_ONE_AUTHORITY_WORLD_MM"
    assert assembly["geometry_summary"]["development_instance_count"] == 9
    assert assembly["geometry_summary"]["reference_keepout_instance_count"] == 5
    assert assembly["physical_validation_eligible"] is False
    assert (tmp_path / "masck_one_development_assembly.step").is_file()

    saved = json.loads((tmp_path / "build_report.json").read_text(encoding="utf-8"))
    assert saved["assembly_skeleton"] == assembly
    assert "masck_one_development_assembly.step" in saved["exported_step_files"]
