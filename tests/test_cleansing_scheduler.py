"""Hostile tests for the regional plan compiler.

The question throughout is not whether a good plan compiles. It is whether the
compiler can be made to strand a region silently, treat a finished region again,
or call a partially-covered face complete.

Synthetic records exercise logic only. Nothing here is qualified policy, measured
hardware capability, or evidence that cleansing works.
"""
import pytest

from masck_one.regional_cleansing import Burden, ControlError, Envelope, Region
from masck_one.cleansing_scheduler import (
    Action, BLOCKED_UNQUALIFIED, HARDWARE_UNEXECUTABLE, NO_PLAN_WITHIN_BOUND,
    PLAN_COMPILED, compile_plan, map_footprints,
)

DIGEST = "b" * 64


def envelope(**over):
    base = dict(policy_id="p1", source_digest=DIGEST, family="BASELINE",
                maximum=Burden(contact_s=600, load_Ns=600, tangential_mm=6000,
                               shear_proxy_Nmm=6000, cleanser_ml=60,
                               cleanser_residence_s=600, water_ml=600, passes=60),
                max_force_N=3.0, max_stroke_mm=30.0, min_rinse_ml=1.0, max_sample_gap_s=1.0)
    base.update(over)
    return Envelope(**base)


def regions(spec):
    return {k: Region(region_id=k, cells=frozenset(v)) for k, v in spec.items()}


def act(aid, kind, cells, *, channel="ch0", complexity=1, **inc):
    defaults = dict(contact_s=1, load_Ns=1, tangential_mm=1, cleanser_ml=1, water_ml=1, passes=1)
    if kind != "CLEAN":
        defaults = dict(contact_s=1, load_Ns=1, water_ml=1, passes=1)
    defaults.update(inc)
    return Action(action_id=aid, kind=kind, cells=frozenset(cells),
                  increment=Burden(**defaults), channel_id=channel, complexity=complexity)


def full_kit(cells_by_region, *, channel="ch0"):
    out = []
    for key, cells in cells_by_region.items():
        for kind in ("CLEAN", "RINSE", "RECOVER"):
            out.append(act(f"{kind.lower()}-{key}", kind, cells, channel=channel))
    return out


def test_a_reachable_routine_compiles():
    r = regions({"forehead": ["f1"], "cheek": ["c1"]})
    out = compile_plan(r, full_kit({"forehead": ["f1"], "cheek": ["c1"]}),
                       envelopes={k: envelope() for k in r},
                       session_water_ml=100, session_cleanser_ml=100)
    assert out["outcome"] == PLAN_COMPILED
    assert out["unfinished_regions"] == []
    assert out["human_use_eligible"] is False
    assert len(out["steps"]) == 6


def test_a_shared_footprint_that_cannot_bypass_a_finished_region_is_unexecutable():
    """The failure this module exists for: every action legal, region stranded.

    No ordering saves this one. The cheek needs two cells recovered and each is
    reachable only by an action that also recovers the forehead, so whichever the
    compiler runs first finishes the forehead and makes the other illegal.
    """
    r = regions({"forehead": ["f1"], "cheek": ["c1", "c2"]})
    actions = [act("clean-all", "CLEAN", ["f1", "c1", "c2"]),
               act("rinse-all", "RINSE", ["f1", "c1", "c2"]),
               act("recover-c1w", "RECOVER", ["f1", "c1"]),
               act("recover-wide", "RECOVER", ["f1", "c2"])]
    out = compile_plan(r, actions, envelopes={k: envelope() for k in r},
                       session_water_ml=100, session_cleanser_ml=100)
    assert out["outcome"] == HARDWARE_UNEXECUTABLE
    w = out["witness"]
    assert w["trapped_region"] == "cheek"
    assert w["reason"] == "COMPLETED_REGION_NOT_BYPASSABLE"
    assert w["blocking_regions"] == {"forehead": ["f1"]}
    assert "cheek" in w["minimum_capability_change"]


