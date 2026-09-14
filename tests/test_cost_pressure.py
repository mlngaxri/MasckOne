"""Where a mechanism spends, against where the user can perceive it."""

from __future__ import annotations

import pytest

from masck_one.cost_pressure import (
    AVOIDABLE_PRESSURE_THRESHOLD,
    EVIDENCE_STATUS,
    CostDriver,
    CostPressureError,
    MechanismCostProfile,
    Perceptibility,
    Verdict,
    aperture_tooling_profiles,
    assess_investment,
)


def _profile(**kw):
    base = dict(
        mechanism_id="X",
        perceptibility=Perceptibility.VISIBLE_SURFACE,
        drivers=(CostDriver.PART_COUNT,),
    )
    base.update(kw)
    return MechanismCostProfile(**base)


# --------------------------------------------------------------------------
# no invented cost
# --------------------------------------------------------------------------

def test_no_currency_is_produced() -> None:
    """A wrong cost is worse than no cost, because it gets carried into decisions."""

    manifest = assess_investment(aperture_tooling_profiles()[0]).manifest()
    assert manifest["evidence_status"] == EVIDENCE_STATUS
    assert "NOT_QUOTED" in manifest["evidence_status"]
    rendered = repr(manifest)
    for symbol in ("$", "£", "€", "USD", "unit_cost", "price"):
        assert symbol not in rendered


def test_pressure_is_ordinal_not_a_quantity() -> None:
    """Drivers are ranked by how hard each is to remove, not priced."""

    assert CostDriver.TOOLING_ACTION.value > CostDriver.TOLERANCE_BURDEN.value
    assert CostDriver.TOLERANCE_BURDEN.value > CostDriver.MATERIAL_CLASS.value
    assert CostDriver.PART_COUNT.value == min(d.value for d in CostDriver)


# --------------------------------------------------------------------------
# the applied finding
# --------------------------------------------------------------------------

def test_zero_draft_apertures_carry_avoidable_cost() -> None:
    """The finding: most of the aperture's cost is deleted by a taper.

    Judging only irreducible pressure reported this as balanced and buried it.
    Avoidable cost is checked first for exactly that reason.
    """

    as_built, _ = aperture_tooling_profiles()
    assessment = assess_investment(as_built)

    assert assessment.verdict is Verdict.AVOIDABLE_COST
    assert as_built.removable_pressure >= AVOIDABLE_PRESSURE_THRESHOLD
    assert CostDriver.TOOLING_ACTION in as_built.removable_by_geometry
    assert "change the geometry" in assessment.reason


def test_tapering_the_cutters_resolves_it() -> None:
    as_built, tapered = aperture_tooling_profiles()
    assert assess_investment(tapered).verdict is Verdict.BALANCED
    assert tapered.pressure < as_built.pressure
    assert tapered.removable_pressure == 0
    # Both are equally perceptible; only the cost changed.
    assert tapered.perceptibility is as_built.perceptibility


def test_apertures_are_the_most_perceptible_class() -> None:
    as_built, _ = aperture_tooling_profiles()
    assert as_built.perceptibility is Perceptibility.SKIN_CONTACT
    assert as_built.perceptibility.value == max(p.value for p in Perceptibility)


# --------------------------------------------------------------------------
# both failure modes
# --------------------------------------------------------------------------

def test_spending_where_nobody_can_perceive_is_flagged() -> None:
    """Do not over-engineer internal invisible mechanisms for prestige."""

    hidden = _profile(
        mechanism_id="HIDDEN_PRELOAD",
        perceptibility=Perceptibility.INTERNAL_INVISIBLE,
        drivers=(CostDriver.TOOLING_ACTION, CostDriver.TOLERANCE_BURDEN, CostDriver.MATERIAL_CLASS),
    )
    assert assess_investment(hidden).verdict is Verdict.OVER_ENGINEERED


def test_skimping_where_everyone_can_perceive_is_flagged() -> None:
    """Invest where the customer perceives or needs the quality."""

    bare = _profile(
        mechanism_id="BARE_SWITCH",
        perceptibility=Perceptibility.HAND_OPERATED,
        drivers=(CostDriver.PART_COUNT,),
    )
    assert assess_investment(bare).verdict is Verdict.UNDER_INVESTED


def test_the_same_drivers_are_judged_differently_by_perceptibility() -> None:
    """Perceptibility is what makes spending justified or not."""

    drivers = (CostDriver.TOOLING_ACTION, CostDriver.TOLERANCE_BURDEN, CostDriver.MATERIAL_CLASS)
    hidden = assess_investment(_profile(perceptibility=Perceptibility.INTERNAL_INVISIBLE, drivers=drivers))
    touched = assess_investment(_profile(perceptibility=Perceptibility.HAND_OPERATED, drivers=drivers))
    assert hidden.verdict is Verdict.OVER_ENGINEERED
    assert touched.verdict is Verdict.BALANCED


def test_avoidable_cost_outranks_the_other_verdicts() -> None:
    """An architecture a geometry change deletes is not judged on its merits."""

    over = _profile(
        perceptibility=Perceptibility.INTERNAL_INVISIBLE,
        drivers=(CostDriver.TOOLING_ACTION, CostDriver.TOLERANCE_BURDEN),
        removable_by_geometry=(CostDriver.TOOLING_ACTION,),
    )
    assert assess_investment(over).verdict is Verdict.AVOIDABLE_COST


# --------------------------------------------------------------------------
# hostile inputs
# --------------------------------------------------------------------------

def test_cannot_remove_a_driver_the_mechanism_does_not_have() -> None:
    with pytest.raises(CostPressureError, match="does not have"):
        _profile(drivers=(CostDriver.PART_COUNT,), removable_by_geometry=(CostDriver.TOOLING_ACTION,))


@pytest.mark.parametrize("bad", ["", "   ", None, 5])
def test_blank_or_non_text_id_fails_closed(bad) -> None:
    with pytest.raises(CostPressureError):
        _profile(mechanism_id=bad)


def test_non_enum_perceptibility_fails_closed() -> None:
    with pytest.raises(CostPressureError, match="Perceptibility"):
        _profile(perceptibility="SKIN_CONTACT")


def test_non_enum_driver_fails_closed() -> None:
    with pytest.raises(CostPressureError, match="CostDriver"):
        _profile(drivers=("TOOLING_ACTION",))


def test_non_profile_fails_closed() -> None:
    with pytest.raises(CostPressureError):
        assess_investment({"mechanism_id": "X"})


def test_manifest_is_deterministic() -> None:
    a, _ = aperture_tooling_profiles()
    assert assess_investment(a).manifest() == assess_investment(a).manifest()
