from __future__ import annotations

"""Stable fail-closed serialization for conditioned HMI input events."""

from types import MappingProxyType
from typing import Any, Mapping

from masck_one.hmi_fault_wire import (
    HmiFaultWireError,
    fault_code_from_wire_id,
    fault_code_wire_id,
)
from masck_one.hmi_runtime import Edge, FaultCode, InputEvent


class HmiEventWireError(ValueError):
    """Raised when an HMI event wire payload violates the contract."""


_CANONICAL_EDGE_TO_WIRE: Mapping[Edge, str] = MappingProxyType({
    Edge.NONE: "none",
    Edge.PRESSED: "pressed",
    Edge.RELEASED: "released",
})
_EDGE_TO_WIRE: Mapping[Edge, str] = _CANONICAL_EDGE_TO_WIRE
_WIRE_TO_EDGE: Mapping[str, Edge] = MappingProxyType(
    {identifier: edge for edge, identifier in _EDGE_TO_WIRE.items()}
)
_FIELDS = frozenset({"stable_pressed", "edge", "faulted", "fault_code"})


def assert_event_wire_contract_complete() -> None:
    """Fail closed if runtime edge coverage or canonical wire semantics drift."""
    valid_keys = {key for key in _EDGE_TO_WIRE if type(key) is Edge}
    invalid_key_reprs = sorted(repr(key) for key in _EDGE_TO_WIRE if type(key) is not Edge)
    missing = set(Edge) - valid_keys
    identifiers = tuple(_EDGE_TO_WIRE.values())
    duplicate_reprs = sorted(
        {repr(identifier) for identifier in identifiers if identifiers.count(identifier) > 1}
    )
    invalid_reprs = sorted(
        repr(identifier)
        for identifier in identifiers
        if type(identifier) is not str or identifier not in {"none", "pressed", "released"}
    )
    canonical_matches = _EDGE_TO_WIRE == _CANONICAL_EDGE_TO_WIRE
    inverse_matches = _WIRE_TO_EDGE == {
        identifier: edge
        for edge, identifier in _EDGE_TO_WIRE.items()
        if type(edge) is Edge and type(identifier) is str
    }
    if (
        missing
        or invalid_key_reprs
        or duplicate_reprs
        or invalid_reprs
        or not canonical_matches
        or not inverse_matches
    ):
        missing_names = sorted(edge.name for edge in missing)
        raise HmiEventWireError(
            "event edge wire contract mismatch: "
            f"missing={missing_names}, invalid_keys={invalid_key_reprs}, "
            f"duplicates={duplicate_reprs}, invalid={invalid_reprs}, "
            f"canonical_matches={canonical_matches}, inverse_matches={inverse_matches}"
        )


def input_event_to_wire(event: InputEvent) -> dict[str, Any]:
    """Serialize one runtime event without exposing enum implementation values."""
    if type(event) is not InputEvent:
        raise HmiEventWireError("event must be an exact InputEvent")
    _validate_event(event)
    assert_event_wire_contract_complete()
    return {
        "stable_pressed": event.stable_pressed,
        "edge": _EDGE_TO_WIRE[event.edge],
        "faulted": event.faulted,
        "fault_code": fault_code_wire_id(event.fault_code) if event.fault_code is not None else None,
    }


def input_event_from_wire(payload: object) -> InputEvent:
    """Decode one exact event payload, rejecting malformed or impossible states.

    The firmware boundary accepts the plain dictionary shape produced by a decoded
    object payload, not arbitrary Mapping implementations. This keeps validation and
    field reads deterministic and prevents caller-defined iteration or lookup behavior
    from changing the object between contract checks and decoding.
    """
    if type(payload) is not dict:
        raise HmiEventWireError("payload must be an exact dict")
    if any(type(key) is not str for key in payload):
        raise HmiEventWireError("payload keys must be exact strings")
    keys = frozenset(payload)
    if keys != _FIELDS:
        missing = sorted(_FIELDS - keys)
        extra = sorted(keys - _FIELDS)
        raise HmiEventWireError(f"event wire fields mismatch: missing={missing}, extra={extra}")

    assert_event_wire_contract_complete()
    stable_pressed = payload["stable_pressed"]
    faulted = payload["faulted"]
    edge_id = payload["edge"]
    fault_id = payload["fault_code"]
    if type(stable_pressed) is not bool or type(faulted) is not bool:
        raise HmiEventWireError("stable_pressed and faulted must be exact bools")
    if type(edge_id) is not str or edge_id not in _WIRE_TO_EDGE:
        raise HmiEventWireError(f"unknown HMI edge wire identifier: {edge_id!r}")
    edge = _WIRE_TO_EDGE[edge_id]

    fault_code = None
    if fault_id is not None:
        try:
            fault_code = fault_code_from_wire_id(fault_id)  # type: ignore[arg-type]
        except HmiFaultWireError as exc:
            raise HmiEventWireError(str(exc)) from exc

    event = InputEvent(
        stable_pressed=stable_pressed,
        edge=edge,
        faulted=faulted,
        fault=None,
        fault_code=fault_code,
    )
    _validate_event(event)
    return event


def _validate_event(event: InputEvent) -> None:
    if type(event.stable_pressed) is not bool or type(event.faulted) is not bool:
        raise HmiEventWireError("event booleans must be exact bools")
    if type(event.edge) is not Edge:
        raise HmiEventWireError("edge must be an exact Edge")
    if event.fault is not None and type(event.fault) is not str:
        raise HmiEventWireError("fault diagnostic must be an exact string or None")
    if event.fault_code is not None and type(event.fault_code) is not FaultCode:
        raise HmiEventWireError("fault_code must be an exact FaultCode or None")
    if event.faulted:
        if event.stable_pressed or event.edge is not Edge.NONE or event.fault_code is None:
            raise HmiEventWireError("faulted event must be released, edgeless, and carry a fault code")
    else:
        if event.fault is not None:
            raise HmiEventWireError("healthy event cannot carry a fault diagnostic")
        if event.fault_code is not None:
            raise HmiEventWireError("healthy event cannot carry a fault code")
    if event.edge is Edge.PRESSED and not event.stable_pressed:
        raise HmiEventWireError("pressed edge requires stable_pressed=true")
    if event.edge is Edge.RELEASED and event.stable_pressed:
        raise HmiEventWireError("released edge requires stable_pressed=false")
