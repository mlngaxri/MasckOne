"""Retention preload adjustment-window screening for Masck One.

The crown/occipital retention system must accommodate head-size and donning variation
without silently converting dimensional mismatch into facial preload. This module
screens an adjustable compliant retention member against a required tension corridor.
Outputs are digital sensitivity evidence only, not fit or comfort validation.
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
class PreloadWindowResult:
    worst_short_tension_n: float
    worst_long_tension_n: float
    required_adjustment_span_mm: float
    available_adjustment_span_mm: float
    low_tension_margin_n: float
    high_tension_margin_n: float
    adjustment_margin_mm: float
    preload_window_ok: bool
    evidence_status: str = "DIGITAL_SENSITIVITY_ONLY"


def evaluate_preload_window(
    *,
    nominal_path_length_mm: float,
    path_length_variation_mm: float,
    adjustment_travel_each_side_mm: float,
    member_stiffness_n_per_mm: float,
    nominal_tension_n: float,
    minimum_tension_n: float,
    maximum_tension_n: float,
    assembly_length_uncertainty_mm: float = 0.0,
    stiffness_uncertainty_fraction: float = 0.0,
) -> PreloadWindowResult:
    """Bound the tension and adjustment travel of one retention member.

    ``path_length_variation_mm`` is the full shortest-to-longest anatomical/donning
    path range around the nominal fit. Adjustment is assumed symmetric about nominal.
    Assembly length uncertainty consumes travel and creates additional extension.
    Stiffness uncertainty is applied adversarially: low stiffness for minimum-tension
    closure and high stiffness for maximum-tension closure.
    """
    length = _finite(nominal_path_length_mm, "nominal_path_length_mm")
    variation = _finite(path_length_variation_mm, "path_length_variation_mm")
    travel = _finite(adjustment_travel_each_side_mm, "adjustment_travel_each_side_mm")
    stiffness = _finite(member_stiffness_n_per_mm, "member_stiffness_n_per_mm")
    nominal_tension = _finite(nominal_tension_n, "nominal_tension_n")
    min_tension = _finite(minimum_tension_n, "minimum_tension_n")
    max_tension = _finite(maximum_tension_n, "maximum_tension_n")
    assembly_unc = _finite(assembly_length_uncertainty_mm, "assembly_length_uncertainty_mm")
    stiffness_unc = _finite(stiffness_uncertainty_fraction, "stiffness_uncertainty_fraction")

    if length <= 0 or stiffness <= 0:
        raise ValueError("nominal path length and stiffness must be positive")
    if variation < 0 or travel < 0 or nominal_tension < 0 or min_tension < 0 or max_tension < 0 or assembly_unc < 0:
        raise ValueError("variation, travel, tensions, and assembly uncertainty must be non-negative")
    if min_tension > max_tension:
        raise ValueError("minimum tension cannot exceed maximum tension")
    if not 0 <= stiffness_unc < 1:
        raise ValueError("stiffness uncertainty must be in [0, 1)")

    half_variation = variation / 2.0
    required_each_side = half_variation + assembly_unc
    required_span = 2.0 * required_each_side
    available_span = 2.0 * travel

    uncompensated = max(0.0, required_each_side - travel)
    k_low = stiffness * (1.0 - stiffness_unc)
    k_high = stiffness * (1.0 + stiffness_unc)

    worst_short = max(0.0, nominal_tension - k_low * uncompensated)
    worst_long = nominal_tension + k_high * uncompensated
    low_margin = worst_short - min_tension
    high_margin = max_tension - worst_long
    adjustment_margin = available_span - required_span

    return PreloadWindowResult(
        worst_short_tension_n=worst_short,
        worst_long_tension_n=worst_long,
        required_adjustment_span_mm=required_span,
        available_adjustment_span_mm=available_span,
        low_tension_margin_n=low_margin,
        high_tension_margin_n=high_margin,
        adjustment_margin_mm=adjustment_margin,
        preload_window_ok=(adjustment_margin >= 0 and low_margin >= 0 and high_margin >= 0),
    )
