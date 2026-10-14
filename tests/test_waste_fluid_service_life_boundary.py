import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_closure import screen_service_routing_closure
from masck_one.waste_fluid_profile import screen_service_profile


def test_aggregate_routing_cannot_extend_past_configured_service_life():
    budget = build_authority_waste_fluid_budget()
    assert budget.service_cycles == 6
    with pytest.raises(WasteFluidAccountingError, match="exceeds configured service life"):
        screen_service_routing_closure(
            budget,
            cycles=7,
            prime_events=0,
            prime_recovery_ratio_contract=1.0,
        )


def test_aggregate_routing_accepts_service_life_prefix_without_granting_future_sink_capacity():
    closure = screen_service_routing_closure(
        build_authority_waste_fluid_budget(),
        cycles=3,
        prime_events=0,
        prime_recovery_ratio_contract=1.0,
    )
    assert closure.cycles == 3
    assert closure.service_residual_ceiling_mL == pytest.approx(1.2)
    assert closure.service_external_leakage_ceiling_mL == pytest.approx(0.15)
    assert closure.nominal_unclassified_nonrecovery_mL == pytest.approx(0.03)


def test_capacity_screen_cannot_reuse_cartridge_past_configured_service_life():
    budget = build_authority_waste_fluid_budget()
    assert budget.service_cycles == 6
    with pytest.raises(WasteFluidAccountingError, match="cycles exceeds configured service life"):
        budget.service_capacity_screen(cycles=7, prime_events=0)


def test_capacity_screen_prefix_accounts_only_requested_cycles():
    budget = build_authority_waste_fluid_budget()
    screen = budget.service_capacity_screen(cycles=3, prime_events=2)
    assert screen.cycles == 3
    assert screen.prime_events == 2
    assert screen.nominal_liquid_mL == pytest.approx(13.8)
    assert screen.prime_liquid_mL == pytest.approx(0.8)
    assert screen.maximum_cartridge_inflow_mL == pytest.approx(14.6)
    assert screen.requirement_margin_mL == pytest.approx(20.4)


def test_maximum_prime_event_screen_inherits_service_life_boundary():
    budget = build_authority_waste_fluid_budget()
    with pytest.raises(WasteFluidAccountingError, match="cycles exceeds configured service life"):
        budget.maximum_prime_events_that_fit(cycles=7)


def test_packaging_cycle_capacity_remains_distinct_from_service_authorization():
    budget = build_authority_waste_fluid_budget()
    packaging_cycles = budget.maximum_service_cycles_that_fit(prime_events=0)
    assert packaging_cycles == 7
    assert packaging_cycles > budget.service_cycles
    with pytest.raises(WasteFluidAccountingError, match="cycles exceeds configured service life"):
        budget.service_capacity_screen(cycles=packaging_cycles, prime_events=0)


def test_profile_target_cannot_extend_past_configured_cartridge_service_life():
    budget = build_authority_waste_fluid_budget()
    assert budget.service_cycles == 6
    with pytest.raises(WasteFluidAccountingError, match="target_cycles exceeds configured service life"):
        screen_service_profile(
            budget,
            prime_events_by_cycle=[0],
            target_cycles=7,
        )


def test_profile_prefix_reserves_only_requested_target_cycles():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=[0],
        target_cycles=3,
        future_prime_events_per_remaining_cycle=1,
    )
    assert profile.target_cycles == 3
    assert profile.final.reserved_future_prime_events == 2
    assert profile.final.reserved_future_prime_mL == pytest.approx(0.8)
    assert profile.final.minimum_projected_service_end_inflow_mL == pytest.approx(14.6)
    assert profile.final.projected_service_end_margin_mL == pytest.approx(20.4)
