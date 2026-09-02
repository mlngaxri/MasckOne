import pytest

from masck_one.industrial_design_contract import IndustrialDesignContractError, validate_measurements, validate_surface_boundary


def nominal():
    return {
        "ID_FRONT_FIELD_MAX_Z": 20.0, "ID_REAR_MAX_Z": 14.0,
        "ID_FRONT_FLAT_PATCH_MAX_AREA": 600.0, "ID_FRONT_FIELD_DEPTH_RANGE": 4.0,
        "ID_SIDE_TRANSITION_RUN_L": 12.0, "ID_SIDE_TRANSITION_RUN_R": 12.0,
        "ID_SIDE_TRANSITION_DEPTH_L": 4.0, "ID_SIDE_TRANSITION_DEPTH_R": 4.0,
        "ID_REAR_FRONTAL_OVERHANG_L": 0.0, "ID_REAR_FRONTAL_OVERHANG_R": 0.0,
        "ID_REAR_FRONTAL_OVERHANG_T": 0.0, "ID_REAR_FRONTAL_OVERHANG_B": 0.0,
        "ID_SERVICE_GRIP_DEPTH": 0.9, "ID_SERVICE_GRIP_LAND": 12.0,
        "ID_SERVICE_RELEASE_CLEARANCE": 1.5, "ID_QUICK_RELEASE_TACTILE_LAND": 10.0,
        "ID_HAIR_PINCH_CLEARANCE_L": 2.0, "ID_HAIR_PINCH_CLEARANCE_R": 2.0,
        "ID_CONTROL_TACTILE_LAND_CLEAN": 10.0, "ID_CONTROL_TACTILE_LAND_SECONDARY": 8.0,
        "ID_CONTROL_TACTILE_SEPARATION": 2.0, "ID_EYE_APERTURE_CANT_L": -2.0,
        "ID_EYE_APERTURE_CANT_R": 2.0, "ID_EYE_SURROUND_WIDTH_MIN_L": 7.0,
        "ID_EYE_SURROUND_WIDTH_MAX_L": 10.0, "ID_EYE_SURROUND_WIDTH_MIN_R": 7.0,
        "ID_EYE_SURROUND_WIDTH_MAX_R": 10.0, "ID_MOUTH_SURROUND_WIDTH_MIN": 8.0,
        "ID_MOUTH_SURROUND_WIDTH_MAX": 12.0, "ID_MOUTH_SURROUND_SIDE_WIDTH_L": 10.0,
        "ID_MOUTH_SURROUND_SIDE_WIDTH_R": 10.0, "ID_NOSE_PROJECTION_ABOVE_FIELD": 1.0,
        "ID_RETENTION_VISIBLE_WIDTH_L": 10.0, "ID_RETENTION_VISIBLE_WIDTH_R": 10.0,
        "ID_SIDE_HARDWARE_PROJECTION_L": 1.0, "ID_SIDE_HARDWARE_PROJECTION_R": 1.0,
        "ID_SIDE_HARDWARE_STEP_L": 0.25, "ID_SIDE_HARDWARE_STEP_R": 0.25,
    }


def test_nominal_contract_passes():
    validate_measurements(nominal()); validate_surface_boundary("A", 0.05, 1.0); validate_surface_boundary("B", 0.10, 2.0)


def test_mirrored_signed_eye_cant_is_valid():
    values = nominal(); values["ID_EYE_APERTURE_CANT_L"] = -3.0; values["ID_EYE_APERTURE_CANT_R"] = 3.0
    validate_measurements(values)


def test_missing_named_measurement_fails_closed():
    values = nominal(); del values["ID_SERVICE_GRIP_DEPTH"]
    with pytest.raises(IndustrialDesignContractError, match="missing stable ID measurements"): validate_measurements(values)


def test_front_field_dead_zones_fail_closed():
    values = nominal(); values["ID_FRONT_FLAT_PATCH_MAX_AREA"] = 900.1
    with pytest.raises(IndustrialDesignContractError, match="flat dead zone"): validate_measurements(values)
    values = nominal(); values["ID_FRONT_FIELD_DEPTH_RANGE"] = 1.99
    with pytest.raises(IndustrialDesignContractError, match="flat plate"): validate_measurements(values)


def test_abrupt_side_mass_fails():
    values = nominal(); values["ID_SIDE_TRANSITION_RUN_L"] = 8.0
    with pytest.raises(IndustrialDesignContractError, match="too abrupt"): validate_measurements(values)


def test_unintended_side_asymmetry_fails():
    values = nominal(); values["ID_SIDE_TRANSITION_DEPTH_R"] = 5.1; values["ID_SIDE_TRANSITION_RUN_R"] = 15.3
    with pytest.raises(IndustrialDesignContractError, match="depth asymmetry"): validate_measurements(values)


def test_rear_mass_outside_frontal_field_fails():
    values = nominal(); values["ID_REAR_FRONTAL_OVERHANG_R"] = 0.2
    with pytest.raises(IndustrialDesignContractError, match="escapes frontal field"): validate_measurements(values)


def test_rear_layer_visual_dominance_fails():
    values = nominal(); values["ID_REAR_MAX_Z"] = 15.1
    with pytest.raises(IndustrialDesignContractError, match="too visually dominant"): validate_measurements(values)


