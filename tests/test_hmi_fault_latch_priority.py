import pytest

from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode, InputEvent


def _stale_fault(runtime: DebouncedInput) -> InputEvent:
    runtime.arm(now_s=1.0)
    event = runtime.watchdog(now_s=1.0 + runtime.stale_after_s + 0.001)
    assert event.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED
    return event


@pytest.mark.parametrize("operation", ["sample", "arm", "watchdog", "reset"])
def test_latched_first_fault_survives_malformed_service_calls(operation: str) -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    first = _stale_fault(runtime)

    if operation == "sample":
        observed = runtime.sample(pressed="invalid", now_s=float("nan"))  # type: ignore[arg-type]
    elif operation == "arm":
        observed = runtime.arm(now_s=float("nan"))
    elif operation == "watchdog":
        observed = runtime.watchdog(now_s=float("nan"))
    else:
        observed = runtime.reset(now_s=float("nan"))

    assert observed == first
    assert observed.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED


@pytest.mark.parametrize("operation", ["sample", "arm", "watchdog"])
def test_valid_faulted_observation_advances_clock_floor_without_replacing_fault(operation: str) -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    first = _stale_fault(runtime)
    service_time = 2.0

    if operation == "sample":
        observed = runtime.sample(pressed=False, now_s=service_time)
    elif operation == "arm":
        observed = runtime.arm(now_s=service_time)
    else:
        observed = runtime.watchdog(now_s=service_time)

    assert observed == first

    # Recovery cannot move behind a valid service observation made while faulted.
    rejected_reset = runtime.reset(now_s=service_time - 0.001)
    assert rejected_reset == first
    assert runtime.faulted

    accepted_reset = runtime.reset(now_s=service_time)
    assert accepted_reset == InputEvent(False, Edge.NONE)
    assert not runtime.faulted


def test_recovery_after_fault_requires_release_even_after_clock_floor_service() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    _stale_fault(runtime)
    runtime.watchdog(now_s=2.0)
    assert runtime.reset(now_s=2.0) == InputEvent(False, Edge.NONE)

    # A held input after reset cannot become a synthetic press regardless of dwell.
    assert runtime.sample(pressed=True, now_s=2.01) == InputEvent(False, Edge.NONE)
    assert runtime.sample(pressed=True, now_s=2.20) == InputEvent(False, Edge.NONE)

    release_started = 2.21
    assert runtime.sample(pressed=False, now_s=release_started) == InputEvent(False, Edge.NONE)
    release_deadline = release_started + runtime.debounce_s
    assert runtime.sample(pressed=False, now_s=release_deadline) == InputEvent(False, Edge.NONE)

    press_started = release_deadline + 0.01
    assert runtime.sample(pressed=True, now_s=press_started) == InputEvent(False, Edge.NONE)
    press_deadline = press_started + runtime.debounce_s
    assert runtime.sample(pressed=True, now_s=press_deadline) == InputEvent(True, Edge.PRESSED)
