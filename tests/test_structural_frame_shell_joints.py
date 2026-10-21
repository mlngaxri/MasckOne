from __future__ import annotations

import json

import cadquery as cq
import pytest

from masck_one.model import build_model
from masck_one.structural_frame_realization import build_structural_frame_realization
from masck_one.structural_frame_shell_joints import (
    JOINT_IDS,
    PIN_BORE_DIAMETER_MM,
    PIN_CLIP_AXIAL_PROBE_MM,
    PIN_CLIP_INNER_RADIUS_MM,
    PIN_CLIP_OUTER_RADIUS_MM,
    PIN_DIAMETER_MM,
    PIN_GROOVE_RADIUS_MM,
    PIN_HEAD_DIAMETER_MM,
    PIN_HEAD_RELIEF_AXIAL_CLEARANCE_MM,
    PIN_HEAD_RELIEF_RADIAL_CLEARANCE_MM,
    PIN_HEAD_THICKNESS_MM,
    PIN_OVERHANG_MM,
    PIN_RETENTION_EXTENSION_MM,
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
        assert joint.nominal_clip_pin_intersection_mm3 <= 1e-7
        assert joint.clip_negative_axial_stop_intersection_mm3 > 0.0
        assert joint.clip_positive_axial_stop_intersection_mm3 > 0.0


def test_joint_manifest_is_deterministic_source_bound_and_not_physical_evidence() -> None:
    first = build_structural_frame_shell_joints()
    second = build_structural_frame_shell_joints()

    assert first.architecture_sha256 == second.architecture_sha256
    assert first.manifest() == second.manifest()
    assert first.source_frame_geometry_sha256 == build_structural_frame_realization().geometry_sha256
    assert first.physical_validation_eligible is False
    assert first.manifest()["load_path_status"].startswith("POSITIVE_GEOMETRIC_COUNTERPARTS_REALIZED")
    assert "SINGLE_HEADED_CAPTURE_PINS" in first.manifest()["service_status"]
    json.dumps(first.manifest(), sort_keys=True, allow_nan=False)


def test_capture_pin_is_single_head_service_insertable_and_clip_retained() -> None:
    assert PIN_BORE_DIAMETER_MM > PIN_DIAMETER_MM
    assert PIN_HEAD_RELIEF_RADIAL_CLEARANCE_MM > 0.0
    assert PIN_HEAD_RELIEF_AXIAL_CLEARANCE_MM > 0.0
    assert PIN_HEAD_DIAMETER_MM > PIN_BORE_DIAMETER_MM
    assert PIN_RETENTION_EXTENSION_MM > 0.0
    assert PIN_GROOVE_RADIUS_MM < PIN_DIAMETER_MM / 2.0
    assert PIN_GROOVE_RADIUS_MM < PIN_CLIP_INNER_RADIUS_MM < PIN_DIAMETER_MM / 2.0
    assert PIN_CLIP_OUTER_RADIUS_MM > PIN_CLIP_INNER_RADIUS_MM
    assert PIN_CLIP_AXIAL_PROBE_MM > 0.0

    architecture = build_structural_frame_shell_joints()
    for joint in architecture.joints:
        assert _intersection_volume(joint.pin, joint.frame_tenon_union) <= 1e-7
        assert _intersection_volume(joint.pin, joint.shell_with_mortise_and_pin_bore) <= 1e-7
        assert _intersection_volume(joint.retainer_clip, joint.pin) <= 1e-7
        assert _intersection_volume(joint.retainer_clip.translate((-PIN_CLIP_AXIAL_PROBE_MM, 0.0, 0.0)), joint.pin) > 0.0
        assert _intersection_volume(joint.retainer_clip.translate((PIN_CLIP_AXIAL_PROBE_MM, 0.0, 0.0)), joint.pin) > 0.0
        manifest = joint.manifest()
        assert manifest["service_installation_status"].startswith("ONE_PIECE_PIN_INSERTION")
        assert manifest["dimensions_mm"]["pin_head_relief_radial_clearance"] == PIN_HEAD_RELIEF_RADIAL_CLEARANCE_MM
        assert manifest["dimensions_mm"]["pin_head_relief_axial_clearance"] == PIN_HEAD_RELIEF_AXIAL_CLEARANCE_MM


def test_regression_rejects_loss_of_pin_head_relief(monkeypatch: pytest.MonkeyPatch) -> None:
    import masck_one.structural_frame_shell_joints as joints

    original = joints._pin_geometry

    def no_head_relief(center_x, center_y, z_center, length):
        pin, _bore, clip = original(center_x, center_y, z_center, length)
        shaft_half_span = length + PIN_RETENTION_EXTENSION_MM
        shaft_bore = cq.Workplane("YZ").circle(PIN_BORE_DIAMETER_MM / 2.0).extrude(shaft_half_span + PIN_OVERHANG_MM, both=True).translate((center_x, center_y, z_center))
        return pin, shaft_bore, clip

    monkeypatch.setattr(joints, "_pin_geometry", no_head_relief)
    with pytest.raises(StructuralFrameShellJointError, match="shell-side bore"):
        joints.build_structural_frame_shell_joints()


def test_regression_rejects_retainer_without_positive_groove_shoulders(monkeypatch: pytest.MonkeyPatch) -> None:
    import masck_one.structural_frame_shell_joints as joints

    original = joints._pin_geometry

    def clip_far_from_groove(center_x, center_y, z_center, length):
        pin, bore, clip = original(center_x, center_y, z_center, length)
        return pin, bore, clip.translate((20.0, 0.0, 0.0))

    monkeypatch.setattr(joints, "_pin_geometry", clip_far_from_groove)
    with pytest.raises(StructuralFrameShellJointError, match="positively captured"):
        joints.build_structural_frame_shell_joints()


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
