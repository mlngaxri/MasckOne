"""Fail-closed evidence contract for Masck One physical CMF convergence.

This module does not choose production colour or claim durability. It prevents a
CMF candidate from being promoted on render appearance alone by requiring
measured physical plaques/samples across the actual material hierarchy.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class CMFEvidenceLimits:
    shell_gloss_min_gu60: float = 8.0
    shell_gloss_max_gu60: float = 28.0
    max_shell_gloss_spread_gu60: float = 4.0
    max_post_clean_gloss_shift_gu60: float = 5.0
    max_post_clean_delta_e00: float = 3.0


REQUIRED_MEASUREMENTS = (
    "CMF_SHELL_GLOSS_GU60_A",
    "CMF_SHELL_GLOSS_GU60_B",
    "CMF_SHELL_GLOSS_GU60_C",
    "CMF_SHELL_POST_CLEAN_GLOSS_SHIFT_GU60",
    "CMF_SHELL_POST_CLEAN_DELTA_E00",
)


class CMFEvidenceContractError(ValueError):
    """Raised when a physical CMF candidate lacks adequate measured evidence."""


def _finite_nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value < 0:
        raise CMFEvidenceContractError(f"{name} must be finite and >= 0")
    return value


def validate_cmf_evidence(values: Mapping[str, float], limits: CMFEvidenceLimits = CMFEvidenceLimits()) -> None:
    """Reject render-only, inconsistent, or visibly unstable shell CMF evidence.

    A/B/C are three independently measured locations or plaques from the same
    candidate process/material/texture condition. The thresholds are prototype
    convergence controls only and must not be represented as production specs.
    """
    missing = sorted(set(REQUIRED_MEASUREMENTS) - set(values))
    if missing:
        raise CMFEvidenceContractError("missing physical CMF measurements: " + ", ".join(missing))
    v = {name: _finite_nonnegative(name, values[name]) for name in REQUIRED_MEASUREMENTS}

    gloss = [v["CMF_SHELL_GLOSS_GU60_A"], v["CMF_SHELL_GLOSS_GU60_B"], v["CMF_SHELL_GLOSS_GU60_C"]]
    if any(g < limits.shell_gloss_min_gu60 or g > limits.shell_gloss_max_gu60 for g in gloss):
        raise CMFEvidenceContractError("shell gloss falls outside the low-gloss prototype exploration window")
    if max(gloss) - min(gloss) > limits.max_shell_gloss_spread_gu60:
        raise CMFEvidenceContractError("shell gloss is too inconsistent across the physical candidate")
    if v["CMF_SHELL_POST_CLEAN_GLOSS_SHIFT_GU60"] > limits.max_post_clean_gloss_shift_gu60:
        raise CMFEvidenceContractError("cleaning causes excessive shell gloss shift for prototype convergence")
    if v["CMF_SHELL_POST_CLEAN_DELTA_E00"] > limits.max_post_clean_delta_e00:
        raise CMFEvidenceContractError("cleaning causes excessive shell colour shift for prototype convergence")
