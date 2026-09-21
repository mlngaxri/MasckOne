import pytest

import masck_one.hmi_event_wire as wire
from masck_one.hmi_event_wire import HmiEventWireError, input_event_from_wire, input_event_to_wire
from masck_one.hmi_runtime import Edge, InputEvent


def _healthy_payload(edge: str = "none", stable_pressed: bool = False) -> dict[str, object]:
    return {
        "stable_pressed": stable_pressed,
        "edge": edge,
        "faulted": False,
        "fault_code": None,
    }


def test_edge_wire_contract_is_complete_for_current_runtime() -> None:
    wire.assert_event_wire_contract_complete()
    assert set(wire._EDGE_TO_WIRE) == set(Edge)
    assert set(wire._EDGE_TO_WIRE.values()) == {"none", "pressed", "released"}


def test_encoder_fails_closed_if_edge_contract_loses_runtime_member(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(wire._EDGE_TO_WIRE, Edge.PRESSED)
    with pytest.raises(HmiEventWireError, match="event edge wire contract mismatch"):
        input_event_to_wire(InputEvent(True, Edge.PRESSED))


def test_decoder_fails_closed_if_edge_contract_loses_runtime_member(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(wire._EDGE_TO_WIRE, Edge.RELEASED)
    with pytest.raises(HmiEventWireError, match="event edge wire contract mismatch"):
        input_event_from_wire(_healthy_payload())


def test_contract_rejects_duplicate_edge_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(wire._EDGE_TO_WIRE, Edge.RELEASED, "pressed")
    with pytest.raises(HmiEventWireError, match="duplicates"):
        wire.assert_event_wire_contract_complete()


def test_contract_rejects_identifier_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(wire._EDGE_TO_WIRE, Edge.PRESSED, "PRESS")
    with pytest.raises(HmiEventWireError, match="invalid"):
        wire.assert_event_wire_contract_complete()


def test_contract_rejects_stale_inverse_table(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(wire._WIRE_TO_EDGE, "pressed", Edge.RELEASED)
    with pytest.raises(HmiEventWireError, match="inverse_matches=False"):
        wire.assert_event_wire_contract_complete()
