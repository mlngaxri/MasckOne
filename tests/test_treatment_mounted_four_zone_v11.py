from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock

import pytest

from masck_one import treatment_mounted_four_zone_v9 as v9
from masck_one import treatment_mounted_four_zone_v10 as v10
from masck_one import treatment_mounted_four_zone_v11 as v11
from masck_one.treatment_terminal_datum_preload_v5 import COLLISION_KERNEL, SOURCE_CELL6_HEAD_SHA


def _valid_v10_payload() -> dict[str, object]:
    provenance = {
        "source_cell6_head_sha": SOURCE_CELL6_HEAD_SHA,
        "source_cell6_geometry_head_sha": SOURCE_CELL6_HEAD_SHA,
        "source_cell6_head_semantics": v10.SOURCE_CELL6_HEAD_SEMANTICS,
        "active_cell6_owner_head_claimed": False,
        "live_cell6_owner_recheck_required_before_promotion": True,
    }
    return {
        "schema": v10.SCHEMA_V10,
        **provenance,
        "fusion_handoff": dict(provenance),
        "upstream_marker": "v10-owned",
    }


def _patch_manifest_boundary(monkeypatch, payload: dict[str, object]):
    architecture = object()
    datums = object()
    monkeypatch.setattr(v11, "_require_promoted_build_result", lambda a, d: (a, d))
    monkeypatch.setattr(v10, "manifest_v10", lambda a, d: payload)
    return architecture, datums


def test_v11_manifest_records_kernel_promotion_without_geometry_claim_change(monkeypatch):
    architecture, datums = _patch_manifest_boundary(monkeypatch, _valid_v10_payload())
    payload = v11.manifest_v11(architecture, datums)
    assert payload["schema"] == v11.SCHEMA
    assert payload["supersedes"] == v10.SCHEMA_V10
    assert payload["collision_kernel"] == COLLISION_KERNEL
    assert payload["terminal_datum_verification"] == "TERMINAL_DATUM_PRELOAD_V5"
    assert payload["physical_architecture_changed_from_v10"] is False
    assert payload["collision_threshold_weakened"] is False
    assert payload["physical_validation_eligible"] is False
    v11.verify_promoted_evidence_v11(payload)


def test_v11_manifest_promotion_does_not_mutate_upstream_v10_evidence(monkeypatch):
    upstream = _valid_v10_payload()
    original = {**upstream, "fusion_handoff": dict(upstream["fusion_handoff"])}
    architecture, datums = _patch_manifest_boundary(monkeypatch, upstream)
    promoted = v11.manifest_v11(architecture, datums)
    assert promoted is not upstream
    assert upstream == original
    assert promoted["fusion_handoff"] is not upstream["fusion_handoff"]
    assert upstream["schema"] == v10.SCHEMA_V10
    assert "collision_kernel" not in upstream
    assert "promoted_evidence_sha256" not in upstream
    assert promoted["schema"] == v11.SCHEMA
    assert promoted["upstream_marker"] == "v10-owned"


def test_v11_manifest_rejects_non_dict_materialization(monkeypatch):
    architecture = object()
    datums = object()
    monkeypatch.setattr(v11, "_require_promoted_build_result", lambda a, d: (a, d))
    monkeypatch.setattr(v10, "manifest_v10", lambda a, d: [("schema", v10.SCHEMA_V10)])
    with pytest.raises(v11.TreatmentMountedFourZoneV11Error, match="exact dict manifest"):
        v11.manifest_v11(architecture, datums)


def test_v11_manifest_rejects_payload_lineage_mismatch(monkeypatch):
    hostile = _valid_v10_payload()
    hostile["source_cell6_head_sha"] = "hostile-lineage"
    architecture, datums = _patch_manifest_boundary(monkeypatch, hostile)
    with pytest.raises(v11.TreatmentMountedFourZoneV11Error, match="Cell 6 provenance field"):
        v11.manifest_v11(architecture, datums)


def test_v11_manifest_rejects_nested_payload_lineage_mismatch(monkeypatch):
    hostile = _valid_v10_payload()
    hostile["fusion_handoff"]["source_cell6_geometry_head_sha"] = "hostile-lineage"
    architecture, datums = _patch_manifest_boundary(monkeypatch, hostile)
    with pytest.raises(v11.TreatmentMountedFourZoneV11Error, match="fusion Cell 6 provenance field"):
        v11.manifest_v11(architecture, datums)


