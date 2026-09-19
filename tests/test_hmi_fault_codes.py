import pytest

from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        (lambda c: c.sample(pressed=1, now_s=0.0), FaultCode.PRESSED_NOT_BOOL),
        (lambda c: c.sample(pressed=False, now_s=float("nan")), FaultCode.SAMPLE_TIME_INVALID),
        (lambda c: c.arm(now_s=float("inf")), FaultCode.ARM_TIME_INVALID),
        (lambda c: c.watchdog(now_s=float("-inf")), FaultCode.WATCHDOG_TIME_INVALID),
    ],
)
def test_malformed_inputs_expose_stable_fault_codes(operation, expected):
    event = operation(DebouncedInput())
    assert event.faulted is True
    assert event.stable_pressed is False
    assert event.edge is Edge.NONE
    assert event.fault_code is expected
    assert event.fault


def test_time_regression_codes_identify_the_failing_api():
    sample_control = DebouncedInput()
    sample_control.sample(pressed=False, now_s=2.0)
    assert sample_control.sample(pressed=False, now_s=1.0).fault_code is FaultCode.SAMPLE_TIME_REGRESSION

    arm_control = DebouncedInput()
    arm_control.arm(now_s=2.0)
    assert arm_control.arm(now_s=1.0).fault_code is FaultCode.ARM_TIME_REGRESSION

    watchdog_control = DebouncedInput()
    watchdog_control.watchdog(now_s=2.0)
    assert watchdog_control.watchdog(now_s=1.0).fault_code is FaultCode.WATCHDOG_TIME_REGRESSION


def test_timeout_codes_distinguish_startup_from_stale_stream():
    startup = DebouncedInput(stale_after_s=0.25)
    startup.arm(now_s=0.0)
    assert startup.watchdog(now_s=0.251).fault_code is FaultCode.INPUT_STREAM_NOT_STARTED

    stale = DebouncedInput(stale_after_s=0.25)
    stale.sample(pressed=False, now_s=0.0)
    assert stale.watchdog(now_s=0.251).fault_code is FaultCode.INPUT_STREAM_STALE


def test_first_fault_code_is_latched_with_first_diagnostic_until_reset():
    control = DebouncedInput()
    first = control.sample(pressed=1, now_s=1.0)
    later = control.watchdog(now_s=float("nan"))

    assert first.fault_code is FaultCode.PRESSED_NOT_BOOL
    assert later.fault_code is first.fault_code
    assert later.fault == first.fault

    control.reset()
    new_fault = control.watchdog(now_s=float("nan"))
    assert new_fault.fault_code is FaultCode.WATCHDOG_TIME_INVALID
    assert new_fault.fault != first.fault


def test_healthy_events_never_carry_fault_metadata():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    first = control.sample(pressed=True, now_s=0.0)
    pressed = control.sample(pressed=True, now_s=0.03)

    assert first.faulted is False and first.fault is None and first.fault_code is None
    assert pressed.edge is Edge.PRESSED
    assert pressed.faulted is False and pressed.fault is None and pressed.fault_code is None
