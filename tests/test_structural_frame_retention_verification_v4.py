from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_verification_v4 import (
    MAX_BILATERAL_PIN_CAPTURE_RELATIVE_MISMATCH,
    StructuralFrameRetentionVerificationV4,
    StructuralFrameRetentionVerificationV4Error,
    verify_structural_frame_retention_roots_v4,
)


def test_nominal_bilateral_capture_is_consistent() -> None:
    result = verify_structural_frame_retention_roots_v4()
    assert result.bilateral_pin_capture_relative_mismatch <= MAX_BILATERAL_PIN_CAPTURE_RELATIVE_MISMATCH
    assert result.physical_validation_eligible is False


def test_material_one_sided_capture_drift_is_rejected() -> None:
    nominal = verify_structural_frame_retention_roots_v4()
    left, right = nominal.v3.v2.roots
    drifted_left = replace(left, pin_bore_capture_mm3=left.pin_bore_capture_mm3 * 0.99)
    drifted_v2 = replace(nominal.v3.v2, roots=(drifted_left, right))
    drifted_v3 = replace(nominal.v3, v2=drifted_v2)
    with pytest.raises(StructuralFrameRetentionVerificationV4Error, match="not symmetric"):
        StructuralFrameRetentionVerificationV4(v3=drifted_v3).validate()


def test_caller_cannot_weaken_bilateral_mismatch_ceiling() -> None:
    nominal = verify_structural_frame_retention_roots_v4()
    with pytest.raises(StructuralFrameRetentionVerificationV4Error, match="cannot weaken"):
        StructuralFrameRetentionVerificationV4(
            v3=nominal.v3,
            maximum_bilateral_pin_capture_relative_mismatch=MAX_BILATERAL_PIN_CAPTURE_RELATIVE_MISMATCH * 10.0,
        ).validate()


def test_caller_may_strengthen_bilateral_mismatch_ceiling() -> None:
    nominal = verify_structural_frame_retention_roots_v4()
    StructuralFrameRetentionVerificationV4(
        v3=nominal.v3,
        maximum_bilateral_pin_capture_relative_mismatch=MAX_BILATERAL_PIN_CAPTURE_RELATIVE_MISMATCH * 0.5,
    ).validate()


def test_invalid_mismatch_limit_fails_closed() -> None:
    nominal = verify_structural_frame_retention_roots_v4()
    with pytest.raises(StructuralFrameRetentionVerificationV4Error, match="finite and nonnegative"):
        StructuralFrameRetentionVerificationV4(
            v3=nominal.v3,
            maximum_bilateral_pin_capture_relative_mismatch=float("nan"),
        ).validate()


def test_manifest_exposes_authority_and_measured_mismatch() -> None:
    manifest = verify_structural_frame_retention_roots_v4().manifest()
    assert manifest["verification_semantics"] == "FAIL_CLOSED_V3_PLUS_BILATERAL_PIN_BORE_CAPTURE_CONSISTENCY"
    assert manifest["authority_maximum_bilateral_pin_capture_relative_mismatch"] == MAX_BILATERAL_PIN_CAPTURE_RELATIVE_MISMATCH
    assert manifest["enforced_maximum_bilateral_pin_capture_relative_mismatch"] == MAX_BILATERAL_PIN_CAPTURE_RELATIVE_MISMATCH
    assert manifest["measured_bilateral_pin_capture_relative_mismatch"] <= MAX_BILATERAL_PIN_CAPTURE_RELATIVE_MISMATCH
    assert manifest["physical_validation_eligible"] is False
