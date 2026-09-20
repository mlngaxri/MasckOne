"""Synthetic regressions for chronological HMI supervision fault priority.

These traces verify deterministic software behavior only. They do not establish
physical switch, sensor, transport, or hardware timing performance.
"""

import pytest

from masck_one.hmi_runtime import DebouncedInput, FaultCode


@pytest.mark.parametrize("pressed", [0, 1, None, "pressed"])
def test_expired_sample_stream_wins_over_malformed_level(pressed):
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=True, now_s=1.00)
    assert control.sample(pressed=True, now_s=1.03).stable_pressed is True

    fault = control.sample(pressed=pressed, now_s=1.281)

    assert fault.faulted is True
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE
    assert fault.stable_pressed is False


def test_malformed_level_inside_live_stream_retains_level_fault():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=False, now_s=2.00)

    fault = control.sample(pressed=1, now_s=2.10)

    assert fault.faulted is True
    assert fault.fault_code is FaultCode.PRESSED_NOT_BOOL


def test_expired_no_start_window_wins_over_malformed_first_level():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    assert control.arm(now_s=3.00).faulted is False

    fault = control.sample(pressed=None, now_s=3.251)

    assert fault.faulted is True
    assert fault.fault_code is FaultCode.INPUT_STREAM_NOT_STARTED
    assert fault.stable_pressed is False
