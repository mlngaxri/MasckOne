from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError
from masck_one.waste_fluid_component_recovery_allocation import evaluate_component_recovery_allocation
from masck_one.waste_fluid_component_sink_closure import evaluate_component_sink_closure
from masck_one.waste_fluid_delivery_recovery import build_authority_delivery_recovery_ledger


def _allocation(*, face, cleanser, post):
    return evaluate_component_recovery_allocation(
        ledger=build_authority_delivery_recovery_ledger(),
        recovered_face_water_mL=face,
        recovered_cleanser_mL=cleanser,
        recovered_post_flush_water_mL=post,
    )


def test_authority_recovery_floor_exposes_unclassified_liquid():
    allocation = _allocation(face=18.0, cleanser=3.0, post=3.84)
    closure = evaluate_component_sink_closure(allocation)
    assert allocation.meets_recovery_floor is True
    assert closure.nonrecovered_mL == pytest.approx(2.76)
    assert closure.residual_capacity_mL == pytest.approx(2.40)
    assert closure.leakage_capacity_mL == pytest.approx(0.30)
    assert closure.classified_capacity_mL == pytest.approx(2.70)
    assert closure.unclassified_liquid_mL == pytest.approx(0.06)
    assert closure.feasible is False


def test_recovery_above_floor_can_close_individual_sinks():
    # 24.90 mL recovered leaves exactly 2.70 mL for the two classified sinks.
    allocation = _allocation(face=18.0, cleanser=3.0, post=3.90)
    closure = evaluate_component_sink_closure(allocation)
    assert closure.feasible is True
    assert closure.unclassified_liquid_mL == pytest.approx(0.0)
    assert closure.residual_allocation_min_mL == pytest.approx(2.40)
    assert closure.residual_allocation_max_mL == pytest.approx(2.40)
    assert closure.leakage_allocation_min_mL == pytest.approx(0.30)
    assert closure.leakage_allocation_max_mL == pytest.approx(0.30)


def test_full_recovery_has_zero_sink_demand():
    ledger = build_authority_delivery_recovery_ledger()
    allocation = evaluate_component_recovery_allocation(
        ledger=ledger,
        recovered_face_water_mL=ledger.service_face_water_mL,
        recovered_cleanser_mL=ledger.service_cleanser_mL,
        recovered_post_flush_water_mL=ledger.service_post_flush_water_mL,
    )
    closure = evaluate_component_sink_closure(allocation)
    assert closure.nonrecovered_mL == pytest.approx(0.0)
    assert closure.residual_allocation_max_mL == pytest.approx(0.0)
    assert closure.leakage_allocation_max_mL == pytest.approx(0.0)
    assert closure.feasible is True


def test_failed_recovery_allocation_also_quantifies_sink_deficit():
    allocation = _allocation(face=16.44, cleanser=0.84, post=2.04)
    closure = evaluate_component_sink_closure(allocation)
    assert allocation.meets_recovery_floor is False
    assert closure.nonrecovered_mL == pytest.approx(8.28)
    assert closure.unclassified_liquid_mL == pytest.approx(5.58)
    assert closure.feasible is False


def test_forged_sink_closure_fails_closed():
    allocation = _allocation(face=18.0, cleanser=3.0, post=3.90)
    valid = evaluate_component_sink_closure(allocation)
    with pytest.raises(WasteFluidAccountingError):
        replace(valid, unclassified_liquid_mL=0.1)
    with pytest.raises(WasteFluidAccountingError):
        replace(valid, feasible=False)
    with pytest.raises(WasteFluidAccountingError):
        replace(valid, residual_capacity_mL=99.0)


def test_exact_component_allocation_source_is_required():
    with pytest.raises(WasteFluidAccountingError):
        evaluate_component_sink_closure(object())
