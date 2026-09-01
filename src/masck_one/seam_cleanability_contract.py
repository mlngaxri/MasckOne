"""Physical seam and residue-trap gates for Masck One appearance CAD.

These are prototype convergence controls. They do not assert tooling capability,
cleanability validation, ingress protection, or production seam quality.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


class SeamCleanabilityContractError(ValueError):
    """Raised when seam or cleanability evidence is absent or degrading."""


@dataclass(frozen=True)
class SeamCleanabilityLimits:
    primary_seam_gap_min_mm: float = 0.35
    primary_seam_gap_max_mm: float = 0.60
    max_primary_seam_gap_spread_mm: float = 0.15
    max_primary_seam_offset_from_turnover_mm: float = 2.0
    min_wet_exterior_trench_width_mm: float = 2.0
    min_wet_exterior_root_radius_mm: float = 0.75
    max_blind_trench_depth_width_ratio: float = 0.50


REQUIRED = (
    "ID_PRIMARY_SEAM_GAP_MIN",
    "ID_PRIMARY_SEAM_GAP_MAX",
    "ID_PRIMARY_SEAM_OFFSET_FROM_TURNOVER",
    "ID_WET_EXTERIOR_MIN_TRENCH_WIDTH",
    "ID_WET_EXTERIOR_MIN_ROOT_RADIUS",
    "ID_WET_EXTERIOR_MAX_BLIND_TRENCH_DEPTH",
)


def _nonnegative(name: str, raw: float) -> float:
    value = float(raw)
    if not isfinite(value) or value < 0:
        raise SeamCleanabilityContractError(f"{name} must be finite and >= 0")
    return value


def validate_seam_cleanability(values: Mapping[str, float], limits: SeamCleanabilityLimits = SeamCleanabilityLimits()) -> None:
    """Fail closed on wandering premium seams and hard-to-clean exterior traps."""
    missing = sorted(set(REQUIRED) - set(values))
    if missing:
        raise SeamCleanabilityContractError("missing seam/cleanability measurements: " + ", ".join(missing))
    v = {name: _nonnegative(name, values[name]) for name in REQUIRED}

    gap_min = v["ID_PRIMARY_SEAM_GAP_MIN"]
    gap_max = v["ID_PRIMARY_SEAM_GAP_MAX"]
    if gap_min > gap_max:
        raise SeamCleanabilityContractError("primary seam minimum exceeds maximum")
    if gap_min < limits.primary_seam_gap_min_mm or gap_max > limits.primary_seam_gap_max_mm:
        raise SeamCleanabilityContractError("primary seam escapes prototype premium-gap exploration band")
    if gap_max - gap_min > limits.max_primary_seam_gap_spread_mm:
        raise SeamCleanabilityContractError("primary seam gap variation is visually uncontrolled")
    if v["ID_PRIMARY_SEAM_OFFSET_FROM_TURNOVER"] > limits.max_primary_seam_offset_from_turnover_mm:
        raise SeamCleanabilityContractError("primary seam wanders away from the intended low-highlight turnover")

    width = v["ID_WET_EXTERIOR_MIN_TRENCH_WIDTH"]
    radius = v["ID_WET_EXTERIOR_MIN_ROOT_RADIUS"]
    depth = v["ID_WET_EXTERIOR_MAX_BLIND_TRENCH_DEPTH"]
    if width < limits.min_wet_exterior_trench_width_mm:
        raise SeamCleanabilityContractError("wet exterior trench is too narrow for prototype wipe access")
    if radius < limits.min_wet_exterior_root_radius_mm:
        raise SeamCleanabilityContractError("wet exterior root radius is too tight for residue-tolerant geometry")
    if depth / width > limits.max_blind_trench_depth_width_ratio:
        raise SeamCleanabilityContractError("wet exterior blind trench is too deep relative to its cleanable opening")
