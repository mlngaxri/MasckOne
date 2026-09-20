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


def _install_upstream(monkeypatch, upstream: dict[str, object]):
    architecture = object()
    datums = object()
    monkeypatch.setattr(v11, "_require_promoted_build_result", lambda a, d: (a, d))
    monkeypatch.setattr(v10, "manifest_v10", lambda a, d: upstream)
    return architecture, datums


@pytest.mark.parametrize("schema", [None, "", v11.SCHEMA, "HOSTILE_PREDECESSOR", 0])
def test_v11_rejects_non_v10_predecessor_before_promotion(monkeypatch, schema):
    provenance = _provenance()
    upstream = {
        "schema": schema,
        **provenance,
        "fusion_handoff": dict(provenance),
    }
    architecture, datums = _install_upstream(monkeypatch, upstream)

    with pytest.raises(v11.TreatmentMountedFourZoneV11Error, match="authentic V10 predecessor schema"):
        v11.manifest_v11(architecture, datums)


def test_v11_rejects_predecessor_carrying_promoted_digest(monkeypatch):
    provenance = _provenance()
    upstream = {
        "schema": v10.SCHEMA_V10,
        **provenance,
        "fusion_handoff": dict(provenance),
        "promoted_evidence_sha256": "0" * 64,
    }
    architecture, datums = _install_upstream(monkeypatch, upstream)

    with pytest.raises(v11.TreatmentMountedFourZoneV11Error, match="must not contain a V11 promotion digest"):
        v11.manifest_v11(architecture, datums)


def test_v11_accepts_exact_v10_predecessor_without_mutating_it(monkeypatch):
    provenance = _provenance()
    upstream = {
        "schema": v10.SCHEMA_V10,
        **provenance,
        "fusion_handoff": dict(provenance),
        "predecessor_marker": "v10-owned",
    }
    snapshot = {**upstream, "fusion_handoff": dict(upstream["fusion_handoff"])}
    architecture, datums = _install_upstream(monkeypatch, upstream)

    promoted = v11.manifest_v11(architecture, datums)

    assert upstream == snapshot
    assert promoted["schema"] == v11.SCHEMA
    assert promoted["supersedes"] == v10.SCHEMA_V10
    assert promoted["predecessor_marker"] == "v10-owned"
    v11.verify_promoted_evidence_v11(promoted)
