"""Condition-sequence gate for the Masck One physical retention adjuster.

Durability evidence must not be pooled across incompatible interface conditions. This
module checks each condition's cycle sequence independently, then requires the full
condition matrix to close. Outputs remain engineering sensitivity only.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping, Sequence

from .retention_adjuster_wear_sequence import WearCheckpoint, evaluate_wear_sequence


@dataclass(frozen=True)
class ConditionSequenceResult:
    passed: bool
    missing_conditions: tuple[str, ...]
    failing_conditions: tuple[str, ...]
    first_failure_cycle_by_condition: dict[str, int | None]


def _condition(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("condition names must be non-empty strings")
    return value.strip().lower()


def evaluate_condition_sequences(
    sequences: Mapping[str, Sequence[WearCheckpoint]],
    *,
    required_conditions: Iterable[str],
    **wear_kwargs: float,
) -> ConditionSequenceResult:
    """Require independent durability closure for every released condition.

    `wear_kwargs` are passed unchanged to `evaluate_wear_sequence`, so the same
    production-intent geometry and screening thresholds are used for every condition.
    Conditions are deliberately not averaged: one failing wet or contaminated sequence
    blocks the matrix even when dry evidence passes.
    """
    required = tuple(_condition(c) for c in required_conditions)
    if not required:
        raise ValueError("at least one required condition is needed")
    if len(set(required)) != len(required):
        raise ValueError("required conditions must be unique")

    normalized: dict[str, Sequence[WearCheckpoint]] = {}
    for raw_name, checkpoints in sequences.items():
        name = _condition(raw_name)
        if name in normalized:
            raise ValueError(f"duplicate normalized condition: {name}")
        normalized[name] = checkpoints

    missing = tuple(c for c in required if c not in normalized)
    failing: list[str] = []
    first_failure: dict[str, int | None] = {}

    for condition in required:
        if condition not in normalized:
            first_failure[condition] = None
            continue
        result = evaluate_wear_sequence(normalized[condition], **wear_kwargs)
        first_failure[condition] = result.first_failing_cycle
        if not result.passed:
            failing.append(condition)

    return ConditionSequenceResult(
        passed=not missing and not failing,
        missing_conditions=missing,
        failing_conditions=tuple(failing),
        first_failure_cycle_by_condition=first_failure,
    )
