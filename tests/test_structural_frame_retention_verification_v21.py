from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_roots import build_structural_frame_retention_roots
from masck_one.structural_frame_retention_verification_v21 import (
    StructuralFrameRetentionVerificationV21,
    StructuralFrameRetentionVerificationV21Error,
    build_structural_frame_retention_verification_v21,
)


def test_v21_binds_complete_root_manifest_to_fresh_model_rebuild() -> None:
    verification = build_structural_frame_retention_verification_v21()
    assert verification.recorded_root_architecture_sha256 == verification.expected_root_architecture_sha256
    manifest = verification.manifest()
    assert manifest["fresh_root_rebuild_match"] is True
    assert manifest["physical_validation_eligible"] is False


def test_v21_rejects_mutated_retention_root_evidence_with_valid_upstream_source_digest() -> None:
    roots = build_structural_frame_retention_roots()
    left = roots.roots[0]
    hostile_left = replace(
        left,
        frame_capture_volume_mm3=left.frame_capture_volume_mm3 + 0.01,
    )
    hostile_roots = replace(roots, roots=(hostile_left, roots.roots[1]))

    # Upstream provenance is deliberately unchanged. V20's source binding alone cannot
    # prove that the complete retained root evidence still matches a fresh model rebuild.
    assert (
        hostile_roots.source_frame_reaction_architecture_sha256
        == roots.source_frame_reaction_architecture_sha256
    )
    with pytest.raises(StructuralFrameRetentionVerificationV21Error):
        build_structural_frame_retention_verification_v21(roots=hostile_roots)


@pytest.mark.parametrize(
    "digest",
    ["0" * 63, "g" * 64, "A" * 64, "0" * 63 + "\n"],
)
def test_v21_rejects_noncanonical_digest_evidence(digest: str) -> None:
    with pytest.raises(StructuralFrameRetentionVerificationV21Error):
        StructuralFrameRetentionVerificationV21(
            recorded_root_architecture_sha256=digest,
            expected_root_architecture_sha256="0" * 64,
        ).validate()


def test_v21_rejects_physical_validation_promotion() -> None:
    with pytest.raises(StructuralFrameRetentionVerificationV21Error):
        StructuralFrameRetentionVerificationV21(
            recorded_root_architecture_sha256="0" * 64,
            expected_root_architecture_sha256="0" * 64,
            physical_validation_eligible=True,
        ).validate()
