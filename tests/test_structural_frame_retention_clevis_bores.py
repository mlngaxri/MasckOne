from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_clevis_bores import (
    CLEVIS_BORE_RADIUS_MM,
    INTERSECTION_TOLERANCE_MM3,
    StructuralFrameRetentionClevisBoreError,
    build_structural_frame_retention_clevis_bores,
)
from masck_one.structural_frame_retention_roots import YOKE_ROOT_BORE_RADIUS_MM


def test_bilateral_clevis_bores_remove_capture_pin_frame_interference():
    result = build_structural_frame_retention_clevis_bores()
    assert result.physical_validation_eligible is False
    assert CLEVIS_BORE_RADIUS_MM == YOKE_ROOT_BORE_RADIUS_MM
    assert len(result.roots) == 2
    for root in result.roots:
        assert root.pre_cut_pin_frame_intersection_mm3 > INTERSECTION_TOLERANCE_MM3
        assert root.post_cut_pin_frame_intersection_mm3 == 0.0
        assert root.post_cut_frame_capture_volume_mm3 > INTERSECTION_TOLERANCE_MM3
        assert root.corrected_frame_counterpart.val().isValid()


def test_clevis_bore_manifest_exposes_repaired_interference_evidence():
    manifest = build_structural_frame_retention_clevis_bores().manifest()
    assert manifest["physical_validation_eligible"] is False
    assert manifest["bore_radius_mm"] == YOKE_ROOT_BORE_RADIUS_MM
    assert all(root["pre_cut_pin_frame_intersection_mm3"] > 0.0 for root in manifest["roots"])
    assert all(root["post_cut_pin_frame_intersection_mm3"] == 0.0 for root in manifest["roots"])


def test_clevis_bore_rejects_radius_authority_drift():
    result = build_structural_frame_retention_clevis_bores()
    hostile = replace(result.roots[0], bore_radius_mm=CLEVIS_BORE_RADIUS_MM - 0.05)
    with pytest.raises(StructuralFrameRetentionClevisBoreError, match="bore radius drifted"):
        hostile.validate()


def test_clevis_bore_rejects_residual_pin_frame_interference():
    result = build_structural_frame_retention_clevis_bores()
    hostile = replace(result.roots[0], post_cut_pin_frame_intersection_mm3=0.01)
    with pytest.raises(StructuralFrameRetentionClevisBoreError, match="still intersects"):
        hostile.validate()


def test_clevis_bore_rejects_loss_of_positive_frame_attachment():
    result = build_structural_frame_retention_clevis_bores()
    hostile = replace(result.roots[0], post_cut_frame_capture_volume_mm3=0.0)
    with pytest.raises(StructuralFrameRetentionClevisBoreError, match="destroyed positive frame attachment"):
        hostile.validate()


def test_clevis_bore_rejects_physical_validation_promotion():
    result = build_structural_frame_retention_clevis_bores()
    with pytest.raises(StructuralFrameRetentionClevisBoreError, match="not physical validation"):
        replace(result, physical_validation_eligible=True).validate()
