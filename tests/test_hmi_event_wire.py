import pytest

from masck_one.hmi_event_wire import HmiEventWireError, input_event_from_wire, input_event_to_wire
from masck_one.hmi_runtime import DebouncedInput, Edge, FaultCode, InputEvent


def test_pressed_event_has_stable_wire_shape() -> None:
    runtime = DebouncedInput(debounce_s=0.03, stale_after_s=0.25)
    runtime.sample(pressed=True, now_s=1.0)
    event = runtime.sample(pressed=True, now_s=1.03)
    assert input_event_to_wire(event) == {
        "stable_pressed": True,
        "edge": "pressed",
        "faulted": False,
        "fault_code": None,
    }


def test_fault_event_round_trips_without_human_reason_as_wire_authority() -> None:
    event = InputEvent(False, Edge.NONE, True, "diagnostic text", FaultCode.INPUT_STREAM_STALE)
    payload = input_event_to_wire(event)
    assert payload == {
        "stable_pressed": False,
        "edge": "none",
        "faulted": True,
        "fault_code": "input_stream_stale",
    }
    decoded = input_event_from_wire(payload)
    assert decoded == InputEvent(False, Edge.NONE, True, None, FaultCode.INPUT_STREAM_STALE)


@pytest.mark.parametrize(
    "payload",
    [
        {"stable_pressed": 1, "edge": "pressed", "faulted": False, "fault_code": None},
        {"stable_pressed": True, "edge": "PRESS", "faulted": False, "fault_code": None},
        {"stable_pressed": True, "edge": "released", "faulted": False, "fault_code": None},
        {"stable_pressed": False, "edge": "pressed", "faulted": False, "fault_code": None},
        {"stable_pressed": False, "edge": "none", "faulted": True, "fault_code": None},
        {"stable_pressed": False, "edge": "none", "faulted": False, "fault_code": "input_stream_stale"},
        {"stable_pressed": False, "edge": "none", "faulted": True, "fault_code": "unknown"},
    ],
)
def test_decoder_rejects_malformed_or_impossible_states(payload: dict[str, object]) -> None:
    with pytest.raises(HmiEventWireError):
        input_event_from_wire(payload)


def test_decoder_rejects_non_string_keys_and_field_drift() -> None:
    with pytest.raises(HmiEventWireError, match="keys must be exact strings"):
        input_event_from_wire({0: False, "edge": "none", "faulted": False, "fault_code": None})
    with pytest.raises(HmiEventWireError, match="fields mismatch"):
        input_event_from_wire({"stable_pressed": False, "edge": "none", "faulted": False})
    with pytest.raises(HmiEventWireError, match="fields mismatch"):
        input_event_from_wire(
            {"stable_pressed": False, "edge": "none", "faulted": False, "fault_code": None, "extra": 0}
        )


def test_encoder_rejects_semantically_impossible_runtime_event() -> None:
    with pytest.raises(HmiEventWireError, match="pressed edge"):
        input_event_to_wire(InputEvent(False, Edge.PRESSED))


def test_encoder_rejects_invalid_fault_code_through_event_boundary() -> None:
    event = InputEvent(False, Edge.NONE, True, "diagnostic text", "input_stream_stale")  # type: ignore[arg-type]
    with pytest.raises(HmiEventWireError, match="fault_code must be an exact FaultCode"):
        input_event_to_wire(event)
