"""Physical retention-adjuster screening for Masck One.

Screens whether a discrete mechanical adjuster can realize a required path length
without excessive quantization error or backdriving under retention load. Outputs
are digital sensitivity evidence only, not fit, comfort, durability, or usability
validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be an exact numeric scalar")
    out = float(value)
    if not isfinite(out):
        raise ValueError(f"{label} must be finite")
    return out


@dataclass(frozen=True)
class AdjusterResult:
    usable_travel_mm: float
    required_positions: int
    maximum_quantization_error_mm: float
    maximum_quantization_tension_error_n: float
    retention_margin_n: float
    travel_margin_mm: float
    resolution_ok: bool
    retention_ok: bool
    adjuster_ok: bool
    evidence_status: str = "DIGITAL_SENSITIVITY_ONLY"


def evaluate_retention_adjuster(
    *,
    required_adjustment_span_mm: float,
    nominal_travel_mm: float,
    end_stop_uncertainty_mm: float,
    position_increment_mm: float,
    member_stiffness_n_per_mm: float,
    maximum_allowed_tension_error_n: float,
    minimum_backdrive_load_n: float,
    maximum_service_tension_n: float,
    backdrive_load_uncertainty_n: float = 0.0,
    service_tension_uncertainty_n: float = 0.0,
) -> AdjusterResult:
    """Evaluate travel, discrete resolution, and conservative backdrive margin.

    End-stop uncertainty is removed from both ends of nominal travel. A discrete
    adjuster can leave at most half one position increment of path-length error.
    That error is converted to tension error using member stiffness. Backdrive
    capacity is reduced by its uncertainty while service demand is increased by
    its uncertainty. The calculation deliberately does not infer accidental-release,
    wear, wet-grip usability, ratchet fatigue, or human comfort.
    """
    required = _finite(required_adjustment_span_mm, "required_adjustment_span_mm")
    nominal = _finite(nominal_travel_mm, "nominal_travel_mm")
    stop_unc = _finite(end_stop_uncertainty_mm, "end_stop_uncertainty_mm")
    increment = _finite(position_increment_mm, "position_increment_mm")
    stiffness = _finite(member_stiffness_n_per_mm, "member_stiffness_n_per_mm")
    allowed_error = _finite(maximum_allowed_tension_error_n, "maximum_allowed_tension_error_n")
    backdrive = _finite(minimum_backdrive_load_n, "minimum_backdrive_load_n")
    service = _finite(maximum_service_tension_n, "maximum_service_tension_n")
    backdrive_unc = _finite(backdrive_load_uncertainty_n, "backdrive_load_uncertainty_n")
    service_unc = _finite(service_tension_uncertainty_n, "service_tension_uncertainty_n")

    if required < 0 or nominal < 0 or stop_unc < 0 or allowed_error < 0:
        raise ValueError("travel, stop uncertainty, and allowed error must be non-negative")
    if increment <= 0 or stiffness <= 0:
        raise ValueError("position increment and stiffness must be positive")
    if backdrive < 0 or service < 0 or backdrive_unc < 0 or service_unc < 0:
        raise ValueError("loads and load uncertainties must be non-negative")

    usable = max(0.0, nominal - 2.0 * stop_unc)
    quant_error = increment / 2.0
    tension_error = stiffness * quant_error
    conservative_capacity = max(0.0, backdrive - backdrive_unc)
    conservative_demand = service + service_unc
    retention_margin = conservative_capacity - conservative_demand
    travel_margin = usable - required
    positions = ceil(required / increment) + 1 if required > 0 else 1
    resolution_ok = tension_error <= allowed_error
    retention_ok = retention_margin >= 0
    adjuster_ok = travel_margin >= 0 and resolution_ok and retention_ok

    return AdjusterResult(
        usable_travel_mm=usable,
        required_positions=positions,
        maximum_quantization_error_mm=quant_error,
        maximum_quantization_tension_error_n=tension_error,
        retention_margin_n=retention_margin,
        travel_margin_mm=travel_margin,
        resolution_ok=resolution_ok,
        retention_ok=retention_ok,
        adjuster_ok=adjuster_ok,
    )
