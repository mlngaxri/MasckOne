from dataclasses import replace

import pytest

from masck_one.authority import load_authority
from masck_one.water_reservoir import (
    ORIENTATION_CASE_IDS,
    PORT_IDS,
    WaterReservoirError,
    build_water_reservoir_architecture,
)


def test_water_reservoir_is_authority_bound_and_serviceable_without_false_volume_closure():
    authority = load_authority()
    reservoir = build_water_reservoir_architecture(authority)
    assert reservoir.gross_target_mL == 6.5
    assert reservoir.minimum_usable_mL == 5.5
    assert tuple(port.port_id for port in reservoir.ports) == PORT_IDS
    assert reservoir.orientation_case_ids == ORIENTATION_CASE_IDS
    assert reservoir.cavity_classification == "WET_REMOVABLE"
    assert reservoir.computed_internal_volume_mL is None
    assert reservoir.computed_dead_volume_mL is None
    assert reservoir.physical_validation_eligible is False


def test_digital_volume_evaluation_uses_internal_minus_dead_volume_and_does_not_claim_physical_evidence():
    reservoir = build_water_reservoir_architecture(load_authority())
    evaluation = reservoir.evaluate_generated_volume(internal_volume_mL=6.6, dead_volume_mL=0.9)
    assert evaluation.computed_usable_volume_mL == pytest.approx(5.7)
    assert evaluation.gross_target_met is True
    assert evaluation.minimum_usable_met is True
    assert evaluation.evidence_kind == "DIGITAL_GEOMETRIC_VOLUME_ONLY"


def test_volume_evaluation_reports_failed_usable_target_without_weakening_requirement():
    reservoir = build_water_reservoir_architecture(load_authority())
    evaluation = reservoir.evaluate_generated_volume(internal_volume_mL=6.5, dead_volume_mL=1.2)
    assert evaluation.gross_target_met is True
    assert evaluation.minimum_usable_met is False


def test_architecture_rejects_premature_internal_volume_claim_and_wrong_hygiene_class():
    reservoir = build_water_reservoir_architecture(load_authority())
    with pytest.raises(WaterReservoirError, match="cannot claim closed"):
        replace(reservoir, computed_internal_volume_mL=6.5)
    with pytest.raises(WaterReservoirError, match="requires the reservoir cavity"):
        replace(reservoir, cavity_classification="DRY_ALWAYS")


def test_authority_drift_is_detected_and_leakage_remains_unvalidated():
    authority = load_authority()
    reservoir = build_water_reservoir_architecture(authority)
    stale = replace(reservoir, gross_target_mL=6.4)
    with pytest.raises(WaterReservoirError, match="gross target no longer matches"):
        stale.validate_current_authority(authority)
    assert "UNVALIDATED" in reservoir.leakage_boundary_status or "VALIDATION_GATED" in reservoir.leakage_boundary_status


def test_invalid_volume_inputs_fail_closed():
    reservoir = build_water_reservoir_architecture(load_authority())
    with pytest.raises(WaterReservoirError, match="Dead volume cannot exceed"):
        reservoir.evaluate_generated_volume(internal_volume_mL=1.0, dead_volume_mL=2.0)
    with pytest.raises(WaterReservoirError, match="finite real"):
        reservoir.evaluate_generated_volume(internal_volume_mL=True, dead_volume_mL=0.0)
