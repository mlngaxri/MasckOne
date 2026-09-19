from masck_one.hmi_runtime import DebouncedInput, Edge


def test_watchdog_faults_if_sampling_never_starts():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    assert control.watchdog(now_s=10.0).faulted is False
    assert control.watchdog(now_s=10.25).faulted is False

    fault = control.watchdog(now_s=10.251)
    assert fault.faulted is True
    assert fault.stable_pressed is False
    assert fault.edge is Edge.NONE
    assert fault.fault == "input stream did not start"


def test_first_sample_inside_startup_window_cancels_startup_timeout():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    control.watchdog(now_s=5.0)
    sample = control.sample(pressed=False, now_s=5.20)
    assert sample.faulted is False

    assert control.watchdog(now_s=5.45).faulted is False
    fault = control.watchdog(now_s=5.451)
    assert fault.faulted is True
    assert fault.fault == "input stream became stale"


def test_startup_watchdog_uses_shared_monotonic_clock():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    control.watchdog(now_s=2.0)
    fault = control.sample(pressed=False, now_s=1.999)
    assert fault.faulted is True
    assert fault.fault == "input time moved backwards"


def test_reset_requires_release_and_restarts_startup_window():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.watchdog(now_s=0.0)
    assert control.watchdog(now_s=0.251).faulted is True

    control.reset()
    assert control.watchdog(now_s=1.0).faulted is False
    assert control.watchdog(now_s=1.251).fault == "input stream did not start"
