import math
import pytest

from masck_one.retention_hair_pinch_contract import RetentionHairPinchContractError, validate_retention_hair_pinch


def good():
    return {
        "HF_RETENTION_EXPOSED_GAP_L": 5.0,
        "HF_RETENTION_EXPOSED_GAP_R": 5.0,
        "HF_RETENTION_SKIN_EDGE_RADIUS_L": 1.4,
        "HF_RETENTION_SKIN_EDGE_RADIUS_R": 1.4,
        "HF_RETENTION_HAIR_SWEEP_RADIUS_L": 2.0,
        "HF_RETENTION_HAIR_SWEEP_RADIUS_R": 2.0,
    }


def test_nominal_retention_geometry_passes():
    validate_retention_hair_pinch(good())


@pytest.mark.parametrize("key,value", [
    ("HF_RETENTION_EXPOSED_GAP_L", 3.9),
    ("HF_RETENTION_SKIN_EDGE_RADIUS_R", 0.9),
    ("HF_RETENTION_HAIR_SWEEP_RADIUS_L", 1.4),
])
def test_hostile_local_geometry_fails(key, value):
    v = good(); v[key] = value
    with pytest.raises(RetentionHairPinchContractError):
        validate_retention_hair_pinch(v)


def test_bilateral_gap_asymmetry_fails():
    v = good(); v["HF_RETENTION_EXPOSED_GAP_R"] = 6.1
    with pytest.raises(RetentionHairPinchContractError):
        validate_retention_hair_pinch(v)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -0.1])
def test_nonfinite_or_negative_evidence_fails(bad):
    v = good(); v["HF_RETENTION_HAIR_SWEEP_RADIUS_R"] = bad
    with pytest.raises(RetentionHairPinchContractError):
        validate_retention_hair_pinch(v)


def test_missing_evidence_fails_closed():
    v = good(); del v["HF_RETENTION_EXPOSED_GAP_R"]
    with pytest.raises(RetentionHairPinchContractError):
        validate_retention_hair_pinch(v)
