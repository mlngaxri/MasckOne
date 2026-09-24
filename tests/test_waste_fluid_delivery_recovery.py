from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_delivery_recovery import (
    CleanCycleDeliveryRecoveryLedger,
    build_authority_delivery_recovery_ledger,
)


def test_authority_delivery_components_reconcile_into_recovery_service_ledger():
    ledger = build_authority_delivery_recovery_ledger()
    assert ledger.cycles == 6
    assert ledger.face_water_mL_per_cycle == pytest.approx(3.2)
    assert ledger.cleanser_mL_per_cycle == pytest.approx(0.6)
    assert ledger.post_flush_water_mL_per_cycle == pytest.approx(0.8)
    assert ledger.nominal_mL_per_cycle == pytest.approx(4.6)
    assert ledger.service_face_water_mL == pytest.approx(19.2)
    assert ledger.service_cleanser_mL == pytest.approx(3.6)
    assert ledger.service_post_flush_water_mL == pytest.approx(4.8)
    assert ledger.service_nominal_mL == pytest.approx(27.6)
    assert ledger.minimum_service_recovery_mL == pytest.approx(24.84)
    assert ledger.maximum_service_nonrecovery_mL == pytest.approx(2.76)
    assert ledger.water_fraction + ledger.cleanser_fraction == pytest.approx(1.0)


def test_partial_service_preserves_component_and_recovery_conservation():
    ledger = build_authority_delivery_recovery_ledger(cycles=2)
    assert ledger.service_nominal_mL == pytest.approx(9.2)
    assert ledger.service_face_water_mL + ledger.service_cleanser_mL + ledger.service_post_flush_water_mL == pytest.approx(9.2)
    assert ledger.minimum_service_recovery_mL + ledger.maximum_service_nonrecovery_mL == pytest.approx(9.2)


def test_delivery_authority_rejects_recovery_budget_nominal_drift():
    budget = build_authority_waste_fluid_budget()
    forged = replace(budget, nominal_introduced_mL_per_cycle=4.7)
    with pytest.raises(WasteFluidAccountingError, match="delivery authority nominal volume disagrees"):
        build_authority_delivery_recovery_ledger(budget=forged)


def test_ledger_rejects_forged_component_or_recovery_evidence():
    ledger = build_authority_delivery_recovery_ledger()
    with pytest.raises(WasteFluidAccountingError, match="cycle component conservation"):
        replace(ledger, cleanser_mL_per_cycle=0.7)
    with pytest.raises(WasteFluidAccountingError, match="service recovery floor"):
        replace(ledger, minimum_service_recovery_mL=ledger.minimum_service_recovery_mL + 0.01)
    with pytest.raises(WasteFluidAccountingError, match="service face-water total"):
        replace(ledger, service_face_water_mL=ledger.service_face_water_mL + 0.01)


def test_ledger_rejects_overflow_in_derived_conservation_sums():
    ledger = build_authority_delivery_recovery_ledger()
    with pytest.raises(WasteFluidAccountingError, match="cycle component total must remain finite"):
        replace(ledger, face_water_mL_per_cycle=1e308, cleanser_mL_per_cycle=1e308)
    with pytest.raises(WasteFluidAccountingError, match="recovery conservation total must remain finite"):
        replace(ledger, minimum_service_recovery_mL=1e308, maximum_service_nonrecovery_mL=1e308)
    with pytest.raises(WasteFluidAccountingError, match="service component total must remain finite"):
        replace(ledger, service_face_water_mL=1e308, service_cleanser_mL=1e308)


def test_delivery_recovery_cycles_fail_closed_outside_service_life():
    with pytest.raises(WasteFluidAccountingError, match="cycles must lie within"):
        build_authority_delivery_recovery_ledger(cycles=0)
    with pytest.raises(WasteFluidAccountingError, match="cycles must lie within"):
        build_authority_delivery_recovery_ledger(cycles=7)


def test_ledger_requires_exact_budget_evidence():
    ledger = build_authority_delivery_recovery_ledger()
    with pytest.raises(WasteFluidAccountingError, match="exact WasteFluidBudget"):
        CleanCycleDeliveryRecoveryLedger(
            source_budget=object(),
            cycles=ledger.cycles,
            face_water_mL_per_cycle=ledger.face_water_mL_per_cycle,
            cleanser_mL_per_cycle=ledger.cleanser_mL_per_cycle,
            post_flush_water_mL_per_cycle=ledger.post_flush_water_mL_per_cycle,
            nominal_mL_per_cycle=ledger.nominal_mL_per_cycle,
            service_face_water_mL=ledger.service_face_water_mL,
            service_cleanser_mL=ledger.service_cleanser_mL,
            service_post_flush_water_mL=ledger.service_post_flush_water_mL,
            service_nominal_mL=ledger.service_nominal_mL,
            minimum_service_recovery_mL=ledger.minimum_service_recovery_mL,
            maximum_service_nonrecovery_mL=ledger.maximum_service_nonrecovery_mL,
        )
