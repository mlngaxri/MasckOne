from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_verification_v13 import (
    MIN_HEAD_RADIAL_STOP_MARGIN_MM,
    StructuralFrameRetentionVerificationV13,
    StructuralFrameRetentionVerificationV13Error,
    verify_structural_frame_retention_roots_v13,
)


def test_nominal_v13_capture_pin_heads_form_bilateral_proximal_stops():
    result = verify_structural_frame_retention_roots_v13()
    manifest = result.manifest()
    assert manifest["physical_validation_eligible"] is False
    assert all(
        root["head_seating_gap_mm"] <= manifest["axial_seating_numerical_tolerance_mm"]
        and root["head_radial_stop_margin_mm"] >= MIN_HEAD_RADIAL_STOP_MARGIN_MM
        for root in manifest["roots"]
    )


def test_v13_rejects_unseated_capture_pin_head():
    nominal = verify_structural_frame_retention_roots_v13()
    gaps = list(nominal.head_seating_gaps_mm)
    gaps[0] = (gaps[0][0], 0.10)
    with pytest.raises(StructuralFrameRetentionVerificationV13Error, match="not seated"):
        replace(nominal, head_seating_gaps_mm=tuple(gaps)).validate()


def test_v13_rejects_insufficient_head_radial_stop_material():
    nominal = verify_structural_frame_retention_roots_v13()
    margins = list(nominal.head_radial_stop_margins_mm)
    margins[0] = (margins[0][0], MIN_HEAD_RADIAL_STOP_MARGIN_MM - 0.01)
    with pytest.raises(StructuralFrameRetentionVerificationV13Error, match="lacks required radial"):
        replace(nominal, head_radial_stop_margins_mm=tuple(margins)).validate()


def test_v13_rejects_duplicate_root_identity():
    nominal = verify_structural_frame_retention_roots_v13()
    root_id, value = nominal.head_seating_gaps_mm[0]
    with pytest.raises(StructuralFrameRetentionVerificationV13Error, match="exactly one wearer-left"):
        replace(nominal, head_seating_gaps_mm=((root_id, value), (root_id, value))).validate()


def test_v13_rejects_physical_validation_promotion():
    nominal = verify_structural_frame_retention_roots_v13()
    with pytest.raises(StructuralFrameRetentionVerificationV13Error, match="not physical validation"):
        replace(nominal, physical_validation_eligible=True).validate()
