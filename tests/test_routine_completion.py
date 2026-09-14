"""Executable form of the CS-015 / CS-018 routine-completion predicate."""

from __future__ import annotations

import pytest

from masck_one.routine_completion import (
    EVIDENCE_STATUS,
    FORBIDDEN_COMPLETION_SUBSTITUTES,
    ContactElement,
    ContactState,
    OcclusionResolution,
    RegionState,
    RegionStatus,
    RoutineCompletionError,
    RoutineOutcome,
    RoutinePhase,
    Stage,
    evaluate_routine,
)


def _regions(*pairs):
    return tuple(RegionStatus(rid, state) for rid, state in pairs)


def _all_phases(state):
    return {phase: state for phase in RoutinePhase}


@pytest.fixture
def leave_on_stage():
    return Stage(
        "LEAVE_ON_1",
        RoutinePhase.LEAVE_ON,
        _regions(("upper_cheek_left", RegionState.COMPLETE), ("chin", RegionState.COMPLETE)),
    )


# --------------------------------------------------------------------------
# the predicate
# --------------------------------------------------------------------------

def test_a_fully_satisfied_routine_may_claim_complete(leave_on_stage) -> None:
    assessment = evaluate_routine("R", (leave_on_stage,))
    assert assessment.outcome is RoutineOutcome.COMPLETE
    assert assessment.may_claim_complete
    assert assessment.blockers == ()


@pytest.mark.parametrize(
    "state",
    [RegionState.UNREACHABLE, RegionState.UNSUPPORTED, RegionState.INTERRUPTED, RegionState.UNKNOWN],
)
def test_these_states_block_a_mandatory_stage(state) -> None:
    stage = Stage("CLEAN", RoutinePhase.CLEAN, _regions(("chin", state)))
    assessment = evaluate_routine("R", (stage,))
    assert assessment.outcome is RoutineOutcome.BLOCKED
    assert not assessment.may_claim_complete
    assert assessment.blockers[0].code == f"REGION_{state.value}"


@pytest.mark.parametrize("state", [RegionState.PENDING, RegionState.IN_PROGRESS])
def test_unfinished_regions_are_partial_not_blocked(state) -> None:
    """Not finished yet is a different thing from cannot finish."""

    stage = Stage("CLEAN", RoutinePhase.CLEAN, _regions(("chin", state)))
    assert evaluate_routine("R", (stage,)).outcome is RoutineOutcome.PARTIAL


def test_omitting_an_optional_modality_does_not_invalidate_the_routine(leave_on_stage) -> None:
    optional = Stage(
        "MASSAGE", RoutinePhase.TREAT, _regions(("chin", RegionState.PENDING)), mandatory=False
    )
    assert evaluate_routine("R", (leave_on_stage, optional)).outcome is RoutineOutcome.COMPLETE


def test_a_required_treatment_cannot_be_silently_skipped(leave_on_stage) -> None:
    required = Stage(
        "TREAT", RoutinePhase.TREAT, _regions(("chin", RegionState.PENDING)), mandatory=True
    )
    assert evaluate_routine("R", (leave_on_stage, required)).outcome is not RoutineOutcome.COMPLETE


# --------------------------------------------------------------------------
# exclusion is not a loophole
# --------------------------------------------------------------------------

def test_a_deliberate_versioned_exclusion_satisfies_a_region() -> None:
    stage = Stage(
        "SPF",
        RoutinePhase.LEAVE_ON,
        (RegionStatus(
            "temple_left", RegionState.EXCLUDED_WITH_REASON,
            exclusion_reason="outside the facial-mask coverage claim",
            exclusion_claim_version="claim-v1",
        ),),
    )
    assert evaluate_routine("R", (stage,)).outcome is RoutineOutcome.COMPLETE


def test_a_region_the_hardware_could_not_reach_is_not_an_exclusion() -> None:
    """The distinction the contract calls out explicitly: not a loophole."""

    with pytest.raises(RoutineCompletionError, match="UNREACHABLE, not"):
        RegionStatus(
            "temple_left", RegionState.EXCLUDED_WITH_REASON,
            exclusion_reason="could not reach it",
            exclusion_claim_version="claim-v1",
            excluded_due_to_hardware_limitation=True,
        )


def test_an_exclusion_without_a_reason_fails_closed() -> None:
    with pytest.raises(RoutineCompletionError, match="exclusion_reason"):
        RegionStatus("chin", RegionState.EXCLUDED_WITH_REASON)


