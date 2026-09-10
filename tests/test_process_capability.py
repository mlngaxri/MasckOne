"""Can a process actually hold the tolerances the CAD assumes?"""

from __future__ import annotations

import copy
import math

import pytest

from masck_one.authority import Authority, load_authority
from masck_one.process_capability import (
    EVIDENCE_STATUS,
    Feasibility,
    ProcessCapabilityError,
    ProcessClass,
    achievable_tolerance_mm,
    assess_stack,
    required_per_contributor_mm,
    rss_per_contributor_mm,
    seam_feasibility,
)


@pytest.fixture(scope="module")
def authority() -> Authority:
    return load_authority()


# --------------------------------------------------------------------------
# capability model
# --------------------------------------------------------------------------

def test_achievable_tolerance_grows_with_chain_length() -> None:
    """The central fact: tolerance follows the dimension chain, not the part."""

    short = achievable_tolerance_mm(ProcessClass.INJECTION_MOULDED_FILLED, 20.0)
    long = achievable_tolerance_mm(ProcessClass.INJECTION_MOULDED_FILLED, 200.0)
    assert long[0] > short[0] and long[1] > short[1]
    # An order of magnitude of chain costs several times the tolerance.
    assert long[1] / short[1] > 4.0


def test_optimistic_is_always_tighter_than_typical() -> None:
    for process in ProcessClass:
        for length in (10.0, 50.0, 250.0):
            optimistic, typical = achievable_tolerance_mm(process, length)
            assert 0.0 < optimistic < typical


def test_machined_metal_holds_tighter_than_moulding() -> None:
    metal = achievable_tolerance_mm(ProcessClass.MACHINED_METAL, 50.0)
    moulded = achievable_tolerance_mm(ProcessClass.INJECTION_MOULDED, 50.0)
    elastomer = achievable_tolerance_mm(ProcessClass.LSR_MOULDED, 50.0)
    assert metal[1] < moulded[1] < elastomer[1]


def test_worst_case_divides_the_budget_evenly() -> None:
    assert math.isclose(required_per_contributor_mm(0.15, 3), 0.05, rel_tol=1e-12)


def test_removing_a_contributor_buys_more_than_tightening_the_rest() -> None:
    """Why shortening a chain beats tightening a process."""

    three = required_per_contributor_mm(0.15, 3)
    two = required_per_contributor_mm(0.15, 2)
    assert two / three == pytest.approx(1.5)


def test_rss_is_computed_but_refused(authority) -> None:
    """RSS needs supplier Cp/Cpk that does not exist for this programme."""

    assert rss_per_contributor_mm(0.15, 4) > required_per_contributor_mm(0.15, 4)
    stack = seam_feasibility(authority)
    assert stack.rss_is_usable is False
    assert "Cp/Cpk" in stack.manifest()["rss_refusal_reason"]


# --------------------------------------------------------------------------
# feasibility grading
# --------------------------------------------------------------------------

def test_feasibility_grades_span_the_capability_band() -> None:
    common = dict(
        process=ProcessClass.INJECTION_MOULDED_FILLED,
        chain_length_mm=20.0,
        contributor_count=2,
    )
    optimistic, typical = achievable_tolerance_mm(ProcessClass.INJECTION_MOULDED_FILLED, 20.0)

    generous = assess_stack("A", total_budget_mm=typical * 2 * 1.5, **common)
    between = assess_stack("B", total_budget_mm=(optimistic + typical), **common)
    tight = assess_stack("C", total_budget_mm=optimistic * 2 * 0.5, **common)

    assert generous.feasibility is Feasibility.FEASIBLE
    assert between.feasibility is Feasibility.MARGINAL
    assert tight.feasibility is Feasibility.INFEASIBLE


def test_shortfall_factor_reports_how_far_off_it_is() -> None:
    stack = assess_stack(
        "X",
        process=ProcessClass.INJECTION_MOULDED_FILLED,
        chain_length_mm=200.0,
        contributor_count=3,
        total_budget_mm=0.15,
    )
    assert stack.feasibility is Feasibility.INFEASIBLE
    assert stack.shortfall_factor > 5.0


