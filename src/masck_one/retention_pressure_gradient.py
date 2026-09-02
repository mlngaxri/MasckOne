"""Pressure nonuniformity screening for Masck One retention contacts.

Average contact pressure can hide severe edge loading. This module provides a
bounded analytical screen using a linear pressure field across a rectangular
contact footprint. It is not a comfort model and does not replace pressure-film
or instrumented-headform measurements.
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
class PressureGradientInputs:
    normal_force_n: float
    overturning_moment_nmm: float
    contact_width_mm: float
    contact_length_mm: float

    def validate(self) -> None:
        force = _finite(self.normal_force_n, "normal_force_n")
        _finite(self.overturning_moment_nmm, "overturning_moment_nmm")
        width = _finite(self.contact_width_mm, "contact_width_mm")
        length = _finite(self.contact_length_mm, "contact_length_mm")
        if force < 0:
            raise ValueError("normal_force_n must be non-negative")
        if width <= 0 or length <= 0:
            raise ValueError("contact dimensions must be positive")


@dataclass(frozen=True)
class PressureGradientResult:
    average_pressure_kpa: float
    edge_pressure_low_kpa: float
    edge_pressure_high_kpa: float
    eccentricity_mm: float
    kern_half_width_mm: float
    full_contact_possible: bool
    evidence_status: str = "DIGITAL_SENSITIVITY_ONLY"


def evaluate_pressure_gradient(p: PressureGradientInputs) -> PressureGradientResult:
    """Screen edge pressure for moment about the contact-width centroidal axis.

    For a rectangular footprint with linear pressure distribution:
      p_avg = F / (b L)
      p_edge = p_avg * (1 +/- 6 e / b), e = M/F

    Full compressive contact is possible only while |e| <= b/6. Outside that
    middle-third kern, the linear full-contact assumption predicts tension at
    one edge, which a passive pad/head interface cannot sustain. Such a case is
    therefore flagged rather than silently reporting a physically impossible
    negative contact pressure.
    """
    p.validate()
    area = p.contact_width_mm * p.contact_length_mm
    average = p.normal_force_n / area * 1000.0
    if p.normal_force_n == 0:
        if p.overturning_moment_nmm != 0:
            return PressureGradientResult(0.0, 0.0, 0.0, float("inf"), p.contact_width_mm / 6.0, False)
        return PressureGradientResult(0.0, 0.0, 0.0, 0.0, p.contact_width_mm / 6.0, True)
    eccentricity = p.overturning_moment_nmm / p.normal_force_n
    kern = p.contact_width_mm / 6.0
    factor = 6.0 * eccentricity / p.contact_width_mm
    edge_a = average * (1.0 - factor)
    edge_b = average * (1.0 + factor)
    full = abs(eccentricity) <= kern
    return PressureGradientResult(
        average,
        min(edge_a, edge_b),
        max(edge_a, edge_b),
        eccentricity,
        kern,
        full,
    )
