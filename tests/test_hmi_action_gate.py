import pytest

from masck_one.hmi_action_gate import HmiActionGateError, actionable_edge
from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode, InputEvent


def test_held_state_is_not_reinterpreted_as_repeated_action() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    runtime.arm(now_s=1.0)
    runtime.sample(pressed=False, now_s=1.01)
    runtime.sample(pressed=True, now_s=1.02)

    pressed = runtime.sample(pressed=True, now_s=1.05)
    assert actionable_edge(pressed) is Edge.PRESSED

    held = runtime.sample(pressed=True, now_s=1.06)
    assert held.stable_pressed
    assert actionable_edge(held) is Edge.NONE


def test_fault_and_recovery_cannot_create_action_without_fresh_edge() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    runtime.arm(now_s=2.0)
    runtime.sample(pressed=False, now_s=2.01)

    fault = runtime.watchdog(now_s=2.261)
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE
    assert actionable_edge(fault) is Edge.NONE

    runtime.reset(now_s=2.30)
    assert actionable_edge(runtime.sample(pressed=True, now_s=2.31)) is Edge.NONE
    assert actionable_edge(runtime.sample(pressed=False, now_s=2.32)) is Edge.NONE
    assert actionable_edge(runtime.sample(pressed=False, now_s=2.35)) is Edge.NONE

    assert actionable_edge(runtime.sample(pressed=True, now_s=2.36)) is Edge.NONE
    assert actionable_edge(runtime.sample(pressed=True, now_s=2.39)) is Edge.PRESSED


def test_release_edge_remains_explicitly_actionable() -> None:
    assert actionable_edge(InputEvent(True, Edge.PRESSED)) is Edge.PRESSED
    assert actionable_edge(InputEvent(False, Edge.RELEASED)) is Edge.RELEASED
    assert actionable_edge(InputEvent(True, Edge.NONE)) is Edge.NONE


def test_impossible_synthetic_events_fail_explicitly() -> None:
    impossible = (
        InputEvent(False, Edge.PRESSED),
        InputEvent(True, Edge.RELEASED),
        InputEvent(False, Edge.NONE, faulted=False, fault_code=FaultCode.INPUT_STREAM_STALE),
        InputEvent(True, Edge.NONE, faulted=True, fault="input stream stale", fault_code=FaultCode.INPUT_STREAM_STALE),
        InputEvent(False, Edge.PRESSED, faulted=True, fault="input stream stale", fault_code=FaultCode.INPUT_STREAM_STALE),
        InputEvent(False, Edge.NONE, faulted=True),
    )
    for event in impossible:
        with pytest.raises(HmiActionGateError):
            actionable_edge(event)


def test_faulted_event_requires_exact_fault_metadata_types() -> None:
    valid = InputEvent(
        False,
        Edge.NONE,
        faulted=True,
        fault="input stream stale",
        fault_code=FaultCode.INPUT_STREAM_STALE,
    )
    assert actionable_edge(valid) is Edge.NONE

    malformed = (
        InputEvent(False, Edge.NONE, faulted=True, fault="input stream stale", fault_code=7),  # type: ignore[arg-type]
        InputEvent(False, Edge.NONE, faulted=True, fault=7, fault_code=FaultCode.INPUT_STREAM_STALE),  # type: ignore[arg-type]
        InputEvent(False, Edge.NONE, faulted=True, fault=None, fault_code=FaultCode.INPUT_STREAM_STALE),
    )
    for event in malformed:
        with pytest.raises(HmiActionGateError):
            actionable_edge(event)


def test_action_gate_rejects_non_events() -> None:
    with pytest.raises(HmiActionGateError):
        actionable_edge({"stable_pressed": True})  # type: ignore[arg-type]
