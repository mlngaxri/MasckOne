"""Hostile tests for routine, product and prepared-session intelligence.

Every test here is written from the attacker's side. The question is never "does
the happy path work" but "can this system be made to say a step happened when it
did not". The promise being defended is narrow and absolute: when Masck One comes
off, the user should not need to touch their face again to finish that routine.
A device that quietly skips sun protection, doses an unknown product, or trusts a
reservoir somebody refilled has broken that promise while reporting success.

Synthetic records exercise logic only. Nothing here is accepted product evidence.
"""
from copy import deepcopy

import pytest

from masck_one.core_sketch_contracts import CoreSketchError, INVALIDATION_EVENTS
from masck_one.product_lifecycle import (
    APPLICATION_EVIDENCE, FACET_EVIDENCE, REGULATED_APPLICATION_CLASSES,
    REGULATED_APPLICATION_EVIDENCE, RESTRICTED, check_transition, derive_state,
    scope_for, session_product_records, summarise_observations,
)
from masck_one.dock_preparation import (
    DOSE_BLOCKED, DOSE_PREPARED, account_inventory, apply_observed_events, assess_carryover,
    assess_flow_fingerprint, carryover_coverage, derive_session_doses, observe_reservoirs,
    required_carryover_classes,
)
from masck_one.routine_schedule import (
    FORBIDDEN_SPF_SUBSTITUTES, OFFLINE_RESIDENCY_KEYS, assess_offline_execution,
    derive_presented_state, offline_manifest, resolve_session, validate_routine,
)

CONTEXT = "synthetic-lane-context"
APPLICATION_CLASSES = frozenset({"CLEAN", "LEAVE_ON", "MOISTURISE", "FACIAL_SPF"})


def make_product(ident="p", version="1", applications=("MOISTURISE",), actor="BENCH_LAB",
                 context=CONTEXT):
    """A fully qualified product plus the exact evidence that qualified it."""
    evidence = []

    def ids_for(facet, classes, application=None):
        scope = scope_for(context, ident, version, facet, application)
        out = []
        for cls in sorted(classes):
            record = {"id": f"{ident}:{facet}:{application or '-'}:{cls}", "class": cls,
                      "scope": scope, "accepted": True, "result": "PASS"}
            evidence.append(record)
            out.append(record["id"])
        return out

    product = {
        "id": ident,
        "identity": {"status": "RESOLVED", "sku": "SKU-" + ident, "market": "UK",
                     "identity_version": version,
                     "evidence_ids": ids_for("identity", FACET_EVIDENCE["identity"])},
        "behavior": {"state": "CHARACTERISED", "profile_binding": "profile-" + version,
                     "evidence_ids": ids_for("behavior", FACET_EVIDENCE["behavior"])},
        "compatibility": {"state": "PRESERVATION_VERIFIED",
                          "evidence_ids": ids_for("compatibility", FACET_EVIDENCE["compatibility"])},
        "applications": {},
    }
    for application in applications:
        required = (REGULATED_APPLICATION_EVIDENCE if application in REGULATED_APPLICATION_CLASSES
                    else APPLICATION_EVIDENCE)
        product["applications"][application] = {"promoted_by": actor,
            "evidence_ids": ids_for("application", required, application)}
    return product, evidence


def reservoir(**overrides):
    base = dict(slot="a", product="p", sku="SKU-p", market="UK", identity_version="1",
                lot="LOT-1", fill_epoch=0, location="DOCK", readable=True, volume_ml=100.0,
                expires_at_s=10_000.0, contamination_state="VERIFIED_CLEAN", density_g_ml=1.0)
    base.update(overrides)
    return base


def binding(products=("p",)):
    return {"product_bindings": [
        {"id": ident, "sku": "SKU-" + ident, "market": "UK", "identity_version": "1",
         "slot": chr(ord("a") + index)} for index, ident in enumerate(products)]}


def demand(application="MOISTURISE", target=2.0, low=1.0, high=3.0):
    return {"application": application, "target_ml": target, "min_ml": low, "max_ml": high}


def routine(context="AM", kinds=("CLEAN", "RINSE_RECOVER", "MOISTURISE", "FACIAL_SPF"), **over):
    stages = []
    for index, kind in enumerate(kinds):
        stage = {"id": f"s{index}", "kind": kind}
        if kind in APPLICATION_CLASSES:
            stage["product_binding"] = f"p{index}"
        stages.append(stage)
    definition = {"id": "r1", "revision": "1", "contexts": {context: stages}}
    definition.update(over)
    return definition


def eligible(definition, context="AM", drop=()):
    stages = [s["id"] for s in definition["contexts"][context]]
    return {s: "BLOCKED_UNSUPPORTED" if s in drop else "ELIGIBLE_FOR_EXACT_PLAN" for s in stages}


# ---------------------------------------------------------------------------
# product lifecycle: who may promote, and how far
# ---------------------------------------------------------------------------

def test_fully_evidenced_product_reaches_validated():
    product, evidence = make_product()
    state = derive_state(product, evidence, CONTEXT)
    assert state["state"] == "VALIDATED"
    assert state["applications"]["MOISTURISE"]["trust"] == "VALIDATED"
    assert state["model_consistent"]
    assert state["hardware_execution_authorized"] is False


