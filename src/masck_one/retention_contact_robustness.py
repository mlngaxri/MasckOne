"""Tolerance-aware retention contact sensitivity for Masck One.

Nominal support reaction divided by nominal pad area can conceal an unfavorable
combination of load uncertainty and effective-area loss from curvature, edge lift,
hair, wet migration, or assembly variation. This module bounds that analytical
risk without converting it into a comfort claim.
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
class ContactRobustnessInputs:
    nominal_reaction_n: float
    reaction_uncertainty_n: float
    nominal_contact_area_mm2: float
    area_loss_fraction: float
    area_tolerance_mm2: float = 0.0

    def validate(self) -> None:
        reaction = _finite(self.nominal_reaction_n, "nominal_reaction_n")
        uncertainty = _finite(self.reaction_uncertainty_n, "reaction_uncertainty_n")
        area = _finite(self.nominal_contact_area_mm2, "nominal_contact_area_mm2")
        loss = _finite(self.area_loss_fraction, "area_loss_fraction")
        area_tol = _finite(self.area_tolerance_mm2, "area_tolerance_mm2")
        if reaction < 0 or uncertainty < 0:
            raise ValueError("reaction and reaction uncertainty must be non-negative")
        if area <= 0 or area_tol < 0:
            raise ValueError("contact area must be positive and area tolerance non-negative")
        if not 0.0 <= loss < 1.0:
            raise ValueError("area_loss_fraction must be in [0, 1)")
        if area * (1.0 - loss) - area_tol <= 0:
            raise ValueError("worst-case effective contact area must remain positive")


@dataclass(frozen=True)
class ContactRobustnessResult:
    worst_reaction_n: float
    worst_effective_area_mm2: float
    nominal_pressure_kpa: float
    worst_pressure_kpa: float
    pressure_amplification: float
    evidence_status: str = "DIGITAL_SENSITIVITY_ONLY"


def evaluate_contact_robustness(p: ContactRobustnessInputs) -> ContactRobustnessResult:
    """Conservatively combine bounded load growth and effective-area loss."""
    p.validate()
    worst_reaction = p.nominal_reaction_n + p.reaction_uncertainty_n
    effective_area = p.nominal_contact_area_mm2 * (1.0 - p.area_loss_fraction) - p.area_tolerance_mm2
    nominal_pressure = p.nominal_reaction_n / p.nominal_contact_area_mm2 * 1000.0
    worst_pressure = worst_reaction / effective_area * 1000.0
    amplification = worst_pressure / nominal_pressure if nominal_pressure > 0 else 1.0
    return ContactRobustnessResult(
        worst_reaction, effective_area, nominal_pressure, worst_pressure, amplification
    )


def required_nominal_area_mm2(
    worst_reaction_n: float,
    pressure_limit_kpa: float,
    area_loss_fraction: float,
    area_tolerance_mm2: float = 0.0,
) -> float:
    """Nominal area required after bounded fractional and absolute area losses."""
    reaction = _finite(worst_reaction_n, "worst_reaction_n")
    limit = _finite(pressure_limit_kpa, "pressure_limit_kpa")
    loss = _finite(area_loss_fraction, "area_loss_fraction")
    tol = _finite(area_tolerance_mm2, "area_tolerance_mm2")
    if reaction < 0 or limit <= 0 or tol < 0 or not 0.0 <= loss < 1.0:
        raise ValueError("invalid contact robustness sizing inputs")
    required_effective = reaction * 1000.0 / limit
    return (required_effective + tol) / (1.0 - loss)
