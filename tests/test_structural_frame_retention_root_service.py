from __future__ import annotations

import json
import math

import cadquery as cq
import pytest

from masck_one.structural_frame_retention_root_service import (
    ROOT_IDS,
    StructuralFrameRetentionRootServiceError,
    _intersection,
    build_structural_frame_retention_root_service,
    export_structural_frame_retention_root_service,
)


def test_bilateral_retention_root_service_corridors_are_positive_and_collision_free() -> None:
    architecture = build_structural_frame_retention_root_service()
    assert tuple(path.root_id for path in architecture.paths) == ROOT_IDS
    for path in architecture.paths:
        for sweep in (path.pin_withdraw_sweep, path.clip_install_sweep):
            assert sweep.val().isValid()
            assert len(sweep.val().Solids()) == 1
            assert sweep.val().Volume() > 0.0
        assert path.pin_sweep_frame_intersection_mm3 == 0.0
        assert path.pin_sweep_yoke_intersection_mm3 == 0.0
        assert path.clip_sweep_frame_intersection_mm3 == 0.0
        assert path.clip_sweep_yoke_intersection_mm3 == 0.0


def test_hostile_service_collision_is_rejected() -> None:
    architecture = build_structural_frame_retention_root_service()
    path = architecture.paths[0]
    with pytest.raises(StructuralFrameRetentionRootServiceError, match="collides with material"):
        type(path)(
            path.root_id,
            path.pin_withdraw_sweep,
            path.clip_install_sweep,
            pin_sweep_frame_intersection_mm3=0.01,
        )


def test_non_finite_or_negative_service_evidence_is_rejected() -> None:
    architecture = build_structural_frame_retention_root_service()
    path = architecture.paths[0]
    for hostile in (math.nan, math.inf, -0.01):
        with pytest.raises(StructuralFrameRetentionRootServiceError, match="finite and non-negative"):
            type(path)(
                path.root_id,
                path.pin_withdraw_sweep,
                path.clip_install_sweep,
                pin_sweep_frame_intersection_mm3=hostile,
            )


def test_boolean_failure_cannot_be_relabelled_as_zero_clearance_evidence(monkeypatch) -> None:
    architecture = build_structural_frame_retention_root_service()
    sweep = architecture.paths[0].pin_withdraw_sweep

    def fail_boolean(*args, **kwargs):
        raise RuntimeError("synthetic OCC failure")

    monkeypatch.setattr(cq.Workplane, "intersect", fail_boolean)
    with pytest.raises(StructuralFrameRetentionRootServiceError, match="Boolean failed"):
        _intersection(sweep, sweep)


def test_bilateral_service_corridor_drift_is_rejected() -> None:
    architecture = build_structural_frame_retention_root_service()
    left, right = architecture.paths

    shifted_right = type(right)(
        right.root_id,
        right.pin_withdraw_sweep.translate((0.01, 0.0, 0.0)),
        right.clip_install_sweep,
        right.pin_sweep_frame_intersection_mm3,
        right.pin_sweep_yoke_intersection_mm3,
        right.clip_sweep_frame_intersection_mm3,
        right.clip_sweep_yoke_intersection_mm3,
    )
    with pytest.raises(StructuralFrameRetentionRootServiceError, match="mirror registered"):
        type(architecture)(
            architecture.source_retention_root_architecture_sha256,
            (left, shifted_right),
            False,
        )


def test_bilateral_service_corridor_size_asymmetry_is_rejected() -> None:
    architecture = build_structural_frame_retention_root_service()
    left, right = architecture.paths
    clip_bb = right.clip_install_sweep.val().BoundingBox()
    oversized_clip = cq.Workplane("XY").box(
        clip_bb.xlen + 0.01,
        clip_bb.ylen,
        clip_bb.zlen,
        centered=(True, True, True),
    ).translate(((clip_bb.xmin + clip_bb.xmax) / 2.0, (clip_bb.ymin + clip_bb.ymax) / 2.0, (clip_bb.zmin + clip_bb.zmax) / 2.0))

    hostile_right = type(right)(
        right.root_id,
        right.pin_withdraw_sweep,
        oversized_clip,
        right.pin_sweep_frame_intersection_mm3,
        right.pin_sweep_yoke_intersection_mm3,
        right.clip_sweep_frame_intersection_mm3,
        right.clip_sweep_yoke_intersection_mm3,
    )
    with pytest.raises(StructuralFrameRetentionRootServiceError, match="mirror registered"):
        type(architecture)(
            architecture.source_retention_root_architecture_sha256,
            (left, hostile_right),
            False,
        )


def test_retention_root_service_export_is_deterministic_and_roundtrips(tmp_path) -> None:
    first = export_structural_frame_retention_root_service(tmp_path / "a")
    second = export_structural_frame_retention_root_service(tmp_path / "b")
    assert first == second
    assert first["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_SERVICE_V1"
    assert first["whole_head_removal_status"] == "OPEN"
    assert json.loads((tmp_path / "a" / "structural_frame_retention_root_service_manifest.json").read_text()) == first

    for root_id in ROOT_IDS:
        stem = root_id.lower()
        for suffix in ("pin_withdraw_sweep", "clip_install_sweep"):
            step = tmp_path / "a" / f"{stem}_{suffix}.step"
            assert step.exists() and step.stat().st_size > 0
            imported = cq.importers.importStep(str(step)).val()
            assert imported.isValid()
            assert imported.Volume() > 0.0
