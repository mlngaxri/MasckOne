from __future__ import annotations

import json

import cadquery as cq
import pytest

from masck_one.structural_frame_crown_support import (
    CAPTURE_PIN_RADIUS_MM,
    CROWN_LUG_BORE_RADIUS_MM,
    CROWN_LUG_CENTER_ABS_X_MM,
    CROWN_LUG_CENTER_Y_MM,
    CROWN_LUG_CENTER_Z_MM,
    SOURCE_RETENTION_HEAD_SHA,
    SOURCE_RETENTION_LOAD_PATH_BLOB_SHA,
    StructuralFrameCrownSupportError,
    build_structural_frame_crown_support,
    export_structural_frame_crown_support,
)


def test_bilateral_crown_support_is_positive_source_bound_brep() -> None:
    architecture = build_structural_frame_crown_support()
    assert architecture.crown_support.val().isValid()
    assert len(architecture.crown_support.val().Solids()) == 1
    assert architecture.crown_support.val().Volume() > 0.0
    assert tuple(a.side for a in architecture.attachments) == ("WEARER_LEFT", "WEARER_RIGHT")
    assert tuple(a.lug_center_xyz_mm for a in architecture.attachments) == (
        (-CROWN_LUG_CENTER_ABS_X_MM, CROWN_LUG_CENTER_Y_MM, CROWN_LUG_CENTER_Z_MM),
        (CROWN_LUG_CENTER_ABS_X_MM, CROWN_LUG_CENTER_Y_MM, CROWN_LUG_CENTER_Z_MM),
    )
    assert all(a.pin_bore_radial_clearance_mm == pytest.approx(CROWN_LUG_BORE_RADIUS_MM - CAPTURE_PIN_RADIUS_MM) for a in architecture.attachments)
    assert all(a.eyelet_lug_material_intersection_mm3 == 0.0 for a in architecture.attachments)
    assert all(a.pin_lug_material_intersection_mm3 == 0.0 for a in architecture.attachments)
    assert all(a.protected_intersection_mm3 == 0.0 for a in architecture.attachments)
    manifest = architecture.manifest()
    assert manifest["source_retention_head_sha"] == SOURCE_RETENTION_HEAD_SHA
    assert manifest["source_retention_load_path_blob_sha"] == SOURCE_RETENTION_LOAD_PATH_BLOB_SHA
    assert manifest["load_path_status"] == "BILATERAL_CARRIER_CROWN_LUG_TO_ONE_PIECE_CROWN_SUPPORT_POSITIVE_ATTACHMENT_REALIZED"
    assert manifest["physical_validation_eligible"] is False


def test_hostile_oversized_crown_pin_is_rejected_by_source_lug_material() -> None:
    with pytest.raises(StructuralFrameCrownSupportError, match="source lug bore|source lug material|positive radial clearance|pass through source lug bore"):
        build_structural_frame_crown_support(pin_radius_mm=CROWN_LUG_BORE_RADIUS_MM + 0.20)


def test_crown_export_is_deterministic_and_step_roundtrips(tmp_path) -> None:
    architecture = build_structural_frame_crown_support()
    first = export_structural_frame_crown_support(tmp_path / "a", architecture)
    second = export_structural_frame_crown_support(tmp_path / "b", architecture)
    first_manifest = json.loads((tmp_path / "a" / "structural_frame_crown_support_manifest.json").read_text())
    second_manifest = json.loads((tmp_path / "b" / "structural_frame_crown_support_manifest.json").read_text())
    assert first_manifest == second_manifest
    assert first_manifest["architecture_sha256"] == architecture.architecture_sha256
    assert [p.name for p in first] == [p.name for p in second]

    for path in first:
        if path.suffix.lower() not in {".step", ".stp"}:
            continue
        imported = cq.importers.importStep(str(path))
        assert imported.val().isValid()
        assert imported.val().Volume() > 0.0
