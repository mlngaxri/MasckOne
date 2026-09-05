from __future__ import annotations

import pytest

import masck_one.retention_load_path_release as release_module
from masck_one.retention_load_path_release import (
    RetentionLoadPathReleaseError,
    SOURCE_OCCIPITAL_STABILIZER_GIT_BLOB_SHA,
    build_retention_load_path_release,
)


def test_release_manifest_records_exact_occipital_stabilizer_source_blob():
    release = build_retention_load_path_release()
    assert release.manifest()["source_occipital_stabilizer_git_blob_sha"] == (
        SOURCE_OCCIPITAL_STABILIZER_GIT_BLOB_SHA
    )


def test_release_occipital_source_blob_tamper_fails_closed(monkeypatch):
    source = build_retention_load_path_release().source
    monkeypatch.setattr(
        release_module,
        "SOURCE_OCCIPITAL_STABILIZER_GIT_BLOB_SHA",
        "0" * 40,
    )
    with pytest.raises(RetentionLoadPathReleaseError, match="requires explicit rebind"):
        release_module.build_retention_load_path_release(source)
