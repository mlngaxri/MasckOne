from __future__ import annotations

import math

import pytest

from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode


DEBOUNCE_S = 0.030
STALE_AFTER_S = 0.250


def _faulted_pressed_input() -> DebouncedInput:
    runtime = DebouncedInput(debounce_s=DEBOUNCE_S, stale_after_s=STALE_AFTER_S)
    runtime.sample(pressed=True, now_s=0.000)
    runtime.sample(pressed=True, now_s=DEBOUNCE_S)
    fault = runtime.watchdog(now_s=DEBOUNCE_S + STALE_AFTER_S + 0.001)
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE
    return runtime


def test_timed_reset_supervises_recovery_stream_at_exact_deadline() -> None:
    runtime = _faulted_pressed_input()
    reset_at_s = 1.000
    reset = runtime.reset(now_s=reset_at_s)
    assert not reset.faulted

    deadline_s = reset_at_s + STALE_AFTER_S
    boundary = runtime.watchdog(now_s=deadline_s)
    assert not boundary.faulted
    assert boundary.edge is Edge.NONE
    assert boundary.stable_pressed is False

    expired = runtime.watchdog(now_s=math.nextafter(deadline_s, math.inf))
    assert expired.faulted
    assert expired.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED
    assert expired.edge is Edge.NONE
    assert expired.stable_pressed is False


def test_held_input_refreshes_recovery_supervision_without_synthesising_press() -> None:
    runtime = _faulted_pressed_input()
    reset_at_s = 1.000
    runtime.reset(now_s=reset_at_s)

    first = runtime.sample(pressed=True, now_s=reset_at_s + 0.001)
    assert not first.faulted
    assert first.edge is Edge.NONE
    assert first.stable_pressed is False

    last_held_at_s = reset_at_s + STALE_AFTER_S
    held = runtime.sample(pressed=True, now_s=last_held_at_s)
    assert not held.faulted
    assert held.edge is Edge.NONE
    assert held.stable_pressed is False

    watchdog_deadline_s = last_held_at_s + STALE_AFTER_S
    boundary = runtime.watchdog(now_s=watchdog_deadline_s)
    assert not boundary.faulted
    assert boundary.edge is Edge.NONE
    assert boundary.stable_pressed is False

    stale = runtime.watchdog(now_s=math.nextafter(watchdog_deadline_s, math.inf))
    assert stale.faulted
    assert stale.fault_code is FaultCode.INPUT_STREAM_STALE


def test_recovery_release_then_fresh_press_is_only_path_to_pressed_edge() -> None:
    runtime = _faulted_pressed_input()
    reset_at_s = 1.000
    runtime.reset(now_s=reset_at_s)

    runtime.sample(pressed=True, now_s=1.001)
    release_started_at_s = 1.010
    runtime.sample(pressed=False, now_s=release_started_at_s)
    released = runtime.sample(pressed=False, now_s=release_started_at_s + DEBOUNCE_S)
    assert released.edge is Edge.NONE
    assert released.stable_pressed is False

    press_started_at_s = release_started_at_s + DEBOUNCE_S + 0.001
    runtime.sample(pressed=True, now_s=press_started_at_s)
    pressed = runtime.sample(pressed=True, now_s=press_started_at_s + DEBOUNCE_S)
    assert pressed.edge is Edge.PRESSED
    assert pressed.stable_pressed is True


@pytest.mark.parametrize("malformed_pressed", [None, 0, 1, "pressed", object()])
def test_expired_recovery_stream_keeps_chronological_supervision_fault_priority(
    malformed_pressed: object,
) -> None:
    runtime = _faulted_pressed_input()
    reset_at_s = 1.000
    runtime.reset(now_s=reset_at_s)

    event = runtime.sample(
        pressed=malformed_pressed,  # type: ignore[arg-type]
        now_s=math.nextafter(reset_at_s + STALE_AFTER_S, math.inf),
    )
    assert event.faulted
    assert event.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED
    assert event.edge is Edge.NONE
    assert event.stable_pressed is False
