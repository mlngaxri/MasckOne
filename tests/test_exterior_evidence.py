from pathlib import Path

from masck_one.exterior_evidence import (
    SECTION_SPECS,
    VIEW_DIRECTIONS,
    render_exterior_view_evidence,
)


def test_multi_view_renderer_emits_actual_brep_views_sections_and_manifest(tmp_path: Path):
    report = render_exterior_view_evidence(tmp_path)
    assert report["schema"] == "MASCK_ONE_CELL2_EXTERIOR_VIEW_EVIDENCE_V3"
    assert report["coordinate_frame"] == "MASCK_ONE_AUTHORITY_WORLD_MM"
    assert report["shell_valid"] is True
    assert report["shell_solid_count"] == 1
    assert report["shell_volume_mm3"] > 0.0
    assert report["visible_assembly_valid"] is True
    assert report["visible_assembly_solid_count"] == 2
    assert report["visible_assembly_volume_mm3"] > report["shell_volume_mm3"]
    assert report["rear_service_skin"]["current_cell3_package_interface"]["package_reflow_required"] is True
    assert len(report["view_files"]) == len(VIEW_DIRECTIONS) == 8
    assert len(report["section_files"]) == len(SECTION_SPECS) == 2
    assert (tmp_path / "cell2_exterior_view_manifest.json").exists()
    generated = report["view_files"] + report["section_files"]
    assert set(report["file_sha256"]) == set(generated)
    for filename in generated:
        path = tmp_path / filename
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert text.lstrip().startswith("<?xml")
        assert "<svg" in text
        assert len(text) > 500
        assert len(report["file_sha256"][filename]) == 64


def test_view_registry_covers_required_aesthetic_baseline():
    assert tuple(VIEW_DIRECTIONS) == (
        "front",
        "three_quarter_right",
        "three_quarter_left",
        "right_side",
        "left_side",
        "rear_wearer_side",
        "top",
        "bottom",
    )
    assert tuple(SECTION_SPECS) == (
        "section_yz_center",
        "section_xz_center",
    )
