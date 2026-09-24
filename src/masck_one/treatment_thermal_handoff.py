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

    This is the strongest treatment-facing thermal boundary. It revalidates canonical
    CLEAN outlet distribution, shared capacity-aware recovery qualification, measured
    four-zone massage mechanics, and thermal coexistence immediately before the
    command is issued. No acceptance threshold or thermal policy is changed here.
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
