from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_component_prime_sink_closure import evaluate_prime_adjusted_component_sink_closure
from masck_one.waste_fluid_component_recovery_allocation import evaluate_component_recovery_allocation
from masck_one.waste_fluid_cycle_routing import screen_cycle_resolved_routing_closure
from masck_one.waste_fluid_delivery_recovery import build_authority_delivery_recovery_ledger


def _allocation(*, post):
    return evaluate_component_recovery_allocation(
        ledger=build_authority_delivery_recovery_ledger(),
        recovered_face_water_mL=18.0,
        recovered_cleanser_mL=3.0,
        recovered_post_flush_water_mL=post,
    )


def _routing():
    return screen_cycle_resolved_routing_closure(
        build_authority_waste_fluid_budget(),
        prime_events_by_cycle=[1] * 6,
        prime_recovery_ratio_contract=.90,
        prime_residual_ratio_contract=.08,
        prime_external_leakage_ratio_contract=.02,
    )


def test_prime_sink_use_invalidates_nominal_closure_that_only_fits_without_prime():
    # 24.90 mL nominal recovery leaves 2.70 mL, exactly the unprimed sink capacity.
    # Six primes consume 0.192 mL residual and 0.048 mL leakage capacity.
    closure = evaluate_prime_adjusted_component_sink_closure(_allocation(post=3.90), _routing())
    assert closure.nominal_nonrecovered_mL == pytest.approx(2.70)
    assert closure.prime_residual_mL == pytest.approx(.192)
    assert closure.prime_external_leakage_mL == pytest.approx(.048)
    assert closure.residual_capacity_after_prime_mL == pytest.approx(2.208)
    assert closure.leakage_capacity_after_prime_mL == pytest.approx(.252)
    assert closure.classified_capacity_after_prime_mL == pytest.approx(2.46)
    assert closure.unclassified_nominal_liquid_mL == pytest.approx(.24)
    assert closure.feasible is False


def test_additional_nominal_recovery_can_close_prime_adjusted_sinks_exactly():
    # 25.14 mL nominal recovery leaves 2.46 mL, matching capacity after prime use.
    closure = evaluate_prime_adjusted_component_sink_closure(_allocation(post=4.14), _routing())
    assert closure.feasible is True
    assert closure.unclassified_nominal_liquid_mL == pytest.approx(0.0)
    assert closure.residual_allocation_min_mL == pytest.approx(2.208)
    assert closure.residual_allocation_max_mL == pytest.approx(2.208)
    assert closure.leakage_allocation_min_mL == pytest.approx(.252)
    assert closure.leakage_allocation_max_mL == pytest.approx(.252)


def test_full_nominal_recovery_needs_no_remaining_sink_capacity():
    ledger = build_authority_delivery_recovery_ledger()
    allocation = evaluate_component_recovery_allocation(
        ledger=ledger,
        recovered_face_water_mL=ledger.service_face_water_mL,
        recovered_cleanser_mL=ledger.service_cleanser_mL,
        recovered_post_flush_water_mL=ledger.service_post_flush_water_mL,
    )
    closure = evaluate_prime_adjusted_component_sink_closure(allocation, _routing())
    assert closure.nominal_nonrecovered_mL == pytest.approx(0.0)
    assert closure.feasible is True


def test_mismatched_service_interval_fails_closed():
    short_routing = screen_cycle_resolved_routing_closure(
        build_authority_waste_fluid_budget(), prime_events_by_cycle=[0] * 5
    )
    with pytest.raises(WasteFluidAccountingError, match="same service interval"):
        evaluate_prime_adjusted_component_sink_closure(_allocation(post=4.14), short_routing)


def test_forged_prime_adjusted_evidence_fails_closed():
    valid = evaluate_prime_adjusted_component_sink_closure(_allocation(post=4.14), _routing())
    with pytest.raises(WasteFluidAccountingError):
        replace(valid, residual_capacity_after_prime_mL=99.0)
    with pytest.raises(WasteFluidAccountingError):
        replace(valid, unclassified_nominal_liquid_mL=.1)
    with pytest.raises(WasteFluidAccountingError):
        replace(valid, feasible=False)


def test_exact_sources_are_required():
    with pytest.raises(WasteFluidAccountingError):
        evaluate_prime_adjusted_component_sink_closure(object(), _routing())
    with pytest.raises(WasteFluidAccountingError):
        evaluate_prime_adjusted_component_sink_closure(_allocation(post=4.14), object())
