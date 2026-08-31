"""Deterministic digital tolerance envelopes for mechanism clearance checks.

This module performs geometry-only worst-case interval arithmetic. It does not
claim manufacturing capability, fatigue life, comfort, or physical clearance.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re

_ID = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


def _finite_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real numeric value, not bool/string/alias")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return 0.0 if value == 0.0 else value


def _identity(name: str, value: object) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ValueError(f"{name} must be canonical ASCII uppercase identity")
    return value


@dataclass(frozen=True)
class ScalarTolerance:
    nominal_mm: float
    minus_mm: float
    plus_mm: float

    def __post_init__(self) -> None:
        n = _finite_number("nominal_mm", self.nominal_mm)
        lo = _finite_number("minus_mm", self.minus_mm)
        hi = _finite_number("plus_mm", self.plus_mm)
        if lo < 0.0 or hi < 0.0:
            raise ValueError("tolerance magnitudes must be nonnegative")
        object.__setattr__(self, "nominal_mm", n)
        object.__setattr__(self, "minus_mm", lo)
        object.__setattr__(self, "plus_mm", hi)

    @property
    def interval_mm(self) -> tuple[float, float]:
        return (self.nominal_mm - self.minus_mm, self.nominal_mm + self.plus_mm)


@dataclass(frozen=True)
class ClearanceStack:
    """Worst-case scalar clearance between moving and protected boundaries.

    Positive clearance is separation. Contributions are signed sensitivities:
    +1 means increasing the dimension increases clearance, -1 decreases it.
    This deliberately uses endpoint enumeration rather than RSS/statistics.
    """
    stack_id: str
    coordinate_frame_id: str
    source_geometry_sha256: str
    nominal_clearance_mm: float
    contributions: tuple[tuple[str, ScalarTolerance, int], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "stack_id", _identity("stack_id", self.stack_id))
        object.__setattr__(self, "coordinate_frame_id", _identity("coordinate_frame_id", self.coordinate_frame_id))
        if not isinstance(self.source_geometry_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", self.source_geometry_sha256):
            raise ValueError("source_geometry_sha256 must be canonical lowercase SHA-256")
        object.__setattr__(self, "nominal_clearance_mm", _finite_number("nominal_clearance_mm", self.nominal_clearance_mm))
        frozen = tuple(self.contributions)
        seen: set[str] = set()
        checked = []
        for item in frozen:
            if not isinstance(item, tuple) or len(item) != 3:
                raise TypeError("each contribution must be (id, ScalarTolerance, sensitivity)")
            cid, tol, sensitivity = item
            cid = _identity("contribution_id", cid)
            if cid in seen:
                raise ValueError("duplicate contribution identity")
            seen.add(cid)
            if type(tol) is not ScalarTolerance:
                raise TypeError("contribution tolerance must be ScalarTolerance")
            if type(sensitivity) is not int or sensitivity not in (-1, 1):
                raise ValueError("sensitivity must be exact integer -1 or +1")
            checked.append((cid, tol, sensitivity))
        object.__setattr__(self, "contributions", tuple(checked))

    def worst_case_clearance_mm(self, *, current_geometry_sha256: str, coordinate_frame_id: str) -> float:
        if current_geometry_sha256 != self.source_geometry_sha256:
            raise RuntimeError("stale mechanism geometry provenance")
        if coordinate_frame_id != self.coordinate_frame_id:
            raise RuntimeError("local/world coordinate-frame mismatch")
        result = self.nominal_clearance_mm
        for _, tol, sensitivity in self.contributions:
            low, high = tol.interval_mm
            delta_low = low - tol.nominal_mm
            delta_high = high - tol.nominal_mm
            result += min(sensitivity * delta_low, sensitivity * delta_high)
        if not math.isfinite(result):
            raise ArithmeticError("clearance stack is not finitely representable")
        return math.nextafter(result, -math.inf)

    def assert_positive_clearance(self, *, current_geometry_sha256: str, coordinate_frame_id: str) -> float:
        value = self.worst_case_clearance_mm(current_geometry_sha256=current_geometry_sha256, coordinate_frame_id=coordinate_frame_id)
        if value <= 0.0:
            raise RuntimeError(f"worst-case digital clearance is nonpositive: {value!r} mm")
        return value

    @property
    def provenance_sha256(self) -> str:
        payload = {
            "stack_id": self.stack_id,
            "coordinate_frame_id": self.coordinate_frame_id,
            "source_geometry_sha256": self.source_geometry_sha256,
            "nominal_clearance_mm": self.nominal_clearance_mm,
            "contributions": [(cid, t.nominal_mm, t.minus_mm, t.plus_mm, s) for cid, t, s in self.contributions],
            "evidence": "DIGITAL_GEOMETRY_ONLY",
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")).hexdigest()
