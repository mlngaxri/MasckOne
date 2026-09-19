from __future__ import annotations

from dataclasses import replace

import cadquery as cq
import pytest

from masck_one.structural_frame_retention_roots import build_structural_frame_retention_roots
from masck_one.structural_frame_retention_verification_v2 import (
    INTERSECTION_TOLERANCE_MM3,
    RetentionRootVerificationV2,
    StructuralFrameRetentionVerificationV2Error,
    _strict_intersection_volume,
    verify_structural_frame_retention_roots_v2,
)


def test_nominal_bilateral_retention_roots_pass_independent_fail_closed_recheck() -> None:
    result = verify_structural_frame_retention_roots_v2()
    assert len(result.roots) == 2
    assert result.physical_validation_eligible is False
    for root in result.roots:
        assert root.source_frame_capture_mm3 > INTERSECTION_TOLERANCE_MM3
        assert root.yoke_material_intersection_mm3 <= INTERSECTION_TOLERANCE_MM3
        assert root.pin_yoke_material_intersection_mm3 <= INTERSECTION_TOLERANCE_MM3
        assert root.protected_intersection_mm3 <= INTERSECTION_TOLERANCE_MM3
    manifest = result.manifest()
    assert manifest["verification_semantics"] == "FAIL_CLOSED_INDEPENDENT_BREP_COLLISION_AND_SOURCE_CAPTURE_RECHECK"
    assert manifest["physical_validation_eligible"] is False


def test_strict_intersection_detects_positive_overlap() -> None:
    first = cq.Workplane("XY").box(2.0, 2.0, 2.0)
    second = cq.Workplane("XY").box(2.0, 2.0, 2.0).translate((1.0, 0.0, 0.0))
    assert _strict_intersection_volume(first, second) > INTERSECTION_TOLERANCE_MM3


def test_strict_intersection_fails_closed_when_kernel_query_cannot_be_performed() -> None:
    valid = cq.Workplane("XY").box(1.0, 1.0, 1.0)
    invalid = cq.Workplane("XY")
    with pytest.raises(StructuralFrameRetentionVerificationV2Error, match="failed closed"):
        _strict_intersection_volume(valid, invalid)


def test_root_metric_rejects_missing_source_frame_capture() -> None:
    metric = RetentionRootVerificationV2(
        root_id="RETENTION_ROOT_WEARER_LEFT",
        source_frame_capture_mm3=0.0,
        yoke_material_intersection_mm3=0.0,
        pin_yoke_material_intersection_mm3=0.0,
        protected_intersection_mm3=0.0,
    )
    with pytest.raises(StructuralFrameRetentionVerificationV2Error, match="no positive source-frame capture"):
        metric.validate()


def test_verifier_rejects_mismatched_source_frame_identity() -> None:
    architecture = build_structural_frame_retention_roots()
    stale = replace(
        architecture,
        source_frame_reaction_architecture_sha256="0" * 64,
    )
    with pytest.raises(StructuralFrameRetentionVerificationV2Error, match="reconstructed source reaction frame"):
        verify_structural_frame_retention_roots_v2(architecture=stale)


def test_verifier_rejects_wrong_architecture_type() -> None:
    with pytest.raises(StructuralFrameRetentionVerificationV2Error):
        verify_structural_frame_retention_roots_v2(architecture=object())  # type: ignore[arg-type]
