from pathlib import Path

import cadquery as cq
import pytest

from masck_one.structural_frame_shell_joint_service import (
    JOINT_IDS,
    StructuralFrameShellJointServiceError,
    build_structural_frame_shell_joint_service,
    export_structural_frame_shell_joint_service,
)


def test_all_shell_joints_have_continuous_collision_free_service_corridors():
    architecture = build_structural_frame_shell_joint_service()
    assert tuple(p.joint_id for p in architecture.paths) == JOINT_IDS
    assert architecture.physical_validation_eligible is False
    for path in architecture.paths:
        assert path.pin_withdraw_sweep.val().isValid()
        assert path.clip_install_sweep.val().isValid()
        assert path.pin_sweep_shell_intersection_mm3 == pytest.approx(0.0, abs=1e-7)
        assert path.clip_sweep_shell_intersection_mm3 == pytest.approx(0.0, abs=1e-7)


def test_hostile_service_collision_is_rejected():
    architecture = build_structural_frame_shell_joint_service()
    path = architecture.paths[0]
    with pytest.raises(StructuralFrameShellJointServiceError):
        type(path)(
            path.joint_id,
            path.pin_withdraw_sweep,
            path.clip_install_sweep,
            0.01,
            path.clip_sweep_shell_intersection_mm3,
        )


def test_service_artifacts_round_trip(tmp_path: Path):
    manifest = export_structural_frame_shell_joint_service(tmp_path)
    assert manifest["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_SHELL_JOINT_SERVICE_V1"
    assert manifest["physical_validation_eligible"] is False
    for joint_id in JOINT_IDS:
        stem = joint_id.lower()
        for suffix in ("pin_withdraw_sweep", "clip_install_sweep"):
            path = tmp_path / f"{stem}_{suffix}.step"
            assert path.exists()
            imported = cq.importers.importStep(str(path))
            assert imported.val().isValid()
            assert float(imported.val().Volume()) > 0.0
