import pytest

from masck_one.waste_fluid_accounting import build_authority_waste_fluid_budget
from masck_one.waste_fluid_limiting_event_capacity import screen_limiting_event_cartridge_capacity


def _screen(recovery: float, residual: float, leakage: float):
    budget = build_authority_waste_fluid_budget()
    return budget, screen_limiting_event_cartridge_capacity(
        budget,
        cycles=budget.service_cycles,
        prime_recovery_ratio_contract=recovery,
        prime_residual_ratio_contract=residual,
        prime_external_leakage_ratio_contract=leakage,
    )


def test_maximum_recovery_capacity_failure_is_attributed_to_reprime_when_nominal_service_fits():
    budget, screen = _screen(.90, .08, .02)
    assert screen.nominal_only_cartridge_overflow_mL == pytest.approx(0.0)
    assert screen.nominal_capacity_exceeded_at_maximum_recovery is False
    assert screen.prime_incremental_cartridge_overflow_mL > 0.0
    assert screen.capacity_exceeded_by_reprime_at_maximum_recovery is True
    assert screen.cartridge_capacity_exceeded_at_maximum_nominal_recovery is True
    assert screen.cartridge_overflow_at_maximum_nominal_recovery_mL == pytest.approx(
        screen.prime_incremental_cartridge_overflow_mL
    )
    assert screen.nominal_liquid_at_maximum_recovery_mL <= budget.cartridge_retained_capacity_requirement_mL


def test_sink_first_boundary_reports_no_cartridge_failure_source():
    _, screen = _screen(0.0, 1.0, 0.0)
    assert screen.service_envelope.controlling_constraint == "RESIDUAL_CEILING"
    assert screen.nominal_capacity_exceeded_at_maximum_recovery is False
    assert screen.capacity_exceeded_by_reprime_at_maximum_recovery is False
    assert screen.cartridge_capacity_exceeded_at_maximum_nominal_recovery is False
    assert screen.cartridge_overflow_at_maximum_nominal_recovery_mL == pytest.approx(0.0)


def test_maximum_recovery_failure_sources_are_mutually_exclusive():
    _, screen = _screen(1.0, 0.0, 0.0)
    assert not (
        screen.nominal_capacity_exceeded_at_maximum_recovery
        and screen.capacity_exceeded_by_reprime_at_maximum_recovery
    )
    assert screen.cartridge_capacity_exceeded_at_maximum_nominal_recovery == (
        screen.nominal_capacity_exceeded_at_maximum_recovery
        or screen.capacity_exceeded_by_reprime_at_maximum_recovery
    )