@pytest.mark.parametrize("actor", ["AI", "COMMUNITY", "USER_SELF_REPORT", "RETAILER_LISTING"])
def test_observing_actor_cannot_promote_a_product_it_fully_evidenced(actor):
    """The evidence is complete and correctly scoped. The promoter is not allowed."""
    product, evidence = make_product(actor=actor)
    state = derive_state(product, evidence, CONTEXT)
    assert state["state"] == "CHARACTERISED"
    assert state["applications"]["MOISTURISE"]["trust"] == "UNSUPPORTED"
    assert "PROMOTER_MAY_NOT_VALIDATE" in state["applications"]["MOISTURISE"]["blockers"]


@pytest.mark.parametrize("actor", ["AI", "COMMUNITY"])
def test_unknown_cannot_be_promoted_straight_to_validated(actor):
    verdict = check_transition("UNKNOWN", "VALIDATED", actor)
    assert not verdict["model_consistent"]
    assert actor + ":MAY_NOT_PROMOTE" in verdict["blockers"]
    assert "LIFECYCLE_STAGE_SKIPPED" in verdict["blockers"]


def test_even_a_bench_lab_cannot_skip_a_lifecycle_stage():
    verdict = check_transition("KNOWN", "VALIDATED", "BENCH_LAB")
    assert "LIFECYCLE_STAGE_SKIPPED" in verdict["blockers"]
    assert check_transition("KNOWN", "CHARACTERISED", "BENCH_LAB")["model_consistent"]


@pytest.mark.parametrize("actor", sorted({"AI", "COMMUNITY", "BENCH_LAB", "USER_SELF_REPORT"}))
def test_anyone_may_restrict_a_product_at_any_time(actor):
    """Movement toward refusal is always permitted; that is the safe direction."""
    assert check_transition("VALIDATED", RESTRICTED, actor)["model_consistent"]


def test_restriction_cannot_be_lifted_without_requalification():
    verdict = check_transition(RESTRICTED, "VALIDATED", "BENCH_LAB")
    assert "RESTRICTION_LIFTED_WITHOUT_REQUALIFICATION" in verdict["blockers"]


def test_restricted_product_derives_restricted_whatever_its_evidence_says():
    product, evidence = make_product()
    product["restriction"] = "SUPPLIER_RECALL"
    state = derive_state(product, evidence, CONTEXT)
    assert state["state"] == RESTRICTED
    assert not state["model_consistent"]


def test_no_volume_of_community_reports_promotes_anything():
    summary = summarise_observations([{"actor": "COMMUNITY"}] * 10_000 + [{"actor": "AI"}] * 500)
    assert summary["counts"] == {"COMMUNITY": 10_000, "AI": 500}
    assert summary["promotes_nothing"] is True


def test_qualifying_work_cannot_be_filed_as_a_field_observation():
    with pytest.raises(CoreSketchError):
        summarise_observations([{"actor": "BENCH_LAB"}])


def test_reformulation_demotes_by_moving_every_evidence_scope():
    """Nobody revokes the old evidence. It simply stops covering the new version."""
    product, evidence = make_product(version="1")
    assert derive_state(product, evidence, CONTEXT)["state"] == "VALIDATED"
    product["identity"]["identity_version"] = "2"
    after = derive_state(product, evidence, CONTEXT)
    assert after["state"] == "UNKNOWN"
    assert any("NOT_ESTABLISHED_FOR_2" in b for b in after["blockers"])


def test_flow_fingerprint_cannot_resolve_identity():
    product, evidence = make_product()
    product["identity"]["resolved_by"] = "FLOW_FINGERPRINT"
    state = derive_state(product, evidence, CONTEXT)
    assert state["state"] == "UNKNOWN"
    assert state["facets"]["identity"] is False


def test_pumpable_is_not_validated():
    """Characterised flow says the machine can move it, nothing more."""
    product, evidence = make_product(applications=())
    assert derive_state(product, evidence, CONTEXT)["state"] == "CHARACTERISED"


def test_validation_for_one_application_never_covers_another():
    product, evidence = make_product(applications=("MOISTURISE",))
    product["applications"]["FACIAL_SPF"] = deepcopy(product["applications"]["MOISTURISE"])
    state = derive_state(product, evidence, CONTEXT)
    assert state["applications"]["MOISTURISE"]["trust"] == "VALIDATED"
    assert state["applications"]["FACIAL_SPF"]["trust"] == "UNSUPPORTED"
    assert "APPLICATION_EVIDENCE_MISSING" in state["applications"]["FACIAL_SPF"]["blockers"]


def test_spf_is_not_satisfied_by_ordinary_deposition_evidence():
    """Bench and supplier proof places a film. It does not establish a protection factor."""
    product, evidence = make_product(applications=("FACIAL_SPF",))
    thinned = [e for e in evidence if e["class"] not in {"HUMAN", "REG_CLAIM"}]
    state = derive_state(product, thinned, CONTEXT)
    assert state["applications"]["FACIAL_SPF"]["trust"] == "UNSUPPORTED"
    assert REGULATED_APPLICATION_EVIDENCE > APPLICATION_EVIDENCE


def test_unaccepted_or_failed_evidence_does_not_qualify():
    product, evidence = make_product()
    for record in evidence:
        record["accepted"] = False
    assert derive_state(product, evidence, CONTEXT)["state"] == "UNKNOWN"


