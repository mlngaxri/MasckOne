from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode


def _stale_fault() -> DebouncedInput:
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=False, now_s=10.0)
    fault = control.watchdog(now_s=10.251)
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE
    return control


def test_timed_fault_reset_starts_recovery_supervision_at_reset_request():
    control = _stale_fault()
    control.reset(now_s=20.0)

    assert control.watchdog(now_s=20.25).faulted is False
    fault = control.watchdog(now_s=20.251)

    assert fault.faulted is True
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED
    assert fault.fault == "input stream did not start"


def test_delayed_legacy_reset_does_not_reuse_old_fault_timestamp_as_deadline():
    control = _stale_fault()
    control.reset()

    assert control.watchdog(now_s=20.0).faulted is False
    fault = control.watchdog(now_s=20.251)

    assert fault.faulted is True
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED


def test_late_first_recovery_sample_cannot_cancel_timed_reset_supervision():
    control = _stale_fault()
    control.reset(now_s=20.0)

    fault = control.sample(pressed=False, now_s=20.251)

    assert fault.faulted is True
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED


def test_repeated_arm_after_timed_reset_cannot_postpone_recovery_deadline():
    control = _stale_fault()
    control.reset(now_s=20.0)

    assert control.arm(now_s=20.20).faulted is False
    fault = control.arm(now_s=20.251)

    assert fault.faulted is True
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED


def test_recovery_sample_inside_timed_reset_window_enters_normal_stale_supervision():
    control = _stale_fault()
    control.reset(now_s=20.0)

    assert control.sample(pressed=False, now_s=20.20).faulted is False
    assert control.sample(pressed=False, now_s=20.23).faulted is False
    assert control.watchdog(now_s=20.48).faulted is False
    stale = control.watchdog(now_s=20.481)

    assert stale.faulted is True
    assert stale.fault_code is FaultCode.INPUT_STREAM_STALE


def test_timed_reset_regression_preserves_existing_first_fault():
    control = _stale_fault()

    reset = control.reset(now_s=10.20)

    assert reset.faulted is True
    assert reset.fault_code is FaultCode.INPUT_STREAM_STALE
    assert reset.fault == "input stream became stale"
    assert control.faulted is True


def test_timed_reset_malformed_time_preserves_existing_first_fault():
    control = _stale_fault()

    reset = control.reset(now_s=float("nan"))

    assert reset.faulted is True
    assert reset.fault_code is FaultCode.INPUT_STREAM_STALE
    assert reset.fault == "input stream became stale"
    assert control.faulted is True


def test_healthy_timed_reset_malformed_time_latches_fail_closed_fault():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=True, now_s=1.0)
    pressed = control.sample(pressed=True, now_s=1.03)
    assert pressed.stable_pressed is True

    reset = control.reset(now_s=float("nan"))

    assert reset.faulted is True
    assert reset.fault_code is FaultCode.RESET_TIME_INVALID
    assert reset.stable_pressed is False
    assert reset.edge is Edge.NONE
    assert control.faulted is True


def test_healthy_timed_reset_clock_regression_latches_fail_closed_fault():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=True, now_s=2.0)
    pressed = control.sample(pressed=True, now_s=2.03)
    assert pressed.stable_pressed is True

    reset = control.reset(now_s=2.02)

    assert reset.faulted is True
    assert reset.fault_code is FaultCode.RESET_TIME_REGRESSION
    assert reset.stable_pressed is False
    assert reset.edge is Edge.NONE
    assert control.faulted is True


def test_valid_healthy_timed_reset_remains_non_destructive():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=True, now_s=3.0)
    pressed = control.sample(pressed=True, now_s=3.03)
    assert pressed.stable_pressed is True

    control.reset(now_s=3.04)

    still_pressed = control.sample(pressed=True, now_s=3.05)
    assert still_pressed.stable_pressed is True
    assert still_pressed.faulted is False


def test_healthy_timed_reset_advances_shared_clock_for_sample_path():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=True, now_s=4.0)
    pressed = control.sample(pressed=True, now_s=4.03)
    assert pressed.stable_pressed is True

    control.reset(now_s=4.10)
    regressed = control.sample(pressed=True, now_s=4.09)

    assert regressed.faulted is True
    assert regressed.fault_code is FaultCode.SAMPLE_TIME_REGRESSION


def test_healthy_timed_reset_advances_shared_clock_for_arm_path():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=False, now_s=6.0)

    control.reset(now_s=6.10)
    regressed = control.arm(now_s=6.09)

    assert regressed.faulted is True
    assert regressed.fault_code is FaultCode.ARM_TIME_REGRESSION


def test_healthy_timed_reset_advances_shared_clock_for_watchdog_path():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=False, now_s=8.0)

    control.reset(now_s=8.10)
    regressed = control.watchdog(now_s=8.09)

    assert regressed.faulted is True
    assert regressed.fault_code is FaultCode.WATCHDOG_TIME_REGRESSION


def test_healthy_untimed_reset_does_not_advance_shared_clock():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=False, now_s=10.0)

    control.reset()
    event = control.sample(pressed=False, now_s=10.0)

    assert event.faulted is False


def test_malformed_level_timestamp_can_bound_timed_recovery_supervision():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    fault = control.sample(pressed=1, now_s=100.0)
    assert fault.fault_code is FaultCode.PRESSED_NOT_BOOL
    control.reset(now_s=100.1)

    assert control.watchdog(now_s=100.35).faulted is False
    late = control.watchdog(now_s=100.351)

    assert late.faulted is True
    assert late.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED


def test_invalid_sample_time_does_not_create_a_recovery_clock_anchor():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    fault = control.sample(pressed=False, now_s=float("nan"))
    assert fault.fault_code is FaultCode.SAMPLE_TIME_INVALID
    control.reset()

    assert control.watchdog(now_s=100.0).faulted is False
    late = control.watchdog(now_s=100.251)

    assert late.faulted is True
    assert late.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED
