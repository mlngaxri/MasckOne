from __future__ import annotations

import json
from pathlib import Path

from masck_one.export import export_release
from masck_one.service_kinematics_integration import SCHEMA


def test_release_export_embeds_service_kinematics_and_emits_manifest(tmp_path: Path):
    report = export_release(tmp_path)
    manifest_path = tmp_path / "whole_product_service_kinematics_v1.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    embedded = report["integration_ledgers"]["service_kinematics_v1"]
    assert embedded == manifest
    assert manifest["schema"] == SCHEMA
    assert manifest["blocked_motion_count"] == 7
    assert manifest["current_main_motion_geometry_available_count"] == 0
    assert report["exported_integration_files"] == [manifest_path.name]
    assert manifest["physical_validation_eligible"] is False
