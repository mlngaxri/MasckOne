"""Dock reservoir identity, derived invalidation and session dose preparation (CS-016/CS-017).

``core_sketch_contracts.invalidate`` applies an invalidation event that somebody
already knew about. ``assess_readiness`` then refuses a session whose epoch moved.
Between those two sits the part that decides an event happened at all, and until
now nothing filled it: a reservoir could be unscrewed, emptied, refilled with a
different SKU and screwed back on, and every gate downstream would still be
comparing the digests it was handed.

This module observes the dock between preparations and *derives* the events the
existing owner consumes. It also prepares the session dose manifest, which is the
other place a silent zero can enter the system: a product the routine needs but
the dock does not hold is BLOCKED, never a quantity of nothing.

Dock bulk and wearable session inventory are accounted separately and never
summed. A litre of cleanser in the dock is not a litre on someone's face.

Nothing here measures a fluid, proves a changeover, or authorises hardware.
"""
from __future__ import annotations

from copy import deepcopy

from .core_sketch_contracts import (
    CLASSIFICATION, CoreSketchError, INVALIDATION_EVENTS, digest, evidence_covers,
    invalidate, number, result, text, unique,
)
from .core_sketch_resources import Bound, fixed, read, total
from .product_lifecycle import APPLICATION_CLASSES, IDENTITY_FIELDS

EVIDENCE_STATUS = "DECLARED_DOCK_STATE_CONSISTENCY_NOT_MEASURED_FLUID_IDENTITY"

#: Where inventory physically sits. Only WEARABLE inventory is ever carried.
LOCATIONS = frozenset({"DOCK", "WEARABLE"})
#: A reservoir must name all of these before anything downstream may trust it.
RESERVOIR_FIELDS = ("slot", "product", "lot", "fill_epoch") + IDENTITY_FIELDS

DOSE_BLOCKED = "BLOCKED_NOT_PREPARED"
DOSE_PREPARED = "SEALED_PREPARED"


def _reservoir(record: dict) -> dict:
    if not isinstance(record, dict):
        raise CoreSketchError("reservoir record must be an object")
    for field in RESERVOIR_FIELDS:
        if field != "fill_epoch":
            text(record.get(field), field)
    epoch = record.get("fill_epoch")
    if type(epoch) is not int or epoch < 0:
        raise CoreSketchError("fill_epoch must be a nonnegative integer")
    if record.get("location") not in LOCATIONS:
        raise CoreSketchError("reservoir must declare DOCK or WEARABLE location")
    if type(record.get("readable")) is not bool:
        raise CoreSketchError("reservoir must declare whether its identity could be read")
    return record


def _slots(records: list[dict]) -> dict[str, dict]:
    return {slot: _reservoir(r) for slot, r in unique(records, "slot").items()}


def observe_reservoirs(previous: list[dict], current: list[dict]) -> dict:
    """Derive invalidation events from what physically changed in the dock.

    Every event returned is a member of the existing ``INVALIDATION_EVENTS`` set,
    so the caller feeds them straight to ``invalidate`` rather than to a second,
    parallel notion of staleness.
    """
    before, after = _slots(previous), _slots(current)
    events: set[str] = set()
    findings: list[str] = []

    def note(slot: str, reason: str, event: str) -> None:
        findings.append(slot + ":" + reason)
        events.add(event)

    for slot in sorted(set(before) | set(after)):
        was, now = before.get(slot), after.get(slot)
        if was is None or now is None:
            note(slot, "SLOT_ADDED" if was is None else "SLOT_REMOVED", "ASSIGNMENT_CHANGED")
            if now is not None and not now["readable"]:
                note(slot, "IDENTITY_UNREADABLE", "CHANGEOVER_INCOMPLETE")
            continue
        # An unreadable reservoir is not an unchanged one. Nothing may be assumed
        # about a container whose label the dock could not resolve.
        if not (was["readable"] and now["readable"]):
            note(slot, "IDENTITY_UNREADABLE", "CHANGEOVER_INCOMPLETE")
        if now["identity_version"] != was["identity_version"]:
            note(slot, "IDENTITY_VERSION_CHANGED", "REFORMULATION")
            note(slot, "IDENTITY_VERSION_CHANGED", "PRODUCT_CHANGED")
        if now["sku"] != was["sku"] or now["market"] != was["market"]:
            note(slot, "SKU_OR_MARKET_CHANGED", "PRODUCT_CHANGED")
        if now["lot"] != was["lot"]:
            note(slot, "LOT_CHANGED", "PRODUCT_CHANGED")
        if now["fill_epoch"] != was["fill_epoch"]:
            note(slot, "REFILLED", "PRODUCT_CHANGED")
        if now["product"] != was["product"]:
            note(slot, "PRODUCT_BINDING_MOVED", "ASSIGNMENT_CHANGED")
        if now["location"] != was["location"]:
            note(slot, "LOCATION_CHANGED", "HARDWARE_CHANGED")
        old_ml, new_ml = was.get("volume_ml"), now.get("volume_ml")
        if old_ml is None or new_ml is None:
            note(slot, "VOLUME_UNKNOWN", "RESOURCE_CHANGED")
        else:
            number(old_ml, "volume_ml"), number(new_ml, "volume_ml")
            # A top-up under an unchanged lot and fill epoch mixes an unproven
            # quantity of new fluid into old fluid. The dock cannot see that, so
            # rising volume without a declared refill is treated as a change.
            if new_ml > old_ml and now["fill_epoch"] == was["fill_epoch"]:
                note(slot, "UNDECLARED_TOP_UP", "PRODUCT_CHANGED")
            elif new_ml < old_ml:
                note(slot, "VOLUME_DRAWN_DOWN", "RESOURCE_CHANGED")
    moved = {r["product"]: slot for slot, r in after.items()}
    for slot, was in before.items():
        if moved.get(was["product"], slot) != slot:
            note(slot, "PRODUCT_SERVED_FROM_DIFFERENT_SLOT", "ASSIGNMENT_CHANGED")
    if not events <= INVALIDATION_EVENTS:
        raise CoreSketchError("derived an event the session model cannot apply")
    return result(sorted(findings), derived_events=sorted(events),
        preparation_survives=not events, evidence_status=EVIDENCE_STATUS,
        previous_digest=digest(previous), current_digest=digest(current))


