"""Whole-treatment evidence binding CLEAN delivery/recovery to massage and thermal evidence."""
from __future__ import annotations

from dataclasses import dataclass

from .actuation_parameters import ActuationParameterSet
from .actuation_zone_sweep import FourZoneImpedanceSweep
from .authority import Authority
from .cleanser_storage import CleanserStorageArchitecture
from .coverage import FacialCoverageMesh
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
    """Build only when CLEAN and massage/thermal share the exact recovery evidence object."""
    evidence = FullTreatmentEvidence(clean=clean, integrated=integrated)
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
    """Reject stale subsystem evidence or independently substituted recovery qualification."""
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
    return evidence
