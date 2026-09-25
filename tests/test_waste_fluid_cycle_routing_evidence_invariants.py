from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import (
    WasteFluidAccountingError,
    build_authority_waste_fluid_budget,
)
from masck_one.waste_fluid_cycle_routing import (
    CycleResolvedRoutingClosure,
    screen_cycle_resolved_routing_closure,
)


def _closure():
    return screen_cycle_resolved_routing_closure(
        build_authority_waste_fluid_budget(),
        prime_events_by_cycle=[0, 1, 0],
        prime_recovery_ratio_contract=1.0,
    )


def _replace_cycle(valid, index, **changes):
    cycles = list(valid.cycles)
    cycles[index] = replace(cycles[index], **changes)
    return tuple(cycles)


def test_closure_rejects_empty_cycle_evidence():
    valid = _closure()
    with pytest.raises(WasteFluidAccountingError, match="nonempty tuple"):
        CycleResolvedRoutingClosure(cycles=(), service=valid.service)


def test_closure_rejects_noncontiguous_cycle_numbers():
    valid = _closure()
    forged = replace(valid.cycles[1], cycle=7)
    with pytest.raises(WasteFluidAccountingError, match="contiguous and one-indexed"):
        CycleResolvedRoutingClosure(cycles=(valid.cycles[0], forged, valid.cycles[2]), service=valid.service)


def test_closure_rejects_service_cycle_count_drift():
    valid = _closure()
    forged_service = replace(valid.service, cycles=2)
    with pytest.raises(WasteFluidAccountingError, match="cycle count does not match"):
        CycleResolvedRoutingClosure(cycles=valid.cycles, service=forged_service)


def test_closure_rejects_service_prime_event_drift():
    valid = _closure()
    forged_service = replace(valid.service, prime_events=99)
    with pytest.raises(WasteFluidAccountingError, match="prime-event count does not match"):
        CycleResolvedRoutingClosure(cycles=valid.cycles, service=forged_service)


def test_closure_rejects_cycle_service_liquid_parity_drift():
    valid = _closure()
    forged_service = replace(valid.service, minimum_prime_liquid_routed_to_cartridge_mL=valid.service.minimum_prime_liquid_routed_to_cartridge_mL + 0.001)
    with pytest.raises(WasteFluidAccountingError, match="parity failure for prime cartridge routing"):
        CycleResolvedRoutingClosure(cycles=valid.cycles, service=forged_service)


def test_closure_rejects_equal_and_opposite_nominal_prime_service_drift():
    valid = _closure()
    delta = 0.001
    forged_service = replace(
        valid.service,
        minimum_nominal_liquid_routed_to_cartridge_mL=valid.service.minimum_nominal_liquid_routed_to_cartridge_mL + delta,
        minimum_prime_liquid_routed_to_cartridge_mL=valid.service.minimum_prime_liquid_routed_to_cartridge_mL - delta,
    )
    with pytest.raises(WasteFluidAccountingError, match="parity failure for nominal cartridge routing"):
        CycleResolvedRoutingClosure(cycles=valid.cycles, service=forged_service)


def test_closure_rejects_equal_and_opposite_nominal_prime_cycle_drift():
    valid = _closure()
    delta = 0.001
    forged_cycle = replace(
        valid.cycles[1],
        minimum_nominal_routed_to_cartridge_mL=valid.cycles[1].minimum_nominal_routed_to_cartridge_mL + delta,
        minimum_prime_routed_to_cartridge_mL=valid.cycles[1].minimum_prime_routed_to_cartridge_mL - delta,
    )
    with pytest.raises(WasteFluidAccountingError, match="minimum routing components"):
        CycleResolvedRoutingClosure(cycles=(valid.cycles[0], forged_cycle, valid.cycles[2]), service=valid.service)


def test_closure_rejects_final_cumulative_routing_drift():
    valid = _closure()
    forged_final = replace(valid.cycles[-1], cumulative_minimum_cartridge_routing_mL=valid.cycles[-1].cumulative_minimum_cartridge_routing_mL + 0.001)
    with pytest.raises(WasteFluidAccountingError, match="cumulative minimum cartridge routing"):
        CycleResolvedRoutingClosure(cycles=valid.cycles[:-1] + (forged_final,), service=valid.service)


def test_closure_rejects_intermediate_cumulative_minimum_drift_even_when_final_is_valid():
    valid = _closure()
    cycles = _replace_cycle(
        valid,
        1,
        cumulative_minimum_cartridge_routing_mL=valid.cycles[1].cumulative_minimum_cartridge_routing_mL + 0.001,
    )
    with pytest.raises(WasteFluidAccountingError, match="cycle 2 cumulative minimum"):
        CycleResolvedRoutingClosure(cycles=cycles, service=valid.service)


def test_closure_rejects_intermediate_occupancy_uncertainty_drift():
    valid = _closure()
    cycles = _replace_cycle(
        valid,
        1,
        cartridge_occupancy_uncertainty_mL=valid.cycles[1].cartridge_occupancy_uncertainty_mL + 0.001,
    )
    with pytest.raises(WasteFluidAccountingError, match="cycle 2 cartridge occupancy uncertainty"):
        CycleResolvedRoutingClosure(cycles=cycles, service=valid.service)


def test_closure_rejects_capacity_margin_that_implies_different_retained_capacity():
    valid = _closure()
    cycles = _replace_cycle(
        valid,
        1,
        cartridge_capacity_margin_mL=valid.cycles[1].cartridge_capacity_margin_mL + 0.001,
    )
    with pytest.raises(WasteFluidAccountingError, match="capacity margins do not resolve"):
        CycleResolvedRoutingClosure(cycles=cycles, service=valid.service)


def test_closure_rejects_capacity_disposition_that_disagrees_with_margin():
    valid = _closure()
    cycles = _replace_cycle(
        valid,
        0,
        cartridge_capacity_satisfied=not valid.cycles[0].cartridge_capacity_satisfied,
    )
    with pytest.raises(WasteFluidAccountingError, match="capacity disposition disagrees"):
        CycleResolvedRoutingClosure(cycles=cycles, service=valid.service)


def test_closure_rejects_classified_sink_capacity_drift():
    valid = _closure()
    cycles = _replace_cycle(
        valid,
        1,
        classified_sink_capacity_after_prime_mL=valid.cycles[1].classified_sink_capacity_after_prime_mL + 0.001,
    )
    with pytest.raises(WasteFluidAccountingError, match="classified sink capacity does not reconcile"):
        CycleResolvedRoutingClosure(cycles=cycles, service=valid.service)


def test_builder_still_returns_self_consistent_closure():
    valid = _closure()
    assert valid.service.cycles == len(valid.cycles)
    assert valid.service.prime_events == sum(state.prime_events for state in valid.cycles)
