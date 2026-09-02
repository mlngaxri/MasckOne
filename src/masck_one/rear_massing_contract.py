"""Executable rear-massing industrial-design gates.

These checks prevent packaging and service volumes from producing a backpack-like rear
body, isolated service hump, or bilateral rear imbalance. Evidence must come from stable
named CAD measurements rather than kernel face or edge indices.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class RearMassingLimits:
    max_rear_depth_mm: float = 30.0
    max_local_service_bulge_mm: float = 3.0
    min_service_blend_run_mm: float = 14.0
    max_bilateral_depth_mismatch_mm: float = 1.0


REQUIRED_MEASUREMENTS = (
    "ID_REAR_DEPTH_L",
    "ID_REAR_DEPTH_R",
    "ID_REAR_SERVICE_BULGE_L",
    "ID_REAR_SERVICE_BULGE_R",
    "ID_REAR_SERVICE_BLEND_RUN_L",
    "ID_REAR_SERVICE_BLEND_RUN_R",
)


class RearMassingContractError(ValueError):
    """Raised when rear packaging violates the restrained-massing contract."""


def _nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise RearMassingContractError(f"{name} must be finite")
    if value < 0:
        raise RearMassingContractError(f"{name} must be >= 0")
    return value


def validate_rear_massing(
    values: Mapping[str, float],
    limits: RearMassingLimits = RearMassingLimits(),
) -> None:
    """Fail closed on backpack depth, service humps, and rear bilateral imbalance."""
    missing = sorted(set(REQUIRED_MEASUREMENTS) - set(values))
    if missing:
        raise RearMassingContractError(
            "missing stable rear-massing measurements: " + ", ".join(missing)
        )
    v = {name: _nonnegative(name, values[name]) for name in REQUIRED_MEASUREMENTS}

    for side in ("L", "R"):
        if v[f"ID_REAR_DEPTH_{side}"] > limits.max_rear_depth_mm:
            raise RearMassingContractError(
                f"rear depth {side} is too large and reads as backpack-like mass"
            )
        if v[f"ID_REAR_SERVICE_BULGE_{side}"] > limits.max_local_service_bulge_mm:
            raise RearMassingContractError(
                f"rear service volume {side} forms an isolated local hump"
            )
        if v[f"ID_REAR_SERVICE_BLEND_RUN_{side}"] < limits.min_service_blend_run_mm:
            raise RearMassingContractError(
                f"rear service volume {side} lacks sufficient authored blend run"
            )

    if abs(v["ID_REAR_DEPTH_L"] - v["ID_REAR_DEPTH_R"]) > limits.max_bilateral_depth_mismatch_mm:
        raise RearMassingContractError("bilateral rear depth is visually imbalanced")
