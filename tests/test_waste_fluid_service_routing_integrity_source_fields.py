from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_closure import screen_service_routing_closure
from masck_one.waste_fluid_service_routing_integrity import validate_service_routing_closure_evidence


def _evidence():
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


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("cycles", 0, "invalid cycle window"),
        ("cycles", 1.5, "invalid cycle window"),
        ("prime_events", -1, "invalid prime-event count"),
        ("prime_events", 1.5, "invalid prime-event count"),
        ("prime_recovery_ratio_contract", float("nan"), "prime_recovery_ratio_contract"),
        ("prime_residual_ratio_contract", float("inf"), "prime_residual_ratio_contract"),
        ("prime_external_leakage_ratio_contract", -.01, "prime_external_leakage_ratio_contract"),
    ],
)
def test_rejects_invalid_source_fields_before_derived_evidence_can_be_trusted(field, value, message):
    budget, closure = _evidence()
    corrupted = replace(closure, **{field: value})
    with pytest.raises(WasteFluidAccountingError, match=message):
        validate_service_routing_closure_evidence(budget, corrupted)


@pytest.mark.parametrize(
    ("field", "delta"),
    [
        ("prime_recovery_ratio_contract", -.01),
        ("prime_residual_ratio_contract", -.01),
        ("prime_external_leakage_ratio_contract", -.01),
    ],
)
def test_rejects_coherent_looking_but_stale_source_contracts(field, delta):
    budget, closure = _evidence()
    corrupted = replace(closure, **{field: getattr(closure, field) + delta})
    with pytest.raises(WasteFluidAccountingError):
        validate_service_routing_closure_evidence(budget, corrupted)


def test_rejects_service_window_beyond_budget_authority():
    budget, closure = _evidence()
    corrupted = replace(closure, cycles=budget.service_cycles + 1)
    with pytest.raises(WasteFluidAccountingError, match="invalid cycle window"):
        validate_service_routing_closure_evidence(budget, corrupted)
