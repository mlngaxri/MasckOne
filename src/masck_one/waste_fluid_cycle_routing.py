"""Cycle-resolved routing checks for prime liquid."""
from __future__ import annotations
from dataclasses import dataclass
from .waste_fluid_accounting import WasteFluidAccountingError, WasteFluidBudget
from .waste_fluid_closure import ServiceRoutingClosure, screen_service_routing_closure

@dataclass(frozen=True)
class CycleRoutingScreen:
    cycle: int
    prime_events: int
    prime_residual_mL: float
    prime_external_leakage_mL: float
    minimum_nominal_routed_to_cartridge_mL: float
    minimum_prime_routed_to_cartridge_mL: float
    minimum_total_routed_to_cartridge_mL: float
    residual_ceiling_margin_mL: float
    external_leakage_ceiling_margin_mL: float
    classified_sink_capacity_after_prime_mL: float
    nominal_unclassified_nonrecovery_after_prime_mL: float
    classified_sink_headroom_after_nominal_mL: float
    local_routing_contract_complete: bool

@dataclass(frozen=True)
class CycleResolvedRoutingClosure:
    cycles: tuple[CycleRoutingScreen, ...]
    service: ServiceRoutingClosure

    @property
    def first_incomplete_cycle(self) -> int | None:
        """First cycle whose delivery/recovery routing contract does not close."""
        return next((state.cycle for state in self.cycles if not state.local_routing_contract_complete), None)

    @property
    def all_cycles_routing_complete(self) -> bool:
        return self.first_incomplete_cycle is None

    @property
    def minimum_total_routed_to_cartridge_mL(self) -> float:
        """Minimum liquid explicitly required to reach the cartridge over this profile."""
        return sum(state.minimum_total_routed_to_cartridge_mL for state in self.cycles)

def screen_cycle_resolved_routing_closure(
    budget: WasteFluidBudget,
    *,
    prime_events_by_cycle: tuple[int, ...] | list[int],
    prime_recovery_ratio_contract: float | None = None,
    prime_residual_ratio_contract: float | None = None,
    prime_external_leakage_ratio_contract: float | None = None,
) -> CycleResolvedRoutingClosure:
    """Check routing contracts without averaging sink use across service cycles.

    Each cycle also exposes the minimum liquid contractually routed into the waste
    cartridge. Nominal liquid uses the authority recovery floor; prime liquid is
    credited only when an explicit prime recovery contract exists. This is a
    requirement-level routing load, not a prediction of physically retained volume.
    """
    budget.validate()
    if not isinstance(prime_events_by_cycle, (tuple, list)) or not prime_events_by_cycle:
        raise WasteFluidAccountingError("prime_events_by_cycle must be a nonempty tuple or list")
    if len(prime_events_by_cycle) > budget.service_cycles:
        raise WasteFluidAccountingError(
            "prime_events_by_cycle exceeds configured service life: "
            f"{len(prime_events_by_cycle)} cycles supplied for {budget.service_cycles} service cycles"
        )
    if any(type(count) is not int or count < 0 for count in prime_events_by_cycle):
        raise WasteFluidAccountingError("prime event counts must be nonnegative integers")

    screens: list[CycleRoutingScreen] = []
    for index, prime_events in enumerate(prime_events_by_cycle, start=1):
        local = screen_service_routing_closure(
            budget,
            cycles=1,
            prime_events=prime_events,
            prime_recovery_ratio_contract=prime_recovery_ratio_contract,
            prime_residual_ratio_contract=prime_residual_ratio_contract,
            prime_external_leakage_ratio_contract=prime_external_leakage_ratio_contract,
        )
        classified_after_prime = local.prime_residual_ceiling_margin_mL + local.prime_external_leakage_ceiling_margin_mL
        nominal_unrecovered = budget.maximum_unrecovered_nominal_mL_per_cycle
        nominal_routed = budget.minimum_recovered_mL_per_cycle
        prime_routed = local.minimum_prime_liquid_routed_to_cartridge_mL
        screens.append(CycleRoutingScreen(
            cycle=index,
            prime_events=prime_events,
            prime_residual_mL=local.maximum_prime_residual_mL,
            prime_external_leakage_mL=local.maximum_prime_external_leakage_mL,
            minimum_nominal_routed_to_cartridge_mL=nominal_routed,
            minimum_prime_routed_to_cartridge_mL=prime_routed,
            minimum_total_routed_to_cartridge_mL=nominal_routed + prime_routed,
            residual_ceiling_margin_mL=local.prime_residual_ceiling_margin_mL,
            external_leakage_ceiling_margin_mL=local.prime_external_leakage_ceiling_margin_mL,
            classified_sink_capacity_after_prime_mL=classified_after_prime,
            nominal_unclassified_nonrecovery_after_prime_mL=local.shared_sink_unclassified_nonrecovery_mL,
            classified_sink_headroom_after_nominal_mL=max(0.0, classified_after_prime - nominal_unrecovered),
            local_routing_contract_complete=local.routing_contract_complete,
        ))

    service = screen_service_routing_closure(
        budget,
        cycles=len(prime_events_by_cycle),
        prime_events=sum(prime_events_by_cycle),
        prime_recovery_ratio_contract=prime_recovery_ratio_contract,
        prime_residual_ratio_contract=prime_residual_ratio_contract,
        prime_external_leakage_ratio_contract=prime_external_leakage_ratio_contract,
    )
    return CycleResolvedRoutingClosure(cycles=tuple(screens), service=service)
