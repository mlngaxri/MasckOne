from copy import deepcopy
import json
from pathlib import Path

import jsonschema
import pytest

from masck_one.digital_release import (
    ArtifactKind,
    ConsumerProfile,
    DigitalProductRelease,
    DigitalReleaseError,
    ReleaseArtifact,
    load_repo_split_config,
    validate_consumer_profile,
    validate_current_hardware_commit,
    validate_repo_split_config,
)

GIT_SHA = "a" * 40
OTHER_GIT_SHA = "b" * 40
AUTHORITY_SHA = "c" * 64


def artifact(kind: ArtifactKind, artifact_id: str, seed: str) -> ReleaseArtifact:
    return ReleaseArtifact(
        artifact_id=artifact_id,
        kind=kind,
        relative_path=f"generated/digital_product_release/{artifact_id.lower()}.json",
        media_type="application/json",
        revision=1,
        content_sha256=seed * 64,
        source_provenance_sha256=seed.upper().lower() * 64,
    )


def core_artifacts() -> tuple[ReleaseArtifact, ...]:
    return (
        artifact(ArtifactKind.PRODUCT_MANIFEST, "PRODUCT", "1"),
        artifact(ArtifactKind.CLAIMS_MANIFEST, "CLAIMS", "2"),
        artifact(ArtifactKind.COMPONENT_MANIFEST, "COMPONENTS", "3"),
        artifact(ArtifactKind.DEVICE_STATE_MANIFEST, "DEVICE_STATE", "4"),
        artifact(ArtifactKind.VISUAL_SYSTEM_MANIFEST, "VISUAL_SYSTEM", "5"),
    )


def release(artifacts: tuple[ReleaseArtifact, ...] | None = None) -> DigitalProductRelease:
    return DigitalProductRelease(
        release_id="DIGITAL_ALPHA_001",
        hardware_commit_sha=GIT_SHA,
        authority_sha256=AUTHORITY_SHA,
        artifacts=core_artifacts() if artifacts is None else artifacts,
    )


def test_release_is_deterministic_across_caller_artifact_order():
    a = release()
    b = release(tuple(reversed(core_artifacts())))
    assert a.manifest() == b.manifest()
    assert a.release_sha256 == b.release_sha256
    assert [item["artifact_id"] for item in a.manifest()["artifacts"]] == sorted(
        item.artifact_id for item in core_artifacts()
    )


def test_web_and_app_profiles_require_their_minimum_authoritative_manifests():
    r = release()
    validate_consumer_profile(r, ConsumerProfile.WEB)
    validate_consumer_profile(r, ConsumerProfile.APP)

    no_components = tuple(
        item for item in core_artifacts() if item.kind is not ArtifactKind.COMPONENT_MANIFEST
    )
    with pytest.raises(DigitalReleaseError, match="COMPONENT_MANIFEST"):
        validate_consumer_profile(release(no_components), ConsumerProfile.WEB)

    no_state = tuple(
        item for item in core_artifacts() if item.kind is not ArtifactKind.DEVICE_STATE_MANIFEST
    )
    with pytest.raises(DigitalReleaseError, match="DEVICE_STATE_MANIFEST"):
        validate_consumer_profile(release(no_state), ConsumerProfile.APP)


def test_stale_hardware_commit_fails_closed():
    validate_current_hardware_commit(release(), current_hardware_commit_sha=GIT_SHA)
    with pytest.raises(DigitalReleaseError, match="stale"):
        validate_current_hardware_commit(release(), current_hardware_commit_sha=OTHER_GIT_SHA)


def test_release_paths_are_confined_to_export_root_and_canonical():
    base = artifact(ArtifactKind.PRODUCT_MANIFEST, "PRODUCT", "1")
    for bad in (
        "src/masck_one/product.json",
        "generated/digital_product_release/../authority.yaml",
        "generated/digital_product_release//product.json",
        "/generated/digital_product_release/product.json",
        "generated\\digital_product_release\\product.json",
    ):
        with pytest.raises(DigitalReleaseError):
            ReleaseArtifact(
                base.artifact_id,
                base.kind,
                bad,
                base.media_type,
                base.revision,
                base.content_sha256,
                base.source_provenance_sha256,
            )


