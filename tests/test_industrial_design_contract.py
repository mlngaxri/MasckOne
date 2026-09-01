import pytest

from masck_one.industrial_design_contract import (
    IndustrialDesignContractError,
    validate_measurements,
    validate_surface_boundary,
)


def nominal():
    return {
        "ID_FRONT_FIELD_MAX_Z": 20.0,
        "ID_SIDE_TRANSITION_RUN_L": 12.0,
        "ID_SIDE_TRANSITION_RUN_R": 12.0,
        "ID_SIDE_TRANSITION_DEPTH_L": 4.0,
        "ID_SIDE_TRANSITION_DEPTH_R": 4.0,
        "ID_REAR_FRONTAL_OVERHANG_L": 0.0,
        "ID_REAR_FRONTAL_OVERHANG_R": 0.0,
        "ID_REAR_FRONTAL_OVERHANG_T": 0.0,
        "ID_REAR_FRONTAL_OVERHANG_B": 0.0,
        "ID_SERVICE_GRIP_DEPTH": 0.9,
        "ID_CONTROL_TACTILE_LAND_CLEAN": 10.0,
        "ID_CONTROL_TACTILE_LAND_SECONDARY": 8.0,
        "ID_CONTROL_TACTILE_SEPARATION": 2.0,
    }


def test_nominal_contract_passes():
    validate_measurements(nominal())
    validate_surface_boundary("A", 0.05, 1.0)
    validate_surface_boundary("B", 0.10, 2.0)


def test_missing_named_measurement_fails_closed():
    values = nominal()
    del values["ID_SERVICE_GRIP_DEPTH"]
    with pytest.raises(IndustrialDesignContractError, match="missing stable ID measurements"):
        validate_measurements(values)


def test_abrupt_side_mass_fails():
    values = nominal()
    values["ID_SIDE_TRANSITION_RUN_L"] = 8.0
    with pytest.raises(IndustrialDesignContractError, match="too abrupt"):
        validate_measurements(values)


def test_rear_mass_outside_frontal_field_fails():
    values = nominal()
    values["ID_REAR_FRONTAL_OVERHANG_R"] = 0.2
    with pytest.raises(IndustrialDesignContractError, match="escapes frontal field"):
        validate_measurements(values)


def test_service_grip_and_control_tactility_fail_closed():
    values = nominal()
    values["ID_SERVICE_GRIP_DEPTH"] = 0.4
    with pytest.raises(IndustrialDesignContractError, match="service grip depth"):
        validate_measurements(values)

    values = nominal()
    values["ID_CONTROL_TACTILE_LAND_CLEAN"] = 9.9
    with pytest.raises(IndustrialDesignContractError, match="CLEAN tactile land"):
        validate_measurements(values)


def test_surface_continuity_over_limit_fails():
    with pytest.raises(IndustrialDesignContractError, match="A-surface continuity failed"):
        validate_surface_boundary("A", 0.051, 1.0)
    with pytest.raises(IndustrialDesignContractError, match="B-surface continuity failed"):
        validate_surface_boundary("B", 0.10, 2.01)
