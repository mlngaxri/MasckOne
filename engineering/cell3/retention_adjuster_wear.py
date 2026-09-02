"""Wear-drift sensitivity gate for the Masck One physical retention adjuster.

This model keeps initial adjuster qualification separate from durability. It screens
whether measured or bounded wear can consume fit-range, tension-resolution, or
anti-backdrive margin. Outputs are engineering sensitivity only, not comfort or life
claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be an exact numeric scalar")
    out = float(value)
    if not isfinite(out):
        raise ValueError(f"{label} must be finite")
    return out


@dataclass(frozen=True)
class RetentionAdjusterWearResult:
    worn_increment_mm: float
    worn_reachable_travel_mm: float
    travel_margin_mm: float
    max_tension_quantization_error_n: float
    worn_backdrive_capacity_n: float
    required_backdrive_capacity_n: float
    travel_ok: bool
    resolution_ok: bool
    backdrive_ok: bool
    screening_closed: bool
    evidence_status: str


def evaluate_adjuster_wear(
    *,
    initial_reachable_travel_mm: float,
    required_travel_mm: float,
    initial_increment_mm: float,
    increment_growth_mm: float,
    endpoint_position_loss_mm: float,
    retention_stiffness_n_per_mm: float,
    max_tension_error_n: float,
    initial_backdrive_capacity_n: float,
    backdrive_capacity_loss_n: float,
    max_service_tension_n: float,
    service_tension_uncertainty_n: float = 0.0,
    required_backdrive_margin_n: float = 0.0,
) -> RetentionAdjusterWearResult:
    values = {
        name: _finite(value, name)
        for name, value in locals().items()
        if name != "values"
    }
    if any(v < 0 for v in values.values()):
        raise ValueError("adjuster wear inputs must be non-negative")
    if values["initial_increment_mm"] <= 0:
        raise ValueError("initial_increment_mm must be positive")

    worn_increment = values["initial_increment_mm"] + values["increment_growth_mm"]
    worn_reachable = max(0.0, values["initial_reachable_travel_mm"] - values["endpoint_position_loss_mm"])
    travel_margin = worn_reachable - values["required_travel_mm"]

    # Half a stable-position increment is the worst residual fit quantization.
    tension_error = 0.5 * worn_increment * values["retention_stiffness_n_per_mm"]

    worn_backdrive = max(0.0, values["initial_backdrive_capacity_n"] - values["backdrive_capacity_loss_n"])
    required_backdrive = (
        values["max_service_tension_n"]
        + values["service_tension_uncertainty_n"]
        + values["required_backdrive_margin_n"]
    )

    travel_ok = travel_margin >= 0
    resolution_ok = tension_error <= values["max_tension_error_n"]
    backdrive_ok = worn_backdrive >= required_backdrive
    closed = travel_ok and resolution_ok and backdrive_ok
    return RetentionAdjusterWearResult(
        worn_increment,
        worn_reachable,
        travel_margin,
        tension_error,
        worn_backdrive,
        required_backdrive,
        travel_ok,
        resolution_ok,
        backdrive_ok,
        closed,
        "DIGITAL_SENSITIVITY_ONLY" if closed else "PHYSICAL_TEST_REQUIRED",
    )
