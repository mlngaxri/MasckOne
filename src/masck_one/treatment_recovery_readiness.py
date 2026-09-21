"""Fail-closed recovery readiness for treatment subsystem handoff."""
from __future__ import annotations
from dataclasses import dataclass
from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_cycle_evidence import validate_cycle_routing_evidence
from .waste_fluid_cycle_routing import CycleResolvedRoutingClosure
from .waste_fluid_overflow_guard import CartridgeOverflowGuard


def _derive_blocker(closure: CycleResolvedRoutingClosure) -> tuple[int | None, str | None]:
    incomplete = closure.first_incomplete_cycle
    unavoidable = closure.first_unavoidable_cartridge_capacity_exceeded_cycle
    conservative = closure.first_cartridge_capacity_exceeded_cycle
    if incomplete is not None:
        return incomplete, "routing contract incomplete"
    if unavoidable is not None:
        return unavoidable, "minimum contractual cartridge routing exceeds retained capacity"
    if conservative is not None:
        return conservative, "fail-conservative cartridge inflow exceeds retained capacity"
    return None, None


def _derive_guard_blocker(guard: CartridgeOverflowGuard) -> tuple[int | None, str | None]:
    incomplete = guard.routing.first_incomplete_cycle
    if incomplete is not None:
        return incomplete, "routing contract incomplete"
    if guard.first_unavoidable_overflow_cycle is not None:
        return guard.first_unavoidable_overflow_cycle, "minimum contractual cartridge routing exceeds usable capacity"
    if guard.first_conservative_capacity_failure_cycle is not None:
        return guard.first_conservative_capacity_failure_cycle, "fail-conservative cartridge inflow exceeds usable capacity"
    return None, None


@dataclass(frozen=True, slots=True)
class TreatmentRecoveryReadiness:
    source_closure: CycleResolvedRoutingClosure
    routing_complete: bool
    minimum_routing_capacity_satisfied: bool
    conservative_capacity_satisfied: bool
    post_recovery_handoff_permitted: bool
    blocking_cycle: int | None
    blocking_reason: str | None
    source_capacity_guard: CartridgeOverflowGuard | None = None

    def __post_init__(self) -> None:
        if type(self.source_closure) is not CycleResolvedRoutingClosure:
            raise WasteFluidAccountingError("treatment recovery readiness requires exact source CycleResolvedRoutingClosure")
        validate_cycle_routing_evidence(self.source_closure)
        for name, value in (("routing_complete", self.routing_complete), ("minimum_routing_capacity_satisfied", self.minimum_routing_capacity_satisfied), ("conservative_capacity_satisfied", self.conservative_capacity_satisfied), ("post_recovery_handoff_permitted", self.post_recovery_handoff_permitted)):
            if type(value) is not bool:
                raise WasteFluidAccountingError(f"{name} must be an exact bool")
        if self.blocking_cycle is not None and (type(self.blocking_cycle) is not int or self.blocking_cycle <= 0):
            raise WasteFluidAccountingError("blocking_cycle must be a positive integer or None")
        if self.blocking_reason is not None and (type(self.blocking_reason) is not str or not self.blocking_reason.strip()):
            raise WasteFluidAccountingError("blocking_reason must be a non-empty string or None")
        if self.source_capacity_guard is not None:
            if type(self.source_capacity_guard) is not CartridgeOverflowGuard:
                raise WasteFluidAccountingError("source_capacity_guard must be exact CartridgeOverflowGuard evidence or None")
            if self.source_capacity_guard.routing is not self.source_closure:
                raise WasteFluidAccountingError("capacity guard must bind the exact source routing closure")
            expected_cycle, expected_reason = _derive_guard_blocker(self.source_capacity_guard)
            expected = (self.source_closure.all_cycles_routing_complete, not self.source_capacity_guard.unavoidable_overflow, self.source_capacity_guard.capacity_proven_by_conservative_screen, expected_cycle is None, expected_cycle, expected_reason)
        else:
            expected_cycle, expected_reason = _derive_blocker(self.source_closure)
            expected = (self.source_closure.all_cycles_routing_complete, self.source_closure.all_cycles_minimum_routing_capacity_satisfied, self.source_closure.all_cycles_cartridge_capacity_satisfied, expected_cycle is None, expected_cycle, expected_reason)
        supplied = (self.routing_complete, self.minimum_routing_capacity_satisfied, self.conservative_capacity_satisfied, self.post_recovery_handoff_permitted, self.blocking_cycle, self.blocking_reason)
        if supplied != expected:
            raise WasteFluidAccountingError("treatment recovery readiness fields must exactly match source routing closure")


def screen_treatment_recovery_readiness(evidence: CycleResolvedRoutingClosure | CartridgeOverflowGuard) -> TreatmentRecoveryReadiness:
    """Qualify CLEAN/recovery evidence; reserve-aware guards are retained for handoff."""
    if type(evidence) is CartridgeOverflowGuard:
        closure = evidence.routing
        validate_cycle_routing_evidence(closure)
        blocking_cycle, reason = _derive_guard_blocker(evidence)
        return TreatmentRecoveryReadiness(source_closure=closure, routing_complete=closure.all_cycles_routing_complete, minimum_routing_capacity_satisfied=not evidence.unavoidable_overflow, conservative_capacity_satisfied=evidence.capacity_proven_by_conservative_screen, post_recovery_handoff_permitted=blocking_cycle is None, blocking_cycle=blocking_cycle, blocking_reason=reason, source_capacity_guard=evidence)
    if type(evidence) is not CycleResolvedRoutingClosure:
        raise WasteFluidAccountingError("treatment recovery readiness requires exact CycleResolvedRoutingClosure or CartridgeOverflowGuard")
    validate_cycle_routing_evidence(evidence)
    blocking_cycle, reason = _derive_blocker(evidence)
    return TreatmentRecoveryReadiness(source_closure=evidence, routing_complete=evidence.all_cycles_routing_complete, minimum_routing_capacity_satisfied=evidence.all_cycles_minimum_routing_capacity_satisfied, conservative_capacity_satisfied=evidence.all_cycles_cartridge_capacity_satisfied, post_recovery_handoff_permitted=blocking_cycle is None, blocking_cycle=blocking_cycle, blocking_reason=reason)
