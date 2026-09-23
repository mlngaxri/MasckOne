import math

import pytest

from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode, InputEvent


def _stale_fault() -> tuple[DebouncedInput, float, InputEvent]:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    runtime.arm(now_s=1.0)
    runtime.sample(pressed=False, now_s=1.01)
    fault_at = 1.01 + runtime.stale_after_s + 0.001
    fault = runtime.watchdog(now_s=fault_at)
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE
    return runtime, fault_at, fault


@pytest.mark.parametrize("service", ["arm", "sample", "watchdog"])
def test_faulted_service_calls_preserve_chronological_first_fault(service: str) -> None:
    runtime, fault_at, original = _stale_fault()

    call_at = fault_at + 0.10
    if service == "sample":
        observed = runtime.sample(pressed="malformed", now_s=call_at)  # type: ignore[arg-type]
    elif service == "arm":
        observed = runtime.arm(now_s=call_at)
    else:
        observed = runtime.watchdog(now_s=call_at)

    assert observed == original
    assert observed.fault_code is FaultCode.INPUT_STREAM_STALE
    assert observed == InputEvent(False, Edge.NONE, True, original.fault, original.fault_code)

    # A later valid service observation advances the shared clock floor while faulted.
    # Resetting behind that observation must not silently recover the input.
    reset = runtime.reset(now_s=call_at - 0.001)
    assert reset == original
    assert runtime.faulted


def test_faulted_reset_with_valid_forward_time_is_the_only_recovery_path() -> None:
    runtime, fault_at, original = _stale_fault()

    # Invalid reset observations cannot clear or replace the first fault.
    for invalid in (math.nan, math.inf, -math.inf, True):
        assert runtime.reset(now_s=invalid) == original
        assert runtime.faulted

    reset_at = fault_at + 0.10
    assert runtime.reset(now_s=reset_at) == InputEvent(False, Edge.NONE)
    assert not runtime.faulted

    # Recovery is not an implicit input edge. A real debounced release remains
    # mandatory before a fresh press can become actionable.
    held_at = reset_at + 0.01
    assert runtime.sample(pressed=True, now_s=held_at) == InputEvent(False, Edge.NONE)
    release_at = held_at + 0.01
    assert runtime.sample(pressed=False, now_s=release_at) == InputEvent(False, Edge.NONE)
    assert runtime.sample(pressed=False, now_s=release_at + runtime.debounce_s) == InputEvent(False, Edge.NONE)

    press_at = release_at + runtime.debounce_s + 0.01
    assert runtime.sample(pressed=True, now_s=press_at) == InputEvent(False, Edge.NONE)
    assert runtime.sample(pressed=True, now_s=press_at + runtime.debounce_s) == InputEvent(True, Edge.PRESSED)


def test_faulted_calls_with_invalid_times_do_not_poison_future_valid_recovery() -> None:
    runtime, fault_at, original = _stale_fault()

    assert runtime.arm(now_s=math.nan) == original
    assert runtime.watchdog(now_s=math.inf) == original
    assert runtime.sample(pressed=False, now_s=-math.inf) == original

    # Invalid observations are ignored for clock-floor advancement while preserving
    # the latched cause, so a subsequent valid forward reset remains possible.
    assert runtime.reset(now_s=fault_at + 0.01) == InputEvent(False, Edge.NONE)
    assert not runtime.faulted
