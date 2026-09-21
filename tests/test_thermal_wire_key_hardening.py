import pytest

from masck_one.thermal_control import ThermalCommand, ThermalControlError


@pytest.mark.parametrize(
    "payload",
    [
        {
            "mode": "off",
            "warm_enable": False,
            "cool_enable": False,
            "inhibited": False,
            "reason": None,
            7: "unexpected",
        },
        {
            "mode": "off",
            "warm_enable": False,
            "cool_enable": False,
            "inhibited": False,
            "reason": None,
            ("unexpected",): True,
        },
        {
            1: "off",
            "warm_enable": False,
            "cool_enable": False,
            "inhibited": False,
            "reason": None,
        },
    ],
)
def test_wire_decoder_rejects_non_string_keys_with_control_error(payload):
    with pytest.raises(ThermalControlError, match="keys must be exact strings"):
        ThermalCommand.from_wire(payload)


def test_wire_decoder_still_reports_string_field_mismatch_deterministically():
    payload = {
        "mode": "off",
        "warm_enable": False,
        "cool_enable": False,
        "inhibited": False,
        "reason": None,
        "unexpected": True,
    }
    with pytest.raises(
        ThermalControlError,
        match=r"fields mismatch: missing=\[\], extra=\['unexpected'\]",
    ):
        ThermalCommand.from_wire(payload)
