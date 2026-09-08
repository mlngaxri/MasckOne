from __future__ import annotations

import json

import cadquery as cq
import pytest

from masck_one.structural_frame_crown_service import (
    StructuralFrameCrownServiceError,
    build_structural_frame_crown_service,
    export_structural_frame_crown_service,
)


def test_bilateral_crown_service_corridors_are_positive_and_collision_free() -> None:
    architecture = build_structural_frame_crown_service()
    assert tuple(path.side for path in architecture.paths) == ("WEARER_LEFT", "WEARER_RIGHT")
    for path in architecture.paths:
        for sweep in (path.pin_withdraw_sweep, path.clip_install_sweep):
            assert sweep.val().isValid()
            assert len(sweep.val().Solids()) == 1
            assert sweep.val().Volume() > 0.0
        assert path.pin_sweep_crown_intersection_mm3 == 0.0
        assert path.pin_sweep_lug_intersection_mm3 == 0.0
        assert path.clip_sweep_crown_intersection_mm3 == 0.0
        assert path.clip_sweep_lug_intersection_mm3 == 0.0


def test_hostile_crown_service_collision_is_rejected() -> None:
    architecture = build_structural_frame_crown_service()
    path = architecture.paths[0]
    with pytest.raises(StructuralFrameCrownServiceError, match="collides with material"):
        type(path)(path.side, path.pin_withdraw_sweep, path.clip_install_sweep, pin_sweep_crown_intersection_mm3=0.01)


def test_crown_service_export_is_deterministic_and_roundtrips(tmp_path) -> None:
    first = export_structural_frame_crown_service(tmp_path / "a")
    second = export_structural_frame_crown_service(tmp_path / "b")
    assert first == second
    assert first["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_CROWN_SERVICE_V1"
    assert first["whole_head_removal_status"] == "OPEN"
    assert json.loads((tmp_path / "a" / "structural_frame_crown_service_manifest.json").read_text()) == first
    for side in ("wearer_left", "wearer_right"):
        for suffix in ("pin_withdraw_sweep", "clip_install_sweep"):
            step = tmp_path / "a" / f"crown_{side}_{suffix}.step"
            assert step.exists() and step.stat().st_size > 0
            imported = cq.importers.importStep(str(step)).val()
            assert imported.isValid()
            assert imported.Volume() > 0.0
