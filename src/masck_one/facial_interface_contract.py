"""Prototype geometry gates for the Masck One compliant facial interface.

These checks constrain geometry that can create hard pressure ridges, pinch-prone
edge terminations, or abrupt rigid-to-compliant visual transitions. They are
CAD convergence criteria, not validated comfort or fit claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class FacialInterfaceLimits:
    max_contact_edge_thickness_mm: float = 2.0
    min_pressure_transition_run_mm: float = 8.0
    max_pressure_transition_slope: float = 0.25
    min_rigid_edge_setback_mm: float = 3.0
    max_bilateral_transition_run_mismatch_mm: float = 2.0
    max_bilateral_edge_thickness_mismatch_mm: float = 0.5


REQUIRED_MEASUREMENTS = (
    "HF_CONTACT_EDGE_THICKNESS_L",
    "HF_CONTACT_EDGE_THICKNESS_R",
    "HF_PRESSURE_TRANSITION_RUN_L",
    "HF_PRESSURE_TRANSITION_RUN_R",
    "HF_PRESSURE_TRANSITION_RISE_L",
    "HF_PRESSURE_TRANSITION_RISE_R",
    "HF_RIGID_EDGE_SETBACK_L",
    "HF_RIGID_EDGE_SETBACK_R",
)


class FacialInterfaceContractError(ValueError):
    """Raised when released facial-interface CAD evidence violates the contract."""


def _finite_nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value < 0:
        raise FacialInterfaceContractError(f"{name} must be finite and >= 0")
    return value


def validate_facial_interface(values: Mapping[str, float], limits: FacialInterfaceLimits = FacialInterfaceLimits()) -> None:
    """Fail closed on absent or pressure-transition-degrading interface evidence."""
    missing = sorted(set(REQUIRED_MEASUREMENTS) - set(values))
    if missing:
        raise FacialInterfaceContractError("missing stable facial-interface measurements: " + ", ".join(missing))
    v = {name: _finite_nonnegative(name, values[name]) for name in REQUIRED_MEASUREMENTS}

    for side in ("L", "R"):
        edge = v[f"HF_CONTACT_EDGE_THICKNESS_{side}"]
        run = v[f"HF_PRESSURE_TRANSITION_RUN_{side}"]
        rise = v[f"HF_PRESSURE_TRANSITION_RISE_{side}"]
        setback = v[f"HF_RIGID_EDGE_SETBACK_{side}"]
        if edge > limits.max_contact_edge_thickness_mm:
            raise FacialInterfaceContractError(f"{side} contact edge is too thick for the low-ridge prototype target")
        if run < limits.min_pressure_transition_run_mm:
            raise FacialInterfaceContractError(f"{side} pressure transition is too short")
        if run <= 0 or rise / run > limits.max_pressure_transition_slope:
            raise FacialInterfaceContractError(f"{side} pressure transition is too abrupt")
        if setback < limits.min_rigid_edge_setback_mm:
            raise FacialInterfaceContractError(f"{side} rigid structure approaches the skin-contact edge too closely")

    if abs(v["HF_PRESSURE_TRANSITION_RUN_L"] - v["HF_PRESSURE_TRANSITION_RUN_R"]) > limits.max_bilateral_transition_run_mismatch_mm:
        raise FacialInterfaceContractError("bilateral pressure-transition run mismatch may create uneven facial loading")
    if abs(v["HF_CONTACT_EDGE_THICKNESS_L"] - v["HF_CONTACT_EDGE_THICKNESS_R"]) > limits.max_bilateral_edge_thickness_mismatch_mm:
        raise FacialInterfaceContractError("bilateral contact-edge thickness mismatch creates uneven interface geometry")
