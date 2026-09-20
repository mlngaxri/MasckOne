from __future__ import annotations

from copy import deepcopy

from masck_one import treatment_mounted_four_zone_v10 as v10
from masck_one import treatment_mounted_four_zone_v11 as v11
from masck_one.treatment_terminal_datum_preload_v5 import SOURCE_CELL6_HEAD_SHA


def _accepted_provenance() -> dict[str, object]:
    return {
        "source_cell6_head_sha": SOURCE_CELL6_HEAD_SHA,
        "source_cell6_geometry_head_sha": SOURCE_CELL6_HEAD_SHA,
        "source_cell6_head_semantics": v10.SOURCE_CELL6_HEAD_SEMANTICS,
        "active_cell6_owner_head_claimed": False,
        "live_cell6_owner_recheck_required_before_promotion": True,
    }


def test_v11_promotion_deeply_isolates_nested_v10_evidence(monkeypatch):
    architecture = object()
    datums = object()
    provenance = _accepted_provenance()
    upstream = {
        "schema": v10.SCHEMA_V10,
        **provenance,
        "fusion_handoff": dict(provenance),
        "nested_engineering_evidence": {
            "zones": [
                {"zone_id": "UL", "checks": ["collision", "datum"]},
                {"zone_id": "UR", "checks": ["collision", "datum"]},
            ]
        },
    }
    original = deepcopy(upstream)

    monkeypatch.setattr(v11, "_require_promoted_build_result", lambda a, d: (a, d))
    monkeypatch.setattr(v10, "manifest_v10", lambda a, d: upstream)

    promoted = v11.manifest_v11(architecture, datums)

    assert promoted is not upstream
    assert promoted["fusion_handoff"] is not upstream["fusion_handoff"]
    assert promoted["nested_engineering_evidence"] is not upstream["nested_engineering_evidence"]
    assert promoted["nested_engineering_evidence"]["zones"] is not upstream["nested_engineering_evidence"]["zones"]

    promoted["fusion_handoff"]["source_cell6_head_sha"] = "post-promotion-tamper"
    promoted["nested_engineering_evidence"]["zones"][0]["checks"].append("hostile")

    assert upstream == original


def test_v11_promotion_fails_closed_when_predecessor_cannot_be_deep_copied(monkeypatch):
    architecture = object()
    datums = object()
    provenance = _accepted_provenance()
    upstream = {
        "schema": v10.SCHEMA_V10,
        **provenance,
        "fusion_handoff": dict(provenance),
    }

    monkeypatch.setattr(v11, "_require_promoted_build_result", lambda a, d: (a, d))
    monkeypatch.setattr(v10, "manifest_v10", lambda a, d: upstream)

    def hostile_deepcopy(payload):
        raise RuntimeError("copy refused")

    monkeypatch.setattr(v11.copy, "deepcopy", hostile_deepcopy)

    try:
        v11.manifest_v11(architecture, datums)
    except v11.TreatmentMountedFourZoneV11Error as exc:
        assert "cannot be isolated for promotion" in str(exc)
    else:
        raise AssertionError("V11 accepted predecessor evidence that could not be isolated")