def apply_observed_events(session: dict, previous: list[dict], current: list[dict]) -> dict:
    """Observe the dock, then hand every derived event to the existing owner."""
    observation = observe_reservoirs(previous, current)
    updated = deepcopy(session)
    for event in observation["derived_events"]:
        updated = invalidate(updated, event)
    return {"session": updated, "observation": observation,
        "classification": CLASSIFICATION, "hardware_execution_authorized": False}


def assess_carryover(transitions: list[dict], evidence: list[dict], context: str) -> dict:
    """Judge residue handed from one product to the next at a shared node.

    Scopes match ``assess_integrity`` exactly, so one bench result serves the
    producer and the gate instead of two records drifting apart.
    """
    context = text(context, "context")
    blockers: list[str] = []
    for record in unique(transitions).values():
        node = text(record.get("node"), "node")
        following = text(record.get("to_product"), "to_product")
        prior = record.get("from_product")
        changeover = record.get("changeover")
        if changeover not in {"VERIFIED_COMPLETE", "INCOMPLETE", "UNKNOWN"}:
            raise CoreSketchError("changeover state must be explicit")
        if prior is None or prior == "UNKNOWN":
            # Residue of unknown origin is the one case that cannot be argued
            # clean: there is no pair to prove a carryover result for.
            blockers.append(node + ":UNKNOWN_RESIDUE_IS_NOT_CLEAN")
            continue
        text(prior, "from_product")
        if changeover != "VERIFIED_COMPLETE":
            blockers.append(node + ":" + prior + "->" + following + ":CHANGEOVER_" + changeover)
        scope = context + "/carryover/" + node + "/" + prior + "/" + following
        if not evidence_covers({"BENCH"}, record.get("evidence_ids", []), evidence, scope):
            blockers.append(node + ":" + prior + "->" + following + ":CARRYOVER_UNPROVED")
    return result(blockers, evidence_status=EVIDENCE_STATUS,
        interpretation="A clean path is proved per ordered product pair, never assumed from silence.")


