from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError
from masck_one.waste_fluid_component_recovery_allocation import (
    ComponentRecoveryAllocation,
    evaluate_component_recovery_allocation,
)
from masck_one.waste_fluid_delivery_recovery import build_authority_delivery_recovery_ledger


def test_authority_floor_allocation_reconciles_jointly():
    ledger = build_authority_delivery_recovery_ledger()
    # One admissible allocation exactly at the 24.84 mL aggregate floor.
    result = evaluate_component_recovery_allocation(
        ledger=ledger,
        recovered_face_water_mL=18.0,
        recovered_cleanser_mL=3.0,
        recovered_post_flush_water_mL=3.84,
    )
    assert result.total_recovered_mL == pytest.approx(24.84)
    assert result.total_nonrecovered_mL == pytest.approx(2.76)
    assert result.recovery_ratio == pytest.approx(0.90)
    assert result.meets_recovery_floor is True


def test_individually_plausible_components_can_fail_joint_floor():
    ledger = build_authority_delivery_recovery_ledger()
    result = evaluate_component_recovery_allocation(
        ledger=ledger,
        recovered_face_water_mL=16.44,
        recovered_cleanser_mL=0.84,
        recovered_post_flush_water_mL=2.04,
    )
    # Each value is an individual lower bound, but those extrema cannot be
    # interpreted as a simultaneously passing allocation.
    assert result.total_recovered_mL == pytest.approx(19.32)
    assert result.total_nonrecovered_mL == pytest.approx(8.28)
    assert result.meets_recovery_floor is False


def test_full_recovery_is_valid_because_requirement_is_a_floor():
    ledger = build_authority_delivery_recovery_ledger()
    result = evaluate_component_recovery_allocation(
        ledger=ledger,
        recovered_face_water_mL=ledger.service_face_water_mL,
        recovered_cleanser_mL=ledger.service_cleanser_mL,
        recovered_post_flush_water_mL=ledger.service_post_flush_water_mL,
    )
    assert result.recovery_ratio == pytest.approx(1.0)
    assert result.total_nonrecovered_mL == pytest.approx(0.0)
    assert result.meets_recovery_floor is True


def test_component_overrecovery_is_rejected():
    ledger = build_authority_delivery_recovery_ledger()
    with pytest.raises(WasteFluidAccountingError):
        evaluate_component_recovery_allocation(
            ledger=ledger,
            recovered_face_water_mL=ledger.service_face_water_mL + 0.001,
            recovered_cleanser_mL=0.0,
            recovered_post_flush_water_mL=0.0,
        )


def test_forged_derived_totals_fail_closed():
    ledger = build_authority_delivery_recovery_ledger()
    valid = evaluate_component_recovery_allocation(
        ledger=ledger,
        recovered_face_water_mL=18.0,
        recovered_cleanser_mL=3.0,
        recovered_post_flush_water_mL=3.84,
    )
    with pytest.raises(WasteFluidAccountingError):
        replace(valid, total_nonrecovered_mL=0.0)
    with pytest.raises(WasteFluidAccountingError):
        replace(valid, recovery_ratio=0.99)
    with pytest.raises(WasteFluidAccountingError):
        replace(valid, meets_recovery_floor=False)


def test_exact_ledger_type_is_required():
    with pytest.raises(WasteFluidAccountingError):
        evaluate_component_recovery_allocation(
            ledger=object(),
            recovered_face_water_mL=0.0,
            recovered_cleanser_mL=0.0,
            recovered_post_flush_water_mL=0.0,
        )
