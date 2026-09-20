import pytest

from masck_one.thermal_control import (
    ThermalCommand,
    ThermalCommandInterlock,
    ThermalControlError,
    ThermalInhibitReason,
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
    assert command.reason is None


def test_warm_command_never_enables_cool():
    command = ThermalCommandInterlock().command(
        warm_requested=True, cool_requested=False, recovery_complete=False
    )
    assert command.mode is ThermalMode.WARM
    assert command.warm_enable is True
    assert command.cool_enable is False
    assert command.reason is None


def test_cool_is_inhibited_until_recovery_completes():
    command = ThermalCommandInterlock().command(
        warm_requested=False, cool_requested=True, recovery_complete=False
    )
    assert command.mode is ThermalMode.OFF
    assert command.warm_enable is False
    assert command.cool_enable is False
    assert command.inhibited is True
    assert command.reason is ThermalInhibitReason.RECOVERY_INCOMPLETE


def test_cool_can_be_commanded_after_recovery():
    command = ThermalCommandInterlock().command(
        warm_requested=False, cool_requested=True, recovery_complete=True
    )
    assert command.mode is ThermalMode.COOL
    assert command.warm_enable is False
    assert command.cool_enable is True
    assert command.inhibited is False
    assert command.reason is None


def test_conflicting_requests_fail_closed_even_after_recovery():
    command = ThermalCommandInterlock().command(
        warm_requested=True, cool_requested=True, recovery_complete=True
    )
    assert command.mode is ThermalMode.OFF
    assert command.warm_enable is False
    assert command.cool_enable is False
    assert command.inhibited is True
    assert command.reason is ThermalInhibitReason.CONFLICTING_REQUESTS


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


@pytest.mark.parametrize(
    "command",
    [
        (ThermalMode.OFF, True, False, False, None),
        (ThermalMode.OFF, False, True, False, None),
        (ThermalMode.WARM, False, False, False, None),
        (ThermalMode.WARM, True, True, False, None),
        (ThermalMode.COOL, False, False, False, None),
        (ThermalMode.COOL, True, True, False, None),
    ],
)
def test_impossible_mode_output_combinations_are_rejected(command):
    with pytest.raises(ThermalControlError, match="impossible command"):
        ThermalCommand(*command)


def test_inhibited_command_must_be_off_and_explain_why():
    with pytest.raises(ThermalControlError, match="inhibited command must be OFF"):
        ThermalCommand(
            ThermalMode.WARM,
            True,
            False,
            inhibited=True,
            reason=ThermalInhibitReason.CONFLICTING_REQUESTS,
        )
    with pytest.raises(ThermalControlError, match="requires a reason"):
        ThermalCommand(ThermalMode.OFF, False, False, inhibited=True)


def test_non_inhibited_command_cannot_carry_fault_reason():
    with pytest.raises(ThermalControlError, match="cannot carry a reason"):
        ThermalCommand(
            ThermalMode.OFF,
            False,
            False,
            reason=ThermalInhibitReason.RECOVERY_INCOMPLETE,
        )


def test_free_form_inhibit_reasons_are_rejected():
    with pytest.raises(ThermalControlError, match="ThermalInhibitReason"):
        ThermalCommand(
            ThermalMode.OFF,
            False,
            False,
            inhibited=True,
            reason="recovery incomplete",
        )


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"mode": "WARM", "warm_enable": True, "cool_enable": False}, "mode must be"),
        ({"mode": ThermalMode.OFF, "warm_enable": 0, "cool_enable": False}, "warm_enable"),
        ({"mode": ThermalMode.OFF, "warm_enable": False, "cool_enable": False, "inhibited": 1}, "inhibited"),
        ({"mode": ThermalMode.OFF, "warm_enable": False, "cool_enable": False, "reason": 7}, "reason must"),
    ],
)
def test_malformed_output_fields_are_rejected(kwargs, message):
    with pytest.raises(ThermalControlError, match=message):
        ThermalCommand(**kwargs)
