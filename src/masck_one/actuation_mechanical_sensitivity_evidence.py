"""Consumption-time integrity boundary for measured massage sensitivity evidence."""
from __future__ import annotations

from .actuation_mechanical_sensitivity import (
    ActuationMechanicalSensitivityEnvelope,
    reduce_measured_mechanical_sensitivity,
)
from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_zone_sweep import FourZoneImpedanceSweep


def validate_mechanical_sensitivity_evidence(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    evidence: ActuationMechanicalSensitivityEnvelope,
) -> ActuationMechanicalSensitivityEnvelope:
    """Fail closed unless sensitivity evidence exactly matches current measured inputs.

    Adjacent-angle summaries retain extrema and two-record provenance. Recompute the
    complete envelope from the current authority-bound sweep before consumption so
    stale, substituted, or mutated sensitivity evidence cannot cross the treatment
    mechanics boundary.
    """
    if not isinstance(evidence, ActuationMechanicalSensitivityEnvelope):
        raise TypeError("evidence must be an ActuationMechanicalSensitivityEnvelope")
    expected = reduce_measured_mechanical_sensitivity(sweep, parameters)
    if evidence != expected:
        raise ActuationParameterError(
            "Mechanical sensitivity evidence is stale or disagrees with the current measured four-zone sweep"
        )
    return evidence
