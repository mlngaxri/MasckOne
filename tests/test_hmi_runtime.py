import pytest

from masck_one.hmi_runtime import DebouncedInput, Edge, HmiInputError


def test_press_and_release_require_continuous_debounce_interval():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    assert control.sample(pressed=True, now_s=0.00).edge is Edge.NONE
    assert control.sample(pressed=True, now_s=0.029).edge is Edge.NONE
    event = control.sample(pressed=True, now_s=0.030)
    assert event.edge is Edge.PRESSED
    assert event.stable_pressed is True

    assert control.sample(pressed=False, now_s=0.040).edge is Edge.NONE
    event = control.sample(pressed=False, now_s=0.070)
    assert event.edge is Edge.RELEASED
    assert event.stable_pressed is False


def test_healthy_reset_does_not_drop_a_stable_held_input():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=True, now_s=0.0)
    pressed = control.sample(pressed=True, now_s=0.03)
    assert pressed.edge is Edge.PRESSED
    assert pressed.stable_pressed is True

    control.reset()
    event = control.watchdog(now_s=0.04)

    assert event.faulted is False
    assert event.stable_pressed is True
    assert event.edge is Edge.NONE


def test_healthy_reset_does_not_restart_an_inflight_debounce_candidate():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    assert control.sample(pressed=True, now_s=1.0).edge is Edge.NONE

    control.reset()
    event = control.sample(pressed=True, now_s=1.03)

    assert event.faulted is False
    assert event.edge is Edge.PRESSED
    assert event.stable_pressed is True


def test_bounce_restarts_candidate_interval_and_never_emits_false_press():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    assert control.sample(pressed=True, now_s=0.000).edge is Edge.NONE
    assert control.sample(pressed=False, now_s=0.010).edge is Edge.NONE
    assert control.sample(pressed=True, now_s=0.020).edge is Edge.NONE
    assert control.sample(pressed=True, now_s=0.049).edge is Edge.NONE
    assert control.sample(pressed=True, now_s=0.050).edge is Edge.PRESSED


def test_stale_held_input_fails_closed_without_release_edge():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=True, now_s=0.0)
    assert control.sample(pressed=True, now_s=0.03).stable_pressed is True
    fault = control.watchdog(now_s=0.281)
    assert fault.faulted is True
    assert fault.stable_pressed is False
    assert fault.edge is Edge.NONE
    assert "stale" in fault.fault
    assert control.sample(pressed=True, now_s=0.29).faulted is True


def test_non_monotonic_time_faults_and_latches_until_reset():
    control = DebouncedInput()
    control.sample(pressed=False, now_s=1.0)
    fault = control.sample(pressed=False, now_s=0.9)
    assert fault.faulted is True
    assert control.sample(pressed=False, now_s=1.1).faulted is True
    control.reset()
    event = control.sample(pressed=False, now_s=1.1)
    assert event.faulted is False
    assert event.edge is Edge.NONE


def test_watchdog_clock_regression_faults_and_latches():
    control = DebouncedInput()
    control.sample(pressed=False, now_s=1.0)
    assert control.watchdog(now_s=1.1).faulted is False
    fault = control.watchdog(now_s=1.05)
    assert fault.faulted is True
    assert fault.stable_pressed is False
    assert fault.edge is Edge.NONE
    assert "backwards" in fault.fault


def test_sample_cannot_move_clock_backwards_after_watchdog():
    control = DebouncedInput()
    control.sample(pressed=False, now_s=1.0)
    assert control.watchdog(now_s=1.1).faulted is False
    fault = control.sample(pressed=True, now_s=1.05)
    assert fault.faulted is True
    assert fault.stable_pressed is False
    assert fault.edge is Edge.NONE
    assert "backwards" in fault.fault


def test_reset_cannot_reassert_a_command_while_control_remains_held():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=True, now_s=0.00)
    assert control.sample(pressed=True, now_s=0.03).edge is Edge.PRESSED
    assert control.watchdog(now_s=0.281).faulted is True

    control.reset()
    assert control.sample(pressed=True, now_s=0.281).stable_pressed is False
    assert control.sample(pressed=True, now_s=0.381).edge is Edge.NONE
    assert control.sample(pressed=True, now_s=0.481).stable_pressed is False

    assert control.sample(pressed=False, now_s=0.491).edge is Edge.NONE
    assert control.sample(pressed=False, now_s=0.521).edge is Edge.NONE
    assert control.sample(pressed=True, now_s=0.531).edge is Edge.NONE
    event = control.sample(pressed=True, now_s=0.561)
    assert event.edge is Edge.PRESSED
    assert event.stable_pressed is True


def test_release_to_rearm_does_not_synthesise_release_edge():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=False, now_s=1.0)
    assert control.sample(pressed=False, now_s=0.9).faulted is True
    control.reset()
    assert control.sample(pressed=False, now_s=1.0).edge is Edge.NONE
    event = control.sample(pressed=False, now_s=1.03)
    assert event.faulted is False
    assert event.stable_pressed is False
    assert event.edge is Edge.NONE


def test_release_glitch_after_reset_does_not_rearm_control():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=True, now_s=0.00)
    assert control.sample(pressed=True, now_s=0.03).edge is Edge.PRESSED
    assert control.watchdog(now_s=0.281).faulted is True

    control.reset()
    assert control.sample(pressed=False, now_s=0.281).edge is Edge.NONE
    assert control.sample(pressed=True, now_s=0.291).edge is Edge.NONE
    assert control.sample(pressed=True, now_s=0.381).edge is Edge.NONE
    assert control.sample(pressed=True, now_s=0.481).stable_pressed is False

    assert control.sample(pressed=False, now_s=0.491).edge is Edge.NONE
    assert control.sample(pressed=False, now_s=0.520).edge is Edge.NONE
    assert control.sample(pressed=False, now_s=0.521).edge is Edge.NONE
    assert control.sample(pressed=True, now_s=0.531).edge is Edge.NONE
    assert control.sample(pressed=True, now_s=0.561).edge is Edge.PRESSED


@pytest.mark.parametrize("pressed", [0, 1, None, "pressed"])
def test_malformed_digital_level_faults(pressed):
    control = DebouncedInput()
    event = control.sample(pressed=pressed, now_s=0.0)
    assert event.faulted is True
    assert event.stable_pressed is False


@pytest.mark.parametrize("now_s", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_time_faults(now_s):
    control = DebouncedInput()
    assert control.sample(pressed=False, now_s=now_s).faulted is True


def test_invalid_timing_configuration_is_rejected():
    with pytest.raises(HmiInputError):
        DebouncedInput(debounce_s=0.0)
    with pytest.raises(HmiInputError):
        DebouncedInput(debounce_s=0.03, stale_after_s=0.03)
