import pytest

from masck_one.chin_field_contract import ChinFieldContractError, validate_chin_field


def nominal():
    return {
        "ID_MOUTH_TO_CHIN_BLEND_RUN": 12.0,
        "ID_CHIN_PROJECTION_ABOVE_LOWER_FIELD": 1.0,
        "ID_JAW_TRANSITION_RUN_L": 14.0,
        "ID_JAW_TRANSITION_RUN_R": 14.0,
        "ID_JAW_TRANSITION_DEPTH_L": 2.0,
        "ID_JAW_TRANSITION_DEPTH_R": 2.0,
        "ID_LOWER_EDGE_HEIGHT_L": 8.0,
        "ID_LOWER_EDGE_HEIGHT_R": 8.0,
    }


def test_nominal_chin_field_passes():
    validate_chin_field(nominal())


def test_missing_evidence_fails_closed():
    values = nominal(); del values["ID_JAW_TRANSITION_RUN_L"]
    with pytest.raises(ChinFieldContractError, match="missing stable chin-field measurements"):
        validate_chin_field(values)


def test_abrupt_mouth_to_chin_transition_fails():
    values = nominal(); values["ID_MOUTH_TO_CHIN_BLEND_RUN"] = 9.9
    with pytest.raises(ChinFieldContractError, match="lower bumper"):
        validate_chin_field(values)


def test_protruding_chin_tab_fails():
    values = nominal(); values["ID_CHIN_PROJECTION_ABOVE_LOWER_FIELD"] = 2.1
    with pytest.raises(ChinFieldContractError, match="separate tab"):
        validate_chin_field(values)


def test_short_or_deep_jaw_transition_fails_bilaterally():
    values = nominal(); values["ID_JAW_TRANSITION_RUN_L"] = 11.9
    with pytest.raises(ChinFieldContractError, match="broad lower-face blend"):
        validate_chin_field(values)
    values = nominal(); values["ID_JAW_TRANSITION_DEPTH_R"] = 3.1
    with pytest.raises(ChinFieldContractError, match="lower pod"):
        validate_chin_field(values)


def test_lower_face_asymmetry_fails_closed():
    values = nominal(); values["ID_JAW_TRANSITION_RUN_R"] = 15.6
    with pytest.raises(ChinFieldContractError, match="run asymmetry"):
        validate_chin_field(values)
    values = nominal(); values["ID_JAW_TRANSITION_DEPTH_R"] = 2.8
    with pytest.raises(ChinFieldContractError, match="depth asymmetry"):
        validate_chin_field(values)
    values = nominal(); values["ID_LOWER_EDGE_HEIGHT_R"] = 9.1
    with pytest.raises(ChinFieldContractError, match="tilted chin silhouette"):
        validate_chin_field(values)


def test_nonfinite_and_negative_evidence_fail_closed():
    values = nominal(); values["ID_CHIN_PROJECTION_ABOVE_LOWER_FIELD"] = float("nan")
    with pytest.raises(ChinFieldContractError, match="must be finite"):
        validate_chin_field(values)
    values = nominal(); values["ID_LOWER_EDGE_HEIGHT_L"] = -0.1
    with pytest.raises(ChinFieldContractError, match="must be >= 0"):
        validate_chin_field(values)
