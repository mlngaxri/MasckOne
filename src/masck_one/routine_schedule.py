"""Routine definition, schedule context, SPF handling and offline execution (CS-016).

The product promise is that a user does not change their routine for the device;
the device learns to perform their routine. That makes the routine a first-class
record with a revision, not a set of options chosen at run time, and it makes the
honest reporting of a *reduced* routine a safety property rather than a nicety:
a session that skipped a step has not completed the scheduled routine, however
well the steps it did run went.

Two rules here are stricter than the rest and deliberately so.

Sun protection is a regulated outcome, not a deposition. It runs in the morning,
it is never substituted by a moisturiser that happens to carry a claim on its
carton, and it is never inferred from a routine that did not schedule it.

Normal configured use is phone-, cloud- and internet-independent. Network state
is therefore not an input to readiness anywhere in this module; what the device
needs, it must already hold. ``assess_offline_execution`` fails a routine whose
normal path reaches for a network.

Nothing here schedules real hardware, doses a product, or authorises execution.
"""
from __future__ import annotations

from .core_sketch_contracts import (
    CLASSIFICATION, CoreSketchError, STAGE_ORDER, digest, number, result, text, unique,
)
from .product_lifecycle import APPLICATION_CLASSES, REGULATED_APPLICATION_CLASSES

EVIDENCE_STATUS = "DECLARED_ROUTINE_CONSISTENCY_NOT_A_SCHEDULED_HARDWARE_SESSION"

#: The six honest states. They are distinct concepts, not severities of one.
DEGRADED_STATES = ("READY", "PREPARING", "NEEDS_ATTENTION", "PARTIAL_ROUTINE_AVAILABLE",
                   "NOT_READY", "SAFETY_HOLD")
SCHEDULE_CONTEXTS = frozenset({"AM", "PM", "WEEKLY", "AS_NEEDED"})
#: Sun protection belongs to the morning. A PM SPF stage is a definition error.
SPF_CONTEXTS = frozenset({"AM"})
SPF_STAGE = "FACIAL_SPF"

#: Ways a routine could claim sun protection happened without running an SPF
#: stage validated for it. Each is a real product behaviour, and none is SPF.
FORBIDDEN_SPF_SUBSTITUTES = frozenset({
    "MOISTURISER_WITH_SPF_CLAIM_ON_CARTON",
    "LEAVE_ON_WITH_UV_FILTER_INGREDIENT",
    "EXTENDED_MOISTURISE_STAGE",
    "PREVIOUS_DAY_RESIDUAL_FILM",
    "AI_INFERRED_ADEQUATE_PROTECTION",
})

#: Locally resident facts a normal session needs. Absent any of these the device
#: cannot run the routine by itself, which is the only mode that counts.
OFFLINE_RESIDENCY_KEYS = ("routine_revision", "profile_revision", "hardware_revision",
                          "authority_digest", "stage_parameters", "dose_windows",
                          "protected_region_map", "fault_response_table")


def validate_routine(routine: dict) -> dict:
    """Check a routine definition. Ordering, SPF placement and substitution."""
    digest(routine)
    text(routine.get("id"), "routine id")
    text(routine.get("revision"), "routine revision")
    contexts = routine.get("contexts")
    if not isinstance(contexts, dict) or not contexts:
        raise CoreSketchError("routine must declare at least one schedule context")
    if routine.get("substitutions"):
        # A routine that carries substitution rules can silently become a
        # different routine at run time, which is the thing the revision exists
        # to prevent.
        raise CoreSketchError("routine substitutions are not representable; revise the routine")
    resolved: dict[str, list[dict]] = {}
    blockers: list[str] = []
    for context, stages in contexts.items():
        if context not in SCHEDULE_CONTEXTS:
            raise CoreSketchError("unknown schedule context")
        ordered = list(unique(stages).values())
        kinds = [s.get("kind") for s in ordered]
        if any(k not in STAGE_ORDER for k in kinds):
            raise CoreSketchError("unknown stage kind")
        if [STAGE_ORDER[k] for k in kinds] != sorted(STAGE_ORDER[k] for k in kinds):
            raise CoreSketchError("stage order is not the selected routine order")
        for stage in ordered:
            if stage["kind"] in APPLICATION_CLASSES:
                text(stage.get("product_binding"), "product_binding")
            if stage.get("satisfied_by") in FORBIDDEN_SPF_SUBSTITUTES:
                blockers.append(context + ":" + stage["id"] + ":FORBIDDEN_SPF_SUBSTITUTE")
        if SPF_STAGE in kinds and context not in SPF_CONTEXTS:
            blockers.append(context + ":SPF_SCHEDULED_OUTSIDE_MORNING")
        if kinds.count(SPF_STAGE) > 1:
            raise CoreSketchError("sun protection cannot be scheduled twice in one session")
        resolved[context] = ordered
    return result(blockers, routine_id=routine["id"], revision=routine["revision"],
        contexts={c: [s["id"] for s in v] for c, v in resolved.items()},
        spf_contexts=sorted(c for c, v in resolved.items() if any(s["kind"] == SPF_STAGE for s in v)),
        routine_digest=digest(routine), evidence_status=EVIDENCE_STATUS)


