"""Integrated, provenance-bound evidence bundle for measured massage mechanics."""
from __future__ import annotations

from dataclasses import dataclass

from .actuation_mechanical_curvature import ActuationMechanicalCurvatureEnvelope, reduce_measured_mechanical_curvature
from .actuation_mechanical_curvature_evidence import validate_mechanical_curvature_evidence
from .actuation_mechanical_reversal import ActuationMechanicalReversalEnvelope, reduce_measured_mechanical_reversals
from .actuation_mechanical_reversal_evidence import validate_mechanical_reversal_evidence
from .actuation_mechanical_sensitivity import ActuationMechanicalSensitivityEnvelope, reduce_measured_mechanical_sensitivity
from .actuation_mechanical_sensitivity_evidence import validate_mechanical_sensitivity_evidence
from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_zone_response_evidence import (
    MeasuredActuationResponseEvidence,
    build_measured_actuation_response_evidence,
    validate_measured_actuation_response_evidence,
)
from .actuation_zone_sweep import FourZoneImpedanceSweep


@dataclass(frozen=True, slots=True)
class MeasuredMassageMechanicsEvidenceBundle:
    """One atomic view of the measured four-zone mechanics reductions."""

    source_sweep_sha256: str
    response: MeasuredActuationResponseEvidence
    sensitivity: ActuationMechanicalSensitivityEnvelope
    curvature: ActuationMechanicalCurvatureEnvelope
    reversal: ActuationMechanicalReversalEnvelope


def build_measured_massage_mechanics_evidence_bundle(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
) -> MeasuredMassageMechanicsEvidenceBundle:
    """Build all measured massage reductions from one authority-bound sweep."""
    response = build_measured_actuation_response_evidence(sweep, parameters)
    return MeasuredMassageMechanicsEvidenceBundle(
        source_sweep_sha256=sweep.sweep_sha256,
        response=response,
        sensitivity=reduce_measured_mechanical_sensitivity(sweep, parameters),
        curvature=reduce_measured_mechanical_curvature(sweep, parameters),
        reversal=reduce_measured_mechanical_reversals(sweep, parameters),
    )


def validate_measured_massage_mechanics_evidence_bundle(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    evidence: MeasuredMassageMechanicsEvidenceBundle,
) -> MeasuredMassageMechanicsEvidenceBundle:
    """Fail closed unless every mechanics view comes from the same current sweep.

    Downstream packaging and treatment decisions often need response margins,
    adjacent-angle sensitivity, curvature, and slope reversals together. Validating
    those independently at call sites can accidentally combine evidence from
    different measurement captures. This boundary validates each canonical view and
    then reconstructs the atomic bundle from the current sweep.
    """
    if type(evidence) is not MeasuredMassageMechanicsEvidenceBundle:
        raise TypeError("evidence must be exact MeasuredMassageMechanicsEvidenceBundle")

    validate_measured_actuation_response_evidence(sweep, parameters, evidence.response)
    validate_mechanical_sensitivity_evidence(sweep, parameters, evidence.sensitivity)
    validate_mechanical_curvature_evidence(sweep, parameters, evidence.curvature)
    validate_mechanical_reversal_evidence(sweep, parameters, evidence.reversal)

    expected = build_measured_massage_mechanics_evidence_bundle(sweep, parameters)
    if evidence != expected:
        raise ActuationParameterError(
            "Measured massage mechanics evidence bundle is stale or mixes four-zone sweep provenance"
        )
    return evidence
