from __future__ import annotations

"""Fail-closed conversion from conditioned HMI events to actionable edges.

This module deliberately does not assign product functions to controls. It provides the
small firmware-facing gate between the conditioned input stream and any later command
binding, so held state, fault state, or malformed synthetic events cannot be mistaken
for a new user action.
"""

from masck_one.hmi_runtime import Edge, InputEvent


class HmiActionGateError(ValueError):
    """Raised when an impossible conditioned-event state reaches the action gate."""


def actionable_edge(event: InputEvent) -> Edge:
    """Return the one edge firmware may act on, failing closed on invalid state.

    ``stable_pressed`` is state, not an action request. A healthy held input therefore
    returns ``Edge.NONE`` unless the runtime emitted a fresh edge. Faulted events are
    always non-actionable. Structurally impossible events raise rather than being
    silently reinterpreted.
    """
    if type(event) is not InputEvent:
        raise HmiActionGateError("event must be an exact InputEvent")
    if type(event.stable_pressed) is not bool or type(event.faulted) is not bool:
        raise HmiActionGateError("event booleans must be exact bools")
    if type(event.edge) is not Edge:
        raise HmiActionGateError("edge must be an exact Edge")

    if event.faulted:
        if event.stable_pressed or event.edge is not Edge.NONE or event.fault_code is None:
            raise HmiActionGateError("faulted event must be released, edgeless, and carry a fault code")
        return Edge.NONE

    if event.fault is not None or event.fault_code is not None:
        raise HmiActionGateError("healthy event cannot carry fault metadata")
    if event.edge is Edge.PRESSED and not event.stable_pressed:
        raise HmiActionGateError("pressed edge requires stable_pressed=true")
    if event.edge is Edge.RELEASED and event.stable_pressed:
        raise HmiActionGateError("released edge requires stable_pressed=false")
    return event.edge
