"""Hostile tests for the CS-018 finite access-topology solver.

793 lines of solver, metrology and instrumentation arrived with no tests. The
solver's whole value is that it *refuses* — it has eight distinct ways to reject
a graph and one impossibility witness — and an unexercised refusal is
indistinguishable from an absent one.

So every test here tries to obtain a sequence that should not exist: by leaving
evidence out, by putting a contact where a finished layer is, by sweeping through
applied product, by carrying reaction on reference geometry. Missing evidence in
particular must never read as clear.

Synthetic graphs exercise logic only. Nothing here is registered anatomy,
measured geometry, or evidence that any product reached skin.
"""
from dataclasses import replace

import pytest

from masck_one.facial_interface_topology import (
    Cell, Configuration, Participant, Problem, TopologyError, Transition,
    edge_defects, solve, state_defects, support_trap_witness, validate,
)

EV = "EV-SYNTHETIC"


def problem(**over):
    """A graph that should solve: reach both layers, then release cleanly."""
    base = dict(
        cells=(Cell(id="cheek", required_layers=("clean", "leave_on"), registration="REG-1"),
               Cell(id="eye", required_layers=(), protected=True, registration="REG-2")),
        participants=(Participant(id="frame", source_identity="frame@sha", classification="MATERIAL",
                                  reaction_role=True),),
        configurations=(
            Configuration(id="attached", contacts=(), blocked_access=(), reaction=("frame",),
                          reachable=("cheek",), emergency_independent=True),
            Configuration(id="released", contacts=(), blocked_access=(), reaction=None,
                          reachable=None, emergency_independent=True, detached=True),
        ),
        transitions=(
            Transition(id="release", start="attached", end="released", moving=("frame",),
                       swept_contact_cells=(), protected_common_mm3=0.0,
                       reaction_during=("frame",), continuous_evidence=EV, group="g1",
                       normal_release=True, standoff_evidence=EV),
        ),
        initial="attached",
        support_certificates
        =((("frame",), EV),),
    )
    base.update(over)
    return Problem(**base)


def edit(p, tid, **over):
    return replace(p, transitions=tuple(
        replace(t, **over) if t.id == tid else t for t in p.transitions))


def state(p, sid, **over):
    return replace(p, configurations=tuple(
        replace(s, **over) if s.id == sid else s for s in p.configurations))


# ---------------------------------------------------------------------------
# the graph that should solve, and what the answer is allowed to claim
# ---------------------------------------------------------------------------

def test_a_complete_registered_graph_yields_a_sequence():
    out = solve(problem())
    assert out["status"] == "ACCESS_SEQUENCE_EXISTS"
    assert out["path"]


def test_no_result_ever_claims_physical_completion():
    for p in (problem(), problem(cells=(Cell(id="cheek", required_layers=("clean",)),))):
        out = solve(p)
        assert out["physical_complete"] is False
        assert out["human_use_eligible"] is False
        assert "NOT_DEPOSITION_OR_LOAD_CAPACITY" in out["proof"]


def test_the_search_is_deterministic():
    runs = [solve(problem()) for _ in range(3)]
    assert len({r["status"] for r in runs}) == 1
    assert len({str(r.get("path")) for r in runs}) == 1


# ---------------------------------------------------------------------------
# missing evidence is never clear
# ---------------------------------------------------------------------------

def test_an_unregistered_required_cell_blocks_rather_than_solving():
    p = problem(cells=(Cell(id="cheek", required_layers=("clean",), registration=None),))
    out = solve(p)
    assert out["status"] == "BLOCKED_MISSING_REGISTRATION"
    assert out["witness"]["kind"] == "MISSING_SOURCE_EVIDENCE"
    assert out["all_missing_cells"] == ["cheek"]


@pytest.mark.parametrize("field,defect", [
    ("continuous_evidence", "CONTINUOUS_PATH_UNKNOWN"),
    ("swept_contact_cells", "SWEPT_CONTACT_UNKNOWN"),
    ("protected_common_mm3", "PROTECTED_PATH_UNKNOWN"),
])
def test_unknown_transition_evidence_is_a_defect_not_a_pass(field, defect):
    p = edit(problem(), "release", **{field: None})
    assert defect in edge_defects(p, p.transitions[0], frozenset())
    assert solve(p)["status"] == "NO_SEQUENCE_IN_SUPPLIED_GRAPH"


