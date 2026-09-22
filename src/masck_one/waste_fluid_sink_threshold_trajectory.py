"""Cycle-resolved recovery threshold imposed by shared residual/leakage sinks.

This reducer exposes when nominal recovery must exceed the requirement floor because
prime liquid consumes the same finite residual and external-leakage allowances.
It reconstructs nominal introduced volume from each cycle's independently retained
routing and sink evidence. It is requirement arithmetic, not physical validation.
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
    def peak_additional_recovery_above_floor_mL(self) -> float:
        return max(state.additional_recovery_above_requirement_floor_mL for state in self.cycles)


def _derive(routing: CycleResolvedRoutingClosure) -> tuple[CycleSinkRecoveryThreshold, ...]:
    cumulative_introduced = 0.0
    cumulative_floor = 0.0
    cumulative_prime_residual = 0.0
    cumulative_prime_leakage = 0.0
    cumulative_classified = 0.0
    cumulative_nominal_unrecovered = 0.0
    result: list[CycleSinkRecoveryThreshold] = []

    for state in routing.cycles:
        # Exactly one of gap/headroom can be positive. Their signed difference
        # reconstructs nominal nonrecovery from the retained local sink evidence.
        nominal_unrecovered = (
            state.classified_sink_capacity_after_prime_mL
            + state.nominal_unclassified_nonrecovery_after_prime_mL
            - state.classified_sink_headroom_after_nominal_mL
        )
        local_values = (
            state.minimum_nominal_routed_to_cartridge_mL,
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

        cumulative_introduced += local_introduced
        cumulative_floor += state.minimum_nominal_routed_to_cartridge_mL
        cumulative_nominal_unrecovered += nominal_unrecovered
        cumulative_prime_residual += state.prime_residual_mL
        cumulative_prime_leakage += state.prime_external_leakage_mL
        cumulative_classified += state.classified_sink_capacity_after_prime_mL

        gap = max(0.0, cumulative_nominal_unrecovered - cumulative_classified)
        threshold = cumulative_floor + gap
        ratio = threshold / cumulative_introduced
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
