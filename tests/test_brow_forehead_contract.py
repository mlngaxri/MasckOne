import pytest

from masck_one.brow_forehead_contract import BrowForeheadContractError, validate_brow_forehead


def nominal():
    return {
        "ID_BROW_SHELF_PROJECTION_L": 0.8,
        "ID_BROW_SHELF_PROJECTION_R": 0.8,
        "ID_BROW_TO_FOREHEAD_BLEND_RUN_L": 14.0,
        "ID_BROW_TO_FOREHEAD_BLEND_RUN_R": 14.0,
        "ID_FOREHEAD_TO_TEMPLE_BLEND_RUN_L": 16.0,
        "ID_FOREHEAD_TO_TEMPLE_BLEND_RUN_R": 16.0,
        "ID_TEMPLE_DEPTH_EXCURSION_L": 2.0,
        "ID_TEMPLE_DEPTH_EXCURSION_R": 2.0,
    }


def test_nominal_upper_face_passes():
    validate_brow_forehead(nominal())


def test_missing_evidence_fails_closed():
    values = nominal(); del values["ID_BROW_SHELF_PROJECTION_L"]
    with pytest.raises(BrowForeheadContractError, match="missing stable brow/forehead measurements"):
        validate_brow_forehead(values)


def test_visor_brow_fails():
    values = nominal(); values["ID_BROW_SHELF_PROJECTION_R"] = 1.6
    with pytest.raises(BrowForeheadContractError, match="visor shelf"):
        validate_brow_forehead(values)


def test_abrupt_brow_to_forehead_transition_fails():
    values = nominal(); values["ID_BROW_TO_FOREHEAD_BLEND_RUN_L"] = 11.9
    with pytest.raises(BrowForeheadContractError, match="calm continuous facial field"):
        validate_brow_forehead(values)


def test_short_or_deep_temple_transition_fails():
    values = nominal(); values["ID_FOREHEAD_TO_TEMPLE_BLEND_RUN_R"] = 13.9
    with pytest.raises(BrowForeheadContractError, match="attached side hardware"):
        validate_brow_forehead(values)
    values = nominal(); values["ID_TEMPLE_DEPTH_EXCURSION_L"] = 3.1
    with pytest.raises(BrowForeheadContractError, match="temple pod"):
        validate_brow_forehead(values)


def test_upper_face_asymmetry_fails_closed():
    values = nominal(); values["ID_BROW_SHELF_PROJECTION_R"] = 1.5
    with pytest.raises(BrowForeheadContractError, match="facial expression"):
        validate_brow_forehead(values)
    values = nominal(); values["ID_FOREHEAD_TO_TEMPLE_BLEND_RUN_R"] = 17.6
    with pytest.raises(BrowForeheadContractError, match="visual mass"):
        validate_brow_forehead(values)
    values = nominal(); values["ID_TEMPLE_DEPTH_EXCURSION_R"] = 2.8
    with pytest.raises(BrowForeheadContractError, match="side-hardware integration"):
        validate_brow_forehead(values)


def test_nonfinite_and_negative_evidence_fail_closed():
    values = nominal(); values["ID_TEMPLE_DEPTH_EXCURSION_L"] = float("inf")
    with pytest.raises(BrowForeheadContractError, match="must be finite"):
        validate_brow_forehead(values)
    values = nominal(); values["ID_BROW_TO_FOREHEAD_BLEND_RUN_R"] = -0.1
    with pytest.raises(BrowForeheadContractError, match="must be >= 0"):
        validate_brow_forehead(values)
