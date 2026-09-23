from dataclasses import replace

import pytest

from masck_one.actuation_parameters import ActuationParameterError
from masck_one.treatment_integrated_evidence import (
    build_integrated_treatment_evidence,
    validate_integrated_treatment_evidence,
)
from masck_one.treatment_massage_thermal_evidence import build_treatment_massage_thermal_evidence
from masck_one.treatment_recovery_readiness import screen_treatment_recovery_readiness
from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_overflow_guard import screen_cartridge_overflow_guard
from tests.test_actuation_zone_system_response import _parameters, _sweep


def _readiness():
    budget = build_authority_waste_fluid_budget()
    guard = screen_cartridge_overflow_guard(
        budget,
        prime_events_by_cycle=[0] * budget.service_cycles,
        prime_recovery_ratio_contract=1.0,
    )
    return screen_treatment_recovery_readiness(guard)


def _evidence():
    parameters = _parameters()
    sweep = _sweep(parameters)
    massage_thermal = build_treatment_massage_thermal_evidence(sweep, parameters)
    evidence = build_integrated_treatment_evidence(
        _readiness(), sweep, parameters, massage_thermal
    )
    return parameters, sweep, evidence


def test_accepts_current_recovery_and_measured_actuation_evidence():
    parameters, sweep, evidence = _evidence()
    assert validate_integrated_treatment_evidence(sweep, parameters, evidence) is evidence


def test_rejects_substituted_measured_sweep():
    parameters, sweep, evidence = _evidence()
    changed = replace(sweep.records[0], measurement_id="different-capture")
    other = type(sweep)(parameters=sweep.parameters, records=(changed, *sweep.records[1:]))
    with pytest.raises((ActuationParameterError, ValueError)):
        validate_integrated_treatment_evidence(other, parameters, evidence)


def test_rejects_mutated_nested_recovery_evidence():
    parameters, sweep, evidence = _evidence()
    object.__setattr__(evidence.recovery, "post_recovery_handoff_permitted", False)
    with pytest.raises(WasteFluidAccountingError):
        validate_integrated_treatment_evidence(sweep, parameters, evidence)


def test_rejects_non_capacity_qualified_recovery_evidence():
    parameters = _parameters()
    sweep = _sweep(parameters)
    budget = build_authority_waste_fluid_budget()
    guard = screen_cartridge_overflow_guard(
        budget, prime_events_by_cycle=[0] * budget.service_cycles, prime_recovery_ratio_contract=1.0
    )
    closure_only = screen_treatment_recovery_readiness(guard.routing)
    massage_thermal = build_treatment_massage_thermal_evidence(sweep, parameters)
    with pytest.raises(WasteFluidAccountingError, match="reserve-aware CartridgeOverflowGuard"):
        build_integrated_treatment_evidence(
            closure_only, sweep, parameters, massage_thermal
        )


def test_rejects_wrong_integrated_evidence_type():
    parameters = _parameters()
    with pytest.raises(TypeError, match="exact IntegratedTreatmentEvidence"):
        validate_integrated_treatment_evidence(_sweep(parameters), parameters, object())
