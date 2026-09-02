"""Prototype human-factors gates for retention-path hair and pinch geometry.

These checks prevent visually integrated retention and quick-release hardware from
creating narrow exposed capture gaps or under-radiused skin/hair-facing edges.
They are CAD convergence criteria, not validated pinch-safety or hair-snag claims.
"""
from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class RetentionHairPinchLimits:
    min_exposed_gap_mm: float = 4.0
    min_skin_facing_edge_radius_mm: float = 1.0
    min_hair_sweep_radius_mm: float = 1.5
    max_bilateral_gap_mismatch_mm: float = 1.0


REQUIRED_MEASUREMENTS = (
    "HF_RETENTION_EXPOSED_GAP_L",
    "HF_RETENTION_EXPOSED_GAP_R",
    "HF_RETENTION_SKIN_EDGE_RADIUS_L",
    "HF_RETENTION_SKIN_EDGE_RADIUS_R",
    "HF_RETENTION_HAIR_SWEEP_RADIUS_L",
    "HF_RETENTION_HAIR_SWEEP_RADIUS_R",
)


class RetentionHairPinchContractError(ValueError):
    """Raised when released retention CAD evidence violates the prototype contract."""


def _finite_nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value < 0:
        raise RetentionHairPinchContractError(f"{name} must be finite and >= 0")
    return value


def validate_retention_hair_pinch(values: Mapping[str, float], limits: RetentionHairPinchLimits = RetentionHairPinchLimits()) -> None:
    """Fail closed on absent or capture-prone retention geometry evidence."""
    missing = sorted(set(REQUIRED_MEASUREMENTS) - set(values))
    if missing:
        raise RetentionHairPinchContractError("missing stable retention hair/pinch measurements: " + ", ".join(missing))
    v = {name: _finite_nonnegative(name, values[name]) for name in REQUIRED_MEASUREMENTS}

    for side in ("L", "R"):
        if v[f"HF_RETENTION_EXPOSED_GAP_{side}"] < limits.min_exposed_gap_mm:
            raise RetentionHairPinchContractError(f"{side} retention gap is too narrow for the prototype anti-capture target")
        if v[f"HF_RETENTION_SKIN_EDGE_RADIUS_{side}"] < limits.min_skin_facing_edge_radius_mm:
            raise RetentionHairPinchContractError(f"{side} skin-facing retention edge is too sharp")
        if v[f"HF_RETENTION_HAIR_SWEEP_RADIUS_{side}"] < limits.min_hair_sweep_radius_mm:
            raise RetentionHairPinchContractError(f"{side} retention transition is too abrupt at the hair sweep")

    if abs(v["HF_RETENTION_EXPOSED_GAP_L"] - v["HF_RETENTION_EXPOSED_GAP_R"]) > limits.max_bilateral_gap_mismatch_mm:
        raise RetentionHairPinchContractError("bilateral exposed-gap mismatch creates inconsistent retention capture geometry")
