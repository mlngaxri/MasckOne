from dataclasses import replace

import pytest

from masck_one.treatment_recovery_readiness import screen_treatment_recovery_readiness
from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_cycle_routing import CycleResolvedRoutingClosure, screen_cycle_resolved_routing_closure


def _closure():
    return screen_cycle_resolved_routing_closure(
        build_authority_waste_fluid_budget(),
        prime_events_by_cycle=[0, 1, 0],
        prime_recovery_ratio_contract=1.0,
    )


def _unchecked_with_state(valid, index, state):
    cycles = list(valid.cycles)
    cycles[index] = state
    forged = object.__new__(CycleResolvedRoutingClosure)
    object.__setattr__(forged, "cycles", tuple(cycles))
    object.__setattr__(forged, "service", valid.service)
    return forged


def test_handoff_rejects_simultaneous_nominal_sink_deficit_and_headroom():
    valid = _closure()
    state = replace(
        valid.cycles[0],
        nominal_unclassified_nonrecovery_after_prime_mL=0.01,
        classified_sink_headroom_after_nominal_mL=0.01,
    )
    forged = _unchecked_with_state(valid, 0, state)
    with pytest.raises(WasteFluidAccountingError, match="simultaneously have nominal sink deficit"):
        screen_treatment_recovery_readiness(forged)


def test_handoff_rejects_complete_routing_with_unclassified_nominal_liquid():
    valid = _closure()
    state = replace(
        valid.cycles[0],
        nominal_unclassified_nonrecovery_after_prime_mL=0.01,
        classified_sink_headroom_after_nominal_mL=0.0,
        local_routing_contract_complete=True,
    )
    forged = _unchecked_with_state(valid, 0, state)
    with pytest.raises(WasteFluidAccountingError, match="routing cannot be complete"):
        screen_treatment_recovery_readiness(forged)
