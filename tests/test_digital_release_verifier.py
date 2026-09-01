from hashlib import sha256
import os
from pathlib import Path

import pytest

from masck_one.authority import load_authority
from masck_one.digital_release import (
    ArtifactKind,
    DigitalProductRelease,
    DigitalReleaseError,
    ReleaseArtifact,
)
from masck_one.digital_release_verifier import (
    authority_content_sha256,
    controlled_file_sha256,
    source_provenance_for_file,
    source_provenance_identity_sha256,
    verify_digital_release_export,
)


HARDWARE_SHA = "1" * 40


def _write(root: Path, relative: str, data: bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _fixture(tmp_path: Path):
    product_rel = "generated/digital_product_release/product.json"
    claims_rel = "generated/digital_product_release/claims.json"
    product_source_rel = "generated/source_contracts/product_source.json"
    claims_source_rel = "generated/source_contracts/claims_source.json"

    product_bytes = b'{"product":"Masck One"}\n'
    claims_bytes = b'{"claims":[]}\n'
    product_source_bytes = b'{"source":"product-contract-v1"}\n'
    claims_source_bytes = b'{"source":"claims-contract-v1"}\n'

    _write(tmp_path, product_rel, product_bytes)
    _write(tmp_path, claims_rel, claims_bytes)
    _write(tmp_path, product_source_rel, product_source_bytes)
    _write(tmp_path, claims_source_rel, claims_source_bytes)

    authority = load_authority()
    root = str(tmp_path)
    artifacts = (
        ReleaseArtifact(
            artifact_id="CLAIMS_ARTIFACT",
            kind=ArtifactKind.CLAIMS_MANIFEST,
            relative_path=claims_rel,
            media_type="application/json",
            revision=1,
            content_sha256=sha256(claims_bytes).hexdigest(),
            source_provenance_sha256=source_provenance_for_file(
                repository_root=root,
                artifact_id="CLAIMS_ARTIFACT",
                source_path=claims_source_rel,
            ),
        ),
        ReleaseArtifact(
            artifact_id="PRODUCT_ARTIFACT",
            kind=ArtifactKind.PRODUCT_MANIFEST,
            relative_path=product_rel,
            media_type="application/json",
            revision=1,
            content_sha256=sha256(product_bytes).hexdigest(),
            source_provenance_sha256=source_provenance_for_file(
                repository_root=root,
                artifact_id="PRODUCT_ARTIFACT",
                source_path=product_source_rel,
            ),
        ),
    )
    release = DigitalProductRelease(
        release_id="TEST_RELEASE",
        hardware_commit_sha=HARDWARE_SHA,
        authority_sha256=authority_content_sha256(authority),
        artifacts=artifacts,
    )
    provenance_paths = {
        "CLAIMS_ARTIFACT": claims_source_rel,
        "PRODUCT_ARTIFACT": product_source_rel,
    }
    return release, authority, provenance_paths


def _verify(tmp_path: Path, release, authority, provenance_paths):
    return verify_digital_release_export(
        release,
        repository_root=str(tmp_path),
        current_authority=authority,
        current_hardware_commit_sha=HARDWARE_SHA,
        provenance_paths=provenance_paths,
    )


def test_release_verification_binds_real_bytes_authority_and_provenance(tmp_path):
    release, authority, provenance_paths = _fixture(tmp_path)
    report = _verify(tmp_path, release, authority, provenance_paths)
    assert report.release_sha256 == release.release_sha256
    assert report.hardware_commit_sha == HARDWARE_SHA
    assert report.authority_sha256 == release.authority_sha256
    assert tuple(item.artifact_id for item in report.artifacts) == (
        "CLAIMS_ARTIFACT",
        "PRODUCT_ARTIFACT",
    )
    assert report.physical_evidence_promoted is False


def test_declared_content_hash_does_not_substitute_for_actual_bytes(tmp_path):
    release, authority, provenance_paths = _fixture(tmp_path)
    path = tmp_path / "generated/digital_product_release/product.json"
    path.write_bytes(b'{"product":"substituted"}\n')
    with pytest.raises(DigitalReleaseError, match="content SHA-256 mismatch"):
        _verify(tmp_path, release, authority, provenance_paths)


def test_missing_artifact_fails_closed(tmp_path):
    release, authority, provenance_paths = _fixture(tmp_path)
    (tmp_path / "generated/digital_product_release/claims.json").unlink()
    with pytest.raises(DigitalReleaseError, match="missing"):
        _verify(tmp_path, release, authority, provenance_paths)


def test_swapped_artifact_files_fail_closed(tmp_path):
    release, authority, provenance_paths = _fixture(tmp_path)
    product = tmp_path / "generated/digital_product_release/product.json"
    claims = tmp_path / "generated/digital_product_release/claims.json"
    product_bytes = product.read_bytes()
    claims_bytes = claims.read_bytes()
    product.write_bytes(claims_bytes)
    claims.write_bytes(product_bytes)
    with pytest.raises(DigitalReleaseError, match="content SHA-256 mismatch"):
        _verify(tmp_path, release, authority, provenance_paths)


def test_source_provenance_binds_actual_source_file_content(tmp_path):
    release, authority, provenance_paths = _fixture(tmp_path)
    source = tmp_path / "generated/source_contracts/product_source.json"
    source.write_bytes(b'{"source":"stale-or-substituted"}\n')
    with pytest.raises(DigitalReleaseError, match="source provenance mismatch"):
        _verify(tmp_path, release, authority, provenance_paths)


def test_source_provenance_identity_binds_path_as_well_as_content(tmp_path):
    release, authority, provenance_paths = _fixture(tmp_path)
    original = tmp_path / "generated/source_contracts/product_source.json"
    alternate_rel = "generated/source_contracts/copied_product_source.json"
    _write(tmp_path, alternate_rel, original.read_bytes())
    changed = dict(provenance_paths)
    changed["PRODUCT_ARTIFACT"] = alternate_rel
    with pytest.raises(DigitalReleaseError, match="source provenance mismatch"):
        _verify(tmp_path, release, authority, changed)


def test_source_provenance_identity_is_deterministic_and_not_an_opaque_string():
    content_sha = sha256(b"source").hexdigest()
    first = source_provenance_identity_sha256(
        artifact_id="PRODUCT_ARTIFACT",
        source_path="generated/source_contracts/product.json",
        source_content_sha256=content_sha,
    )
    second = source_provenance_identity_sha256(
        artifact_id="PRODUCT_ARTIFACT",
        source_path="generated/source_contracts/product.json",
        source_content_sha256=content_sha,
    )
    different_path = source_provenance_identity_sha256(
        artifact_id="PRODUCT_ARTIFACT",
        source_path="generated/source_contracts/product_v2.json",
        source_content_sha256=content_sha,
    )
    assert first == second
    assert first != different_path


def test_forged_or_stale_authority_digest_rejected_with_same_hardware_commit(tmp_path):
    release, authority, provenance_paths = _fixture(tmp_path)
    forged = DigitalProductRelease(
        release_id=release.release_id,
        hardware_commit_sha=release.hardware_commit_sha,
        authority_sha256="f" * 64,
        artifacts=release.artifacts,
    )
    with pytest.raises(DigitalReleaseError, match="stale or forged"):
        _verify(tmp_path, forged, authority, provenance_paths)


def test_current_authority_hostile_same_value_alias_rejected(tmp_path):
    release, authority, provenance_paths = _fixture(tmp_path)

    class HostileStr(str):
        pass

    original = authority.data["project"]["name"]
    authority.data["project"]["name"] = HostileStr(original)
    with pytest.raises(DigitalReleaseError, match="aliased value type"):
        _verify(tmp_path, release, authority, provenance_paths)


def test_hardware_commit_remains_an_independent_release_gate(tmp_path):
    release, authority, provenance_paths = _fixture(tmp_path)
    with pytest.raises(DigitalReleaseError, match="stale digital release hardware commit"):
        verify_digital_release_export(
            release,
            repository_root=str(tmp_path),
            current_authority=authority,
            current_hardware_commit_sha="2" * 40,
            provenance_paths=provenance_paths,
        )


def test_post_construction_release_type_corruption_rejected_before_file_trust(tmp_path):
    release, authority, provenance_paths = _fixture(tmp_path)

    class HostileStr(str):
        pass

    object.__setattr__(
        release.artifacts[0],
        "content_sha256",
        HostileStr(release.artifacts[0].content_sha256),
    )
    with pytest.raises(DigitalReleaseError, match="content_sha256 must be exact"):
        _verify(tmp_path, release, authority, provenance_paths)


def test_artifact_symlink_is_not_accepted_as_verified_release_content(tmp_path):
    release, authority, provenance_paths = _fixture(tmp_path)
    artifact = tmp_path / "generated/digital_product_release/product.json"
    target = tmp_path / "outside_product.json"
    target.write_bytes(artifact.read_bytes())
    artifact.unlink()
    try:
        os.symlink(target, artifact)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    with pytest.raises(DigitalReleaseError, match="must not traverse symlinks"):
        _verify(tmp_path, release, authority, provenance_paths)


def test_provenance_path_must_not_self_reference_artifact(tmp_path):
    release, authority, provenance_paths = _fixture(tmp_path)
    changed = dict(provenance_paths)
    changed["PRODUCT_ARTIFACT"] = "generated/digital_product_release/product.json"
    with pytest.raises(DigitalReleaseError, match="cannot self-declare"):
        _verify(tmp_path, release, authority, changed)


def test_controlled_file_hash_rejects_traversal_before_filesystem_access(tmp_path):
    with pytest.raises(DigitalReleaseError, match="traversal"):
        controlled_file_sha256(
            repository_root=str(tmp_path),
            relative_path="generated/../outside.json",
        )
