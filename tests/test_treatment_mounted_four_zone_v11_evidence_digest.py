from __future__ import annotations

import hashlib
import json

import pytest

from masck_one import treatment_mounted_four_zone_v10 as v10
from masck_one import treatment_mounted_four_zone_v11 as v11
from masck_one.treatment_terminal_datum_preload_v5 import SOURCE_CELL6_HEAD_SHA


def _canonical_digest(payload: dict[str, object]) -> str:
    evidence = dict(payload)
    evidence.pop("promoted_evidence_sha256", None)
    canonical = json.dumps(
        evidence,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _manifest(monkeypatch, **extra):
    architecture = object()
    datums = object()
    upstream = {
        "schema": v10.SCHEMA_V10,
        "source_cell6_head_sha": SOURCE_CELL6_HEAD_SHA,
        **extra,
    }
    monkeypatch.setattr(v11, "_require_promoted_build_result", lambda a, d: (a, d))
    monkeypatch.setattr(v10, "manifest_v10", lambda a, d: upstream)
    return v11.manifest_v11(architecture, datums), upstream


def test_v11_digest_covers_complete_promoted_payload_without_mutating_v10(monkeypatch):
    promoted, upstream = _manifest(monkeypatch, upstream_marker="v10-owned")

    assert promoted["promoted_evidence_sha256"] == _canonical_digest(promoted)
    v11.verify_promoted_evidence_v11(promoted)
    assert "promoted_evidence_sha256" not in upstream
    assert upstream["schema"] == v10.SCHEMA_V10


def test_v11_digest_changes_when_promoted_collision_evidence_changes(monkeypatch):
    promoted, _ = _manifest(monkeypatch)
    altered = dict(promoted)
    altered.pop("promoted_evidence_sha256")
    altered["collision_kernel"] = "hostile-kernel"

    assert promoted["promoted_evidence_sha256"] != v11._promoted_evidence_sha256(altered)


def test_v11_verifier_rejects_post_materialization_tamper(monkeypatch):
    promoted, _ = _manifest(monkeypatch)
    promoted["collision_kernel"] = "hostile-kernel"

    with pytest.raises(v11.TreatmentMountedFourZoneV11Error, match="qualification field"):
        v11.verify_promoted_evidence_v11(promoted)


@pytest.mark.parametrize("bad_digest", [None, "", "0" * 63, b"0" * 64, "g" * 64, "A" * 64])
def test_v11_verifier_rejects_missing_or_malformed_digest(monkeypatch, bad_digest):
    promoted, _ = _manifest(monkeypatch)
    if bad_digest is None:
        promoted.pop("promoted_evidence_sha256")
    else:
        promoted["promoted_evidence_sha256"] = bad_digest

    with pytest.raises(v11.TreatmentMountedFourZoneV11Error, match="missing or malformed"):
        v11.verify_promoted_evidence_v11(promoted)


def test_v11_verifier_rejects_wrong_schema(monkeypatch):
    promoted, _ = _manifest(monkeypatch)
    promoted["schema"] = v10.SCHEMA_V10

    with pytest.raises(v11.TreatmentMountedFourZoneV11Error, match="requires V11 schema"):
        v11.verify_promoted_evidence_v11(promoted)


@pytest.mark.parametrize(
    ("field", "hostile"),
    [
        ("supersedes", "hostile-schema"),
        ("source_cell6_head_sha", "hostile-source"),
        ("collision_kernel", "hostile-kernel"),
        ("terminal_datum_verification", "hostile-terminal"),
        ("physical_architecture_changed_from_v10", True),
        ("collision_threshold_weakened", True),
        ("physical_validation_eligible", True),
    ],
)
def test_v11_verifier_rejects_rehashed_semantic_forgery(monkeypatch, field, hostile):
    promoted, _ = _manifest(monkeypatch)
    promoted[field] = hostile
    promoted["promoted_evidence_sha256"] = _canonical_digest(promoted)

    with pytest.raises(v11.TreatmentMountedFourZoneV11Error, match="qualification field"):
        v11.verify_promoted_evidence_v11(promoted)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf"), object()])
def test_v11_digest_fails_closed_for_noncanonical_evidence(monkeypatch, bad_value):
    architecture = object()
    datums = object()
    monkeypatch.setattr(v11, "_require_promoted_build_result", lambda a, d: (a, d))
    monkeypatch.setattr(
        v10,
        "manifest_v10",
        lambda a, d: {
            "schema": v10.SCHEMA_V10,
            "source_cell6_head_sha": SOURCE_CELL6_HEAD_SHA,
            "hostile": bad_value,
        },
    )

    with pytest.raises(v11.TreatmentMountedFourZoneV11Error, match="canonically serializable"):
        v11.manifest_v11(architecture, datums)
