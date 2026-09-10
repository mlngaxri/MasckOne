"""Whole-product mass, CG and head-load closure tests."""

from __future__ import annotations

import copy
import math

import pytest

from masck_one.authority import Authority, load_authority
from masck_one.mass_balance import (
    STANDARD_GRAVITY_M_S2,
    MassBalanceError,
    MassEntry,
    MassEvidence,
    build_mass_balance_ledger,
    check_limit_closure,
    liquid_charge_entries,
    max_cg_height_mm,
    max_mass_g,
    pitch_torque_nm,
)


@pytest.fixture(scope="module")
def authority() -> Authority:
    return load_authority()


@pytest.fixture(scope="module")
def ledger(authority):
    return build_mass_balance_ledger(authority)


# --------------------------------------------------------------------------
# physics
# --------------------------------------------------------------------------

def test_pitch_torque_matches_closed_form() -> None:
    assert math.isclose(
        pitch_torque_nm(255.0, 30.0), 0.255 * STANDARD_GRAVITY_M_S2 * 0.030, rel_tol=1e-12
    )


def test_torque_is_linear_in_mass_and_arm() -> None:
    base = pitch_torque_nm(100.0, 20.0)
    assert math.isclose(pitch_torque_nm(200.0, 20.0), 2 * base, rel_tol=1e-12)
    assert math.isclose(pitch_torque_nm(100.0, 40.0), 2 * base, rel_tol=1e-12)


def test_cg_and_mass_bounds_invert_the_torque_relation() -> None:
    z = max_cg_height_mm(255.0, 0.070)
    assert math.isclose(pitch_torque_nm(255.0, z), 0.070, rel_tol=1e-12)
    m = max_mass_g(27.9, 0.070)
    assert math.isclose(pitch_torque_nm(m, 27.9), 0.070, rel_tol=1e-12)


# --------------------------------------------------------------------------
# the released limit set
# --------------------------------------------------------------------------

def test_released_limit_set_closes(ledger) -> None:
    """Every allowed (mass, CG) corner must meet the torque limit.

    This failed before cg_z_max_mm was tightened from 30.0 mm: at 255 g the
    worst allowed corner produced 0.0750 N*m against a 0.070 N*m limit.
    """

    assert ledger.limit_set_closes
    for corner in ledger.corners:
        assert corner.closes, (
            f"{corner.corner_id}: {corner.torque_nm:.6f} N*m exceeds "
            f"{corner.torque_limit_nm} N*m"
        )


def test_the_binding_corner_is_the_loaded_one(ledger) -> None:
    """Loaded, not dry, is the worn condition that sizes the CG limit."""

    by_id = {c.corner_id: c for c in ledger.corners}
    assert by_id["loaded_max"].margin_fraction < by_id["dry_max"].margin_fraction
    assert math.isclose(
        ledger.cg_bound_from_torque_at_loaded_mm,
        max_cg_height_mm(ledger.loaded_limit_g, ledger.torque_limit_nm),
        rel_tol=1e-12,
    )


def test_cg_limit_respects_the_torque_derived_bound(ledger) -> None:
    assert ledger.cg_limit_mm <= ledger.cg_bound_from_torque_at_loaded_mm


def test_the_previous_cg_limit_is_detected_as_non_closing() -> None:
    """Guard against silently regressing to the unsatisfiable value."""

    corners, closes = check_limit_closure(215.0, 255.0, 30.0, 0.070)
    assert not closes
    by_id = {c.corner_id: c for c in corners}
    assert by_id["dry_max"].closes
    assert not by_id["loaded_max"].closes
    assert math.isclose(by_id["loaded_max"].torque_nm, 0.07502087, rel_tol=1e-6)


def test_cg_carries_more_leverage_per_unit_than_mass(ledger) -> None:
    """Why CG was the variable that moved, not the mass budget."""

    # 1 mm of anterior CG costs far more torque than 1 g of mass does.
    assert ledger.torque_per_mm_nm > 5.0 * ledger.torque_per_gram_nm


# --------------------------------------------------------------------------
# mass evidence firewall
# --------------------------------------------------------------------------

def test_unresolved_entry_cannot_assert_a_mass() -> None:
    with pytest.raises(MassBalanceError, match="cannot also assert a mass"):
        MassEntry("frame", 120.0, 10.0, MassEvidence.UNRESOLVED)


def test_envelope_bound_is_not_established_mass() -> None:
    """An envelope bounds a volume; it does not establish what is inside it."""

    entry = MassEntry("shell_envelope", 90.0, 12.0, MassEvidence.ENVELOPE_UPPER_BOUND)
    assert not entry.is_established


@pytest.mark.parametrize(
    "evidence",
    [
        MassEvidence.MEASURED,
        MassEvidence.SUPPLIER_DATASHEET,
        MassEvidence.MATERIAL_AND_REALIZED_VOLUME,
        MassEvidence.DERIVED_FROM_AUTHORITY,
    ],
)
def test_established_evidence_classes_count(evidence) -> None:
    assert MassEntry("x", 10.0, 5.0, evidence).is_established


def test_incomplete_ledger_reports_a_lower_bound_not_product_mass(authority) -> None:
    entries = liquid_charge_entries(authority) + (
        MassEntry("structural_frame", 0.0, 0.0, MassEvidence.UNRESOLVED),
        MassEntry("shell", 85.0, 14.0, MassEvidence.ENVELOPE_UPPER_BOUND),
    )
    ledger = build_mass_balance_ledger(authority, entries)

    assert not ledger.is_complete
    assert "structural_frame" in ledger.unresolved_items
    assert "shell" in ledger.unresolved_items
    assert "LOWER_BOUND" in ledger.manifest()["evidence_status"]
    # The envelope entry must not be silently folded into the established mass.
    assert ledger.established_mass_g < 85.0


def test_ledger_cg_uses_only_established_entries(authority) -> None:
    entries = (
        MassEntry("a", 10.0, 10.0, MassEvidence.MEASURED),
        MassEntry("b", 10.0, 30.0, MassEvidence.MEASURED),
        MassEntry("c", 100.0, 500.0, MassEvidence.ENVELOPE_UPPER_BOUND),
    )
    ledger = build_mass_balance_ledger(authority, entries)
    assert math.isclose(ledger.cg_z_mm(), 20.0, rel_tol=1e-12)


def test_ledger_with_no_established_entries_has_no_cg(authority) -> None:
    entries = (MassEntry("only", 0.0, 0.0, MassEvidence.UNRESOLVED),)
    assert build_mass_balance_ledger(authority, entries).cg_z_mm() is None


# --------------------------------------------------------------------------
# liquid charges
# --------------------------------------------------------------------------

def test_liquid_charges_are_derived_from_the_authority(authority) -> None:
    charges = {e.item_id: e for e in liquid_charge_entries(authority)}
    water = authority.number("fluid", "water_reservoir", "gross_mL")

    assert charges["charge_water"].evidence is MassEvidence.DERIVED_FROM_AUTHORITY
    assert math.isclose(charges["charge_water"].mass_g, water * 0.997, rel_tol=1e-9)
    # Cleanser density is a formulation property; the assumption must be stated.
    assert "unresolved" in charges["charge_cleanser"].note.lower()


def test_liquid_charge_fits_inside_the_dry_to_loaded_allowance(ledger, authority) -> None:
    """Loaded minus dry must at least cover the fluid the product carries."""

    allowance = ledger.loaded_limit_g - ledger.dry_limit_g
    charge = sum(e.mass_g for e in liquid_charge_entries(authority))
    assert charge < allowance


# --------------------------------------------------------------------------
# authority gate
# --------------------------------------------------------------------------

def test_authority_rejects_a_non_closing_limit_set(authority) -> None:
    from masck_one.authority import _semantic_issues

    assert not _semantic_issues(authority.data)

    data = copy.deepcopy(authority.data)
    data["mass"]["cg_z_max_mm"] = 30.0
    issues = [
        i for i in _semantic_issues(data)
        if i.code == "MASS_BALANCE_LIMIT_SET_DOES_NOT_CLOSE"
    ]
    assert len(issues) == 1
    assert issues[0].actual["corner"] == "loaded_absolute_max_g"
    assert math.isclose(issues[0].expected["max_cg_z_mm_at_this_mass"], 27.9922, rel_tol=1e-4)


