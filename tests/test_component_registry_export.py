from __future__ import annotations

import json

from masck_one.component_registry import REGISTRY_SCHEMA
from masck_one.export import export_release


def test_release_export_emits_component_registry_manifest(tmp_path) -> None:
    report = export_release(tmp_path)
    emitted = report["component_registry"]

    assert emitted["schema"] == REGISTRY_SCHEMA
    assert len(emitted["registry_sha256"]) == 64
    assert len(emitted["components"]) == 36

    saved = json.loads((tmp_path / "build_report.json").read_text(encoding="utf-8"))
    assert saved["component_registry"] == emitted
