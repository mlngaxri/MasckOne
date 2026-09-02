import math
import pytest

from masck_one.retention_contact_robustness import (
    ContactRobustnessInputs, evaluate_contact_robustness, required_nominal_area_mm2,
)


def test_load_growth_and_area_loss_compound_pressure_demand():
    r = evaluate_contact_robustness(ContactRobustnessInputs(2.0, 0.5, 1000.0, 0.20, 50.0))
    assert r.worst_reaction_n == pytest.approx(2.5)
    assert r.worst_effective_area_mm2 == pytest.approx(750.0)
    assert r.nominal_pressure_kpa == pytest.approx(2.0)
    assert r.worst_pressure_kpa == pytest.approx(10.0 / 3.0)
    assert r.pressure_amplification > 1.0
    assert r.evidence_status == "DIGITAL_SENSITIVITY_ONLY"


def test_zero_uncertainty_reproduces_nominal_pressure():
    r = evaluate_contact_robustness(ContactRobustnessInputs(1.5, 0.0, 750.0, 0.0, 0.0))
    assert r.nominal_pressure_kpa == pytest.approx(2.0)
    assert r.worst_pressure_kpa == pytest.approx(2.0)
    assert r.pressure_amplification == pytest.approx(1.0)


def test_each_uncertainty_term_monotonically_increases_worst_pressure():
    base = evaluate_contact_robustness(ContactRobustnessInputs(2.0, 0.0, 1000.0, 0.0, 0.0))
    load = evaluate_contact_robustness(ContactRobustnessInputs(2.0, 0.5, 1000.0, 0.0, 0.0))
    frac = evaluate_contact_robustness(ContactRobustnessInputs(2.0, 0.0, 1000.0, 0.2, 0.0))
    absolute = evaluate_contact_robustness(ContactRobustnessInputs(2.0, 0.0, 1000.0, 0.0, 100.0))
    assert load.worst_pressure_kpa > base.worst_pressure_kpa
    assert frac.worst_pressure_kpa > base.worst_pressure_kpa
    assert absolute.worst_pressure_kpa > base.worst_pressure_kpa


def test_required_nominal_area_accounts_for_area_loss_and_tolerance():
    area = required_nominal_area_mm2(2.5, 2.0, 0.20, 50.0)
    assert area == pytest.approx((1250.0 + 50.0) / 0.8)


def test_zero_load_has_defined_amplification_and_finite_pressure():
    r = evaluate_contact_robustness(ContactRobustnessInputs(0.0, 0.0, 1000.0, 0.2, 0.0))
    assert r.worst_pressure_kpa == 0.0
    assert r.pressure_amplification == 1.0


def test_invalid_or_collapsed_effective_area_fails_closed():
    with pytest.raises(ValueError):
        evaluate_contact_robustness(ContactRobustnessInputs(1.0, 0.0, 1000.0, 1.0, 0.0))
    with pytest.raises(ValueError):
        evaluate_contact_robustness(ContactRobustnessInputs(1.0, 0.0, 1000.0, 0.9, 100.0))
    with pytest.raises(ValueError):
        evaluate_contact_robustness(ContactRobustnessInputs(1.0, -0.1, 1000.0, 0.0, 0.0))
    with pytest.raises(ValueError):
        evaluate_contact_robustness(ContactRobustnessInputs(1.0, 0.0, math.inf, 0.0, 0.0))
    with pytest.raises(ValueError):
        required_nominal_area_mm2(1.0, 0.0, 0.0)
