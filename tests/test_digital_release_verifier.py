from hashlib import sha256
import os
from pathlib import Path
import subprocess

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
    source_provenance_for_registered_source,
    source_provenance_identity_sha256,
    verify_digital_release_export,
)


REGISTRY_REL = "config/digital_provenance_registry.yaml"
PRODUCT_REL = "generated/digital_product_release/product.json"
CLAIMS_REL = "generated/digital_product_release/claims.json"
PRODUCT_SOURCE_REL = "sources/product_source.json"
CLAIMS_SOURCE_REL = "sources/claims_source.json"
UNRELATED_SOURCE_REL = "sources/unrelated.json"


def _write(root: Path, relative: str, data: bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def _registry_bytes(
    *,
    product_source: str = PRODUCT_SOURCE_REL,
    claims_source: str = CLAIMS_SOURCE_REL,
) -> bytes:
    return (
        "schema: MASCK_ONE_DIGITAL_PROVENANCE_REGISTRY_V1\n"
        "artifact_kind_sources:\n"
        f"  PRODUCT_MANIFEST: {product_source}\n"
        f"  CLAIMS_MANIFEST: {claims_source}\n"
        f"  COMPONENT_MANIFEST: {product_source}\n"
        f"  DEVICE_STATE_MANIFEST: {product_source}\n"
        f"  VISUAL_SYSTEM_MANIFEST: {product_source}\n"
    ).encode("utf-8")


def _fixture(tmp_path: Path):
    product_bytes = b'{"product":"Masck One"}\n'
    claims_bytes = b'{"claims":[]}\n'
    product_source_bytes = b'{"source":"product-contract-v1"}\n'
    claims_source_bytes = b'{"source":"claims-contract-v1"}\n'
    unrelated_source_bytes = b'{"source":"unrelated-but-regular"}\n'

    _write(tmp_path, REGISTRY_REL, _registry_bytes())
    _write(tmp_path, PRODUCT_SOURCE_REL, product_source_bytes)
    _write(tmp_path, CLAIMS_SOURCE_REL, claims_source_bytes)
    _write(tmp_path, UNRELATED_SOURCE_REL, unrelated_source_bytes)

    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", REGISTRY_REL, PRODUCT_SOURCE_REL, CLAIMS_SOURCE_REL, UNRELATED_SOURCE_REL)
    _git(
        tmp_path,
        "-c",
        "user.name=Masck One Test",
        "-c",
        "user.email=masck-one-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "digital provenance fixture",
    )
    hardware_sha = _git(tmp_path, "rev-parse", "HEAD")

    _write(tmp_path, PRODUCT_REL, product_bytes)
    _write(tmp_path, CLAIMS_REL, claims_bytes)

    authority = load_authority()
    root = str(tmp_path)
    artifacts = (
        ReleaseArtifact(
            artifact_id="CLAIMS_ARTIFACT",
            kind=ArtifactKind.CLAIMS_MANIFEST,
            relative_path=CLAIMS_REL,
            media_type="application/json",
            revision=1,
            content_sha256=sha256(claims_bytes).hexdigest(),
            source_provenance_sha256=source_provenance_for_registered_source(
                repository_root=root,
                artifact_id="CLAIMS_ARTIFACT",
                artifact_kind=ArtifactKind.CLAIMS_MANIFEST,
                hardware_commit_sha=hardware_sha,
            ),
        ),
        ReleaseArtifact(
            artifact_id="PRODUCT_ARTIFACT",
            kind=ArtifactKind.PRODUCT_MANIFEST,
            relative_path=PRODUCT_REL,
            media_type="application/json",
            revision=1,
            content_sha256=sha256(product_bytes).hexdigest(),
            source_provenance_sha256=source_provenance_for_registered_source(
                repository_root=root,
                artifact_id="PRODUCT_ARTIFACT",
                artifact_kind=ArtifactKind.PRODUCT_MANIFEST,
                hardware_commit_sha=hardware_sha,
            ),
        ),
    )
    release = DigitalProductRelease(
        release_id="TEST_RELEASE",
        hardware_commit_sha=hardware_sha,
        authority_sha256=authority_content_sha256(authority),
        artifacts=artifacts,
    )
    return release, authority, hardware_sha


def _verify(tmp_path: Path, release, authority, hardware_sha):
    return verify_digital_release_export(
        release,
        repository_root=str(tmp_path),
        current_authority=authority,
        current_hardware_commit_sha=hardware_sha,
    )


def _replace_artifact(
    release: DigitalProductRelease,
    artifact_id: str,
    *,
    source_provenance_sha256: str | None = None,
) -> DigitalProductRelease:
    changed = []
    for artifact in release.artifacts:
        if artifact.artifact_id != artifact_id:
            changed.append(artifact)
            continue
        changed.append(
            ReleaseArtifact(
                artifact.artifact_id,
                artifact.kind,
                artifact.relative_path,
                artifact.media_type,
                artifact.revision,
                artifact.content_sha256,
                artifact.source_provenance_sha256
                if source_provenance_sha256 is None
                else source_provenance_sha256,
            )
        )
    return DigitalProductRelease(
        release.release_id,
        release.hardware_commit_sha,
        release.authority_sha256,
        tuple(changed),
    )


def test_release_verification_binds_real_bytes_authority_commit_and_registry(tmp_path):
    release, authority, hardware_sha = _fixture(tmp_path)
    report = _verify(tmp_path, release, authority, hardware_sha)
    assert report.release_sha256 == release.release_sha256
    assert report.hardware_commit_sha == hardware_sha
    assert report.authority_sha256 == release.authority_sha256
    assert len(report.provenance_registry_sha256) == 64
    assert tuple(item.artifact_id for item in report.artifacts) == (
        "CLAIMS_ARTIFACT",
        "PRODUCT_ARTIFACT",
    )
    assert report.physical_evidence_promoted is False


def test_declared_content_hash_does_not_substitute_for_actual_bytes(tmp_path):
    release, authority, hardware_sha = _fixture(tmp_path)
    (tmp_path / PRODUCT_REL).write_bytes(b'{"product":"substituted"}\n')
    with pytest.raises(DigitalReleaseError, match="content SHA-256 mismatch"):
        _verify(tmp_path, release, authority, hardware_sha)


def test_missing_artifact_fails_closed(tmp_path):
    release, authority, hardware_sha = _fixture(tmp_path)
    (tmp_path / CLAIMS_REL).unlink()
    with pytest.raises(DigitalReleaseError, match="missing"):
        _verify(tmp_path, release, authority, hardware_sha)


def test_swapped_artifact_files_fail_closed(tmp_path):
    release, authority, hardware_sha = _fixture(tmp_path)
    product = tmp_path / PRODUCT_REL
    claims = tmp_path / CLAIMS_REL
    product_bytes = product.read_bytes()
    claims_bytes = claims.read_bytes()
    product.write_bytes(claims_bytes)
    claims.write_bytes(product_bytes)
    with pytest.raises(DigitalReleaseError, match="content SHA-256 mismatch"):
        _verify(tmp_path, release, authority, hardware_sha)


def test_working_source_drift_cannot_masquerade_as_declared_commit(tmp_path):
    release, authority, hardware_sha = _fixture(tmp_path)
    (tmp_path / PRODUCT_SOURCE_REL).write_bytes(b'{"source":"working-tree-drift"}\n')
    with pytest.raises(DigitalReleaseError, match="differs from declared hardware commit"):
        _verify(tmp_path, release, authority, hardware_sha)


def test_unrelated_self_consistent_source_is_not_authorized(tmp_path):
    release, authority, hardware_sha = _fixture(tmp_path)
    unrelated_bytes = (tmp_path / UNRELATED_SOURCE_REL).read_bytes()
    forged = source_provenance_identity_sha256(
        artifact_id="PRODUCT_ARTIFACT",
        artifact_kind=ArtifactKind.PRODUCT_MANIFEST,
        hardware_commit_sha=hardware_sha,
        source_path=UNRELATED_SOURCE_REL,
        source_content_sha256=sha256(unrelated_bytes).hexdigest(),
    )
    forged_release = _replace_artifact(
        release,
        "PRODUCT_ARTIFACT",
        source_provenance_sha256=forged,
    )
    with pytest.raises(DigitalReleaseError, match="source provenance mismatch"):
        _verify(tmp_path, forged_release, authority, hardware_sha)


def test_working_registry_cannot_redirect_authorized_source(tmp_path):
    release, authority, hardware_sha = _fixture(tmp_path)
    (tmp_path / REGISTRY_REL).write_bytes(
        _registry_bytes(product_source=UNRELATED_SOURCE_REL)
    )
    with pytest.raises(
        DigitalReleaseError,
        match="working provenance registry differs from declared hardware commit",
    ):
        _verify(tmp_path, release, authority, hardware_sha)


def test_source_provenance_identity_binds_kind_commit_path_and_content():
    content_sha = sha256(b"source").hexdigest()
    hardware_sha = "1" * 40
    base = source_provenance_identity_sha256(
        artifact_id="PRODUCT_ARTIFACT",
        artifact_kind=ArtifactKind.PRODUCT_MANIFEST,
        hardware_commit_sha=hardware_sha,
        source_path="sources/product.json",
        source_content_sha256=content_sha,
    )
    assert base == source_provenance_identity_sha256(
        artifact_id="PRODUCT_ARTIFACT",
        artifact_kind=ArtifactKind.PRODUCT_MANIFEST,
        hardware_commit_sha=hardware_sha,
        source_path="sources/product.json",
        source_content_sha256=content_sha,
    )
    assert base != source_provenance_identity_sha256(
        artifact_id="PRODUCT_ARTIFACT",
        artifact_kind=ArtifactKind.CLAIMS_MANIFEST,
        hardware_commit_sha=hardware_sha,
        source_path="sources/product.json",
        source_content_sha256=content_sha,
    )
    assert base != source_provenance_identity_sha256(
        artifact_id="PRODUCT_ARTIFACT",
        artifact_kind=ArtifactKind.PRODUCT_MANIFEST,
        hardware_commit_sha="2" * 40,
        source_path="sources/product.json",
        source_content_sha256=content_sha,
    )
    assert base != source_provenance_identity_sha256(
        artifact_id="PRODUCT_ARTIFACT",
        artifact_kind=ArtifactKind.PRODUCT_MANIFEST,
        hardware_commit_sha=hardware_sha,
        source_path="sources/product_v2.json",
        source_content_sha256=content_sha,
    )


def test_unregistered_optional_artifact_kind_fails_closed(tmp_path):
    release, authority, hardware_sha = _fixture(tmp_path)
    glb_rel = "generated/digital_product_release/product.glb"
    glb_bytes = b"glTF-test-payload"
    _write(tmp_path, glb_rel, glb_bytes)
    optional = ReleaseArtifact(
        artifact_id="MODEL_GLTF",
        kind=ArtifactKind.WEB_GLTF,
        relative_path=glb_rel,
        media_type="model/gltf-binary",
        revision=1,
        content_sha256=sha256(glb_bytes).hexdigest(),
        source_provenance_sha256="a" * 64,
    )
    expanded = DigitalProductRelease(
        release.release_id,
        release.hardware_commit_sha,
        release.authority_sha256,
        release.artifacts + (optional,),
    )
    with pytest.raises(DigitalReleaseError, match="WEB_GLTF has no authorized provenance source"):
        _verify(tmp_path, expanded, authority, hardware_sha)


def test_forged_or_stale_authority_digest_rejected_with_same_hardware_commit(tmp_path):
    release, authority, hardware_sha = _fixture(tmp_path)
    forged = DigitalProductRelease(
        release_id=release.release_id,
        hardware_commit_sha=release.hardware_commit_sha,
        authority_sha256="f" * 64,
        artifacts=release.artifacts,
    )
    with pytest.raises(DigitalReleaseError, match="stale or forged"):
        _verify(tmp_path, forged, authority, hardware_sha)


def test_current_authority_hostile_same_value_alias_rejected(tmp_path):
    release, authority, hardware_sha = _fixture(tmp_path)

    class HostileStr(str):
        pass

    original = authority.data["project"]["name"]
    authority.data["project"]["name"] = HostileStr(original)
    with pytest.raises(DigitalReleaseError, match="aliased value type"):
        _verify(tmp_path, release, authority, hardware_sha)


def test_hardware_commit_remains_an_independent_release_gate(tmp_path):
    release, authority, _ = _fixture(tmp_path)
    with pytest.raises(DigitalReleaseError, match="stale digital release hardware commit"):
        verify_digital_release_export(
            release,
            repository_root=str(tmp_path),
            current_authority=authority,
            current_hardware_commit_sha="2" * 40,
        )


def test_post_construction_release_type_corruption_rejected_before_file_trust(tmp_path):
    release, authority, hardware_sha = _fixture(tmp_path)

    class HostileStr(str):
        pass

    object.__setattr__(
        release.artifacts[0],
        "content_sha256",
        HostileStr(release.artifacts[0].content_sha256),
    )
    with pytest.raises(DigitalReleaseError, match="content_sha256 must be exact"):
        _verify(tmp_path, release, authority, hardware_sha)


def test_artifact_symlink_is_not_accepted_as_verified_release_content(tmp_path):
    release, authority, hardware_sha = _fixture(tmp_path)
    artifact = tmp_path / PRODUCT_REL
    target = tmp_path / "outside_product.json"
    target.write_bytes(artifact.read_bytes())
    artifact.unlink()
    try:
        os.symlink(target, artifact)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    with pytest.raises(DigitalReleaseError, match="must not traverse symlinks"):
        _verify(tmp_path, release, authority, hardware_sha)


def test_registry_duplicate_key_is_rejected_from_declared_commit(tmp_path):
    release, authority, hardware_sha = _fixture(tmp_path)
    duplicate = (
        "schema: MASCK_ONE_DIGITAL_PROVENANCE_REGISTRY_V1\n"
        "artifact_kind_sources:\n"
        f"  PRODUCT_MANIFEST: {PRODUCT_SOURCE_REL}\n"
        f"  PRODUCT_MANIFEST: {UNRELATED_SOURCE_REL}\n"
        f"  CLAIMS_MANIFEST: {CLAIMS_SOURCE_REL}\n"
        f"  COMPONENT_MANIFEST: {PRODUCT_SOURCE_REL}\n"
        f"  DEVICE_STATE_MANIFEST: {PRODUCT_SOURCE_REL}\n"
        f"  VISUAL_SYSTEM_MANIFEST: {PRODUCT_SOURCE_REL}\n"
    ).encode("utf-8")
    (tmp_path / REGISTRY_REL).write_bytes(duplicate)
    _git(tmp_path, "add", REGISTRY_REL)
    _git(
        tmp_path,
        "-c",
        "user.name=Masck One Test",
        "-c",
        "user.email=masck-one-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "hostile duplicate registry",
    )
    hostile_sha = _git(tmp_path, "rev-parse", "HEAD")
    hostile_release = DigitalProductRelease(
        release.release_id,
        hostile_sha,
        release.authority_sha256,
        release.artifacts,
    )
    with pytest.raises(DigitalReleaseError, match="duplicate mapping key"):
        _verify(tmp_path, hostile_release, authority, hostile_sha)


def test_controlled_file_hash_rejects_traversal_before_filesystem_access(tmp_path):
    with pytest.raises(DigitalReleaseError, match="traversal"):
        controlled_file_sha256(
            repository_root=str(tmp_path),
            relative_path="generated/../outside.json",
        )