# ---------------------------------------------------------------------------
# dock: a reservoir is a physical object somebody can swap
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("change,expected", [
    ({"sku": "SKU-other"}, "PRODUCT_CHANGED"),
    ({"market": "US"}, "PRODUCT_CHANGED"),
    ({"lot": "LOT-2"}, "PRODUCT_CHANGED"),
    ({"fill_epoch": 1}, "PRODUCT_CHANGED"),
    ({"identity_version": "2"}, "REFORMULATION"),
    ({"product": "other"}, "ASSIGNMENT_CHANGED"),
    ({"location": "WEARABLE"}, "HARDWARE_CHANGED"),
    ({"readable": False}, "CHANGEOVER_INCOMPLETE"),
    ({"volume_ml": 140.0}, "PRODUCT_CHANGED"),
    ({"volume_ml": 60.0}, "RESOURCE_CHANGED"),
    ({"volume_ml": None}, "RESOURCE_CHANGED"),
])
def test_the_same_slot_changing_underneath_the_session_is_detected(change, expected):
    observation = observe_reservoirs([reservoir()], [reservoir(**change)])
    assert expected in observation["derived_events"]
    assert observation["preparation_survives"] is False


def test_an_unchanged_dock_invalidates_nothing():
    observation = observe_reservoirs([reservoir()], [reservoir()])
    assert observation["derived_events"] == []
    assert observation["preparation_survives"] is True


def test_every_derived_event_is_one_the_session_model_can_apply():
    observation = observe_reservoirs(
        [reservoir(), reservoir(slot="b", product="q", volume_ml=50.0)],
        [reservoir(sku="SKU-new", identity_version="9", volume_ml=None)])
    assert set(observation["derived_events"]) <= INVALIDATION_EVENTS
    assert observation["derived_events"]


def test_a_swapped_reservoir_bumps_the_epoch_the_readiness_gate_reads():
    session = {"epoch": 4, "invalidations": [], "cached_ready": True}
    applied = apply_observed_events(session, [reservoir()], [reservoir(sku="SKU-other")])
    assert applied["session"]["epoch"] == 5
    assert "PRODUCT_CHANGED" in applied["session"]["invalidations"]
    # A remembered READY cannot survive the thing that invalidated it.
    assert "cached_ready" not in applied["session"]


def test_an_undeclared_top_up_is_a_product_change_not_a_convenience():
    observation = observe_reservoirs([reservoir(volume_ml=20.0)], [reservoir(volume_ml=95.0)])
    assert "PRODUCT_CHANGED" in observation["derived_events"]
    assert any("UNDECLARED_TOP_UP" in b for b in observation["blockers"])


def test_a_declared_refill_is_still_a_product_change():
    observation = observe_reservoirs([reservoir(volume_ml=20.0)],
                                     [reservoir(volume_ml=95.0, fill_epoch=1, lot="LOT-2")])
    assert "PRODUCT_CHANGED" in observation["derived_events"]


def test_moving_a_product_to_another_slot_is_an_assignment_change():
    observation = observe_reservoirs(
        [reservoir(slot="a", product="p")],
        [reservoir(slot="b", product="p")])
    assert "ASSIGNMENT_CHANGED" in observation["derived_events"]


def test_a_reservoir_must_declare_where_it_physically_sits():
    with pytest.raises(CoreSketchError):
        observe_reservoirs([], [reservoir(location="SOMEWHERE")])


# ---------------------------------------------------------------------------
# doses: the place a silent zero would enter
# ---------------------------------------------------------------------------

def test_a_prepared_dose_carries_identity_and_expiry():
    out = derive_session_doses({"p": demand()}, [reservoir()], binding(), now_s=1.0)
    assert out["model_consistent"]
    row = out["doses"][0]
    assert row["state"] == DOSE_PREPARED and row["quantity_ml"] == 2.0
    assert row["dose_id"] and row["preservation"] == "VERIFIED"


def test_a_product_the_dock_does_not_hold_is_blocked_never_zero():
    out = derive_session_doses({"p": demand()}, [], binding(), now_s=1.0)
    row = out["doses"][0]
    assert row["state"] == DOSE_BLOCKED
    assert row["quantity_ml"] is None
    assert "p:PRODUCT_NOT_LOADED" in out["blockers"]
    assert out["wearable_session_product_ml"]["high"] is None


def test_an_uncharacterised_dose_stays_unknown_rather_than_becoming_zero():
    out = derive_session_doses({"p": demand(target=None)}, [reservoir()], binding(), now_s=1.0)
    assert "p:DOSE_UNKNOWN" in out["blockers"]
    assert out["doses"][0]["quantity_ml"] is None
    assert out["wearable_session_product_ml"]["unknowns"] == ["p.dose_ml"]


def test_a_blocked_product_cannot_be_dropped_from_the_manifest():
    """Silently omitting a step is how a partial routine reports as complete."""
    out = derive_session_doses({"p": demand(), "q": demand()},
                               [reservoir()], binding(("p", "q")), now_s=1.0)
    assert out["every_product_accounted"] is True
    assert {row["product_binding"] for row in out["doses"]} == {"p", "q"}
    assert "q:PRODUCT_NOT_LOADED" in out["blockers"]


def test_dose_demands_must_cover_exactly_the_bound_products():
    with pytest.raises(CoreSketchError):
        derive_session_doses({}, [reservoir()], binding(), now_s=1.0)


