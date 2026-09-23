from masck_one.hmi_event_wire import input_event_from_wire, input_event_to_wire
from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode, InputEvent


def _wire_round_trip(event: InputEvent) -> InputEvent:
    decoded = input_event_from_wire(input_event_to_wire(event))
    # Human-readable diagnostics are intentionally not transported. The machine
    # contract must preserve every field that firmware is allowed to act on.
    return decoded


def test_runtime_fault_recovery_trace_remains_fail_closed_across_wire_boundary() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)

    assert _wire_round_trip(runtime.arm(now_s=1.0)) == InputEvent(False, Edge.NONE)
    assert _wire_round_trip(runtime.sample(pressed=False, now_s=1.01)) == InputEvent(False, Edge.NONE)

    fault_at = 1.01 + runtime.stale_after_s + 0.001
    fault = _wire_round_trip(runtime.watchdog(now_s=fault_at))
    assert fault == InputEvent(
        stable_pressed=False,
        edge=Edge.NONE,
        faulted=True,
        fault_code=FaultCode.INPUT_STREAM_STALE,
    )

    # A held control cannot become actionable merely because the fault was reset.
    reset_at = fault_at + 0.10
    assert _wire_round_trip(runtime.reset(now_s=reset_at)) == InputEvent(False, Edge.NONE)
    assert _wire_round_trip(runtime.sample(pressed=True, now_s=reset_at + 0.01)) == InputEvent(False, Edge.NONE)

    # Recovery requires a real debounced release. Neither sample may synthesize a
    # release edge because the pre-fault held state was invalidated by the fault.
    release_at = reset_at + 0.02
    assert _wire_round_trip(runtime.sample(pressed=False, now_s=release_at)) == InputEvent(False, Edge.NONE)
    assert _wire_round_trip(runtime.sample(pressed=False, now_s=release_at + runtime.debounce_s)) == InputEvent(
        False, Edge.NONE
    )

    # Only a fresh post-release press may cross the firmware boundary as actionable.
    press_at = release_at + runtime.debounce_s + 0.01
    assert _wire_round_trip(runtime.sample(pressed=True, now_s=press_at)) == InputEvent(False, Edge.NONE)
    assert _wire_round_trip(runtime.sample(pressed=True, now_s=press_at + runtime.debounce_s)) == InputEvent(
        True, Edge.PRESSED
    )


def test_wire_boundary_preserves_first_fault_during_post_fault_service_calls() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    runtime.arm(now_s=2.0)
    runtime.sample(pressed=False, now_s=2.01)

    fault_at = 2.01 + runtime.stale_after_s + 0.001
    expected = _wire_round_trip(runtime.watchdog(now_s=fault_at))
    assert expected.fault_code is FaultCode.INPUT_STREAM_STALE

    # Later malformed electrical data must not replace the chronological first
    # fault or leak an actionable edge through serialization.
    observed = _wire_round_trip(runtime.sample(pressed="malformed", now_s=fault_at + 0.05))  # type: ignore[arg-type]
    assert observed == expected
    assert observed.edge is Edge.NONE
    assert not observed.stable_pressed

    # The valid post-fault observation advances the runtime clock floor. A reset
    # behind it remains faulted, and the wire representation must preserve that.
    stale_reset = _wire_round_trip(runtime.reset(now_s=fault_at + 0.04))
    assert stale_reset == expected
    assert runtime.faulted
