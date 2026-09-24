from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_profile import screen_service_profile
from masck_one.waste_fluid_profile_closure import validate_service_profile_closure


def _profile():
    budget = build_authority_waste_fluid_budget()
    return screen_service_profile(
        budget,
        prime_events_by_cycle=(1, 0, 1),
        target_cycles=budget.service_cycles,
        future_prime_events_per_remaining_cycle=1,
    )


def _mutate_cycle(profile, index, **changes):
    cycles = list(profile.cycles)
    cycles[index] = replace(cycles[index], **changes)
    return replace(profile, cycles=tuple(cycles))


def test_authority_profile_closes():
    profile = _profile()
    assert validate_service_profile_closure(profile) is profile
    assert validate_service_profile_closure(profile, build_authority_waste_fluid_budget()) is profile


@pytest.mark.parametrize(
    "field",
    ("requirement_margin_mL", "projected_mandatory_recovery_margin_mL", "projected_service_end_margin_mL"),
)
def test_rejects_stale_margin(field):
    profile = _profile()
    state = profile.cycles[0]
    bad = _mutate_cycle(profile, 0, **{field: getattr(state, field) + 0.01})
    with pytest.raises(WasteFluidAccountingError):
        validate_service_profile_closure(bad)


@pytest.mark.parametrize(
    "field",
    ("capacity_satisfied", "minimum_recovery_capacity_satisfied", "mandatory_recovery_service_target_feasible", "service_target_feasible"),
)
def test_rejects_stale_decision_boolean(field):
    profile = _profile()
    state = profile.cycles[0]
    bad = _mutate_cycle(profile, 0, **{field: not getattr(state, field)})
    marker_by_field = {
        "capacity_satisfied": "first_overflow_cycle",
        "mandatory_recovery_service_target_feasible": "first_mandatory_recovery_target_infeasible_cycle",
        "service_target_feasible": "first_target_infeasible_cycle",
        "minimum_recovery_capacity_satisfied": "first_mandatory_recovery_overflow_cycle",
    }
    marker = marker_by_field[field]
    cycles = bad.cycles
    expected_marker = next((s.cycle for s in cycles if not getattr(s, field)), None)
    bad = replace(bad, **{marker: expected_marker})
    with pytest.raises(WasteFluidAccountingError):
        validate_service_profile_closure(bad)


def test_rejects_projected_recovery_below_accumulated_recovery_even_with_coherent_margin():
    profile = _profile()
    state = profile.cycles[-1]
    projected = state.minimum_recovered_nominal_mL - 0.01
    bad = _mutate_cycle(
        profile,
        len(profile.cycles) - 1,
        minimum_projected_service_end_recovered_mL=projected,
        projected_mandatory_recovery_margin_mL=profile.usable_capacity_mL - projected,
    )
    with pytest.raises(WasteFluidAccountingError):
        validate_service_profile_closure(bad)


def test_rejects_projected_inflow_below_accumulated_inflow_even_with_coherent_margin():
    profile = _profile()
    state = profile.cycles[-1]
    projected = state.maximum_cartridge_inflow_mL - 0.01
    bad = _mutate_cycle(
        profile,
        len(profile.cycles) - 1,
        minimum_projected_service_end_inflow_mL=projected,
        projected_service_end_margin_mL=profile.usable_capacity_mL - projected,
    )
    with pytest.raises(WasteFluidAccountingError):
        validate_service_profile_closure(bad)


@pytest.mark.parametrize(
    "field",
    (
        "cumulative_nominal_mL",
        "cumulative_prime_mL",
        "minimum_recovered_nominal_mL",
        "maximum_cartridge_inflow_mL",
        "reserved_future_prime_mL",
        "minimum_projected_service_end_recovered_mL",
        "minimum_projected_service_end_inflow_mL",
    ),
)
def test_authority_closure_rejects_stale_source_derived_volume(field):
    budget = build_authority_waste_fluid_budget()
    profile = _profile()
    state = profile.cycles[0]
    bad = _mutate_cycle(profile, 0, **{field: getattr(state, field) + 0.01})
    with pytest.raises(WasteFluidAccountingError):
        validate_service_profile_closure(bad, budget)


def test_authority_closure_rejects_stale_additional_prime_headroom():
    budget = build_authority_waste_fluid_budget()
    profile = _profile()
    state = profile.cycles[0]
    bad = _mutate_cycle(
        profile,
        0,
        maximum_additional_prime_events_for_target=state.maximum_additional_prime_events_for_target + 1,
    )
    with pytest.raises(WasteFluidAccountingError):
        validate_service_profile_closure(bad, budget)


def test_authority_closure_rejects_stale_unreserved_prime_headroom():
    budget = build_authority_waste_fluid_budget()
    profile = _profile()
    state = profile.cycles[0]
    bad = _mutate_cycle(
        profile,
        0,
        maximum_unreserved_prime_events_after_contingency=state.maximum_unreserved_prime_events_after_contingency + 1,
    )
    with pytest.raises(WasteFluidAccountingError):
        validate_service_profile_closure(bad, budget)
