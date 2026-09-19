from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode


def test_arm_faults_when_existing_sample_stream_is_stale():
    control = DebouncedInput(debounce_s=0.030, stale_after_s=0.250)
    control.sample(pressed=False, now_s=1.0)

    fault = control.arm(now_s=1.251)

    assert fault.faulted is True
    assert fault.stable_pressed is False
    assert fault.edge is Edge.NONE
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE
    assert fault.fault == "input stream became stale"


def test_arm_preserves_healthy_stream_before_stale_deadline():
    control = DebouncedInput(debounce_s=0.030, stale_after_s=0.250)
    control.sample(pressed=False, now_s=1.0)

    event = control.arm(now_s=1.250)

    assert event.faulted is False
    assert event.stable_pressed is False
    assert event.edge is Edge.NONE


def test_repeated_arm_cannot_extend_existing_sample_stale_deadline():
    control = DebouncedInput(debounce_s=0.030, stale_after_s=0.250)
    control.sample(pressed=False, now_s=1.0)

    assert control.arm(now_s=1.100).faulted is False
    assert control.arm(now_s=1.200).faulted is False
    fault = control.arm(now_s=1.251)

    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE


def test_arm_fails_closed_if_last_stable_state_was_pressed():
    control = DebouncedInput(debounce_s=0.030, stale_after_s=0.250)
    control.sample(pressed=True, now_s=1.0)
    pressed = control.sample(pressed=True, now_s=1.030)
    assert pressed.edge is Edge.PRESSED
    assert pressed.stable_pressed is True

    fault = control.arm(now_s=1.281)

    assert fault.faulted is True
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE
    assert fault.stable_pressed is False
