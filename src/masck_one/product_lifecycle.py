"""Product identity lifecycle and promotion authority for CS-017.

``core_sketch_contracts.assess_integrity`` and ``assess_readiness`` both require
a product whose application trust already reads ``VALIDATED`` and whose
``promoted_by`` is neither ``COMMUNITY`` nor ``AI``. Neither gate can see *how* a
record reached that value; both read a field that some earlier writer chose. A
learning system that decides a product "looks fine" only has to write the word.

This module is the missing producer. It derives lifecycle state from declared
facets and accepted evidence, refuses the transitions an inference system would
otherwise take on its own, and emits exactly the records those gates consume. It
does not replace them: nothing here judges a prepared session, and every result
still denies hardware authorization.

Evidence is bound to an identity *version*, so a reformulation demotes a product
by construction rather than by a special case: evidence scoped to one version
never covers the next.

Nothing here creates BENCH, HUMAN, REG_CLAIM or SUPPLIER evidence, measures a
product, or authorises hardware. A passing check means a declared record is
internally consistent, not that the product was ever put on a bench.
"""
from __future__ import annotations

from typing import Any

from .core_sketch_contracts import (
    CLASSIFICATION, CoreSketchError, digest, evidence_covers, result, text, unique,
)

EVIDENCE_STATUS = "DECLARED_RECORD_CONSISTENCY_NOT_PRODUCT_QUALIFICATION"

#: Ordered lifecycle. ``RESTRICTED_OR_UNSUPPORTED`` is deliberately outside the
#: rank ladder: it is a terminal refusal reachable from anywhere, not a rung.
LIFECYCLE = ("UNKNOWN", "KNOWN", "CHARACTERISED", "VALIDATED")
RESTRICTED = "RESTRICTED_OR_UNSUPPORTED"
STATES = frozenset(LIFECYCLE) | {RESTRICTED}
RANK = {state: index for index, state in enumerate(LIFECYCLE)}

#: Stage kinds that bind a product in ``validate_plan``. Application evidence is
#: proven for exactly one of these and is never carried across to another.
APPLICATION_CLASSES = frozenset({"CLEAN", "LEAVE_ON", "MOISTURISE", "FACIAL_SPF"})

#: A regulated performance claim is not a deposition outcome. Proof that a film
#: reached skin says nothing about the protection factor that film delivers, so
#: these classes additionally require human testing and a regulatory file.
REGULATED_APPLICATION_CLASSES = frozenset({"FACIAL_SPF"})

#: Actors whose accepted evidence can raise a product one rung.
PROMOTING_ACTORS = frozenset({"BENCH_LAB", "SUPPLIER_TECHNICAL", "REGULATORY_FILE"})
#: Actors that may observe, report and restrict, but never promote. Community
#: scale is not evidence: ten thousand reports raise nothing.
OBSERVING_ACTORS = frozenset({"AI", "COMMUNITY", "USER_SELF_REPORT", "RETAILER_LISTING"})
ACTORS = PROMOTING_ACTORS | OBSERVING_ACTORS

FACET_EVIDENCE: dict[str, frozenset[str]] = {
    "identity": frozenset({"SUPPLIER"}),
    "behavior": frozenset({"BENCH"}),
    "compatibility": frozenset({"BENCH", "SUPPLIER"}),
}
FACET_STATE = {
    "identity": "RESOLVED",
    "behavior": "CHARACTERISED",
    "compatibility": "PRESERVATION_VERIFIED",
}
APPLICATION_EVIDENCE = frozenset({"BENCH", "SUPPLIER"})
REGULATED_APPLICATION_EVIDENCE = APPLICATION_EVIDENCE | {"HUMAN", "REG_CLAIM"}

IDENTITY_FIELDS = ("sku", "market", "identity_version")


def scope_for(context: str, ident: str, version: str, facet: str, application: str | None = None) -> str:
    """Evidence scope. The identity version is inside the scope on purpose.

    A reformulation changes the version, so every scope moves with it and the
    old evidence stops covering the product without anyone remembering to
    revoke it.
    """
    parts = [text(context, "context"), text(ident, "product id"), text(version, "identity_version"),
             text(facet, "facet")]
    if application is not None:
        if application not in APPLICATION_CLASSES:
            raise CoreSketchError("unknown application class")
        parts.append(application)
    return "/".join(parts)