def test_a_state_without_proved_support_cannot_be_used():
    p = state(problem(), "attached", reaction=None)
    assert "SUPPORT_UNPROVED" in state_defects(p, p.configurations[0], frozenset())
    assert solve(p)["status"] == "NO_SEQUENCE_IN_SUPPLIED_GRAPH"


def test_support_during_transfer_must_itself_be_certified():
    p = edit(problem(), "release", reaction_during=None)
    assert "SUPPORT_LOSS_DURING_TRANSFER" in edge_defects(p, p.transitions[0], frozenset())
    assert solve(p)["status"] == "NO_SEQUENCE_IN_SUPPLIED_GRAPH"


# ---------------------------------------------------------------------------
# protected anatomy and applied product
# ---------------------------------------------------------------------------

def test_a_protected_cell_cannot_be_a_treatment_target():
    with pytest.raises(TopologyError):
        validate(problem(cells=(Cell(id="eye", required_layers=("clean",), protected=True),)))


def test_contacting_protected_anatomy_rejects_the_state():
    p = state(problem(), "attached", contacts=(("frame", ("eye",)),))
    assert "PROTECTED_CONTACT" in state_defects(p, p.configurations[0], frozenset())
    assert solve(p)["status"] == "NO_SEQUENCE_IN_SUPPLIED_GRAPH"


def test_a_protected_collision_along_a_transition_rejects_the_edge():
    p = edit(problem(), "release", protected_common_mm3=1.0)
    assert "PROTECTED_COLLISION" in edge_defects(p, p.transitions[0], frozenset())
    assert solve(p)["status"] == "NO_SEQUENCE_IN_SUPPLIED_GRAPH"


def test_a_vanishing_protected_common_is_still_zero_not_negative():
    with pytest.raises(TopologyError):
        validate(edit(problem(), "release", protected_common_mm3=-1e-9))


def test_contact_on_a_finished_cell_is_rejected():
    p = problem()
    assert "CONTACT_AFTER_APPLICATION" in state_defects(
        p, replace(p.configurations[0], contacts=(("frame", ("cheek",)),)), {"cheek"})


def test_sweeping_through_a_finished_cell_is_a_wipe():
    p = edit(problem(), "release", swept_contact_cells=("cheek",))
    assert "WIPE_AFTER_APPLICATION" in edge_defects(p, p.transitions[0], {"cheek"})
    assert solve(p)["status"] == "NO_SEQUENCE_IN_SUPPLIED_GRAPH"


# ---------------------------------------------------------------------------
# release and cross-contamination
# ---------------------------------------------------------------------------

def test_emergency_release_must_stay_independent_in_every_state():
    p = state(problem(), "attached", emergency_independent=None)
    assert "EMERGENCY_NOT_INDEPENDENT" in state_defects(p, p.configurations[0], frozenset())
    assert solve(p)["status"] == "NO_SEQUENCE_IN_SUPPLIED_GRAPH"


def test_normal_release_without_prior_standoff_is_rejected():
    p = edit(problem(), "release", standoff_evidence=None)
    assert "NO_PRIOR_STANDOFF" in edge_defects(p, p.transitions[0], frozenset())
    assert solve(p)["status"] == "NO_SEQUENCE_IN_SUPPLIED_GRAPH"


def test_a_dirty_crossing_needs_a_separation_certificate():
    p = edit(problem(), "release", crosses_dirty=True, separation_evidence=None)
    assert "DIRTY_CLEAN_CROSSING" in edge_defects(p, p.transitions[0], frozenset())
    p2 = edit(problem(), "release", crosses_dirty=True, separation_evidence=EV)
    assert "DIRTY_CLEAN_CROSSING" not in edge_defects(p2, p2.transitions[0], frozenset())


# ---------------------------------------------------------------------------
# source identity and reaction role
# ---------------------------------------------------------------------------

def test_reference_geometry_cannot_carry_reaction():
    with pytest.raises(TopologyError):
        validate(problem(participants=(Participant(id="frame", source_identity="s",
                                                   classification="REFERENCE", reaction_role=True),)))


