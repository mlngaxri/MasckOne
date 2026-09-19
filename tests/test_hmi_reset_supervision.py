from masck_one.hmi_runtime import DebouncedInput, FaultCode


def _stale_fault() -> DebouncedInput:
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=False, now_s=10.0)
    fault = control.watchdog(now_s=10.251)
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE
    return control


def test_fault_reset_resumes_startup_supervision_without_explicit_arm():
    control = _stale_fault()
    control.reset()

    fault = control.watchdog(now_s=10.502)

    assert fault.faulted is True
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED
    assert fault.fault == "input stream did not start"


def test_late_first_recovery_sample_cannot_cancel_reset_supervision():
    control = _stale_fault()
    control.reset()

    fault = control.sample(pressed=False, now_s=10.502)

    assert fault.faulted is True
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED


def test_repeated_arm_after_reset_cannot_postpone_recovery_deadline():
    control = _stale_fault()
    control.reset()

    assert control.arm(now_s=10.40).faulted is False
    fault = control.arm(now_s=10.502)

    assert fault.faulted is True
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED


def test_recovery_sample_inside_window_enters_normal_stale_supervision():
    control = _stale_fault()
    control.reset()

    assert control.sample(pressed=False, now_s=10.40).faulted is False
    assert control.sample(pressed=False, now_s=10.43).faulted is False
    assert control.watchdog(now_s=10.68).faulted is False
    stale = control.watchdog(now_s=10.681)

    assert stale.faulted is True
    assert stale.fault_code is FaultCode.INPUT_STREAM_STALE


def test_fault_without_trusted_timestamp_still_waits_for_first_watchdog_anchor():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    fault = control.sample(pressed=1, now_s=0.0)
    assert fault.fault_code is FaultCode.PRESSED_NOT_BOOL
    control.reset()

    assert control.watchdog(now_s=100.0).faulted is False
    late = control.watchdog(now_s=100.251)

    assert late.faulted is True
    assert late.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED
