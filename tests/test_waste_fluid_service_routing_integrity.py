from dataclasses import fields, replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_closure import ServiceRoutingClosure, screen_service_routing_closure
from masck_one.waste_fluid_service_routing_integrity import validate_service_routing_closure_evidence


def _closure():
    budget = build_authority_waste_fluid_budget()
    closure = screen_service_routing_closure(
        budget,
        cycles=budget.service_cycles,
        prime_events=1,
        prime_recovery_ratio_contract=.90,
        prime_residual_ratio_contract=.08,
        prime_external_leakage_ratio_contract=.02,
    )
    return budget, closure


def test_authority_bound_service_routing_evidence_validates():
    budget, closure = _closure()
    validate_service_routing_closure_evidence(budget, closure)


@pytest.mark.parametrize(
    "field",
    [
        "minimum_nominal_liquid_routed_to_cartridge_mL",
        "nominal_unclassified_nonrecovery_mL",
        "total_prime_liquid_mL",
        "minimum_prime_liquid_routed_to_cartridge_mL",
        "maximum_prime_residual_mL",
        "maximum_prime_external_leakage_mL",
        "service_residual_ceiling_mL",
        "service_external_leakage_ceiling_mL",
        "prime_residual_ceiling_margin_mL",
        "prime_external_leakage_ceiling_margin_mL",
        "shared_sink_unclassified_nonrecovery_mL",
        "prime_liquid_without_routing_contract_mL",
        "total_liquid_without_routing_contract_mL",
    ],
)
def test_rejects_stale_derived_volume_evidence(field):
    budget, closure = _closure()
    stale = replace(closure, **{field: getattr(closure, field) + .1})
    with pytest.raises(WasteFluidAccountingError, match=field):
        validate_service_routing_closure_evidence(budget, stale)


def test_rejects_nonfinite_derived_volume_evidence():
    budget, closure = _closure()
    stale = replace(closure, minimum_nominal_liquid_routed_to_cartridge_mL=float("nan"))
    with pytest.raises(WasteFluidAccountingError, match="finite numeric evidence"):
        validate_service_routing_closure_evidence(budget, stale)


def test_rejects_stale_routing_completeness_state():
    budget, closure = _closure()
    stale = replace(closure, routing_contract_complete=not closure.routing_contract_complete)
    with pytest.raises(WasteFluidAccountingError, match="completeness state is stale"):
        validate_service_routing_closure_evidence(budget, stale)


def test_validator_covers_every_service_routing_field():
    expected = {field.name for field in fields(ServiceRoutingClosure)}
    assert expected == {
        "cycles", "prime_events", "minimum_nominal_liquid_routed_to_cartridge_mL",
        "nominal_unclassified_nonrecovery_mL", "total_prime_liquid_mL",
        "prime_recovery_ratio_contract", "prime_residual_ratio_contract",
        "prime_external_leakage_ratio_contract", "minimum_prime_liquid_routed_to_cartridge_mL",
        "maximum_prime_residual_mL", "maximum_prime_external_leakage_mL",
        "service_residual_ceiling_mL", "service_external_leakage_ceiling_mL",
        "prime_residual_ceiling_margin_mL", "prime_external_leakage_ceiling_margin_mL",
        "shared_sink_unclassified_nonrecovery_mL", "prime_liquid_without_routing_contract_mL",
        "total_liquid_without_routing_contract_mL", "routing_contract_complete",
    }
