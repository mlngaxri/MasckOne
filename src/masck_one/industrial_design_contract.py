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
    min_control_separation_mm: float = 2.0
    service_grip_depth_min_mm: float = 0.6
    service_grip_depth_max_mm: float = 1.2
    max_eye_aperture_angle_asymmetry_deg: float = 1.5
    max_eye_aperture_hostile_cant_deg: float = 4.0
    max_nose_projection_above_field_mm: float = 2.0
    max_rear_depth_fraction_of_front_field: float = 0.75


REQUIRED_MEASUREMENTS = (
    "ID_FRONT_FIELD_MAX_Z", "ID_REAR_MAX_Z",
    "ID_SIDE_TRANSITION_RUN_L", "ID_SIDE_TRANSITION_RUN_R",
    "ID_SIDE_TRANSITION_DEPTH_L", "ID_SIDE_TRANSITION_DEPTH_R",
    "ID_REAR_FRONTAL_OVERHANG_L", "ID_REAR_FRONTAL_OVERHANG_R",
    "ID_REAR_FRONTAL_OVERHANG_T", "ID_REAR_FRONTAL_OVERHANG_B",
    "ID_SERVICE_GRIP_DEPTH", "ID_CONTROL_TACTILE_LAND_CLEAN",
    "ID_CONTROL_TACTILE_LAND_SECONDARY", "ID_CONTROL_TACTILE_SEPARATION",
    "ID_EYE_APERTURE_CANT_L", "ID_EYE_APERTURE_CANT_R",
    "ID_NOSE_PROJECTION_ABOVE_FIELD",
)


class IndustrialDesignContractError(ValueError):
    """Raised when physical CAD evidence violates the ID contract."""


def _finite_nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value < 0:
        raise IndustrialDesignContractError(f"{name} must be finite and >= 0")
    return value


def validate_measurements(values: Mapping[str, float], limits: IDLimits = IDLimits()) -> None:
    """Fail closed on absent, malformed or packaging-degrading ID evidence."""
    missing = sorted(set(REQUIRED_MEASUREMENTS) - set(values))
    if missing:
        raise IndustrialDesignContractError("missing stable ID measurements: " + ", ".join(missing))
    v = {name: _finite_nonnegative(name, values[name]) for name in REQUIRED_MEASUREMENTS}

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

    grip = v["ID_SERVICE_GRIP_DEPTH"]
    if not limits.service_grip_depth_min_mm <= grip <= limits.service_grip_depth_max_mm:
        raise IndustrialDesignContractError("service grip depth is outside the wet-finger prototype exploration band")
    if v["ID_CONTROL_TACTILE_LAND_CLEAN"] < limits.min_primary_control_land_mm:
        raise IndustrialDesignContractError("CLEAN tactile land is below prototype discoverability target")
    if v["ID_CONTROL_TACTILE_SEPARATION"] < limits.min_control_separation_mm:
        raise IndustrialDesignContractError("adjacent physical controls lack tactile separation")

    cant_l, cant_r = v["ID_EYE_APERTURE_CANT_L"], v["ID_EYE_APERTURE_CANT_R"]
    if max(cant_l, cant_r) > limits.max_eye_aperture_hostile_cant_deg:
        raise IndustrialDesignContractError("eye aperture cant exceeds facial-neutrality target")
    if abs(cant_l - cant_r) > limits.max_eye_aperture_angle_asymmetry_deg:
        raise IndustrialDesignContractError("eye aperture asymmetry creates unintended expression")
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
