import math
import pytest

from masck_one.counter_rest_contract import CounterRestContractError, validate_counter_rest


def good():
    return {
        "ID_COUNTER_SUPPORT_SPAN_MM": 44.0,
        "ID_COUNTER_SUPPORT_DEPTH_MM": 15.0,
        "ID_COUNTER_FACE_SEAL_CLEARANCE_MM": 3.0,
        "ID_COUNTER_SERVICE_CLEARANCE_MM": 3.0,
        "ID_COUNTER_HMI_CLEARANCE_MM": 3.0,
        "ID_COUNTER_CHARGE_CLEARANCE_MM": 3.0,
        "ID_COUNTER_ROCKING_MARGIN_DEG": 10.0,
        "ID_COUNTER_SUPPORT_HEIGHT_MISMATCH_MM": 0.3,
    }


def test_nominal_counter_rest_geometry_passes():
    validate_counter_rest(good())


@pytest.mark.parametrize("key,value", [
    ("ID_COUNTER_SUPPORT_SPAN_MM", 37.9),
    ("ID_COUNTER_SUPPORT_DEPTH_MM", 11.9),
    ("ID_COUNTER_FACE_SEAL_CLEARANCE_MM", 1.9),
    ("ID_COUNTER_SERVICE_CLEARANCE_MM", 1.9),
    ("ID_COUNTER_HMI_CLEARANCE_MM", 1.9),
    ("ID_COUNTER_CHARGE_CLEARANCE_MM", 1.9),
    ("ID_COUNTER_ROCKING_MARGIN_DEG", 7.9),
    ("ID_COUNTER_SUPPORT_HEIGHT_MISMATCH_MM", 0.61),
])
def test_hostile_counter_rest_geometry_fails(key, value):
    v = good(); v[key] = value
    with pytest.raises(CounterRestContractError):
        validate_counter_rest(v)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -0.1])
def test_nonfinite_or_negative_evidence_fails(bad):
    v = good(); v["ID_COUNTER_SUPPORT_DEPTH_MM"] = bad
    with pytest.raises(CounterRestContractError):
        validate_counter_rest(v)


def test_missing_evidence_fails_closed():
    v = good(); del v["ID_COUNTER_CHARGE_CLEARANCE_MM"]
    with pytest.raises(CounterRestContractError):
        validate_counter_rest(v)
