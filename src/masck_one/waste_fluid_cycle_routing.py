"""Cycle-resolved routing checks for prime liquid."""
from __future__ import annotations
import math
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
    cumulative_minimum_cartridge_routing_mL: float
    cumulative_maximum_cartridge_inflow_mL: float
    cartridge_occupancy_uncertainty_mL: float
    minimum_routing_capacity_margin_mL: float
    minimum_routing_capacity_satisfied: bool
    cartridge_capacity_margin_mL: float
    cartridge_capacity_satisfied: bool
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
    def first_unavoidable_cartridge_capacity_exceeded_cycle(self) -> int | None:
        """First cycle where contractual minimum routing alone exceeds capacity."""
        return next((state.cycle for state in self.cycles if not state.minimum_routing_capacity_satisfied), None)

    @property
    def all_cycles_minimum_routing_capacity_satisfied(self) -> bool:
        return self.first_unavoidable_cartridge_capacity_exceeded_cycle is None

    @property
    def first_cartridge_capacity_exceeded_cycle(self) -> int | None:
        """First cycle whose fail-conservative cumulative inflow exceeds capacity."""
        return next((state.cycle for state in self.cycles if not state.cartridge_capacity_satisfied), None)

    @property
    def all_cycles_cartridge_capacity_satisfied(self) -> bool:
        return self.first_cartridge_capacity_exceeded_cycle is None

    @property
    def minimum_total_routed_to_cartridge_mL(self) -> float:
        """Minimum liquid explicitly required to reach the cartridge over this profile."""
        return sum(state.minimum_total_routed_to_cartridge_mL for state in self.cycles)

    @property
    def total_prime_residual_mL(self) -> float:
        return sum(state.prime_residual_mL for state in self.cycles)

    @property
    def total_prime_external_leakage_mL(self) -> float:
        return sum(state.prime_external_leakage_mL for state in self.cycles)


def _assert_cycle_service_parity(cycle_closure: CycleResolvedRoutingClosure) -> None:
    """Fail if cycle-local accounting drifts from the aggregate service ledger."""
    service = cycle_closure.service
    checks = (
        (
            "minimum cartridge routing",
            cycle_closure.minimum_total_routed_to_cartridge_mL,
            service.minimum_nominal_liquid_routed_to_cartridge_mL
            + service.minimum_prime_liquid_routed_to_cartridge_mL,
        ),
        ("prime residual", cycle_closure.total_prime_residual_mL, service.maximum_prime_residual_mL),
        ("prime external leakage", cycle_closure.total_prime_external_leakage_mL, service.maximum_prime_external_leakage_mL),
    )
    for label, cycle_value, service_value in checks:
        if not math.isclose(cycle_value, service_value, rel_tol=0.0, abs_tol=1e-12):
            raise WasteFluidAccountingError(
                f"cycle/service routing parity failure for {label}: cycle total {cycle_value:.12g} mL != service total {service_value:.12g} mL"
            )
    if not math.isclose(
        cycle_closure.cycles[-1].cumulative_minimum_cartridge_routing_mL,
        cycle_closure.minimum_total_routed_to_cartridge_mL,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise WasteFluidAccountingError("cycle cumulative minimum cartridge routing does not reconcile to service total")


def screen_cycle_resolved_routing_closure(
    budget: WasteFluidBudget,
    *,
    prime_events_by_cycle: tuple[int, ...] | list[int],
    prime_recovery_ratio_contract: float | None = None,
    prime_residual_ratio_contract: float | None = None,
    prime_external_leakage_ratio_contract: float | None = None,
) -> CycleResolvedRoutingClosure:
    """Check routing contracts and cumulative cartridge capacity cycle by cycle.

    Minimum routing uses contractual recovery. Capacity uses the independent
    fail-conservative bound that charges every introduced nominal and prime volume
    to the cartridge, so sink allocations never create fictitious capacity credit.
    Both bounds are screened against capacity: a lower-bound failure is unavoidable
    under the supplied routing contract, while an upper-bound failure only means the
    fail-conservative capacity screen cannot prove fit. The interval between them
    remains an uncertainty range rather than a retained-volume prediction.
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
    cumulative_minimum_routing = 0.0
    cumulative_maximum_inflow = 0.0
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
        local_minimum_routing = nominal_routed + prime_routed
        cumulative_minimum_routing += local_minimum_routing
        cumulative_maximum_inflow += budget.nominal_introduced_mL_per_cycle + prime_events * budget.maximum_initial_prime_mL_per_cycle
        occupancy_uncertainty = cumulative_maximum_inflow - cumulative_minimum_routing
        if occupancy_uncertainty < -1e-12:
            raise WasteFluidAccountingError(
                "minimum contractual cartridge routing exceeds fail-conservative introduced-volume bound"
            )
        minimum_capacity_margin = budget.cartridge_retained_capacity_requirement_mL - cumulative_minimum_routing
        capacity_margin = budget.cartridge_retained_capacity_requirement_mL - cumulative_maximum_inflow
        screens.append(CycleRoutingScreen(
            cycle=index,
            prime_events=prime_events,
            prime_residual_mL=local.maximum_prime_residual_mL,
            prime_external_leakage_mL=local.maximum_prime_external_leakage_mL,
            minimum_nominal_routed_to_cartridge_mL=nominal_routed,
            minimum_prime_routed_to_cartridge_mL=prime_routed,
            minimum_total_routed_to_cartridge_mL=local_minimum_routing,
            cumulative_minimum_cartridge_routing_mL=cumulative_minimum_routing,
            cumulative_maximum_cartridge_inflow_mL=cumulative_maximum_inflow,
            cartridge_occupancy_uncertainty_mL=max(0.0, occupancy_uncertainty),
            minimum_routing_capacity_margin_mL=minimum_capacity_margin,
            minimum_routing_capacity_satisfied=minimum_capacity_margin >= -1e-12,
            cartridge_capacity_margin_mL=capacity_margin,
            cartridge_capacity_satisfied=capacity_margin >= -1e-12,
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
    result = CycleResolvedRoutingClosure(cycles=tuple(screens), service=service)
    _assert_cycle_service_parity(result)
    return result