@pytest.mark.parametrize("change,reason", [
    ({"expires_at_s": 0.5}, "SOURCE_AGE_UNKNOWN_OR_EXPIRED"),
    ({"expires_at_s": None}, "SOURCE_AGE_UNKNOWN_OR_EXPIRED"),
    ({"contamination_state": "UNKNOWN"}, "SOURCE_CLEANLINESS_UNPROVED"),
    ({"readable": False}, "SOURCE_IDENTITY_UNREADABLE"),
    ({"sku": "SKU-other"}, "LOADED_IDENTITY_DOES_NOT_MATCH_BINDING"),
    ({"slot": "z"}, "SLOT_DOES_NOT_MATCH_BINDING"),
    ({"volume_ml": 0.5}, "INSUFFICIENT_VOLUME_FOR_DOSE"),
    ({"volume_ml": None}, "AVAILABLE_VOLUME_UNKNOWN"),
])
def test_a_dose_is_not_prepared_from_a_source_that_cannot_be_vouched_for(change, reason):
    out = derive_session_doses({"p": demand()}, [reservoir(**change)], binding(), now_s=1.0)
    assert "p:" + reason in out["blockers"]
    assert out["doses"][0]["state"] == DOSE_BLOCKED


def test_a_dose_outside_the_profile_window_is_refused():
    out = derive_session_doses({"p": demand(target=9.0)}, [reservoir()], binding(), now_s=1.0)
    assert "p:DOSE_OUTSIDE_PROFILE_WINDOW" in out["blockers"]


# ---------------------------------------------------------------------------
# inventory: the dock is not on the user's head
# ---------------------------------------------------------------------------

def test_dock_bulk_is_never_counted_as_worn_mass():
    out = account_inventory([reservoir(volume_ml=500.0, location="DOCK"),
                             reservoir(slot="b", product="q", volume_ml=4.0, location="WEARABLE")],
                            [{"product_binding": "p", "state": DOSE_PREPARED, "quantity_ml": 2.0}])
    assert out["dock_bulk_mass_g"]["high"] == 500.0
    assert out["wearable_reservoir_mass_g"]["high"] == 4.0
    assert out["dock_bulk_counts_toward_worn_mass"] is False
    assert out["session_product_ml"]["high"] == 2.0


def test_an_unprepared_dose_leaves_session_supply_unresolved():
    out = account_inventory([reservoir(location="WEARABLE")],
                            [{"product_binding": "p", "state": DOSE_BLOCKED, "quantity_ml": None}])
    assert out["session_product_ml"]["high"] is None
    assert "session_product_ml:UNRESOLVED" in out["blockers"]


def test_unknown_density_does_not_silently_become_a_mass():
    out = account_inventory([reservoir(density_g_ml=None)], [])
    assert out["dock_bulk_mass_g"]["high"] is None
    assert "dock_bulk_mass_g:UNRESOLVED" in out["blockers"]


# ---------------------------------------------------------------------------
# carryover: residue of unknown origin
# ---------------------------------------------------------------------------

def bench(node, first, second, context=CONTEXT):
    scope = context + "/carryover/" + node + "/" + first + "/" + second
    return {"id": f"c:{node}:{first}:{second}", "class": "BENCH", "scope": scope,
            "accepted": True, "result": "PASS"}


def test_a_proved_changeover_passes():
    record = {"id": "t1", "node": "manifold", "from_product": "a", "to_product": "b",
              "changeover": "VERIFIED_COMPLETE", "evidence_ids": ["c:manifold:a:b"]}
    assert assess_carryover([record], [bench("manifold", "a", "b")], CONTEXT)["model_consistent"]


@pytest.mark.parametrize("prior", [None, "UNKNOWN"])
def test_residue_of_unknown_origin_is_never_clean(prior):
    """There is no pair to run a carryover test on, so nothing can clear it."""
    record = {"id": "t1", "node": "manifold", "from_product": prior, "to_product": "b",
              "changeover": "VERIFIED_COMPLETE"}
    out = assess_carryover([record], [], CONTEXT)
    assert "manifold:UNKNOWN_RESIDUE_IS_NOT_CLEAN" in out["blockers"]


def test_an_executed_purge_without_a_result_proves_nothing():
    record = {"id": "t1", "node": "manifold", "from_product": "a", "to_product": "b",
              "changeover": "VERIFIED_COMPLETE"}
    out = assess_carryover([record], [], CONTEXT)
    assert "manifold:a->b:CARRYOVER_UNPROVED" in out["blockers"]


def test_a_routine_owes_every_applicable_carryover_investigation():
    kinds = ["CLEAN", "RINSE_RECOVER", "LEAVE_ON", "MOISTURISE", "FACIAL_SPF"]
    required = required_carryover_classes(kinds)
    assert "MOISTURISER_TO_SPF" in required
    out = carryover_coverage(["CLEANSER_TO_RINSE"], kinds)
    assert "MOISTURISER_TO_SPF:CARRYOVER_CLASS_NOT_INVESTIGATED" in out["blockers"]
    assert carryover_coverage(sorted(required), kinds)["model_consistent"]


def test_a_routine_without_spf_does_not_owe_the_spf_carryover_pair():
    assert "MOISTURISER_TO_SPF" not in required_carryover_classes(["CLEAN", "RINSE_RECOVER",
                                                                   "MOISTURISE"])


# ---------------------------------------------------------------------------
# flow fingerprint
# ---------------------------------------------------------------------------

def test_contradicting_flow_stops_preparation_and_asks_the_user():
    out = assess_flow_fingerprint({"viscosity": 100.0}, {"viscosity": 400.0}, 0.2)
    assert out["contradicted"] is True
    assert out["action"] == "REQUEST_PRODUCT_CONFIRMATION"


def test_matching_flow_confirms_nothing():
    out = assess_flow_fingerprint({"viscosity": 100.0}, {"viscosity": 101.0}, 0.2)
    assert out["model_consistent"] and out["contradicted"] is False
    assert out["confirms_identity"] is False
    assert out["action"] == "CONTINUE_WITHOUT_CONCLUSION"


