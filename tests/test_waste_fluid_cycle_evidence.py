from dataclasses import replace

import pytest

from masck_one.treatment_recovery_readiness import screen_treatment_recovery_readiness
from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_cycle_evidence import validate_cycle_routing_evidence
from masck_one.waste_fluid_cycle_routing import CycleResolvedRoutingClosure, screen_cycle_resolved_routing_closure


def _closure():
    return screen_cycle_resolved_routing_closure(
        build_authority_waste_fluid_budget(),
        prime_events_by_cycle=[0, 1, 0],
        prime_recovery_ratio_contract=1.0,
    )


def _forge(valid, index, **changes):
    cycles = list(valid.cycles)
    cycles[index] = replace(cycles[index], **changes)
    return object.__new__(CycleResolvedRoutingClosure), tuple(cycles)


def _unchecked_closure(valid, cycles):
    forged = object.__new__(CycleResolvedRoutingClosure)
    object.__setattr__(forged, "cycles", cycles)
    object.__setattr__(forged, "service", valid.service)
    return forged


def test_valid_builder_evidence_passes_independent_validator_and_handoff():
    valid = _closure()
    validate_cycle_routing_evidence(valid)
    assert screen_treatment_recovery_readiness(valid).post_recovery_handoff_permitted


def test_handoff_rejects_forged_local_routing_total():
    valid = _closure()
    state = replace(valid.cycles[0], minimum_total_routed_to_cartridge_mL=valid.cycles[0].minimum_total_routed_to_cartridge_mL + 0.01)
    forged = _unchecked_closure(valid, (state,) + valid.cycles[1:])
    with pytest.raises(WasteFluidAccountingError, match="minimum routing components"):
        screen_treatment_recovery_readiness(forged)


def test_handoff_rejects_forged_intermediate_cumulative_routing():
    valid = _closure()
    state = replace(valid.cycles[1], cumulative_minimum_cartridge_routing_mL=valid.cycles[1].cumulative_minimum_cartridge_routing_mL + 0.01)
    forged = _unchecked_closure(valid, valid.cycles[:1] + (state,) + valid.cycles[2:])
    with pytest.raises(WasteFluidAccountingError, match="cumulative minimum routing"):
        screen_treatment_recovery_readiness(forged)


def test_handoff_rejects_capacity_boolean_that_contradicts_margin():
    valid = _closure()
    state = replace(valid.cycles[0], cartridge_capacity_satisfied=not valid.cycles[0].cartridge_capacity_satisfied)
    forged = _unchecked_closure(valid, (state,) + valid.cycles[1:])
    with pytest.raises(WasteFluidAccountingError, match="capacity boolean contradicts margin"):
        screen_treatment_recovery_readiness(forged)


def test_handoff_rejects_nonfinite_numeric_evidence():
    valid = _closure()
    state = replace(valid.cycles[0], cartridge_capacity_margin_mL=float("nan"))
    forged = _unchecked_closure(valid, (state,) + valid.cycles[1:])
    with pytest.raises(WasteFluidAccountingError, match="finite numeric evidence"):
        screen_treatment_recovery_readiness(forged)


@pytest.mark.parametrize(
    "field",
    [
        "prime_residual_mL",
        "prime_external_leakage_mL",
        "minimum_nominal_routed_to_cartridge_mL",
        "minimum_prime_routed_to_cartridge_mL",
        "minimum_total_routed_to_cartridge_mL",
        "cumulative_minimum_cartridge_routing_mL",
        "cumulative_maximum_cartridge_inflow_mL",
        "cartridge_occupancy_uncertainty_mL",
        "residual_ceiling_margin_mL",
        "external_leakage_ceiling_margin_mL",
        "classified_sink_capacity_after_prime_mL",
        "nominal_unclassified_nonrecovery_after_prime_mL",
        "classified_sink_headroom_after_nominal_mL",
    ],
)
def test_handoff_rejects_negative_physical_volume_evidence(field):
    valid = _closure()
    state = replace(valid.cycles[0], **{field: -0.01})
    forged = _unchecked_closure(valid, (state,) + valid.cycles[1:])
    with pytest.raises(WasteFluidAccountingError, match="nonnegative volume evidence"):
        screen_treatment_recovery_readiness(forged)


def test_handoff_rejects_capacity_baseline_drift_between_cycles():
    valid = _closure()
    state = replace(valid.cycles[1], minimum_routing_capacity_margin_mL=valid.cycles[1].minimum_routing_capacity_margin_mL + 0.01)
    forged = _unchecked_closure(valid, valid.cycles[:1] + (state,) + valid.cycles[2:])
    with pytest.raises(WasteFluidAccountingError, match="different retained capacities|drifts across profile"):
        screen_treatment_recovery_readiness(forged)


def test_handoff_rejects_local_minimum_routing_above_local_conservative_inflow():
    valid = _closure()
    first = valid.cycles[0]
    second = valid.cycles[1]
    local_minimum = second.minimum_total_routed_to_cartridge_mL
    forged_cumulative_maximum = first.cumulative_maximum_cartridge_inflow_mL + local_minimum - 0.01
    state = replace(
        second,
        cumulative_maximum_cartridge_inflow_mL=forged_cumulative_maximum,
        cartridge_occupancy_uncertainty_mL=max(0.0, forged_cumulative_maximum - second.cumulative_minimum_cartridge_routing_mL),
    )
    forged = _unchecked_closure(valid, valid.cycles[:1] + (state,) + valid.cycles[2:])
    with pytest.raises(WasteFluidAccountingError, match="local conservative inflow bound"):
        screen_treatment_recovery_readiness(forged)


def test_handoff_rejects_classified_sink_capacity_component_drift():
    valid = _closure()
    state = replace(
        valid.cycles[1],
        classified_sink_capacity_after_prime_mL=valid.cycles[1].classified_sink_capacity_after_prime_mL + 0.01,
    )
    forged = _unchecked_closure(valid, valid.cycles[:1] + (state,) + valid.cycles[2:])
    with pytest.raises(WasteFluidAccountingError, match="classified sink capacity"):
        screen_treatment_recovery_readiness(forged)