def test_an_exclusion_without_a_claim_version_fails_closed() -> None:
    with pytest.raises(RoutineCompletionError, match="exclusion_claim_version"):
        RegionStatus("chin", RegionState.EXCLUDED_WITH_REASON, exclusion_reason="deliberate")


def test_exclusion_metadata_on_a_non_excluded_region_fails_closed() -> None:
    with pytest.raises(RoutineCompletionError, match="only meaningful"):
        RegionStatus("chin", RegionState.COMPLETE, exclusion_reason="stray")


# --------------------------------------------------------------------------
# CS-018 occlusion
# --------------------------------------------------------------------------

def _annulus(phase_state, regions=frozenset({"chin"})):
    states = _all_phases(ContactState.RETRACTED_OR_CLEARED)
    states[RoutinePhase.LEAVE_ON] = phase_state
    return ContactElement("stationary_annulus", states, regions, "stationary treatment ring")


def test_a_shadowed_region_blocks_the_leave_on_stage(leave_on_stage) -> None:
    assessment = evaluate_routine("R", (leave_on_stage,), (_annulus(ContactState.CONTACTING),))
    assert assessment.outcome is RoutineOutcome.BLOCKED
    assert assessment.blockers[0].code == "UNRESOLVED_OCCLUSION"


@pytest.mark.parametrize(
    "state", [ContactState.CONTACTING, ContactState.NEAR_SKIN_NONCONTACT,
              ContactState.TRANSITIONING, ContactState.UNKNOWN],
)
def test_only_cleared_or_absent_counts_as_not_shadowing(state) -> None:
    """NEAR_SKIN_NONCONTACT and TRANSITIONING still shadow; UNKNOWN is not a pass."""

    stage = Stage("LEAVE_ON_1", RoutinePhase.LEAVE_ON, _regions(("chin", RegionState.COMPLETE)))
    assert evaluate_routine("R", (stage,), (_annulus(state),)).outcome is RoutineOutcome.BLOCKED


@pytest.mark.parametrize("route", list(OcclusionResolution))
def test_each_declared_resolution_route_clears_the_block(route) -> None:
    stage = Stage(
        "LEAVE_ON_1", RoutinePhase.LEAVE_ON, _regions(("chin", RegionState.COMPLETE)),
        occlusion_resolutions={"chin": route},
    )
    assessment = evaluate_routine("R", (stage,), (_annulus(ContactState.CONTACTING),))
    assert assessment.outcome is RoutineOutcome.COMPLETE


def test_retracting_one_element_does_not_help_if_another_still_shadows() -> None:
    """The contract's exact warning about the massage islands."""

    stage = Stage("LEAVE_ON_1", RoutinePhase.LEAVE_ON, _regions(("chin", RegionState.COMPLETE)))
    islands = ContactElement(
        "massage_islands", _all_phases(ContactState.RETRACTED_OR_CLEARED),
        frozenset({"chin"}), "retracting treatment islands",
    )
    assessment = evaluate_routine("R", (stage,), (islands, _annulus(ContactState.CONTACTING)))
    assert assessment.outcome is RoutineOutcome.BLOCKED
    assert "stationary_annulus" in assessment.blockers[0].detail


def test_a_structure_that_cannot_shadow_the_region_is_not_a_blocker() -> None:
    stage = Stage("LEAVE_ON_1", RoutinePhase.LEAVE_ON, _regions(("chin", RegionState.COMPLETE)))
    elsewhere = _annulus(ContactState.CONTACTING, frozenset({"forehead_centre"}))
    assert evaluate_routine("R", (stage,), (elsewhere,)).outcome is RoutineOutcome.COMPLETE


def test_every_contact_element_must_declare_every_phase() -> None:
    with pytest.raises(RoutineCompletionError, match="every phase must declare"):
        ContactElement("seal", {RoutinePhase.CLEAN: ContactState.CONTACTING})


# --------------------------------------------------------------------------
# substitutes are refused
# --------------------------------------------------------------------------

@pytest.mark.parametrize("substitute", sorted(FORBIDDEN_COMPLETION_SUBSTITUTES))
def test_no_substitute_can_stand_in_for_region_completion(leave_on_stage, substitute) -> None:
    """These are what a product under schedule pressure reaches for."""

    with pytest.raises(RoutineCompletionError, match="cannot substitute"):
        evaluate_routine("R", (leave_on_stage,), completion_substitutes={substitute: 1})


