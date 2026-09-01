import math
import pytest

from masck_one.physical_hmi_contract import PhysicalHMIContractError, validate_measurements


def valid():
    return {
        "HMI_PRIMARY_HEIGHT_MM": 1.00,
        "HMI_SECONDARY_HEIGHT_MM": 0.50,
        "HMI_PRIMARY_TACTILE_FEATURE_MM": 0.70,
        "HMI_SECONDARY_TACTILE_FEATURE_MM": 0.45,
        "HMI_STATUS_WINDOW_MINOR_AXIS_MM": 2.5,
        "HMI_STATUS_WINDOW_RECESS_MM": 0.30,
        "HMI_STATUS_WINDOW_EDGE_RADIUS_MM": 0.75,
        "HMI_CONTROL_TO_SERVICE_SEPARATION_MM": 8.0,
        "HMI_CONTROL_CENTER_SPACING_MM": 12.0,
        "HMI_SECONDARY_GUARD_OFFSET_MM": 0.80,
    }


def test_valid_physical_hmi_passes():
    validate_measurements(valid())


@pytest.mark.parametrize("key,value", [
    ("HMI_PRIMARY_HEIGHT_MM", 0.70),
    ("HMI_PRIMARY_TACTILE_FEATURE_MM", 0.20),
    ("HMI_SECONDARY_TACTILE_FEATURE_MM", 0.20),
    ("HMI_STATUS_WINDOW_MINOR_AXIS_MM", 1.5),
    ("HMI_STATUS_WINDOW_RECESS_MM", 0.80),
    ("HMI_STATUS_WINDOW_EDGE_RADIUS_MM", 0.20),
    ("HMI_CONTROL_TO_SERVICE_SEPARATION_MM", 4.0),
    ("HMI_CONTROL_CENTER_SPACING_MM", 7.0),
    ("HMI_SECONDARY_GUARD_OFFSET_MM", 0.20),
    ("HMI_SECONDARY_GUARD_OFFSET_MM", 2.0),
])
def test_hostile_hmi_geometry_fails(key, value):
    evidence = valid()
    evidence[key] = value
    with pytest.raises(PhysicalHMIContractError):
        validate_measurements(evidence)


def test_missing_hmi_evidence_fails_closed():
    evidence = valid()
    evidence.pop("HMI_STATUS_WINDOW_MINOR_AXIS_MM")
    with pytest.raises(PhysicalHMIContractError):
        validate_measurements(evidence)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -1.0])
def test_invalid_hmi_evidence_fails_closed(bad):
    evidence = valid()
    evidence["HMI_PRIMARY_TACTILE_FEATURE_MM"] = bad
    with pytest.raises(PhysicalHMIContractError):
        validate_measurements(evidence)
