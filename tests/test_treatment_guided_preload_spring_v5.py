from __future__ import annotations

from types import SimpleNamespace

from masck_one import treatment_collision_kernel_v2 as collision_v2
from masck_one import treatment_guided_preload_spring_v5 as guided_v5
from masck_one import treatment_terminal_datum_preload_v4 as terminal_v4
from masck_one.structural_frame_actuator_reactions import REACTION_IDS
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
    assert tuple(station.reaction_id for station in architecture.stations) == tuple(REACTION_IDS)
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


def test_guided_v5_rejects_duplicate_terminal_identity_before_generating_springs(monkeypatch):
    duplicate_id = REACTION_IDS[0]
    fake_station = SimpleNamespace(reaction_id=duplicate_id)
    terminal = SimpleNamespace(
        source_cell6_head_sha=guided_v5.SOURCE_CELL6_HEAD_SHA,
        stations=tuple(fake_station for _ in REACTION_IDS),
    )
    generated = 0

    def should_not_generate(_station):
        nonlocal generated
        generated += 1
        raise AssertionError("spring generation must not begin for an invalid station set")

    monkeypatch.setattr(guided_v5, "build_terminal_datum_preload_v5_architecture", lambda **_kwargs: terminal)
    monkeypatch.setattr(guided_v5, "build_guided_preload_spring_station", should_not_generate)

    try:
        build_guided_preload_spring_v5_architecture()
    except ValueError as exc:
        assert "terminal input station identity drifted" in str(exc)
    else:
        raise AssertionError("duplicate terminal identity must fail closed")

    assert generated == 0


def test_guided_v5_rejects_reordered_terminal_identity_before_generating_springs(monkeypatch):
    terminal = SimpleNamespace(
        source_cell6_head_sha=guided_v5.SOURCE_CELL6_HEAD_SHA,
        stations=tuple(SimpleNamespace(reaction_id=value) for value in reversed(REACTION_IDS)),
    )
    generated = 0

    def should_not_generate(_station):
        nonlocal generated
        generated += 1
        raise AssertionError("spring generation must not begin for a reordered station set")

    monkeypatch.setattr(guided_v5, "build_terminal_datum_preload_v5_architecture", lambda **_kwargs: terminal)
    monkeypatch.setattr(guided_v5, "build_guided_preload_spring_station", should_not_generate)

    try:
        build_guided_preload_spring_v5_architecture()
    except ValueError as exc:
        assert "terminal input station identity drifted" in str(exc)
    else:
        raise AssertionError("reordered terminal identity must fail closed")

    assert generated == 0


def _valid_capture_screen():
    return {"X_root": 0.01, "Z_root": 0.01, "X_tip": 0.01, "Z_tip": 0.01}


def test_guided_v5_rejects_nonfinite_capture_evidence_immediately(monkeypatch):
    terminal_stations = tuple(SimpleNamespace(reaction_id=value) for value in REACTION_IDS)
    terminal = SimpleNamespace(
        source_cell6_head_sha=guided_v5.SOURCE_CELL6_HEAD_SHA,
        stations=terminal_stations,
    )
    generated = 0

    def invalid_capture(station):
        nonlocal generated
        generated += 1
        capture = _valid_capture_screen()
        capture["X_root"] = float("nan")
        return SimpleNamespace(reaction_id=station.reaction_id, capture_screen=capture)

    monkeypatch.setattr(guided_v5, "build_terminal_datum_preload_v5_architecture", lambda **_kwargs: terminal)
    monkeypatch.setattr(guided_v5, "build_guided_preload_spring_station", invalid_capture)

    try:
        build_guided_preload_spring_v5_architecture()
    except ValueError as exc:
        assert "capture evidence must be finite" in str(exc)
    else:
        raise AssertionError("non-finite capture evidence must fail closed")

    assert generated == 1


def test_guided_v5_rejects_missing_capture_probe(monkeypatch):
    terminal_stations = tuple(SimpleNamespace(reaction_id=value) for value in REACTION_IDS)
    terminal = SimpleNamespace(
        source_cell6_head_sha=guided_v5.SOURCE_CELL6_HEAD_SHA,
        stations=terminal_stations,
    )

    def incomplete_capture(station):
        capture = _valid_capture_screen()
        del capture["Z_tip"]
        return SimpleNamespace(reaction_id=station.reaction_id, capture_screen=capture)

    monkeypatch.setattr(guided_v5, "build_terminal_datum_preload_v5_architecture", lambda **_kwargs: terminal)
    monkeypatch.setattr(guided_v5, "build_guided_preload_spring_station", incomplete_capture)

    try:
        build_guided_preload_spring_v5_architecture()
    except ValueError as exc:
        assert "capture screen keys drifted" in str(exc)
    else:
        raise AssertionError("missing capture probe must fail closed")
