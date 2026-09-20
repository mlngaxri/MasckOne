import pytest

from masck_one.thermal_control import (
    ThermalCommandInterlock,
    ThermalControlError,
    ThermalMode,
)


def test_idle_is_fail_safe_off():
    command = ThermalCommandInterlock().command(
        warm_requested=False, cool_requested=False, recovery_complete=False
    )
    assert command.mode is ThermalMode.OFF
    assert command.warm_enable is False
    assert command.cool_enable is False
    assert command.inhibited is False


def test_warm_command_never_enables_cool():
    command = ThermalCommandInterlock().command(
        warm_requested=True, cool_requested=False, recovery_complete=False
    )
    assert command.mode is ThermalMode.WARM
    assert command.warm_enable is True
    assert command.cool_enable is False


def test_cool_is_inhibited_until_recovery_completes():
    command = ThermalCommandInterlock().command(
        warm_requested=False, cool_requested=True, recovery_complete=False
    )
    assert command.mode is ThermalMode.OFF
    assert command.warm_enable is False
    assert command.cool_enable is False
    assert command.inhibited is True
    assert command.reason == "cool request requires completed recovery"


def test_cool_can_be_commanded_after_recovery():
    command = ThermalCommandInterlock().command(
        warm_requested=False, cool_requested=True, recovery_complete=True
    )
    assert command.mode is ThermalMode.COOL
    assert command.warm_enable is False
    assert command.cool_enable is True
    assert command.inhibited is False


def test_conflicting_requests_fail_closed_even_after_recovery():
    command = ThermalCommandInterlock().command(
        warm_requested=True, cool_requested=True, recovery_complete=True
    )
    assert command.mode is ThermalMode.OFF
    assert command.warm_enable is False
    assert command.cool_enable is False
    assert command.inhibited is True
    assert command.reason == "warm and cool requests are mutually exclusive"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("warm_requested", 1),
        ("cool_requested", 0),
        ("recovery_complete", None),
    ],
)
def test_non_boolean_control_inputs_are_rejected(field, value):
    kwargs = {
        "warm_requested": False,
        "cool_requested": False,
        "recovery_complete": False,
    }
    kwargs[field] = value
    with pytest.raises(ThermalControlError, match=f"{field} must be an exact bool"):
        ThermalCommandInterlock().command(**kwargs)
