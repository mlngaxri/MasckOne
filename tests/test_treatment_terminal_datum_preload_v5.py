from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock
from types import SimpleNamespace

from masck_one import treatment_collision_kernel_v2 as collision_v2
from masck_one import treatment_terminal_datum_preload_v4 as v4
from masck_one.treatment_terminal_datum_preload_v5 import (
    COLLISION_KERNEL,
    SCHEMA,
    TreatmentTerminalDatumPreloadV5Error,
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


def test_v5_rejects_duck_typed_builder_result(monkeypatch):
    original_hook = v4.intersection_volume_mm3
    fake = SimpleNamespace(source_cell6_head_sha=v4.SOURCE_CELL6_HEAD_SHA)
    monkeypatch.setattr(v4, "build_terminal_datum_preload_v4_architecture", lambda **_kwargs: fake)

    try:
        build_terminal_datum_preload_v5_architecture()
    except TreatmentTerminalDatumPreloadV5Error as exc:
        assert "invalid architecture type" in str(exc)
    else:
        raise AssertionError("duck-typed terminal architecture must fail closed")

    assert v4.intersection_volume_mm3 is original_hook


def test_v5_manifest_rejects_unverified_duck_typed_architecture():
    fake = SimpleNamespace(manifest=lambda: {"schema": "hostile"})
    try:
        manifest_v5(fake)
    except TreatmentTerminalDatumPreloadV5Error as exc:
        assert "requires a verified architecture" in str(exc)
    else:
        raise AssertionError("manifest must not certify an unverified architecture")


def test_v5_serializes_process_global_v4_collision_hook(monkeypatch):
    original_hook = v4.intersection_volume_mm3
    original_builder = v4.build_terminal_datum_preload_v4_architecture
    first_entered = Event()
    release_first = Event()
    calls_lock = Lock()
    call_count = 0

    def blocking_build(**kwargs):
        nonlocal call_count
        with calls_lock:
            call_count += 1
            ordinal = call_count
        assert v4.intersection_volume_mm3 is collision_v2.intersection_volume_mm3
        if ordinal == 1:
            first_entered.set()
            assert release_first.wait(timeout=2.0)
        return original_builder(**kwargs)

    monkeypatch.setattr(v4, "build_terminal_datum_preload_v4_architecture", blocking_build)
    start = Barrier(3)

    def invoke():
        start.wait(timeout=2.0)
        return build_terminal_datum_preload_v5_architecture()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(invoke) for _ in range(2)]
        start.wait(timeout=2.0)
        assert first_entered.wait(timeout=2.0)
        with calls_lock:
            assert call_count == 1
        release_first.set()
        results = [future.result(timeout=4.0) for future in futures]

    assert len(results) == 2
    assert call_count == 2
    assert all(isinstance(result, v4.TerminalDatumPreloadV4Architecture) for result in results)
    assert v4.intersection_volume_mm3 is original_hook