def test_an_exhausted_region_is_reported_as_exhausted_not_as_unreachable():
    """Hitting a ceiling and being finished are different problems."""
    r = regions({"tight": ["t1"], "cheek": ["c1"]})
    actions = [act("clean-all", "CLEAN", ["t1", "c1"]),
               act("rinse-all", "RINSE", ["t1", "c1"]),
               act("recover-all", "RECOVER", ["t1", "c1"])]
    out = compile_plan(r, actions,
                       envelopes={"tight": envelope(maximum=Burden(contact_s=1, load_Ns=1,
                                                                   water_ml=1, passes=1),
                                                    min_rinse_ml=0.5),
                                  "cheek": envelope()},
                       session_water_ml=100, session_cleanser_ml=100)
    assert out["outcome"] == HARDWARE_UNEXECUTABLE
    assert out["witness"]["reason"] == "EXHAUSTED_REGION_NOT_BYPASSABLE"
    assert out["witness"]["exhausted_regions"] == {"tight": ["t1"]}


def test_the_witness_names_the_exact_coupling_cells():
    r = regions({"a": ["a1", "a2"], "b": ["b1"]})
    actions = full_kit({"a": ["a1", "a2"]})
    actions += [act(f"{k.lower()}-wide", k, ["a2", "b1"]) for k in ("CLEAN", "RINSE", "RECOVER")]
    out = compile_plan(r, actions, envelopes={k: envelope() for k in r},
                       session_water_ml=100, session_cleanser_ml=100)
    assert out["outcome"] == HARDWARE_UNEXECUTABLE
    assert out["witness"]["blocking_regions"] == {"a": ["a2"]}


def test_a_region_no_action_reaches_is_named_not_silently_dropped():
    r = regions({"a": ["a1"], "unreachable": ["u1"]})
    actions = full_kit({"a": ["a1"]}) + [act("noop", "CLEAN", ["a1"])]
    with pytest.raises(ControlError):
        compile_plan(r, actions + [act("bad", "CLEAN", ["ghost"])],
                     envelopes={k: envelope() for k in r},
                     session_water_ml=100, session_cleanser_ml=100)
    out = compile_plan(r, actions, envelopes={k: envelope() for k in r},
                       session_water_ml=100, session_cleanser_ml=100)
    assert out["outcome"] == HARDWARE_UNEXECUTABLE
    assert out["witness"]["trapped_region"] == "unreachable"
    assert out["witness"]["reason"] == "NO_ACTION_REACHES_REGION"


def test_a_footprint_cell_belonging_to_no_region_is_refused():
    """Not knowing what an action touches is missing information, never CLEAR."""
    r = regions({"a": ["a1"]})
    with pytest.raises(ControlError):
        map_footprints([act("wide", "CLEAN", ["a1", "unmapped"])], r)


def test_one_cell_cannot_belong_to_two_regions():
    r = {"a": Region(region_id="a", cells=frozenset({"x"})),
         "b": Region(region_id="b", cells=frozenset({"x"}))}
    with pytest.raises(ControlError):
        map_footprints([act("c", "CLEAN", ["x"])], r)


def test_a_finished_region_is_never_swept_again():
    r = regions({"a": ["a1"], "b": ["b1"]})
    out = compile_plan(r, full_kit({"a": ["a1"], "b": ["b1"]}),
                       envelopes={k: envelope() for k in r},
                       session_water_ml=100, session_cleanser_ml=100)
    assert out["outcome"] == PLAN_COMPILED
    order = [s["action_id"] for s in out["steps"]]
    for key in ("a", "b"):
        finish = max(i for i, a in enumerate(order) if a.endswith("-" + key))
        after = [s for s in out["steps"][finish + 1:] if key in s["regions"]]
        assert not after, f"{key} touched after it finished: {after}"


@pytest.mark.parametrize("missing", ["water", "cleanser", "envelope"])
def test_missing_qualified_input_blocks_rather_than_assuming(missing):
    r = regions({"a": ["a1"]})
    kw = dict(envelopes={"a": envelope()}, session_water_ml=100, session_cleanser_ml=100)
    kw[{"water": "session_water_ml", "cleanser": "session_cleanser_ml"}.get(missing, "envelopes")] = (
        None if missing != "envelope" else {"a": None})
    out = compile_plan(r, full_kit({"a": ["a1"]}), **kw)
    assert out["outcome"] == BLOCKED_UNQUALIFIED
    assert out["steps"] == []
    assert out["evidence_owner"]


