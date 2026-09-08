from __future__ import annotations

import json

import cadquery as cq
import pytest

from masck_one.structural_frame_retention_roots import (
    CLEVIS_PIN_RADIUS_MM,
    ROOT_IDS,
    SOURCE_OCCIPITAL_HEAD_SHA,
    YOKE_ROOT_BORE_RADIUS_MM,
    StructuralFrameRetentionRootError,
    build_structural_frame_retention_roots,
    export_retention_root_counterparts,
)


def _intersection_mm3(a: cq.Workplane, b: cq.Workplane) -> float:
    return max(0.0, float(a.intersect(b).val().Volume()))


def test_bilateral_retention_roots_are_positive_source_bound_breps() -> None:
    architecture = build_structural_frame_retention_roots()
    assert tuple(root.root_id for root in architecture.roots) == ROOT_IDS
    assert len(architecture.source_frame_reaction_architecture_sha256) == 64
    assert architecture.physical_validation_eligible is False
    assert architecture.frame_with_retention_roots.val().isValid()
    assert len(architecture.frame_with_retention_roots.val().Solids()) == 1

    for root in architecture.roots:
        assert root.frame_capture_volume_mm3 > 0.0
        assert root.yoke_material_intersection_mm3 == 0.0
        assert root.pin_yoke_material_intersection_mm3 == 0.0
        assert root.protected_intersection_volume_mm3 == 0.0
        assert root.pin_bore_radial_clearance_mm == pytest.approx(
            YOKE_ROOT_BORE_RADIUS_MM - CLEVIS_PIN_RADIUS_MM,
            abs=1e-12,
        )
        assert root.capture_pin.val().isValid()
        assert root.split_retainer.val().isValid()

    manifest = architecture.manifest()
    assert manifest["source_occipital_pr"] == 123
    assert manifest["source_occipital_head_sha"] == SOURCE_OCCIPITAL_HEAD_SHA
    assert "CROWN" in manifest["load_path_status"]
    assert manifest["physical_validation_eligible"] is False


def test_retention_root_pin_cannot_be_relabelled_as_overlap_attachment() -> None:
    architecture = build_structural_frame_retention_roots()
    for root in architecture.roots:
        assert _intersection_mm3(root.capture_pin, root.yoke_root_reference) <= 1e-7
        assert "POSITIVE_CAPTURE_PIN" in root.manifest()["interface_semantics"]


def test_hostile_oversize_pin_regresses_yoke_bore_clearance() -> None:
    architecture = build_structural_frame_retention_roots()
    root = architecture.roots[0]
    x, y, z = root.center_xyz_mm
    hostile_radius = YOKE_ROOT_BORE_RADIUS_MM + 0.10
    hostile = cq.Workplane("YZ").workplane(offset=x).center(y, z).circle(hostile_radius).extrude(14.0)
    # The hostile construction is intentionally not the released pin. It must consume
    # yoke-root reference material and therefore demonstrates that the nominal zero-
    # material-intersection criterion detects loss of bore clearance.
    assert _intersection_mm3(hostile, root.yoke_root_reference) > 1e-7


def test_retention_root_export_is_deterministic_and_roundtrips(tmp_path) -> None:
    first = export_retention_root_counterparts(tmp_path / "a")
    second = export_retention_root_counterparts(tmp_path / "b")
    assert first == second

    manifest_path = tmp_path / "a" / "structural_frame_retention_roots_manifest.json"
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == first

    step_path = tmp_path / "a" / "structural_frame_with_bilateral_retention_roots.step"
    imported = cq.importers.importStep(str(step_path))
    assert imported.val().isValid()
    assert len(imported.val().Solids()) == 1
    assert float(imported.val().Volume()) > 0.0

    for root_id in ROOT_IDS:
        token = root_id.lower()
        assert (tmp_path / "a" / f"{token}_capture_pin.step").is_file()
        assert (tmp_path / "a" / f"{token}_split_retainer.step").is_file()


def test_invalid_source_architecture_type_is_rejected() -> None:
    with pytest.raises(StructuralFrameRetentionRootError):
        build_structural_frame_retention_roots(reactions=object())  # type: ignore[arg-type]
