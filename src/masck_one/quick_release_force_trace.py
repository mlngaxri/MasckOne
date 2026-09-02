"""Force-displacement evidence for the Masck One mechanical emergency release.

This module prevents a single reported peak force from hiding an inaccessible force
spike, excessive actuation work, incomplete travel, or a release that never produces
a clear post-latch force drop. Inputs are measured physical traces. No CAD or spring
estimate may be labelled as physical evidence through this gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be an exact numeric scalar")
    out = float(value)
    if not isfinite(out):
        raise ValueError(f"{label} must be finite")
    return out


@dataclass(frozen=True)
class ForceDisplacementPoint:
    travel_mm: float
    force_n: float

    def validate(self) -> None:
        if _finite(self.travel_mm, "travel_mm") < 0:
            raise ValueError("travel_mm must be non-negative")
        if _finite(self.force_n, "force_n") < 0:
            raise ValueError("force_n must be non-negative")


@dataclass(frozen=True)
class QuickReleaseTraceResult:
    peak_force_n: float
    peak_force_travel_mm: float
    terminal_force_n: float
    measured_travel_mm: float
    work_mj: float
    force_corridor_ok: bool
    travel_complete: bool
    post_latch_drop_ok: bool
    work_ok: bool
    validation_closed: bool
    evidence_status: str


def evaluate_release_force_trace(
    points: Iterable[ForceDisplacementPoint], *,
    min_peak_force_n: float = 5.0,
    max_peak_force_n: float = 12.0,
    required_travel_mm: float,
    travel_tolerance_mm: float = 0.5,
    min_post_latch_force_drop_n: float = 2.0,
    max_work_mj: float = 80.0,
) -> QuickReleaseTraceResult:
    """Evaluate a monotonic measured pull trace using trapezoidal work integration."""
    lo = _finite(min_peak_force_n, "min_peak_force_n")
    hi = _finite(max_peak_force_n, "max_peak_force_n")
    required = _finite(required_travel_mm, "required_travel_mm")
    tol = _finite(travel_tolerance_mm, "travel_tolerance_mm")
    drop_req = _finite(min_post_latch_force_drop_n, "min_post_latch_force_drop_n")
    work_limit = _finite(max_work_mj, "max_work_mj")
    if min(lo, hi, required, tol, drop_req, work_limit) < 0 or lo > hi:
        raise ValueError("release trace gate bounds are invalid")

    rows = tuple(points)
    if len(rows) < 2:
        raise ValueError("release trace requires at least two measured points")
    for row in rows:
        if not isinstance(row, ForceDisplacementPoint):
            raise ValueError("all trace rows must be ForceDisplacementPoint records")
        row.validate()
    for previous, current in zip(rows, rows[1:]):
        if current.travel_mm <= previous.travel_mm:
            raise ValueError("release trace travel must be strictly increasing")

    peak_index = max(range(len(rows)), key=lambda i: rows[i].force_n)
    peak = rows[peak_index]
    terminal = rows[-1]
    measured_travel = terminal.travel_mm - rows[0].travel_mm
    work_mj = sum(
        0.5 * (a.force_n + b.force_n) * (b.travel_mm - a.travel_mm)
        for a, b in zip(rows, rows[1:])
    )
    corridor_ok = lo <= peak.force_n <= hi
    travel_complete = measured_travel + tol >= required
    post_drop_ok = peak_index < len(rows) - 1 and peak.force_n - terminal.force_n >= drop_req
    work_ok = work_mj <= work_limit
    closed = corridor_ok and travel_complete and post_drop_ok and work_ok
    return QuickReleaseTraceResult(
        peak.force_n, peak.travel_mm, terminal.force_n, measured_travel, work_mj,
        corridor_ok, travel_complete, post_drop_ok, work_ok, closed,
        "PHYSICAL_TRACE_GATE_CLOSED" if closed else "PHYSICAL_TEST_REQUIRED",
    )
