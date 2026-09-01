"""Filesystem, authority, and commit-bound provenance verification for digital releases.

A digital release manifest is only a declaration until this module verifies the actual
exported bytes, the exact freshly validated authority content, and each artifact's
owning engineering source from the hardware commit named by the release. The owning
source is selected by a versioned registry stored in that same commit, never by a
caller-supplied path. This remains a digital trust boundary only and cannot promote
any artifact to physical evidence.
"""
from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess

import yaml

from .authority import Authority, AuthorityError, validate_authority_data
from .digital_release import (
    ArtifactKind,
    DigitalProductRelease,
    DigitalReleaseError,
    validate_current_hardware_commit,
)


_PROVENANCE_SCHEMA = "MASCK_ONE_SOURCE_PROVENANCE_V2"
_REGISTRY_SCHEMA = "MASCK_ONE_DIGITAL_PROVENANCE_REGISTRY_V1"
_REGISTRY_PATH = "config/digital_provenance_registry.yaml"
_RELEASE_ROOT = "generated/digital_product_release/"
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_GIT_OBJECT_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_ID_RE = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z")
_REGISTRY_KINDS = frozenset(
    {
        ArtifactKind.PRODUCT_MANIFEST,
        ArtifactKind.CLAIMS_MANIFEST,
        ArtifactKind.COMPONENT_MANIFEST,
        ArtifactKind.DEVICE_STATE_MANIFEST,
        ArtifactKind.VISUAL_SYSTEM_MANIFEST,
    }
)


@dataclass(frozen=True, slots=True)
class VerifiedArtifactRecord:
    artifact_id: str
    relative_path: str
    content_sha256: str
    source_path: str
    source_content_sha256: str
    source_provenance_sha256: str


@dataclass(frozen=True, slots=True)
class DigitalReleaseVerificationReport:
    release_sha256: str
    hardware_commit_sha: str
    authority_sha256: str
    provenance_registry_sha256: str
    artifacts: tuple[VerifiedArtifactRecord, ...]
    physical_evidence_promoted: bool = False


def _exact_text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise DigitalReleaseError(f"{label} must be exact built-in nonblank text")
    return value


def _sha256_text(value: object, label: str) -> str:
    value = _exact_text(value, label)
    if _SHA256_RE.fullmatch(value) is None:
        raise DigitalReleaseError(f"{label} must be canonical lowercase SHA-256")
    return value


def _git_object(value: object, label: str = "hardware_commit_sha") -> str:
    value = _exact_text(value, label)
    if _GIT_OBJECT_RE.fullmatch(value) is None:
        raise DigitalReleaseError(f"{label} must be canonical lowercase Git object identity")
    return value


def _artifact_id(value: object) -> str:
    value = _exact_text(value, "artifact_id")
    if _ID_RE.fullmatch(value) is None:
        raise DigitalReleaseError("artifact_id must be canonical ASCII uppercase identifier")
    return value


def _artifact_kind(value: object) -> ArtifactKind:
    if type(value) is not ArtifactKind:
        raise DigitalReleaseError("artifact kind must be exact ArtifactKind")
    return value


def _canonical_repo_path(value: object, label: str) -> str:
    value = _exact_text(value, label)
    if "\\" in value or value.startswith("/") or "\x00" in value:
        raise DigitalReleaseError(f"{label} must be canonical POSIX repository-relative path")
    path = PurePosixPath(value)
    if path.as_posix() != value or any(part in ("", ".", "..") for part in path.parts):
        raise DigitalReleaseError(f"{label} must not contain path aliases or traversal")
    return value


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, OverflowError) as exc:
        raise DigitalReleaseError("value cannot be serialized canonically") from exc


