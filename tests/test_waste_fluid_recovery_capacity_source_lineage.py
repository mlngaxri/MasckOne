from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import build_authority_waste_fluid_budget
from masck_one.waste_fluid_limiting_event_capacity import screen_limiting_event_cartridge_capacity
from masck_one.waste_fluid_recovery_capacity_compatibility import (
    RecoveryCapacityCompatibilityError,
    evaluate_recovery_capacity_compatibility,
)


def _screen():
    budget = build_authority_waste_fluid_budget()
    return budget, screen_limiting_event_cartridge_capacity(
        budget,
        cycles=budget.service_cycles,
        prime_recovery_ratio_contract=.90,
        prime_residual_ratio_contract=.08,
        prime_external_leakage_ratio_contract=.02,
    )


def _replace_limiting_closure(screen, **changes):
    envelope = screen.service_envelope
    point = envelope.first_infeasible if envelope.first_infeasible is not None else envelope.maximum_feasible
    stale_point = replace(point, source_closure=replace(point.source_closure, **changes))
    if envelope.first_infeasible is not None:
        return replace(screen, service_envelope=replace(envelope, first_infeasible=stale_point))
    return replace(screen, service_envelope=replace(envelope, maximum_feasible=stale_point))


def test_rejects_limiting_source_closure_with_wrong_prime_event_count():
    budget, screen = _screen()
    stale = _replace_limiting_closure(screen, prime_events=screen.limiting_prime_events - 1)
    with pytest.raises(RecoveryCapacityCompatibilityError, match="source closure prime count disagrees"):
        evaluate_recovery_capacity_compatibility(budget, stale)


def test_rejects_top_level_reprime_load_detached_from_nested_routing_contract():
    budget, screen = _screen()
    stale_reprime = screen.prime_liquid_routed_to_cartridge_mL + 0.1
    stale = replace(
        screen,
        prime_liquid_routed_to_cartridge_mL=stale_reprime,
        authority_floor_cartridge_demand_mL=screen.authority_floor_cartridge_demand_mL + 0.1,
        cartridge_demand_at_maximum_nominal_recovery_mL=screen.cartridge_demand_at_maximum_nominal_recovery_mL + 0.1,
    )
    with pytest.raises(RecoveryCapacityCompatibilityError, match="recovered reprime load disagrees"):
        evaluate_recovery_capacity_compatibility(budget, stale)


def test_rejects_nonfinite_nested_prime_recovery_contract():
    budget, screen = _screen()
    stale = _replace_limiting_closure(screen, prime_recovery_ratio_contract=float("nan"))
    with pytest.raises(RecoveryCapacityCompatibilityError, match="prime recovery contract must be finite"):
        evaluate_recovery_capacity_compatibility(budget, stale)


@pytest.mark.parametrize("ratio", [-0.01, 1.01])
def test_rejects_out_of_range_nested_prime_recovery_contract_even_if_reprime_is_reconciled(ratio):
    budget, screen = _screen()
    stale = _replace_limiting_closure(screen, prime_recovery_ratio_contract=ratio)
    with pytest.raises(RecoveryCapacityCompatibilityError, match=r"prime recovery contract must lie within \[0, 1\]"):
        evaluate_recovery_capacity_compatibility(budget, stale)


def test_rejects_non_integer_limiting_prime_event_count():
    budget, screen = _screen()
    envelope = replace(screen.service_envelope, limiting_next_prime_events=1.5)
    stale = replace(screen, limiting_prime_events=1.5, service_envelope=envelope)
    stale = _replace_limiting_closure(stale, prime_events=1.5)
    with pytest.raises(RecoveryCapacityCompatibilityError, match="limiting prime event count must be a non-negative integer"):
        evaluate_recovery_capacity_compatibility(budget, stale)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("prime_residual_ratio_contract", float("nan"), "prime residual contract must be finite"),
        ("prime_external_leakage_ratio_contract", 1.01, r"prime external leakage contract must lie within \[0, 1\]"),
    ],
)
def test_rejects_invalid_nested_nonrecovery_contracts(field, value, message):
    budget, screen = _screen()
    stale = _replace_limiting_closure(screen, **{field: value})
    with pytest.raises(RecoveryCapacityCompatibilityError, match=message):
        evaluate_recovery_capacity_compatibility(budget, stale)


def test_rejects_nested_prime_partition_above_unity():
    budget, screen = _screen()
    stale = _replace_limiting_closure(screen, prime_residual_ratio_contract=.09)
    with pytest.raises(RecoveryCapacityCompatibilityError, match="routing contracts must not sum above one"):
        evaluate_recovery_capacity_compatibility(budget, stale)


@pytest.mark.parametrize(
    ("field", "delta", "message"),
    [
        ("total_prime_liquid_mL", .1, "total prime load disagrees"),
        ("minimum_prime_liquid_routed_to_cartridge_mL", .1, "recovered prime load disagrees"),
        ("maximum_prime_residual_mL", .1, "prime residual load disagrees"),
        ("maximum_prime_external_leakage_mL", .1, "prime leakage load disagrees"),
    ],
)
def test_rejects_stale_nested_prime_sink_volumes(field, delta, message):
    budget, screen = _screen()
    envelope = screen.service_envelope
    point = envelope.first_infeasible if envelope.first_infeasible is not None else envelope.maximum_feasible
    value = getattr(point.source_closure, field)
    stale = _replace_limiting_closure(screen, **{field: value + delta})
    with pytest.raises(RecoveryCapacityCompatibilityError, match=message):
        evaluate_recovery_capacity_compatibility(budget, stale)
