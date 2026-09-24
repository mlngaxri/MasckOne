from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_verification_v14 import (
    DIMENSIONAL_NUMERICAL_TOLERANCE_MM,
    StructuralFrameRetentionVerificationV14Error,
    verify_structural_frame_retention_roots_v14,
)


def test_nominal_v14_capture_pins_match_structural_authority():
    result = verify_structural_frame_retention_roots_v14()
    manifest = result.manifest()
    assert manifest["physical_validation_eligible"] is False
    assert all(
        abs(root["pin_overall_length_mm"] - manifest["expected_pin_overall_length_mm"])
        <= DIMENSIONAL_NUMERICAL_TOLERANCE_MM
        and abs(root["pin_head_radius_mm"] - manifest["expected_pin_head_radius_mm"])
        <= DIMENSIONAL_NUMERICAL_TOLERANCE_MM
        for root in manifest["roots"]
    )


def test_v14_rejects_coherent_pin_length_drift():
    nominal = verify_structural_frame_retention_roots_v14()
    values = list(nominal.pin_overall_lengths_mm)
    values[0] = (values[0][0], values[0][1] + 0.05)
    with pytest.raises(StructuralFrameRetentionVerificationV14Error, match="overall length drifted"):
        replace(nominal, pin_overall_lengths_mm=tuple(values)).validate()


def test_v14_rejects_head_radius_drift_even_when_v13_minimum_stop_still_passes():
    nominal = verify_structural_frame_retention_roots_v14()
    values = list(nominal.pin_head_radii_mm)
    values[0] = (values[0][0], values[0][1] - 0.05)
    with pytest.raises(StructuralFrameRetentionVerificationV14Error, match="head radius drifted"):
        replace(nominal, pin_head_radii_mm=tuple(values)).validate()


def test_v14_rejects_duplicate_root_identity():
    nominal = verify_structural_frame_retention_roots_v14()
    root_id, value = nominal.pin_overall_lengths_mm[0]
    with pytest.raises(StructuralFrameRetentionVerificationV14Error, match="exactly one wearer-left"):
        replace(nominal, pin_overall_lengths_mm=((root_id, value), (root_id, value))).validate()


def test_v14_rejects_physical_validation_promotion():
    nominal = verify_structural_frame_retention_roots_v14()
    with pytest.raises(StructuralFrameRetentionVerificationV14Error, match="not physical validation"):
        replace(nominal, physical_validation_eligible=True).validate()
