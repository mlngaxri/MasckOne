from __future__ import annotations

import itertools

import pytest

from masck_one.hmi_runtime import DebouncedInput, Edge


@pytest.mark.parametrize("initial_pressed,target_pressed", itertools.product((False, True), repeat=2))
def test_debounce_boundary_requires_continuous_candidate_dwell(
    initial_pressed: bool,
    target_pressed: bool,
) -> None:
    """A candidate changes state only after one uninterrupted debounce interval."""
    runtime = DebouncedInput(debounce_s=0.030, stale_after_s=0.250)

    runtime.sample(pressed=initial_pressed, now_s=0.000)
    settled = runtime.sample(pressed=initial_pressed, now_s=0.030)
    if initial_pressed:
        assert settled.edge is Edge.PRESSED
        assert settled.stable_pressed is True
    else:
        assert settled.edge is Edge.NONE
        assert settled.stable_pressed is False

    first = runtime.sample(pressed=target_pressed, now_s=0.040)
    assert first.edge is Edge.NONE
    assert first.stable_pressed is initial_pressed

    before = runtime.sample(pressed=target_pressed, now_s=0.069999)
    assert before.edge is Edge.NONE
    assert before.stable_pressed is initial_pressed

    boundary = runtime.sample(pressed=target_pressed, now_s=0.070)
    if target_pressed == initial_pressed:
        assert boundary.edge is Edge.NONE
        assert boundary.stable_pressed is initial_pressed
    else:
        assert boundary.edge is (Edge.PRESSED if target_pressed else Edge.RELEASED)
        assert boundary.stable_pressed is target_pressed


def test_bounce_back_to_stable_cancels_candidate_dwell() -> None:
    runtime = DebouncedInput(debounce_s=0.030, stale_after_s=0.250)

    runtime.sample(pressed=False, now_s=0.000)
    runtime.sample(pressed=True, now_s=0.010)
    runtime.sample(pressed=True, now_s=0.029)

    cancelled = runtime.sample(pressed=False, now_s=0.030)
    assert cancelled.edge is Edge.NONE
    assert cancelled.stable_pressed is False

    restarted = runtime.sample(pressed=True, now_s=0.031)
    assert restarted.edge is Edge.NONE
    assert restarted.stable_pressed is False

    still_waiting = runtime.sample(pressed=True, now_s=0.060999)
    assert still_waiting.edge is Edge.NONE
    assert still_waiting.stable_pressed is False

    accepted = runtime.sample(pressed=True, now_s=0.061)
    assert accepted.edge is Edge.PRESSED
    assert accepted.stable_pressed is True


def test_post_fault_release_dwell_cannot_emit_release_or_press_edge() -> None:
    debounce_s = 0.030
    runtime = DebouncedInput(debounce_s=debounce_s, stale_after_s=0.250)
    runtime.sample(pressed=True, now_s=0.000)
    runtime.sample(pressed=True, now_s=0.030)
    assert runtime.watchdog(now_s=0.281).faulted

    reset = runtime.reset(now_s=0.282)
    assert not reset.faulted
    assert reset.edge is Edge.NONE
    assert reset.stable_pressed is False

    held = runtime.sample(pressed=True, now_s=0.283)
    assert held.edge is Edge.NONE
    assert held.stable_pressed is False

    release_started_at_s = 0.284
    release_start = runtime.sample(pressed=False, now_s=release_started_at_s)
    assert release_start.edge is Edge.NONE
    assert release_start.stable_pressed is False

    release_deadline_s = release_started_at_s + debounce_s
    release_boundary = runtime.sample(pressed=False, now_s=release_deadline_s)
    assert release_boundary.edge is Edge.NONE
    assert release_boundary.stable_pressed is False

    press_started_at_s = release_deadline_s + 0.001
    press_start = runtime.sample(pressed=True, now_s=press_started_at_s)
    assert press_start.edge is Edge.NONE
    assert press_start.stable_pressed is False

    press_deadline_s = press_started_at_s + debounce_s
    press_boundary = runtime.sample(pressed=True, now_s=press_deadline_s)
    assert press_boundary.edge is Edge.PRESSED
    assert press_boundary.stable_pressed is True
