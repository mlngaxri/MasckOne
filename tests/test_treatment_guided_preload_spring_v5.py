from __future__ import annotations

from masck_one import treatment_collision_kernel_v2 as collision_v2
from masck_one import treatment_terminal_datum_preload_v4 as terminal_v4
from masck_one.treatment_guided_preload_spring_v5 import (
    COLLISION_KERNEL,
    SCHEMA,
    build_guided_preload_spring_v5_architecture,
)


def test_guided_v5_builds_four_captive_stations_through_collision_v2(monkeypatch):
    calls = 0
    exact = collision_v2.intersection_volume_mm3

    def observed(left, right):
        nonlocal calls
        calls += 1
        return exact(left, right)

    original = terminal_v4.intersection_volume_mm3
    monkeypatch.setattr(collision_v2, "intersection_volume_mm3", observed)
    architecture = build_guided_preload_spring_v5_architecture()

    assert calls > 0
    assert terminal_v4.intersection_volume_mm3 is original
    assert len(architecture.stations) == 4
    assert len({station.reaction_id for station in architecture.stations}) == 4
    for station in architecture.stations:
        assert min(station.capture_screen.values()) > 0.0

    manifest = architecture.manifest()
    assert manifest["schema"] == SCHEMA
    assert manifest["collision_kernel"] == COLLISION_KERNEL
    assert manifest["physical_geometry_changed_from_guided_v4"] is False
    assert manifest["collision_threshold_weakened"] is False
    assert manifest["physical_validation_eligible"] is False


def test_guided_v5_does_not_generate_springs_if_terminal_v2_verification_fails(monkeypatch):
    original = terminal_v4.intersection_volume_mm3

    def forced_failure(_left, _right):
        raise RuntimeError("forced terminal collision failure")

    monkeypatch.setattr(collision_v2, "intersection_volume_mm3", forced_failure)
    try:
        build_guided_preload_spring_v5_architecture()
    except RuntimeError as exc:
        assert str(exc) == "forced terminal collision failure"
    else:
        raise AssertionError("terminal verification failure must block guided spring generation")

    assert terminal_v4.intersection_volume_mm3 is original