# --------------------------------------------------------------------------
# the applied seam case
# --------------------------------------------------------------------------

def test_seam_is_infeasible_as_a_butt_joint_to_the_global_outline(authority) -> None:
    """The finding: the seam tolerance cannot be held from the part outline.

    Three contributors over a ~200 mm chain need +/-0.050 mm each. Filled
    moulding holds roughly +/-0.31 mm there -- short by about 6x.
    """

    stack = seam_feasibility(authority, self_locating=False)
    assert stack.feasibility is Feasibility.INFEASIBLE
    assert stack.required_per_contributor_mm == pytest.approx(0.05, rel=1e-9)
    assert stack.shortfall_factor > 5.0


def test_seam_is_feasible_when_it_locates_itself(authority) -> None:
    """Locating the seam to itself removes the frame term and shortens the chain."""

    stack = seam_feasibility(authority, self_locating=True)
    assert stack.feasibility is Feasibility.FEASIBLE
    assert stack.required_per_contributor_mm == pytest.approx(0.075, rel=1e-9)
    # Held even at the pessimistic end of the moulding band.
    assert stack.achievable_typical_mm < stack.required_per_contributor_mm


def test_released_authority_declares_a_feasible_seam_strategy(authority) -> None:
    strategy = authority.get("geometry", "visible_seam", "control_strategy")
    assert strategy == "SELF_LOCATING_LOCAL_DATUM"
    assert seam_feasibility(authority).feasibility is Feasibility.FEASIBLE


# --------------------------------------------------------------------------
# authority gate
# --------------------------------------------------------------------------

def test_authority_rejects_an_unmanufacturable_seam_strategy(authority) -> None:
    from masck_one.authority import _semantic_issues

    assert not _semantic_issues(authority.data)

    data = copy.deepcopy(authority.data)
    data["geometry"]["visible_seam"]["control_strategy"] = "BUTT_JOINT_TO_GLOBAL_OUTLINE"
    issues = [
        i for i in _semantic_issues(data)
        if i.code == "VISIBLE_SEAM_TOLERANCE_NOT_MANUFACTURABLE"
    ]
    assert len(issues) == 1
    assert issues[0].actual["shortfall_factor"] > 5.0


def test_authority_rejects_a_seam_tolerance_tightened_past_capability(authority) -> None:
    """The gate catches the defect from the tolerance side too."""

    from masck_one.authority import _semantic_issues

    data = copy.deepcopy(authority.data)
    data["geometry"]["visible_seam"]["tolerance_mm"] = 0.02
    codes = [i.code for i in _semantic_issues(data)]
    assert "VISIBLE_SEAM_TOLERANCE_NOT_MANUFACTURABLE" in codes


# --------------------------------------------------------------------------
# evidence firewall and hostile inputs
# --------------------------------------------------------------------------

def test_capability_values_are_not_supplier_evidence(authority) -> None:
    manifest = seam_feasibility(authority).manifest()
    assert manifest["evidence_status"] == EVIDENCE_STATUS
    assert "NOT_SUPPLIER" in manifest["evidence_status"]


def test_manifest_is_deterministic(authority) -> None:
    assert seam_feasibility(authority).manifest() == seam_feasibility(authority).manifest()


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
def test_nonpositive_and_nonfinite_inputs_fail_closed(bad) -> None:
    with pytest.raises(ProcessCapabilityError):
        achievable_tolerance_mm(ProcessClass.INJECTION_MOULDED, bad)
    with pytest.raises(ProcessCapabilityError):
        required_per_contributor_mm(bad, 3)


def test_zero_contributors_fails_closed() -> None:
    with pytest.raises(ProcessCapabilityError):
        required_per_contributor_mm(0.15, 0)


def test_non_process_class_fails_closed() -> None:
    with pytest.raises(ProcessCapabilityError):
        achievable_tolerance_mm("INJECTION_MOULDED", 20.0)


def test_empty_stack_id_fails_closed() -> None:
    with pytest.raises(ProcessCapabilityError):
        assess_stack(
            "  ",
            process=ProcessClass.INJECTION_MOULDED,
            chain_length_mm=20.0,
            contributor_count=2,
            total_budget_mm=0.15,
        )
