import pytest
from masck_one.thermal_control import ThermalCommandInterlock, ThermalInhibitReason, ThermalMode
from masck_one.treatment_recovery_readiness import screen_treatment_recovery_readiness
from masck_one.treatment_thermal_handoff import command_thermal_after_treatment
from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_overflow_guard import screen_cartridge_overflow_guard
from masck_one.waste_fluid_cycle_routing import screen_cycle_resolved_routing_closure


def _budget(recovery_floor=None):
    budget = build_authority_waste_fluid_budget()
    if recovery_floor is not None:
        budget = type(budget)(budget.service_cycles, budget.nominal_introduced_mL_per_cycle, budget.maximum_initial_prime_mL_per_cycle, recovery_floor, budget.residual_free_liquid_max_mL, budget.external_leakage_max_mL_per_cycle, budget.cartridge_retained_capacity_requirement_mL)
    return budget


def _readiness(schedule, *, recovery=1.0, residual=None, leakage=None, recovery_floor=None, reserve=0.0):
    guard = screen_cartridge_overflow_guard(_budget(recovery_floor), prime_events_by_cycle=schedule, prime_recovery_ratio_contract=recovery, prime_residual_ratio_contract=residual, prime_external_leakage_ratio_contract=leakage, capacity_reserve_mL=reserve)
    return screen_treatment_recovery_readiness(guard)


def test_cool_is_enabled_only_from_permitted_recovery_evidence():
    command = command_thermal_after_treatment(ThermalCommandInterlock(), _readiness([0, 0, 0], recovery=1.0, recovery_floor=.95), warm_requested=False, cool_requested=True)
    assert command.mode is ThermalMode.COOL
    assert command.cool_enable
    assert not command.inhibited


@pytest.mark.parametrize("readiness", [
    pytest.param(lambda: _readiness([1], recovery=.90, residual=.08, leakage=.02), id="routing-incomplete"),
    pytest.param(lambda: _readiness([0, 0, 0, 0, 0, 30], recovery=1.0, recovery_floor=.95), id="minimum-capacity-failure"),
    pytest.param(lambda: _readiness([0, 0, 0, 0, 0, 20], recovery=.90, residual=.10, recovery_floor=.95), id="conservative-capacity-failure"),
])
def test_any_recovery_blocker_inhibits_cool(readiness):
    command = command_thermal_after_treatment(ThermalCommandInterlock(), readiness(), warm_requested=False, cool_requested=True)
    assert command.mode is ThermalMode.OFF
    assert not command.cool_enable
    assert command.inhibited
    assert command.reason is ThermalInhibitReason.RECOVERY_INCOMPLETE


def test_capacity_reserve_can_block_handoff_when_unreserved_capacity_would_fit():
    unreserved = _readiness([1, 1, 1, 1, 1, 1], recovery=1.0, recovery_floor=.95)
    reserved = _readiness([1, 1, 1, 1, 1, 1], recovery=1.0, recovery_floor=.95, reserve=5.5)
    assert unreserved.post_recovery_handoff_permitted
    assert not reserved.post_recovery_handoff_permitted
    assert reserved.source_capacity_guard.usable_capacity_mL == pytest.approx(29.5)
    assert reserved.blocking_cycle == 6
    assert reserved.blocking_reason == "fail-conservative cartridge inflow exceeds usable capacity"
    command = command_thermal_after_treatment(ThermalCommandInterlock(), reserved, warm_requested=False, cool_requested=True)
    assert command.mode is ThermalMode.OFF
    assert command.inhibited


def test_warm_semantics_are_not_silently_changed_by_recovery_adapter():
    command = command_thermal_after_treatment(ThermalCommandInterlock(), _readiness([1], recovery=.90, residual=.08, leakage=.02), warm_requested=True, cool_requested=False)
    assert command.mode is ThermalMode.WARM
    assert command.warm_enable


def test_mutually_exclusive_thermal_requests_remain_fail_closed():
    command = command_thermal_after_treatment(ThermalCommandInterlock(), _readiness([0], recovery=1.0, recovery_floor=.95), warm_requested=True, cool_requested=True)
    assert command.mode is ThermalMode.OFF
    assert command.inhibited
    assert command.reason is ThermalInhibitReason.CONFLICTING_REQUESTS


@pytest.mark.parametrize("evidence", [True, object(), None])
def test_raw_or_untyped_recovery_claims_cannot_cross_treatment_handoff(evidence):
    with pytest.raises(WasteFluidAccountingError, match="requires exact TreatmentRecoveryReadiness"):
        command_thermal_after_treatment(ThermalCommandInterlock(), evidence, warm_requested=False, cool_requested=True)


def test_closure_only_readiness_cannot_cross_thermal_boundary():
    closure = screen_cycle_resolved_routing_closure(_budget(.95), prime_events_by_cycle=[0], prime_recovery_ratio_contract=1.0)
    readiness = screen_treatment_recovery_readiness(closure)
    assert readiness.post_recovery_handoff_permitted
    with pytest.raises(WasteFluidAccountingError, match="requires reserve-aware CartridgeOverflowGuard evidence"):
        command_thermal_after_treatment(ThermalCommandInterlock(), readiness, warm_requested=False, cool_requested=True)


def test_noncanonical_interlock_is_rejected():
    class LookalikeInterlock:
        def command(self, **kwargs):
            raise AssertionError("must not be called")
    with pytest.raises(WasteFluidAccountingError, match="requires exact ThermalCommandInterlock"):
        command_thermal_after_treatment(LookalikeInterlock(), _readiness([0], recovery=1.0, recovery_floor=.95), warm_requested=False, cool_requested=True)
