from itertools import product

import pytest

from masck_one.hmi_event_wire import (
    HmiEventWireError,
    input_event_from_wire,
    input_event_to_wire,
)
from masck_one.hmi_fault_wire import fault_code_wire_id
from masck_one.hmi_runtime import Edge, FaultCode, InputEvent


@pytest.mark.parametrize(
    ("stable_pressed", "edge"),
    [
        (False, Edge.NONE),
        (True, Edge.NONE),
        (True, Edge.PRESSED),
        (False, Edge.RELEASED),
    ],
)
def test_every_healthy_runtime_event_shape_round_trips(stable_pressed: bool, edge: Edge):
    event = InputEvent(stable_pressed=stable_pressed, edge=edge)

    payload = input_event_to_wire(event)

    assert input_event_from_wire(payload) == event


@pytest.mark.parametrize("fault_code", list(FaultCode))
def test_every_fault_code_round_trips_in_the_only_valid_faulted_event_shape(fault_code: FaultCode):
    event = InputEvent(
        stable_pressed=False,
        edge=Edge.NONE,
        faulted=True,
        fault="local diagnostic is deliberately not transported",
        fault_code=fault_code,
    )

    payload = input_event_to_wire(event)
    decoded = input_event_from_wire(payload)

    assert payload == {
        "stable_pressed": False,
        "edge": "none",
        "faulted": True,
        "fault_code": fault_code_wire_id(fault_code),
    }
    assert decoded == InputEvent(
        stable_pressed=False,
        edge=Edge.NONE,
        faulted=True,
        fault=None,
        fault_code=fault_code,
    )


def test_all_other_representable_semantic_event_tuples_fail_closed():
    fault_options = [None, *FaultCode]
    valid = {
        (False, Edge.NONE, False, None),
        (True, Edge.NONE, False, None),
        (True, Edge.PRESSED, False, None),
        (False, Edge.RELEASED, False, None),
        *((False, Edge.NONE, True, code) for code in FaultCode),
    }

    for stable_pressed, edge, faulted, fault_code in product(
        (False, True), Edge, (False, True), fault_options
    ):
        key = (stable_pressed, edge, faulted, fault_code)
        event = InputEvent(
            stable_pressed=stable_pressed,
            edge=edge,
            faulted=faulted,
            fault=None,
            fault_code=fault_code,
        )
        if key in valid:
            input_event_to_wire(event)
            continue
        with pytest.raises(HmiEventWireError):
            input_event_to_wire(event)


def test_decoder_accepts_exactly_the_same_semantic_state_space_as_encoder():
    edge_ids = ("none", "pressed", "released")
    fault_ids = [None, *(fault_code_wire_id(code) for code in FaultCode)]
    accepted = 0

    for stable_pressed, edge_id, faulted, fault_id in product(
        (False, True), edge_ids, (False, True), fault_ids
    ):
        payload = {
            "stable_pressed": stable_pressed,
            "edge": edge_id,
            "faulted": faulted,
            "fault_code": fault_id,
        }
        try:
            event = input_event_from_wire(payload)
        except HmiEventWireError:
            continue
        accepted += 1
        assert input_event_from_wire(input_event_to_wire(event)) == event

    assert accepted == 4 + len(FaultCode)
