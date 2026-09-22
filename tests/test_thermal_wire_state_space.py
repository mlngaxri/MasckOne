import itertools

import pytest

from masck_one.thermal_control import (
    ThermalCommand,
    ThermalControlError,
    ThermalInhibitReason,
    ThermalMode,
)


VALID_WIRE_STATES = {
    ("off", False, False, False, None),
    ("warm", True, False, False, None),
    ("cool", False, True, False, None),
    ("off", False, False, True, "conflicting_requests"),
    ("off", False, False, True, "recovery_incomplete"),
}


def _payload(state):
    mode, warm_enable, cool_enable, inhibited, reason = state
    return {
        "mode": mode,
        "warm_enable": warm_enable,
        "cool_enable": cool_enable,
        "inhibited": inhibited,
        "reason": reason,
    }


def test_thermal_wire_decoder_accepts_exactly_the_closed_semantic_state_space():
    """Synthetic exhaustive regression over every currently representable wire tuple."""
    modes = tuple(mode.value for mode in ThermalMode)
    reasons = (None, *(reason.value for reason in ThermalInhibitReason))

    accepted = set()
    rejected = set()
    for state in itertools.product(modes, (False, True), (False, True), (False, True), reasons):
        try:
            command = ThermalCommand.from_wire(_payload(state))
        except ThermalControlError:
            rejected.add(state)
        else:
            accepted.add(state)
            assert command.to_wire() == _payload(state)

    assert accepted == VALID_WIRE_STATES
    assert rejected.isdisjoint(VALID_WIRE_STATES)
    assert len(accepted) + len(rejected) == len(modes) * 2 * 2 * 2 * len(reasons)


@pytest.mark.parametrize("state", sorted(VALID_WIRE_STATES, key=repr))
def test_every_valid_thermal_wire_state_round_trips_without_semantic_drift(state):
    decoded = ThermalCommand.from_wire(_payload(state))
    assert decoded.to_wire() == _payload(state)
