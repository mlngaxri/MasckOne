from __future__ import annotations

import math

import cadquery as cq
import pytest

from masck_one.structural_frame_retention_verification_v19 import (
    ROOT_IDS,
    RootKeepoutClearance,
    StructuralFrameRetentionVerificationV19,
    StructuralFrameRetentionVerificationV19Error,
    _intersection_mm3,
    build_structural_frame_retention_verification_v19,
)


def test_v19_recomputes_bilateral_pin_yoke_and_protected_clearance() -> None:
    verification = build_structural_frame_retention_verification_v19()
    assert tuple(root.root_id for root in verification.roots) == ROOT_IDS
    for root in verification.roots:
        assert root.pin_yoke_intersection_mm3 == 0.0
        assert root.protected_intersection_mm3 == 0.0
    manifest = verification.manifest()
    assert manifest["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V19"
    assert manifest["physical_validation_eligible"] is False


def test_v19_boolean_failure_cannot_be_relabelled_as_zero(monkeypatch) -> None:
    solid = cq.Workplane("XY").box(1.0, 1.0, 1.0)

    def fail_boolean(*args, **kwargs):
        raise RuntimeError("synthetic OCC failure")

    monkeypatch.setattr(cq.Workplane, "intersect", fail_boolean)
    with pytest.raises(StructuralFrameRetentionVerificationV19Error, match="clearance evidence is unavailable"):
        _intersection_mm3(solid, solid, "synthetic")


def test_v19_rejects_collision_and_invalid_numeric_evidence() -> None:
    for hostile in (0.01, math.nan, math.inf, -0.01):
        evidence = RootKeepoutClearance(ROOT_IDS[0], hostile, 0.0)
        with pytest.raises(StructuralFrameRetentionVerificationV19Error):
            evidence.validate()


def test_v19_requires_bilateral_identity_and_blocks_physical_promotion() -> None:
    nominal = build_structural_frame_retention_verification_v19()
    with pytest.raises(StructuralFrameRetentionVerificationV19Error, match="both bilateral roots"):
        StructuralFrameRetentionVerificationV19((nominal.roots[0],), False).validate()
    with pytest.raises(StructuralFrameRetentionVerificationV19Error, match="not physical validation"):
        StructuralFrameRetentionVerificationV19(nominal.roots, True).validate()
