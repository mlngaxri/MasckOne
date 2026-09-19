from __future__ import annotations

import pytest

from masck_one import treatment_mounted_four_zone_v9 as v9
from masck_one import treatment_mounted_four_zone_v10 as v10
from masck_one import treatment_mounted_four_zone_v11 as v11
from masck_one.treatment_terminal_datum_preload_v5 import COLLISION_KERNEL


def test_v11_manifest_records_kernel_promotion_without_geometry_claim_change(monkeypatch):
    architecture = object()
    datums = object()
    monkeypatch.setattr(v10, "manifest_v10", lambda a, d: {"schema": v10.SCHEMA_V10})

    payload = v11.manifest_v11(architecture, datums)

    assert payload["schema"] == v11.SCHEMA
    assert payload["supersedes"] == v10.SCHEMA_V10
    assert payload["collision_kernel"] == COLLISION_KERNEL
    assert payload["terminal_datum_verification"] == "TERMINAL_DATUM_PRELOAD_V5"
    assert payload["physical_architecture_changed_from_v10"] is False
    assert payload["collision_threshold_weakened"] is False
    assert payload["physical_validation_eligible"] is False


def test_v11_routes_mounted_and_terminal_checks_through_v2_and_restores_hooks(monkeypatch):
    original_intersection = v9.intersection_volume_mm3
    original_terminal_builder = v9.build_terminal_datum_preload_v4_architecture
    observed = {}

    def fake_build(**kwargs):
        observed["intersection"] = v9.intersection_volume_mm3
        observed["terminal_builder"] = v9.build_terminal_datum_preload_v4_architecture
        return "architecture", "datums"

    monkeypatch.setattr(v10, "build_mounted_four_zone_architecture_v10", fake_build)
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
