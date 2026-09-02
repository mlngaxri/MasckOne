"""Executable upper-side shoulder industrial-design gates.

These checks prevent an otherwise compliant crown and temple field from terminating in
helmet-like ears, abrupt side shoulders, or visually detached retention roots. Evidence
must come from stable named CAD measurements rather than kernel face or edge indices.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class UpperSideTransitionLimits:
    min_transition_run_mm: float = 16.0
    max_shoulder_projection_mm: float = 2.5
    max_projection_mismatch_mm: float = 0.75
    max_tangent_break_deg: float = 7.0


REQUIRED_MEASUREMENTS = (
    "ID_UPPER_SIDE_TRANSITION_RUN_L",
    "ID_UPPER_SIDE_TRANSITION_RUN_R",
    "ID_UPPER_SIDE_SHOULDER_PROJECTION_L",
    "ID_UPPER_SIDE_SHOULDER_PROJECTION_R",
    "ID_UPPER_SIDE_MAX_TANGENT_BREAK_DEG_L",
    "ID_UPPER_SIDE_MAX_TANGENT_BREAK_DEG_R",
)


class UpperSideTransitionContractError(ValueError):
    """Raised when crown-to-side geometry violates the calm shoulder contract."""


def _nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise UpperSideTransitionContractError(f"{name} must be finite")
    if value < 0:
        raise UpperSideTransitionContractError(f"{name} must be >= 0")
    return value


def validate_upper_side_transition(
    values: Mapping[str, float],
    limits: UpperSideTransitionLimits = UpperSideTransitionLimits(),
) -> None:
    """Fail closed on ear-like shoulders, abrupt side breaks, and bilateral imbalance."""
    missing = sorted(set(REQUIRED_MEASUREMENTS) - set(values))
    if missing:
        raise UpperSideTransitionContractError(
            "missing stable upper-side measurements: " + ", ".join(missing)
        )
    v = {name: _nonnegative(name, values[name]) for name in REQUIRED_MEASUREMENTS}

    for side in ("L", "R"):
        if v[f"ID_UPPER_SIDE_TRANSITION_RUN_{side}"] < limits.min_transition_run_mm:
            raise UpperSideTransitionContractError(
                f"upper-side transition {side} is too short and reads as an attached shoulder or ear"
            )
        if v[f"ID_UPPER_SIDE_SHOULDER_PROJECTION_{side}"] > limits.max_shoulder_projection_mm:
            raise UpperSideTransitionContractError(
                f"upper-side shoulder {side} projects too far from the authored facial field"
            )
        if v[f"ID_UPPER_SIDE_MAX_TANGENT_BREAK_DEG_{side}"] > limits.max_tangent_break_deg:
            raise UpperSideTransitionContractError(
                f"upper-side transition {side} contains an abrupt tangent break"
            )

    mismatch = abs(
        v["ID_UPPER_SIDE_SHOULDER_PROJECTION_L"]
        - v["ID_UPPER_SIDE_SHOULDER_PROJECTION_R"]
    )
    if mismatch > limits.max_projection_mismatch_mm:
        raise UpperSideTransitionContractError(
            "bilateral upper-side shoulder projection is visually imbalanced"
        )
