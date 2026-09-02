import math
import pytest

from masck_one.facial_interface_contract import FacialInterfaceContractError, validate_facial_interface


def good():
    return {
        "HF_CONTACT_EDGE_THICKNESS_L": 1.4,
        "HF_CONTACT_EDGE_THICKNESS_R": 1.4,
        "HF_PRESSURE_TRANSITION_RUN_L": 10.0,
        "HF_PRESSURE_TRANSITION_RUN_R": 10.0,
        "HF_PRESSURE_TRANSITION_RISE_L": 1.5,
        "HF_PRESSURE_TRANSITION_RISE_R": 1.5,
        "HF_RIGID_EDGE_SETBACK_L": 4.0,
        "HF_RIGID_EDGE_SETBACK_R": 4.0,
        "HF_EDGE_RETURN_RADIUS_L": 1.4,
        "HF_EDGE_RETURN_RADIUS_R": 1.4,
        "HF_EDGE_TERMINAL_LAND_L": 2.0,
        "HF_EDGE_TERMINAL_LAND_R": 2.0,
    }


def test_nominal_interface_passes():
    validate_facial_interface(good())


@pytest.mark.parametrize("key,value", [
    ("HF_CONTACT_EDGE_THICKNESS_L", 2.1),
    ("HF_PRESSURE_TRANSITION_RUN_R", 7.9),
    ("HF_PRESSURE_TRANSITION_RISE_L", 2.6),
    ("HF_RIGID_EDGE_SETBACK_R", 2.9),
    ("HF_EDGE_RETURN_RADIUS_L", 0.9),
    ("HF_EDGE_TERMINAL_LAND_R", 1.4),
])
def test_hostile_local_geometry_fails(key, value):
    v = good(); v[key] = value
    with pytest.raises(FacialInterfaceContractError):
        validate_facial_interface(v)


def test_transition_asymmetry_fails():
    v = good(); v["HF_PRESSURE_TRANSITION_RUN_R"] = 13.0
    with pytest.raises(FacialInterfaceContractError):
        validate_facial_interface(v)


def test_edge_thickness_asymmetry_fails():
    v = good(); v["HF_CONTACT_EDGE_THICKNESS_R"] = 2.0
    with pytest.raises(FacialInterfaceContractError):
        validate_facial_interface(v)


def test_edge_return_asymmetry_fails():
    v = good(); v["HF_EDGE_RETURN_RADIUS_R"] = 2.0
    with pytest.raises(FacialInterfaceContractError):
        validate_facial_interface(v)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -0.1])
def test_nonfinite_or_negative_evidence_fails(bad):
    v = good(); v["HF_RIGID_EDGE_SETBACK_L"] = bad
    with pytest.raises(FacialInterfaceContractError):
        validate_facial_interface(v)


def test_missing_evidence_fails_closed():
    v = good(); del v["HF_EDGE_TERMINAL_LAND_R"]
    with pytest.raises(FacialInterfaceContractError):
        validate_facial_interface(v)
