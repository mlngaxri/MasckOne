"""Physical validation gates for the Masck One emergency quick release.

This module deliberately separates geometry preflight from measured physical evidence.
It cannot turn CAD targets into claims. A release is validation-closed only when wet,
one-hand, unpowered test evidence satisfies force, time, reset, accidental-pull and
pinch/hair requirements.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be an exact numeric scalar")
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


@dataclass(frozen=True)
class QuickReleaseEvidence:
    wet_one_hand_peak_force_n: float
    wet_one_hand_release_time_s: float
    accidental_pull_force_n: float
    reset_retention_force_n: float
    release_trials: int
    pinch_failures: int
    hair_entanglement_failures: int
    unpowered_trials: int
    one_hand_trials: int

    def validate(self) -> None:
        for label in (
            "wet_one_hand_peak_force_n", "wet_one_hand_release_time_s",
            "accidental_pull_force_n", "reset_retention_force_n"
        ):
            value = _finite(getattr(self, label), label)
            if value < 0:
                raise ValueError(f"{label} must be non-negative")
        for label in (
            "release_trials", "pinch_failures", "hair_entanglement_failures",
            "unpowered_trials", "one_hand_trials"
        ):
            value = getattr(self, label)
            if type(value) is not int or value < 0:
                raise ValueError(f"{label} must be a non-negative integer")
        if self.release_trials <= 0:
            raise ValueError("release_trials must be positive")
        if self.pinch_failures > self.release_trials or self.hair_entanglement_failures > self.release_trials:
            raise ValueError("failure count cannot exceed release_trials")
        if self.unpowered_trials > self.release_trials or self.one_hand_trials > self.release_trials:
            raise ValueError("qualified trial count cannot exceed release_trials")


@dataclass(frozen=True)
class QuickReleaseGateResult:
    force_corridor_ok: bool
    release_time_ok: bool
    accidental_pull_margin_ok: bool
    reset_margin_ok: bool
    pinch_ok: bool
    hair_ok: bool
    all_trials_unpowered: bool
    all_trials_one_hand: bool
    validation_closed: bool
    accidental_pull_margin_n: float
    reset_margin_n: float
    evidence_status: str = "PHYSICAL_TEST_REQUIRED"


def evaluate_quick_release_evidence(
    evidence: QuickReleaseEvidence,
    *,
    min_release_force_n: float = 5.0,
    max_release_force_n: float = 12.0,
    max_release_time_s: float = 2.0,
    min_accidental_pull_margin_n: float = 2.0,
    min_reset_margin_n: float = 2.0,
) -> QuickReleaseGateResult:
    """Fail-closed gate for measured emergency-release evidence.

    The force corridor and time limit are validation gates, not predictions. The
    accidental-pull margin compares measured release force against the prescribed
    accidental pull. Reset margin requires the reset latch to retain above the
    measured release force by a prescribed margin. Any pinch/hair failure, powered
    dependency, or two-hand trial prevents closure.
    """
    evidence.validate()
    lo = _finite(min_release_force_n, "min_release_force_n")
    hi = _finite(max_release_force_n, "max_release_force_n")
    tmax = _finite(max_release_time_s, "max_release_time_s")
    pull_margin_req = _finite(min_accidental_pull_margin_n, "min_accidental_pull_margin_n")
    reset_margin_req = _finite(min_reset_margin_n, "min_reset_margin_n")
    if min(lo, hi, tmax, pull_margin_req, reset_margin_req) < 0 or lo > hi:
        raise ValueError("quick-release gate bounds are invalid")

    pull_margin = evidence.wet_one_hand_peak_force_n - evidence.accidental_pull_force_n
    reset_margin = evidence.reset_retention_force_n - evidence.wet_one_hand_peak_force_n
    force_ok = lo <= evidence.wet_one_hand_peak_force_n <= hi
    time_ok = evidence.wet_one_hand_release_time_s <= tmax
    pull_ok = pull_margin >= pull_margin_req
    reset_ok = reset_margin >= reset_margin_req
    pinch_ok = evidence.pinch_failures == 0
    hair_ok = evidence.hair_entanglement_failures == 0
    unpowered_ok = evidence.unpowered_trials == evidence.release_trials
    one_hand_ok = evidence.one_hand_trials == evidence.release_trials
    closed = all((force_ok, time_ok, pull_ok, reset_ok, pinch_ok, hair_ok, unpowered_ok, one_hand_ok))
    return QuickReleaseGateResult(
        force_ok, time_ok, pull_ok, reset_ok, pinch_ok, hair_ok,
        unpowered_ok, one_hand_ok, closed, pull_margin, reset_margin,
        "PHYSICAL_VALIDATION_CLOSED" if closed else "PHYSICAL_TEST_REQUIRED",
    )
