import math
import pytest

from masck_one.rear_massing_contract import RearMassingContractError, validate_rear_massing


def good():
    return {
        "ID_REAR_DEPTH_L": 26.0,
        "ID_REAR_DEPTH_R": 26.4,
        "ID_REAR_SERVICE_BULGE_L": 2.0,
        "ID_REAR_SERVICE_BULGE_R": 2.2,
        "ID_REAR_SERVICE_BLEND_RUN_L": 16.0,
        "ID_REAR_SERVICE_BLEND_RUN_R": 15.5,
    }


def test_accepts_restrained_rear_massing():
    validate_rear_massing(good())


@pytest.mark.parametrize(
    "key,value",
    [
        ("ID_REAR_DEPTH_L", 31.0),
        ("ID_REAR_SERVICE_BULGE_R", 3.1),
        ("ID_REAR_SERVICE_BLEND_RUN_L", 13.9),
    ],
)
def test_rejects_packaging_driven_rear_forms(key, value):
    values = good(); values[key] = value
    with pytest.raises(RearMassingContractError):
        validate_rear_massing(values)


def test_rejects_bilateral_depth_imbalance():
    values = good(); values["ID_REAR_DEPTH_R"] = 27.2
    with pytest.raises(RearMassingContractError):
        validate_rear_massing(values)


def test_rejects_missing_and_nonfinite_evidence():
    values = good(); values.pop("ID_REAR_DEPTH_L")
    with pytest.raises(RearMassingContractError):
        validate_rear_massing(values)
    values = good(); values["ID_REAR_DEPTH_L"] = math.nan
    with pytest.raises(RearMassingContractError):
        validate_rear_massing(values)
