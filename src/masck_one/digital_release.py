"""Fail-closed hardware-to-digital release boundary for Masck One.

Web and app workspaces consume exported artifacts from
``generated/digital_product_release/`` only. This module authenticates those
artifacts and their engineering provenance without promoting digital state to
physical evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping

import yaml


class DigitalReleaseError(ValueError):
    """Raised when a digital release or split-boundary invariant is violated."""


_RELEASE_SCHEMA = "MASCK_ONE_DIGITAL_PRODUCT_RELEASE_V1"
_SPLIT_SCHEMA = "MASCK_ONE_DIGITAL_REPO_SPLIT_V1"
_RELEASE_ROOT = "generated/digital_product_release/"
_EVIDENCE_BOUNDARY = "DIGITAL_BINDING_ONLY_NOT_PHYSICAL_EVIDENCE"
_ID_RE = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_GIT_COMMIT_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


class ArtifactKind(str, Enum):
    PRODUCT_MANIFEST = "PRODUCT_MANIFEST"
    CLAIMS_MANIFEST = "CLAIMS_MANIFEST"
    COMPONENT_MANIFEST = "COMPONENT_MANIFEST"
    ANIMATION_MANIFEST = "ANIMATION_MANIFEST"
    DEVICE_STATE_MANIFEST = "DEVICE_STATE_MANIFEST"
    VISUAL_SYSTEM_MANIFEST = "VISUAL_SYSTEM_MANIFEST"
    WEB_GLTF = "WEB_GLTF"
    EXPLODED_TRANSFORMS = "EXPLODED_TRANSFORMS"
    FLUID_ROUTES = "FLUID_ROUTES"
    MATERIAL_SLOTS = "MATERIAL_SLOTS"
    CAMERA_PRESETS = "CAMERA_PRESETS"
    POSTER_ASSET = "POSTER_ASSET"


class ConsumerProfile(str, Enum):
    WEB = "WEB"
    APP = "APP"


_REQUIRED_KINDS: Mapping[ConsumerProfile, frozenset[ArtifactKind]] = {
    ConsumerProfile.WEB: frozenset(
        {
            ArtifactKind.PRODUCT_MANIFEST,
            ArtifactKind.CLAIMS_MANIFEST,
            ArtifactKind.COMPONENT_MANIFEST,
            ArtifactKind.VISUAL_SYSTEM_MANIFEST,
        }
    ),
    ConsumerProfile.APP: frozenset(
        {
            ArtifactKind.PRODUCT_MANIFEST,
            ArtifactKind.CLAIMS_MANIFEST,
            ArtifactKind.DEVICE_STATE_MANIFEST,
            ArtifactKind.VISUAL_SYSTEM_MANIFEST,
        }
    ),
}


def _exact_text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise DigitalReleaseError(f"{label} must be exact built-in nonblank text")
    return value


def _canonical_id(value: object, label: str) -> str:
    value = _exact_text(value, label)
    if _ID_RE.fullmatch(value) is None:
        raise DigitalReleaseError(f"{label} must be canonical ASCII uppercase identifier")
    return value


def _sha256(value: object, label: str) -> str:
    value = _exact_text(value, label)
    if _SHA256_RE.fullmatch(value) is None:
        raise DigitalReleaseError(f"{label} must be canonical lowercase SHA-256")
    return value


def _git_commit(value: object, label: str = "hardware_commit_sha") -> str:
    value = _exact_text(value, label)
    if _GIT_COMMIT_RE.fullmatch(value) is None:
        raise DigitalReleaseError(f"{label} must be canonical lowercase Git commit identity")
    return value


def _positive_int(value: object, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise DigitalReleaseError(f"{label} must be an exact positive integer")
    return value


def _release_path(value: object) -> str:
    value = _exact_text(value, "relative_path")
    if "\\" in value or value.startswith("/"):
        raise DigitalReleaseError("relative_path must be canonical POSIX relative path")
    path = PurePosixPath(value)
    if path.as_posix() != value or any(part in ("", ".", "..") for part in path.parts):
        raise DigitalReleaseError("relative_path must not contain aliases or traversal")
    if not value.startswith(_RELEASE_ROOT) or value == _RELEASE_ROOT.rstrip("/"):
        raise DigitalReleaseError(
            f"relative_path must be a file below {_RELEASE_ROOT}"
        )
    return value


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


@dataclass(frozen=True, slots=True)
class ReleaseArtifact:
    artifact_id: str
    kind: ArtifactKind
    relative_path: str
    media_type: str
    revision: int
    content_sha256: str
    source_provenance_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", _canonical_id(self.artifact_id, "artifact_id"))
        if type(self.kind) is not ArtifactKind:
            raise DigitalReleaseError("kind must be exact ArtifactKind")
        object.__setattr__(self, "relative_path", _release_path(self.relative_path))
        object.__setattr__(self, "media_type", _exact_text(self.media_type, "media_type"))
        object.__setattr__(self, "revision", _positive_int(self.revision, "revision"))
        object.__setattr__(self, "content_sha256", _sha256(self.content_sha256, "content_sha256"))
        object.__setattr__(
            self,
            "source_provenance_sha256",
            _sha256(self.source_provenance_sha256, "source_provenance_sha256"),
        )

    def validate_invariants(self) -> None:
        ReleaseArtifact(
            self.artifact_id,
            self.kind,
            self.relative_path,
            self.media_type,
            self.revision,
            self.content_sha256,
            self.source_provenance_sha256,
        )

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "artifact_id": self.artifact_id,
            "kind": self.kind.value,
            "relative_path": self.relative_path,
            "media_type": self.media_type,
            "revision": self.revision,
            "content_sha256": self.content_sha256,
            "source_provenance_sha256": self.source_provenance_sha256,
        }


@dataclass(frozen=True, slots=True)
class DigitalProductRelease:
    release_id: str
    hardware_commit_sha: str
    authority_sha256: str
    artifacts: tuple[ReleaseArtifact, ...]
    physical_evidence_promoted: bool = False
    schema: str = _RELEASE_SCHEMA
    evidence_boundary: str = _EVIDENCE_BOUNDARY

    def __post_init__(self) -> None:
        object.__setattr__(self, "release_id", _canonical_id(self.release_id, "release_id"))
        object.__setattr__(self, "hardware_commit_sha", _git_commit(self.hardware_commit_sha))
        object.__setattr__(self, "authority_sha256", _sha256(self.authority_sha256, "authority_sha256"))
        if type(self.artifacts) is not tuple or any(type(item) is not ReleaseArtifact for item in self.artifacts):
            raise DigitalReleaseError("artifacts must be an exact tuple of ReleaseArtifact")
        ordered = tuple(sorted(self.artifacts, key=lambda item: item.artifact_id))
        if len({item.artifact_id for item in ordered}) != len(ordered):
            raise DigitalReleaseError("artifact_id values must be unique")
        singleton_kinds = {
            ArtifactKind.PRODUCT_MANIFEST,
            ArtifactKind.CLAIMS_MANIFEST,
            ArtifactKind.COMPONENT_MANIFEST,
            ArtifactKind.ANIMATION_MANIFEST,
            ArtifactKind.DEVICE_STATE_MANIFEST,
            ArtifactKind.VISUAL_SYSTEM_MANIFEST,
            ArtifactKind.EXPLODED_TRANSFORMS,
            ArtifactKind.FLUID_ROUTES,
            ArtifactKind.MATERIAL_SLOTS,
            ArtifactKind.CAMERA_PRESETS,
        }
        for kind in singleton_kinds:
            if sum(item.kind is kind for item in ordered) > 1:
                raise DigitalReleaseError(f"{kind.value} must not have multiple authorities")
        object.__setattr__(self, "artifacts", ordered)
        if type(self.physical_evidence_promoted) is not bool or self.physical_evidence_promoted:
            raise DigitalReleaseError("digital release cannot promote physical evidence")
        if type(self.schema) is not str or self.schema != _RELEASE_SCHEMA:
            raise DigitalReleaseError("unsupported digital release schema")
        if type(self.evidence_boundary) is not str or self.evidence_boundary != _EVIDENCE_BOUNDARY:
            raise DigitalReleaseError("digital evidence boundary must remain controlled")

    def validate_invariants(self) -> None:
        if type(self.artifacts) is not tuple:
            raise DigitalReleaseError("artifacts must remain immutable tuple")
        for artifact in self.artifacts:
            if type(artifact) is not ReleaseArtifact:
                raise DigitalReleaseError("artifacts must remain exact ReleaseArtifact values")
            artifact.validate_invariants()
        DigitalProductRelease(
            self.release_id,
            self.hardware_commit_sha,
            self.authority_sha256,
            self.artifacts,
            self.physical_evidence_promoted,
            self.schema,
            self.evidence_boundary,
        )

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "schema": self.schema,
            "release_id": self.release_id,
            "hardware_commit_sha": self.hardware_commit_sha,
            "authority_sha256": self.authority_sha256,
            "evidence_boundary": self.evidence_boundary,
            "physical_evidence_promoted": self.physical_evidence_promoted,
            "artifacts": [item.manifest() for item in self.artifacts],
        }

    @property
    def release_sha256(self) -> str:
        return sha256(_canonical_json(self.manifest())).hexdigest()


def validate_consumer_profile(release: DigitalProductRelease, profile: ConsumerProfile) -> None:
    if type(release) is not DigitalProductRelease:
        raise DigitalReleaseError("release must be exact DigitalProductRelease")
    if type(profile) is not ConsumerProfile:
        raise DigitalReleaseError("profile must be exact ConsumerProfile")
    release.validate_invariants()
    present = frozenset(item.kind for item in release.artifacts)
    missing = sorted(kind.value for kind in _REQUIRED_KINDS[profile] - present)
    if missing:
        raise DigitalReleaseError(
            f"{profile.value} release missing required artifact kinds: {', '.join(missing)}"
        )


def validate_current_hardware_commit(
    release: DigitalProductRelease,
    *,
    current_hardware_commit_sha: str,
) -> None:
    if type(release) is not DigitalProductRelease:
        raise DigitalReleaseError("release must be exact DigitalProductRelease")
    release.validate_invariants()
    current = _git_commit(current_hardware_commit_sha, "current_hardware_commit_sha")
    if release.hardware_commit_sha != current:
        raise DigitalReleaseError("stale digital release hardware commit")


def validate_repo_split_config(config: object) -> None:
    if type(config) is not dict:
        raise DigitalReleaseError("digital repo split config must be exact mapping")
    if config.get("schema") != _SPLIT_SCHEMA or type(config.get("schema")) is not str:
        raise DigitalReleaseError("unsupported digital repo split schema")
    if config.get("source_repository") != "mlngaxri/MasckOne":
        raise DigitalReleaseError("source_repository must remain authoritative hardware repo")
    if config.get("digital_release_root") != _RELEASE_ROOT:
        raise DigitalReleaseError("digital_release_root must remain canonical export root")
    if config.get("shared_contract_package") is not None:
        raise DigitalReleaseError("shared contract package is not yet authorized")
    roots = config.get("allowed_consumer_roots")
    if type(roots) is not list or roots != [_RELEASE_ROOT]:
        raise DigitalReleaseError("frontends may consume only the exported digital release root")

    workspaces = config.get("workspaces")
    if type(workspaces) is not dict or set(workspaces) != {"web", "app"}:
        raise DigitalReleaseError("split config must define exactly web and app workspaces")
    expected = {
        "web": ("MasckOne-Web", "products/web/"),
        "app": ("MasckOne-App", "products/app/"),
    }
    for name, (future_repo, prefix) in expected.items():
        item = workspaces[name]
        if type(item) is not dict:
            raise DigitalReleaseError(f"{name} workspace must be exact mapping")
        if item.get("future_repository") != future_repo or item.get("current_prefix") != prefix:
            raise DigitalReleaseError(f"{name} workspace migration identity drift")
        for command_name in ("build_command", "test_command", "typecheck_command"):
            _exact_text(item.get(command_name), f"{name}.{command_name}")
        env = item.get("environment_schema")
        if type(env) is not list:
            raise DigitalReleaseError(f"{name}.environment_schema must be list")
        env_names: set[str] = set()
        for entry in env:
            if type(entry) is not dict or set(entry) != {"name", "secret"}:
                raise DigitalReleaseError(f"{name} environment entry malformed")
            env_name = _exact_text(entry["name"], f"{name} environment name")
            if env_name in env_names:
                raise DigitalReleaseError(f"{name} environment names must be unique")
            env_names.add(env_name)
            if type(entry["secret"]) is not bool:
                raise DigitalReleaseError(f"{name} environment secret flag must be exact bool")
        split_command = _exact_text(item.get("history_split_command"), f"{name}.history_split_command")
        required_fragment = f"--path {prefix} --path-rename {prefix}:"
        if required_fragment not in split_command:
            raise DigitalReleaseError(f"{name} history split command does not preserve prefix history")

    import_policy = config.get("import_policy")
    if type(import_policy) is not dict:
        raise DigitalReleaseError("import_policy must be exact mapping")
    if import_policy.get("rule") != "FRONTENDS_CONSUME_EXPORTED_RELEASES_ONLY":
        raise DigitalReleaseError("frontend import policy weakened")
    if import_policy.get("migration_is_administrative_not_rewrite") is not True:
        raise DigitalReleaseError("migration must remain administrative")
    forbidden = import_policy.get("forbidden_direct_roots")
    if type(forbidden) is not list or not {"src/", "config/masck_one_authority.yaml", "schemas/", "tests/"}.issubset(set(forbidden)):
        raise DigitalReleaseError("hardware direct-import firewall incomplete")

    release_policy = config.get("release_policy")
    required_release_flags = {
        "require_content_sha256",
        "require_source_provenance_sha256",
        "require_hardware_commit_binding",
        "reject_stale_release",
        "physical_evidence_promotion_forbidden",
    }
    if type(release_policy) is not dict or set(release_policy) != required_release_flags:
        raise DigitalReleaseError("release_policy must contain exact controlled flags")
    if any(value is not True for value in release_policy.values()):
        raise DigitalReleaseError("all digital release safety flags must remain enabled")


def load_repo_split_config(path: str | Path = "config/digital_repo_split.yaml") -> dict[str, object]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    validate_repo_split_config(payload)
    return payload
