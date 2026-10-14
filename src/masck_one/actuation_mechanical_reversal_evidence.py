"""Consumption-time integrity boundary for measured massage slope-reversal evidence."""
from __future__ import annotations

from .actuation_mechanical_reversal import (
    ActuationMechanicalReversalEnvelope,
    reduce_measured_mechanical_reversals,
)
from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_zone_sweep import FourZoneImpedanceSweep


def validate_mechanical_reversal_evidence(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    evidence: ActuationMechanicalReversalEnvelope,
) -> ActuationMechanicalReversalEnvelope:
    """Fail closed unless reversal evidence exactly matches current measured inputs.

    Reversal summaries carry turning-point classifications, counts, and exact
    three-record provenance. Recompute them from the current authority-bound
    four-zone sweep before any downstream treatment decision consumes them.
    """
    if not isinstance(evidence, ActuationMechanicalReversalEnvelope):
        raise TypeError("evidence must be an ActuationMechanicalReversalEnvelope")
    expected = reduce_measured_mechanical_reversals(sweep, parameters)
    if evidence != expected:
        raise ActuationParameterError(
            "Mechanical reversal evidence is stale or disagrees with the current measured four-zone sweep"
        )
    return evidence
