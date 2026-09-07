from __future__ import annotations

import json

import cadquery as cq
import pytest

from masck_one.model import build_model
from masck_one.structural_frame_realization import build_structural_frame_realization
from masck_one.structural_frame_shell_joints import (
    JOINT_IDS,
    PIN_BORE_DIAMETER_MM,
    PIN_DIAMETER_MM,
    StructuralFrameShellJointError,
    build_structural_frame_shell_joints,
)


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        return max(0.0, float(a.intersect(b).val().Volume()))
    except Exception:
        return 0.0


def test_four_positive_shell_joint_counterparts_are_real_breps() -> None:
    model = build_model()
    frame = build_structural_frame_realization(model=model)
    architecture = build_structural_frame_shell_joints(model=model, frame=frame)

    assert tuple(joint.joint_id for joint in architecture.joints) == JOINT_IDS
    assert architecture.assembled_frame.val().isValid()
    assert architecture.modified_shell.val().isValid()
    assert len(architecture.assembled_frame.val().Solids()) == 1
    assert len(architecture.modified_shell.val().Solids()) == 1
    assert architecture.frame_shell_nominal_intersection_mm3 <= 1e-7

    for joint in architecture.joints:
        assert joint.frame_capture_volume_mm3 > 0.0
        assert joint.shell_socket_removed_volume_mm3 > 0.0
        assert joint.nominal_tenon_shell_intersection_mm3 <= 1e-7
        assert joint.nominal_pin_frame_intersection_mm3 <= 1e-7
        assert joint.nominal_pin_shell_intersection_mm3 <= 1e-7


def test_joint_manifest_is_deterministic_source_bound_and_not_physical_evidence() -> None:
    first = build_structural_frame_shell_joints()
    second = build_structural_frame_shell_joints()

    assert first.architecture_sha256 == second.architecture_sha256
    assert first.manifest() == second.manifest()
    assert first.source_frame_geometry_sha256 == build_structural_frame_realization().geometry_sha256
    assert first.physical_validation_eligible is False
    assert first.manifest()["load_path_status"].startswith("POSITIVE_GEOMETRIC_COUNTERPARTS_REALIZED")
    json.dumps(first.manifest(), sort_keys=True, allow_nan=False)


def test_capture_pin_has_positive_radial_bore_clearance() -> None:
    assert PIN_BORE_DIAMETER_MM > PIN_DIAMETER_MM
    architecture = build_structural_frame_shell_joints()
    for joint in architecture.joints:
        assert _intersection_volume(joint.pin, joint.frame_tenon_union) <= 1e-7
        assert _intersection_volume(joint.pin, joint.shell_with_mortise_and_pin_bore) <= 1e-7


def test_regression_rejects_loss_of_positive_frame_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    import masck_one.structural_frame_shell_joints as joints

    original = joints._joint_centers

    def outside(model):
        centers = original(model)
        return tuple((x * 8.0, y * 8.0) for x, y in centers)

    monkeypatch.setattr(joints, "_joint_centers", outside)
    with pytest.raises(StructuralFrameShellJointError, match="positively embed"):
        joints.build_structural_frame_shell_joints()


def test_regression_rejects_shell_counterpart_that_removes_no_material(monkeypatch: pytest.MonkeyPatch) -> None:
    import masck_one.structural_frame_shell_joints as joints

    original_box = joints._box_at
    call_count = 0

    def shifted_box(center_x, center_y, z_center, width, height, depth):
        nonlocal call_count
        call_count += 1
        shape = original_box(center_x, center_y, z_center, width, height, depth)
        if call_count == 2:
            return shape.translate((0.0, 0.0, 1000.0))
        return shape

    monkeypatch.setattr(joints, "_box_at", shifted_box)
    with pytest.raises(StructuralFrameShellJointError, match="mortise does not cut"):
        joints.build_structural_frame_shell_joints()
