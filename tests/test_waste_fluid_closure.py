from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import build_authority_waste_fluid_budget
from masck_one.waste_fluid_closure import screen_nonrecovery_closure


def test_authority_profile_exposes_unclassified_nonrecovery_allowance():
    closure = screen_nonrecovery_closure(build_authority_waste_fluid_budget())
    assert closure.maximum_unrecovered_nominal_mL == pytest.approx(0.460)
    assert closure.residual_ceiling_mL == pytest.approx(0.400)
    assert closure.external_leakage_ceiling_mL == pytest.approx(0.050)
    assert closure.classified_nonrecovery_ceiling_mL == pytest.approx(0.450)
    assert closure.unclassified_nonrecovery_allowance_mL == pytest.approx(0.010)
    assert closure.classified_sink_headroom_mL == pytest.approx(0.0)
    assert closure.closes_using_only_classified_sinks is False


def test_closure_at_exact_cross_requirement_threshold_has_no_gap():
    budget = build_authority_waste_fluid_budget()
    threshold = budget.recovery_ratio_for_residual_leakage_closure
    closure = screen_nonrecovery_closure(replace(budget, recovery_ratio_min=threshold))
    assert closure.unclassified_nonrecovery_allowance_mL == pytest.approx(0.0, abs=1e-12)
    assert closure.classified_sink_headroom_mL == pytest.approx(0.0, abs=1e-12)
    assert closure.closes_using_only_classified_sinks is True


def test_higher_recovery_floor_reports_classified_sink_headroom_not_negative_gap():
    budget = replace(build_authority_waste_fluid_budget(), recovery_ratio_min=0.95)
    closure = screen_nonrecovery_closure(budget)
    assert closure.maximum_unrecovered_nominal_mL == pytest.approx(0.230)
    assert closure.unclassified_nonrecovery_allowance_mL == pytest.approx(0.0)
    assert closure.classified_sink_headroom_mL == pytest.approx(0.220)
    assert closure.closes_using_only_classified_sinks is True


def test_closure_screen_does_not_credit_sinks_to_cartridge_capacity():
    budget = build_authority_waste_fluid_budget()
    baseline = budget.maximum_cartridge_inflow_screen_mL
    screen_nonrecovery_closure(budget)
    assert budget.maximum_cartridge_inflow_screen_mL == pytest.approx(baseline)