def test_type_aliases_and_invalid_hashes_fail_closed():
    class Alias(str):
        pass

    base = artifact(ArtifactKind.PRODUCT_MANIFEST, "PRODUCT", "1")
    with pytest.raises(DigitalReleaseError):
        ReleaseArtifact(
            Alias("PRODUCT"),
            base.kind,
            base.relative_path,
            base.media_type,
            base.revision,
            base.content_sha256,
            base.source_provenance_sha256,
        )
    with pytest.raises(DigitalReleaseError):
        ReleaseArtifact(
            base.artifact_id,
            base.kind,
            base.relative_path,
            base.media_type,
            True,
            base.content_sha256,
            base.source_provenance_sha256,
        )
    with pytest.raises(DigitalReleaseError):
        ReleaseArtifact(
            base.artifact_id,
            base.kind,
            base.relative_path,
            base.media_type,
            base.revision,
            "A" * 64,
            base.source_provenance_sha256,
        )
    with pytest.raises(DigitalReleaseError):
        DigitalProductRelease(
            Alias("DIGITAL_ALPHA_001"),
            GIT_SHA,
            AUTHORITY_SHA,
            core_artifacts(),
        )


def test_duplicate_ids_and_singleton_authorities_fail_closed():
    product = artifact(ArtifactKind.PRODUCT_MANIFEST, "PRODUCT", "1")
    duplicate_id = artifact(ArtifactKind.CLAIMS_MANIFEST, "PRODUCT", "2")
    with pytest.raises(DigitalReleaseError, match="artifact_id"):
        release((product, duplicate_id))

    second_product = artifact(ArtifactKind.PRODUCT_MANIFEST, "PRODUCT_ALT", "2")
    with pytest.raises(DigitalReleaseError, match="multiple authorities"):
        release((product, second_product))


def test_physical_evidence_cannot_be_promoted_by_digital_release():
    with pytest.raises(DigitalReleaseError, match="physical evidence"):
        DigitalProductRelease(
            "DIGITAL_ALPHA_001",
            GIT_SHA,
            AUTHORITY_SHA,
            core_artifacts(),
            physical_evidence_promoted=True,
        )


def test_post_construction_corruption_is_rejected_before_hash_or_consumption():
    r = release()
    object.__setattr__(r.artifacts[0], "relative_path", "src/masck_one/authority.py")
    with pytest.raises(DigitalReleaseError):
        _ = r.release_sha256

    r = release()
    object.__setattr__(r, "artifacts", tuple(reversed(r.artifacts)))
    with pytest.raises(DigitalReleaseError, match="canonical artifact order"):
        _ = r.release_sha256


def test_release_hash_binds_content_provenance_and_hardware_revision():
    baseline = release()
    altered_content = list(core_artifacts())
    altered_content[0] = ReleaseArtifact(
        "PRODUCT",
        ArtifactKind.PRODUCT_MANIFEST,
        "generated/digital_product_release/product.json",
        "application/json",
        1,
        "9" * 64,
        "1" * 64,
    )
    changed_content = release(tuple(altered_content))
    changed_hardware = DigitalProductRelease(
        "DIGITAL_ALPHA_001",
        OTHER_GIT_SHA,
        AUTHORITY_SHA,
        core_artifacts(),
    )
    assert baseline.release_sha256 != changed_content.release_sha256
    assert baseline.release_sha256 != changed_hardware.release_sha256


def test_split_config_is_valid_and_blocks_hardware_imports():
    config = load_repo_split_config()
    assert config["allowed_consumer_roots"] == ["generated/digital_product_release/"]
    assert config["workspaces"]["web"]["future_repository"] == "MasckOne-Web"
    assert config["workspaces"]["app"]["future_repository"] == "MasckOne-App"

    bad = deepcopy(config)
    bad["allowed_consumer_roots"] = ["src/"]
    with pytest.raises(DigitalReleaseError):
        validate_repo_split_config(bad)

    bad = deepcopy(config)
    bad["workspaces"]["web"]["environment_schema"][0]["secret"] = "false"
    with pytest.raises(DigitalReleaseError):
        validate_repo_split_config(bad)


def test_split_config_rejects_hostile_string_aliases_and_migration_drift():
    class Alias(str):
        pass

    config = load_repo_split_config()
    bad = deepcopy(config)
    bad["source_repository"] = Alias("mlngaxri/MasckOne")
    with pytest.raises(DigitalReleaseError):
        validate_repo_split_config(bad)

    bad = deepcopy(config)
    bad["workspaces"]["app"]["history_split_command"] = "git filter-repo --path products/web/"
    with pytest.raises(DigitalReleaseError, match="history split"):
        validate_repo_split_config(bad)


def test_json_schema_is_independently_valid_and_accepts_canonical_manifest():
    schema = json.loads(Path("schemas/digital_product_release.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(release().manifest(), schema)

    bad = release().manifest()
    bad["physical_evidence_promoted"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)

    bad = release().manifest()
    bad["artifacts"][0]["relative_path"] = "generated/digital_product_release/../authority.yaml"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)
