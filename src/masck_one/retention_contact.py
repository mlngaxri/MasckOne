"""Retention contact-reaction sensitivity model.

This module closes a gap left by the vertical-load ledger: the horizontal force
couple required to react anterior CG pitch moment also loads the crown and
occipital contact structures. Results are analytical sensitivity outputs, not
human comfort evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isfinite


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be an exact numeric scalar")
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


@dataclass(frozen=True)
class ContactReactionInputs:
    crown_vertical_n: float
    occipital_vertical_n: float
    pitch_balance_force_n: float
    crown_contact_area_mm2: float
    occipital_contact_area_mm2: float

    def validate(self) -> None:
        for label, value in self.__dict__.items():
            _finite(value, label)
        if self.crown_vertical_n < 0 or self.occipital_vertical_n < 0:
            raise ValueError("vertical support reactions must be non-negative")
        if self.pitch_balance_force_n < 0:
            raise ValueError("pitch balance force magnitude must be non-negative")
        if self.crown_contact_area_mm2 <= 0 or self.occipital_contact_area_mm2 <= 0:
            raise ValueError("contact areas must be positive")


@dataclass(frozen=True)
class ContactReactionResult:
    crown_resultant_n: float
    occipital_resultant_n: float
    crown_nominal_pressure_kpa: float
    occipital_nominal_pressure_kpa: float
    evidence_status: str = "DIGITAL_SENSITIVITY_ONLY"


def evaluate_contact_reactions(p: ContactReactionInputs) -> ContactReactionResult:
    """Resolve the pitch couple into each support's total contact reaction.

    The pitch couple is represented by equal and opposite horizontal reactions
    at crown and occipital supports. Each contact therefore sees the full couple
    force magnitude in addition to its assigned vertical support load.

    Pressure is resultant/contact-area only. It is deliberately named nominal:
    it cannot predict local pressure peaks, edge loading, soft-tissue response,
    strap curvature or comfort.
    """
    p.validate()
    crown_r = hypot(p.crown_vertical_n, p.pitch_balance_force_n)
    occ_r = hypot(p.occipital_vertical_n, p.pitch_balance_force_n)
    # 1 N/mm^2 = 1000 kPa
    crown_p = crown_r / p.crown_contact_area_mm2 * 1000.0
    occ_p = occ_r / p.occipital_contact_area_mm2 * 1000.0
    return ContactReactionResult(crown_r, occ_r, crown_p, occ_p)


def minimum_contact_area_mm2(reaction_n: float, nominal_pressure_limit_kpa: float) -> float:
    """Area required to stay below a controlled nominal-pressure sensitivity gate."""
    reaction = _finite(reaction_n, "reaction_n")
    limit = _finite(nominal_pressure_limit_kpa, "nominal_pressure_limit_kpa")
    if reaction < 0:
        raise ValueError("reaction_n must be non-negative")
    if limit <= 0:
        raise ValueError("nominal_pressure_limit_kpa must be positive")
    return reaction * 1000.0 / limit
