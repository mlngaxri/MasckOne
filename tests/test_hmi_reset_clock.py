from masck_one.hmi_runtime import DebouncedInput, Edge


def _fault_after_valid_sample() -> DebouncedInput:
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=False, now_s=10.0)
    fault = control.watchdog(now_s=10.251)
    assert fault.faulted is True
    assert fault.fault == "input stream became stale"
    return control


def test_reset_does_not_allow_sample_clock_to_rewind():
    control = _fault_after_valid_sample()

    control.reset()
    fault = control.sample(pressed=False, now_s=10.250)

    assert fault.faulted is True
    assert fault.stable_pressed is False
    assert fault.edge is Edge.NONE
    assert fault.fault == "input time moved backwards"


def test_reset_does_not_allow_arm_clock_to_rewind():
    control = _fault_after_valid_sample()

    control.reset()
    fault = control.arm(now_s=10.250)

    assert fault.faulted is True
    assert fault.fault == "arm time moved backwards"


def test_reset_does_not_allow_watchdog_clock_to_rewind():
    control = _fault_after_valid_sample()

    control.reset()
    fault = control.watchdog(now_s=10.250)

    assert fault.faulted is True
    assert fault.fault == "watchdog time moved backwards"


def test_reset_accepts_equal_timestamp_then_requires_debounced_release():
    control = _fault_after_valid_sample()

    control.reset()
    assert control.arm(now_s=10.251).faulted is False
    assert control.sample(pressed=False, now_s=10.251).faulted is False
    released = control.sample(pressed=False, now_s=10.281)

    assert released.faulted is False
    assert released.stable_pressed is False
    assert released.edge is Edge.NONE

    control.sample(pressed=True, now_s=10.282)
    pressed = control.sample(pressed=True, now_s=10.312)
    assert pressed.faulted is False
    assert pressed.stable_pressed is True
    assert pressed.edge is Edge.PRESSED
