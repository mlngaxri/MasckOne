from masck_one.hmi_runtime import DebouncedInput, Edge


def test_malformed_sample_cannot_replace_latched_fault_cause():
    control = DebouncedInput()
    control.sample(pressed=False, now_s=1.0)
    original = control.sample(pressed=False, now_s=0.9)
    assert original.faulted is True
    assert original.fault == "input time moved backwards"

    repeated = control.sample(pressed="bad", now_s=float("nan"))
    assert repeated.faulted is True
    assert repeated.stable_pressed is False
    assert repeated.edge is Edge.NONE
    assert repeated.fault == original.fault


def test_malformed_watchdog_cannot_replace_latched_fault_cause():
    control = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    control.sample(pressed=True, now_s=0.0)
    control.sample(pressed=True, now_s=0.03)
    original = control.watchdog(now_s=0.281)
    assert original.faulted is True
    assert original.fault == "input stream became stale"

    repeated = control.watchdog(now_s=float("nan"))
    assert repeated.faulted is True
    assert repeated.stable_pressed is False
    assert repeated.edge is Edge.NONE
    assert repeated.fault == original.fault


def test_reset_allows_new_fault_cause_to_latch():
    control = DebouncedInput()
    control.sample(pressed=False, now_s=1.0)
    assert control.sample(pressed=False, now_s=0.9).fault == "input time moved backwards"

    control.reset()
    new_fault = control.sample(pressed="bad", now_s=0.0)
    assert new_fault.faulted is True
    assert new_fault.fault == "pressed must be an exact bool"