def test_an_unobserved_channel_is_not_agreement():
    out = assess_flow_fingerprint({"viscosity": 100.0}, {"viscosity": None}, 0.2)
    assert "viscosity:FLOW_OBSERVATION_UNKNOWN" in out["blockers"]


# ---------------------------------------------------------------------------
# routine, schedule and sun protection
# ---------------------------------------------------------------------------

def test_a_well_formed_am_routine_validates():
    out = validate_routine(routine())
    assert out["model_consistent"] and out["spf_contexts"] == ["AM"]


def test_sun_protection_is_not_scheduled_in_the_evening():
    out = validate_routine(routine(context="PM"))
    assert "PM:SPF_SCHEDULED_OUTSIDE_MORNING" in out["blockers"]


@pytest.mark.parametrize("substitute", sorted(FORBIDDEN_SPF_SUBSTITUTES))
def test_sun_protection_is_never_satisfied_by_something_else(substitute):
    definition = routine()
    definition["contexts"]["AM"][-1]["satisfied_by"] = substitute
    out = validate_routine(definition)
    assert "AM:s3:FORBIDDEN_SPF_SUBSTITUTE" in out["blockers"]


def test_a_routine_cannot_carry_run_time_substitution_rules():
    with pytest.raises(CoreSketchError):
        validate_routine(routine(substitutions={"FACIAL_SPF": "MOISTURISE"}))


def test_stages_out_of_routine_order_are_refused():
    with pytest.raises(CoreSketchError):
        validate_routine(routine(kinds=("FACIAL_SPF", "CLEAN")))


def test_a_full_session_reports_that_it_completes_the_scheduled_routine():
    definition = routine()
    out = resolve_session(definition, "AM", eligible(definition))
    assert out["completes_scheduled_routine"] is True
    assert out["is_reduced_routine"] is False


def test_a_reduced_session_is_a_different_routine_not_a_finished_one():
    definition = routine()
    full = resolve_session(definition, "AM", eligible(definition))
    reduced = resolve_session(definition, "AM", eligible(definition, drop=("s3",)))
    assert reduced["completes_scheduled_routine"] is False
    assert reduced["is_reduced_routine"] is True
    assert reduced["session_plan_digest"] != full["session_plan_digest"]
    assert "s3:SUN_PROTECTION_DROPPED" in reduced["blockers"]
    assert reduced["sun_protection_scheduled"] is True
    assert reduced["sun_protection_runnable"] is False


def test_eligibility_must_be_declared_for_every_scheduled_stage():
    definition = routine()
    with pytest.raises(CoreSketchError):
        resolve_session(definition, "AM", {"s0": "ELIGIBLE_FOR_EXACT_PLAN"})


# ---------------------------------------------------------------------------
# offline execution
# ---------------------------------------------------------------------------

def resident():
    return {key: {"revision": key + "-1"} for key in OFFLINE_RESIDENCY_KEYS}


def test_a_complete_manifest_runs_from_local_state():
    manifest = offline_manifest(routine(), "AM", resident())
    assert manifest["model_consistent"]
    out = assess_offline_execution(manifest, resident(), network_reachable=False)
    assert out["model_consistent"]


def test_an_unreachable_network_does_not_make_a_prepared_device_unready():
    manifest = offline_manifest(routine(), "AM", resident())
    offline = assess_offline_execution(manifest, resident(), network_reachable=False)
    online = assess_offline_execution(manifest, resident(), network_reachable=True)
    assert offline["blockers"] == online["blockers"] == []
    assert offline["network_considered_in_readiness"] is False


def test_a_reachable_network_does_not_substitute_for_missing_local_state():
    manifest = offline_manifest(routine(), "AM", resident())
    cache = resident()
    cache.pop("dose_windows")
    out = assess_offline_execution(manifest, cache, network_reachable=True)
    assert "dose_windows:NOT_CACHED_LOCALLY" in out["blockers"]


def test_normal_use_may_not_reach_for_the_network_at_run_time():
    manifest = offline_manifest(routine(), "AM", resident())
    cache = resident()
    cache["stage_parameters"] = {"resolved_from": "NETWORK_AT_RUN_TIME"}
    out = assess_offline_execution(manifest, cache, network_reachable=True)
    assert "stage_parameters:NORMAL_USE_DEPENDS_ON_NETWORK" in out["blockers"]


def test_a_stale_local_copy_is_not_the_manifest():
    manifest = offline_manifest(routine(), "AM", resident())
    cache = resident()
    cache["routine_revision"] = {"revision": "stale"}
    out = assess_offline_execution(manifest, cache, network_reachable=False)
    assert "routine_revision:CACHED_COPY_DOES_NOT_MATCH_MANIFEST" in out["blockers"]


# ---------------------------------------------------------------------------
# the six honest states
# ---------------------------------------------------------------------------

def presented(readiness_blockers=(), prepared=True, session_reduced=False, offline_blockers=(),
              **flags):
    definition = routine()
    session = resolve_session(definition, "AM",
        eligible(definition, drop=("s3",) if session_reduced else ()))
    readiness = {"blockers": list(readiness_blockers), "prepared_ready": prepared}
    offline = {"blockers": list(offline_blockers)}
    options = {"preparing": False, "user_action_required": False,
               "reduced_routine_accepted": False}
    options.update(flags)
    return derive_presented_state(readiness, session, offline, **options)


def test_ready_requires_everything_to_be_clear():
    assert presented()["state"] == "READY"