def derive_session_doses(demands: dict, reservoirs: list[dict], binding: dict, now_s: float) -> dict:
    """Prepare the dose manifest ``assess_readiness`` consumes.

    A product the routine requires and the dock does not hold is BLOCKED. It is
    never a dose of zero, and never silently dropped from the manifest, because
    both of those turn a missing step into a completed one.
    """
    now = number(now_s, "now_s")
    expected = unique(binding.get("product_bindings", []))
    if not expected:
        raise CoreSketchError("complete routine needs explicit product bindings")
    if set(expected) != set(demands):
        raise CoreSketchError("dose demands must cover exactly the bound products")
    held = {r["product"]: r for r in (_reservoir(x) for x in reservoirs)}
    blockers: list[str] = []
    rows: list[dict] = []
    volumes: list[Bound] = []
    for ident, want in sorted(expected.items()):
        demand = demands[ident]
        if not isinstance(demand, dict):
            raise CoreSketchError("dose demand must be an object")
        if demand.get("application") not in APPLICATION_CLASSES:
            raise CoreSketchError("dose demand must name its application class")
        reasons: list[str] = []
        source = held.get(ident)
        target = demand.get("target_ml")
        if source is None:
            reasons.append("PRODUCT_NOT_LOADED")
        else:
            if not source["readable"]:
                reasons.append("SOURCE_IDENTITY_UNREADABLE")
            if any(source.get(f) != want.get(f) for f in IDENTITY_FIELDS):
                reasons.append("LOADED_IDENTITY_DOES_NOT_MATCH_BINDING")
            if source.get("slot") != want.get("slot"):
                reasons.append("SLOT_DOES_NOT_MATCH_BINDING")
            if source.get("expires_at_s") is None or now >= number(source["expires_at_s"], "expiry"):
                reasons.append("SOURCE_AGE_UNKNOWN_OR_EXPIRED")
            if source.get("contamination_state") != "VERIFIED_CLEAN":
                reasons.append("SOURCE_CLEANLINESS_UNPROVED")
        if target is None:
            # The dose this product needs was never characterised. Unknown is the
            # answer; substituting zero would report the step as performed.
            reasons.append("DOSE_UNKNOWN")
        else:
            number(target, "target_ml")
            lo, hi = demand.get("min_ml"), demand.get("max_ml")
            if lo is None or hi is None:
                reasons.append("DOSE_WINDOW_UNKNOWN")
            elif not number(lo, "min_ml") <= target <= number(hi, "max_ml"):
                reasons.append("DOSE_OUTSIDE_PROFILE_WINDOW")
            available = None if source is None else source.get("volume_ml")
            if available is None:
                reasons.append("AVAILABLE_VOLUME_UNKNOWN")
            elif number(available, "volume_ml") < target:
                reasons.append("INSUFFICIENT_VOLUME_FOR_DOSE")
        prepared = not reasons
        volumes.append(fixed(target) if prepared else read(None, ident + ".dose_ml"))
        blockers += [ident + ":" + reason for reason in reasons]
        rows.append({"product_binding": ident, "binding": deepcopy(want),
            "dose_id": None if not prepared else "dose:" + digest([want, target, source["lot"],
                source["fill_epoch"]])[:32],
            "state": DOSE_PREPARED if prepared else DOSE_BLOCKED,
            "preservation": "VERIFIED" if prepared else "UNPROVED",
            "expires_at_s": source.get("expires_at_s") if prepared else None,
            "quantity_ml": target if prepared else None,
            "application": demand["application"], "blockers": sorted(reasons)})
    demanded = total(volumes)
    return result(blockers, doses=rows, wearable_session_product_ml=demanded.record(),
        evidence_status=EVIDENCE_STATUS, binding_digest=digest(binding),
        every_product_accounted=len(rows) == len(expected))


def account_inventory(reservoirs: list[dict], doses: list[dict]) -> dict:
    """Keep dock bulk and wearable session inventory in separate columns.

    Bulk sitting in the dock is the reason the wearable can be small. Adding it
    to the worn mass would misreport the product; counting it as available on
    the head would misreport the session.
    """
    records = [_reservoir(r) for r in reservoirs]
    unique(reservoirs, "slot")
    columns = {"DOCK": [], "WEARABLE": []}
    for record in records:
        volume = read(None, record["slot"] + ".volume_ml") if record.get("volume_ml") is None \
            else fixed(number(record["volume_ml"], "volume_ml"))
        density = read(None, record["slot"] + ".density_g_ml") if record.get("density_g_ml") is None \
            else fixed(number(record["density_g_ml"], "density_g_ml"))
        columns[record["location"]].append(volume * density)
    prepared = [d for d in doses if d.get("state") == DOSE_PREPARED]
    session_ml = total([fixed(number(d["quantity_ml"], "quantity_ml")) for d in prepared]
                       + [read(None, d["product_binding"] + ".dose_ml")
                          for d in doses if d.get("state") != DOSE_PREPARED])
    dock_mass, wearable_mass = total(columns["DOCK"]), total(columns["WEARABLE"])
    blockers = [k + ":UNRESOLVED" for k, v in
                {"dock_bulk_mass_g": dock_mass, "wearable_reservoir_mass_g": wearable_mass,
                 "session_product_ml": session_ml}.items() if v.high is None]
    return result(blockers, dock_bulk_mass_g=dock_mass.record(),
        wearable_reservoir_mass_g=wearable_mass.record(), session_product_ml=session_ml.record(),
        dock_bulk_counts_toward_worn_mass=False, evidence_status=EVIDENCE_STATUS,
        interpretation="Dock bulk is never added to worn mass and never offered as session supply.")


