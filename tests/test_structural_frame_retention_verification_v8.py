from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_verification_v7 import verify_structural_frame_retention_roots_v7
from masck_one.structural_frame_retention_verification_v8 import (
    CLEARANCE_METADATA_ABSOLUTE_TOLERANCE_MM,
    StructuralFrameRetentionVerificationV8,
    StructuralFrameRetentionVerificationV8Error,
    verify_structural_frame_retention_roots_v8,
)


def _nominal_candidate():
    result = verify_structural_frame_retention_roots_v8()
    return result.v7, result.generated_clearances_mm, result.independent_clearances_mm


def test_nominal_v8_clearance_matches_independent_brep_distance():
    result = verify_structural_frame_retention_roots_v8()
    manifest = result.manifest()
    assert manifest["physical_validation_eligible"] is False
    assert manifest["clearance_metadata_absolute_tolerance_mm"] == CLEARANCE_METADATA_ABSOLUTE_TOLERANCE_MM
    assert all(root["absolute_error_mm"] <= CLEARANCE_METADATA_ABSOLUTE_TOLERANCE_MM for root in manifest["roots"])


def test_v8_rejects_stale_generated_clearance_metadata():
    v7, generated, independent = _nominal_candidate()
    stale = list(generated)
    root_id, value = stale[0]
    stale[0] = (root_id, value + 0.01)
    with pytest.raises(StructuralFrameRetentionVerificationV8Error, match="disagrees with independent"):
        StructuralFrameRetentionVerificationV8(v7=v7, generated_clearances_mm=tuple(stale), independent_clearances_mm=independent).validate()


def test_v8_rejects_nonpositive_independent_clearance():
    v7, generated, independent = _nominal_candidate()
    bad = list(independent)
    bad[0] = (bad[0][0], 0.0)
    with pytest.raises(StructuralFrameRetentionVerificationV8Error, match="independent radial clearance must be finite and positive"):
        StructuralFrameRetentionVerificationV8(v7=v7, generated_clearances_mm=generated, independent_clearances_mm=tuple(bad)).validate()


def test_v8_rejects_missing_or_duplicate_clearance_identity():
    v7, generated, independent = _nominal_candidate()
    root_id, value = generated[0]
    with pytest.raises(StructuralFrameRetentionVerificationV8Error, match="exactly one wearer-left"):
        StructuralFrameRetentionVerificationV8(v7=v7, generated_clearances_mm=((root_id, value), (root_id, value)), independent_clearances_mm=independent).validate()


def test_v8_rejects_physical_validation_promotion():
    v7, generated, independent = _nominal_candidate()
    candidate = StructuralFrameRetentionVerificationV8(v7=v7, generated_clearances_mm=generated, independent_clearances_mm=independent)
    with pytest.raises(StructuralFrameRetentionVerificationV8Error, match="not physical validation"):
        replace(candidate, physical_validation_eligible=True).validate()
