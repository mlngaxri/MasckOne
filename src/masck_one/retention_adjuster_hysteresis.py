"""Physical retention-adjuster hysteresis and lost-motion screening for Masck One.

A discrete adjuster can satisfy static pitch, travel and backdrive checks yet still
produce direction-dependent fit because backlash, tooth clearance, cable seating or
compliant take-up consumes commanded motion after reversal. Outputs remain digital
sensitivity evidence only.
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
class AdjusterHysteresisResult:
    conservative_lost_motion_mm: float
    reversal_tension_deadband_n: float
    conservative_reachable_span_mm: float
    span_margin_mm: float
    lost_motion_ok: bool
    tension_deadband_ok: bool
    span_ok: bool
    hysteresis_ok: bool
    evidence_status: str = "DIGITAL_SENSITIVITY_ONLY"


def evaluate_adjuster_hysteresis(
    *,
    measured_lost_motion_mm: float,
    lost_motion_uncertainty_mm: float,
    maximum_allowed_lost_motion_mm: float,
    member_stiffness_n_per_mm: float,
    maximum_allowed_reversal_tension_deadband_n: float,
    reachable_discrete_span_mm: float,
    required_adjustment_span_mm: float,
) -> AdjusterHysteresisResult:
    """Gate reversal lost motion, resulting tension deadband and retained fit span.

    Lost-motion uncertainty is added adversarially. The conservative lost motion is
    charged against reachable discrete span because endpoint reach that exists only
    before a direction reversal is not robust fit coverage. The same lost motion is
    converted through retention-member stiffness into a reversal tension deadband.
    This is a screening model, not a comfort or lifetime-fit claim.
    """
    measured = _finite(measured_lost_motion_mm, "measured_lost_motion_mm")
    uncertainty = _finite(lost_motion_uncertainty_mm, "lost_motion_uncertainty_mm")
    allowed_motion = _finite(maximum_allowed_lost_motion_mm, "maximum_allowed_lost_motion_mm")
    stiffness = _finite(member_stiffness_n_per_mm, "member_stiffness_n_per_mm")
    allowed_deadband = _finite(
        maximum_allowed_reversal_tension_deadband_n,
        "maximum_allowed_reversal_tension_deadband_n",
    )
    reachable = _finite(reachable_discrete_span_mm, "reachable_discrete_span_mm")
    required = _finite(required_adjustment_span_mm, "required_adjustment_span_mm")

    if measured < 0 or uncertainty < 0 or allowed_motion < 0:
        raise ValueError("lost motion, uncertainty, and allowed lost motion must be non-negative")
    if stiffness <= 0:
        raise ValueError("member stiffness must be positive")
    if allowed_deadband < 0 or reachable < 0 or required < 0:
        raise ValueError("deadband limit and adjustment spans must be non-negative")

    conservative_lost_motion = measured + uncertainty
    tension_deadband = conservative_lost_motion * stiffness
    conservative_span = max(0.0, reachable - conservative_lost_motion)
    span_margin = conservative_span - required

    lost_motion_ok = conservative_lost_motion <= allowed_motion
    tension_deadband_ok = tension_deadband <= allowed_deadband
    span_ok = span_margin >= -1e-12

    return AdjusterHysteresisResult(
        conservative_lost_motion_mm=conservative_lost_motion,
        reversal_tension_deadband_n=tension_deadband,
        conservative_reachable_span_mm=conservative_span,
        span_margin_mm=span_margin,
        lost_motion_ok=lost_motion_ok,
        tension_deadband_ok=tension_deadband_ok,
        span_ok=span_ok,
        hysteresis_ok=lost_motion_ok and tension_deadband_ok and span_ok,
    )
