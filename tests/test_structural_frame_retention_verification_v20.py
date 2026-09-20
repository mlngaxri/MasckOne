from dataclasses import replace

import pytest

from masck_one.model import build_model
from masck_one.structural_frame_retention_roots import build_structural_frame_retention_roots
from masck_one.structural_frame_retention_verification_v20 import (
    StructuralFrameRetentionVerificationV20,
    StructuralFrameRetentionVerificationV20Error,
    build_structural_frame_retention_verification_v20,
)


def test_v20_binds_roots_to_current_model_reaction_architecture() -> None:
    evidence = build_structural_frame_retention_verification_v20()
    assert evidence.recorded_source_sha256 == evidence.expected_source_sha256
    assert evidence.manifest()["source_binding_match"] is True


def test_v20_rejects_stale_or_foreign_root_provenance() -> None:
    model = build_model()
    roots = build_structural_frame_retention_roots(model=model)
    stale = replace(roots, source_frame_reaction_architecture_sha256="0" * 64)
    with pytest.raises(StructuralFrameRetentionVerificationV20Error, match="not bound"):
        build_structural_frame_retention_verification_v20(roots=stale, model=model)


@pytest.mark.parametrize("bad", ["", "abc", "g" * 63])
def test_v20_rejects_malformed_source_digest(bad: str) -> None:
    with pytest.raises(StructuralFrameRetentionVerificationV20Error, match="SHA-256 is invalid"):
        StructuralFrameRetentionVerificationV20(bad, "a" * 64).validate()


def test_v20_rejects_physical_validation_promotion() -> None:
    with pytest.raises(StructuralFrameRetentionVerificationV20Error, match="not physical validation"):
        StructuralFrameRetentionVerificationV20("a" * 64, "a" * 64, True).validate()
