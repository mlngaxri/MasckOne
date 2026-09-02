"""Fail-closed cheek-field industrial-design gates for Masck One.

These limits prevent locally compliant aperture and side geometry from leaving a
pinched, hollow, or mechanically segmented mid-face. They are digital prototype
convergence hypotheses, not validated fit, comfort, moulding, or Class-A claims.
"""
from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class CheekFieldLimits:
    min_bridge_width_mm: float = 12.0
    min_blend_run_mm: float = 10.0
    max_depth_excursion_mm: float = 2.5
    max_bilateral_width_mismatch_mm: float = 1.5
    max_bilateral_depth_mismatch_mm: float = 0.75


REQUIRED = (
    "ID_CHEEK_BRIDGE_WIDTH_L",
    "ID_CHEEK_BRIDGE_WIDTH_R",
    "ID_CHEEK_BLEND_RUN_L",
    "ID_CHEEK_BLEND_RUN_R",
    "ID_CHEEK_DEPTH_EXCURSION_L",
    "ID_CHEEK_DEPTH_EXCURSION_R",
)


class CheekFieldError(ValueError):
    pass


def _n(name: str, value: float) -> float:
    x = float(value)
    if not isfinite(x) or x < 0:
        raise CheekFieldError(f"{name} must be finite and >= 0")
    return x


def validate_cheek_field(values: Mapping[str, float], limits: CheekFieldLimits = CheekFieldLimits()) -> None:
    missing = sorted(set(REQUIRED) - set(values))
    if missing:
        raise CheekFieldError("missing cheek-field evidence: " + ", ".join(missing))
    v = {k: _n(k, values[k]) for k in REQUIRED}
    wl, wr = v["ID_CHEEK_BRIDGE_WIDTH_L"], v["ID_CHEEK_BRIDGE_WIDTH_R"]
    rl, rr = v["ID_CHEEK_BLEND_RUN_L"], v["ID_CHEEK_BLEND_RUN_R"]
    dl, dr = v["ID_CHEEK_DEPTH_EXCURSION_L"], v["ID_CHEEK_DEPTH_EXCURSION_R"]
    if min(wl, wr) < limits.min_bridge_width_mm:
        raise CheekFieldError("cheek bridge is too narrow; mid-face risks pinched/goggle segmentation")
    if min(rl, rr) < limits.min_blend_run_mm:
        raise CheekFieldError("cheek transition is too abrupt for a broad authored facial field")
    if max(dl, dr) > limits.max_depth_excursion_mm:
        raise CheekFieldError("cheek depth excursion is too large; local pod/hollow reading risk")
    if abs(wl - wr) > limits.max_bilateral_width_mismatch_mm:
        raise CheekFieldError("cheek bridge width is bilaterally incoherent")
    if abs(dl - dr) > limits.max_bilateral_depth_mismatch_mm:
        raise CheekFieldError("cheek depth excursion is bilaterally incoherent")
