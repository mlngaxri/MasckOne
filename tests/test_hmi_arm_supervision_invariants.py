from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode, InputEvent


def test_repeated_arm_calls_cannot_extend_no_sample_deadline() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    armed_at = 1.0
    assert runtime.arm(now_s=armed_at) == InputEvent(False, Edge.NONE)
    assert runtime.arm(now_s=1.10) == InputEvent(False, Edge.NONE)
    deadline = armed_at + runtime.stale_after_s
    assert runtime.arm(now_s=deadline) == InputEvent(False, Edge.NONE)

    fault = runtime.arm(now_s=deadline + 0.000001)
    assert fault.faulted
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED


def test_arm_after_sampling_cannot_refresh_sample_staleness_deadline() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    runtime.arm(now_s=2.0)
    sample_at = 2.01
    assert runtime.sample(pressed=False, now_s=sample_at) == InputEvent(False, Edge.NONE)
    assert runtime.arm(now_s=2.20) == InputEvent(False, Edge.NONE)
    deadline = sample_at + runtime.stale_after_s
    assert runtime.arm(now_s=deadline) == InputEvent(False, Edge.NONE)

    fault = runtime.arm(now_s=deadline + 0.000001)
    assert fault.faulted
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE


def test_arm_at_exact_sample_deadline_is_healthy_and_does_not_synthesise_edge() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    runtime.arm(now_s=3.0)
    press_started = 3.01
    runtime.sample(pressed=True, now_s=press_started)
    press_deadline = press_started + runtime.debounce_s
    assert runtime.sample(pressed=True, now_s=press_deadline) == InputEvent(True, Edge.PRESSED)

    stale_deadline = press_deadline + runtime.stale_after_s
    assert runtime.arm(now_s=stale_deadline) == InputEvent(True, Edge.NONE)

    fault = runtime.arm(now_s=stale_deadline + 0.000001)
    assert fault.faulted
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE
    assert not fault.stable_pressed
    assert fault.edge is Edge.NONE


def test_recovery_arm_calls_cannot_replace_or_clear_required_electrical_release() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    armed_at = 4.0
    runtime.arm(now_s=armed_at)
    initial_deadline = armed_at + runtime.stale_after_s
    fault_at = initial_deadline + 0.001
    fault = runtime.watchdog(now_s=fault_at)
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED
    assert runtime.reset(now_s=fault_at) == InputEvent(False, Edge.NONE)

    first_arm_at = fault_at + 0.05
    second_arm_at = fault_at + 0.15
    assert runtime.arm(now_s=first_arm_at) == InputEvent(False, Edge.NONE)
    assert runtime.arm(now_s=second_arm_at) == InputEvent(False, Edge.NONE)

    # Repeated lifecycle arm calls must not clear the post-fault release interlock.
    # A held control transfers supervision to the real sample stream but remains
    # suppressed until an electrical release itself survives the debounce window.
    held_at = second_arm_at + 0.01
    assert runtime.sample(pressed=True, now_s=held_at) == InputEvent(False, Edge.NONE)
    assert runtime.sample(pressed=True, now_s=held_at + 0.01) == InputEvent(False, Edge.NONE)

    release_started = held_at + 0.02
    assert runtime.sample(pressed=False, now_s=release_started) == InputEvent(False, Edge.NONE)
    release_deadline = release_started + runtime.debounce_s
    assert runtime.sample(pressed=False, now_s=release_deadline) == InputEvent(False, Edge.NONE)

    # Recovery release is not itself an actionable edge. Only a fresh press after
    # qualification may become visible to downstream control logic.
    press_started = release_deadline + 0.01
    assert runtime.sample(pressed=True, now_s=press_started) == InputEvent(False, Edge.NONE)
    press_deadline = press_started + runtime.debounce_s
    assert runtime.sample(pressed=True, now_s=press_deadline) == InputEvent(True, Edge.PRESSED)


def test_first_valid_sample_after_rearm_replaces_no_sample_supervision_with_sample_supervision() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    armed_at = 5.0
    runtime.arm(now_s=armed_at)
    sample_at = 5.20
    assert runtime.sample(pressed=False, now_s=sample_at) == InputEvent(False, Edge.NONE)

    # The original arm deadline is no longer authoritative once a valid electrical
    # sample exists. Supervision now follows the last real sample only.
    original_deadline = armed_at + runtime.stale_after_s
    assert runtime.watchdog(now_s=original_deadline + 0.001) == InputEvent(False, Edge.NONE)
    sample_deadline = sample_at + runtime.stale_after_s
    assert runtime.watchdog(now_s=sample_deadline) == InputEvent(False, Edge.NONE)

    stale = runtime.watchdog(now_s=sample_deadline + 0.000001)
    assert stale.faulted
    assert stale.fault_code is FaultCode.INPUT_STREAM_STALE
