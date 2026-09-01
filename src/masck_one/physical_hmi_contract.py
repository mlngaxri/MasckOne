"""Prototype physical-HMI convergence gates for Masck One.

These checks prevent the CLEAN and secondary controls from becoming visually or
tactually ambiguous, reduce accidental wet-hand actuation risk, and keep mode/status
feedback legible without app dependence. They are CAD/prototype hypotheses, not
validated accessibility, usability, or accidental-activation claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class PhysicalHMILimits:
    min_primary_secondary_height_delta_mm: float = 0.35
    min_primary_tactile_feature_mm: float = 0.50
    min_secondary_tactile_feature_mm: float = 0.35
    min_status_window_minor_axis_mm: float = 2.0
    max_status_window_recess_mm: float = 0.60
    min_status_window_edge_radius_mm: float = 0.50
    min_control_to_service_separation_mm: float = 6.0
    min_control_center_spacing_mm: float = 10.0
    min_secondary_guard_offset_mm: float = 0.50
    max_secondary_guard_offset_mm: float = 1.50
    min_control_edge_radius_mm: float = 0.60
    min_secondary_guard_root_radius_mm: float = 0.75


REQUIRED_MEASUREMENTS = (
    "HMI_PRIMARY_HEIGHT_MM",
    "HMI_SECONDARY_HEIGHT_MM",
    "HMI_PRIMARY_TACTILE_FEATURE_MM",
    "HMI_SECONDARY_TACTILE_FEATURE_MM",
    "HMI_STATUS_WINDOW_MINOR_AXIS_MM",
    "HMI_STATUS_WINDOW_RECESS_MM",
    "HMI_STATUS_WINDOW_EDGE_RADIUS_MM",
    "HMI_CONTROL_TO_SERVICE_SEPARATION_MM",
    "HMI_CONTROL_CENTER_SPACING_MM",
    "HMI_SECONDARY_GUARD_OFFSET_MM",
    "HMI_PRIMARY_EDGE_RADIUS_MM",
    "HMI_SECONDARY_EDGE_RADIUS_MM",
    "HMI_SECONDARY_GUARD_ROOT_RADIUS_MM",
)


class PhysicalHMIContractError(ValueError):
    pass


def _finite_nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value < 0:
        raise PhysicalHMIContractError(f"{name} must be finite and >= 0")
    return value


def validate_measurements(values: Mapping[str, float], limits: PhysicalHMILimits = PhysicalHMILimits()) -> None:
    missing = sorted(set(REQUIRED_MEASUREMENTS) - set(values))
    if missing:
        raise PhysicalHMIContractError("missing stable physical-HMI measurements: " + ", ".join(missing))
    v = {name: _finite_nonnegative(name, values[name]) for name in REQUIRED_MEASUREMENTS}

    if v["HMI_PRIMARY_HEIGHT_MM"] - v["HMI_SECONDARY_HEIGHT_MM"] < limits.min_primary_secondary_height_delta_mm:
        raise PhysicalHMIContractError("primary CLEAN control lacks tactile hierarchy over secondary control")
    if v["HMI_PRIMARY_TACTILE_FEATURE_MM"] < limits.min_primary_tactile_feature_mm:
        raise PhysicalHMIContractError("primary CLEAN control tactile feature is too weak for eyes-free differentiation")
    if v["HMI_SECONDARY_TACTILE_FEATURE_MM"] < limits.min_secondary_tactile_feature_mm:
        raise PhysicalHMIContractError("secondary control tactile feature is too weak for eyes-free differentiation")
    if v["HMI_STATUS_WINDOW_MINOR_AXIS_MM"] < limits.min_status_window_minor_axis_mm:
        raise PhysicalHMIContractError("physical status window is too small for prototype state legibility")
    if v["HMI_STATUS_WINDOW_RECESS_MM"] > limits.max_status_window_recess_mm:
        raise PhysicalHMIContractError("status window recess creates an avoidable wet residue trap")
    if v["HMI_STATUS_WINDOW_EDGE_RADIUS_MM"] < limits.min_status_window_edge_radius_mm:
        raise PhysicalHMIContractError("status window edge is too sharp for wet exterior cleanability")
    if v["HMI_CONTROL_TO_SERVICE_SEPARATION_MM"] < limits.min_control_to_service_separation_mm:
        raise PhysicalHMIContractError("controls are too close to service actuation, increasing mode/service confusion")
    if v["HMI_CONTROL_CENTER_SPACING_MM"] < limits.min_control_center_spacing_mm:
        raise PhysicalHMIContractError("primary and secondary controls are too crowded for deliberate wet-hand targeting")
    guard = v["HMI_SECONDARY_GUARD_OFFSET_MM"]
    if guard < limits.min_secondary_guard_offset_mm:
        raise PhysicalHMIContractError("secondary control lacks enough local guarding against incidental contact")
    if guard > limits.max_secondary_guard_offset_mm:
        raise PhysicalHMIContractError("secondary-control guard is too proud and creates an avoidable snag/residue feature")
    if v["HMI_PRIMARY_EDGE_RADIUS_MM"] < limits.min_control_edge_radius_mm:
        raise PhysicalHMIContractError("primary CLEAN control edge is too sharp for comfortable wet-hand targeting and wiping")
    if v["HMI_SECONDARY_EDGE_RADIUS_MM"] < limits.min_control_edge_radius_mm:
        raise PhysicalHMIContractError("secondary control edge is too sharp for comfortable wet-hand targeting and wiping")
    if v["HMI_SECONDARY_GUARD_ROOT_RADIUS_MM"] < limits.min_secondary_guard_root_radius_mm:
        raise PhysicalHMIContractError("secondary-control guard root is too tight and creates a residue-prone crease")
