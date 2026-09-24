from dataclasses import replace

import pytest

from masck_one.model import build_model
from masck_one.structural_frame_retention_roots import build_structural_frame_retention_roots
from masck_one.structural_frame_retention_verification_v6 import verify_structural_frame_retention_roots_v6
from masck_one.structural_frame_retention_verification_v7 import (
    CAPTURE_METADATA_RELATIVE_TOLERANCE,
    StructuralFrameRetentionVerificationV7,
    StructuralFrameRetentionVerificationV7Error,
    verify_structural_frame_retention_roots_v7,
)


def _generated_for(v6):
    return tuple(
        (root.root_id, root.source_frame_capture_mm3)
        for root in v6.v5.v4.v3.v2.roots
    )


def test_nominal_v7_generator_capture_matches_independent_brep():
    result = verify_structural_frame_retention_roots_v7()
    manifest = result.manifest()
    assert manifest["physical_validation_eligible"] is False
    assert manifest["capture_metadata_relative_tolerance"] == CAPTURE_METADATA_RELATIVE_TOLERANCE
    assert all(root["relative_error"] <= CAPTURE_METADATA_RELATIVE_TOLERANCE for root in manifest["roots"])


def test_v7_uses_supplied_architecture_metadata():
    model = build_model()
    architecture = build_structural_frame_retention_roots(model=model)
    result = verify_structural_frame_retention_roots_v7(model=model, architecture=architecture)
    assert dict(result.generated_capture_volumes_mm3) == {
        root.root_id: root.frame_capture_volume_mm3 for root in architecture.roots
    }


def test_v7_rejects_stale_or_mixed_capture_metadata():
    v6 = verify_structural_frame_retention_roots_v6()
    generated = list(_generated_for(v6))
    root_id, value = generated[0]
    generated[0] = (root_id, value * 1.01)
    with pytest.raises(StructuralFrameRetentionVerificationV7Error, match="disagrees with independent"):
        StructuralFrameRetentionVerificationV7(v6=v6, generated_capture_volumes_mm3=tuple(generated)).validate()


def test_v7_rejects_missing_or_duplicate_metadata_identity():
    v6 = verify_structural_frame_retention_roots_v6()
    root_id, value = _generated_for(v6)[0]
    with pytest.raises(StructuralFrameRetentionVerificationV7Error, match="exactly one wearer-left"):
        StructuralFrameRetentionVerificationV7(
            v6=v6,
            generated_capture_volumes_mm3=((root_id, value), (root_id, value)),
        ).validate()


@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf")])
def test_v7_rejects_invalid_generated_capture_metadata(value):
    v6 = verify_structural_frame_retention_roots_v6()
    generated = list(_generated_for(v6))
    generated[0] = (generated[0][0], value)
    with pytest.raises(StructuralFrameRetentionVerificationV7Error, match="finite and positive"):
        StructuralFrameRetentionVerificationV7(v6=v6, generated_capture_volumes_mm3=tuple(generated)).validate()


def test_v7_rejects_physical_validation_promotion():
    v6 = verify_structural_frame_retention_roots_v6()
    candidate = StructuralFrameRetentionVerificationV7(v6=v6, generated_capture_volumes_mm3=_generated_for(v6))
    with pytest.raises(StructuralFrameRetentionVerificationV7Error, match="not physical validation"):
        replace(candidate, physical_validation_eligible=True).validate()
