"""Typed CLEAN/recovery to thermal-control integration boundary."""
from __future__ import annotations

from .actuation_parameters import ActuationParameterSet
from .actuation_zone_sweep import FourZoneImpedanceSweep
from .authority import Authority
from .cleanser_storage import CleanserStorageArchitecture
from .coverage import FacialCoverageMesh
from .distribution_manifold import DistributionManifoldArchitecture
from .fresh_pump_packaging import FreshPumpPackagingArchitecture
from .protected_volumes import ProtectedVolumeSet
from .structural_frame import StructuralFrameTopology
from .thermal_control import ThermalCommand, ThermalCommandInterlock
from .treatment_full_evidence import FullTreatmentEvidence, validate_full_treatment_evidence
from .treatment_integrated_evidence import (
    IntegratedTreatmentEvidence,
    validate_integrated_treatment_evidence,
)
from .treatment_recovery_readiness import TreatmentRecoveryReadiness
from .water_reservoir import WaterReservoirArchitecture
from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_capacity_reserve import CapacityReservedOverflowGuard
from .waste_fluid_overflow_guard import CartridgeOverflowGuard


def command_thermal_after_treatment(interlock: ThermalCommandInterlock, readiness: TreatmentRecoveryReadiness, *, warm_requested: bool, cool_requested: bool) -> ThermalCommand:
    """Arbitrate WARM/COOL only from reserve-aware recovery-capacity evidence."""
    if type(interlock) is not ThermalCommandInterlock:
        raise WasteFluidAccountingError("treatment thermal handoff requires exact ThermalCommandInterlock")
    if type(readiness) is not TreatmentRecoveryReadiness:
        raise WasteFluidAccountingError("treatment thermal handoff requires exact TreatmentRecoveryReadiness")
    if type(warm_requested) is not bool or type(cool_requested) is not bool:
        raise WasteFluidAccountingError("treatment thermal requests must be exact booleans")
    readiness.__post_init__()
    if type(readiness.source_capacity_guard) is not CartridgeOverflowGuard:
        raise WasteFluidAccountingError("treatment thermal handoff requires reserve-aware CartridgeOverflowGuard evidence")
    return interlock.command(warm_requested=warm_requested, cool_requested=cool_requested, recovery_complete=readiness.post_recovery_handoff_permitted)


def command_thermal_from_integrated_treatment_evidence(
    interlock: ThermalCommandInterlock,
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    evidence: IntegratedTreatmentEvidence,
    *,
    warm_requested: bool,
    cool_requested: bool,
) -> ThermalCommand:
    """Arbitrate thermal output only after validating massage/thermal and recovery evidence."""
    validate_integrated_treatment_evidence(sweep, parameters, evidence)
    return command_thermal_after_treatment(
        interlock,
        evidence.recovery,
        warm_requested=warm_requested,
        cool_requested=cool_requested,
    )


def command_thermal_from_full_treatment_evidence(
    interlock: ThermalCommandInterlock,
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    evidence: FullTreatmentEvidence,
    *,
    authority: Authority,
    manifold: DistributionManifoldArchitecture,
    pump: FreshPumpPackagingArchitecture,
    water: WaterReservoirArchitecture,
    cleanser: CleanserStorageArchitecture,
    frame: StructuralFrameTopology,
    coverage: FacialCoverageMesh,
    protected: ProtectedVolumeSet,
    warm_requested: bool,
    cool_requested: bool,
) -> ThermalCommand:
    """Command WARM/COOL only from the complete current treatment evidence tree.

    This engineering boundary revalidates canonical CLEAN outlet distribution, shared
    capacity-aware recovery qualification, measured four-zone massage mechanics, and
    thermal coexistence immediately before the command is issued. Scalar capacity
    reserve guards remain accepted here for engineering sweeps; production callers
    should use ``command_thermal_from_reserved_full_treatment_evidence``.
    """
    validate_full_treatment_evidence(
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
    return command_thermal_after_treatment(
        interlock,
        evidence.integrated.recovery,
        warm_requested=warm_requested,
        cool_requested=cool_requested,
    )


def command_thermal_from_reserved_full_treatment_evidence(
    interlock: ThermalCommandInterlock,
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    evidence: FullTreatmentEvidence,
    *,
    authority: Authority,
    manifold: DistributionManifoldArchitecture,
    pump: FreshPumpPackagingArchitecture,
    water: WaterReservoirArchitecture,
    cleanser: CleanserStorageArchitecture,
    frame: StructuralFrameTopology,
    coverage: FacialCoverageMesh,
    protected: ProtectedVolumeSet,
    warm_requested: bool,
    cool_requested: bool,
) -> ThermalCommand:
    """Production command boundary requiring full treatment and typed reserve provenance.

    In addition to complete CLEAN, recovery, massage, and thermal revalidation, this
    boundary requires the shared recovery tree to retain the composition-bound
    ``CapacityReservedOverflowGuard``. A scalar cartridge reserve cannot therefore
    cross the production whole-treatment command boundary.
    """
    validate_full_treatment_evidence(
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
    readiness = evidence.integrated.recovery
    reserve_evidence = readiness.source_capacity_reserve_evidence
    if type(reserve_evidence) is not CapacityReservedOverflowGuard:
        raise WasteFluidAccountingError(
            "reserved full treatment thermal handoff requires typed CapacityReservedOverflowGuard evidence"
        )
    if readiness.source_capacity_guard is not reserve_evidence.guard:
        raise WasteFluidAccountingError(
            "reserved full treatment thermal handoff requires recovery bound to the exact reserve guard"
        )
    return command_thermal_after_treatment(
        interlock,
        readiness,
        warm_requested=warm_requested,
        cool_requested=cool_requested,
    )
