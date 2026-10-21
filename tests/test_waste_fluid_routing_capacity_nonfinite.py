from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import (
    WasteFluidAccountingError,
    build_authority_waste_fluid_budget,
)
from masck_one.waste_fluid_closure import screen_service_routing_closure
from masck_one.waste_fluid_profile import screen_service_profile
from masck_one.waste_fluid_routing_capacity import derive_routing_qualified_capacity_floor


def _evidence():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=[1] * budget.service_cycles,
        target_cycles=budget.service_cycles,
    )
    routing = screen_service_routing_closure(
        budget,
        cycles=budget.service_cycles,
        prime_events=budget.service_cycles,
        prime_recovery_ratio_contract=1.0,
    )
    return profile, routing


def test_nan_nominal_routing_floor_fails_closed():
    profile, routing = _evidence()
    corrupted = replace(routing, minimum_nominal_liquid_routed_to_cartridge_mL=float("nan"))
    with pytest.raises(WasteFluidAccountingError, match="routing nominal recovery floor must be finite"):
        derive_routing_qualified_capacity_floor(profile, corrupted)


def test_infinite_prime_routing_floor_fails_closed():
    profile, routing = _evidence()
    corrupted = replace(routing, minimum_prime_liquid_routed_to_cartridge_mL=float("inf"))
    with pytest.raises(WasteFluidAccountingError, match="routing prime recovery floor must be finite"):
        derive_routing_qualified_capacity_floor(profile, corrupted)


def test_authority_evidence_still_produces_finite_capacity_decision():
    profile, routing = _evidence()
    floor = derive_routing_qualified_capacity_floor(profile, routing)
    assert floor.combined_recovery_floor_mL == pytest.approx(
        routing.minimum_nominal_liquid_routed_to_cartridge_mL
        + routing.minimum_prime_liquid_routed_to_cartridge_mL
    )
    assert floor.headroom_mL == pytest.approx(
        profile.usable_capacity_mL - floor.combined_recovery_floor_mL
    )
    assert floor.fit
    assert floor.integration_ready
