from __future__ import annotations

import json

from masck_one.component_registry import REGISTRY_SCHEMA, build_whole_product_component_registry
from masck_one.export import export_release


def test_release_export_emits_exact_component_registry(tmp_path) -> None:
    report = export_release(tmp_path)
    expected = build_whole_product_component_registry().manifest()

    assert report["component_registry"] == expected
    assert report["component_registry"]["schema"] == REGISTRY_SCHEMA
    assert report["component_registry"]["registry_sha256"] == expected["registry_sha256"]

    saved = json.loads((tmp_path / "build_report.json").read_text(encoding="utf-8"))
    assert saved["component_registry"] == expected
    assert len(saved["component_registry"]["components"]) == 36
