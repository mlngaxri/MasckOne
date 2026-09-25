from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_closure_margin import derive_service_closure_margin
from masck_one.waste_fluid_recovery_requirement import derive_service_recovery_requirement


def test_authority_closure_margin_exposes_per_cycle_deficit():
    requirement = derive_service_recovery_requirement(build_authority_waste_fluid_budget(), cycles=6, prime_events=0)
    margin = derive_service_closure_margin(requirement)
    assert margin.configured_nominal_nonrecovery_mL == pytest.approx(2.760)
    assert margin.available_sink_mL == pytest.approx(2.700)
    assert margin.signed_sink_margin_mL == pytest.approx(-0.060)
    assert margin.sink_surplus_mL == pytest.approx(0.0)
    assert margin.service_deficit_mL == pytest.approx(0.060)
    assert margin.signed_sink_margin_mL_per_cycle == pytest.approx(-0.010)
    assert margin.sink_surplus_mL_per_cycle == pytest.approx(0.0)
    assert margin.deficit_mL_per_cycle == pytest.approx(0.010)
    assert margin.required_combined_sink_mL_per_cycle_at_authority_recovery == pytest.approx(0.460)
    assert margin.configured_combined_sink_mL_per_cycle == pytest.approx(0.450)
    assert margin.combined_sink_shortfall_mL_per_cycle == pytest.approx(0.010)
    assert margin.closes is False


def test_prime_sink_consumption_increases_closure_deficit():
    requirement = derive_service_recovery_requirement(
        build_authority_waste_fluid_budget(), cycles=6, prime_events=6,
        prime_recovery_ratio_contract=0.90, prime_residual_ratio_contract=0.08,
        prime_external_leakage_ratio_contract=0.02,
    )
    margin = derive_service_closure_margin(requirement)
    assert margin.available_sink_mL == pytest.approx(2.460)
    assert margin.signed_sink_margin_mL == pytest.approx(-0.300)
    assert margin.service_deficit_mL == pytest.approx(0.300)
    assert margin.deficit_mL_per_cycle == pytest.approx(0.050)
    assert margin.configured_combined_sink_mL_per_cycle == pytest.approx(0.410)


def test_threshold_recovery_closes_margin_without_extra_sink():
    base = build_authority_waste_fluid_budget()
    threshold = derive_service_recovery_requirement(base, cycles=6, prime_events=0).required_nominal_recovery_ratio
    requirement = derive_service_recovery_requirement(replace(base, recovery_ratio_min=threshold), cycles=6, prime_events=0)
    margin = derive_service_closure_margin(requirement)
    assert margin.signed_sink_margin_mL == pytest.approx(0.0, abs=1e-12)
    assert margin.sink_surplus_mL == pytest.approx(0.0, abs=1e-12)
    assert margin.service_deficit_mL == pytest.approx(0.0, abs=1e-12)
    assert margin.combined_sink_shortfall_mL_per_cycle == pytest.approx(0.0, abs=1e-12)
    assert margin.closes is True


def test_recovery_above_threshold_exposes_positive_sink_surplus():
    base = build_authority_waste_fluid_budget()
    requirement = derive_service_recovery_requirement(replace(base, recovery_ratio_min=0.92), cycles=6, prime_events=0)
    margin = derive_service_closure_margin(requirement)
    # 27.6 mL * 8% = 2.208 mL nonrecovery against 2.700 mL sink capacity.
    assert margin.signed_sink_margin_mL == pytest.approx(0.492)
    assert margin.sink_surplus_mL == pytest.approx(0.492)
    assert margin.service_deficit_mL == pytest.approx(0.0)
    assert margin.signed_sink_margin_mL_per_cycle == pytest.approx(0.082)
    assert margin.sink_surplus_mL_per_cycle == pytest.approx(0.082)
    assert margin.deficit_mL_per_cycle == pytest.approx(0.0)
    assert margin.closes is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("configured_nominal_nonrecovery_mL", 2.70),
        ("available_sink_mL", 2.71),
        ("signed_sink_margin_mL", -0.05),
        ("sink_surplus_mL", 0.01),
        ("service_deficit_mL", 0.05),
        ("signed_sink_margin_mL_per_cycle", -0.02),
        ("sink_surplus_mL_per_cycle", 0.01),
        ("deficit_mL_per_cycle", 0.02),
        ("required_combined_sink_mL_per_cycle_at_authority_recovery", 0.45),
        ("configured_combined_sink_mL_per_cycle", 0.46),
        ("combined_sink_shortfall_mL_per_cycle", 0.02),
        ("closes", True),
    ],
)
def test_closure_margin_rejects_forged_evidence(field, value):
    requirement = derive_service_recovery_requirement(build_authority_waste_fluid_budget(), cycles=6, prime_events=0)
    margin = derive_service_closure_margin(requirement)
    with pytest.raises(WasteFluidAccountingError):
        replace(margin, **{field: value})


def test_closure_margin_rejects_cycle_substitution():
    requirement = derive_service_recovery_requirement(build_authority_waste_fluid_budget(), cycles=6, prime_events=0)
    margin = derive_service_closure_margin(requirement)
    with pytest.raises(WasteFluidAccountingError):
        replace(margin, cycles=5)