def test_safety_outranks_every_other_presentation():
    out = presented(readiness_blockers=["FAULT_OR_FAULT_STATE_UNKNOWN"], prepared=False,
                    preparing=True, user_action_required=True)
    assert out["state"] == "SAFETY_HOLD"


def test_a_blocked_session_is_not_downgraded_to_needs_attention():
    out = presented(readiness_blockers=["p:DOSE_AGE_UNKNOWN_OR_EXPIRED"], prepared=False,
                    user_action_required=True)
    assert out["state"] == "NOT_READY"


def test_an_accepted_reduced_routine_is_reported_as_partial_not_ready():
    out = presented(prepared=False, session_reduced=True, reduced_routine_accepted=True)
    assert out["state"] == "PARTIAL_ROUTINE_AVAILABLE"
    assert out["completes_scheduled_routine"] is False


def test_an_unaccepted_reduced_routine_does_not_present_as_ready():
    out = presented(prepared=True, session_reduced=True, reduced_routine_accepted=False)
    assert out["state"] == "NOT_READY"


def test_offline_gaps_keep_the_device_out_of_ready():
    out = presented(offline_blockers=["dose_windows:NOT_CACHED_LOCALLY"])
    assert out["state"] == "NOT_READY"


def test_presentation_flags_must_be_explicit():
    definition = routine()
    session = resolve_session(definition, "AM", eligible(definition))
    with pytest.raises(CoreSketchError):
        derive_presented_state({"blockers": [], "prepared_ready": True}, session, {"blockers": []},
            preparing=None, user_action_required=False, reduced_routine_accepted=False)


# ---------------------------------------------------------------------------
# end to end: the records this lane hands the existing readiness gate
# ---------------------------------------------------------------------------

def test_session_product_records_feed_the_readiness_gate():
    product, evidence = make_product()
    out = session_product_records(binding(), [product], evidence, CONTEXT, {"p": "MOISTURISE"})
    assert out["model_consistent"]
    row = out["products"][0]
    assert row["trust"] == "VALIDATED" and row["promoted_by"] == "BENCH_LAB"
    assert row["identity_status"] == "RESOLVED"
    assert row["context_digest"] == out["context_digest"]


def test_a_missing_catalogue_entry_produces_an_unsupported_row_not_a_gap():
    out = session_product_records(binding(), [], [], CONTEXT, {"p": "MOISTURISE"})
    assert "p:PRODUCT_NOT_IN_CATALOGUE" in out["blockers"]
    assert out["products"][0]["trust"] == "UNSUPPORTED"


def test_an_ai_promoted_product_never_reaches_the_readiness_gate_as_validated():
    product, evidence = make_product(actor="AI")
    out = session_product_records(binding(), [product], evidence, CONTEXT, {"p": "MOISTURISE"})
    assert out["products"][0]["trust"] == "UNSUPPORTED"
    assert out["products"][0]["promoted_by"] is None


def test_the_routine_must_say_which_application_each_product_performs():
    product, evidence = make_product()
    with pytest.raises(CoreSketchError):
        session_product_records(binding(), [product], evidence, CONTEXT, {})


def test_a_product_validated_for_moisturising_cannot_serve_the_spf_stage():
    product, evidence = make_product(applications=("MOISTURISE",))
    out = session_product_records(binding(), [product], evidence, CONTEXT, {"p": "FACIAL_SPF"})
    assert "p:FACIAL_SPF:NOT_VALIDATED_FOR_REQUIRED_APPLICATION" in out["blockers"]


def test_a_bound_identity_that_disagrees_with_the_catalogue_is_refused():
    product, evidence = make_product()
    product["identity"]["sku"] = "SKU-different"
    out = session_product_records(binding(), [product], evidence, CONTEXT, {"p": "MOISTURISE"})
    assert "p:BOUND_IDENTITY_DOES_NOT_MATCH_CATALOGUE" in out["blockers"]


def test_no_result_in_this_lane_authorises_hardware():
    product, evidence = make_product()
    results = [
        derive_state(product, evidence, CONTEXT),
        check_transition("KNOWN", "CHARACTERISED", "BENCH_LAB"),
        observe_reservoirs([reservoir()], [reservoir()]),
        derive_session_doses({"p": demand()}, [reservoir()], binding(), now_s=1.0),
        account_inventory([reservoir()], []),
        validate_routine(routine()),
        offline_manifest(routine(), "AM", resident()),
        session_product_records(binding(), [product], evidence, CONTEXT, {"p": "MOISTURISE"}),
    ]
    assert all(r["hardware_execution_authorized"] is False for r in results)


# ---------------------------------------------------------------------------
# integration: the producers in this lane against the gate that consumes them
# ---------------------------------------------------------------------------

