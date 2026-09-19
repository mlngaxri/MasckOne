from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_verification_v5 import verify_structural_frame_retention_roots_v5
from masck_one.structural_frame_retention_verification_v6 import (
    CAPTURE_VOLUME_RELATIVE_NUMERICAL_TOLERANCE,
    StructuralFrameRetentionVerificationV6,
    StructuralFrameRetentionVerificationV6Error,
    verify_structural_frame_retention_roots_v6,
)


def _capacities_for(v5, multiplier: float = 1.01):
    return tuple(
        (root.root_id, root.source_frame_capture_mm3 * multiplier)
        for root in v5.v4.v3.v2.roots
    )


def test_nominal_v6_source_capture_is_physically_bounded():
    result = verify_structural_frame_retention_roots_v6()
    manifest = result.manifest()
    assert manifest["physical_validation_eligible"] is False
    assert manifest["capture_volume_relative_numerical_tolerance"] == CAPTURE_VOLUME_RELATIVE_NUMERICAL_TOLERANCE
    assert all(root["source_frame_capture_fraction"] <= 1.0 + CAPTURE_VOLUME_RELATIVE_NUMERICAL_TOLERANCE for root in manifest["roots"])


def test_v6_rejects_capture_larger_than_counterpart_body():
    v5 = verify_structural_frame_retention_roots_v5()
    capacities = list(_capacities_for(v5))
    root_id, _ = capacities[0]
    capture = next(root.source_frame_capture_mm3 for root in v5.v4.v3.v2.roots if root.root_id == root_id)
    capacities[0] = (root_id, capture * 0.99)
    with pytest.raises(StructuralFrameRetentionVerificationV6Error, match="exceeds physical counterpart volume"):
        StructuralFrameRetentionVerificationV6(v5=v5, frame_counterpart_volumes_mm3=tuple(capacities)).validate()


def test_v6_rejects_missing_or_duplicate_capacity_identity():
    v5 = verify_structural_frame_retention_roots_v5()
    left = v5.v4.v3.v2.roots[0]
    bad = ((left.root_id, left.source_frame_capture_mm3 * 2.0),) * 2
    with pytest.raises(StructuralFrameRetentionVerificationV6Error, match="exactly one wearer-left"):
        StructuralFrameRetentionVerificationV6(v5=v5, frame_counterpart_volumes_mm3=bad).validate()


@pytest.mark.parametrize("capacity", [0.0, -1.0, float("nan"), float("inf")])
def test_v6_rejects_invalid_counterpart_capacity(capacity):
    v5 = verify_structural_frame_retention_roots_v5()
    capacities = list(_capacities_for(v5))
    capacities[0] = (capacities[0][0], capacity)
    with pytest.raises(StructuralFrameRetentionVerificationV6Error, match="finite and positive"):
        StructuralFrameRetentionVerificationV6(v5=v5, frame_counterpart_volumes_mm3=tuple(capacities)).validate()


def test_v6_rejects_physical_validation_promotion():
    v5 = verify_structural_frame_retention_roots_v5()
    candidate = StructuralFrameRetentionVerificationV6(v5=v5, frame_counterpart_volumes_mm3=_capacities_for(v5))
    with pytest.raises(StructuralFrameRetentionVerificationV6Error, match="not physical validation"):
        replace(candidate, physical_validation_eligible=True).validate()
