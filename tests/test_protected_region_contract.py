import pytest

from masck_one.protected_region_contract import ProtectedRegionContractError, validate_protected_regions


def nominal():
    return {
        "ID_EYE_APERTURE_AREA_L": 900.0, "ID_EYE_APERTURE_AREA_R": 900.0,
        "ID_EYE_APERTURE_WIDTH_L": 42.0, "ID_EYE_APERTURE_WIDTH_R": 42.0,
        "ID_EYE_APERTURE_HEIGHT_L": 24.0, "ID_EYE_APERTURE_HEIGHT_R": 24.0,
        "ID_EYE_EDGE_CLEARANCE_L": 4.0, "ID_EYE_EDGE_CLEARANCE_R": 4.0,
        "ID_NOSTRIL_EDGE_CLEARANCE_L": 3.5, "ID_NOSTRIL_EDGE_CLEARANCE_R": 3.5,
        "ID_MOUTH_EDGE_CLEARANCE_L": 5.0, "ID_MOUTH_EDGE_CLEARANCE_R": 5.0,
    }


def test_nominal_protected_regions_pass():
    validate_protected_regions(nominal())


def test_missing_or_nonfinite_evidence_fails_closed():
    values = nominal(); del values["ID_MOUTH_EDGE_CLEARANCE_R"]
    with pytest.raises(ProtectedRegionContractError, match="missing protected-region"): validate_protected_regions(values)
    values = nominal(); values["ID_EYE_APERTURE_AREA_L"] = float("nan")
    with pytest.raises(ProtectedRegionContractError, match="finite and > 0"): validate_protected_regions(values)


def test_eye_aperture_visual_imbalance_fails():
    values = nominal(); values["ID_EYE_APERTURE_AREA_R"] = 820.0
    with pytest.raises(ProtectedRegionContractError, match="area imbalance"): validate_protected_regions(values)
    values = nominal(); values["ID_EYE_APERTURE_WIDTH_R"] = 44.1
    with pytest.raises(ProtectedRegionContractError, match="width asymmetry"): validate_protected_regions(values)
    values = nominal(); values["ID_EYE_APERTURE_HEIGHT_R"] = 26.1
    with pytest.raises(ProtectedRegionContractError, match="height asymmetry"): validate_protected_regions(values)


@pytest.mark.parametrize("name,value,match", [
    ("ID_EYE_EDGE_CLEARANCE_L", 2.9, "eye protected-region"),
    ("ID_NOSTRIL_EDGE_CLEARANCE_R", 2.9, "nostril protected-region"),
    ("ID_MOUTH_EDGE_CLEARANCE_L", 3.9, "mouth protected-region"),
])
def test_protected_region_encroachment_fails(name, value, match):
    values = nominal(); values[name] = value
    with pytest.raises(ProtectedRegionContractError, match=match): validate_protected_regions(values)


def test_clearance_asymmetry_fails():
    values = nominal(); values["ID_MOUTH_EDGE_CLEARANCE_R"] = 6.6
    with pytest.raises(ProtectedRegionContractError, match="clearance asymmetry"): validate_protected_regions(values)
