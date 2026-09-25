"""Cycle-resolved recovery threshold imposed by shared residual/leakage sinks.

This reducer exposes when nominal recovery must exceed the requirement floor because
prime liquid consumes the same finite residual and external-leakage allowances.
It also checks the resulting higher recovery demand against retained cartridge
capacity, preventing a sink fix from silently creating a storage conflict. This is
requirement arithmetic, not physical validation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_cycle_routing import CycleResolvedRoutingClosure

_TOL = 1e-12


@dataclass(frozen=True, slots=True)
class CycleSinkRecoveryThreshold:
    cycle: int
    cumulative_nominal_introduced_mL: float
    cumulative_prime_residual_mL: float
    cumulative_prime_external_leakage_mL: float
    cumulative_classified_sink_capacity_after_prime_mL: float
    requirement_floor_recovery_mL: float
    minimum_recovery_for_sink_closure_mL: float
    minimum_recovery_ratio_for_sink_closure: float
    additional_recovery_above_requirement_floor_mL: float
    requirement_floor_closes_shared_sinks: bool
    cumulative_prime_routed_to_cartridge_mL: float
    minimum_total_cartridge_routing_at_sink_closure_mL: float
    retained_cartridge_capacity_mL: float
    cartridge_capacity_margin_at_sink_closure_mL: float
    sink_closure_fits_retained_cartridge_capacity: bool


@dataclass(frozen=True, slots=True)
class SinkRecoveryThresholdTrajectory:
    source_routing: CycleResolvedRoutingClosure
    cycles: tuple[CycleSinkRecoveryThreshold, ...]

    def __post_init__(self) -> None:
        if type(self.source_routing) is not CycleResolvedRoutingClosure:
            raise WasteFluidAccountingError("sink threshold trajectory requires exact cycle routing evidence")
        self.source_routing.__post_init__()
        if self.cycles != _derive(self.source_routing):
            raise WasteFluidAccountingError("sink threshold trajectory does not reconcile to routing evidence")

    @property
    def first_cycle_requiring_recovery_above_floor(self) -> int | None:
        return next((state.cycle for state in self.cycles if not state.requirement_floor_closes_shared_sinks), None)

    @property
    def first_cycle_sink_closure_exceeds_cartridge_capacity(self) -> int | None:
        return next((state.cycle for state in self.cycles if not state.sink_closure_fits_retained_cartridge_capacity), None)

    @property
    def all_sink_closure_thresholds_fit_cartridge_capacity(self) -> bool:
        return self.first_cycle_sink_closure_exceeds_cartridge_capacity is None

    @property
    def peak_additional_recovery_above_floor_mL(self) -> float:
        return max(state.additional_recovery_above_requirement_floor_mL for state in self.cycles)

    @property
    def peak_minimum_recovery_ratio_for_sink_closure(self) -> float:
        """Highest cycle-resolved nominal recovery ratio required to close shared sinks."""
        return max(state.minimum_recovery_ratio_for_sink_closure for state in self.cycles)

    @property
    def peak_minimum_recovery_ratio_cycle(self) -> int:
        """Earliest cycle at the peak required recovery ratio."""
        peak = self.peak_minimum_recovery_ratio_for_sink_closure
        return next(
            state.cycle
            for state in self.cycles
            if math.isclose(state.minimum_recovery_ratio_for_sink_closure, peak, rel_tol=0.0, abs_tol=_TOL)
        )


def _derive(routing: CycleResolvedRoutingClosure) -> tuple[CycleSinkRecoveryThreshold, ...]:
    cumulative_introduced = 0.0
    cumulative_floor = 0.0
    cumulative_prime_residual = 0.0
    cumulative_prime_leakage = 0.0
    cumulative_prime_routed = 0.0
    cumulative_classified = 0.0
    cumulative_nominal_unrecovered = 0.0
    retained_capacity: float | None = None
    result: list[CycleSinkRecoveryThreshold] = []

    for state in routing.cycles:
        nominal_unrecovered = (
            state.classified_sink_capacity_after_prime_mL
            + state.nominal_unclassified_nonrecovery_after_prime_mL
            - state.classified_sink_headroom_after_nominal_mL
        )
        local_values = (
            state.minimum_nominal_routed_to_cartridge_mL,
            state.minimum_prime_routed_to_cartridge_mL,
            nominal_unrecovered,
            state.prime_residual_mL,
            state.prime_external_leakage_mL,
            state.classified_sink_capacity_after_prime_mL,
        )
        if any(not math.isfinite(value) or value < -_TOL for value in local_values):
            raise WasteFluidAccountingError(f"cycle {state.cycle} has invalid sink threshold evidence")
        nominal_unrecovered = max(0.0, nominal_unrecovered)
        local_introduced = state.minimum_nominal_routed_to_cartridge_mL + nominal_unrecovered
        if local_introduced <= _TOL:
            raise WasteFluidAccountingError("sink threshold trajectory requires positive nominal introduced liquid")

        capacity_from_minimum = (
            state.cumulative_minimum_cartridge_routing_mL + state.minimum_routing_capacity_margin_mL
        )
        if not math.isfinite(capacity_from_minimum) or capacity_from_minimum < -_TOL:
            raise WasteFluidAccountingError(f"cycle {state.cycle} has invalid retained cartridge capacity evidence")
        if retained_capacity is None:
            retained_capacity = max(0.0, capacity_from_minimum)
        elif not math.isclose(capacity_from_minimum, retained_capacity, rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError("retained cartridge capacity changed within sink threshold trajectory")

        cumulative_introduced += local_introduced
        cumulative_floor += state.minimum_nominal_routed_to_cartridge_mL
        cumulative_nominal_unrecovered += nominal_unrecovered
        cumulative_prime_residual += state.prime_residual_mL
        cumulative_prime_leakage += state.prime_external_leakage_mL
        cumulative_prime_routed += state.minimum_prime_routed_to_cartridge_mL
        cumulative_classified += state.classified_sink_capacity_after_prime_mL

        gap = max(0.0, cumulative_nominal_unrecovered - cumulative_classified)
        threshold = cumulative_floor + gap
        ratio = threshold / cumulative_introduced
        threshold_total_routing = threshold + cumulative_prime_routed
        capacity_margin = retained_capacity - threshold_total_routing
        result.append(CycleSinkRecoveryThreshold(
            cycle=state.cycle,
            cumulative_nominal_introduced_mL=cumulative_introduced,
            cumulative_prime_residual_mL=cumulative_prime_residual,
            cumulative_prime_external_leakage_mL=cumulative_prime_leakage,
            cumulative_classified_sink_capacity_after_prime_mL=cumulative_classified,
            requirement_floor_recovery_mL=cumulative_floor,
            minimum_recovery_for_sink_closure_mL=threshold,
            minimum_recovery_ratio_for_sink_closure=ratio,
            additional_recovery_above_requirement_floor_mL=gap,
            requirement_floor_closes_shared_sinks=gap <= _TOL,
            cumulative_prime_routed_to_cartridge_mL=cumulative_prime_routed,
            minimum_total_cartridge_routing_at_sink_closure_mL=threshold_total_routing,
            retained_cartridge_capacity_mL=retained_capacity,
            cartridge_capacity_margin_at_sink_closure_mL=capacity_margin,
            sink_closure_fits_retained_cartridge_capacity=capacity_margin >= -_TOL,
        ))

    if not result:
        raise WasteFluidAccountingError("sink threshold trajectory requires at least one cycle")
    final = result[-1]
    service = routing.service
    if not math.isclose(final.requirement_floor_recovery_mL,
                        service.minimum_nominal_liquid_routed_to_cartridge_mL,
                        rel_tol=0.0, abs_tol=_TOL):
        raise WasteFluidAccountingError("cycle threshold recovery floor does not reconcile to service evidence")
    if not math.isclose(final.additional_recovery_above_requirement_floor_mL,
                        service.shared_sink_unclassified_nonrecovery_mL,
                        rel_tol=0.0, abs_tol=_TOL):
        raise WasteFluidAccountingError("cycle threshold sink deficit does not reconcile to service evidence")
    if not math.isclose(final.cumulative_prime_routed_to_cartridge_mL,
                        service.minimum_prime_liquid_routed_to_cartridge_mL,
                        rel_tol=0.0, abs_tol=_TOL):
        raise WasteFluidAccountingError("cycle threshold prime cartridge routing does not reconcile to service evidence")
    return tuple(result)


def evaluate_sink_recovery_threshold_trajectory(
    routing: CycleResolvedRoutingClosure,
) -> SinkRecoveryThresholdTrajectory:
    """Derive shared-sink recovery and resulting cartridge-capacity demand per cycle."""
    if type(routing) is not CycleResolvedRoutingClosure:
        raise WasteFluidAccountingError("sink threshold trajectory requires exact cycle routing evidence")
    routing.__post_init__()
    result = SinkRecoveryThresholdTrajectory(routing, _derive(routing))
    result.__post_init__()
    return result
