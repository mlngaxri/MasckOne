import pytest

from masck_one.hmi_runtime import DebouncedInput, FaultCode


def _fault_at(now_s: float = 1.0) -> DebouncedInput:
    control = DebouncedInput()
    fault = control.sample(pressed="bad", now_s=now_s)  # type: ignore[arg-type]
    assert fault.fault_code is FaultCode.PRESSED_NOT_BOOL
    return control


@pytest.mark.parametrize("service", ["sample", "arm", "watchdog"])
def test_valid_post_fault_service_time_advances_reset_clock_floor(service):
    control = _fault_at()

    if service == "sample":
        repeated = control.sample(pressed=False, now_s=5.0)
    elif service == "arm":
        repeated = control.arm(now_s=5.0)
    else:
        repeated = control.watchdog(now_s=5.0)

    assert repeated.fault_code is FaultCode.PRESSED_NOT_BOOL
    reset = control.reset(now_s=4.999)
    assert reset.fault_code is FaultCode.PRESSED_NOT_BOOL
    assert reset.fault == "pressed must be an exact bool"
    assert control.faulted is True


def test_post_fault_service_does_not_replace_first_fault():
    control = _fault_at()

    later = control.watchdog(now_s=2.0)

    assert later.fault_code is FaultCode.PRESSED_NOT_BOOL
    assert later.fault == "pressed must be an exact bool"


def test_malformed_post_fault_time_does_not_replace_fault_or_poison_recovery_clock():
    control = _fault_at()

    repeated = control.watchdog(now_s=float("nan"))
    assert repeated.fault_code is FaultCode.PRESSED_NOT_BOOL

    control.reset(now_s=1.0)
    assert control.faulted is False


def test_regressed_post_fault_time_does_not_lower_clock_floor():
    control = _fault_at(now_s=10.0)

    repeated = control.arm(now_s=9.0)
    assert repeated.fault_code is FaultCode.PRESSED_NOT_BOOL

    reset = control.reset(now_s=9.5)
    assert reset.fault_code is FaultCode.PRESSED_NOT_BOOL
    assert reset.fault == "pressed must be an exact bool"
    assert control.faulted is True


def test_untimed_reset_preserves_latest_post_fault_service_observation():
    control = _fault_at()
    control.watchdog(now_s=5.0)

    control.reset()
    regressed = control.sample(pressed=False, now_s=4.999)

    assert regressed.faulted is True
    assert regressed.fault_code is FaultCode.SAMPLE_TIME_REGRESSION
