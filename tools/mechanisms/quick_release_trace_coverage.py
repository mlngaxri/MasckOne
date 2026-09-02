"""Coverage gate for Masck One emergency-release force/displacement evidence.

A set of individually passing traces is not sufficient if it samples only one specimen,
one cycle, or one benign condition. This module gates coverage without converting test
counts into a reliability claim. Thresholds are protocol requirements, not evidence of
population-level safety.
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
class ReleaseTraceRecord:
    specimen_id: str
    cycle_index: int
    condition: str
    trace_gate_closed: bool
    calibration_id: str
    peak_force_n: float
    work_mj: float

    def validate(self) -> None:
        if not self.specimen_id.strip():
            raise ValueError("specimen_id is required")
        if type(self.cycle_index) is not int or self.cycle_index < 1:
            raise ValueError("cycle_index must be a positive integer")
        if not self.condition.strip():
            raise ValueError("condition is required")
        if type(self.trace_gate_closed) is not bool:
            raise ValueError("trace_gate_closed must be boolean")
        if not self.calibration_id.strip():
            raise ValueError("calibration_id is required")
        if _finite(self.peak_force_n, "peak_force_n") < 0:
            raise ValueError("peak_force_n must be non-negative")
        if _finite(self.work_mj, "work_mj") < 0:
            raise ValueError("work_mj must be non-negative")


@dataclass(frozen=True)
class ReleaseTraceCoverageResult:
    specimen_count: int
    condition_count: int
    minimum_cycles_per_specimen_condition: int
    all_traces_closed: bool
    required_conditions_present: bool
    coverage_closed: bool
    evidence_status: str


def evaluate_release_trace_coverage(
    records: Iterable[ReleaseTraceRecord], *,
    required_conditions: tuple[str, ...] = ("wet",),
    min_specimens: int = 3,
    min_cycles_per_specimen_condition: int = 3,
) -> ReleaseTraceCoverageResult:
    """Fail closed when trace evidence lacks breadth or repeat-cycle coverage."""
    if type(min_specimens) is not int or min_specimens < 1:
        raise ValueError("min_specimens must be a positive integer")
    if type(min_cycles_per_specimen_condition) is not int or min_cycles_per_specimen_condition < 1:
        raise ValueError("min_cycles_per_specimen_condition must be a positive integer")
    required = tuple(c.strip() for c in required_conditions)
    if not required or any(not c for c in required) or len(set(required)) != len(required):
        raise ValueError("required_conditions must contain unique non-empty names")

    rows = tuple(records)
    if not rows:
        raise ValueError("at least one trace record is required")
    for row in rows:
        if not isinstance(row, ReleaseTraceRecord):
            raise ValueError("all records must be ReleaseTraceRecord instances")
        row.validate()

    identities = [(r.specimen_id, r.condition, r.cycle_index) for r in rows]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate specimen/condition/cycle trace record")

    specimens = {r.specimen_id for r in rows}
    conditions = {r.condition for r in rows}
    required_present = set(required).issubset(conditions)
    counts = {
        (specimen, condition): sum(
            1 for r in rows if r.specimen_id == specimen and r.condition == condition
        )
        for specimen in specimens for condition in required
    }
    minimum_cycles = min(counts.values()) if counts else 0
    all_closed = all(r.trace_gate_closed for r in rows)
    coverage = (
        len(specimens) >= min_specimens
        and required_present
        and minimum_cycles >= min_cycles_per_specimen_condition
        and all_closed
    )
    return ReleaseTraceCoverageResult(
        len(specimens), len(conditions), minimum_cycles, all_closed,
        required_present, coverage,
        "PHYSICAL_TRACE_COVERAGE_CLOSED" if coverage else "PHYSICAL_TEST_REQUIRED",
    )