def test_v11_rejects_unqualified_builder_output_and_restores_hooks(monkeypatch):
    original_intersection = v9.intersection_volume_mm3
    original_terminal_builder = v9.build_terminal_datum_preload_v4_architecture
    monkeypatch.setattr(v10, "build_mounted_four_zone_architecture_v10", lambda **kwargs: (object(), object()))
    with pytest.raises(v11.TreatmentMountedFourZoneV11Error, match="exact MountedFourZoneArchitecture"):
        v11.build_mounted_four_zone_architecture_v11()
    assert v9.intersection_volume_mm3 is original_intersection
    assert v9.build_terminal_datum_preload_v4_architecture is original_terminal_builder


def test_v11_manifest_rejects_unqualified_objects():
    with pytest.raises(v11.TreatmentMountedFourZoneV11Error, match="exact MountedFourZoneArchitecture"):
        v11.manifest_v11(object(), object())


def test_v11_routes_mounted_and_terminal_checks_through_v2_and_restores_hooks(monkeypatch):
    original_intersection = v9.intersection_volume_mm3
    original_terminal_builder = v9.build_terminal_datum_preload_v4_architecture
    observed = {}
    def fake_build(**kwargs):
        observed["intersection"] = v9.intersection_volume_mm3
        observed["terminal_builder"] = v9.build_terminal_datum_preload_v4_architecture
        return "architecture", "datums"
    monkeypatch.setattr(v10, "build_mounted_four_zone_architecture_v10", fake_build)
    monkeypatch.setattr(v11, "_require_promoted_build_result", lambda a, d: (a, d))
    assert v11.build_mounted_four_zone_architecture_v11() == ("architecture", "datums")
    assert observed["intersection"] is v11.collision_v2.intersection_volume_mm3
    assert observed["terminal_builder"] is v11.build_terminal_datum_preload_v5_architecture
    assert v9.intersection_volume_mm3 is original_intersection
    assert v9.build_terminal_datum_preload_v4_architecture is original_terminal_builder


def test_v11_restores_legacy_hooks_when_build_fails(monkeypatch):
    original_intersection = v9.intersection_volume_mm3
    original_terminal_builder = v9.build_terminal_datum_preload_v4_architecture
    def fail_build(**kwargs):
        assert v9.intersection_volume_mm3 is v11.collision_v2.intersection_volume_mm3
        assert v9.build_terminal_datum_preload_v4_architecture is v11.build_terminal_datum_preload_v5_architecture
        raise RuntimeError("hostile mounted verification failure")
    monkeypatch.setattr(v10, "build_mounted_four_zone_architecture_v10", fail_build)
    with pytest.raises(RuntimeError, match="hostile mounted verification failure"):
        v11.build_mounted_four_zone_architecture_v11()
    assert v9.intersection_volume_mm3 is original_intersection
    assert v9.build_terminal_datum_preload_v4_architecture is original_terminal_builder


def test_v11_serializes_process_global_verification_hooks_for_concurrent_builds(monkeypatch):
    original_intersection = v9.intersection_volume_mm3
    original_terminal_builder = v9.build_terminal_datum_preload_v4_architecture
    first_entered = Event()
    release_first = Event()
    calls_lock = Lock()
    call_count = 0
    def blocking_build(**kwargs):
        nonlocal call_count
        with calls_lock:
            call_count += 1
            ordinal = call_count
        assert v9.intersection_volume_mm3 is v11.collision_v2.intersection_volume_mm3
        assert v9.build_terminal_datum_preload_v4_architecture is v11.build_terminal_datum_preload_v5_architecture
        if ordinal == 1:
            first_entered.set()
            assert release_first.wait(timeout=2.0)
        return ordinal, "datums"
    monkeypatch.setattr(v10, "build_mounted_four_zone_architecture_v10", blocking_build)
    monkeypatch.setattr(v11, "_require_promoted_build_result", lambda a, d: (a, d))
    start = Barrier(3)
    def invoke():
        start.wait(timeout=2.0)
        return v11.build_mounted_four_zone_architecture_v11()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(invoke) for _ in range(2)]
        start.wait(timeout=2.0)
        assert first_entered.wait(timeout=2.0)
        with calls_lock:
            assert call_count == 1
        release_first.set()
        results = [future.result(timeout=2.0) for future in futures]
    assert sorted(result[0] for result in results) == [1, 2]
    assert v9.intersection_volume_mm3 is original_intersection
    assert v9.build_terminal_datum_preload_v4_architecture is original_terminal_builder
