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


@pytest.mark.parametrize(
    ("field", "delta", "message"),
    [
        ("service_residual_ceiling_mL", .1, "service residual ceiling disagrees"),
        ("service_external_leakage_ceiling_mL", .1, "service leakage ceiling disagrees"),
        ("prime_residual_ceiling_margin_mL", .1, "prime residual margin is stale"),
        ("prime_external_leakage_ceiling_margin_mL", .1, "prime leakage margin is stale"),
        ("shared_sink_unclassified_nonrecovery_mL", .1, "shared sink gap is stale"),
        ("prime_liquid_without_routing_contract_mL", .1, "unresolved prime load is stale"),
        ("total_liquid_without_routing_contract_mL", .1, "unresolved total load is stale"),
    ],
)
def test_rejects_stale_shared_sink_and_unresolved_volume_evidence(field, delta, message):
    budget, screen = _screen()
    envelope = screen.service_envelope
    point = envelope.first_infeasible if envelope.first_infeasible is not None else envelope.maximum_feasible
    value = getattr(point.source_closure, field)
    stale = _replace_limiting_closure(screen, **{field: value + delta})
    with pytest.raises(RecoveryCapacityCompatibilityError, match=message):
        evaluate_recovery_capacity_compatibility(budget, stale)


def test_rejects_stale_routing_completeness_flag():
    budget, screen = _screen()
    envelope = screen.service_envelope
    point = envelope.first_infeasible if envelope.first_infeasible is not None else envelope.maximum_feasible
    stale = _replace_limiting_closure(
        screen,
        routing_contract_complete=not point.source_closure.routing_contract_complete,
    )
    with pytest.raises(RecoveryCapacityCompatibilityError, match="routing completeness flag is stale"):
        evaluate_recovery_capacity_compatibility(budget, stale)


def test_current_authority_bound_screen_still_evaluates():
    budget, screen = _screen()
    result = evaluate_recovery_capacity_compatibility(budget, screen)
    assert result.recovered_reprime_reserved_mL == pytest.approx(screen.prime_liquid_routed_to_cartridge_mL)
