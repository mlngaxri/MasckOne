import math

import pytest

from masck_one.upper_side_transition_contract import (
    UpperSideTransitionContractError,
    validate_upper_side_transition,
)


def nominal():
    return {
        "ID_UPPER_SIDE_TRANSITION_RUN_L": 18.0,
        "ID_UPPER_SIDE_TRANSITION_RUN_R": 18.0,
        "ID_UPPER_SIDE_SHOULDER_PROJECTION_L": 1.5,
        "ID_UPPER_SIDE_SHOULDER_PROJECTION_R": 1.5,
        "ID_UPPER_SIDE_MAX_TANGENT_BREAK_DEG_L": 5.0,
        "ID_UPPER_SIDE_MAX_TANGENT_BREAK_DEG_R": 5.0,
    }


def test_nominal_upper_side_transition_passes():
    validate_upper_side_transition(nominal())


@pytest.mark.parametrize(
    "key,value",
    [
        ("ID_UPPER_SIDE_TRANSITION_RUN_L", 15.9),
        ("ID_UPPER_SIDE_TRANSITION_RUN_R", 15.9),
        ("ID_UPPER_SIDE_SHOULDER_PROJECTION_L", 2.6),
        ("ID_UPPER_SIDE_SHOULDER_PROJECTION_R", 2.6),
        ("ID_UPPER_SIDE_MAX_TANGENT_BREAK_DEG_L", 7.1),
        ("ID_UPPER_SIDE_MAX_TANGENT_BREAK_DEG_R", 7.1),
    ],
)
def test_hostile_local_geometry_fails(key, value):
    values = nominal()
    values[key] = value
    with pytest.raises(UpperSideTransitionContractError):
        validate_upper_side_transition(values)


def test_bilateral_projection_mismatch_fails():
    values = nominal()
    values["ID_UPPER_SIDE_SHOULDER_PROJECTION_R"] = 2.3
    with pytest.raises(UpperSideTransitionContractError):
        validate_upper_side_transition(values)


def test_missing_measurement_fails_closed():
    values = nominal()
    del values["ID_UPPER_SIDE_TRANSITION_RUN_L"]
    with pytest.raises(UpperSideTransitionContractError):
        validate_upper_side_transition(values)


@pytest.mark.parametrize("value", [-0.1, math.inf, math.nan])
def test_invalid_measurement_fails(value):
    values = nominal()
    values["ID_UPPER_SIDE_TRANSITION_RUN_L"] = value
    with pytest.raises(UpperSideTransitionContractError):
        validate_upper_side_transition(values)
