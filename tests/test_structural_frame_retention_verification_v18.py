from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_clevis_bores import INTERSECTION_TOLERANCE_MM3
from masck_one.structural_frame_retention_verification_v18 import (
    StructuralFrameRetentionVerificationV18Error,
    build_structural_frame_retention_verification_v18,
)


def test_v18_capture_pins_clear_fully_integrated_corrected_frame():
    result = build_structural_frame_retention_verification_v18()
    assert result.physical_validation_eligible is False
    assert len(result.roots) == 2
    assert all(root.pin_integrated_frame_intersection_mm3 <= INTERSECTION_TOLERANCE_MM3 for root in result.roots)


def test_v18_manifest_exposes_integrated_collision_evidence():
    manifest = build_structural_frame_retention_verification_v18().manifest()
    assert manifest["physical_validation_eligible"] is False
    assert manifest["intersection_tolerance_mm3"] == INTERSECTION_TOLERANCE_MM3
    assert len(manifest["roots"]) == 2
    assert all(root["pin_integrated_frame_intersection_mm3"] <= INTERSECTION_TOLERANCE_MM3 for root in manifest["roots"])


def test_v18_rejects_integrated_frame_collision():
    result = build_structural_frame_retention_verification_v18()
    hostile_root = replace(
        result.roots[0],
        pin_integrated_frame_intersection_mm3=INTERSECTION_TOLERANCE_MM3 * 10.0,
    )
    hostile = replace(result, roots=(hostile_root, result.roots[1]))
    with pytest.raises(StructuralFrameRetentionVerificationV18Error, match="intersects integrated structural frame"):
        hostile.validate()


def test_v18_rejects_nonfinite_integrated_collision_evidence():
    result = build_structural_frame_retention_verification_v18()
    hostile_root = replace(result.roots[0], pin_integrated_frame_intersection_mm3=float("nan"))
    hostile = replace(result, roots=(hostile_root, result.roots[1]))
    with pytest.raises(StructuralFrameRetentionVerificationV18Error, match="finite and nonnegative"):
        hostile.validate()


def test_v18_rejects_duplicate_bilateral_identity():
    result = build_structural_frame_retention_verification_v18()
    hostile = replace(result, roots=(result.roots[0], result.roots[0]))
    with pytest.raises(StructuralFrameRetentionVerificationV18Error, match="both bilateral roots"):
        hostile.validate()


def test_v18_rejects_physical_validation_promotion():
    result = build_structural_frame_retention_verification_v18()
    with pytest.raises(StructuralFrameRetentionVerificationV18Error, match="not physical validation"):
        replace(result, physical_validation_eligible=True).validate()
