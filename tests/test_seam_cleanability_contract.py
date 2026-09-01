import pytest

from masck_one.seam_cleanability_contract import SeamCleanabilityContractError, validate_seam_cleanability


def nominal():
    return {
        "ID_PRIMARY_SEAM_GAP_MIN": 0.40,
        "ID_PRIMARY_SEAM_GAP_MAX": 0.50,
        "ID_PRIMARY_SEAM_OFFSET_FROM_TURNOVER": 1.0,
        "ID_WET_EXTERIOR_MIN_TRENCH_WIDTH": 2.5,
        "ID_WET_EXTERIOR_MIN_ROOT_RADIUS": 1.0,
        "ID_WET_EXTERIOR_MAX_BLIND_TRENCH_DEPTH": 1.0,
    }


def test_nominal_passes():
    validate_seam_cleanability(nominal())


def test_missing_or_nonfinite_evidence_fails_closed():
    values = nominal(); del values["ID_PRIMARY_SEAM_GAP_MIN"]
    with pytest.raises(SeamCleanabilityContractError, match="missing seam/cleanability"): validate_seam_cleanability(values)
    values = nominal(); values["ID_WET_EXTERIOR_MIN_ROOT_RADIUS"] = float("nan")
    with pytest.raises(SeamCleanabilityContractError, match="finite"): validate_seam_cleanability(values)


def test_seam_band_and_uniformity_are_guarded():
    values = nominal(); values["ID_PRIMARY_SEAM_GAP_MIN"] = 0.34
    with pytest.raises(SeamCleanabilityContractError, match="premium-gap"): validate_seam_cleanability(values)
    values = nominal(); values["ID_PRIMARY_SEAM_GAP_MAX"] = 0.61
    with pytest.raises(SeamCleanabilityContractError, match="premium-gap"): validate_seam_cleanability(values)
    values = nominal(); values["ID_PRIMARY_SEAM_GAP_MIN"] = 0.35; values["ID_PRIMARY_SEAM_GAP_MAX"] = 0.51
    with pytest.raises(SeamCleanabilityContractError, match="visually uncontrolled"): validate_seam_cleanability(values)


def test_seam_must_track_low_highlight_turnover():
    values = nominal(); values["ID_PRIMARY_SEAM_OFFSET_FROM_TURNOVER"] = 2.01
    with pytest.raises(SeamCleanabilityContractError, match="wanders"): validate_seam_cleanability(values)


def test_wet_exterior_rejects_residue_traps():
    values = nominal(); values["ID_WET_EXTERIOR_MIN_TRENCH_WIDTH"] = 1.99
    with pytest.raises(SeamCleanabilityContractError, match="too narrow"): validate_seam_cleanability(values)
    values = nominal(); values["ID_WET_EXTERIOR_MIN_ROOT_RADIUS"] = 0.74
    with pytest.raises(SeamCleanabilityContractError, match="root radius"): validate_seam_cleanability(values)
    values = nominal(); values["ID_WET_EXTERIOR_MAX_BLIND_TRENCH_DEPTH"] = 1.26
    with pytest.raises(SeamCleanabilityContractError, match="too deep"): validate_seam_cleanability(values)
