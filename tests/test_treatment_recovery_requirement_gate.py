from dataclasses import replace

import pytest

from masck_one.treatment_recovery_readiness import screen_treatment_recovery_readiness
from masck_one.treatment_recovery_requirement_gate import qualify_treatment_recovery_requirement
from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_cycle_routing import screen_cycle_resolved_routing_closure
from masck_one.waste_fluid_recovery_requirement import derive_service_recovery_requirement


def _evidence(*, recovery_floor=None, prime_events=0, prime_recovery=1.0, prime_residual=None, prime_leakage=None):
    budget = build_authority_waste_fluid_budget()
    if recovery_floor is not None:
        budget = replace(budget, recovery_ratio_min=recovery_floor)
    schedule = tuple([1] * prime_events + [0] * (budget.service_cycles - prime_events))
    closure = screen_cycle_resolved_routing_closure(
        budget,
        prime_events_by_cycle=schedule,
        prime_recovery_ratio_contract=prime_recovery,
        prime_residual_ratio_contract=prime_residual,
        prime_external_leakage_ratio_contract=prime_leakage,
    )
    readiness = screen_treatment_recovery_readiness(closure)
    requirement = derive_service_recovery_requirement(
        budget,
        cycles=budget.service_cycles,
        prime_events=prime_events,
        prime_recovery_ratio_contract=prime_recovery,
        prime_residual_ratio_contract=prime_residual,
        prime_external_leakage_ratio_contract=prime_leakage,
    )
    return readiness, requirement


def test_authority_recovery_floor_blocks_handoff_when_shared_sink_budget_does_not_close():
    readiness, requirement = _evidence()
    assert readiness.post_recovery_handoff_permitted
    assert not requirement.recovery_requirement_closes
    qualified = qualify_treatment_recovery_requirement(readiness, requirement)
    assert not qualified.recovery_requirement_satisfied
    assert not qualified.post_recovery_handoff_permitted
    assert qualified.blocking_cycle is None
    assert qualified.blocking_reason == "authority recovery floor does not close residual and leakage sink budget"
    assert requirement.additional_nominal_recovery_required_mL == pytest.approx(0.06)


def test_recovery_floor_at_derived_threshold_permits_handoff():
    readiness0, requirement0 = _evidence()
    readiness, requirement = _evidence(recovery_floor=requirement0.required_nominal_recovery_ratio)
    qualified = qualify_treatment_recovery_requirement(readiness, requirement)
    assert qualified.recovery_requirement_satisfied
    assert qualified.post_recovery_handoff_permitted
    assert qualified.blocking_reason is None


def test_prime_sink_use_can_raise_recovery_requirement_and_block_handoff():
    readiness, requirement = _evidence(
        prime_events=6,
        prime_recovery=.90,
        prime_residual=.08,
        prime_leakage=.02,
    )
    qualified = qualify_treatment_recovery_requirement(readiness, requirement)
    assert not qualified.post_recovery_handoff_permitted
    assert requirement.required_nominal_recovery_ratio == pytest.approx(0.9108695652173913)
    assert requirement.additional_nominal_recovery_required_mL == pytest.approx(0.30)


def test_gate_rejects_requirement_from_different_service_contract():
    readiness, _ = _evidence()
    _, other_requirement = _evidence(prime_events=1)
    with pytest.raises(WasteFluidAccountingError, match="same service routing contract"):
        qualify_treatment_recovery_requirement(readiness, other_requirement)


def test_gate_preserves_earlier_routing_or_capacity_blocker_precedence():
    budget = replace(build_authority_waste_fluid_budget(), recovery_ratio_min=.95)
    closure = screen_cycle_resolved_routing_closure(
        budget,
        prime_events_by_cycle=(0, 0, 0, 0, 0, 30),
        prime_recovery_ratio_contract=1.0,
    )
    readiness = screen_treatment_recovery_readiness(closure)
    requirement = derive_service_recovery_requirement(
        budget,
        cycles=6,
        prime_events=30,
        prime_recovery_ratio_contract=1.0,
    )
    qualified = qualify_treatment_recovery_requirement(readiness, requirement)
    assert not qualified.post_recovery_handoff_permitted
    assert qualified.blocking_cycle == readiness.blocking_cycle
    assert qualified.blocking_reason == readiness.blocking_reason


def test_qualified_evidence_rejects_forged_permission():
    readiness, requirement = _evidence()
    qualified = qualify_treatment_recovery_requirement(readiness, requirement)
    with pytest.raises(WasteFluidAccountingError, match="must exactly match bound source evidence"):
        replace(qualified, recovery_requirement_satisfied=True, post_recovery_handoff_permitted=True, blocking_reason=None)
