from pathlib import Path

from masck_one.exterior_evidence import VIEW_DIRECTIONS, render_exterior_view_evidence


def test_multi_view_renderer_emits_actual_brep_views_and_manifest(tmp_path: Path):
    report = render_exterior_view_evidence(tmp_path)
    assert report["shell_valid"] is True
    assert report["shell_volume_mm3"] > 0.0
    assert len(report["view_files"]) == len(VIEW_DIRECTIONS) == 8
    assert (tmp_path / "cell2_exterior_view_manifest.json").exists()
    for filename in report["view_files"]:
        path = tmp_path / filename
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert text.lstrip().startswith("<?xml")
        assert "<svg" in text
        assert len(text) > 500
