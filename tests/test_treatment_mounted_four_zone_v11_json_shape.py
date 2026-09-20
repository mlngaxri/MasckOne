from __future__ import annotations

import pytest

from masck_one import treatment_mounted_four_zone_v10 as v10
from masck_one import treatment_mounted_four_zone_v11 as v11
from masck_one.treatment_terminal_datum_preload_v5 import SOURCE_CELL6_HEAD_SHA


def _provenance() -> dict[str, object]:
    return {
        "source_cell6_head_sha": SOURCE_CELL6_HEAD_SHA,
        "source_cell6_geometry_head_sha": SOURCE_CELL6_HEAD_SHA,
        "source_cell6_head_semantics": v10.SOURCE_CELL6_HEAD_SEMANTICS,
        "active_cell6_owner_head_claimed": False,
        "live_cell6_owner_recheck_required_before_promotion": True,
    }


def _materialize(monkeypatch, hostile: object):
    architecture = object()
    datums = object()
    provenance = _provenance()
    monkeypatch.setattr(v11, "_require_promoted_build_result", lambda a, d: (a, d))
    monkeypatch.setattr(
        v10,
        "manifest_v10",
        lambda a, d: {
            "schema": v10.SCHEMA_V10,
            **provenance,
            "fusion_handoff": dict(provenance),
            "nested_engineering_evidence": hostile,
        },
    )
    return v11.manifest_v11(architecture, datums)


@pytest.mark.parametrize(
    "hostile",
    [
        {1: "integer-key"},
        {(1, 2): "tuple-key"},
        ("tuple", "silently-json-list-before-this-gate"),
        bytearray(b"mutable-binary"),
    ],
)
def test_v11_rejects_evidence_that_json_would_coerce_or_cannot_represent(monkeypatch, hostile):
    with pytest.raises(v11.TreatmentMountedFourZoneV11Error, match="string JSON object keys|non-JSON-native"):
        _materialize(monkeypatch, hostile)


def test_v11_accepts_nested_native_json_evidence(monkeypatch):
    promoted = _materialize(
        monkeypatch,
        {"samples": [1, 2.5, True, False, None, "qualified-digital-evidence"]},
    )

    v11.verify_promoted_evidence_v11(promoted)
