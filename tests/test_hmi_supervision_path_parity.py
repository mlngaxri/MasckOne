import pytest

from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode


STALE_AFTER_S = 0.250


def _started_control(*, pressed: bool = False) -> DebouncedInput:
    control = DebouncedInput(debounce_s=0.030, stale_after_s=STALE_AFTER_S)
    control.sample(pressed=pressed, now_s=1.0)
    if pressed:
        control.sample(pressed=True, now_s=1.030)
    return control


@pytest.mark.parametrize("service", ["arm", "sample", "watchdog"])
def test_existing_stream_is_accepted_at_exact_stale_deadline(service: str):
    control = _started_control()
    deadline = 1.0 + STALE_AFTER_S

    if service == "sample":
        event = control.sample(pressed=False, now_s=deadline)
    else:
        event = getattr(control, service)(now_s=deadline)

    assert event.faulted is False
    assert event.edge is Edge.NONE


@pytest.mark.parametrize("service", ["arm", "sample", "watchdog"])
def test_existing_stream_fails_closed_immediately_after_stale_deadline(service: str):
    control = _started_control(pressed=True)
    deadline = 1.030 + STALE_AFTER_S
    late = deadline + 1e-6

    if service == "sample":
        event = control.sample(pressed=True, now_s=late)
    else:
        event = getattr(control, service)(now_s=late)

    assert event.faulted is True
    assert event.fault_code is FaultCode.INPUT_STREAM_STALE
    assert event.fault == "input stream became stale"
    assert event.stable_pressed is False
    assert event.edge is Edge.NONE


@pytest.mark.parametrize("service", ["arm", "sample", "watchdog"])
def test_recovery_no_sample_supervision_has_identical_deadline_semantics(service: str):
    control = DebouncedInput(debounce_s=0.030, stale_after_s=STALE_AFTER_S)
    control.sample(pressed=False, now_s=1.0)
    control.sample(pressed=False, now_s=1.251)
    assert control.faulted is True

    control.reset(now_s=2.0)
    deadline = 2.0 + STALE_AFTER_S

    if service == "sample":
        at_deadline = control.sample(pressed=False, now_s=deadline)
    else:
        at_deadline = getattr(control, service)(now_s=deadline)

    assert at_deadline.faulted is False

    if service == "sample":
        # A sample at the deadline starts a new stream, so verify the next stale
        # boundary from that accepted sample rather than the recovery anchor.
        event = control.sample(pressed=False, now_s=deadline + STALE_AFTER_S + 1e-6)
        expected = FaultCode.INPUT_STREAM_STALE
    else:
        event = getattr(control, service)(now_s=deadline + 1e-6)
        expected = FaultCode.INPUT_STREAM_NOT_STARTED

    assert event.faulted is True
    assert event.fault_code is expected
    assert event.stable_pressed is False
    assert event.edge is Edge.NONE
