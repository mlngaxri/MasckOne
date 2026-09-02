"""Sequence-level durability gate for the Masck One physical retention adjuster.

Single end-of-life bounds can hide non-monotonic measurements, conditioning damage,
or an intermediate-cycle failure. This module evaluates every measured wear state,
requires monotonic degradation for irreversible wear observables, and refuses closure
if any state fails the existing adjuster-wear screening model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from retention_adjuster_wear import evaluate_adjuster_wear


@dataclass(frozen=True)
class AdjusterWearState:
    cycle_count: int
    increment_growth_mm: float
    endpoint_position_loss_mm: float
    backdrive_capacity_loss_n: float


@dataclass(frozen=True)
class AdjusterWearSequenceResult:
    state_count: int
    first_failing_cycle: int | None
    monotonic_degradation: bool
    every_state_closed: bool
    screening_closed: bool
    evidence_status: str


def _state(value: object) -> AdjusterWearState:
    if not isinstance(value, AdjusterWearState):
        raise ValueError("states must contain AdjusterWearState records")
    if type(value.cycle_count) is not int or value.cycle_count < 0:
        raise ValueError("cycle_count must be a non-negative integer")
    return value


def evaluate_adjuster_wear_sequence(
    *,
    states: Iterable[AdjusterWearState],
    initial_reachable_travel_mm: float,
    required_travel_mm: float,
    initial_increment_mm: float,
    retention_stiffness_n_per_mm: float,
    max_tension_error_n: float,
    initial_backdrive_capacity_n: float,
    max_service_tension_n: float,
    service_tension_uncertainty_n: float = 0.0,
    required_backdrive_margin_n: float = 0.0,
) -> AdjusterWearSequenceResult:
    records = tuple(_state(s) for s in states)
    if not records:
        raise ValueError("at least one measured wear state is required")
    if records[0].cycle_count != 0:
        raise ValueError("wear sequence must include the zero-cycle baseline")
    if any(b.cycle_count <= a.cycle_count for a, b in zip(records, records[1:])):
        raise ValueError("cycle_count must be strictly increasing")

    monotonic = True
    first_failure = None
    all_closed = True
    previous = None
    for record in records:
        if previous is not None:
            monotonic &= record.increment_growth_mm >= previous.increment_growth_mm
            monotonic &= record.endpoint_position_loss_mm >= previous.endpoint_position_loss_mm
            monotonic &= record.backdrive_capacity_loss_n >= previous.backdrive_capacity_loss_n
        result = evaluate_adjuster_wear(
            initial_reachable_travel_mm=initial_reachable_travel_mm,
            required_travel_mm=required_travel_mm,
            initial_increment_mm=initial_increment_mm,
            increment_growth_mm=record.increment_growth_mm,
            endpoint_position_loss_mm=record.endpoint_position_loss_mm,
            retention_stiffness_n_per_mm=retention_stiffness_n_per_mm,
            max_tension_error_n=max_tension_error_n,
            initial_backdrive_capacity_n=initial_backdrive_capacity_n,
            backdrive_capacity_loss_n=record.backdrive_capacity_loss_n,
            max_service_tension_n=max_service_tension_n,
            service_tension_uncertainty_n=service_tension_uncertainty_n,
            required_backdrive_margin_n=required_backdrive_margin_n,
        )
        if not result.screening_closed:
            all_closed = False
            if first_failure is None:
                first_failure = record.cycle_count
        previous = record

    closed = monotonic and all_closed
    return AdjusterWearSequenceResult(
        len(records), first_failure, monotonic, all_closed, closed,
        "DIGITAL_SENSITIVITY_ONLY" if closed else "PHYSICAL_TEST_REQUIRED",
    )
