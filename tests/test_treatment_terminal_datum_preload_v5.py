from __future__ import annotations

from masck_one import treatment_collision_kernel_v2 as collision_v2
from masck_one import treatment_terminal_datum_preload_v4 as v4
from masck_one.treatment_terminal_datum_preload_v5 import (
    COLLISION_KERNEL,
    SCHEMA,
    build_terminal_datum_preload_v5_architecture,
    manifest_v5,
)


def test_v5_builds_v4_geometry_under_collision_kernel_v2(monkeypatch):
    original = v4.intersection_volume_mm3
    calls = 0
    exact = collision_v2.intersection_volume_mm3

    def observed(left, right):
        nonlocal calls
        calls += 1
        return exact(left, right)

    monkeypatch.setattr(collision_v2, "intersection_volume_mm3", observed)
    architecture = build_terminal_datum_preload_v5_architecture()

    assert calls > 0
    assert v4.intersection_volume_mm3 is original
    payload = manifest_v5(architecture)
    assert payload["schema"] == SCHEMA
    assert payload["supersedes"] == v4.SCHEMA
    assert payload["collision_kernel"] == COLLISION_KERNEL
    assert payload["physical_geometry_changed_from_v4"] is False
    assert payload["collision_threshold_weakened"] is False
    assert payload["physical_validation_eligible"] is False


def test_v5_restores_v4_collision_hook_when_build_fails(monkeypatch):
    original = v4.intersection_volume_mm3

    def forced_failure(_left, _right):
        raise RuntimeError("forced collision-kernel failure")

    monkeypatch.setattr(collision_v2, "intersection_volume_mm3", forced_failure)
    try:
        build_terminal_datum_preload_v5_architecture()
    except RuntimeError as exc:
        assert str(exc) == "forced collision-kernel failure"
    else:
        raise AssertionError("hostile collision-kernel failure must propagate")

    assert v4.intersection_volume_mm3 is original
