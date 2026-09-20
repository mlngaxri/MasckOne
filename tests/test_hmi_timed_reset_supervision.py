"""Regression tests for timed healthy-reset stream supervision.

Synthetic firmware-time traces only. These tests establish deterministic software
behaviour; they do not establish physical switch, sensor, or hardware timing.
"""

from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode


def test_timed_healthy_reset_faults_stale_held_stream_fail_closed():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=True, now_s=1.00)
    pressed = control.sample(pressed=True, now_s=1.03)
    assert pressed.edge is Edge.PRESSED
    assert pressed.stable_pressed is True

    control.reset(now_s=1.281)

    assert control.faulted is True
    fault = control.watchdog(now_s=1.281)
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE
    assert fault.stable_pressed is False
    assert fault.edge is Edge.NONE


def test_timed_healthy_reset_accepts_exact_stale_deadline_without_extending_it():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=False, now_s=2.00)

    control.reset(now_s=2.25)
    assert control.faulted is False

    fault = control.arm(now_s=2.250001)
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE
    assert fault.stable_pressed is False


def test_timed_healthy_reset_faults_when_armed_stream_never_started():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    assert control.arm(now_s=3.00).faulted is False

    control.reset(now_s=3.251)

    assert control.faulted is True
    fault = control.sample(pressed=False, now_s=3.251)
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED
    assert fault.stable_pressed is False
    assert fault.edge is Edge.NONE


def test_timed_healthy_reset_does_not_start_supervision_when_runtime_is_unarmed():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    control.reset(now_s=4.00)
    assert control.faulted is False
    assert control.watchdog(now_s=4.30).faulted is False

    fault = control.watchdog(now_s=4.551)
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED
