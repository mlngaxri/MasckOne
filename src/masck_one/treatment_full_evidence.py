"""Whole-treatment evidence binding CLEAN delivery/recovery to massage and thermal evidence."""
from __future__ import annotations

from dataclasses import dataclass

from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_zone_sweep import FourZoneImpedanceSweep
from .authority import Authority
from .cleanser_storage import CleanserStorageArchitecture
from .coverage import FacialCoverageMesh
from .distribution_geometry import DistributionGeometryError
from .distribution_manifold import DistributionManifoldArchitecture
from .fresh_pump_packaging import FreshPumpPackagingArchitecture
from .protected_volumes import ProtectedVolumeSet
from .structural_frame import StructuralFrameTopology
from .treatment_clean_distribution_evidence import (
    TreatmentCleanDistributionEvidence,
    validate_treatment_clean_distribution_evidence,
)
from .treatment_integrated_evidence import (
    IntegratedTreatmentEvidence,
    validate_integrated_treatment_evidence,
)
from .water_reservoir import WaterReservoirArchitecture
from .waste_fluid_accounting import WasteFluidAccountingError


@dataclass(frozen=True, slots=True)
class FullTreatmentEvidence:
    """Atomic evidence tree for CLEAN delivery/recovery and massage/thermal operation."""

    clean: TreatmentCleanDistributionEvidence
    integrated: IntegratedTreatmentEvidence
    source_distribution_sha256: str
    source_parameter_sha256: str
    source_sweep_sha256: str


def build_full_treatment_evidence(
    clean: TreatmentCleanDistributionEvidence,
    integrated: IntegratedTreatmentEvidence,
    *,
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    authority: Authority,
    manifold: DistributionManifoldArchitecture,
    pump: FreshPumpPackagingArchitecture,
    water: WaterReservoirArchitecture,
    cleanser: CleanserStorageArchitecture,
    frame: StructuralFrameTopology,
    coverage: FacialCoverageMesh,
    protected: ProtectedVolumeSet,
) -> FullTreatmentEvidence:
    """Build only when CLEAN and massage/thermal share recovery and source provenance."""
    evidence = FullTreatmentEvidence(
        clean=clean,
        integrated=integrated,
        source_distribution_sha256=clean.source_distribution_sha256,
        source_parameter_sha256=integrated.source_parameter_sha256,
        source_sweep_sha256=integrated.source_sweep_sha256,
    )
    return validate_full_treatment_evidence(
        evidence,
        sweep=sweep,
        parameters=parameters,
        authority=authority,
        manifold=manifold,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=coverage,
        protected=protected,
    )


def validate_full_treatment_evidence(
    evidence: FullTreatmentEvidence,
    *,
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    authority: Authority,
    manifold: DistributionManifoldArchitecture,
    pump: FreshPumpPackagingArchitecture,
    water: WaterReservoirArchitecture,
    cleanser: CleanserStorageArchitecture,
    frame: StructuralFrameTopology,
    coverage: FacialCoverageMesh,
    protected: ProtectedVolumeSet,
) -> FullTreatmentEvidence:
    """Reject stale subsystem evidence, source provenance, or substituted recovery qualification."""
    if type(evidence) is not FullTreatmentEvidence:
        raise TypeError("evidence must be exact FullTreatmentEvidence")
    validate_treatment_clean_distribution_evidence(
        evidence.clean,
        authority=authority,
        manifold=manifold,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=coverage,
        protected=protected,
    )
    validate_integrated_treatment_evidence(sweep, parameters, evidence.integrated)
    if evidence.clean.recovery is not evidence.integrated.recovery:
        raise WasteFluidAccountingError(
            "full treatment evidence requires one shared recovery qualification instance"
        )
    if evidence.source_distribution_sha256 != evidence.clean.source_distribution_sha256:
        raise DistributionGeometryError(
            "full treatment evidence does not match CLEAN distribution provenance"
        )
    if evidence.source_parameter_sha256 != evidence.integrated.source_parameter_sha256:
        raise ActuationParameterError(
            "full treatment evidence does not match actuation parameter provenance"
        )
    if evidence.source_sweep_sha256 != evidence.integrated.source_sweep_sha256:
        raise ActuationParameterError(
            "full treatment evidence does not match four-zone sweep provenance"
        )
    return evidence
