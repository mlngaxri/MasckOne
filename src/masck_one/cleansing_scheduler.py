"""Deterministic regional plan compiler for the canonical cleansing controller.

``regional_cleansing`` already answers the runtime question well: given this
action, right now, do all the regions it touches authorize it? ``permits``,
``shared_channel_permitted`` and ``SessionLedger.authorize_shared`` between them
refuse averaged budgets and refuse a shared channel whose footprint reaches a
region that has stopped consenting.

Nothing answers the question before the session starts: *is there any ordering of
the actions this hardware actually has that finishes every required region
without treating a finished one again?* That is not the same question. A plan can
consist entirely of individually-authorized actions and still strand a region,
because the authorization check is local and the stranding is a property of the
footprint graph.

The stranding case is concrete. Suppose the left cheek still needs cleaning, the
forehead is already COMPLETE, and every CLEAN action whose footprint reaches the
left cheek also reaches the forehead. Each of those actions is individually
refused, correctly, by the forehead's ledger. Run the session anyway and the left
cheek simply never completes, with no single refusal explaining why. The honest
answer is that the demand partition this routine asks for is not executable on
this mechanism, and the caller needs to know that before anyone is wearing it --
along with which cells caused it.

So this module compiles. It consumes the real channel/footprint topology rather
than assuming one actuator per cell, and returns either a bounded ordered plan or
a machine-checkable witness naming the trapped region, the blocking region and
the exact cells that couple them.

Nothing here relaxes a ceiling, authorizes hardware, or invents a human-use
limit. A compiled plan is a claim about reachability under declared footprints,
not a claim that cleansing works.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .regional_cleansing import Burden, ControlError, Region, VERSION, finite

EVIDENCE_STATUS = "DECLARED_FOOTPRINT_REACHABILITY_NOT_VALIDATED_CLEANSING"

#: Stages a required region must pass, in order. Recovery follows rinse because
#: rinsing is what it recovers from; the order is not a preference.
STAGE_ORDER = ("CLEAN", "RINSE", "RECOVER")

#: Outcomes. Exactly one is returned, and none of them means "probably fine".
PLAN_COMPILED = "PLAN_COMPILED"
HARDWARE_UNEXECUTABLE = "HARDWARE_UNEXECUTABLE"
BLOCKED_UNQUALIFIED = "BLOCKED_UNQUALIFIED"
NO_PLAN_WITHIN_BOUND = "NO_PLAN_WITHIN_BOUND"


@dataclass(frozen=True)
class Action:
    """One thing the mechanism can actually do, and everything it touches.

    ``cells`` is the *whole* affected footprint, not the intended target. An
    action that incidentally reaches a neighbouring region must declare those
    cells here; that incidental reach is the entire subject of this module.
    """

    action_id: str
    kind: str
    cells: frozenset[str]
    increment: Burden
    channel_id: str
    complexity: int = 1

    def __post_init__(self) -> None:
        if not self.action_id or not self.channel_id:
            raise ControlError("action and channel identity required")
        if self.kind not in STAGE_ORDER:
            raise ControlError("unsupported action kind")
        if not self.cells or any(not isinstance(c, str) or not c for c in self.cells):
            raise ControlError("explicit affected-cell footprint required")
        if type(self.complexity) is not int or self.complexity < 1:
            raise ControlError("positive integer complexity required")
        if self.kind != "CLEAN" and (self.increment.cleanser_ml or self.increment.tangential_mm):
            raise ControlError("cleaning hidden in another action kind")


@dataclass
class _Demand:
    region: Region
    stage_index: int = 0
    covered: dict[str, set[str]] = field(default_factory=dict)

    @property
    def stage(self) -> str | None:
        return STAGE_ORDER[self.stage_index] if self.stage_index < len(STAGE_ORDER) else None

    @property
    def finished(self) -> bool:
        return self.stage is None


def map_footprints(actions: list[Action], regions: dict[str, Region]) -> dict[str, frozenset[str]]:
    """Which regions each action reaches. An unmapped cell is never harmless.

    A footprint cell belonging to no declared region means the caller does not
    know what that part of the action touches. That is missing information, and
    missing information is refused rather than treated as reaching nothing.
    """

    owner: dict[str, str] = {}
    for key, region in regions.items():
        if key != region.region_id:
            raise ControlError("region identity mismatch")
        for cell in region.cells:
            if cell in owner:
                raise ControlError("coverage cell claimed by two regions")
            owner[cell] = key
    reach: dict[str, frozenset[str]] = {}
    seen: set[str] = set()
    for action in actions:
        if action.action_id in seen:
            raise ControlError("duplicate action identity")
        seen.add(action.action_id)
        unmapped = sorted(c for c in action.cells if c not in owner)
        if unmapped:
            raise ControlError(
                "action " + action.action_id + " touches unregistered cells: " + ",".join(unmapped)
            )
        reach[action.action_id] = frozenset(owner[c] for c in action.cells)
    return reach


def _witness(demand: _Demand, actions: list[Action], reach: dict[str, frozenset[str]],
             finished: set[str], regions: dict[str, Region], demands: dict,
             envelopes: dict, spent: dict, water: float, cleanser: float,
             session_water_ml: float, session_cleanser_ml: float) -> dict:
    """Name why a region is stranded, distinguishing the ways it can happen.

    "Completed" and "exhausted" are different failures with different remedies.
    A region that finished is done and should be bypassed; a region that hit its
    ceiling mid-routine is a budget problem. Reporting both as "no action reaches
    this region" would be false -- actions do reach it, and something else
    rejected them.
    """

    completed: dict[str, list[str]] = {}
    exhausted: dict[str, list[str]] = {}
    resource = False
    candidates = 0
    for action in actions:
        if action.kind != demand.stage or not (action.cells & demand.region.cells):
            continue
        candidates += 1
        touched = reach[action.action_id]
        for other in sorted(touched & finished):
            shared = sorted(action.cells & regions[other].cells)
            completed.setdefault(other, [])
            completed[other] += [c for c in shared if c not in completed[other]]
        for other in sorted(touched):
            if other in finished or other not in demands:
                continue
            if not spent[other].plus(action.increment).within(envelopes[other].maximum):
                shared = sorted(action.cells & regions[other].cells)
                exhausted.setdefault(other, [])
                exhausted[other] += [c for c in shared if c not in exhausted[other]]
        if (water + action.increment.water_ml > session_water_ml
                or cleanser + action.increment.cleanser_ml > session_cleanser_ml):
            resource = True

    if not candidates:
        reason = "NO_ACTION_REACHES_REGION"
        remedy = ("any action of kind " + str(demand.stage) + " reaching "
                  + demand.region.region_id)
    elif completed:
        reason = "COMPLETED_REGION_NOT_BYPASSABLE"
        remedy = ("an action of kind " + str(demand.stage) + " whose footprint reaches "
                  + demand.region.region_id + " without reaching " + ", ".join(sorted(completed)))
    elif exhausted:
        reason = "EXHAUSTED_REGION_NOT_BYPASSABLE"
        remedy = ("an action of kind " + str(demand.stage) + " whose footprint reaches "
                  + demand.region.region_id + " without spending budget in "
                  + ", ".join(sorted(exhausted)))
    elif resource:
        reason = "SESSION_RESOURCE_EXHAUSTED"
        remedy = "more qualified session water or cleanser, or a lower-consumption action"
    else:
        reason = "NO_ADMISSIBLE_ACTION"
        remedy = "an action of kind " + str(demand.stage) + " admissible in this state"

    return {
        "trapped_region": demand.region.region_id,
        "trapped_stage": demand.stage,
        "trapped_cells": sorted(demand.region.cells - demand.covered.get(demand.stage or "", set())),
        "blocking_regions": {k: sorted(v) for k, v in sorted(completed.items())},
        "exhausted_regions": {k: sorted(v) for k, v in sorted(exhausted.items())},
        "reason": reason,
        "minimum_capability_change": remedy,
    }


def compile_plan(regions: dict[str, Region], actions: list[Action], *, envelopes: dict,
                 session_water_ml: float | None = None, session_cleanser_ml: float | None = None,
                 max_steps: int = 256) -> dict:
    """Compile an ordered plan, or refuse with a witness. Never a partial guess.

    Selection is lexicographic and deterministic, in the contract's own order:
    constraint satisfaction first, then required-region progress, then least
    mechanical burden, then least chemical exposure, then fewest already-finished
    regions touched (which is always zero -- an action that touches one is not a
    candidate at all), then lower action complexity, then action id so two runs
    on the same inputs produce the same plan.
    """

    if type(max_steps) is not int or max_steps < 1:
        raise ControlError("positive step bound required")
    required = {k: r for k, r in regions.items() if r.classification == "REQUIRED"}
    if not required:
        raise ControlError("a cleansing plan requires at least one required region")
    reach = map_footprints(actions, regions)

    missing = sorted(k for k in required if envelopes.get(k) is None)
    if missing or session_water_ml is None or session_cleanser_ml is None:
        return {
            "version": VERSION, "evidence_status": EVIDENCE_STATUS,
            "outcome": BLOCKED_UNQUALIFIED, "human_use_eligible": False,
            "unqualified_regions": missing,
            "unqualified_session_resources": sorted(
                name for name, value in (("water_ml", session_water_ml),
                                         ("cleanser_ml", session_cleanser_ml)) if value is None),
            "evidence_owner": "qualified policy and session-resource owner",
            "steps": [], "witness": None,
        }
    finite(session_water_ml, "session water")
    finite(session_cleanser_ml, "session cleanser")

    demands = {k: _Demand(r) for k, r in required.items()}
    spent = {k: Burden() for k in required}
    water = cleanser = 0.0
    steps: list[dict] = []

    while any(not d.finished for d in demands.values()):
        if len(steps) >= max_steps:
            return _result(NO_PLAN_WITHIN_BOUND, steps, None, demands, water, cleanser,
                           bound=max_steps)
        finished = {k for k, d in demands.items() if d.finished}
        best = None
        for action in actions:
            touched = reach[action.action_id]
            # An action reaching a finished region is not a candidate. Over-treating
            # a region that has stopped consenting is the failure, not a cost.
            if touched & finished:
                continue
            gain = 0
            for key in touched:
                demand = demands.get(key)
                if demand is None or demand.finished or demand.stage != action.kind:
                    continue
                gain += len((action.cells & demand.region.cells)
                            - demand.covered.get(action.kind, set()))
            if not gain:
                continue
            over = False
            for key in touched:
                demand = demands[key]
                projected = spent[key].plus(action.increment)
                if not projected.within(envelopes[key].maximum):
                    over = True
                    break
            if over:
                continue
            if (water + action.increment.water_ml > session_water_ml
                    or cleanser + action.increment.cleanser_ml > session_cleanser_ml):
                continue
            # Lexicographic, in the contract's own order. Constraint satisfaction
            # already happened above (a non-candidate never gets here); what is
            # ranked is progress, then mechanical burden, then chemical exposure,
            # then treating a region that has already finished this stage, then
            # mechanism complexity, then identity so the plan is reproducible.
            repeats = sum(
                1 for key in touched
                if (d := demands.get(key)) is not None and not d.finished
                and d.stage != action.kind
            )
            rank = (-gain, action.increment.load_Ns + action.increment.tangential_mm,
                    action.increment.cleanser_ml, repeats, action.complexity,
                    action.action_id)
            if best is None or rank < best[0]:
                best = (rank, action, touched)
        if best is None:
            stalled = sorted(k for k, d in demands.items() if not d.finished)
            witness = _witness(demands[stalled[0]], actions, reach, finished, regions,
                               demands, envelopes, spent, water, cleanser,
                               session_water_ml, session_cleanser_ml)
            return _result(HARDWARE_UNEXECUTABLE, steps, witness, demands, water, cleanser,
                           bound=max_steps)
        _, action, touched = best
        water += action.increment.water_ml
        cleanser += action.increment.cleanser_ml
        for key in touched:
            demand = demands[key]
            spent[key] = spent[key].plus(action.increment)
            demand.covered.setdefault(action.kind, set()).update(
                action.cells & demand.region.cells)
            while (not demand.finished
                   and demand.covered.get(demand.stage, set()) >= demand.region.cells):
                demand.stage_index += 1
        steps.append({"action_id": action.action_id, "kind": action.kind,
                      "channel_id": action.channel_id, "regions": sorted(touched),
                      "cells": sorted(action.cells)})
    return _result(PLAN_COMPILED, steps, None, demands, water, cleanser, bound=max_steps)


def _result(outcome: str, steps: list[dict], witness: dict | None, demands: dict,
            water: float, cleanser: float, *, bound: int) -> dict:
    return {
        "version": VERSION, "evidence_status": EVIDENCE_STATUS, "outcome": outcome,
        "human_use_eligible": False, "steps": steps, "step_bound": bound,
        "witness": witness,
        "projected_session_water_ml": water, "projected_session_cleanser_ml": cleanser,
        "unfinished_regions": sorted(k for k, d in demands.items() if not d.finished),
        "remaining_stage": {k: d.stage for k, d in sorted(demands.items()) if not d.finished},
        "interpretation": "Reachability under declared footprints. Not proof that "
                          "cleansing occurred, and not a human-use authorization.",
    }