def test_authority_also_rejects_a_mass_increase_that_breaks_closure(authority) -> None:
    """The gate must catch the defect from either side."""

    from masck_one.authority import _semantic_issues

    data = copy.deepcopy(authority.data)
    data["mass"]["loaded_absolute_max_g"] = 300.0
    codes = [i.code for i in _semantic_issues(data)]
    assert "MASS_BALANCE_LIMIT_SET_DOES_NOT_CLOSE" in codes


def test_ledger_and_authority_gate_agree(authority) -> None:
    from masck_one.authority import _semantic_issues

    for cg, expected_closes in ((27.9, True), (30.0, False)):
        data = copy.deepcopy(authority.data)
        data["mass"]["cg_z_max_mm"] = cg
        led = build_mass_balance_ledger(
            Authority(data, authority.source, authority.validation_report)
        )
        flagged = any(
            i.code == "MASS_BALANCE_LIMIT_SET_DOES_NOT_CLOSE" for i in _semantic_issues(data)
        )
        assert led.limit_set_closes is expected_closes
        assert flagged is (not expected_closes)


def test_manifest_disclaims_as_built_mass(ledger) -> None:
    disclaimed = " ".join(ledger.manifest()["not_evidence_of"]).lower()
    for topic in ("as-built product mass", "measured centre of gravity", "comfort"):
        assert topic in disclaimed


def test_manifest_is_deterministic(authority) -> None:
    assert build_mass_balance_ledger(authority).manifest() == build_mass_balance_ledger(
        authority
    ).manifest()


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0])
def test_nonfinite_and_negative_masses_fail_closed(bad) -> None:
    with pytest.raises(MassBalanceError):
        MassEntry("x", bad, 0.0, MassEvidence.MEASURED)


def test_zero_mass_cannot_produce_a_cg_bound() -> None:
    with pytest.raises(MassBalanceError):
        max_cg_height_mm(0.0, 0.070)


def test_zero_cg_cannot_produce_a_mass_bound() -> None:
    with pytest.raises(MassBalanceError):
        max_mass_g(0.0, 0.070)


# --------------------------------------------------------------------------
# coverage requirement
# --------------------------------------------------------------------------

def test_default_ledger_is_honest_about_what_it_does_not_cover(ledger) -> None:
    """The liquid charge alone must never read as a complete product mass.

    Before the coverage requirement the default ledger contained two fluid
    entries, found nothing unresolved among them, and reported COMPLETE_LEDGER
    for 7 g of a 215 g product.
    """

    from masck_one.mass_balance import REQUIRED_MASS_COVERAGE

    assert not ledger.is_complete
    assert "LOWER_BOUND" in ledger.manifest()["evidence_status"]
    assert ledger.established_mass_g < 0.1 * ledger.dry_limit_g
    # Every required subsystem is present in the ledger, resolved or not.
    assert {e.item_id for e in ledger.entries} >= set(REQUIRED_MASS_COVERAGE)


def test_uncovered_subsystems_are_materialised_not_omitted(ledger) -> None:
    for name in ("structural_frame", "rigid_shell", "battery", "retention_system"):
        assert name in ledger.unresolved_items


def test_ledger_becomes_complete_only_when_every_subsystem_is_evidenced(authority) -> None:
    from masck_one.mass_balance import REQUIRED_MASS_COVERAGE

    entries = tuple(
        MassEntry(item_id, 5.0, 10.0, MassEvidence.MEASURED)
        for item_id in REQUIRED_MASS_COVERAGE
    )
    complete = build_mass_balance_ledger(authority, entries)
    assert complete.is_complete
    assert complete.manifest()["evidence_status"] == "COMPLETE_LEDGER"

    # Drop one and it must fall back to a lower bound.
    partial = build_mass_balance_ledger(authority, entries[:-1])
    assert not partial.is_complete
