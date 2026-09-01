"""Prototype geometry gates for facial protected regions.

These checks are industrial-design convergence controls, not anthropometric or
clinical claims. Values must come from released CAD measurements in the
canonical facial coordinate frame and remain subject to representative fit
validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


class ProtectedRegionContractError(ValueError):
    """Raised when protected-region CAD evidence is absent or degrading."""


@dataclass(frozen=True)
class ProtectedRegionLimits:
    max_eye_area_asymmetry_fraction: float = 0.08
    max_eye_width_asymmetry_mm: float = 2.0
    max_eye_height_asymmetry_mm: float = 2.0
    min_eye_edge_clearance_mm: float = 3.0
    min_nostril_edge_clearance_mm: float = 3.0
    min_mouth_edge_clearance_mm: float = 4.0
    max_protected_edge_clearance_asymmetry_mm: float = 1.5


REQUIRED = (
    "ID_EYE_APERTURE_AREA_L", "ID_EYE_APERTURE_AREA_R",
    "ID_EYE_APERTURE_WIDTH_L", "ID_EYE_APERTURE_WIDTH_R",
    "ID_EYE_APERTURE_HEIGHT_L", "ID_EYE_APERTURE_HEIGHT_R",
    "ID_EYE_EDGE_CLEARANCE_L", "ID_EYE_EDGE_CLEARANCE_R",
    "ID_NOSTRIL_EDGE_CLEARANCE_L", "ID_NOSTRIL_EDGE_CLEARANCE_R",
    "ID_MOUTH_EDGE_CLEARANCE_L", "ID_MOUTH_EDGE_CLEARANCE_R",
)


def _positive(name: str, raw: float) -> float:
    value = float(raw)
    if not isfinite(value) or value <= 0:
        raise ProtectedRegionContractError(f"{name} must be finite and > 0")
    return value


def validate_protected_regions(values: Mapping[str, float], limits: ProtectedRegionLimits = ProtectedRegionLimits()) -> None:
    """Fail closed on aperture imbalance or encroachment into protected regions."""
    missing = sorted(set(REQUIRED) - set(values))
    if missing:
        raise ProtectedRegionContractError("missing protected-region measurements: " + ", ".join(missing))
    v = {name: _positive(name, values[name]) for name in REQUIRED}

    area_l, area_r = v["ID_EYE_APERTURE_AREA_L"], v["ID_EYE_APERTURE_AREA_R"]
    area_asymmetry = abs(area_l - area_r) / max(area_l, area_r)
    if area_asymmetry > limits.max_eye_area_asymmetry_fraction:
        raise ProtectedRegionContractError("eye aperture area imbalance creates unintended visual/fit asymmetry")
    if abs(v["ID_EYE_APERTURE_WIDTH_L"] - v["ID_EYE_APERTURE_WIDTH_R"]) > limits.max_eye_width_asymmetry_mm:
        raise ProtectedRegionContractError("eye aperture width asymmetry exceeds prototype neutrality target")
    if abs(v["ID_EYE_APERTURE_HEIGHT_L"] - v["ID_EYE_APERTURE_HEIGHT_R"]) > limits.max_eye_height_asymmetry_mm:
        raise ProtectedRegionContractError("eye aperture height asymmetry exceeds prototype neutrality target")

    for region, minimum in (("EYE", limits.min_eye_edge_clearance_mm), ("NOSTRIL", limits.min_nostril_edge_clearance_mm), ("MOUTH", limits.min_mouth_edge_clearance_mm)):
        left, right = v[f"ID_{region}_EDGE_CLEARANCE_L"], v[f"ID_{region}_EDGE_CLEARANCE_R"]
        if min(left, right) < minimum:
            raise ProtectedRegionContractError(f"{region.lower()} protected-region edge clearance is below prototype guard band")
        if abs(left - right) > limits.max_protected_edge_clearance_asymmetry_mm:
            raise ProtectedRegionContractError(f"{region.lower()} protected-region clearance asymmetry exceeds prototype neutrality target")
