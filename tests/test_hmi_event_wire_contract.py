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


def test_edge_wire_tables_reject_in_place_mutation() -> None:
    with pytest.raises(TypeError):
        wire._EDGE_TO_WIRE[Edge.PRESSED] = "released"  # type: ignore[index]
    with pytest.raises(TypeError):
        wire._WIRE_TO_EDGE["pressed"] = Edge.RELEASED  # type: ignore[index]
    wire.assert_event_wire_contract_complete()


def test_edge_wire_tables_reject_in_place_deletion() -> None:
    with pytest.raises(TypeError):
        del wire._EDGE_TO_WIRE[Edge.PRESSED]  # type: ignore[attr-defined]
    with pytest.raises(TypeError):
        del wire._WIRE_TO_EDGE["pressed"]  # type: ignore[attr-defined]
    wire.assert_event_wire_contract_complete()


def test_encoder_fails_closed_if_edge_contract_loses_runtime_member(monkeypatch: pytest.MonkeyPatch) -> None:
    corrupted = dict(wire._EDGE_TO_WIRE)
    del corrupted[Edge.PRESSED]
    monkeypatch.setattr(wire, "_EDGE_TO_WIRE", corrupted)
    with pytest.raises(HmiEventWireError, match="event edge wire contract mismatch"):
        input_event_to_wire(InputEvent(True, Edge.PRESSED))


def test_decoder_fails_closed_if_edge_contract_loses_runtime_member(monkeypatch: pytest.MonkeyPatch) -> None:
    corrupted = dict(wire._EDGE_TO_WIRE)
    del corrupted[Edge.RELEASED]
    monkeypatch.setattr(wire, "_EDGE_TO_WIRE", corrupted)
    with pytest.raises(HmiEventWireError, match="event edge wire contract mismatch"):
        input_event_from_wire(_healthy_payload())


def test_contract_rejects_duplicate_edge_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    corrupted = dict(wire._EDGE_TO_WIRE)
    corrupted[Edge.RELEASED] = "pressed"
    monkeypatch.setattr(wire, "_EDGE_TO_WIRE", corrupted)
    with pytest.raises(HmiEventWireError, match="duplicates"):
        wire.assert_event_wire_contract_complete()


def test_contract_rejects_identifier_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    corrupted = dict(wire._EDGE_TO_WIRE)
    corrupted[Edge.PRESSED] = "PRESS"
    monkeypatch.setattr(wire, "_EDGE_TO_WIRE", corrupted)
    with pytest.raises(HmiEventWireError, match="invalid"):
        wire.assert_event_wire_contract_complete()


def test_contract_rejects_stale_inverse_table(monkeypatch: pytest.MonkeyPatch) -> None:
    corrupted = dict(wire._WIRE_TO_EDGE)
    corrupted["pressed"] = Edge.RELEASED
    monkeypatch.setattr(wire, "_WIRE_TO_EDGE", corrupted)
    with pytest.raises(HmiEventWireError, match="inverse_matches=False"):
        wire.assert_event_wire_contract_complete()
