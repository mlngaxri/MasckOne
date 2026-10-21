"""Atomic measured evidence boundary for massage mechanics and thermal coexistence."""
from __future__ import annotations

from dataclasses import dataclass

from .actuation_mechanical_evidence_bundle import (
    MeasuredMassageMechanicsEvidenceBundle,
    build_measured_massage_mechanics_evidence_bundle,
    validate_measured_massage_mechanics_evidence_bundle,
)
from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_thermal_coexistence import (
    ActuationThermalEnvelope,
    reduce_measured_actuation_thermal_envelope,
)
from .actuation_thermal_evidence import validate_paired_thermal_mechanical_evidence
from .actuation_thermal_mechanical_coupling import (
    ActuationThermalMechanicalCoupling,
    reduce_measured_thermal_mechanical_coupling,
)
from .actuation_zone_sweep import FourZoneImpedanceSweep


@dataclass(frozen=True, slots=True)
class TreatmentMassageThermalEvidence:
    """One provenance-bound view of measured massage mechanics and thermal coexistence."""

    source_parameter_sha256: str
    source_sweep_sha256: str
    mechanics: MeasuredMassageMechanicsEvidenceBundle
    thermal: ActuationThermalEnvelope
    coupling: ActuationThermalMechanicalCoupling


def build_treatment_massage_thermal_evidence(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
) -> TreatmentMassageThermalEvidence:
    """Build all treatment-facing massage and thermal reductions from one sweep."""
    return TreatmentMassageThermalEvidence(
        source_parameter_sha256=parameters.parameter_sha256,
        source_sweep_sha256=sweep.sweep_sha256,
        mechanics=build_measured_massage_mechanics_evidence_bundle(sweep, parameters),
        thermal=reduce_measured_actuation_thermal_envelope(sweep, parameters),
        coupling=reduce_measured_thermal_mechanical_coupling(sweep, parameters),
    )


def validate_treatment_massage_thermal_evidence(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    evidence: TreatmentMassageThermalEvidence,
) -> TreatmentMassageThermalEvidence:
    """Reject stale or mixed mechanics/thermal evidence at the treatment boundary."""
    if type(evidence) is not TreatmentMassageThermalEvidence:
        raise TypeError("evidence must be exact TreatmentMassageThermalEvidence")
    if evidence.source_parameter_sha256 != parameters.parameter_sha256:
        raise ActuationParameterError(
            "Treatment massage/thermal evidence is stale for the current actuation parameter set"
        )
    if evidence.source_sweep_sha256 != sweep.sweep_sha256:
        raise ActuationParameterError(
            "Treatment massage/thermal evidence is stale for the current four-zone sweep"
        )

    validate_measured_massage_mechanics_evidence_bundle(sweep, parameters, evidence.mechanics)
    validate_paired_thermal_mechanical_evidence(
        evidence.thermal, evidence.coupling, sweep, parameters
    )

    expected = build_treatment_massage_thermal_evidence(sweep, parameters)
    if evidence != expected:
        raise ActuationParameterError(
            "Treatment massage/thermal evidence is stale or mixes four-zone sweep provenance"
        )
    return evidence
