from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode, InputEvent


def test_repeated_arm_calls_cannot_extend_no_sample_deadline() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    assert runtime.arm(now_s=1.0) == InputEvent(False, Edge.NONE)
    assert runtime.arm(now_s=1.10) == InputEvent(False, Edge.NONE)
    assert runtime.arm(now_s=1.25) == InputEvent(False, Edge.NONE)

    fault = runtime.arm(now_s=1.250001)
    assert fault.faulted
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED


def test_arm_after_sampling_cannot_refresh_sample_staleness_deadline() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    runtime.arm(now_s=2.0)
    assert runtime.sample(pressed=False, now_s=2.01) == InputEvent(False, Edge.NONE)
    assert runtime.arm(now_s=2.20) == InputEvent(False, Edge.NONE)
    assert runtime.arm(now_s=2.26) == InputEvent(False, Edge.NONE)

    fault = runtime.arm(now_s=2.260001)
    assert fault.faulted
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE


def test_arm_at_exact_sample_deadline_is_healthy_and_does_not_synthesise_edge() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    runtime.arm(now_s=3.0)
    runtime.sample(pressed=True, now_s=3.01)
    press_deadline = 3.01 + runtime.debounce_s
    assert runtime.sample(pressed=True, now_s=press_deadline) == InputEvent(True, Edge.PRESSED)

    stale_deadline = press_deadline + runtime.stale_after_s
    assert runtime.arm(now_s=stale_deadline) == InputEvent(True, Edge.NONE)

    fault = runtime.arm(now_s=stale_deadline + 0.000001)
    assert fault.faulted
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE
    assert not fault.stable_pressed
    assert fault.edge is Edge.NONE


def test_recovery_arm_calls_cannot_replace_required_electrical_release_samples() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    runtime.arm(now_s=4.0)
    fault = runtime.watchdog(now_s=4.251)
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED
    assert runtime.reset(now_s=4.251) == InputEvent(False, Edge.NONE)

    assert runtime.arm(now_s=4.30) == InputEvent(False, Edge.NONE)
    assert runtime.arm(now_s=4.40) == InputEvent(False, Edge.NONE)
    assert runtime.arm(now_s=4.501) == InputEvent(False, Edge.NONE)

    stale = runtime.arm(now_s=4.501001)
    assert stale.faulted
    assert stale.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED


def test_first_valid_sample_after_rearm_replaces_no_sample_supervision_with_sample_supervision() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    runtime.arm(now_s=5.0)
    sample_at = 5.20
    assert runtime.sample(pressed=False, now_s=sample_at) == InputEvent(False, Edge.NONE)

    # The original arm deadline is no longer authoritative once a valid electrical
    # sample exists. Supervision now follows the last real sample only.
    assert runtime.watchdog(now_s=5.251) == InputEvent(False, Edge.NONE)
    assert runtime.watchdog(now_s=sample_at + runtime.stale_after_s) == InputEvent(False, Edge.NONE)

    stale = runtime.watchdog(now_s=sample_at + runtime.stale_after_s + 0.000001)
    assert stale.faulted
    assert stale.fault_code is FaultCode.INPUT_STREAM_STALE
