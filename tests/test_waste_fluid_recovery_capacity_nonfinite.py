from dataclasses import replace
import math

import pytest

from masck_one.waste_fluid_accounting import build_authority_waste_fluid_budget
from masck_one.waste_fluid_limiting_event_capacity import screen_limiting_event_cartridge_capacity
from masck_one.waste_fluid_recovery_capacity_compatibility import (
    RecoveryCapacityCompatibilityError,
    evaluate_recovery_capacity_compatibility,
)


def _screen(budget):
    return screen_limiting_event_cartridge_capacity(
        budget,
        cycles=budget.service_cycles,
        prime_recovery_ratio_contract=.90,
        prime_residual_ratio_contract=.08,
        prime_external_leakage_ratio_contract=.02,
    )


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_nonfinite_top_level_capacity_evidence_fails_closed(bad):
    budget = build_authority_waste_fluid_budget()
    screen = _screen(budget)
    for field in (
        "nominal_liquid_at_maximum_recovery_mL",
        "retained_cartridge_capacity_mL",
        "prime_liquid_routed_to_cartridge_mL",
        "authority_floor_nominal_recovery_mL",
        "authority_floor_cartridge_demand_mL",
        "cartridge_demand_at_maximum_nominal_recovery_mL",
        "authority_floor_cartridge_overflow_mL",
        "cartridge_overflow_at_maximum_nominal_recovery_mL",
    ):
        with pytest.raises(RecoveryCapacityCompatibilityError, match="finite numeric evidence"):
            evaluate_recovery_capacity_compatibility(budget, replace(screen, **{field: bad}))


def test_nonfinite_nested_capacity_evidence_fails_before_tolerance_comparison():
    budget = build_authority_waste_fluid_budget()
    screen = _screen(budget)
    stale_point = replace(
        screen.service_envelope.maximum_feasible,
        retained_cartridge_capacity_mL=math.nan,
    )
    stale_envelope = replace(screen.service_envelope, maximum_feasible=stale_point)
    with pytest.raises(RecoveryCapacityCompatibilityError, match="finite numeric evidence"):
        evaluate_recovery_capacity_compatibility(
            budget,
            replace(screen, service_envelope=stale_envelope),
        )


def test_nonfinite_budget_authority_fails_closed():
    budget = build_authority_waste_fluid_budget()
    screen = _screen(budget)
    stale_budget = replace(budget, cartridge_retained_capacity_requirement_mL=math.nan)
    with pytest.raises(RecoveryCapacityCompatibilityError, match="finite numeric evidence"):
        evaluate_recovery_capacity_compatibility(stale_budget, screen)
