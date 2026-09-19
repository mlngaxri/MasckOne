from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_verification_v3 import (
    MIN_PIN_BORE_CAPTURE_MM3,
    MIN_PIN_BORE_CAPTURE_FRACTION,
    NOMINAL_PIN_BORE_CAPTURE_MM3,
    StructuralFrameRetentionVerificationV3,
    StructuralFrameRetentionVerificationV3Error,
    verify_structural_frame_retention_roots_v3,
)


def test_nominal_bilateral_pin_capture_exceeds_coverage_floor() -> None:
    result = verify_structural_frame_retention_roots_v3()
    assert MIN_PIN_BORE_CAPTURE_FRACTION == 0.98
    assert MIN_PIN_BORE_CAPTURE_MM3 == pytest.approx(0.98 * NOMINAL_PIN_BORE_CAPTURE_MM3)
    for root in result.v2.roots:
        assert root.pin_bore_capture_mm3 >= MIN_PIN_BORE_CAPTURE_MM3
    assert result.physical_validation_eligible is False


def test_partial_positive_bore_overlap_is_rejected() -> None:
    nominal = verify_structural_frame_retention_roots_v3()
    left, right = nominal.v2.roots
    barely_positive = replace(left, pin_bore_capture_mm3=MIN_PIN_BORE_CAPTURE_MM3 * 0.5)
    weakened_v2 = replace(nominal.v2, roots=(barely_positive, right))
    with pytest.raises(StructuralFrameRetentionVerificationV3Error, match="does not span enough"):
        StructuralFrameRetentionVerificationV3(v2=weakened_v2).validate()


def test_capture_exactly_at_floor_is_accepted() -> None:
    nominal = verify_structural_frame_retention_roots_v3()
    left, right = nominal.v2.roots
    threshold = replace(left, pin_bore_capture_mm3=MIN_PIN_BORE_CAPTURE_MM3)
    StructuralFrameRetentionVerificationV3(v2=replace(nominal.v2, roots=(threshold, right))).validate()


def test_invalid_minimum_capture_fails_closed() -> None:
    nominal = verify_structural_frame_retention_roots_v3()
    with pytest.raises(StructuralFrameRetentionVerificationV3Error, match="finite and positive"):
        StructuralFrameRetentionVerificationV3(v2=nominal.v2, minimum_pin_bore_capture_mm3=float("nan")).validate()


def test_caller_cannot_weaken_authority_capture_floor() -> None:
    nominal = verify_structural_frame_retention_roots_v3()
    with pytest.raises(StructuralFrameRetentionVerificationV3Error, match="cannot weaken"):
        StructuralFrameRetentionVerificationV3(
            v2=nominal.v2,
            minimum_pin_bore_capture_mm3=MIN_PIN_BORE_CAPTURE_MM3 * 0.5,
        ).validate()


def test_caller_may_strengthen_capture_floor() -> None:
    nominal = verify_structural_frame_retention_roots_v3()
    measured_floor = min(root.pin_bore_capture_mm3 for root in nominal.v2.roots)
    strengthened = MIN_PIN_BORE_CAPTURE_MM3 + (measured_floor - MIN_PIN_BORE_CAPTURE_MM3) * 0.5
    StructuralFrameRetentionVerificationV3(
        v2=nominal.v2,
        minimum_pin_bore_capture_mm3=strengthened,
    ).validate()


def test_manifest_keeps_digital_evidence_firewall_and_authority_floor() -> None:
    manifest = verify_structural_frame_retention_roots_v3().manifest()
    assert manifest["verification_semantics"] == "FAIL_CLOSED_V2_PLUS_MINIMUM_AXIAL_PIN_BORE_CAPTURE_COVERAGE"
    assert manifest["authority_minimum_pin_bore_capture_mm3"] == pytest.approx(MIN_PIN_BORE_CAPTURE_MM3)
    assert manifest["enforced_minimum_pin_bore_capture_mm3"] == pytest.approx(MIN_PIN_BORE_CAPTURE_MM3)
    assert manifest["physical_validation_eligible"] is False