def test_every_participant_needs_a_source_identity():
    with pytest.raises(TopologyError):
        validate(problem(participants=(Participant(id="frame", source_identity="",
                                                   classification="MATERIAL", reaction_role=True),)))


def test_a_support_certificate_needs_a_reaction_participant_and_evidence():
    with pytest.raises(TopologyError):
        validate(problem(support_certificates=((("frame",), ""),)))
    with pytest.raises(TopologyError):
        validate(problem(support_certificates=(((), EV),)))


def test_duplicate_identities_are_refused():
    p = problem()
    with pytest.raises(TopologyError):
        validate(replace(p, cells=p.cells + (p.cells[0],)))


def test_contacts_must_name_known_participants_and_cells():
    with pytest.raises(TopologyError):
        validate(state(problem(), "attached", contacts=(("ghost", ("cheek",)),)))
    with pytest.raises(TopologyError):
        validate(state(problem(), "attached", contacts=(("frame", ("ghost",)),)))


# ---------------------------------------------------------------------------
# the impossibility witness
# ---------------------------------------------------------------------------

def test_a_support_trap_produces_a_minimum_cardinality_witness():
    """Every usable supported state contacts the one cell that needs the last layer."""
    p = problem(configurations=(
        Configuration(id="attached", contacts=(("frame", ("cheek",)),), blocked_access=(),
                      reaction=("frame",), reachable=("cheek",), emergency_independent=True),
        Configuration(id="released", contacts=(), blocked_access=(), reaction=None,
                      reachable=None, emergency_independent=True, detached=True),
    ))
    out = solve(p)
    assert out["status"] == "NO_SEQUENCE_IN_SUPPLIED_GRAPH"
    w = out["witness"]
    assert w["kind"] == "SUPPORT_CONTACT_TRAP"
    assert w["cells"] == ["cheek"]
    assert w["participants"] == ["frame"]
    assert w["minimality"] == "MINIMUM_CARDINALITY_CELL_TRANSVERSAL"
    assert "next_capability" in w


def test_the_witness_declines_to_claim_minimality_it_did_not_compute():
    p = problem()
    p = state(p, "attached", reaction=None)
    w = support_trap_witness(p)
    assert w["minimality"] == "NOT_CLAIMED"
    assert w["kind"] == "EDGE_OR_SOURCE_CONSTRAINT"


def test_rejected_edges_are_reported_with_their_reasons():
    p = edit(problem(), "release", continuous_evidence=None)
    out = solve(p)
    assert "CONTINUOUS_PATH_UNKNOWN" in out["rejected_edges"]["release"]


# ---------------------------------------------------------------------------
# ordering
# ---------------------------------------------------------------------------

def test_a_later_layer_cannot_start_while_an_earlier_one_is_owed_elsewhere():
    """The global stage barrier: no leave-on anywhere while a clean is outstanding."""
    p = problem(
        cells=(Cell(id="a", required_layers=("clean", "leave_on"), registration="R"),
               Cell(id="b", required_layers=("clean", "leave_on"), registration="R")),
        configurations=(
            Configuration(id="attached", contacts=(), blocked_access=(), reaction=("frame",),
                          reachable=("a", "b"), emergency_independent=True),
            Configuration(id="released", contacts=(), blocked_access=(), reaction=None,
                          reachable=None, emergency_independent=True, detached=True),
        ))
    out = solve(p)
    assert out["status"] == "ACCESS_SEQUENCE_EXISTS"
    steps = [s for s in out["path"] if "access" in s]
    first = steps[0]["access"]
    assert sorted(first) == ["a:clean", "b:clean"], first


def test_an_occluded_cell_is_not_reachable():
    p = problem(configurations=(
        Configuration(id="attached", contacts=(), blocked_access=(("frame", ("cheek",)),),
                      reaction=("frame",), reachable=("cheek",), emergency_independent=True),
        Configuration(id="released", contacts=(), blocked_access=(), reaction=None,
                      reachable=None, emergency_independent=True, detached=True),
    ))
    assert solve(p)["status"] == "NO_SEQUENCE_IN_SUPPLIED_GRAPH"


def test_the_node_bound_is_reported_rather_than_searched_forever():
    out = solve(problem(), max_nodes=1)
    assert out["status"] in ("INCONCLUSIVE_SEARCH_LIMIT", "ACCESS_SEQUENCE_EXISTS")
