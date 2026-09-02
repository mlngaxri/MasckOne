"""Prototype physical-ID gates for bathroom-counter rest geometry.

The product must look complete off-face without resting on the compliant facial seal,
wet service apertures, controls or charging interface. These are CAD convergence
criteria only, not validated tip-stability, hygiene or ingress claims.
"""
from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class CounterRestLimits:
    min_support_span_mm: float = 38.0
    min_support_depth_mm: float = 12.0
    min_sensitive_surface_clearance_mm: float = 2.0
    min_rocking_margin_deg: float = 8.0
    max_support_height_mismatch_mm: float = 0.6


REQUIRED_MEASUREMENTS = (
    "ID_COUNTER_SUPPORT_SPAN_MM",
    "ID_COUNTER_SUPPORT_DEPTH_MM",
    "ID_COUNTER_FACE_SEAL_CLEARANCE_MM",
    "ID_COUNTER_SERVICE_CLEARANCE_MM",
    "ID_COUNTER_HMI_CLEARANCE_MM",
    "ID_COUNTER_CHARGE_CLEARANCE_MM",
    "ID_COUNTER_ROCKING_MARGIN_DEG",
    "ID_COUNTER_SUPPORT_HEIGHT_MISMATCH_MM",
)


class CounterRestContractError(ValueError):
    """Raised when released counter-rest evidence violates the prototype contract."""


def _finite_nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value < 0:
        raise CounterRestContractError(f"{name} must be finite and >= 0")
    return value


def validate_counter_rest(values: Mapping[str, float], limits: CounterRestLimits = CounterRestLimits()) -> None:
    """Fail closed on unstable or contamination-prone off-face rest geometry."""
    missing = sorted(set(REQUIRED_MEASUREMENTS) - set(values))
    if missing:
        raise CounterRestContractError("missing stable counter-rest measurements: " + ", ".join(missing))
    v = {name: _finite_nonnegative(name, values[name]) for name in REQUIRED_MEASUREMENTS}

    if v["ID_COUNTER_SUPPORT_SPAN_MM"] < limits.min_support_span_mm:
        raise CounterRestContractError("counter support span is too narrow for the prototype rest target")
    if v["ID_COUNTER_SUPPORT_DEPTH_MM"] < limits.min_support_depth_mm:
        raise CounterRestContractError("counter support depth is too short for the prototype rest target")
    for name in (
        "ID_COUNTER_FACE_SEAL_CLEARANCE_MM",
        "ID_COUNTER_SERVICE_CLEARANCE_MM",
        "ID_COUNTER_HMI_CLEARANCE_MM",
        "ID_COUNTER_CHARGE_CLEARANCE_MM",
    ):
        if v[name] < limits.min_sensitive_surface_clearance_mm:
            raise CounterRestContractError(f"{name} permits a sensitive surface to contact the counter")
    if v["ID_COUNTER_ROCKING_MARGIN_DEG"] < limits.min_rocking_margin_deg:
        raise CounterRestContractError("counter-rest rocking margin is below the prototype target")
    if v["ID_COUNTER_SUPPORT_HEIGHT_MISMATCH_MM"] > limits.max_support_height_mismatch_mm:
        raise CounterRestContractError("counter support height mismatch permits visible rocking or uneven stance")
