from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_verification_v5 import (
    MAX_BILATERAL_SOURCE_FRAME_CAPTURE_RELATIVE_MISMATCH,
    StructuralFrameRetentionVerificationV5,
    StructuralFrameRetentionVerificationV5Error,
    verify_structural_frame_retention_roots_v5,
)


def test_nominal_bilateral_source_frame_capture_is_consistent() -> None:
    result = verify_structural_frame_retention_roots_v5()
    assert (
        result.bilateral_source_frame_capture_relative_mismatch
        <= MAX_BILATERAL_SOURCE_FRAME_CAPTURE_RELATIVE_MISMATCH
    )
    assert result.physical_validation_eligible is False


def test_material_one_sided_source_frame_capture_drift_is_rejected() -> None:
    nominal = verify_structural_frame_retention_roots_v5()
    roots = list(nominal.v4.v3.v2.roots)
    left_index = next(
        index for index, root in enumerate(roots)
        if root.root_id == "RETENTION_ROOT_WEARER_LEFT"
    )
    roots[left_index] = replace(
        roots[left_index],
        source_frame_capture_mm3=roots[left_index].source_frame_capture_mm3 * 0.99,
    )
    drifted_v2 = replace(nominal.v4.v3.v2, roots=tuple(roots))
    drifted_v3 = replace(nominal.v4.v3, v2=drifted_v2)
    drifted_v4 = replace(nominal.v4, v3=drifted_v3)
    with pytest.raises(StructuralFrameRetentionVerificationV5Error, match="not symmetric"):
        StructuralFrameRetentionVerificationV5(v4=drifted_v4).validate()


def test_caller_cannot_weaken_source_frame_mismatch_ceiling() -> None:
    nominal = verify_structural_frame_retention_roots_v5()
    with pytest.raises(StructuralFrameRetentionVerificationV5Error, match="cannot weaken"):
        StructuralFrameRetentionVerificationV5(
            v4=nominal.v4,
            maximum_bilateral_source_frame_capture_relative_mismatch=(
                MAX_BILATERAL_SOURCE_FRAME_CAPTURE_RELATIVE_MISMATCH * 10.0
            ),
        ).validate()


def test_caller_may_strengthen_source_frame_mismatch_ceiling() -> None:
    nominal = verify_structural_frame_retention_roots_v5()
    StructuralFrameRetentionVerificationV5(
        v4=nominal.v4,
        maximum_bilateral_source_frame_capture_relative_mismatch=(
            MAX_BILATERAL_SOURCE_FRAME_CAPTURE_RELATIVE_MISMATCH * 0.5
        ),
    ).validate()


def test_invalid_source_frame_mismatch_limit_fails_closed() -> None:
    nominal = verify_structural_frame_retention_roots_v5()
    with pytest.raises(StructuralFrameRetentionVerificationV5Error, match="finite and nonnegative"):
        StructuralFrameRetentionVerificationV5(
            v4=nominal.v4,
            maximum_bilateral_source_frame_capture_relative_mismatch=float("nan"),
        ).validate()


def test_manifest_exposes_source_frame_authority_and_measured_mismatch() -> None:
    manifest = verify_structural_frame_retention_roots_v5().manifest()
    assert manifest["verification_semantics"] == "FAIL_CLOSED_V4_PLUS_BILATERAL_SOURCE_FRAME_CAPTURE_CONSISTENCY"
    assert manifest["authority_maximum_bilateral_source_frame_capture_relative_mismatch"] == MAX_BILATERAL_SOURCE_FRAME_CAPTURE_RELATIVE_MISMATCH
    assert manifest["enforced_maximum_bilateral_source_frame_capture_relative_mismatch"] == MAX_BILATERAL_SOURCE_FRAME_CAPTURE_RELATIVE_MISMATCH
    assert manifest["measured_bilateral_source_frame_capture_relative_mismatch"] <= MAX_BILATERAL_SOURCE_FRAME_CAPTURE_RELATIVE_MISMATCH
    assert manifest["physical_validation_eligible"] is False
