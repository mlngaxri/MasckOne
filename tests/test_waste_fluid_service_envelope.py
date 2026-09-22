import math

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_service_envelope import evaluate_reprime_service_envelope


def _envelope():
    return evaluate_reprime_service_envelope(
        build_authority_waste_fluid_budget(),
        cycles=6,
        prime_recovery_ratio_contract=.90,
        prime_residual_ratio_contract=.08,
        prime_external_leakage_ratio_contract=.02,
    )


def test_joint_envelope_finds_true_reprime_boundary_beyond_fail_conservative_screen():
    budget = build_authority_waste_fluid_budget()
    envelope = _envelope()

    # The all-inflow packaging screen allows only 18 events because it takes no
    # sink credit. Joint closure can prove 25 events fit, but the 26th cannot.
    assert budget.maximum_prime_events_that_fit(cycles=6) == 18
    assert envelope.maximum_feasible_prime_events == 25
    assert envelope.limiting_next_prime_events == 26

    feasible = envelope.maximum_feasible
    assert feasible.minimum_nominal_recovery_for_sink_closure_mL == pytest.approx(25.90)
    assert feasible.minimum_prime_routed_to_cartridge_mL == pytest.approx(9.00)
    assert feasible.minimum_total_cartridge_routing_for_sink_closure_mL == pytest.approx(34.90)
    assert feasible.cartridge_margin_mL == pytest.approx(.10)
    assert feasible.feasible is True

    blocked = envelope.first_infeasible
    assert blocked.minimum_nominal_recovery_for_sink_closure_mL == pytest.approx(25.94)
    assert blocked.minimum_prime_routed_to_cartridge_mL == pytest.approx(9.36)
    assert blocked.minimum_total_cartridge_routing_for_sink_closure_mL == pytest.approx(35.30)
    assert blocked.cartridge_margin_mL == pytest.approx(-.30)
    assert blocked.feasible is False


def test_joint_envelope_exposes_independent_shared_sink_event_ceiling_headroom():
    envelope = _envelope()

    # At 0.4 mL/prime, the 8% residual route consumes 0.032 mL/event against
    # 6 * 0.4 mL residual allowance. The 2% leakage route consumes 0.008 mL/event
    # against 6 * 0.05 mL leakage allowance. Capacity therefore limits first at
    # event 26, while the hard sink ceilings remain visible at 75 and 37 events.
    assert envelope.maximum_prime_events_before_residual_ceiling == 75
    assert envelope.maximum_prime_events_before_external_leakage_ceiling == 37
    assert envelope.limiting_next_prime_events < envelope.maximum_prime_events_before_external_leakage_ceiling
    assert envelope.limiting_next_prime_events < envelope.maximum_prime_events_before_residual_ceiling


def test_zero_fraction_sink_has_no_finite_event_ceiling():
    envelope = evaluate_reprime_service_envelope(
        build_authority_waste_fluid_budget(),
        cycles=6,
        prime_recovery_ratio_contract=1.0,
        prime_residual_ratio_contract=0.0,
        prime_external_leakage_ratio_contract=0.0,
    )
    assert envelope.maximum_prime_events_before_residual_ceiling is None
    assert envelope.maximum_prime_events_before_external_leakage_ceiling is None


def test_service_envelope_requires_complete_prime_destination_contract():
    budget = build_authority_waste_fluid_budget()
    with pytest.raises(WasteFluidAccountingError):
        evaluate_reprime_service_envelope(
            budget,
            cycles=6,
            prime_recovery_ratio_contract=.80,
            prime_residual_ratio_contract=.08,
            prime_external_leakage_ratio_contract=.02,
        )


def test_service_envelope_rejects_overallocated_prime_contract():
    budget = build_authority_waste_fluid_budget()
    with pytest.raises(WasteFluidAccountingError):
        evaluate_reprime_service_envelope(
            budget,
            cycles=6,
            prime_recovery_ratio_contract=.95,
            prime_residual_ratio_contract=.08,
            prime_external_leakage_ratio_contract=.02,
        )


@pytest.mark.parametrize(
    "recovery,residual,leakage",
    [
        (-.01, .99, .02),
        (1.01, 0.0, -.01),
        (.90, -.01, .11),
        (.90, .11, -.01),
        (math.nan, .08, .02),
        (math.inf, .08, .02),
    ],
)
def test_service_envelope_rejects_nonphysical_destination_ratios(recovery, residual, leakage):
    with pytest.raises(WasteFluidAccountingError):
        evaluate_reprime_service_envelope(
            build_authority_waste_fluid_budget(),
            cycles=6,
            prime_recovery_ratio_contract=recovery,
            prime_residual_ratio_contract=residual,
            prime_external_leakage_ratio_contract=leakage,
        )