def _facet(product: dict, name: str) -> dict:
    facet = product.get(name)
    if not isinstance(facet, dict):
        raise CoreSketchError(f"product must declare an independent {name} record")
    return facet


def _identity_version(product: dict) -> str:
    identity = _facet(product, "identity")
    for field in IDENTITY_FIELDS:
        text(identity.get(field), field)
    return identity["identity_version"]


def derive_state(product: dict, evidence: list[dict], context: str) -> dict:
    """Compute lifecycle state from facets and evidence. Never read a stored state.

    The same rule CS-016 applies to READY applies here: a trust level that is
    remembered rather than recomputed is a trust level nobody is checking.
    """
    digest(product)
    ident = text(product.get("id"), "product id")
    context = text(context, "context")
    for name in ("identity", "behavior", "compatibility", "applications"):
        if not isinstance(product.get(name), dict):
            raise CoreSketchError("product must declare identity, behavior, compatibility and applications")
    blockers: list[str] = []

    restriction = product.get("restriction")
    if restriction is not None:
        text(restriction, "restriction")
        return result([ident + ":" + RESTRICTED], state=RESTRICTED, product_id=ident,
            evidence_status=EVIDENCE_STATUS, restriction=restriction, facets={},
            applications={}, identity_version=None, promoted_by=None)

    version = _identity_version(product)
    facets: dict[str, bool] = {}
    for name, required in FACET_EVIDENCE.items():
        facet = _facet(product, name)
        state_key = "status" if name == "identity" else "state"
        declared = facet.get(state_key) == FACET_STATE[name]
        if name == "identity" and facet.get("resolved_by") == "FLOW_FINGERPRINT":
            # Two clear liquids of similar viscosity behave alike. Behaviour
            # narrows a guess; it never resolves which product is loaded.
            declared = False
        covered = evidence_covers(required, facet.get("evidence_ids", []), evidence,
                                  scope_for(context, ident, version, name))
        if name == "behavior" and not facet.get("profile_binding"):
            declared = False
        facets[name] = bool(declared and covered)
        if not facets[name]:
            blockers.append(ident + ":" + name.upper() + "_NOT_ESTABLISHED_FOR_" + version)

    applications: dict[str, dict] = {}
    for name, record in product["applications"].items():
        if name not in APPLICATION_CLASSES:
            raise CoreSketchError("unknown application class")
        if not isinstance(record, dict):
            raise CoreSketchError("application record must be an object")
        required = (REGULATED_APPLICATION_EVIDENCE if name in REGULATED_APPLICATION_CLASSES
                    else APPLICATION_EVIDENCE)
        actor = record.get("promoted_by")
        reasons: list[str] = []
        if actor is not None and actor not in ACTORS:
            raise CoreSketchError("unknown promoting actor")
        if actor not in PROMOTING_ACTORS:
            reasons.append("PROMOTER_MAY_NOT_VALIDATE")
        if not evidence_covers(required, record.get("evidence_ids", []), evidence,
                               scope_for(context, ident, version, "application", name)):
            reasons.append("APPLICATION_EVIDENCE_MISSING")
        # Behaviour is what carries a product through the path; an application
        # cannot be validated on a product whose flow was never measured.
        if not (facets["behavior"] and facets["compatibility"] and facets["identity"]):
            reasons.append("UNDERLYING_FACETS_NOT_ESTABLISHED")
        trusted = not reasons
        applications[name] = {"trust": "VALIDATED" if trusted else "UNSUPPORTED",
            "promoted_by": actor if trusted else None, "blockers": sorted(reasons)}
        if not trusted:
            blockers += [ident + ":" + name + ":" + reason for reason in reasons]

    if not facets["identity"]:
        state = "UNKNOWN"
    elif not (facets["behavior"] and facets["compatibility"]):
        state = "KNOWN"
    elif any(a["trust"] == "VALIDATED" for a in applications.values()):
        state = "VALIDATED"
    else:
        state = "CHARACTERISED"
    promoters = {a["promoted_by"] for a in applications.values() if a["promoted_by"]}
    return result(blockers, state=state, product_id=ident, identity_version=version,
        evidence_status=EVIDENCE_STATUS, restriction=None, facets=facets,
        applications=applications, promoted_by=sorted(promoters))