def test_an_exhausted_cleanser_budget_stops_the_plan_rather_than_borrowing():
    r = regions({"a": ["a1"], "b": ["b1"]})
    out = compile_plan(r, full_kit({"a": ["a1"], "b": ["b1"]}),
                       envelopes={k: envelope() for k in r},
                       session_water_ml=100, session_cleanser_ml=1)
    assert out["outcome"] != PLAN_COMPILED
    assert out["unfinished_regions"]


def test_a_region_ceiling_is_never_averaged_with_a_neighbour():
    """A tight ceiling on one region must not be paid for out of another's slack."""
    r = regions({"tight": ["t1"], "loose": ["l1"]})
    actions = [act(f"{k.lower()}-both", k, ["t1", "l1"]) for k in ("CLEAN", "RINSE", "RECOVER")]
    out = compile_plan(r, actions,
                       envelopes={"tight": envelope(maximum=Burden(water_ml=0.5, passes=1), min_rinse_ml=0.4),
                                  "loose": envelope()},
                       session_water_ml=100, session_cleanser_ml=100)
    assert out["outcome"] != PLAN_COMPILED
    assert "tight" in out["unfinished_regions"]


def test_completion_requires_every_region_not_an_aggregate():
    r = regions({"a": ["a1"], "b": ["b1"], "c": ["c1"]})
    out = compile_plan(r, full_kit({"a": ["a1"], "b": ["b1"]}),
                       envelopes={k: envelope() for k in r},
                       session_water_ml=100, session_cleanser_ml=100)
    assert out["outcome"] == HARDWARE_UNEXECUTABLE
    assert out["unfinished_regions"] == ["c"]


def test_every_stage_must_complete_not_just_cleaning():
    r = regions({"a": ["a1"]})
    out = compile_plan(r, [act("clean-a", "CLEAN", ["a1"])],
                       envelopes={"a": envelope()},
                       session_water_ml=100, session_cleanser_ml=100)
    assert out["outcome"] == HARDWARE_UNEXECUTABLE
    assert out["remaining_stage"] == {"a": "RINSE"}


def test_partial_cell_coverage_does_not_advance_a_stage():
    r = regions({"a": ["a1", "a2"]})
    actions = [act("clean-half", "CLEAN", ["a1"]), act("rinse-a", "RINSE", ["a1", "a2"]),
               act("recover-a", "RECOVER", ["a1", "a2"])]
    out = compile_plan(r, actions, envelopes={"a": envelope()},
                       session_water_ml=100, session_cleanser_ml=100)
    assert out["outcome"] == HARDWARE_UNEXECUTABLE
    assert out["remaining_stage"] == {"a": "CLEAN"}


def test_the_step_bound_is_reported_rather_than_looping():
    r = regions({"a": [f"a{i}" for i in range(6)]})
    actions = [act(f"clean-{i}", "CLEAN", [f"a{i}"]) for i in range(6)]
    out = compile_plan(r, actions, envelopes={"a": envelope()},
                       session_water_ml=100, session_cleanser_ml=100, max_steps=2)
    assert out["outcome"] == NO_PLAN_WITHIN_BOUND
    assert out["step_bound"] == 2


def test_the_compiler_is_deterministic():
    r = regions({"a": ["a1"], "b": ["b1"]})
    kit = full_kit({"a": ["a1"], "b": ["b1"]})
    runs = [compile_plan(r, list(kit), envelopes={k: envelope() for k in r},
                         session_water_ml=100, session_cleanser_ml=100) for _ in range(3)]
    assert len({tuple(s["action_id"] for s in run["steps"]) for run in runs}) == 1


def test_cleaning_cannot_hide_inside_a_rinse_action():
    with pytest.raises(ControlError):
        Action(action_id="sneaky", kind="RINSE", cells=frozenset({"a1"}),
               increment=Burden(cleanser_ml=1), channel_id="ch0")


def test_duplicate_action_identity_is_refused():
    r = regions({"a": ["a1"]})
    with pytest.raises(ControlError):
        map_footprints([act("dup", "CLEAN", ["a1"]), act("dup", "RINSE", ["a1"])], r)


def test_no_compiled_plan_authorises_human_use():
    r = regions({"a": ["a1"]})
    out = compile_plan(r, full_kit({"a": ["a1"]}), envelopes={"a": envelope()},
                       session_water_ml=100, session_cleanser_ml=100)
    assert out["human_use_eligible"] is False
    assert "not a human-use authorization" in out["interpretation"]
