"""Executable brow and forehead-field industrial-design gates.

These checks prevent a mechanically valid upper facial field from collapsing into a
heavy visor shelf, angry brow, forehead plate, or asymmetric temple transition.
Measurements must come from stable named CAD evidence, not kernel face or edge indices.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class BrowForeheadLimits:
    max_brow_shelf_projection_mm: float = 1.5
    min_brow_to_forehead_blend_run_mm: float = 12.0
    min_forehead_to_temple_blend_run_mm: float = 14.0
    max_temple_depth_excursion_mm: float = 3.0
    max_brow_projection_asymmetry_mm: float = 0.6
    max_temple_run_asymmetry_mm: float = 1.5
    max_temple_depth_asymmetry_mm: float = 0.75


REQUIRED_MEASUREMENTS = (
    "ID_BROW_SHELF_PROJECTION_L",
    "ID_BROW_SHELF_PROJECTION_R",
    "ID_BROW_TO_FOREHEAD_BLEND_RUN_L",
    "ID_BROW_TO_FOREHEAD_BLEND_RUN_R",
    "ID_FOREHEAD_TO_TEMPLE_BLEND_RUN_L",
    "ID_FOREHEAD_TO_TEMPLE_BLEND_RUN_R",
    "ID_TEMPLE_DEPTH_EXCURSION_L",
    "ID_TEMPLE_DEPTH_EXCURSION_R",
)


class BrowForeheadContractError(ValueError):
    """Raised when upper-face geometry violates the brow/forehead contract."""


def _nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise BrowForeheadContractError(f"{name} must be finite")
    if value < 0:
        raise BrowForeheadContractError(f"{name} must be >= 0")
    return value


def validate_brow_forehead(
    values: Mapping[str, float], limits: BrowForeheadLimits = BrowForeheadLimits()
) -> None:
    """Fail closed on visor-like, angry, plate-like or asymmetric upper-face geometry."""
    missing = sorted(set(REQUIRED_MEASUREMENTS) - set(values))
    if missing:
        raise BrowForeheadContractError(
            "missing stable brow/forehead measurements: " + ", ".join(missing)
        )
    v = {name: _nonnegative(name, values[name]) for name in REQUIRED_MEASUREMENTS}

    for side in ("L", "R"):
        if v[f"ID_BROW_SHELF_PROJECTION_{side}"] > limits.max_brow_shelf_projection_mm:
            raise BrowForeheadContractError(
                f"{side} brow projects as a visor shelf and creates an aggressive eye expression"
            )
        if v[f"ID_BROW_TO_FOREHEAD_BLEND_RUN_{side}"] < limits.min_brow_to_forehead_blend_run_mm:
            raise BrowForeheadContractError(
                f"{side} brow-to-forehead transition is too abrupt for a calm continuous facial field"
            )
        if v[f"ID_FOREHEAD_TO_TEMPLE_BLEND_RUN_{side}"] < limits.min_forehead_to_temple_blend_run_mm:
            raise BrowForeheadContractError(
                f"{side} forehead-to-temple transition is too short and reads as attached side hardware"
            )
        if v[f"ID_TEMPLE_DEPTH_EXCURSION_{side}"] > limits.max_temple_depth_excursion_mm:
            raise BrowForeheadContractError(
                f"{side} temple transition has excessive local depth and reads as a temple pod"
            )

    if abs(v["ID_BROW_SHELF_PROJECTION_L"] - v["ID_BROW_SHELF_PROJECTION_R"]) > limits.max_brow_projection_asymmetry_mm:
        raise BrowForeheadContractError("brow projection asymmetry creates unintended facial expression")
    if abs(v["ID_FOREHEAD_TO_TEMPLE_BLEND_RUN_L"] - v["ID_FOREHEAD_TO_TEMPLE_BLEND_RUN_R"]) > limits.max_temple_run_asymmetry_mm:
        raise BrowForeheadContractError("temple blend-run asymmetry creates uneven upper-face visual mass")
    if abs(v["ID_TEMPLE_DEPTH_EXCURSION_L"] - v["ID_TEMPLE_DEPTH_EXCURSION_R"]) > limits.max_temple_depth_asymmetry_mm:
        raise BrowForeheadContractError("temple depth asymmetry creates uneven side-hardware integration")
