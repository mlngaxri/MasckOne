from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_recovery_requirement import derive_service_recovery_requirement


def test_authority_service_quantifies_existing_nominal_recovery_shortfall():
    result = derive_service_recovery_requirement(build_authority_waste_fluid_budget(), cycles=6, prime_events=0)
    assert result.nominal_service_liquid_mL == pytest.approx(27.600)
    assert result.available_nominal_nonrecovery_sink_mL == pytest.approx(2.700)
    assert result.required_nominal_recovery_mL == pytest.approx(24.900)
    assert result.required_nominal_recovery_ratio == pytest.approx(0.9021739130434783)
    assert result.recovery_ratio_shortfall == pytest.approx(0.0021739130434783)
    assert result.additional_nominal_recovery_required_mL == pytest.approx(0.060)
    assert result.recovery_requirement_closes is False


def test_prime_sink_use_raises_required_nominal_recovery_ratio():
    result = derive_service_recovery_requirement(
        build_authority_waste_fluid_budget(), cycles=6, prime_events=6,
        prime_recovery_ratio_contract=0.90, prime_residual_ratio_contract=0.08,
        prime_external_leakage_ratio_contract=0.02,
    )
    assert result.available_nominal_nonrecovery_sink_mL == pytest.approx(2.460)
    assert result.required_nominal_recovery_ratio == pytest.approx(0.9108695652173913)
    assert result.recovery_ratio_shortfall == pytest.approx(0.0108695652173913)
    assert result.additional_nominal_recovery_required_mL == pytest.approx(0.300)
    assert result.recovery_requirement_closes is False


def test_recovery_floor_at_derived_threshold_closes_requirement():
    base = build_authority_waste_fluid_budget()
    threshold = derive_service_recovery_requirement(
        base, cycles=6, prime_events=6, prime_recovery_ratio_contract=0.90,
        prime_residual_ratio_contract=0.08, prime_external_leakage_ratio_contract=0.02,
    ).required_nominal_recovery_ratio
    result = derive_service_recovery_requirement(
        replace(base, recovery_ratio_min=threshold), cycles=6, prime_events=6,
        prime_recovery_ratio_contract=0.90, prime_residual_ratio_contract=0.08,
        prime_external_leakage_ratio_contract=0.02,
    )
    assert result.recovery_ratio_shortfall == pytest.approx(0.0, abs=1e-12)
    assert result.additional_nominal_recovery_required_mL == pytest.approx(0.0, abs=1e-12)
    assert result.recovery_requirement_closes is True


def test_prime_recovery_only_does_not_consume_nominal_sink_capacity():
    result = derive_service_recovery_requirement(
        build_authority_waste_fluid_budget(), cycles=6, prime_events=6,
        prime_recovery_ratio_contract=1.0,
    )
    assert result.available_nominal_nonrecovery_sink_mL == pytest.approx(2.700)
    assert result.required_nominal_recovery_ratio == pytest.approx(0.9021739130434783)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("available_nominal_nonrecovery_sink_mL", 2.8),
        ("required_nominal_recovery_mL", 24.8),
        ("required_nominal_recovery_ratio", 0.91),
        ("recovery_ratio_shortfall", 0.01),
        ("additional_nominal_recovery_required_mL", 0.10),
        ("recovery_requirement_closes", True),
        ("authority_recovery_ratio_min", 0.91),
        ("nominal_service_liquid_mL", 27.5),
    ],
)
def test_recovery_requirement_rejects_forged_derived_or_authority_evidence(field, value):
    result = derive_service_recovery_requirement(build_authority_waste_fluid_budget(), cycles=6, prime_events=0)
    with pytest.raises(WasteFluidAccountingError):
        replace(result, **{field: value})


def test_recovery_requirement_rejects_budget_substitution_even_when_result_fields_are_unchanged():
    result = derive_service_recovery_requirement(build_authority_waste_fluid_budget(), cycles=6, prime_events=0)
    forged_budget = replace(result.source_budget, nominal_introduced_mL_per_cycle=4.5)
    with pytest.raises(WasteFluidAccountingError):
        replace(result, source_budget=forged_budget)


def test_recovery_requirement_rejects_routing_evidence_from_different_budget():
    result = derive_service_recovery_requirement(build_authority_waste_fluid_budget(), cycles=6, prime_events=0)
    forged_source = replace(result.source, minimum_nominal_liquid_routed_to_cartridge_mL=24.0)
    with pytest.raises(WasteFluidAccountingError):
        replace(result, source=forged_source)