def test_unrelated_telemetry_is_not_refused(leave_on_stage) -> None:
    """The refusal must be specific, not a blanket ban on passing anything."""

    assessment = evaluate_routine(
        "R", (leave_on_stage,), completion_substitutes={"session_started_at": 0}
    )
    assert assessment.outcome is RoutineOutcome.COMPLETE


# --------------------------------------------------------------------------
# safety ordering
# --------------------------------------------------------------------------

def test_emergency_release_outranks_film_preservation(leave_on_stage) -> None:
    """It may yield INTERRUPTED or PARTIAL; it is never delayed for a cosmetic layer."""

    assessment = evaluate_routine(
        "R", (leave_on_stage,), emergency_release_invoked=True,
        release_preserved_leave_on=False,
    )
    assert assessment.outcome is RoutineOutcome.PARTIAL
    assert not assessment.may_claim_complete
    # The wiped leave-on layer is not held against an emergency release.
    assert not any(b.code == "RELEASE_DID_NOT_PRESERVE_LEAVE_ON" for b in assessment.blockers)


def test_emergency_release_over_a_blocked_routine_is_interrupted() -> None:
    stage = Stage("CLEAN", RoutinePhase.CLEAN, _regions(("chin", RegionState.UNREACHABLE)))
    assessment = evaluate_routine("R", (stage,), emergency_release_invoked=True)
    assert assessment.outcome is RoutineOutcome.INTERRUPTED


def test_normal_release_that_wipes_a_required_region_blocks_completion(leave_on_stage) -> None:
    """Release is part of completion."""

    assessment = evaluate_routine("R", (leave_on_stage,), release_preserved_leave_on=False)
    assert assessment.outcome is not RoutineOutcome.COMPLETE
    assert any(b.code == "RELEASE_DID_NOT_PRESERVE_LEAVE_ON" for b in assessment.blockers)


def test_interrupted_required_settling_blocks_release_ready_status() -> None:
    stage = Stage(
        "SETTLE", RoutinePhase.SETTLE, _regions(("chin", RegionState.COMPLETE)),
        requires_settle=True, settle_completed=False,
    )
    assessment = evaluate_routine("R", (stage,))
    assert any(b.code == "SETTLE_INCOMPLETE" for b in assessment.blockers)


def test_invalid_session_state_blocks_completion(leave_on_stage) -> None:
    assessment = evaluate_routine("R", (leave_on_stage,), session_state_valid=False)
    assert assessment.outcome is RoutineOutcome.BLOCKED


# --------------------------------------------------------------------------
# contract and hostile inputs
# --------------------------------------------------------------------------

def test_assessment_disclaims_physical_treatment_evidence(leave_on_stage) -> None:
    manifest = evaluate_routine("R", (leave_on_stage,)).manifest()
    assert manifest["evidence_status"] == EVIDENCE_STATUS
    disclaimed = " ".join(manifest["not_evidence_of"]).lower()
    for topic in ("cleansing", "spatial film", "spf", "skin outcome"):
        assert topic in disclaimed


def test_manifest_is_deterministic(leave_on_stage) -> None:
    a = evaluate_routine("R", (leave_on_stage,)).manifest()
    b = evaluate_routine("R", (leave_on_stage,)).manifest()
    assert a == b


def test_a_routine_with_no_stages_fails_closed() -> None:
    with pytest.raises(RoutineCompletionError, match="at least one stage"):
        evaluate_routine("R", ())


def test_duplicate_stage_ids_fail_closed(leave_on_stage) -> None:
    with pytest.raises(RoutineCompletionError, match="declared twice"):
        evaluate_routine("R", (leave_on_stage, leave_on_stage))


def test_duplicate_region_in_a_stage_fails_closed() -> None:
    with pytest.raises(RoutineCompletionError, match="declared twice"):
        Stage("CLEAN", RoutinePhase.CLEAN,
              _regions(("chin", RegionState.COMPLETE), ("chin", RegionState.PENDING)))


@pytest.mark.parametrize("bad", ["", "   ", None, 7])
def test_blank_identifiers_fail_closed(bad) -> None:
    with pytest.raises(RoutineCompletionError):
        RegionStatus(bad, RegionState.COMPLETE)
