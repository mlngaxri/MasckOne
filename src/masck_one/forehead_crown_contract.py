"""Executable upper-perimeter industrial-design gates.

These checks keep the forehead crown visually calm and complete instead of allowing a
mechanically valid shell to terminate as a helmet brow, flat plate, central horn, or
uneven scallop. Measurements must come from stable named CAD evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class ForeheadCrownLimits:
    min_crown_blend_span_mm: float = 36.0
    max_crown_local_rise_mm: float = 2.5
    max_upper_edge_height_mismatch_mm: float = 0.75
    max_crown_slope_break_deg: float = 8.0


REQUIRED_MEASUREMENTS = (
    "ID_FOREHEAD_CROWN_BLEND_SPAN",
    "ID_FOREHEAD_CROWN_LOCAL_RISE",
    "ID_UPPER_EDGE_HEIGHT_L",
    "ID_UPPER_EDGE_HEIGHT_R",
    "ID_FOREHEAD_CROWN_MAX_SLOPE_BREAK_DEG",
)


class ForeheadCrownContractError(ValueError):
    """Raised when the upper silhouette violates the forehead-crown contract."""


def _nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise ForeheadCrownContractError(f"{name} must be finite")
    if value < 0:
        raise ForeheadCrownContractError(f"{name} must be >= 0")
    return value


def validate_forehead_crown(
    values: Mapping[str, float], limits: ForeheadCrownLimits = ForeheadCrownLimits()
) -> None:
    """Fail closed on plate-like, peaked, scalloped, or asymmetric upper silhouettes."""
    missing = sorted(set(REQUIRED_MEASUREMENTS) - set(values))
    if missing:
        raise ForeheadCrownContractError(
            "missing stable forehead-crown measurements: " + ", ".join(missing)
        )
    v = {name: _nonnegative(name, values[name]) for name in REQUIRED_MEASUREMENTS}

    if v["ID_FOREHEAD_CROWN_BLEND_SPAN"] < limits.min_crown_blend_span_mm:
        raise ForeheadCrownContractError(
            "forehead crown transition is too narrow and reads as a central horn or helmet feature"
        )
    if v["ID_FOREHEAD_CROWN_LOCAL_RISE"] > limits.max_crown_local_rise_mm:
        raise ForeheadCrownContractError(
            "forehead crown rise is too pronounced for a calm low-mass upper silhouette"
        )
    if abs(v["ID_UPPER_EDGE_HEIGHT_L"] - v["ID_UPPER_EDGE_HEIGHT_R"]) > limits.max_upper_edge_height_mismatch_mm:
        raise ForeheadCrownContractError(
            "upper-edge height mismatch creates a visibly tilted or scalloped forehead termination"
        )
    if v["ID_FOREHEAD_CROWN_MAX_SLOPE_BREAK_DEG"] > limits.max_crown_slope_break_deg:
        raise ForeheadCrownContractError(
            "forehead crown contains an abrupt slope break instead of an authored broad transition"
        )
