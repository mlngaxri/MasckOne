import pytest

from masck_one.forehead_crown_contract import ForeheadCrownContractError, validate_forehead_crown


def nominal():
    return {
        "ID_FOREHEAD_CROWN_BLEND_SPAN": 42.0,
        "ID_FOREHEAD_CROWN_LOCAL_RISE": 1.6,
        "ID_UPPER_EDGE_HEIGHT_L": 18.0,
        "ID_UPPER_EDGE_HEIGHT_R": 18.0,
        "ID_FOREHEAD_CROWN_MAX_SLOPE_BREAK_DEG": 5.0,
    }


def test_nominal_forehead_crown_passes():
    validate_forehead_crown(nominal())


def test_missing_evidence_fails_closed():
    values = nominal(); del values["ID_FOREHEAD_CROWN_BLEND_SPAN"]
    with pytest.raises(ForeheadCrownContractError, match="missing stable forehead-crown measurements"):
        validate_forehead_crown(values)


def test_narrow_or_peaked_crown_fails():
    values = nominal(); values["ID_FOREHEAD_CROWN_BLEND_SPAN"] = 35.9
    with pytest.raises(ForeheadCrownContractError, match="central horn or helmet feature"):
        validate_forehead_crown(values)
    values = nominal(); values["ID_FOREHEAD_CROWN_LOCAL_RISE"] = 2.6
    with pytest.raises(ForeheadCrownContractError, match="calm low-mass upper silhouette"):
        validate_forehead_crown(values)


def test_tilted_or_scalloped_upper_edge_fails():
    values = nominal(); values["ID_UPPER_EDGE_HEIGHT_R"] = 18.8
    with pytest.raises(ForeheadCrownContractError, match="tilted or scalloped"):
        validate_forehead_crown(values)


def test_abrupt_crown_slope_break_fails():
    values = nominal(); values["ID_FOREHEAD_CROWN_MAX_SLOPE_BREAK_DEG"] = 8.1
    with pytest.raises(ForeheadCrownContractError, match="abrupt slope break"):
        validate_forehead_crown(values)


def test_nonfinite_and_negative_evidence_fail_closed():
    values = nominal(); values["ID_FOREHEAD_CROWN_LOCAL_RISE"] = float("inf")
    with pytest.raises(ForeheadCrownContractError, match="must be finite"):
        validate_forehead_crown(values)
    values = nominal(); values["ID_FOREHEAD_CROWN_MAX_SLOPE_BREAK_DEG"] = -0.1
    with pytest.raises(ForeheadCrownContractError, match="must be >= 0"):
        validate_forehead_crown(values)
