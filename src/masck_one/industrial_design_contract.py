"""Executable industrial-design gates for Masck One physical CAD evidence.

Checks consume stable named measurements rather than CAD kernel face/edge IDs.
Targets remain digital/prototype gates until physical fit, tooling and CMF work
promote them.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class IDLimits:
    max_unseamed_depth_step_mm: float = 3.0
    min_side_transition_run_depth_ratio: float = 3.0
    max_side_depth_asymmetry_mm: float = 1.0
    max_side_run_asymmetry_mm: float = 2.0
    max_a_surface_gap_mm: float = 0.05
    max_a_surface_tangent_deg: float = 1.0
    max_b_surface_gap_mm: float = 0.10
    max_b_surface_tangent_deg: float = 2.0
    min_primary_control_land_mm: float = 10.0
    min_secondary_control_land_mm: float = 8.0
    min_control_separation_mm: float = 2.0
    service_grip_depth_min_mm: float = 0.6
    service_grip_depth_max_mm: float = 1.2
    min_service_grip_land_mm: float = 12.0
    min_service_release_clearance_mm: float = 1.5
    min_quick_release_tactile_land_mm: float = 10.0
    min_hair_pinch_clearance_mm: float = 2.0
    max_eye_aperture_angle_asymmetry_deg: float = 1.5
    max_eye_aperture_hostile_cant_deg: float = 4.0
    max_eye_surround_width_asymmetry_mm: float = 1.5
    max_eye_surround_width_range_mm: float = 5.0
    max_nose_projection_above_field_mm: float = 2.0
    max_rear_depth_fraction_of_front_field: float = 0.75
    max_retention_visible_width_mm: float = 12.0
    max_retention_width_asymmetry_mm: float = 1.0
    max_side_hardware_projection_mm: float = 2.0
    max_side_hardware_projection_asymmetry_mm: float = 0.75
    max_side_hardware_step_mm: float = 0.50
    max_side_hardware_step_asymmetry_mm: float = 0.25
    max_front_flat_patch_area_mm2: float = 900.0
    min_front_field_depth_range_mm: float = 2.0


REQUIRED_MEASUREMENTS = (
    "ID_FRONT_FIELD_MAX_Z", "ID_REAR_MAX_Z",
    "ID_FRONT_FLAT_PATCH_MAX_AREA", "ID_FRONT_FIELD_DEPTH_RANGE",
    "ID_SIDE_TRANSITION_RUN_L", "ID_SIDE_TRANSITION_RUN_R",
    "ID_SIDE_TRANSITION_DEPTH_L", "ID_SIDE_TRANSITION_DEPTH_R",
    "ID_REAR_FRONTAL_OVERHANG_L", "ID_REAR_FRONTAL_OVERHANG_R",
    "ID_REAR_FRONTAL_OVERHANG_T", "ID_REAR_FRONTAL_OVERHANG_B",
    "ID_SERVICE_GRIP_DEPTH", "ID_SERVICE_GRIP_LAND",
    "ID_SERVICE_RELEASE_CLEARANCE", "ID_QUICK_RELEASE_TACTILE_LAND",
    "ID_HAIR_PINCH_CLEARANCE_L", "ID_HAIR_PINCH_CLEARANCE_R",
    "ID_CONTROL_TACTILE_LAND_CLEAN", "ID_CONTROL_TACTILE_LAND_SECONDARY",
    "ID_CONTROL_TACTILE_SEPARATION", "ID_EYE_APERTURE_CANT_L",
    "ID_EYE_APERTURE_CANT_R", "ID_EYE_SURROUND_WIDTH_MIN_L",
    "ID_EYE_SURROUND_WIDTH_MAX_L", "ID_EYE_SURROUND_WIDTH_MIN_R",
    "ID_EYE_SURROUND_WIDTH_MAX_R", "ID_NOSE_PROJECTION_ABOVE_FIELD",
    "ID_RETENTION_VISIBLE_WIDTH_L", "ID_RETENTION_VISIBLE_WIDTH_R",
    "ID_SIDE_HARDWARE_PROJECTION_L", "ID_SIDE_HARDWARE_PROJECTION_R",
    "ID_SIDE_HARDWARE_STEP_L", "ID_SIDE_HARDWARE_STEP_R",
)

SIGNED_MEASUREMENTS = frozenset(("ID_EYE_APERTURE_CANT_L", "ID_EYE_APERTURE_CANT_R"))


class IndustrialDesignContractError(ValueError):
    """Raised when physical CAD evidence violates the ID contract."""


def _finite(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise IndustrialDesignContractError(f"{name} must be finite")
    return value


def _finite_nonnegative(name: str, value: float) -> float:
    value = _finite(name, value)
    if value < 0:
        raise IndustrialDesignContractError(f"{name} must be >= 0")
    return value


def validate_measurements(values: Mapping[str, float], limits: IDLimits = IDLimits()) -> None:
    """Fail closed on absent, malformed or packaging-degrading ID evidence."""
    missing = sorted(set(REQUIRED_MEASUREMENTS) - set(values))
    if missing:
        raise IndustrialDesignContractError("missing stable ID measurements: " + ", ".join(missing))
    v = {
        name: (_finite(name, values[name]) if name in SIGNED_MEASUREMENTS else _finite_nonnegative(name, values[name]))
        for name in REQUIRED_MEASUREMENTS
    }

    if v["ID_FRONT_FLAT_PATCH_MAX_AREA"] > limits.max_front_flat_patch_area_mm2:
        raise IndustrialDesignContractError("front facial field contains an oversized flat dead zone")
    if v["ID_FRONT_FIELD_DEPTH_RANGE"] < limits.min_front_field_depth_range_mm:
        raise IndustrialDesignContractError("front facial field lacks sufficient authored depth variation and reads as a flat plate")

    for side in ("L", "R"):
        run = v[f"ID_SIDE_TRANSITION_RUN_{side}"]
        depth = v[f"ID_SIDE_TRANSITION_DEPTH_{side}"]
        if depth > limits.max_unseamed_depth_step_mm and run < limits.min_side_transition_run_depth_ratio * depth:
            raise IndustrialDesignContractError(
                f"{side} side transition is too abrupt: run/depth={run / depth:.2f}, requires >= {limits.min_side_transition_run_depth_ratio:.2f}"
            )
    if abs(v["ID_SIDE_TRANSITION_DEPTH_L"] - v["ID_SIDE_TRANSITION_DEPTH_R"]) > limits.max_side_depth_asymmetry_mm:
        raise IndustrialDesignContractError("side depth asymmetry creates unintended visual weight")
    if abs(v["ID_SIDE_TRANSITION_RUN_L"] - v["ID_SIDE_TRANSITION_RUN_R"]) > limits.max_side_run_asymmetry_mm:
        raise IndustrialDesignContractError("side transition asymmetry creates unintended visual weight")

    if any(v[f"ID_REAR_FRONTAL_OVERHANG_{d}"] > 0 for d in ("L", "R", "T", "B")):
        raise IndustrialDesignContractError("rear/service mass escapes frontal field silhouette; packaging justification required before ID release")
    if v["ID_FRONT_FIELD_MAX_Z"] <= 0:
        raise IndustrialDesignContractError("front field depth must be positive")
    if v["ID_REAR_MAX_Z"] > limits.max_rear_depth_fraction_of_front_field * v["ID_FRONT_FIELD_MAX_Z"]:
        raise IndustrialDesignContractError("rear/service layer is too visually dominant relative to facial field")

    for side in ("L", "R"):
        if v[f"ID_RETENTION_VISIBLE_WIDTH_{side}"] > limits.max_retention_visible_width_mm:
            raise IndustrialDesignContractError(f"{side} retention member is too visually dominant in the worn silhouette")
        if v[f"ID_SIDE_HARDWARE_PROJECTION_{side}"] > limits.max_side_hardware_projection_mm:
            raise IndustrialDesignContractError(f"{side} side hardware reads as an attached pod rather than an integrated transition")
        if v[f"ID_SIDE_HARDWARE_STEP_{side}"] > limits.max_side_hardware_step_mm:
            raise IndustrialDesignContractError(f"{side} side hardware has an abrupt local step that breaks the continuous side field")
    if abs(v["ID_RETENTION_VISIBLE_WIDTH_L"] - v["ID_RETENTION_VISIBLE_WIDTH_R"]) > limits.max_retention_width_asymmetry_mm:
        raise IndustrialDesignContractError("retention visual width asymmetry creates unintended worn imbalance")
    if abs(v["ID_SIDE_HARDWARE_PROJECTION_L"] - v["ID_SIDE_HARDWARE_PROJECTION_R"]) > limits.max_side_hardware_projection_asymmetry_mm:
        raise IndustrialDesignContractError("side hardware projection asymmetry creates unintended visual weight")
    if abs(v["ID_SIDE_HARDWARE_STEP_L"] - v["ID_SIDE_HARDWARE_STEP_R"]) > limits.max_side_hardware_step_asymmetry_mm:
        raise IndustrialDesignContractError("side hardware local-step asymmetry creates unintended highlight imbalance")

    grip = v["ID_SERVICE_GRIP_DEPTH"]
    if not limits.service_grip_depth_min_mm <= grip <= limits.service_grip_depth_max_mm:
        raise IndustrialDesignContractError("service grip depth is outside the wet-finger prototype exploration band")
    if v["ID_SERVICE_GRIP_LAND"] < limits.min_service_grip_land_mm:
        raise IndustrialDesignContractError("service grip land is too small for deliberate wet-finger acquisition")
    if v["ID_SERVICE_RELEASE_CLEARANCE"] < limits.min_service_release_clearance_mm:
        raise IndustrialDesignContractError("service release lacks prototype finger/tool clearance")
    if v["ID_QUICK_RELEASE_TACTILE_LAND"] < limits.min_quick_release_tactile_land_mm:
        raise IndustrialDesignContractError("quick release tactile land is below prototype discoverability target")
    for side in ("L", "R"):
        if v[f"ID_HAIR_PINCH_CLEARANCE_{side}"] < limits.min_hair_pinch_clearance_mm:
            raise IndustrialDesignContractError(f"{side} retention/service interface lacks prototype hair-pinch clearance")
    if v["ID_CONTROL_TACTILE_LAND_CLEAN"] < limits.min_primary_control_land_mm:
        raise IndustrialDesignContractError("CLEAN tactile land is below prototype discoverability target")
    if v["ID_CONTROL_TACTILE_LAND_SECONDARY"] < limits.min_secondary_control_land_mm:
        raise IndustrialDesignContractError("secondary tactile land is below prototype discoverability target")
    if v["ID_CONTROL_TACTILE_SEPARATION"] < limits.min_control_separation_mm:
        raise IndustrialDesignContractError("adjacent physical controls lack tactile separation")

    cant_l, cant_r = v["ID_EYE_APERTURE_CANT_L"], v["ID_EYE_APERTURE_CANT_R"]
    if max(abs(cant_l), abs(cant_r)) > limits.max_eye_aperture_hostile_cant_deg:
        raise IndustrialDesignContractError("eye aperture cant exceeds facial-neutrality target")
    if abs(abs(cant_l) - abs(cant_r)) > limits.max_eye_aperture_angle_asymmetry_deg:
        raise IndustrialDesignContractError("eye aperture asymmetry creates unintended expression")
    for side in ("L", "R"):
        eye_min = v[f"ID_EYE_SURROUND_WIDTH_MIN_{side}"]
        eye_max = v[f"ID_EYE_SURROUND_WIDTH_MAX_{side}"]
        if eye_max < eye_min:
            raise IndustrialDesignContractError(f"{side} eye surround evidence has max width below min width")
        if eye_max - eye_min > limits.max_eye_surround_width_range_mm:
            raise IndustrialDesignContractError(f"{side} eye surround has excessive local width variation and reads as a goggle rim")
    if abs(v["ID_EYE_SURROUND_WIDTH_MIN_L"] - v["ID_EYE_SURROUND_WIDTH_MIN_R"]) > limits.max_eye_surround_width_asymmetry_mm or abs(v["ID_EYE_SURROUND_WIDTH_MAX_L"] - v["ID_EYE_SURROUND_WIDTH_MAX_R"]) > limits.max_eye_surround_width_asymmetry_mm:
        raise IndustrialDesignContractError("eye surround width asymmetry creates unintended facial expression")
    if v["ID_NOSE_PROJECTION_ABOVE_FIELD"] > limits.max_nose_projection_above_field_mm:
        raise IndustrialDesignContractError("nose bridge reads as a protruding cone rather than part of the facial field")


def validate_surface_boundary(surface_class: str, positional_gap_mm: float, tangent_discontinuity_deg: float,
                              limits: IDLimits = IDLimits()) -> None:
    """Validate intended-continuous A/B appearance boundaries."""
    gap = _finite_nonnegative("positional_gap_mm", positional_gap_mm)
    tangent = _finite_nonnegative("tangent_discontinuity_deg", tangent_discontinuity_deg)
    cls = surface_class.upper()
    if cls == "A":
        max_gap, max_tangent = limits.max_a_surface_gap_mm, limits.max_a_surface_tangent_deg
    elif cls == "B":
        max_gap, max_tangent = limits.max_b_surface_gap_mm, limits.max_b_surface_tangent_deg
    else:
        raise IndustrialDesignContractError("surface_class must be A or B for appearance-boundary QA")
    if gap > max_gap or tangent > max_tangent:
        raise IndustrialDesignContractError(
            f"{cls}-surface continuity failed: gap={gap:.3f} mm, tangent={tangent:.3f} deg; limits={max_gap:.3f} mm/{max_tangent:.3f} deg"
        )
