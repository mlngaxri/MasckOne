"""Atomic CLEAN evidence across canonical outlet distribution and recovery readiness."""
from __future__ import annotations

from dataclasses import dataclass

from .authority import Authority
from .cleanser_storage import CleanserStorageArchitecture
from .coverage import FacialCoverageMesh
from .distribution_geometry import DistributionGeometryArchitecture, DistributionGeometryError
from .distribution_geometry_evidence import validate_canonical_distribution_geometry
from .distribution_manifold import DistributionManifoldArchitecture
from .fresh_pump_packaging import FreshPumpPackagingArchitecture
from .protected_volumes import ProtectedVolumeSet
from .structural_frame import StructuralFrameTopology
from .treatment_recovery_readiness import TreatmentRecoveryReadiness
from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_overflow_guard import CartridgeOverflowGuard
from .water_reservoir import WaterReservoirArchitecture


@dataclass(frozen=True, slots=True)
class TreatmentCleanDistributionEvidence:
    """One fail-closed CLEAN view spanning delivery geometry and recovery readiness."""

    distribution: DistributionGeometryArchitecture
    recovery: TreatmentRecoveryReadiness
    source_distribution_sha256: str


def _validate_recovery(recovery: TreatmentRecoveryReadiness) -> None:
    if type(recovery) is not TreatmentRecoveryReadiness:
        raise WasteFluidAccountingError(
            "CLEAN distribution evidence requires exact TreatmentRecoveryReadiness"
        )
    recovery.__post_init__()
    if type(recovery.source_capacity_guard) is not CartridgeOverflowGuard:
        raise WasteFluidAccountingError(
            "CLEAN distribution evidence requires reserve-aware CartridgeOverflowGuard evidence"
        )


def build_treatment_clean_distribution_evidence(
    geometry: DistributionGeometryArchitecture,
    recovery: TreatmentRecoveryReadiness,
    *,
    authority: Authority,
    manifold: DistributionManifoldArchitecture,
    pump: FreshPumpPackagingArchitecture,
    water: WaterReservoirArchitecture,
    cleanser: CleanserStorageArchitecture,
    frame: StructuralFrameTopology,
    coverage: FacialCoverageMesh,
    protected: ProtectedVolumeSet,
) -> TreatmentCleanDistributionEvidence:
    """Bind canonical delivery placement and capacity-aware recovery evidence."""
    validate_canonical_distribution_geometry(
        geometry,
        authority=authority,
        manifold=manifold,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=coverage,
        protected=protected,
    )
    _validate_recovery(recovery)
    return TreatmentCleanDistributionEvidence(
        distribution=geometry,
        recovery=recovery,
        source_distribution_sha256=geometry.architecture_sha256,
    )


def validate_treatment_clean_distribution_evidence(
    evidence: TreatmentCleanDistributionEvidence,
    *,
    authority: Authority,
    manifold: DistributionManifoldArchitecture,
    pump: FreshPumpPackagingArchitecture,
    water: WaterReservoirArchitecture,
    cleanser: CleanserStorageArchitecture,
    frame: StructuralFrameTopology,
    coverage: FacialCoverageMesh,
    protected: ProtectedVolumeSet,
) -> TreatmentCleanDistributionEvidence:
    """Reject stale or independently substituted CLEAN delivery/recovery evidence."""
    if type(evidence) is not TreatmentCleanDistributionEvidence:
        raise TypeError("evidence must be exact TreatmentCleanDistributionEvidence")
    validate_canonical_distribution_geometry(
        evidence.distribution,
        authority=authority,
        manifold=manifold,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=coverage,
        protected=protected,
    )
    _validate_recovery(evidence.recovery)
    if evidence.source_distribution_sha256 != evidence.distribution.architecture_sha256:
        raise DistributionGeometryError(
            "CLEAN distribution evidence digest does not match canonical distribution geometry"
        )
    return evidence
