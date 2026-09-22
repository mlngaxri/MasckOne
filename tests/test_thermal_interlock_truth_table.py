import itertools

import pytest

from masck_one.thermal_control import (
    ThermalCommand,
    ThermalCommandInterlock,
    ThermalControlError,
    ThermalInhibitReason,
    ThermalMode,
)


EXPECTED_DECISIONS = {
    (False, False, False): ThermalCommand(ThermalMode.OFF, False, False),
    (False, False, True): ThermalCommand(ThermalMode.OFF, False, False),
    (True, False, False): ThermalCommand(ThermalMode.WARM, True, False),
    (True, False, True): ThermalCommand(ThermalMode.WARM, True, False),
    (False, True, False): ThermalCommand(
        ThermalMode.OFF,
        False,
        False,
        inhibited=True,
        reason=ThermalInhibitReason.RECOVERY_INCOMPLETE,
    ),
    (False, True, True): ThermalCommand(ThermalMode.COOL, False, True),
    (True, True, False): ThermalCommand(
        ThermalMode.OFF,
        False,
        False,
        inhibited=True,
        reason=ThermalInhibitReason.CONFLICTING_REQUESTS,
    ),
    (True, True, True): ThermalCommand(
        ThermalMode.OFF,
        False,
        False,
        inhibited=True,
        reason=ThermalInhibitReason.CONFLICTING_REQUESTS,
    ),
}


def test_thermal_interlock_exhaustively_matches_closed_decision_table():
    """Synthetic exhaustive regression over every exact-bool request/recovery tuple."""
    interlock = ThermalCommandInterlock()
    observed = {}

    for inputs in itertools.product((False, True), repeat=3):
        warm_requested, cool_requested, recovery_complete = inputs
        command = interlock.command(
            warm_requested=warm_requested,
            cool_requested=cool_requested,
            recovery_complete=recovery_complete,
        )
        observed[inputs] = command
        assert command.to_wire() == EXPECTED_DECISIONS[inputs].to_wire()

    assert observed == EXPECTED_DECISIONS


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("warm_requested", 0),
        ("warm_requested", 1),
        ("warm_requested", None),
        ("cool_requested", 0),
        ("cool_requested", 1),
        ("cool_requested", None),
        ("recovery_complete", 0),
        ("recovery_complete", 1),
        ("recovery_complete", None),
    ],
)
def test_thermal_interlock_rejects_non_boolean_control_inputs(field, bad_value):
    inputs = {
        "warm_requested": False,
        "cool_requested": False,
        "recovery_complete": False,
    }
    inputs[field] = bad_value

    with pytest.raises(ThermalControlError, match=rf"^{field} must be an exact bool$"):
        ThermalCommandInterlock().command(**inputs)