def resolve_session(routine: dict, context: str, eligible_stages: dict) -> dict:
    """Resolve what this session would actually run, and say so honestly.

    A reduced routine is a different routine. It gets its own digest and it is
    never reported as the scheduled one completing.
    """
    definition = validate_routine(routine)
    if context not in definition["contexts"]:
        raise CoreSketchError("routine does not define this schedule context")
    scheduled = definition["contexts"][context]
    if not isinstance(eligible_stages, dict) or set(eligible_stages) != set(scheduled):
        raise CoreSketchError("eligibility must be declared for exactly the scheduled stages")
    runnable = [s for s in scheduled if eligible_stages[s] == "ELIGIBLE_FOR_EXACT_PLAN"]
    dropped = [s for s in scheduled if s not in runnable]
    stages = {s["id"]: s for s in unique(routine["contexts"][context]).values()}
    spf_dropped = [s for s in dropped if stages[s]["kind"] == SPF_STAGE]
    blockers = [s + ":STAGE_NOT_ELIGIBLE" for s in dropped]
    blockers += [s + ":SUN_PROTECTION_DROPPED" for s in spf_dropped]
    reduced = bool(dropped)
    return result(blockers, routine_id=routine["id"], context=context,
        scheduled_stage_ids=scheduled, runnable_stage_ids=runnable, dropped_stage_ids=dropped,
        is_reduced_routine=reduced,
        # A reduced session is a new eligible session with its own identity.
        session_plan_digest=digest({"routine": definition["routine_digest"], "context": context,
                                    "stages": runnable}),
        completes_scheduled_routine=not reduced,
        sun_protection_scheduled=any(stages[s]["kind"] == SPF_STAGE for s in scheduled),
        sun_protection_runnable=any(stages[s]["kind"] == SPF_STAGE for s in runnable),
        evidence_status=EVIDENCE_STATUS)


def offline_manifest(routine: dict, context: str, revisions: dict) -> dict:
    """List what must already be on the device for this session to run alone."""
    definition = validate_routine(routine)
    if context not in definition["contexts"]:
        raise CoreSketchError("routine does not define this schedule context")
    if not isinstance(revisions, dict):
        raise CoreSketchError("revisions must be an object")
    missing = [key for key in OFFLINE_RESIDENCY_KEYS if revisions.get(key) in (None, "", {}, [])]
    entries = {key: revisions.get(key) for key in OFFLINE_RESIDENCY_KEYS}
    return result([key + ":NOT_RESIDENT" for key in missing], required=list(OFFLINE_RESIDENCY_KEYS),
        entries=entries, missing=missing, routine_id=routine["id"], context=context,
        residency_digest=digest(entries), evidence_status=EVIDENCE_STATUS)


def assess_offline_execution(manifest: dict, local_cache: dict, network_reachable: bool) -> dict:
    """Judge whether the routine runs unaided. Network state is recorded, not used.

    ``network_reachable`` is accepted so a caller cannot claim this function
    never considered it. It is deliberately excluded from every blocker: a
    reachable network must not make a device ready, and an unreachable one must
    not make a properly prepared device unready.
    """
    if type(network_reachable) is not bool:
        raise CoreSketchError("network reachability must be explicit")
    if not isinstance(local_cache, dict):
        raise CoreSketchError("local cache must be an object")
    required = manifest.get("required")
    if not isinstance(required, list) or not required:
        raise CoreSketchError("manifest must declare its residency requirements")
    blockers = [key + ":NOT_CACHED_LOCALLY" for key in required
                if local_cache.get(key) in (None, "", {}, [])]
    blockers += [key + ":CACHED_COPY_DOES_NOT_MATCH_MANIFEST" for key in required
                 if local_cache.get(key) not in (None, "", {}, [])
                 and local_cache.get(key) != manifest.get("entries", {}).get(key)]
    for key in required:
        source = local_cache.get(key)
        if isinstance(source, dict) and source.get("resolved_from") == "NETWORK_AT_RUN_TIME":
            blockers.append(key + ":NORMAL_USE_DEPENDS_ON_NETWORK")
    return result(blockers, network_reachable=network_reachable,
        network_considered_in_readiness=False, evidence_status=EVIDENCE_STATUS,
        interpretation="Normal configured use is phone, cloud and internet independent.")


def derive_presented_state(readiness: dict, session: dict, offline: dict, *,
                           preparing: bool, user_action_required: bool,
                           reduced_routine_accepted: bool) -> dict:
    """Collapse the gates into one of the six honest states.

    The ordering matters: safety outranks everything, and a not-ready device is
    never presented as merely needing attention.
    """
    for flag in (preparing, user_action_required, reduced_routine_accepted):
        if type(flag) is not bool:
            raise CoreSketchError("presentation flags must be explicit")
    for record, name in ((readiness, "readiness"), (session, "session"), (offline, "offline")):
        if not isinstance(record, dict) or "blockers" not in record:
            raise CoreSketchError(name + " result required")
    safety = [b for b in readiness["blockers"] if b.startswith("FAULT") or "SAFETY" in b]
    blockers = sorted(set(readiness["blockers"]) | set(offline["blockers"]))
    if safety:
        state = "SAFETY_HOLD"
    elif readiness.get("prepared_ready") and not blockers and not session["blockers"]:
        state = "READY"
    elif preparing:
        state = "PREPARING"
    elif session.get("is_reduced_routine") and reduced_routine_accepted and not blockers:
        # Accepted, permissible and prepared: a new eligible session, reported as
        # exactly that and never as the scheduled routine finishing.
        state = "PARTIAL_ROUTINE_AVAILABLE"
    elif user_action_required and not blockers:
        state = "NEEDS_ATTENTION"
    else:
        state = "NOT_READY"
    return {"classification": CLASSIFICATION, "hardware_execution_authorized": False,
        "state": state, "blockers": blockers, "safety_blockers": sorted(safety),
        "completes_scheduled_routine": bool(session.get("completes_scheduled_routine"))
            and state == "READY",
        "sun_protection_runnable": bool(session.get("sun_protection_runnable")),
        "evidence_status": EVIDENCE_STATUS,
        "model_consistent": state == "READY"}
