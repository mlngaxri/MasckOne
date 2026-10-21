"""Provenance-bound evidence for measured four-zone massage response reductions."""
from __future__ import annotations

from dataclasses import dataclass

from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_zone_sweep import FourZoneImpedanceSweep, SystemMeasuredResponse, ZoneMeasuredResponse
from .actuator_frames import ZONE_IDS


@dataclass(frozen=True, slots=True)
class MeasuredActuationResponseEvidence:
    """Bind zone and system response reductions to the exact measured sweep."""

    source_sweep_sha256: str
    zone_responses: tuple[ZoneMeasuredResponse, ...]
    system_response: SystemMeasuredResponse


def build_measured_actuation_response_evidence(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
) -> MeasuredActuationResponseEvidence:
    """Reduce one validated measured sweep without discarding its provenance."""
    by_zone = sweep.measured_response_by_zone(parameters)
    system = sweep.measured_system_response(parameters)
    return MeasuredActuationResponseEvidence(
        source_sweep_sha256=sweep.sweep_sha256,
        zone_responses=tuple(by_zone[zone_id] for zone_id in ZONE_IDS),
        system_response=system,
    )


def validate_measured_actuation_response_evidence(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    evidence: MeasuredActuationResponseEvidence,
) -> MeasuredActuationResponseEvidence:
    """Fail closed unless response evidence matches the exact current measured sweep.

    Numeric extrema alone cannot distinguish two measurement sets that happen to
    reduce to the same values. Rebuilding this envelope also compares the canonical
    sweep digest, so record identity and measurement provenance remain part of the
    treatment mechanics consumption boundary.
    """
    if type(evidence) is not MeasuredActuationResponseEvidence:
        raise TypeError("evidence must be exact MeasuredActuationResponseEvidence")
    expected = build_measured_actuation_response_evidence(sweep, parameters)
    if evidence != expected:
        raise ActuationParameterError(
            "Measured actuation response evidence is stale or disagrees with the current four-zone sweep"
        )
    return evidence
