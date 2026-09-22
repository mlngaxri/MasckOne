"""Bind treatment recovery readiness to the service-level recovery requirement.

This is a digital requirement-consistency gate. It does not claim measured recovery,
leakage, residual-liquid, or cartridge performance.
"""
from __future__ import annotations

from dataclasses import dataclass

from .treatment_recovery_readiness import TreatmentRecoveryReadiness
from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_cycle_evidence import validate_cycle_routing_evidence
from .waste_fluid_recovery_requirement import ServiceRecoveryRequirement

_RECOVERY_REQUIREMENT_BLOCKER = "authority recovery floor does not close residual and leakage sink budget"


@dataclass(frozen=True, slots=True)
class RecoveryRequirementQualifiedReadiness:
    """Post-recovery handoff qualified by routing, capacity, and sink closure."""

    source_readiness: TreatmentRecoveryReadiness
    source_recovery_requirement: ServiceRecoveryRequirement
    recovery_requirement_satisfied: bool
    post_recovery_handoff_permitted: bool
    blocking_cycle: int | None
    blocking_reason: str | None

    def __post_init__(self) -> None:
        if type(self.source_readiness) is not TreatmentRecoveryReadiness:
            raise WasteFluidAccountingError("qualified readiness requires exact TreatmentRecoveryReadiness evidence")
        if type(self.source_recovery_requirement) is not ServiceRecoveryRequirement:
            raise WasteFluidAccountingError("qualified readiness requires exact ServiceRecoveryRequirement evidence")
        validate_cycle_routing_evidence(self.source_readiness.source_closure)
        # Trigger the requirement object's complete provenance/arithmetic validation.
        self.source_recovery_requirement.__post_init__()

        routing_service = self.source_readiness.source_closure.service
        requirement_service = self.source_recovery_requirement.source
        if routing_service != requirement_service:
            raise WasteFluidAccountingError(
                "recovery requirement must describe the same service routing contract as treatment readiness"
            )
        if requirement_service.cycles != len(self.source_readiness.source_closure.cycles):
            raise WasteFluidAccountingError("recovery requirement cycle count does not match cycle-resolved routing")
        if requirement_service.prime_events != sum(
            state.prime_events for state in self.source_readiness.source_closure.cycles
        ):
            raise WasteFluidAccountingError("recovery requirement prime-event count does not match cycle-resolved routing")

        expected_recovery = self.source_recovery_requirement.recovery_requirement_closes
        if self.source_readiness.post_recovery_handoff_permitted:
            expected_cycle = None
            expected_reason = None if expected_recovery else _RECOVERY_REQUIREMENT_BLOCKER
        else:
            expected_cycle = self.source_readiness.blocking_cycle
            expected_reason = self.source_readiness.blocking_reason
        expected_permitted = self.source_readiness.post_recovery_handoff_permitted and expected_recovery

        if type(self.recovery_requirement_satisfied) is not bool:
            raise WasteFluidAccountingError("recovery_requirement_satisfied must be an exact bool")
        if type(self.post_recovery_handoff_permitted) is not bool:
            raise WasteFluidAccountingError("post_recovery_handoff_permitted must be an exact bool")
        supplied = (
            self.recovery_requirement_satisfied,
            self.post_recovery_handoff_permitted,
            self.blocking_cycle,
            self.blocking_reason,
        )
        expected = (expected_recovery, expected_permitted, expected_cycle, expected_reason)
        if supplied != expected:
            raise WasteFluidAccountingError("qualified readiness fields must exactly match bound source evidence")


def qualify_treatment_recovery_requirement(
    readiness: TreatmentRecoveryReadiness,
    requirement: ServiceRecoveryRequirement,
) -> RecoveryRequirementQualifiedReadiness:
    """Require service sink closure before permitting the post-recovery handoff."""
    if type(readiness) is not TreatmentRecoveryReadiness:
        raise WasteFluidAccountingError("qualified readiness requires exact TreatmentRecoveryReadiness evidence")
    if type(requirement) is not ServiceRecoveryRequirement:
        raise WasteFluidAccountingError("qualified readiness requires exact ServiceRecoveryRequirement evidence")

    recovery_ok = requirement.recovery_requirement_closes
    if readiness.post_recovery_handoff_permitted:
        blocking_cycle = None
        blocking_reason = None if recovery_ok else _RECOVERY_REQUIREMENT_BLOCKER
    else:
        blocking_cycle = readiness.blocking_cycle
        blocking_reason = readiness.blocking_reason

    return RecoveryRequirementQualifiedReadiness(
        source_readiness=readiness,
        source_recovery_requirement=requirement,
        recovery_requirement_satisfied=recovery_ok,
        post_recovery_handoff_permitted=readiness.post_recovery_handoff_permitted and recovery_ok,
        blocking_cycle=blocking_cycle,
        blocking_reason=blocking_reason,
    )
