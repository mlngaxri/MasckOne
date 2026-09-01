"""Trial-level physical evidence gate for the Masck One emergency release.

Aggregate minima/maxima can hide mixed populations. This module evaluates every
recorded wet, one-hand, unpowered release trial before reducing evidence to a gate.
Targets remain validation requirements, not measured claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be an exact numeric scalar")
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


@dataclass(frozen=True)
class QuickReleaseTrial:
    peak_release_force_n: float
    removal_time_s: float
    accidental_pull_force_n: float
    reset_retention_force_n: float
    unpowered: bool
    one_hand: bool
    wet: bool
    pinch_failure: bool = False
    hair_entanglement_failure: bool = False

    def validate(self) -> None:
        for label in (
            "peak_release_force_n", "removal_time_s", "accidental_pull_force_n",
            "reset_retention_force_n",
        ):
            value = _finite(getattr(self, label), label)
            if value < 0:
                raise ValueError(f"{label} must be non-negative")
        for label in (
            "unpowered", "one_hand", "wet", "pinch_failure",
            "hair_entanglement_failure",
        ):
            if type(getattr(self, label)) is not bool:
                raise ValueError(f"{label} must be bool")


@dataclass(frozen=True)
class QuickReleaseTrialGate:
    trial_count: int
    force_failures: int
    time_failures: int
    accidental_margin_failures: int
    reset_margin_failures: int
    qualification_failures: int
    pinch_failures: int
    hair_failures: int
    validation_closed: bool
    evidence_status: str


def evaluate_quick_release_trials(
    trials: Iterable[QuickReleaseTrial], *,
    min_release_force_n: float = 5.0,
    max_release_force_n: float = 12.0,
    max_release_time_s: float = 2.0,
    min_accidental_pull_margin_n: float = 2.0,
    min_reset_margin_n: float = 2.0,
) -> QuickReleaseTrialGate:
    """Require every trial to satisfy every safety/basic-function gate."""
    lo = _finite(min_release_force_n, "min_release_force_n")
    hi = _finite(max_release_force_n, "max_release_force_n")
    tmax = _finite(max_release_time_s, "max_release_time_s")
    pull_req = _finite(min_accidental_pull_margin_n, "min_accidental_pull_margin_n")
    reset_req = _finite(min_reset_margin_n, "min_reset_margin_n")
    if min(lo, hi, tmax, pull_req, reset_req) < 0 or lo > hi:
        raise ValueError("quick-release gate bounds are invalid")

    rows = tuple(trials)
    if not rows:
        raise ValueError("at least one physical release trial is required")
    for row in rows:
        if not isinstance(row, QuickReleaseTrial):
            raise ValueError("all trials must be QuickReleaseTrial records")
        row.validate()

    force = sum(not (lo <= r.peak_release_force_n <= hi) for r in rows)
    timing = sum(r.removal_time_s > tmax for r in rows)
    accidental = sum(
        r.peak_release_force_n - r.accidental_pull_force_n < pull_req for r in rows
    )
    reset = sum(
        r.reset_retention_force_n - r.peak_release_force_n < reset_req for r in rows
    )
    qualification = sum(not (r.unpowered and r.one_hand and r.wet) for r in rows)
    pinch = sum(r.pinch_failure for r in rows)
    hair = sum(r.hair_entanglement_failure for r in rows)
    closed = not any((force, timing, accidental, reset, qualification, pinch, hair))
    return QuickReleaseTrialGate(
        len(rows), force, timing, accidental, reset, qualification, pinch, hair,
        closed, "PHYSICAL_VALIDATION_CLOSED" if closed else "PHYSICAL_TEST_REQUIRED",
    )