def check_transition(before: str, after: str, actor: str) -> dict:
    """Judge a lifecycle move. Restriction is free; promotion is earned, one rung."""
    for state in (before, after):
        if state not in STATES:
            raise CoreSketchError("unknown lifecycle state")
    if actor not in ACTORS:
        raise CoreSketchError("unknown actor")
    blockers: list[str] = []
    if after == RESTRICTED or before == RESTRICTED and after == before:
        pass  # fail-closed direction: anyone may restrict, at any time.
    elif before == RESTRICTED:
        blockers.append("RESTRICTION_LIFTED_WITHOUT_REQUALIFICATION")
    elif RANK[after] > RANK[before]:
        if actor not in PROMOTING_ACTORS:
            blockers.append(actor + ":MAY_NOT_PROMOTE")
        if RANK[after] - RANK[before] > 1:
            blockers.append("LIFECYCLE_STAGE_SKIPPED")
    return result(blockers, before=before, after=after, actor=actor,
        evidence_status=EVIDENCE_STATUS,
        direction="RESTRICT" if after == RESTRICTED else
                 "PROMOTE" if RANK.get(after, -1) > RANK.get(before, -1) else
                 "DEMOTE" if RANK.get(after, -1) < RANK.get(before, -1) else "HOLD")


def summarise_observations(observations: list[dict]) -> dict:
    """Bucket field reports. Volume is reported; it never becomes qualification."""
    counts: dict[str, int] = {}
    for record in observations:
        if not isinstance(record, dict):
            raise CoreSketchError("observation must be an object")
        actor = text(record.get("actor"), "actor")
        if actor not in ACTORS:
            raise CoreSketchError("unknown actor")
        if actor in PROMOTING_ACTORS:
            raise CoreSketchError("qualifying work is evidence, not a field observation")
        counts[actor] = counts.get(actor, 0) + 1
    return result([], counts=counts, promotes_nothing=True, evidence_status=EVIDENCE_STATUS,
        interpretation="Field reports may restrict a product. No count of them promotes one.")


def session_product_records(binding: dict, products: list[dict], evidence: list[dict],
                            context: str, required_applications: dict[str, str]) -> dict:
    """Emit the ``current['products']`` rows ``assess_readiness`` consumes.

    ``required_applications`` maps each bound product to the application class
    the routine actually asks it to perform. Validation for one class never
    satisfies another, so an SPF stage is not covered by a moisturiser's record.
    """
    digest([binding, required_applications])
    catalog = unique(products)
    expected = unique(binding.get("product_bindings", []))
    if not expected:
        raise CoreSketchError("complete routine needs explicit product bindings")
    if set(expected) != set(required_applications):
        raise CoreSketchError("every bound product must name the application it performs")
    context_digest = digest(binding)
    blockers: list[str] = []
    rows: list[dict] = []
    for ident, want in expected.items():
        for field in IDENTITY_FIELDS + ("slot",):
            text(want.get(field), field)
        application = required_applications[ident]
        if application not in APPLICATION_CLASSES:
            raise CoreSketchError("unknown application class")
        product = catalog.get(ident)
        if product is None:
            # A product the plan needs but the catalog lacks is unknown, never absent-and-fine.
            blockers.append(ident + ":PRODUCT_NOT_IN_CATALOGUE")
            rows.append({"id": ident, "binding": want, "trust": "UNSUPPORTED", "promoted_by": None,
                "context_digest": context_digest, "identity_status": "UNKNOWN",
                "application": application, "lifecycle_state": "UNKNOWN"})
            continue
        state = derive_state(product, evidence, context)
        identity = product["identity"]
        if any(identity.get(f) != want.get(f) for f in IDENTITY_FIELDS):
            blockers.append(ident + ":BOUND_IDENTITY_DOES_NOT_MATCH_CATALOGUE")
        record = state["applications"].get(application, {"trust": "UNSUPPORTED", "promoted_by": None,
            "blockers": ["APPLICATION_NOT_DECLARED"]})
        if record["trust"] != "VALIDATED":
            blockers.append(ident + ":" + application + ":NOT_VALIDATED_FOR_REQUIRED_APPLICATION")
        blockers += state["blockers"]
        rows.append({"id": ident, "binding": want, "trust": record["trust"],
            "promoted_by": record["promoted_by"], "context_digest": context_digest,
            "identity_status": "RESOLVED" if state["facets"].get("identity") else "UNKNOWN",
            "application": application, "lifecycle_state": state["state"]})
    return result(blockers, products=rows, context_digest=context_digest,
        evidence_status=EVIDENCE_STATUS, classification=CLASSIFICATION)
