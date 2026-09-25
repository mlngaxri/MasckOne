"""Consumption-time integrity boundary for measured massage curvature evidence."""
from __future__ import annotations

from .actuation_mechanical_curvature import (
    ActuationMechanicalCurvatureEnvelope,
    reduce_measured_mechanical_curvature,
)
from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_zone_sweep import FourZoneImpedanceSweep


def validate_mechanical_curvature_evidence(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    evidence: ActuationMechanicalCurvatureEnvelope,
) -> ActuationMechanicalCurvatureEnvelope:
    """Fail closed unless curvature evidence exactly matches current measured inputs.

    Curvature summaries retain extrema and three-record provenance, so accepting a
    stale or mutated frozen envelope would weaken the measured four-zone evidence
    boundary. Recompute from the current authority-bound sweep before consumption.
    """
    if not isinstance(evidence, ActuationMechanicalCurvatureEnvelope):
        raise TypeError("evidence must be an ActuationMechanicalCurvatureEnvelope")
    expected = reduce_measured_mechanical_curvature(sweep, parameters)
    if evidence != expected:
        raise ActuationParameterError(
            "Mechanical curvature evidence is stale or disagrees with the current measured four-zone sweep"
        )
    return evidence
