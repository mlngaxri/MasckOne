from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import build_authority_waste_fluid_budget
from masck_one.waste_fluid_capacity_failure_diagnostic import (
    CapacityFailureDiagnosticError,
    diagnose_limiting_event_capacity_failure,
)
from masck_one.waste_fluid_limiting_event_capacity import screen_limiting_event_cartridge_capacity


def _screen(recovery: float, residual: float, leakage: float):
    budget = build_authority_waste_fluid_budget()
    return screen_limiting_event_cartridge_capacity(
        budget,
        cycles=budget.service_cycles,
        prime_recovery_ratio_contract=recovery,
        prime_residual_ratio_contract=residual,
        prime_external_leakage_ratio_contract=leakage,
    )


def test_authority_case_attributes_capacity_failure_to_reprime_load():
    diagnostic = diagnose_limiting_event_capacity_failure(_screen(.90, .08, .02))
    assert diagnostic.authority_floor_source == "REPRIME_LOAD"
    assert diagnostic.maximum_recovery_source == "REPRIME_LOAD"
    assert diagnostic.authority_to_maximum_transition_source == "ALREADY_FAILED_AT_AUTHORITY_FLOOR"
    assert diagnostic.authority_floor_overflow_mL > 0.0
    assert diagnostic.maximum_recovery_overflow_mL > 0.0
    assert diagnostic.maximum_recovery_overflow_mL == pytest.approx(
        diagnostic.authority_floor_overflow_mL + diagnostic.recovery_uplift_incremental_overflow_mL
    )


def test_sink_limited_case_reports_no_capacity_failure_source():
    diagnostic = diagnose_limiting_event_capacity_failure(_screen(0.0, 1.0, 0.0))
    assert diagnostic.authority_floor_source == "NONE"
    assert diagnostic.maximum_recovery_source == "NONE"
    assert diagnostic.authority_to_maximum_transition_source == "NONE"
    assert diagnostic.authority_floor_overflow_mL == pytest.approx(0.0)
    assert diagnostic.maximum_recovery_overflow_mL == pytest.approx(0.0)
    assert diagnostic.recovery_uplift_incremental_overflow_mL == pytest.approx(0.0)


def test_recovery_uplift_crossing_is_distinct_from_authority_floor_failure():
    budget = replace(
        build_authority_waste_fluid_budget(),
        cartridge_retained_capacity_requirement_mL=26.0,
    )
    screen = screen_limiting_event_cartridge_capacity(
        budget,
        cycles=budget.service_cycles,
        prime_recovery_ratio_contract=0.0,
        prime_residual_ratio_contract=1.0,
        prime_external_leakage_ratio_contract=0.0,
    )
    diagnostic = diagnose_limiting_event_capacity_failure(screen)
    assert diagnostic.authority_floor_source == "NONE"
    assert diagnostic.maximum_recovery_source == "NOMINAL_LOAD"
    assert diagnostic.authority_to_maximum_transition_source == "NOMINAL_RECOVERY_UPLIFT"
    assert diagnostic.authority_floor_overflow_mL == pytest.approx(0.0)
    assert diagnostic.recovery_uplift_incremental_overflow_mL == pytest.approx(1.6)
    assert diagnostic.maximum_recovery_overflow_mL == pytest.approx(1.6)


def test_diagnostic_rejects_total_failure_without_a_failure_source():
    screen = _screen(0.0, 1.0, 0.0)
    corrupted = replace(screen, authority_floor_cartridge_capacity_exceeded=True)
    with pytest.raises(CapacityFailureDiagnosticError, match="does not match total capacity state"):
        diagnose_limiting_event_capacity_failure(corrupted)


def test_diagnostic_rejects_mutually_exclusive_source_violation():
    screen = _screen(.90, .08, .02)
    corrupted = replace(screen, authority_floor_nominal_capacity_exceeded=True)
    with pytest.raises(CapacityFailureDiagnosticError, match="must be mutually exclusive"):
        diagnose_limiting_event_capacity_failure(corrupted)


def test_diagnostic_rejects_failure_source_without_overflow():
    screen = _screen(.90, .08, .02)
    corrupted = replace(screen, authority_floor_cartridge_overflow_mL=0.0)
    with pytest.raises(CapacityFailureDiagnosticError, match="disagrees with overflow"):
        diagnose_limiting_event_capacity_failure(corrupted)


def test_diagnostic_rejects_nonconserving_recovery_uplift_overflow():
    screen = _screen(.90, .08, .02)
    corrupted = replace(screen, nominal_recovery_uplift_incremental_overflow_mL=0.0)
    with pytest.raises(CapacityFailureDiagnosticError, match="does not conserve"):
        diagnose_limiting_event_capacity_failure(corrupted)


def test_diagnostic_rejects_wrong_evidence_type():
    with pytest.raises(TypeError, match="LimitingEventCapacityScreen"):
        diagnose_limiting_event_capacity_failure(object())
