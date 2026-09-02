"""Mechanical state-transition gate for the Masck One emergency quick release.

This is a physical mechanism model, not firmware. It verifies that a proposed latch
sequence has a distinct release event, cannot self-reset when the grip is released,
and requires deliberate reset engagement before returning to LATCHED.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Iterable


class ReleaseState(str, Enum):
    LATCHED = "LATCHED"
    RELEASING = "RELEASING"
    RELEASED = "RELEASED"
    RESET_REQUIRED = "RESET_REQUIRED"


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be an exact numeric scalar")
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


@dataclass(frozen=True)
class MechanicalStateSample:
    travel_mm: float
    state: ReleaseState
    grip_engaged: bool
    latch_engagement_mm: float

    def validate(self) -> None:
        travel = _finite(self.travel_mm, "travel_mm")
        engagement = _finite(self.latch_engagement_mm, "latch_engagement_mm")
        if travel < 0 or engagement < 0:
            raise ValueError("travel and latch engagement must be non-negative")
        if type(self.grip_engaged) is not bool:
            raise ValueError("grip_engaged must be boolean")
        if not isinstance(self.state, ReleaseState):
            raise ValueError("state must be ReleaseState")


@dataclass(frozen=True)
class MechanicalStateGateResult:
    ordered_states_ok: bool
    distinct_release_event_ok: bool
    released_disengagement_ok: bool
    no_self_reset_ok: bool
    deliberate_reset_ok: bool
    gate_closed: bool
    release_travel_mm: float | None
    evidence_status: str = "DIGITAL_SENSITIVITY_ONLY"


def evaluate_mechanical_state_sequence(
    samples: Iterable[MechanicalStateSample],
    *,
    max_released_engagement_mm: float = 0.10,
    min_reset_engagement_mm: float = 0.50,
) -> MechanicalStateGateResult:
    """Screen a sampled physical latch sequence for fail-closed state semantics.

    The sequence must visit LATCHED -> RELEASING -> RELEASED -> RESET_REQUIRED ->
    LATCHED in that order. RELEASED requires near-zero latch engagement. Releasing
    the grip after the release event must not restore LATCHED. The final LATCHED
    state must regain deliberate engagement above ``min_reset_engagement_mm``.

    This does not prove continuous collision clearance, release force, or usability.
    """
    seq = tuple(samples)
    if len(seq) < 5:
        raise ValueError("at least five state samples are required")
    for sample in seq:
        if not isinstance(sample, MechanicalStateSample):
            raise ValueError("all samples must be MechanicalStateSample")
        sample.validate()
    released_limit = _finite(max_released_engagement_mm, "max_released_engagement_mm")
    reset_min = _finite(min_reset_engagement_mm, "min_reset_engagement_mm")
    if released_limit < 0 or reset_min <= released_limit:
        raise ValueError("engagement thresholds are invalid")

    states = [s.state for s in seq]
    required = [ReleaseState.LATCHED, ReleaseState.RELEASING, ReleaseState.RELEASED,
                ReleaseState.RESET_REQUIRED, ReleaseState.LATCHED]
    cursor = 0
    indices: list[int] = []
    for wanted in required:
        try:
            idx = states.index(wanted, cursor)
        except ValueError:
            indices = []
            break
        indices.append(idx)
        cursor = idx + 1
    ordered = len(indices) == len(required)

    release_idx = indices[2] if ordered else None
    reset_idx = indices[3] if ordered else None
    final_idx = indices[4] if ordered else None
    distinct = bool(ordered and release_idx is not None and release_idx > indices[1])
    disengaged = bool(ordered and seq[release_idx].latch_engagement_mm <= released_limit)

    no_self_reset = False
    if ordered:
        post_release_pre_reset = seq[release_idx:reset_idx + 1]
        no_self_reset = all(s.state is not ReleaseState.LATCHED for s in post_release_pre_reset[1:])
        # At least one post-release sample must show the user has let go while the
        # mechanism remains non-latched. Otherwise self-reset resistance is unproven.
        no_self_reset = no_self_reset and any(not s.grip_engaged for s in post_release_pre_reset)

    deliberate_reset = bool(
        ordered
        and seq[reset_idx].state is ReleaseState.RESET_REQUIRED
        and seq[final_idx].state is ReleaseState.LATCHED
        and seq[final_idx].latch_engagement_mm >= reset_min
    )
    closed = all((ordered, distinct, disengaged, no_self_reset, deliberate_reset))
    return MechanicalStateGateResult(
        ordered, distinct, disengaged, no_self_reset, deliberate_reset, closed,
        seq[release_idx].travel_mm if release_idx is not None else None,
    )
