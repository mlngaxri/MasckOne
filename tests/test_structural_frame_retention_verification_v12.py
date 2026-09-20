from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_verification_v12 import (
    INTERFERENCE_TOLERANCE_MM3,
    StructuralFrameRetentionVerificationV12,
    StructuralFrameRetentionVerificationV12Error,
    verify_structural_frame_retention_roots_v12,
)


def test_nominal_v12_retainer_clears_local_frame_and_yoke_material():
    result = verify_structural_frame_retention_roots_v12()
    manifest = result.manifest()
    assert manifest["physical_validation_eligible"] is False
    assert manifest["service_access_verified"] is False
    assert all(
        root["retainer_frame_intersection_mm3"] <= INTERFERENCE_TOLERANCE_MM3
        and root["retainer_yoke_intersection_mm3"] <= INTERFERENCE_TOLERANCE_MM3
        for root in manifest["roots"]
    )


def test_v12_rejects_retainer_frame_interference():
    nominal = verify_structural_frame_retention_roots_v12()
    intersections = list(nominal.retainer_frame_intersections_mm3)
    intersections[0] = (intersections[0][0], 0.01)
    with pytest.raises(StructuralFrameRetentionVerificationV12Error, match="frame counterpart"):
        StructuralFrameRetentionVerificationV12(
            v11=nominal.v11,
            retainer_frame_intersections_mm3=tuple(intersections),
            retainer_yoke_intersections_mm3=nominal.retainer_yoke_intersections_mm3,
        ).validate()


def test_v12_rejects_retainer_yoke_interference():
    nominal = verify_structural_frame_retention_roots_v12()
    intersections = list(nominal.retainer_yoke_intersections_mm3)
    intersections[0] = (intersections[0][0], 0.01)
    with pytest.raises(StructuralFrameRetentionVerificationV12Error, match="yoke material"):
        StructuralFrameRetentionVerificationV12(
            v11=nominal.v11,
            retainer_frame_intersections_mm3=nominal.retainer_frame_intersections_mm3,
            retainer_yoke_intersections_mm3=tuple(intersections),
        ).validate()


def test_v12_rejects_duplicate_root_identity():
    nominal = verify_structural_frame_retention_roots_v12()
    root_id, value = nominal.retainer_frame_intersections_mm3[0]
    with pytest.raises(StructuralFrameRetentionVerificationV12Error, match="exactly one wearer-left"):
        StructuralFrameRetentionVerificationV12(
            v11=nominal.v11,
            retainer_frame_intersections_mm3=((root_id, value), (root_id, value)),
            retainer_yoke_intersections_mm3=nominal.retainer_yoke_intersections_mm3,
        ).validate()


def test_v12_rejects_physical_validation_promotion():
    nominal = verify_structural_frame_retention_roots_v12()
    with pytest.raises(StructuralFrameRetentionVerificationV12Error, match="not physical validation"):
        replace(nominal, physical_validation_eligible=True).validate()
