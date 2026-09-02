"""Physical retention-adjuster reversal repeatability sensitivity gate.

Digital screening only. This module does not establish fit, comfort, durability,
or usability claims.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


@dataclass(frozen=True)
class ReversalSample:
    cycle: int
    lost_motion_mm: float
    lost_motion_uncertainty_mm: float


@dataclass(frozen=True)
class ReversalSequenceResult:
    passes: bool
    first_failing_cycle: int | None
    worst_effective_lost_motion_mm: float
    worst_tension_deadband_n: float


def evaluate_reversal_sequence(
    samples: Iterable[ReversalSample],
    *,
    member_stiffness_n_per_mm: float,
    max_effective_lost_motion_mm: float,
    max_tension_deadband_n: float,
) -> ReversalSequenceResult:
    """Fail closed unless every cycle-indexed reversal checkpoint closes.

    Lost motion is treated as irreversible wear/settling evidence: the conservative
    effective value (measurement + uncertainty) may not decrease with cycle count.
    This prevents a favourable later trace from hiding an intermediate failure.
    """
    values = list(samples)
    scalars = (member_stiffness_n_per_mm, max_effective_lost_motion_mm, max_tension_deadband_n)
    if not values or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not isfinite(x) for x in scalars):
        raise ValueError("finite numeric inputs and at least one sample are required")
    if member_stiffness_n_per_mm < 0 or max_effective_lost_motion_mm < 0 or max_tension_deadband_n < 0:
        raise ValueError("limits and stiffness must be non-negative")
    if values[0].cycle != 0:
        raise ValueError("sequence must include a zero-cycle baseline")

    previous_cycle = -1
    previous_effective = -1.0
    first_failure = None
    worst_motion = 0.0
    worst_deadband = 0.0

    for sample in values:
        nums = (sample.cycle, sample.lost_motion_mm, sample.lost_motion_uncertainty_mm)
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not isfinite(x) for x in nums):
            raise ValueError("sample values must be finite numeric values")
        if not isinstance(sample.cycle, int) or sample.cycle < 0:
            raise ValueError("cycle must be a non-negative integer")
        if sample.cycle <= previous_cycle:
            raise ValueError("cycle count must be strictly increasing")
        if sample.lost_motion_mm < 0 or sample.lost_motion_uncertainty_mm < 0:
            raise ValueError("lost motion and uncertainty must be non-negative")

        effective = sample.lost_motion_mm + sample.lost_motion_uncertainty_mm
        if effective + 1e-12 < previous_effective:
            raise ValueError("conservative lost motion may not improve with cycle count")
        deadband = effective * member_stiffness_n_per_mm
        worst_motion = max(worst_motion, effective)
        worst_deadband = max(worst_deadband, deadband)
        if first_failure is None and (effective > max_effective_lost_motion_mm or deadband > max_tension_deadband_n):
            first_failure = sample.cycle
        previous_cycle = sample.cycle
        previous_effective = effective

    return ReversalSequenceResult(
        passes=first_failure is None,
        first_failing_cycle=first_failure,
        worst_effective_lost_motion_mm=worst_motion,
        worst_tension_deadband_n=worst_deadband,
    )
