import math
import pytest

from masck_one.wet_service_hf_contract import WetServiceHFContractError, validate_wet_service_hf_evidence


def valid():
    return {
        "HF_SERVICE_GRIP_WIDTH_L_MM": 14.0,
        "HF_SERVICE_GRIP_WIDTH_R_MM": 14.0,
        "HF_SERVICE_GRIP_DEPTH_MM": 1.8,
        "HF_SERVICE_GRIP_EDGE_RADIUS_MM": 1.0,
        "HF_SERVICE_RELEASE_CLEARANCE_MM": 2.0,
        "HF_SERVICE_TRAVEL_MM": 5.0,
        "HF_SERVICE_ENDSTOP_OVERTRAVEL_MM": 1.0,
    }


def test_accepts_wet_service_candidate():
    validate_wet_service_hf_evidence(valid())


@pytest.mark.parametrize("key,value", [
    ("HF_SERVICE_GRIP_WIDTH_L_MM", 11.9),
    ("HF_SERVICE_GRIP_DEPTH_MM", 1.19),
    ("HF_SERVICE_GRIP_EDGE_RADIUS_MM", 0.79),
    ("HF_SERVICE_RELEASE_CLEARANCE_MM", 1.49),
    ("HF_SERVICE_TRAVEL_MM", 2.99),
    ("HF_SERVICE_TRAVEL_MM", 8.01),
    ("HF_SERVICE_ENDSTOP_OVERTRAVEL_MM", 0.79),
])
def test_rejects_hostile_service_geometry(key, value):
    evidence = valid()
    evidence[key] = value
    with pytest.raises(WetServiceHFContractError):
        validate_wet_service_hf_evidence(evidence)


def test_rejects_bilateral_grip_mismatch():
    evidence = valid()
    evidence["HF_SERVICE_GRIP_WIDTH_R_MM"] = 12.9
    with pytest.raises(WetServiceHFContractError):
        validate_wet_service_hf_evidence(evidence)


def test_fails_closed_on_missing_evidence():
    evidence = valid()
    del evidence["HF_SERVICE_GRIP_DEPTH_MM"]
    with pytest.raises(WetServiceHFContractError):
        validate_wet_service_hf_evidence(evidence)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -1.0, True])
def test_rejects_invalid_evidence(bad):
    evidence = valid()
    evidence["HF_SERVICE_RELEASE_CLEARANCE_MM"] = bad
    with pytest.raises(WetServiceHFContractError):
        validate_wet_service_hf_evidence(evidence)
