import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_closure import screen_service_routing_closure


def test_aggregate_routing_cannot_extend_past_configured_service_life():
    budget = build_authority_waste_fluid_budget()
    assert budget.service_cycles == 6
    with pytest.raises(WasteFluidAccountingError, match="exceeds configured service life"):
        screen_service_routing_closure(
            budget,
            cycles=7,
            prime_events=0,
            prime_recovery_ratio_contract=1.0,
        )


def test_aggregate_routing_accepts_service_life_prefix_without_granting_future_sink_capacity():
    closure = screen_service_routing_closure(
        build_authority_waste_fluid_budget(),
        cycles=3,
        prime_events=0,
        prime_recovery_ratio_contract=1.0,
    )
    assert closure.cycles == 3
    assert closure.service_residual_ceiling_mL == pytest.approx(1.2)
    assert closure.service_external_leakage_ceiling_mL == pytest.approx(0.15)
    assert closure.nominal_unclassified_nonrecovery_mL == pytest.approx(0.03)
