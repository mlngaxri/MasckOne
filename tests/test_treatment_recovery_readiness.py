import pytest

from masck_one.treatment_recovery_readiness import (
    TreatmentRecoveryReadiness,
    screen_treatment_recovery_readiness,
)
from masck_one.waste_fluid_accounting import (
    WasteFluidAccountingError,
    build_authority_waste_fluid_budget,
)
from masck_one.waste_fluid_cycle_routing import screen_cycle_resolved_routing_closure


def _closure(schedule, *, recovery=1.0, residual=None, leakage=None, recovery_floor=None):
    budget = build_authority_waste_fluid_budget()
    if recovery_floor is not None:
        budget = type(budget)(
            budget.service_cycles,
            budget.nominal_introduced_mL_per_cycle,
            budget.maximum_initial_prime_mL_per_cycle,
            recovery_floor,
            budget.residual_free_liquid_max_mL,
            budget.external_leakage_max_mL_per_cycle,
            budget.cartridge_retained_capacity_requirement_mL,
        )
    return screen_cycle_resolved_routing_closure(
        budget,
        prime_events_by_cycle=schedule,
        prime_recovery_ratio_contract=recovery,
        prime_residual_ratio_contract=residual,
        prime_external_leakage_ratio_contract=leakage,
    )


def test_complete_routing_and_capacity_permit_post_recovery_handoff():
    closure = _closure([0, 0, 0], recovery=1.0, recovery_floor=.95)
    readiness = screen_treatment_recovery_readiness(closure)
    assert readiness.source_closure is closure
    assert readiness.routing_complete
    assert readiness.minimum_routing_capacity_satisfied
    assert readiness.conservative_capacity_satisfied
    assert readiness.post_recovery_handoff_permitted
    assert readiness.blocking_cycle is None
    assert readiness.blocking_reason is None


def test_incomplete_routing_blocks_before_capacity_even_when_capacity_fits():
    readiness = screen_treatment_recovery_readiness(
        _closure([1], recovery=.90, residual=.08, leakage=.02)
    )
    assert not readiness.routing_complete
    assert readiness.minimum_routing_capacity_satisfied
    assert readiness.conservative_capacity_satisfied
    assert not readiness.post_recovery_handoff_permitted
    assert readiness.blocking_cycle == 1
    assert readiness.blocking_reason == "routing contract incomplete"


def test_unavoidable_capacity_failure_blocks_handoff_at_exact_cycle():
    readiness = screen_treatment_recovery_readiness(
        _closure([0, 0, 0, 0, 0, 30], recovery=1.0, recovery_floor=.95)
    )
    assert readiness.routing_complete
    assert not readiness.minimum_routing_capacity_satisfied
    assert not readiness.conservative_capacity_satisfied
    assert not readiness.post_recovery_handoff_permitted
    assert readiness.blocking_cycle == 6
    assert readiness.blocking_reason == (
        "minimum contractual cartridge routing exceeds retained capacity"
    )


def test_conservative_only_capacity_failure_still_blocks_handoff():
    readiness = screen_treatment_recovery_readiness(
        _closure([0, 0, 0, 0, 0, 20], recovery=.50, residual=.50, recovery_floor=.95)
    )
    assert readiness.routing_complete
    assert readiness.minimum_routing_capacity_satisfied
    assert not readiness.conservative_capacity_satisfied
    assert not readiness.post_recovery_handoff_permitted
    assert readiness.blocking_cycle == 6
    assert readiness.blocking_reason == (
        "fail-conservative cartridge inflow exceeds retained capacity"
    )


def test_readiness_rejects_non_builder_evidence():
    with pytest.raises(
        WasteFluidAccountingError,
        match="requires exact CycleResolvedRoutingClosure",
    ):
        screen_treatment_recovery_readiness(object())


def test_readiness_rejects_non_closure_source_evidence():
    with pytest.raises(WasteFluidAccountingError, match="exact source CycleResolvedRoutingClosure"):
        TreatmentRecoveryReadiness(
            source_closure=object(),
            routing_complete=True,
            minimum_routing_capacity_satisfied=True,
            conservative_capacity_satisfied=True,
            post_recovery_handoff_permitted=True,
            blocking_cycle=None,
            blocking_reason=None,
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("routing_complete", 1),
        ("minimum_routing_capacity_satisfied", 1),
        ("conservative_capacity_satisfied", 1),
        ("post_recovery_handoff_permitted", 1),
    ],
)
def test_readiness_rejects_type_confused_boolean_evidence(field, value):
    closure = _closure([0], recovery=1.0, recovery_floor=.95)
    kwargs = dict(
        source_closure=closure,
        routing_complete=True,
        minimum_routing_capacity_satisfied=True,
        conservative_capacity_satisfied=True,
        post_recovery_handoff_permitted=True,
        blocking_cycle=None,
        blocking_reason=None,
    )
    kwargs[field] = value
    with pytest.raises(WasteFluidAccountingError, match=f"{field} must be an exact bool"):
        TreatmentRecoveryReadiness(**kwargs)


def test_readiness_cannot_forge_permitted_handoff_over_failed_source_closure():
    closure = _closure([1], recovery=.90, residual=.08, leakage=.02)
    with pytest.raises(WasteFluidAccountingError, match="must exactly match source routing closure"):
        TreatmentRecoveryReadiness(
            source_closure=closure,
            routing_complete=True,
            minimum_routing_capacity_satisfied=True,
            conservative_capacity_satisfied=True,
            post_recovery_handoff_permitted=True,
            blocking_cycle=None,
            blocking_reason=None,
        )


def test_readiness_cannot_replace_real_blocker_with_plausible_forged_blocker():
    closure = _closure([0, 0, 0, 0, 0, 30], recovery=1.0, recovery_floor=.95)
    with pytest.raises(WasteFluidAccountingError, match="must exactly match source routing closure"):
        TreatmentRecoveryReadiness(
            source_closure=closure,
            routing_complete=True,
            minimum_routing_capacity_satisfied=False,
            conservative_capacity_satisfied=False,
            post_recovery_handoff_permitted=False,
            blocking_cycle=5,
            blocking_reason="minimum contractual cartridge routing exceeds retained capacity",
        )


def test_readiness_cannot_mislabel_source_blocking_reason():
    closure = _closure([1], recovery=.90, residual=.08, leakage=.02)
    with pytest.raises(WasteFluidAccountingError, match="must exactly match source routing closure"):
        TreatmentRecoveryReadiness(
            source_closure=closure,
            routing_complete=False,
            minimum_routing_capacity_satisfied=True,
            conservative_capacity_satisfied=True,
            post_recovery_handoff_permitted=False,
            blocking_cycle=1,
            blocking_reason="fail-conservative cartridge inflow exceeds retained capacity",
        )


def test_readiness_rejects_blank_blocking_reason():
    closure = _closure([1], recovery=.90, residual=.08, leakage=.02)
    with pytest.raises(WasteFluidAccountingError, match="blocking_reason"):
        TreatmentRecoveryReadiness(
            source_closure=closure,
            routing_complete=False,
            minimum_routing_capacity_satisfied=True,
            conservative_capacity_satisfied=True,
            post_recovery_handoff_permitted=False,
            blocking_cycle=1,
            blocking_reason="   ",
        )
