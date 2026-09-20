from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_verification_v17 import (
    AXIS_REGISTRATION_TOLERANCE_MM,
    StructuralFrameRetentionVerificationV17Error,
    build_structural_frame_retention_verification_v17,
)


def test_v17_binds_actual_pin_and_bore_axes_bilaterally():
    result = build_structural_frame_retention_verification_v17()
    assert result.physical_validation_eligible is False
    assert len(result.roots) == 2
    for root in result.roots:
        assert root.pin_bore_axis_offset_mm <= AXIS_REGISTRATION_TOLERANCE_MM
        assert root.pin_axis_xz_mm == pytest.approx(root.bore_axis_xz_mm, abs=AXIS_REGISTRATION_TOLERANCE_MM)


def test_v17_manifest_exposes_axis_registration_evidence():
    manifest = build_structural_frame_retention_verification_v17().manifest()
    assert manifest["physical_validation_eligible"] is False
    assert manifest["axis_registration_tolerance_mm"] == AXIS_REGISTRATION_TOLERANCE_MM
    assert len(manifest["roots"]) == 2
    assert all(root["pin_bore_axis_offset_mm"] <= AXIS_REGISTRATION_TOLERANCE_MM for root in manifest["roots"])


def test_v17_rejects_pin_bore_axis_offset():
    result = build_structural_frame_retention_verification_v17()
    root = result.roots[0]
    shifted_pin_axis = (root.pin_axis_xz_mm[0] + 0.05, root.pin_axis_xz_mm[1])
    hostile_root = replace(
        root,
        pin_axis_xz_mm=shifted_pin_axis,
        pin_bore_axis_offset_mm=0.05,
    )
    with pytest.raises(StructuralFrameRetentionVerificationV17Error, match="not coaxial"):
        hostile_root.validate()


def test_v17_rejects_forged_axis_offset_evidence():
    result = build_structural_frame_retention_verification_v17()
    hostile_root = replace(result.roots[0], pin_bore_axis_offset_mm=0.0, pin_axis_xz_mm=(0.1, 0.2))
    with pytest.raises(StructuralFrameRetentionVerificationV17Error, match="disagrees with B-rep axes"):
        hostile_root.validate()


def test_v17_rejects_bilateral_bore_mirror_drift():
    result = build_structural_frame_retention_verification_v17()
    right = result.roots[1]
    shifted = (right.bore_axis_xz_mm[0] + 0.05, right.bore_axis_xz_mm[1])
    hostile_right = replace(right, pin_axis_xz_mm=shifted, bore_axis_xz_mm=shifted, pin_bore_axis_offset_mm=0.0)
    hostile = replace(result, roots=(result.roots[0], hostile_right))
    with pytest.raises(StructuralFrameRetentionVerificationV17Error, match="mirror registered"):
        hostile.validate()


def test_v17_rejects_nonfinite_axis_evidence():
    result = build_structural_frame_retention_verification_v17()
    hostile = replace(result.roots[0], pin_axis_xz_mm=(float("nan"), 0.0))
    with pytest.raises(StructuralFrameRetentionVerificationV17Error, match="must be finite"):
        hostile.validate()


def test_v17_rejects_physical_validation_promotion():
    result = build_structural_frame_retention_verification_v17()
    with pytest.raises(StructuralFrameRetentionVerificationV17Error, match="not physical validation"):
        replace(result, physical_validation_eligible=True).validate()
