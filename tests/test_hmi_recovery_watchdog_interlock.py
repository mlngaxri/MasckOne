from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode, InputEvent


def _fault_then_reset(runtime: DebouncedInput, *, start_s: float) -> float:
    runtime.arm(now_s=start_s)
    fault_at = start_s + runtime.stale_after_s + 0.001
    fault = runtime.watchdog(now_s=fault_at)
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED
    assert runtime.reset(now_s=fault_at) == InputEvent(False, Edge.NONE)
    return fault_at


def test_recovery_release_samples_refresh_watchdog_without_bypassing_release_interlock() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    reset_at = _fault_then_reset(runtime, start_s=1.0)

    # A held control is still a valid electrical sample for stream supervision, but it
    # must never satisfy the mandatory post-fault release interlock.
    held_at = reset_at + 0.20
    assert runtime.sample(pressed=True, now_s=held_at) == InputEvent(False, Edge.NONE)
    assert runtime.watchdog(now_s=held_at + runtime.stale_after_s) == InputEvent(False, Edge.NONE)

    # Crossing the refreshed sample deadline fails closed even though recovery has not
    # yet completed. Supervision and release qualification remain independent gates.
    stale = runtime.watchdog(now_s=held_at + runtime.stale_after_s + 0.001)
    assert stale.fault_code is FaultCode.INPUT_STREAM_STALE
    assert stale.faulted


def test_recovery_release_dwell_does_not_emit_edge_or_extend_without_samples() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    reset_at = _fault_then_reset(runtime, start_s=2.0)

    release_started = reset_at + 0.01
    assert runtime.sample(pressed=False, now_s=release_started) == InputEvent(False, Edge.NONE)

    # Watchdog service does not count as release dwell evidence and does not refresh the
    # sample stream. The release candidate may exist, but stale sampling still wins.
    assert runtime.watchdog(now_s=release_started + runtime.stale_after_s) == InputEvent(False, Edge.NONE)
    stale = runtime.watchdog(now_s=release_started + runtime.stale_after_s + 0.001)
    assert stale.fault_code is FaultCode.INPUT_STREAM_STALE


def test_completed_recovery_requires_fresh_press_after_release_and_supervision() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    reset_at = _fault_then_reset(runtime, start_s=3.0)

    release_started = reset_at + 0.01
    runtime.sample(pressed=False, now_s=release_started)
    release_deadline = release_started + runtime.debounce_s
    assert runtime.sample(pressed=False, now_s=release_deadline) == InputEvent(False, Edge.NONE)

    # Recovery completion itself is never a RELEASED edge. Only a subsequent fresh,
    # fully debounced press can become an actionable event.
    press_started = release_deadline + 0.01
    assert runtime.sample(pressed=True, now_s=press_started) == InputEvent(False, Edge.NONE)
    press_deadline = press_started + runtime.debounce_s
    assert runtime.sample(pressed=True, now_s=press_deadline) == InputEvent(True, Edge.PRESSED)
