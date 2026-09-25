from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_recovery_requirement import derive_service_recovery_requirement
from masck_one.waste_fluid_sink_allocation import derive_service_sink_allocation_window


def _requirement(**kwargs):
    return derive_service_recovery_requirement(build_authority_waste_fluid_budget(), cycles=6, prime_events=0, **kwargs)


def test_authority_baseline_exposes_no_feasible_individual_sink_allocation():
    result = derive_service_sink_allocation_window(_requirement())
    assert result.nominal_nonrecovery_mL == pytest.approx(2.76)
    assert result.residual_capacity_mL == pytest.approx(2.4)
    assert result.leakage_capacity_mL == pytest.approx(0.3)
    assert result.residual_allocation_min_mL == pytest.approx(2.46)
    assert result.residual_allocation_max_mL == pytest.approx(2.4)
    assert result.leakage_allocation_min_mL == pytest.approx(0.36)
    assert result.leakage_allocation_max_mL == pytest.approx(0.3)
    assert result.residual_capacity_shortfall_mL == pytest.approx(0.06)
    assert result.leakage_capacity_shortfall_mL == pytest.approx(0.06)
    assert result.allocation_interval_gap_mL == pytest.approx(0.06)
    assert result.feasible is False


def test_recovery_at_closure_threshold_has_exact_feasible_boundary():
    baseline = _requirement()
    budget = replace(baseline.source_budget, recovery_ratio_min=baseline.required_nominal_recovery_ratio)
    requirement = derive_service_recovery_requirement(budget, cycles=6, prime_events=0)
    result = derive_service_sink_allocation_window(requirement)
    assert result.feasible is True
    assert result.allocation_interval_gap_mL == pytest.approx(0.0, abs=1e-12)
    assert result.residual_capacity_shortfall_mL == pytest.approx(0.0, abs=1e-12)
    assert result.leakage_capacity_shortfall_mL == pytest.approx(0.0, abs=1e-12)
    assert result.residual_allocation_min_mL == pytest.approx(result.residual_allocation_max_mL)
    assert result.leakage_allocation_min_mL == pytest.approx(result.leakage_allocation_max_mL)
    assert result.residual_allocation_min_mL + result.leakage_allocation_max_mL == pytest.approx(result.nominal_nonrecovery_mL)


def test_prime_sink_use_tightens_each_allocation_bound_and_deficit():
    requirement = derive_service_recovery_requirement(
        build_authority_waste_fluid_budget(), cycles=6, prime_events=6,
        prime_recovery_ratio_contract=0.90,
        prime_residual_ratio_contract=0.08,
        prime_external_leakage_ratio_contract=0.02,
    )
    result = derive_service_sink_allocation_window(requirement)
    assert result.residual_capacity_mL < 2.4
    assert result.leakage_capacity_mL < 0.3
    assert result.allocation_interval_gap_mL == pytest.approx(0.3)
    assert result.residual_capacity_shortfall_mL == pytest.approx(0.3)
    assert result.leakage_capacity_shortfall_mL == pytest.approx(0.3)
    assert result.feasible is False


def test_forged_allocation_evidence_fails_closed():
    result = derive_service_sink_allocation_window(_requirement())
    with pytest.raises(WasteFluidAccountingError):
        replace(result, residual_allocation_min_mL=result.residual_allocation_min_mL - 0.1)
    with pytest.raises(WasteFluidAccountingError):
        replace(result, leakage_allocation_max_mL=result.leakage_allocation_max_mL + 0.1)
    with pytest.raises(WasteFluidAccountingError):
        replace(result, residual_capacity_shortfall_mL=0.0)
    with pytest.raises(WasteFluidAccountingError):
        replace(result, leakage_capacity_shortfall_mL=0.0)
    with pytest.raises(WasteFluidAccountingError):
        replace(result, allocation_interval_gap_mL=0.0)
    with pytest.raises(WasteFluidAccountingError):
        replace(result, feasible=True)


def test_raw_or_lookalike_evidence_is_rejected():
    with pytest.raises(WasteFluidAccountingError):
        derive_service_sink_allocation_window(object())
