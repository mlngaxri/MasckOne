"""Fail-closed prototype DFM gates for visible Masck One rigid-shell evidence.

These limits are industrial-design convergence targets for injection-moulded
appearance studies, not supplier capability or production release dimensions.
"""
from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class AppearanceShellDFMLimits:
    min_wall_mm: float = 1.8
    max_wall_mm: float = 2.5
    max_local_wall_range_mm: float = 0.40
    min_visible_draft_deg: float = 1.0
    max_rib_to_wall_ratio: float = 0.60
    max_boss_to_wall_ratio: float = 0.70


REQUIRED = (
    "ID_SHELL_WALL_MIN", "ID_SHELL_WALL_MAX",
    "ID_SHELL_VISIBLE_DRAFT_MIN", "ID_SHELL_MAX_RIB_THICKNESS",
    "ID_SHELL_MAX_BOSS_WALL", "ID_SHELL_NOMINAL_WALL",
)


class AppearanceShellDFMError(ValueError):
    pass


def _n(name: str, value: float) -> float:
    x = float(value)
    if not isfinite(x) or x < 0:
        raise AppearanceShellDFMError(f"{name} must be finite and >= 0")
    return x


def validate_appearance_shell_dfm(values: Mapping[str, float], limits: AppearanceShellDFMLimits = AppearanceShellDFMLimits()) -> None:
    missing = sorted(set(REQUIRED) - set(values))
    if missing:
        raise AppearanceShellDFMError("missing appearance-shell DFM evidence: " + ", ".join(missing))
    v = {k: _n(k, values[k]) for k in REQUIRED}
    lo, hi, nominal = v["ID_SHELL_WALL_MIN"], v["ID_SHELL_WALL_MAX"], v["ID_SHELL_NOMINAL_WALL"]
    if lo > hi:
        raise AppearanceShellDFMError("shell wall minimum exceeds maximum")
    if not limits.min_wall_mm <= nominal <= limits.max_wall_mm:
        raise AppearanceShellDFMError("nominal appearance-shell wall is outside prototype moulding exploration band")
    if lo < limits.min_wall_mm or hi > limits.max_wall_mm:
        raise AppearanceShellDFMError("appearance-shell wall extrema leave prototype moulding exploration band")
    if hi - lo > limits.max_local_wall_range_mm:
        raise AppearanceShellDFMError("visible shell wall variation is too large; sink/warp/highlight risk requires reconciliation")
    if v["ID_SHELL_VISIBLE_DRAFT_MIN"] < limits.min_visible_draft_deg:
        raise AppearanceShellDFMError("visible shell lacks prototype minimum mould-release draft")
    if v["ID_SHELL_MAX_RIB_THICKNESS"] > limits.max_rib_to_wall_ratio * nominal:
        raise AppearanceShellDFMError("rear rib is too thick relative to appearance wall; sink read-through risk")
    if v["ID_SHELL_MAX_BOSS_WALL"] > limits.max_boss_to_wall_ratio * nominal:
        raise AppearanceShellDFMError("boss wall is too thick relative to appearance wall; sink read-through risk")
