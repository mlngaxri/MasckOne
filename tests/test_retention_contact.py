import math
import pytest

from masck_one.retention_contact import (
    ContactReactionInputs, evaluate_contact_reactions, minimum_contact_area_mm2,
)


def test_pitch_couple_materially_increases_both_support_resultants():
    p = ContactReactionInputs(1.25, 0.75, 1.50, 1800.0, 1400.0)
    r = evaluate_contact_reactions(p)
    assert r.crown_resultant_n == pytest.approx(math.hypot(1.25, 1.50))
    assert r.occipital_resultant_n == pytest.approx(math.hypot(0.75, 1.50))
    assert r.crown_resultant_n > p.crown_vertical_n
    assert r.occipital_resultant_n > p.occipital_vertical_n
    assert r.evidence_status == "DIGITAL_SENSITIVITY_ONLY"


def test_nominal_pressure_uses_total_reaction_not_vertical_load_only():
    p = ContactReactionInputs(1.0, 1.0, 2.0, 1000.0, 1000.0)
    r = evaluate_contact_reactions(p)
    assert r.crown_nominal_pressure_kpa == pytest.approx(math.sqrt(5.0))
    assert r.occipital_nominal_pressure_kpa == pytest.approx(math.sqrt(5.0))


def test_larger_contact_area_reduces_nominal_pressure_without_claiming_comfort():
    small = evaluate_contact_reactions(ContactReactionInputs(1.0, 1.0, 1.0, 500.0, 500.0))
    large = evaluate_contact_reactions(ContactReactionInputs(1.0, 1.0, 1.0, 1000.0, 1000.0))
    assert large.crown_nominal_pressure_kpa == pytest.approx(small.crown_nominal_pressure_kpa / 2.0)


def test_minimum_area_is_explicit_sensitivity_not_hidden_pass_fail():
    assert minimum_contact_area_mm2(2.5, 2.0) == pytest.approx(1250.0)
    assert minimum_contact_area_mm2(0.0, 2.0) == 0.0


def test_invalid_contact_geometry_and_nonfinite_inputs_fail_closed():
    with pytest.raises(ValueError):
        evaluate_contact_reactions(ContactReactionInputs(1.0, 1.0, 1.0, 0.0, 1000.0))
    with pytest.raises(ValueError):
        evaluate_contact_reactions(ContactReactionInputs(1.0, -1.0, 1.0, 1000.0, 1000.0))
    with pytest.raises(ValueError):
        evaluate_contact_reactions(ContactReactionInputs(1.0, 1.0, math.inf, 1000.0, 1000.0))
    with pytest.raises(ValueError):
        evaluate_contact_reactions(ContactReactionInputs(True, 1.0, 1.0, 1000.0, 1000.0))
    with pytest.raises(ValueError):
        minimum_contact_area_mm2(1.0, 0.0)
