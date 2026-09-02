import math
import pytest

from masck_one.cheek_field_contract import CheekFieldError, validate_cheek_field


def evidence(**overrides):
    values = {
        "ID_CHEEK_BRIDGE_WIDTH_L": 14.0,
        "ID_CHEEK_BRIDGE_WIDTH_R": 14.2,
        "ID_CHEEK_BLEND_RUN_L": 12.0,
        "ID_CHEEK_BLEND_RUN_R": 12.0,
        "ID_CHEEK_DEPTH_EXCURSION_L": 1.6,
        "ID_CHEEK_DEPTH_EXCURSION_R": 1.7,
    }
    values.update(overrides)
    return values


def test_nominal_cheek_field_passes():
    validate_cheek_field(evidence())


@pytest.mark.parametrize("key,value", [
    ("ID_CHEEK_BRIDGE_WIDTH_L", 11.9),
    ("ID_CHEEK_BLEND_RUN_R", 9.9),
    ("ID_CHEEK_DEPTH_EXCURSION_L", 2.51),
])
def test_rejects_local_midface_failures(key, value):
    with pytest.raises(CheekFieldError):
        validate_cheek_field(evidence(**{key: value}))


def test_rejects_bilateral_width_mismatch():
    with pytest.raises(CheekFieldError):
        validate_cheek_field(evidence(ID_CHEEK_BRIDGE_WIDTH_R=15.6))


def test_rejects_bilateral_depth_mismatch():
    with pytest.raises(CheekFieldError):
        validate_cheek_field(evidence(ID_CHEEK_DEPTH_EXCURSION_R=2.4))


def test_rejects_missing_evidence():
    values = evidence()
    del values["ID_CHEEK_BLEND_RUN_L"]
    with pytest.raises(CheekFieldError):
        validate_cheek_field(values)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -0.1])
def test_rejects_invalid_evidence(bad):
    with pytest.raises(CheekFieldError):
        validate_cheek_field(evidence(ID_CHEEK_BRIDGE_WIDTH_L=bad))
