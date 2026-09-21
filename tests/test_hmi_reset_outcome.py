from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode


def test_timed_healthy_reset_surfaces_stale_stream_fault_immediately() -> None:
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=False, now_s=1.0)

    event = control.reset(now_s=1.251)

    assert event.faulted is True
    assert event.fault_code is FaultCode.INPUT_STREAM_STALE
    assert event.stable_pressed is False
    assert event.edge is Edge.NONE
    assert control.faulted is True


def test_healthy_reset_returns_current_stable_state_without_edge() -> None:
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=True, now_s=2.0)
    control.sample(pressed=True, now_s=2.03)

    event = control.reset(now_s=2.04)

    assert event.faulted is False
    assert event.stable_pressed is True
    assert event.edge is Edge.NONE


def test_fault_reset_returns_fail_closed_recovery_state() -> None:
    control = DebouncedInput()
    control.sample(pressed=False, now_s=3.0)
    assert control.sample(pressed=False, now_s=2.9).faulted is True

    event = control.reset(now_s=3.1)

    assert event.faulted is False
    assert event.stable_pressed is False
    assert event.edge is Edge.NONE
    assert control.faulted is False