def test_retention_visual_burden_and_side_hardware_integration_fail_closed():
    values = nominal(); values["ID_RETENTION_VISIBLE_WIDTH_L"] = 12.1
    with pytest.raises(IndustrialDesignContractError, match="retention member is too visually dominant"): validate_measurements(values)
    values = nominal(); values["ID_RETENTION_VISIBLE_WIDTH_R"] = 11.1
    with pytest.raises(IndustrialDesignContractError, match="retention visual width asymmetry"): validate_measurements(values)
    values = nominal(); values["ID_SIDE_HARDWARE_PROJECTION_L"] = 2.1
    with pytest.raises(IndustrialDesignContractError, match="attached pod"): validate_measurements(values)
    values = nominal(); values["ID_SIDE_HARDWARE_PROJECTION_R"] = 1.8
    with pytest.raises(IndustrialDesignContractError, match="side hardware projection asymmetry"): validate_measurements(values)
    values = nominal(); values["ID_SIDE_HARDWARE_STEP_L"] = 0.51
    with pytest.raises(IndustrialDesignContractError, match="abrupt local step"): validate_measurements(values)
    values = nominal(); values["ID_SIDE_HARDWARE_STEP_R"] = 0.50
    with pytest.raises(IndustrialDesignContractError, match="local-step asymmetry"): validate_measurements(values)


def test_service_grip_and_control_tactility_fail_closed():
    values = nominal(); values["ID_SERVICE_GRIP_DEPTH"] = 0.4
    with pytest.raises(IndustrialDesignContractError, match="service grip depth"): validate_measurements(values)
    values = nominal(); values["ID_SERVICE_GRIP_LAND"] = 11.9
    with pytest.raises(IndustrialDesignContractError, match="service grip land"): validate_measurements(values)
    values = nominal(); values["ID_SERVICE_RELEASE_CLEARANCE"] = 1.4
    with pytest.raises(IndustrialDesignContractError, match="service release"): validate_measurements(values)
    values = nominal(); values["ID_QUICK_RELEASE_TACTILE_LAND"] = 9.9
    with pytest.raises(IndustrialDesignContractError, match="quick release tactile land"): validate_measurements(values)
    values = nominal(); values["ID_CONTROL_TACTILE_LAND_CLEAN"] = 9.9
    with pytest.raises(IndustrialDesignContractError, match="CLEAN tactile land"): validate_measurements(values)
    values = nominal(); values["ID_CONTROL_TACTILE_LAND_SECONDARY"] = 7.9
    with pytest.raises(IndustrialDesignContractError, match="secondary tactile land"): validate_measurements(values)
    values = nominal(); values["ID_CONTROL_TACTILE_SEPARATION"] = 1.9
    with pytest.raises(IndustrialDesignContractError, match="tactile separation"): validate_measurements(values)


def test_hair_pinch_clearance_fails_bilaterally():
    values = nominal(); values["ID_HAIR_PINCH_CLEARANCE_L"] = 1.9
    with pytest.raises(IndustrialDesignContractError, match="hair-pinch clearance"): validate_measurements(values)
    values = nominal(); values["ID_HAIR_PINCH_CLEARANCE_R"] = 1.9
    with pytest.raises(IndustrialDesignContractError, match="hair-pinch clearance"): validate_measurements(values)


def test_hostile_or_asymmetric_eye_expression_fails():
    values = nominal(); values["ID_EYE_APERTURE_CANT_L"] = -4.1
    with pytest.raises(IndustrialDesignContractError, match="facial-neutrality"): validate_measurements(values)
    values = nominal(); values["ID_EYE_APERTURE_CANT_R"] = 3.6
    with pytest.raises(IndustrialDesignContractError, match="unintended expression"): validate_measurements(values)


def test_eye_surround_goggle_rim_and_asymmetry_fail_closed():
    values = nominal(); values["ID_EYE_SURROUND_WIDTH_MAX_L"] = 12.1
    with pytest.raises(IndustrialDesignContractError, match="goggle rim"): validate_measurements(values)
    values = nominal(); values["ID_EYE_SURROUND_WIDTH_MIN_R"] = 8.6
    with pytest.raises(IndustrialDesignContractError, match="unintended facial expression"): validate_measurements(values)
    values = nominal(); values["ID_EYE_SURROUND_WIDTH_MIN_L"] = 11.0; values["ID_EYE_SURROUND_WIDTH_MAX_L"] = 10.0
    with pytest.raises(IndustrialDesignContractError, match="max width below min width"): validate_measurements(values)


def test_mouth_surround_ring_and_asymmetry_fail_closed():
    values = nominal(); values["ID_MOUTH_SURROUND_WIDTH_MAX"] = 14.1
    with pytest.raises(IndustrialDesignContractError, match="separate ring"): validate_measurements(values)
    values = nominal(); values["ID_MOUTH_SURROUND_SIDE_WIDTH_R"] = 11.6
    with pytest.raises(IndustrialDesignContractError, match="mouth surround side asymmetry"): validate_measurements(values)
    values = nominal(); values["ID_MOUTH_SURROUND_WIDTH_MIN"] = 13.0; values["ID_MOUTH_SURROUND_WIDTH_MAX"] = 12.0
    with pytest.raises(IndustrialDesignContractError, match="max width below min width"): validate_measurements(values)


def test_nonfinite_signed_eye_geometry_fails_closed():
    values = nominal(); values["ID_EYE_APERTURE_CANT_L"] = float("nan")
    with pytest.raises(IndustrialDesignContractError, match="must be finite"): validate_measurements(values)


def test_protruding_nose_cone_fails():
    values = nominal(); values["ID_NOSE_PROJECTION_ABOVE_FIELD"] = 2.1
    with pytest.raises(IndustrialDesignContractError, match="protruding cone"): validate_measurements(values)


def test_surface_continuity_over_limit_fails():
    with pytest.raises(IndustrialDesignContractError, match="A-surface continuity failed"): validate_surface_boundary("A", 0.051, 1.0)
    with pytest.raises(IndustrialDesignContractError, match="B-surface continuity failed"): validate_surface_boundary("B", 0.10, 2.01)
