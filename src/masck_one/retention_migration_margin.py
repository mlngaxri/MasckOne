"""Retention migration margin screening for Masck One.

This module checks whether bounded tangential support demand remains below available
friction capacity at crown/occipital contacts. It is a sensitivity model only.
It does not establish comfort, fit, slip resistance, or human performance.
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
class MigrationMarginResult:
    available_friction_n: float
    required_tangential_n: float
    friction_margin_n: float
    utilization: float
    migration_resistance_ok: bool
    evidence_status: str = "DIGITAL_SENSITIVITY_ONLY"


def evaluate_migration_margin(
    *,
    normal_reaction_n: float,
    tangential_demand_n: float,
    friction_coefficient_lower_bound: float,
    normal_reaction_uncertainty_fraction: float = 0.0,
    tangential_demand_uncertainty_fraction: float = 0.0,
    minimum_margin_n: float = 0.0,
) -> MigrationMarginResult:
    """Conservative Coulomb-friction screen for one retention contact.

    Normal reaction is reduced by its bounded uncertainty while tangential demand is
    increased. A lower-bound friction coefficient must be supplied from an explicit
    conditioning assumption or measurement. Zero available friction with nonzero
    demand fails closed.
    """
    normal = _finite(normal_reaction_n, "normal_reaction_n")
    tangential = _finite(tangential_demand_n, "tangential_demand_n")
    mu = _finite(friction_coefficient_lower_bound, "friction_coefficient_lower_bound")
    n_unc = _finite(normal_reaction_uncertainty_fraction, "normal_reaction_uncertainty_fraction")
    t_unc = _finite(tangential_demand_uncertainty_fraction, "tangential_demand_uncertainty_fraction")
    min_margin = _finite(minimum_margin_n, "minimum_margin_n")

    if normal < 0 or tangential < 0 or mu < 0 or min_margin < 0:
        raise ValueError("loads, friction coefficient, and minimum margin must be non-negative")
    if not 0 <= n_unc < 1:
        raise ValueError("normal reaction uncertainty must be in [0, 1)")
    if t_unc < 0:
        raise ValueError("tangential demand uncertainty must be non-negative")

    conservative_normal = normal * (1.0 - n_unc)
    required = tangential * (1.0 + t_unc)
    available = mu * conservative_normal
    margin = available - required

    if available == 0.0:
        utilization = 0.0 if required == 0.0 else float("inf")
    else:
        utilization = required / available

    return MigrationMarginResult(
        available_friction_n=available,
        required_tangential_n=required,
        friction_margin_n=margin,
        utilization=utilization,
        migration_resistance_ok=margin >= min_margin,
    )
