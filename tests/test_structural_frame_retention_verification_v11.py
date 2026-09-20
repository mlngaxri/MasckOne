from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_verification_v11 import (
    CLEARANCE_NUMERICAL_TOLERANCE_MM,
    NOMINAL_CLIP_GROOVE_RADIAL_CLEARANCE_MM,
    StructuralFrameRetentionVerificationV11,
    StructuralFrameRetentionVerificationV11Error,
    verify_structural_frame_retention_roots_v11,
)


def test_nominal_v11_retainer_preserves_groove_seating_clearance_without_interference():
    result = verify_structural_frame_retention_roots_v11()
    manifest = result.manifest()
    assert manifest["physical_validation_eligible"] is False
    assert all(
        abs(root["groove_bottom_clearance_mm"] - NOMINAL_CLIP_GROOVE_RADIAL_CLEARANCE_MM)
        <= CLEARANCE_NUMERICAL_TOLERANCE_MM
        and root["retainer_pin_intersection_mm3"] <= manifest["interference_tolerance_mm3"]
        for root in manifest["roots"]
    )


def test_v11_rejects_synthetic_groove_clearance_drift():
    nominal = verify_structural_frame_retention_roots_v11()
    clearances = list(nominal.groove_bottom_clearances_mm)
    clearances[0] = (clearances[0][0], clearances[0][1] + 0.01)
    with pytest.raises(StructuralFrameRetentionVerificationV11Error, match="nominal groove seating clearance"):
        StructuralFrameRetentionVerificationV11(
            v10=nominal.v10,
            groove_bottom_clearances_mm=tuple(clearances),
            retainer_pin_intersections_mm3=nominal.retainer_pin_intersections_mm3,
        ).validate()


def test_v11_rejects_retainer_pin_volumetric_interference():
    nominal = verify_structural_frame_retention_roots_v11()
    intersections = list(nominal.retainer_pin_intersections_mm3)
    intersections[0] = (intersections[0][0], 0.01)
    with pytest.raises(StructuralFrameRetentionVerificationV11Error, match="volumetrically interferes"):
        StructuralFrameRetentionVerificationV11(
            v10=nominal.v10,
            groove_bottom_clearances_mm=nominal.groove_bottom_clearances_mm,
            retainer_pin_intersections_mm3=tuple(intersections),
        ).validate()


def test_v11_rejects_duplicate_root_identity():
    nominal = verify_structural_frame_retention_roots_v11()
    root_id, clearance = nominal.groove_bottom_clearances_mm[0]
    with pytest.raises(StructuralFrameRetentionVerificationV11Error, match="exactly one wearer-left"):
        StructuralFrameRetentionVerificationV11(
            v10=nominal.v10,
            groove_bottom_clearances_mm=((root_id, clearance), (root_id, clearance)),
            retainer_pin_intersections_mm3=nominal.retainer_pin_intersections_mm3,
        ).validate()


def test_v11_rejects_physical_validation_promotion():
    nominal = verify_structural_frame_retention_roots_v11()
    with pytest.raises(StructuralFrameRetentionVerificationV11Error, match="not physical validation"):
        replace(nominal, physical_validation_eligible=True).validate()
