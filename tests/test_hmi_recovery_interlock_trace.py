from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode


def test_fault_recovery_requires_release_before_new_press_across_service_paths() -> None:
    """A held command must not reappear merely because firmware clears a fault."""
    hmi = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    hmi.sample(pressed=True, now_s=0.00)
    pressed = hmi.sample(pressed=True, now_s=0.03)
    assert pressed.edge is Edge.PRESSED
    assert pressed.stable_pressed

    fault = hmi.watchdog(now_s=0.281)
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE
    assert not fault.stable_pressed

    # Servicing a faulted runtime may advance its clock floor, but cannot revive
    # the previously held command or replace the first fault diagnostic.
    held = hmi.sample(pressed=True, now_s=0.30)
    assert held.fault_code is FaultCode.INPUT_STREAM_STALE
    assert not held.stable_pressed
    assert hmi.arm(now_s=0.31).fault_code is FaultCode.INPUT_STREAM_STALE

    hmi.reset(now_s=0.32)

    # A still-held control remains suppressed for any duration after recovery.
    for now_s in (0.33, 0.40, 0.50):
        event = hmi.sample(pressed=True, now_s=now_s)
        assert event.edge is Edge.NONE
        assert not event.stable_pressed
        assert not event.faulted

    # Only a debounced physical release rearms the input.
    assert hmi.sample(pressed=False, now_s=0.51).edge is Edge.NONE
    released = hmi.sample(pressed=False, now_s=0.54)
    assert released.edge is Edge.NONE
    assert not released.stable_pressed

    # The next press must itself debounce before firmware sees a command.
    assert hmi.sample(pressed=True, now_s=0.55).edge is Edge.NONE
    repressed = hmi.sample(pressed=True, now_s=0.58)
    assert repressed.edge is Edge.PRESSED
    assert repressed.stable_pressed
