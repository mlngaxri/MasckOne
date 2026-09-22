"""Cycle-resolved recovery threshold imposed by shared residual/leakage sinks.

This reducer exposes when nominal recovery must exceed the requirement floor because
prime liquid consumes the same finite residual and external-leakage allowances.
It is requirement arithmetic, not physical recovery or leakage evidence.
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
    classified_sink_capacity_after_prime_mL: float
    requirement_floor_recovery_mL: float
    minimum_recovery_for_sink_closure_mL: float
    minimum_recovery_ratio_for_sink_closure: float
    additional_recovery_above_requirement_floor_mL: float
    requirement_floor_closes_shared_sinks: bool


@dataclass(frozen=True, slots=True)
class SinkRecoveryThresholdTrajectory:
    source_routing: CycleResolvedRoutingClosure
    cycles: tuple[CycleSinkRecoveryThreshold, ...]

    def __post_init__(self) -> None:
        if type(self.source_routing) is not CycleResolvedRoutingClosure:
            raise WasteFluidAccountingError("sink threshold trajectory requires exact cycle routing evidence")
        self.source_routing.__post_init__()
        expected = _derive(self.source_routing)
        if self.cycles != expected:
            raise WasteFluidAccountingError("sink threshold trajectory does not reconcile to routing evidence")

    @property
    def first_cycle_requiring_recovery_above_floor(self) -> int | None:
        return next((state.cycle for state in self.cycles if not state.requirement_floor_closes_shared_sinks), None)

    @property
    def peak_additional_recovery_above_floor_mL(self) -> float:
        return max(state.additional_recovery_above_requirement_floor_mL for state in self.cycles)


def _derive(routing: CycleResolvedRoutingClosure) -> tuple[CycleSinkRecoveryThreshold, ...]:
    service = routing.service
    cycles = len(routing.cycles)
    if cycles <= 0:
        raise WasteFluidAccountingError("sink threshold trajectory requires at least one cycle")
    nominal_per_cycle = service.service_nominal_introduced_mL / cycles
    recovery_floor_per_cycle = service.minimum_nominal_liquid_routed_to_cartridge_mL / cycles
    residual_ceiling_per_cycle = service.service_residual_ceiling_mL / cycles
    leakage_ceiling_per_cycle = service.service_external_leakage_ceiling_mL / cycles
    values = (nominal_per_cycle, recovery_floor_per_cycle, residual_ceiling_per_cycle, leakage_ceiling_per_cycle)
    if any(not math.isfinite(value) or value < -_TOL for value in values) or nominal_per_cycle <= _TOL:
        raise WasteFluidAccountingError("sink threshold trajectory requires finite positive nominal service accounting")

    cumulative_prime_residual = 0.0
    cumulative_prime_leakage = 0.0
    result: list[CycleSinkRecoveryThreshold] = []
    for state in routing.cycles:
        cumulative_prime_residual += state.prime_residual_mL
        cumulative_prime_leakage += state.prime_external_leakage_mL
        residual_capacity = state.cycle * residual_ceiling_per_cycle - cumulative_prime_residual
        leakage_capacity = state.cycle * leakage_ceiling_per_cycle - cumulative_prime_leakage
        if residual_capacity < -_TOL or leakage_capacity < -_TOL:
            raise WasteFluidAccountingError(f"prime routing exceeds a shared sink ceiling by cycle {state.cycle}")
        classified = max(0.0, residual_capacity) + max(0.0, leakage_capacity)
        introduced = state.cycle * nominal_per_cycle
        floor = state.cycle * recovery_floor_per_cycle
        threshold = max(0.0, introduced - classified)
        ratio = threshold / introduced
        additional = max(0.0, threshold - floor)
        result.append(CycleSinkRecoveryThreshold(
            cycle=state.cycle,
            cumulative_nominal_introduced_mL=introduced,
            cumulative_prime_residual_mL=cumulative_prime_residual,
            cumulative_prime_external_leakage_mL=cumulative_prime_leakage,
            classified_sink_capacity_after_prime_mL=classified,
            requirement_floor_recovery_mL=floor,
            minimum_recovery_for_sink_closure_mL=threshold,
            minimum_recovery_ratio_for_sink_closure=ratio,
            additional_recovery_above_requirement_floor_mL=additional,
            requirement_floor_closes_shared_sinks=additional <= _TOL,
        ))
    return tuple(result)


def evaluate_sink_recovery_threshold_trajectory(
    routing: CycleResolvedRoutingClosure,
) -> SinkRecoveryThresholdTrajectory:
    """Derive the shared-sink recovery threshold at every completed cycle."""
    if type(routing) is not CycleResolvedRoutingClosure:
        raise WasteFluidAccountingError("sink threshold trajectory requires exact cycle routing evidence")
    routing.__post_init__()
    result = SinkRecoveryThresholdTrajectory(routing, _derive(routing))
    result.__post_init__()
    return result
