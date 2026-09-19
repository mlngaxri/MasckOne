from masck_one.hmi_runtime import DebouncedInput, Edge


def test_explicit_arm_starts_no_sample_deadline_before_first_watchdog():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    assert control.arm(now_s=10.0).faulted is False
    fault = control.watchdog(now_s=10.251)

    assert fault.faulted is True
    assert fault.stable_pressed is False
    assert fault.edge is Edge.NONE
    assert fault.fault == "input stream did not start"


def test_repeated_arm_cannot_postpone_startup_deadline():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    control.arm(now_s=1.0)
    assert control.arm(now_s=1.20).faulted is False
    fault = control.arm(now_s=1.251)

    assert fault.faulted is True
    assert fault.fault == "input stream did not start"


def test_late_first_sample_after_explicit_arm_fails_closed():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    control.arm(now_s=2.0)
    fault = control.sample(pressed=False, now_s=2.251)

    assert fault.faulted is True
    assert fault.edge is Edge.NONE
    assert fault.fault == "input stream did not start"


def test_first_sample_inside_explicit_startup_window_transfers_to_stale_supervision():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    control.arm(now_s=3.0)
    assert control.sample(pressed=False, now_s=3.20).faulted is False
    assert control.watchdog(now_s=3.45).faulted is False
    fault = control.watchdog(now_s=3.451)

    assert fault.faulted is True
    assert fault.fault == "input stream became stale"


def test_arm_uses_shared_monotonic_clock_and_latches_fault():
    control = DebouncedInput()

    control.arm(now_s=5.0)
    fault = control.arm(now_s=4.999)

    assert fault.faulted is True
    assert fault.fault == "arm time moved backwards"
    assert control.watchdog(now_s=6.0).fault == "arm time moved backwards"


def test_arm_after_sampling_does_not_restart_startup_supervision():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    control.sample(pressed=True, now_s=0.0)
    assert control.sample(pressed=True, now_s=0.03).edge is Edge.PRESSED
    event = control.arm(now_s=0.10)

    assert event.faulted is False
    assert event.stable_pressed is True
    assert event.edge is Edge.NONE
    assert control.watchdog(now_s=0.281).fault == "input stream became stale"
