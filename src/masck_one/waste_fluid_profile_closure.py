"""Independent algebraic closure checks for cycle-resolved fluid profiles.

These checks verify internal conservation and decision arithmetic without claiming
physical validation of recovery, leakage, retained capacity, pressure, or flow.
"""
from __future__ import annotations

import math

from .waste_fluid_accounting import WasteFluidAccountingError, WasteFluidBudget
from .waste_fluid_profile import ServiceFluidProfile

_TOL = 1e-12


def _close(actual: float, expected: float, label: str) -> None:
    if not math.isfinite(float(actual)) or not math.isfinite(float(expected)):
        raise WasteFluidAccountingError(f"{label} must remain finite")
    if not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=_TOL):
        raise WasteFluidAccountingError(f"{label} is inconsistent with cycle evidence")


def validate_service_profile_closure(
    profile: ServiceFluidProfile,
    budget: WasteFluidBudget | None = None,
) -> ServiceFluidProfile:
    """Fail closed when stored cycle decisions disagree with source evidence.

    With ``budget`` supplied, this also reconstructs cycle fluid accounting and
    future-prime headroom from the authority budget. This is a synthetic
    conservation/capacity check, not physical validation.
    """
    if type(profile) is not ServiceFluidProfile:
        raise WasteFluidAccountingError("profile closure requires exact ServiceFluidProfile evidence")
    profile.__post_init__()
    if budget is not None:
        if type(budget) is not WasteFluidBudget:
            raise WasteFluidAccountingError("profile authority closure requires exact WasteFluidBudget evidence")
        budget.validate()
        if profile.target_cycles > budget.service_cycles:
            raise WasteFluidAccountingError("profile target exceeds budget service authority")
        _close(
            profile.usable_capacity_mL,
            budget.cartridge_retained_capacity_requirement_mL - profile.capacity_reserve_mL,
            "profile usable capacity",
        )

    usable = float(profile.usable_capacity_mL)
    for state in profile.cycles:
        current_margin = usable - float(state.maximum_cartridge_inflow_mL)
        minimum_recovery_margin = usable - float(state.minimum_recovered_nominal_mL)
        mandatory_margin = usable - float(state.minimum_projected_service_end_recovered_mL)
        projected_margin = usable - float(state.minimum_projected_service_end_inflow_mL)

        _close(state.requirement_margin_mL, current_margin, "cycle requirement margin")
        _close(state.projected_mandatory_recovery_margin_mL, mandatory_margin, "projected mandatory-recovery margin")
        _close(state.projected_service_end_margin_mL, projected_margin, "projected service-end margin")

        expected_capacity = current_margin >= -_TOL
        expected_minimum_recovery = minimum_recovery_margin >= -_TOL
        expected_mandatory_target = mandatory_margin >= -_TOL
        expected_service_target = projected_margin >= -_TOL
        if state.capacity_satisfied is not expected_capacity:
            raise WasteFluidAccountingError("cycle capacity decision is inconsistent with capacity margin")
        if state.minimum_recovery_capacity_satisfied is not expected_minimum_recovery:
            raise WasteFluidAccountingError("minimum-recovery capacity decision is inconsistent with recovered volume")
        if state.mandatory_recovery_service_target_feasible is not expected_mandatory_target:
            raise WasteFluidAccountingError("mandatory-recovery target decision is inconsistent with projected margin")
        if state.service_target_feasible is not expected_service_target:
            raise WasteFluidAccountingError("service target decision is inconsistent with projected margin")

        if state.minimum_projected_service_end_recovered_mL + _TOL < state.minimum_recovered_nominal_mL:
            raise WasteFluidAccountingError("projected mandatory recovery cannot be below already recovered volume")
        if state.minimum_projected_service_end_inflow_mL + _TOL < state.maximum_cartridge_inflow_mL:
            raise WasteFluidAccountingError("projected cartridge inflow cannot be below already accumulated inflow")
        if state.minimum_projected_service_end_inflow_mL + _TOL < state.minimum_projected_service_end_recovered_mL:
            raise WasteFluidAccountingError("projected cartridge inflow cannot be below mandatory recovered volume")

        if budget is not None:
            aggregate = budget.service_capacity_screen(
                cycles=state.cycle,
                prime_events=state.cumulative_prime_events,
            )
            _close(state.cumulative_nominal_mL, aggregate.nominal_liquid_mL, "cycle cumulative nominal volume")
            _close(state.cumulative_prime_mL, aggregate.prime_liquid_mL, "cycle cumulative prime volume")
            _close(state.minimum_recovered_nominal_mL, aggregate.minimum_recovered_nominal_mL, "cycle minimum recovered volume")
            _close(state.maximum_cartridge_inflow_mL, aggregate.maximum_cartridge_inflow_mL, "cycle maximum cartridge inflow")
            _close(state.occupancy_uncertainty_mL, aggregate.occupancy_uncertainty_mL, "cycle occupancy uncertainty")

            remaining = profile.target_cycles - state.cycle
            expected_recovery = aggregate.minimum_recovered_nominal_mL + remaining * budget.minimum_recovered_mL_per_cycle
            _close(state.minimum_projected_service_end_recovered_mL, expected_recovery, "projected mandatory recovery")
            expected_reserved_events = remaining * profile.future_prime_events_per_remaining_cycle
            if state.reserved_future_prime_events != expected_reserved_events:
                raise WasteFluidAccountingError("future prime-event reserve is inconsistent with authority projection")
            expected_reserved_volume = expected_reserved_events * budget.maximum_initial_prime_mL_per_cycle
            _close(state.reserved_future_prime_mL, expected_reserved_volume, "future prime reserve volume")
            nominal_target_inflow = aggregate.maximum_cartridge_inflow_mL + remaining * budget.nominal_introduced_mL_per_cycle
            expected_projected_inflow = nominal_target_inflow + expected_reserved_volume
            _close(state.minimum_projected_service_end_inflow_mL, expected_projected_inflow, "projected service-end inflow")

            prime_volume = budget.maximum_initial_prime_mL_per_cycle
            if prime_volume == 0.0:
                expected_additional = None
                expected_unreserved = None
            else:
                headroom = usable - nominal_target_inflow
                quotient = (headroom + _TOL) / prime_volume
                if not math.isfinite(quotient):
                    raise WasteFluidAccountingError("additional-prime headroom quotient must remain finite")
                expected_additional = max(0, math.floor(quotient))
                if expected_service_target:
                    quotient = (projected_margin + _TOL) / prime_volume
                    if not math.isfinite(quotient):
                        raise WasteFluidAccountingError("unreserved-prime headroom quotient must remain finite")
                    expected_unreserved = max(0, math.floor(quotient))
                else:
                    expected_unreserved = 0
            if state.maximum_additional_prime_events_for_target != expected_additional:
                raise WasteFluidAccountingError("additional-prime headroom is inconsistent with authority budget")
            if state.maximum_unreserved_prime_events_after_contingency != expected_unreserved:
                raise WasteFluidAccountingError("unreserved-prime headroom is inconsistent with authority budget")

    return profile