def _snapshot_authority_value(value: object, path: str = "<root>") -> object:
    """Copy authority data while rejecting aliases and non-finite numeric state."""
    if value is None:
        return None
    if type(value) is bool:
        return value
    if type(value) is int:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise DigitalReleaseError(f"authority contains non-finite number at {path}")
        return 0.0 if value == 0.0 else value
    if type(value) is str:
        return value
    if type(value) is list:
        return [
            _snapshot_authority_value(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise DigitalReleaseError(f"authority mapping keys must be exact strings at {path}")
        return {
            key: _snapshot_authority_value(item, f"{path}.{key}")
            for key, item in value.items()
        }
    raise DigitalReleaseError(
        f"authority contains unsupported or aliased value type at {path}: {type(value).__name__}"
    )


def authority_content_sha256(authority: Authority) -> str:
    """Hash the exact current, freshly revalidated authority content.

    Formatting and YAML comments do not affect this identity. Typed document content does.
    The snapshot rejects hostile subclasses before schema/semantic validation.
    """
    if type(authority) is not Authority:
        raise DigitalReleaseError("authority must be exact Authority")
    if type(authority.data) is not dict:
        raise DigitalReleaseError("authority data must remain exact mapping")
    snapshot = _snapshot_authority_value(authority.data)
    assert type(snapshot) is dict
    try:
        report = validate_authority_data(
            snapshot,
            source="<digital-release-authority-snapshot>",
        )
    except AuthorityError as exc:
        raise DigitalReleaseError("current authority cannot be revalidated") from exc
    if not report.valid:
        raise DigitalReleaseError(
            f"current authority is not valid: {report.format_errors()}"
        )
    return sha256(_canonical_json(snapshot)).hexdigest()


def source_provenance_identity_sha256(
    *,
    artifact_id: str,
    artifact_kind: ArtifactKind,
    hardware_commit_sha: str,
    source_path: str,
    source_content_sha256: str,
) -> str:
    """Bind one artifact to its authorized source file from one exact hardware commit."""
    artifact_id = _artifact_id(artifact_id)
    artifact_kind = _artifact_kind(artifact_kind)
    hardware_commit_sha = _git_object(hardware_commit_sha)
    source_path = _canonical_repo_path(source_path, "source_path")
    source_content_sha256 = _sha256_text(
        source_content_sha256,
        "source_content_sha256",
    )
    return sha256(
        _canonical_json(
            {
                "schema": _PROVENANCE_SCHEMA,
                "artifact_id": artifact_id,
                "artifact_kind": artifact_kind.value,
                "hardware_commit_sha": hardware_commit_sha,
                "source_path": source_path,
                "source_content_sha256": source_content_sha256,
            }
        )
    ).hexdigest()


def _resolve_repository_root(repository_root: str) -> Path:
    repository_root = _exact_text(repository_root, "repository_root")
    raw = Path(repository_root)
    if raw.is_symlink():
        raise DigitalReleaseError("repository_root must not be a symlink")
    try:
        resolved = raw.resolve(strict=True)
    except OSError as exc:
        raise DigitalReleaseError("repository_root does not resolve to an existing path") from exc
    if not resolved.is_dir():
        raise DigitalReleaseError("repository_root must be a directory")
    return resolved


def _hash_controlled_file(root: Path, relative_path: str, *, label: str) -> str:
    relative_path = _canonical_repo_path(relative_path, label)
    parts = PurePosixPath(relative_path).parts
    cursor = root
    final_stat: os.stat_result | None = None
    for part in parts:
        cursor = cursor / part
        try:
            final_stat = cursor.lstat()
        except FileNotFoundError as exc:
            raise DigitalReleaseError(f"{label} is missing: {relative_path}") from exc
        except OSError as exc:
            raise DigitalReleaseError(f"{label} cannot be inspected: {relative_path}") from exc
        if stat.S_ISLNK(final_stat.st_mode):
            raise DigitalReleaseError(f"{label} must not traverse symlinks: {relative_path}")
    assert final_stat is not None
    if not stat.S_ISREG(final_stat.st_mode):
        raise DigitalReleaseError(f"{label} must be a regular file: {relative_path}")
    try:
        resolved = cursor.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise DigitalReleaseError(f"{label} escapes repository_root: {relative_path}") from exc

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(resolved, flags)
    except OSError as exc:
        raise DigitalReleaseError(f"{label} cannot be opened safely: {relative_path}") from exc
    digest = sha256()
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise DigitalReleaseError(f"{label} must remain a regular file: {relative_path}")
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    stable_fields_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    stable_fields_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if stable_fields_before != stable_fields_after:
        raise DigitalReleaseError(f"{label} changed while being verified: {relative_path}")
    return digest.hexdigest()


def _run_git(root: Path, args: list[str], *, label: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise DigitalReleaseError(f"git unavailable while verifying {label}") from exc
    if completed.returncode != 0:
        raise DigitalReleaseError(f"git could not verify {label}")
    return completed.stdout


def _require_git_repository_root(root: Path) -> None:
    raw = _run_git(root, ["rev-parse", "--show-toplevel"], label="repository root")
    try:
        reported = Path(raw.decode("utf-8").strip()).resolve(strict=True)
    except (UnicodeDecodeError, OSError) as exc:
        raise DigitalReleaseError("git repository root could not be resolved") from exc
    if reported != root:
        raise DigitalReleaseError("repository_root must be the exact Git worktree root")


def _git_blob_bytes(
    root: Path,
    *,
    commit_sha: str,
    relative_path: str,
    label: str,
) -> bytes:
    """Read one regular file exactly as stored by the declared Git commit."""
    commit_sha = _git_object(commit_sha)
    relative_path = _canonical_repo_path(relative_path, label)
    tree = _run_git(
        root,
        ["ls-tree", "-z", commit_sha, "--", relative_path],
        label=label,
    )
    entries = tuple(item for item in tree.split(b"\x00") if item)
    if len(entries) != 1:
        raise DigitalReleaseError(f"{label} is not one regular file in declared hardware commit")
    try:
        metadata, encoded_path = entries[0].split(b"\t", 1)
        mode, object_type, object_id = metadata.decode("ascii").split(" ")
        stored_path = encoded_path.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise DigitalReleaseError(f"{label} Git tree entry is malformed") from exc
    if stored_path != relative_path:
        raise DigitalReleaseError(f"{label} Git tree path identity mismatch")
    if mode not in {"100644", "100755"} or object_type != "blob":
        raise DigitalReleaseError(f"{label} must be a regular file in declared hardware commit")
    object_id = _git_object(object_id, f"{label} Git blob identity")
    return _run_git(root, ["cat-file", "blob", object_id], label=label)


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    loader.flatten_mapping(node)
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, Hashable):
            raise DigitalReleaseError("provenance registry contains an unhashable key")
        if key in mapping:
            raise DigitalReleaseError("provenance registry contains a duplicate mapping key")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _parse_provenance_registry(raw: bytes) -> dict[ArtifactKind, str]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DigitalReleaseError("provenance registry must be UTF-8") from exc
    try:
        payload = yaml.load(text, Loader=_UniqueKeySafeLoader)
    except yaml.YAMLError as exc:
        raise DigitalReleaseError("provenance registry YAML cannot be parsed") from exc
    if type(payload) is not dict or any(type(key) is not str for key in payload):
        raise DigitalReleaseError("provenance registry must be an exact string-keyed mapping")
    if set(payload) != {"schema", "artifact_kind_sources"}:
        raise DigitalReleaseError("provenance registry top-level contract drift")
    if _exact_text(payload["schema"], "provenance registry schema") != _REGISTRY_SCHEMA:
        raise DigitalReleaseError("unsupported provenance registry schema")
    sources = payload["artifact_kind_sources"]
    if type(sources) is not dict or any(type(key) is not str for key in sources):
        raise DigitalReleaseError("artifact_kind_sources must be an exact mapping")
    expected_names = {kind.value for kind in _REGISTRY_KINDS}
    if set(sources) != expected_names:
        raise DigitalReleaseError("provenance registry must authorize exactly the V1 manifest kinds")

    registry: dict[ArtifactKind, str] = {}
    for kind in sorted(_REGISTRY_KINDS, key=lambda item: item.value):
        path = _canonical_repo_path(sources[kind.value], f"source path for {kind.value}")
        if path.startswith(_RELEASE_ROOT) or path.startswith("products/") or path.startswith("generated/"):
            raise DigitalReleaseError(
                f"source path for {kind.value} must remain in controlled engineering source"
            )
        registry[kind] = path
    return registry


def _provenance_registry_for_commit(
    root: Path,
    hardware_commit_sha: str,
) -> tuple[dict[ArtifactKind, str], str]:
    hardware_commit_sha = _git_object(hardware_commit_sha)
    committed = _git_blob_bytes(
        root,
        commit_sha=hardware_commit_sha,
        relative_path=_REGISTRY_PATH,
        label="digital provenance registry",
    )
    committed_sha = sha256(committed).hexdigest()
    working_sha = _hash_controlled_file(
        root,
        _REGISTRY_PATH,
        label="working digital provenance registry",
    )
    if working_sha != committed_sha:
        raise DigitalReleaseError(
            "working provenance registry differs from declared hardware commit"
        )
    return _parse_provenance_registry(committed), committed_sha


def controlled_file_sha256(*, repository_root: str, relative_path: str) -> str:
    """Compute a SHA-256 only after repository-relative file safety checks pass."""
    root = _resolve_repository_root(repository_root)
    return _hash_controlled_file(root, relative_path, label="controlled file")


def source_provenance_for_registered_source(
    *,
    repository_root: str,
    artifact_id: str,
    artifact_kind: ArtifactKind,
    hardware_commit_sha: str,
) -> str:
    """Compute provenance only from the kind-authorized source in the bound commit."""
    artifact_id = _artifact_id(artifact_id)
    artifact_kind = _artifact_kind(artifact_kind)
    hardware_commit_sha = _git_object(hardware_commit_sha)
    root = _resolve_repository_root(repository_root)
    _require_git_repository_root(root)
    registry, _ = _provenance_registry_for_commit(root, hardware_commit_sha)
    if artifact_kind not in registry:
        raise DigitalReleaseError(
            f"artifact kind {artifact_kind.value} has no authorized provenance source"
        )
    source_path = registry[artifact_kind]
    committed_source = _git_blob_bytes(
        root,
        commit_sha=hardware_commit_sha,
        relative_path=source_path,
        label=f"authorized source for {artifact_kind.value}",
    )
    source_content_sha256 = sha256(committed_source).hexdigest()
    working_source_sha256 = _hash_controlled_file(
        root,
        source_path,
        label=f"working source for {artifact_kind.value}",
    )
    if working_source_sha256 != source_content_sha256:
        raise DigitalReleaseError(
            f"working source for {artifact_kind.value} differs from declared hardware commit"
        )
    return source_provenance_identity_sha256(
        artifact_id=artifact_id,
        artifact_kind=artifact_kind,
        hardware_commit_sha=hardware_commit_sha,
        source_path=source_path,
        source_content_sha256=source_content_sha256,
    )


def verify_digital_release_export(
    release: DigitalProductRelease,
    *,
    repository_root: str,
    current_authority: Authority,
    current_hardware_commit_sha: str,
) -> DigitalReleaseVerificationReport:
    """Verify release bytes and commit-authorized provenance fail closed.

    The provenance registry is read from ``release.hardware_commit_sha`` at the fixed
    repository path ``config/digital_provenance_registry.yaml``. Each source file is
    read from that same commit and must also match the current worktree byte-for-byte.
    Callers therefore cannot choose a convenient provenance file after the fact.
    """
    if type(release) is not DigitalProductRelease:
        raise DigitalReleaseError("release must be exact DigitalProductRelease")
    release.validate_invariants()
    release_sha256 = release.release_sha256
    validate_current_hardware_commit(
        release,
        current_hardware_commit_sha=current_hardware_commit_sha,
    )

    authority_sha256 = authority_content_sha256(current_authority)
    if release.authority_sha256 != authority_sha256:
        raise DigitalReleaseError("digital release is stale or forged for current authority content")

    root = _resolve_repository_root(repository_root)
    _require_git_repository_root(root)
    registry, registry_sha256 = _provenance_registry_for_commit(
        root,
        release.hardware_commit_sha,
    )

    verified: list[VerifiedArtifactRecord] = []
    source_commit_hashes: dict[str, str] = {}
    for artifact in release.artifacts:
        actual_content_sha256 = _hash_controlled_file(
            root,
            artifact.relative_path,
            label=f"artifact {artifact.artifact_id}",
        )
        if actual_content_sha256 != artifact.content_sha256:
            raise DigitalReleaseError(
                f"artifact {artifact.artifact_id} content SHA-256 mismatch"
            )

        if artifact.kind not in registry:
            raise DigitalReleaseError(
                f"artifact {artifact.artifact_id} kind {artifact.kind.value} has no authorized provenance source"
            )
        source_path = registry[artifact.kind]
        if source_path == artifact.relative_path:
            raise DigitalReleaseError(
                f"artifact {artifact.artifact_id} cannot self-declare source provenance"
            )
        committed_source = _git_blob_bytes(
            root,
            commit_sha=release.hardware_commit_sha,
            relative_path=source_path,
            label=f"authorized source for {artifact.artifact_id}",
        )
        source_content_sha256 = sha256(committed_source).hexdigest()
        working_source_sha256 = _hash_controlled_file(
            root,
            source_path,
            label=f"working source for {artifact.artifact_id}",
        )
        if working_source_sha256 != source_content_sha256:
            raise DigitalReleaseError(
                f"working source for {artifact.artifact_id} differs from declared hardware commit"
            )
        source_commit_hashes[source_path] = source_content_sha256
        expected_provenance = source_provenance_identity_sha256(
            artifact_id=artifact.artifact_id,
            artifact_kind=artifact.kind,
            hardware_commit_sha=release.hardware_commit_sha,
            source_path=source_path,
            source_content_sha256=source_content_sha256,
        )
        if expected_provenance != artifact.source_provenance_sha256:
            raise DigitalReleaseError(
                f"artifact {artifact.artifact_id} source provenance mismatch"
            )
        verified.append(
            VerifiedArtifactRecord(
                artifact.artifact_id,
                artifact.relative_path,
                actual_content_sha256,
                source_path,
                source_content_sha256,
                expected_provenance,
            )
        )

    if authority_content_sha256(current_authority) != authority_sha256:
        raise DigitalReleaseError("authority changed while digital release was being verified")
    if release.release_sha256 != release_sha256:
        raise DigitalReleaseError("release changed while digital release was being verified")
    if _hash_controlled_file(
        root,
        _REGISTRY_PATH,
        label="working digital provenance registry",
    ) != registry_sha256:
        raise DigitalReleaseError("provenance registry changed while release was being verified")
    for source_path, committed_sha256 in source_commit_hashes.items():
        if _hash_controlled_file(
            root,
            source_path,
            label=f"working provenance source {source_path}",
        ) != committed_sha256:
            raise DigitalReleaseError(
                f"provenance source changed while release was being verified: {source_path}"
            )
    for record in verified:
        if _hash_controlled_file(
            root,
            record.relative_path,
            label=f"artifact {record.artifact_id}",
        ) != record.content_sha256:
            raise DigitalReleaseError(
                f"artifact {record.artifact_id} changed while release was being verified"
            )

    return DigitalReleaseVerificationReport(
        release_sha256=release_sha256,
        hardware_commit_sha=release.hardware_commit_sha,
        authority_sha256=authority_sha256,
        provenance_registry_sha256=registry_sha256,
        artifacts=tuple(verified),
        physical_evidence_promoted=False,
    )