def prepared_session(now_s=1.0, reservoirs=None):
    """Build a whole prepared session from this lane's producers.

    Nothing below hand-writes a product row or a dose. Everything the readiness
    gate reads is what ``session_product_records`` and ``derive_session_doses``
    actually emit, so a drift between producer and consumer fails here.
    """
    from pathlib import Path
    from masck_one.core_sketch_contracts import digest, load_manifest

    root = Path(__file__).resolve().parents[1]
    plan = deepcopy(load_manifest(root)["completion"]["example_unresolved_am_plan"])
    plan["scope"] = "REDUCED_REGION_SURROGATE"
    plan["regions"] = [r for r in plan["regions"] if r["id"] == "left_cheek"]
    for stage in plan["stages"]:
        stage["regions"] = {"left_cheek": stage["regions"]["left_cheek"]}
        if "product_binding" in stage:
            stage["product_binding"] = "p"

    bound = binding()
    execution = {"routine_id": "r1", "routine_revision": "1", "schedule_context": "AM:test",
        "stage_ids": [s["id"] for s in plan["stages"]], "plan_digest": digest(plan),
        "product_bindings": bound["product_bindings"], "hardware_revision": "test",
        "profile_revision": "test", "authority_digest": "test-only"}

    product, evidence = make_product()
    produced = session_product_records(execution, [product], evidence, CONTEXT, {"p": "MOISTURISE"})
    doses = derive_session_doses({"p": demand()},
        reservoirs if reservoirs is not None else [reservoir()], execution, now_s=now_s)

    request = {"plan": plan, "binding": execution, "thermal_stage": False,
        "resources": {"water_ml": 1, "waste_free_ml": 1, "usable_energy_Wh": 1},
        "dose_requirements": {"p": {"min_ml": 1.0, "max_ml": 3.0}}}
    current = {"binding": deepcopy(execution), "epoch": 0, "invalidations": [], "faults": [],
        "wear_state": "CONFIRMED_ELIGIBLE",
        "stage_eligibility": {s["id"]: "ELIGIBLE_FOR_EXACT_PLAN" for s in plan["stages"]},
        "local": {k: True for k in ("clock_valid", "profile_cache_verified", "progress_known",
                                    "controller_available")},
        "service": {k: "VERIFIED_COMPLETE" for k in ("cleaning", "changeover", "dry_path_service")},
        "resources": dict(request["resources"]),
        "products": produced["products"], "doses": doses["prepared_doses"]}
    receipt = {"epoch": current["epoch"], "binding_digest": digest(execution),
        "dose_digest": digest(current["doses"]), "request_digest": digest(request),
        "service_digest": digest(current["service"]), "products_digest": digest(current["products"]),
        "resources_digest": digest(current["resources"]),
        "stage_eligibility_digest": digest(current["stage_eligibility"]),
        "service_receipt_id": "svc-1", "prepared_at_s": 0.0, "expires_at_s": 5_000.0,
        "observations_expire_at_s": 5_000.0}
    return request, receipt, current, produced, doses


def test_records_this_lane_produces_satisfy_the_existing_readiness_gate():
    from masck_one.core_sketch_contracts import assess_readiness

    request, receipt, current, produced, doses = prepared_session()
    assert produced["model_consistent"] and doses["model_consistent"]
    verdict = assess_readiness(request, receipt, current, now_s=1.0)
    assert verdict["blockers"] == []
    assert verdict["prepared_ready"] is True and verdict["start_ready"] is True


def test_a_reservoir_swapped_after_preparation_makes_the_gate_refuse():
    """The whole chain: somebody changes the bottle, and READY goes away.

    This is the failure the lane exists to close. Before the dock could derive
    an event, every digest in the prepared session still agreed with itself
    while the fluid behind the slot was a different product entirely.
    """
    from masck_one.core_sketch_contracts import assess_readiness

    request, receipt, current, _, _ = prepared_session()
    assert assess_readiness(request, receipt, current, now_s=1.0)["prepared_ready"] is True

    swapped = apply_observed_events(current, [reservoir()], [reservoir(sku="SKU-impostor")])
    assert "PRODUCT_CHANGED" in swapped["observation"]["derived_events"]

    verdict = assess_readiness(request, receipt, swapped["session"], now_s=1.0)
    assert verdict["prepared_ready"] is False
    assert "PREPARATION_INVALIDATED" in verdict["blockers"]


def test_an_ai_promoted_product_cannot_produce_a_ready_session():
    from masck_one.core_sketch_contracts import assess_readiness, digest

    request, receipt, current, _, _ = prepared_session()
    product, evidence = make_product(actor="AI")
    current["products"] = session_product_records(current["binding"], [product], evidence,
        CONTEXT, {"p": "MOISTURISE"})["products"]
    receipt["products_digest"] = digest(current["products"])
    verdict = assess_readiness(request, receipt, current, now_s=1.0)
    assert verdict["prepared_ready"] is False
    assert "p:PRODUCT_OR_PROFILE_UNSUPPORTED" in verdict["blockers"]


def test_a_blocked_dose_cannot_produce_a_ready_session():
    from masck_one.core_sketch_contracts import assess_readiness

    request, receipt, current, _, doses = prepared_session(reservoirs=[])
    assert doses["doses"][0]["state"] == DOSE_BLOCKED
    assert doses["blocked_product_bindings"] == ["p"]
    # The manifest still carries the product; the session carries no dose for it.
    assert doses["prepared_doses"] == [] and current["doses"] == []
    verdict = assess_readiness(request, receipt, current, now_s=1.0)
    assert verdict["prepared_ready"] is False
    assert "PREPARED_PRODUCT_SET_MISMATCH" in verdict["blockers"]


def test_the_manifest_keeps_a_blocked_product_even_though_the_session_cannot():
    """Both properties at once: nothing is hidden, and nothing unprepared ships."""
    out = derive_session_doses({"p": demand(), "q": demand()}, [reservoir()],
                               binding(("p", "q")), now_s=1.0)
    assert {row["product_binding"] for row in out["doses"]} == {"p", "q"}
    assert [row["product_binding"] for row in out["prepared_doses"]] == ["p"]
    assert out["blocked_product_bindings"] == ["q"]


