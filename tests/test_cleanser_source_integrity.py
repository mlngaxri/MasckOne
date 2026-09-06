from dataclasses import replace
from hashlib import sha1
from pathlib import Path

import pytest

from masck_one.cleanser_graph import AUTHORED_AGAINST_RELEASED_MAIN_SHA
from masck_one.cleanser_source_integrity import (
    RELEASED_MAIN_SHA,
    TRANSITIVE_RELEASED_PRODUCER_BLOBS,
    CleanserSourceIntegrityError,
    build_transitive_released_producers,
)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def test_cleanser_receipt_and_transitive_integrity_share_exact_released_main():
    assert RELEASED_MAIN_SHA == AUTHORED_AGAINST_RELEASED_MAIN_SHA
    assert RELEASED_MAIN_SHA == "afe29ff78419b6625dca5594974b6351f6f80e1b"


def test_all_transitive_released_producer_blobs_match_checkout():
    root = Path(__file__).resolve().parents[1]
    producers = build_transitive_released_producers()
    assert tuple((item.producer_id, item.path, item.blob_sha) for item in producers) == TRANSITIVE_RELEASED_PRODUCER_BLOBS
    for producer in producers:
        path = root / producer.path
        assert path.is_file(), producer.producer_id
        assert _git_blob_sha(path) == producer.blob_sha, producer.producer_id


def test_transitive_producer_graph_has_unique_ids_paths_and_expected_critical_chain():
    producers = build_transitive_released_producers()
    ids = {item.producer_id for item in producers}
    assert {
        "AUTHORITY_SCHEMA",
        "AUTHORITY_LOADER",
        "MODEL",
        "COVERAGE",
        "BOUNDARY_RELEASE",
        "INTERFACE_ATTACHMENT",
        "STRUCTURAL_FRAME",
        "WATER_RESERVOIR",
        "PROTECTED_VOLUMES",
    } <= ids
    assert len({item.producer_id for item in producers}) == len(producers)
    assert len({item.path for item in producers}) == len(producers)


def test_malformed_transitive_git_identity_fails_closed():
    producer = build_transitive_released_producers()[0]
    with pytest.raises(CleanserSourceIntegrityError, match="canonical lowercase"):
        replace(producer, blob_sha="A" * 40)
    with pytest.raises(CleanserSourceIntegrityError, match="canonical lowercase"):
        replace(producer, blob_sha="a" * 39)


def test_transitive_producer_manifest_is_plain_source_provenance_only():
    producers = build_transitive_released_producers()
    for producer in producers:
        assert producer.manifest() == {
            "producer_id": producer.producer_id,
            "path": producer.path,
            "blob_sha": producer.blob_sha,
        }
