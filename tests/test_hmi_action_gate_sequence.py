import pytest

from masck_one.hmi_action_gate import HmiActionGateError, actionable_edge
from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode, InputEvent


def test_long_hold_emits_exactly_one_action_until_release_and_repress() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    runtime.arm(now_s=1.0)
    runtime.sample(pressed=False, now_s=1.01)
    runtime.sample(pressed=True, now_s=1.02)

    edges = [actionable_edge(runtime.sample(pressed=True, now_s=1.05))]
    for now_s in (1.06, 1.10, 1.14, 1.18, 1.22):
        edges.append(actionable_edge(runtime.sample(pressed=True, now_s=now_s)))

    assert edges.count(Edge.PRESSED) == 1
    assert all(edge in (Edge.PRESSED, Edge.NONE) for edge in edges)

    assert actionable_edge(runtime.sample(pressed=False, now_s=1.23)) is Edge.NONE
    assert actionable_edge(runtime.sample(pressed=False, now_s=1.26)) is Edge.RELEASED
    assert actionable_edge(runtime.sample(pressed=True, now_s=1.27)) is Edge.NONE
    assert actionable_edge(runtime.sample(pressed=True, now_s=1.30)) is Edge.PRESSED


def test_stale_fault_mid_hold_cannot_leak_release_or_press_action() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    runtime.arm(now_s=2.0)
    runtime.sample(pressed=False, now_s=2.01)
    runtime.sample(pressed=True, now_s=2.02)
    assert actionable_edge(runtime.sample(pressed=True, now_s=2.05)) is Edge.PRESSED

    fault = runtime.watchdog(now_s=2.301)
    assert fault.fault_code is FaultCode.INPUT_STREAM_STALE
    assert actionable_edge(fault) is Edge.NONE

    reset = runtime.reset(now_s=2.31)
    assert actionable_edge(reset) is Edge.NONE
    assert actionable_edge(runtime.sample(pressed=True, now_s=2.32)) is Edge.NONE
    assert actionable_edge(runtime.sample(pressed=False, now_s=2.33)) is Edge.NONE
    assert actionable_edge(runtime.sample(pressed=False, now_s=2.36)) is Edge.NONE
    assert actionable_edge(runtime.sample(pressed=True, now_s=2.37)) is Edge.NONE
    assert actionable_edge(runtime.sample(pressed=True, now_s=2.40)) is Edge.PRESSED


def test_action_gate_rejects_enum_lookalikes_and_bool_subclasses() -> None:
    class EdgeLookalike:
        pass

    with pytest.raises(HmiActionGateError):
        actionable_edge(InputEvent(True, EdgeLookalike()))  # type: ignore[arg-type]

    with pytest.raises(HmiActionGateError):
        actionable_edge(InputEvent(1, Edge.PRESSED))  # type: ignore[arg-type]


def test_fault_metadata_cannot_survive_on_healthy_recovery_event() -> None:
    malformed = InputEvent(
        False,
        Edge.NONE,
        faulted=False,
        fault="stale historical diagnostic",
        fault_code=FaultCode.INPUT_STREAM_STALE,
    )
    with pytest.raises(HmiActionGateError):
        actionable_edge(malformed)