# ---------------------------------------------------------------------------
# S0/S1/S2: what this lane hands the whole-session resource ledger
# ---------------------------------------------------------------------------

def test_prepared_doses_become_resource_ledger_rows():
    from masck_one.dock_preparation import resource_scenario_products

    doses = derive_session_doses({"p": demand()}, [reservoir()], binding(), now_s=1.0)
    out = resource_scenario_products(doses, [reservoir()])
    assert out["model_consistent"]
    assert out["products"] == [{"id": "p", "role": "MOISTURISE", "dose_ml": [2.0, 2.0],
                               "density_g_ml": [1.0, 1.0]}]


def test_a_blocked_dose_keeps_the_whole_session_ledger_unresolved():
    """The end of the chain: an unpreparable product cannot shrink the session.

    core_sketch_resources.read turns dose_ml None into a bound that names its
    own unknown, and Bound arithmetic carries that unknown through every sum --
    including unknown x 0 -- so no screen can close on a product the dock never
    prepared.
    """
    from masck_one.core_sketch_resources import read, total
    from masck_one.dock_preparation import resource_scenario_products

    doses = derive_session_doses({"p": demand()}, [], binding(), now_s=1.0)
    out = resource_scenario_products(doses, [])
    assert "p:DOSE_UNRESOLVED_IN_RESOURCE_LEDGER" in out["blockers"]
    assert out["products"][0]["dose_ml"] is None

    carried = total([read(p["dose_ml"], p["id"] + ".dose_ml") for p in out["products"]])
    assert carried.high is None and carried.unknowns == ("p.dose_ml",)


def test_the_cleanser_is_not_routed_through_the_product_ledger():
    """Its quantities come from released authority; a row here would double-count."""
    from masck_one.dock_preparation import resource_scenario_products

    doses = derive_session_doses({"p": demand(), "c": demand(application="CLEAN")},
        [reservoir(), reservoir(slot="b", product="c", sku="SKU-c")], binding(("p", "c")),
        now_s=1.0)
    out = resource_scenario_products(doses, [reservoir()])
    assert [p["id"] for p in out["products"]] == ["p"]


def test_a_session_without_a_moisturiser_is_not_a_complete_routine():
    from masck_one.dock_preparation import resource_scenario_products

    doses = derive_session_doses({"p": demand(application="LEAVE_ON")}, [reservoir()],
                                 binding(), now_s=1.0)
    out = resource_scenario_products(doses, [reservoir()])
    assert "NO_MOISTURISE_PRODUCT_IN_SESSION" in out["blockers"]


def test_a_blocked_dose_stays_unknown_inside_the_real_whole_session_ledger():
    """End of the chain, against ``assess_resources`` itself rather than a stub.

    A product the dock could not prepare must not make the session look cheaper.
    Its unknown has to reach the ledger's storage and fluid-mass bounds, because
    those are what the screens close on.
    """
    from masck_one.authority import load_authority
    from masck_one.core_sketch_resources import assess_resources
    from masck_one.dock_preparation import resource_scenario_products

    authority = load_authority()

    def ledger(reservoirs):
        doses = derive_session_doses({"p": demand()}, reservoirs, binding(), now_s=1.0)
        rows = resource_scenario_products(doses, reservoirs)
        return assess_resources(authority, {"id": "probe", "products": rows["products"],
            "status": "UNVALIDATED_PLANNING_SCENARIO", "thermal_selected": False, "inputs": {}})

    prepared = ledger([reservoir()])
    assert prepared["bounds"]["leave_on_total_ml"] == {"low": 2.0, "high": 2.0, "unknowns": []}

    blocked = ledger([])
    for key in ("leave_on_total_ml", "session_product_storage_ml",
                "wearable_session_fluid_mass_g"):
        bound = blocked["bounds"][key]
        assert bound["high"] is None, key
        assert "p.dose_ml" in bound["unknowns"], key
    assert "leave_on_total_ml:UNRESOLVED" in blocked["blockers"]


def test_every_derive_state_result_has_the_same_shape():
    """A restricted product must not return a differently-typed record."""
    product, evidence = make_product()
    normal = derive_state(product, evidence, CONTEXT)
    product["restriction"] = "SUPPLIER_RECALL"
    restricted = derive_state(product, evidence, CONTEXT)
    assert set(normal) == set(restricted)
    for key in ("facets", "applications", "promoted_by"):
        assert type(normal[key]) is type(restricted[key]), key


def test_restricted_stays_restricted_under_its_own_transition():
    assert check_transition(RESTRICTED, RESTRICTED, "AI")["model_consistent"]
    assert check_transition(RESTRICTED, RESTRICTED, "AI")["direction"] == "RESTRICT"


def test_the_concept_screen_hashes_every_module_that_feeds_it():
    """Provenance that omits a module is provenance for a different program.

    The screen reports a source digest set. Half its CS-016/CS-017 inputs now
    come from this lane, so a set that predates these modules would describe
    something the screen no longer is.
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    source = (root / "src/masck_one/core_sketch_contracts.py").read_text()
    listed = {n.value for n in ast.walk(ast.parse(source))
              if isinstance(n, ast.Constant) and isinstance(n.value, str)
              and n.value.startswith(("src/masck_one/", "docs/", "config/"))}
    for module in ("product_lifecycle", "dock_preparation", "routine_schedule",
                   "core_sketch_resources", "core_sketch_trial"):
        assert f"src/masck_one/{module}.py" in listed, module
    for path in listed:
        assert (root / path).is_file(), f"screen hashes a path that does not exist: {path}"
