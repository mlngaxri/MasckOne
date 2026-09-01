"""Filesystem and authority verification for Masck One digital product releases.

The release manifest is a declaration until this module verifies the actual exported
bytes, the exact currently validated authority content, and the concrete owning
source-provenance files. This is a digital trust boundary only; it never promotes
any artifact to physical evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat

from .authority import Authority, AuthorityError, validate_authority_data
from .digital_release import (
    DigitalProductRelease,
    DigitalReleaseError,
    validate_current_hardware_commit,
)


_PROVENANCE_SCHEMA = "MASCK_ONE_SOURCE_PROVENANCE_V1"
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_ID_RE = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z")


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


def _artifact_id(value: object) -> str:
    value = _exact_text(value, "artifact_id")
    if _ID_RE.fullmatch(value) is None:
        raise DigitalReleaseError("artifact_id must be canonical ASCII uppercase identifier")
    return value


def _canonical_repo_path(value: object, label: str) -> str:
    value = _exact_text(value, label)
    if "\\" in value or value.startswith("/"):
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
    source_path: str,
    source_content_sha256: str,
) -> str:
    """Bind an artifact to one named owning source contract/report/manifest file."""
    artifact_id = _artifact_id(artifact_id)
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


def controlled_file_sha256(*, repository_root: str, relative_path: str) -> str:
    """Compute a SHA-256 only after repository-relative file safety checks pass."""
    root = _resolve_repository_root(repository_root)
    return _hash_controlled_file(root, relative_path, label="controlled file")


def source_provenance_for_file(
    *,
    repository_root: str,
    artifact_id: str,
    source_path: str,
) -> str:
    """Compute the provenance identity from an actual controlled source file."""
    root = _resolve_repository_root(repository_root)
    source_path = _canonical_repo_path(source_path, "source_path")
    source_content_sha256 = _hash_controlled_file(
        root,
        source_path,
        label="source provenance file",
    )
    return source_provenance_identity_sha256(
        artifact_id=artifact_id,
        source_path=source_path,
        source_content_sha256=source_content_sha256,
    )


def verify_digital_release_export(
    release: DigitalProductRelease,
    *,
    repository_root: str,
    current_authority: Authority,
    current_hardware_commit_sha: str,
    provenance_paths: dict[str, str],
) -> DigitalReleaseVerificationReport:
    """Verify a release against actual bytes and current engineering identities.

    ``provenance_paths`` maps each artifact ID to the repository-relative path of the
    released owning source contract/report/manifest whose content the artifact's
    ``source_provenance_sha256`` binds via :func:`source_provenance_identity_sha256`.
    """
    if type(release) is not DigitalProductRelease:
        raise DigitalReleaseError("release must be exact DigitalProductRelease")
    release.validate_invariants()
    validate_current_hardware_commit(
        release,
        current_hardware_commit_sha=current_hardware_commit_sha,
    )
    if type(provenance_paths) is not dict or any(
        type(key) is not str or type(value) is not str
        for key, value in provenance_paths.items()
    ):
        raise DigitalReleaseError("provenance_paths must be exact string-to-string mapping")
    artifact_ids = tuple(artifact.artifact_id for artifact in release.artifacts)
    if set(provenance_paths) != set(artifact_ids):
        raise DigitalReleaseError("provenance_paths must cover every artifact exactly once")

    authority_sha256 = authority_content_sha256(current_authority)
    if release.authority_sha256 != authority_sha256:
        raise DigitalReleaseError("digital release is stale or forged for current authority content")

    root = _resolve_repository_root(repository_root)
    verified: list[VerifiedArtifactRecord] = []
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

        source_path = _canonical_repo_path(
            provenance_paths[artifact.artifact_id],
            f"provenance path for {artifact.artifact_id}",
        )
        if source_path == artifact.relative_path:
            raise DigitalReleaseError(
                f"artifact {artifact.artifact_id} cannot self-declare source provenance"
            )
        source_content_sha256 = _hash_controlled_file(
            root,
            source_path,
            label=f"source provenance for {artifact.artifact_id}",
        )
        expected_provenance = source_provenance_identity_sha256(
            artifact_id=artifact.artifact_id,
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

    return DigitalReleaseVerificationReport(
        release_sha256=release.release_sha256,
        hardware_commit_sha=release.hardware_commit_sha,
        authority_sha256=authority_sha256,
        artifacts=tuple(verified),
        physical_evidence_promoted=False,
    )