#: The carryover investigations CS-017 requires. These are classes of transition,
#: not one pair of products, because each has a different failure: a rinse
#: dilutes, a changeover displaces, and a shared return mixes everything that
#: ever went down it.
CARRYOVER_CLASSES = frozenset({
    "CLEANSER_TO_RINSE", "RINSE_TO_FIRST_LEAVE_ON", "LEAVE_ON_TO_LEAVE_ON",
    "LEAVE_ON_TO_MOISTURISER", "MOISTURISER_TO_SPF", "PRODUCT_CHANGEOVER",
    "DOCK_OR_SERVICE_FLUID_RESIDUE", "SHARED_DOWNSTREAM_INTERFACE_OR_RETURN",
})
#: Classes that apply only when the routine actually schedules both sides.
CONDITIONAL_CARRYOVER_CLASSES = {
    "MOISTURISER_TO_SPF": frozenset({"MOISTURISE", "FACIAL_SPF"}),
    "LEAVE_ON_TO_MOISTURISER": frozenset({"LEAVE_ON", "MOISTURISE"}),
    "RINSE_TO_FIRST_LEAVE_ON": frozenset({"RINSE_RECOVER", "LEAVE_ON"}),
    "CLEANSER_TO_RINSE": frozenset({"CLEAN", "RINSE_RECOVER"}),
}


def required_carryover_classes(stage_kinds: list[str]) -> set[str]:
    """Which carryover investigations this routine owes, given what it schedules."""
    kinds = {text(k, "stage kind") for k in stage_kinds}
    required = set(CARRYOVER_CLASSES) - set(CONDITIONAL_CARRYOVER_CLASSES)
    for name, needs in CONDITIONAL_CARRYOVER_CLASSES.items():
        if needs <= kinds:
            required.add(name)
    if list(stage_kinds).count("LEAVE_ON") < 2:
        required.discard("LEAVE_ON_TO_LEAVE_ON")
    return required


def carryover_coverage(declared: list[str], stage_kinds: list[str]) -> dict:
    """Confirm every owed investigation was actually opened.

    An executed purge command is not a result, so this only reports which
    investigations exist; ``assess_carryover`` judges what they found.
    """
    seen = set()
    for name in declared:
        if text(name, "carryover class") not in CARRYOVER_CLASSES:
            raise CoreSketchError("unknown carryover investigation class")
        seen.add(name)
    required = required_carryover_classes(stage_kinds)
    return result(sorted(c + ":CARRYOVER_CLASS_NOT_INVESTIGATED" for c in required - seen),
        required=sorted(required), declared=sorted(seen), evidence_status=EVIDENCE_STATUS)


def assess_flow_fingerprint(expected: dict, observed: dict, tolerance: float) -> dict:
    """Compare observed flow against the expected profile.

    A contradiction stops automated preparation and asks the user to confirm the
    product. A *match* does nothing at all: two clear liquids of similar
    viscosity behave alike, so agreement here is not chemical identity and must
    never be allowed to resolve one.
    """
    tolerance = number(tolerance, "tolerance")
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        raise CoreSketchError("flow profiles must be objects")
    if not expected or set(expected) != set(observed):
        raise CoreSketchError("flow comparison needs the same declared channels")
    blockers, deviations = [], {}
    for channel, want in sorted(expected.items()):
        got = observed[channel]
        if want is None or got is None:
            blockers.append(channel + ":FLOW_OBSERVATION_UNKNOWN")
            deviations[channel] = None
            continue
        want, got = number(want, channel), number(got, channel)
        if want == 0:
            raise CoreSketchError("expected flow profile cannot be zero-referenced")
        deviation = abs(got - want) / want
        deviations[channel] = deviation
        if deviation > tolerance:
            blockers.append(channel + ":OBSERVED_BEHAVIOUR_CONTRADICTS_PROFILE")
    contradicted = bool(blockers)
    return result(blockers, deviations=deviations, contradicted=contradicted,
        action="REQUEST_PRODUCT_CONFIRMATION" if contradicted else "CONTINUE_WITHOUT_CONCLUSION",
        confirms_identity=False, evidence_status=EVIDENCE_STATUS,
        interpretation="A similar flow fingerprint does not prove chemical identity.")
