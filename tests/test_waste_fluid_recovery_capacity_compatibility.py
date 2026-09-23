from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import build_authority_waste_fluid_budget
from masck_one.waste_fluid_limiting_event_capacity import screen_limiting_event_cartridge_capacity
from masck_one.waste_fluid_recovery_capacity_compatibility import (
    RecoveryCapacityCompatibilityError,
    evaluate_recovery_capacity_compatibility,
)


def _screen(budget, recovery=.90, residual=.08, leakage=.02):
    return screen_limiting_event_cartridge_capacity(
        budget,
        cycles=budget.service_cycles,
        prime_recovery_ratio_contract=recovery,
        prime_residual_ratio_contract=residual,
        prime_external_leakage_ratio_contract=leakage,
    )


def test_authority_contract_exposes_capacity_recovery_incompatibility():
    budget = build_authority_waste_fluid_budget()
    result = evaluate_recovery_capacity_compatibility(budget, _screen(budget))
    assert result.authority_recovery_floor_capacity_feasible is False
    assert result.full_nominal_recovery_capacity_feasible is False
    assert result.capacity_limited_nominal_recovery_ratio < result.authority_nominal_recovery_floor_ratio
    assert result.recovery_ratio_margin_above_authority_floor < 0.0
    assert result.recovered_reprime_reserved_mL > 0.0


def test_larger_synthetic_capacity_can_accept_full_nominal_recovery():
    budget = replace(
        build_authority_waste_fluid_budget(),
        cartridge_retained_capacity_requirement_mL=40.0,
    )
    result = evaluate_recovery_capacity_compatibility(budget, _screen(budget))
    assert result.authority_recovery_floor_capacity_feasible is True
    assert result.full_nominal_recovery_capacity_feasible is True
    assert result.capacity_limited_nominal_recovery_ratio == pytest.approx(1.0)
    assert result.recovery_ratio_margin_above_authority_floor >= 0.0


def test_capacity_ceiling_reserves_recovered_reprime_before_nominal_recovery():
    budget = build_authority_waste_fluid_budget()
    screen = _screen(budget)
    result = evaluate_recovery_capacity_compatibility(budget, screen)
    assert result.capacity_available_for_nominal_recovery_mL == pytest.approx(
        max(result.capacity_available_for_nominal_recovery_mL, 0.0)
    )
    assert result.capacity_limited_nominal_recovery_ratio == pytest.approx(
        result.capacity_available_for_nominal_recovery_mL / result.nominal_introduced_service_mL
    )


def test_rejects_capacity_screen_from_different_budget():
    budget = build_authority_waste_fluid_budget()
    altered = replace(budget, cartridge_retained_capacity_requirement_mL=40.0)
    with pytest.raises(RecoveryCapacityCompatibilityError, match="retained capacity disagrees"):
        evaluate_recovery_capacity_compatibility(altered, _screen(budget))


def test_rejects_wrong_evidence_type():
    with pytest.raises(TypeError, match="LimitingEventCapacityScreen"):
        evaluate_recovery_capacity_compatibility(build_authority_waste_fluid_budget(), object())
