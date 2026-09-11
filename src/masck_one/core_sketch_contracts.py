"""Non-authoritative whole-routine feasibility contracts.

These checks judge supplied concept records, not their physical authenticity.
They are deliberately not imported by firmware, the CAD exporter or readiness
hardware. Every result denies hardware authorization. No document or passing
test creates BENCH, HUMAN, REG_CLAIM or SUPPLIER evidence.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from . import _contracts

CLASSIFICATION = "NON_AUTHORITATIVE_CONCEPT_LOGIC_NOT_DEVICE_CONTROL"
PHASES = ("PLACEMENT", "CLEAN", "RINSE_RECOVER", "TREAT", "LEAVE_ON", "SETTLE", "RELEASE")
STAGE_ORDER = {"CLEAN": 0, "RINSE_RECOVER": 1, "TREAT": 2, "LEAVE_ON": 3,
               "MOISTURISE": 4, "FACIAL_SPF": 5, "SETTLE": 6, "RELEASE": 7}
CONTACT_CLASSES = frozenset({"skin_seals", "perimeter_contact", "support_pads",
    "retention_reaction", "massage_islands", "thermal_surfaces", "optical_carriers",
    "fluid_distribution", "stationary_bridges"})
# Coverage bookkeeping only, not registered anatomy or treatment coordinates.
WHOLE_FACE_REGIONS = frozenset({"forehead", "left_temple", "right_temple",
    "left_cheek", "right_cheek", "nose_skin", "upper_lip_surround", "chin",
    "left_jaw", "right_jaw", "eye_protected", "nostril_protected", "mouth_protected"})
EVIDENCE_CLASSES = frozenset({"DOCUMENT", "DIGITAL", "BENCH", "HUMAN", "REG_CLAIM", "SUPPLIER"})
INVALIDATION_EVENTS = frozenset({"ROUTINE_CHANGED", "SCHEDULE_CHANGED", "PRODUCT_CHANGED",
    "REFORMULATION", "ASSIGNMENT_CHANGED", "DOSE_EXPIRED", "DOSE_DISTURBED",
    "CHANGEOVER_INCOMPLETE", "SERVICE_INTERRUPTED", "RESOURCE_CHANGED", "THERMAL_STATE_CHANGED",
    "FAULT", "LOCAL_PROFILE_CHANGED", "CLOCK_UNTRUSTED", "PARTIAL_DELIVERY", "HARDWARE_CHANGED"})


class CoreSketchError(ValueError):
    """Malformed concept input, not a hardware fault."""


def text(value: Any, label: str) -> str:
    return _contracts.non_empty_text(value, label, CoreSketchError)


def number(value: Any, label: str) -> float:
    return _contracts.non_negative(value, label, CoreSketchError)


def digest(value: Any) -> str:
    try:
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
            allow_nan=False).encode()).hexdigest()
    except (TypeError, ValueError) as exc:
        raise CoreSketchError("record is not finite canonical JSON") from exc


def unique(records: list[dict], key: str = "id") -> dict[str, dict]:
    if type(records) is not list:
        raise CoreSketchError("records must be a list")
    result = {}
    for record in records:
        if type(record) is not dict:
            raise CoreSketchError("record must be an object")
        ident = text(record.get(key), key)
        if ident in result:
            raise CoreSketchError(f"duplicate {key}: {ident}")
        result[ident] = record
    return result


def result(blockers: list[str], **fields: Any) -> dict:
    return {"classification": CLASSIFICATION, "hardware_execution_authorized": False,
        "model_consistent": not blockers, "blockers": sorted(set(blockers)), **fields}


def evidence_covers(required: set[str], ids: list[str], records: list[dict], scope: str) -> bool:
    """Check declared, accepted, scope-bound classes; not signature/authenticity verification."""
    by_id = unique(records)
    if type(ids) is not list or any(type(i) is not str for i in ids) or len(ids) != len(set(ids)):
        return False
    if not required or not required <= EVIDENCE_CLASSES:
        raise CoreSketchError("unknown or empty evidence requirement")
    covered = set()
    for ident in ids:
        r = by_id.get(ident, {})
        if r.get("accepted") is True and r.get("result") == "PASS" and r.get("scope") == scope:
            if r.get("class") in EVIDENCE_CLASSES:
                covered.add(r["class"])
    return required <= covered


def validate_plan(plan: dict) -> dict[str, dict]:
    digest(plan)
    if plan.get("scope") not in {"WHOLE_FACE_CONCEPTUAL", "REDUCED_REGION_SURROGATE"}:
        raise CoreSketchError("explicit spatial scope required")
    regions, stages = unique(plan.get("regions")), unique(plan.get("stages"))
    if not regions or not stages:
        raise CoreSketchError("empty region/stage plan")
    if plan["scope"] == "WHOLE_FACE_CONCEPTUAL" and set(regions) != WHOLE_FACE_REGIONS:
        raise CoreSketchError("whole-face conceptual catalog cannot silently lose regions")
    for ident, region in regions.items():
        if ident.endswith("_protected") and region.get("kind") != "PROTECTED_ANATOMY":
            raise CoreSketchError("protected region identity cannot be relabelled")
    kinds = [s.get("kind") for s in stages.values()]
    if any(k not in STAGE_ORDER for k in kinds):
        raise CoreSketchError("unknown stage kind")
    if [STAGE_ORDER[k] for k in kinds] != sorted(STAGE_ORDER[k] for k in kinds):
        raise CoreSketchError("stage order is not the selected routine order")
    if not {"CLEAN", "RINSE_RECOVER", "MOISTURISE", "SETTLE", "RELEASE"} <= set(kinds):
        raise CoreSketchError("baseline complete-routine stages missing")
    for region in regions.values():
        if region.get("kind") not in {"CONCEPTUAL_SKIN", "PROTECTED_ANATOMY"}:
            raise CoreSketchError("region kind missing")
    for s in stages.values():
        if set(s.get("regions", {})) != set(regions):
            raise CoreSketchError(f"{s['id']}: incomplete spatial obligation matrix")
        if s["kind"] in {"CLEAN", "LEAVE_ON", "MOISTURISE", "FACIAL_SPF"}:
            text(s.get("product_binding"), "product_binding")
        for ident, obligation in s["regions"].items():
            status = obligation.get("requirement")
            if regions[ident]["kind"] == "PROTECTED_ANATOMY":
                if status != "PROTECTED":
                    raise CoreSketchError("protected anatomy cannot become an application target")
            elif status not in {"REQUIRED", "EXCLUDED"}:
                raise CoreSketchError("skin obligation must be required or justified exclusion")
            if status == "EXCLUDED":
                if obligation.get("reason") not in {"PRODUCT_INTENDED_EXCLUSION", "QUALIFIED_SAFETY_EXCLUSION"}:
                    raise CoreSketchError("device-unreachable is not a legitimate exclusion reason")
                ids = obligation.get("exclusion_records")
                if type(ids) is not list or not ids:
                    raise CoreSketchError("qualified exclusion records required")
                for ident in ids:
                    text(ident, "exclusion record")
        if not any(o["requirement"] == "REQUIRED" for o in s["regions"].values()):
            raise CoreSketchError("a selected stage cannot exclude every skin region")
    return stages


def assess_completion(plan: dict, observations: dict, products: list[dict], evidence: list[dict]) -> dict:
    """No scalar coverage input is used. Every selected stage/region is evaluated."""
    stages = validate_plan(plan)
    context = digest(plan)
    profiles = unique(products)
    blockers = []
    rows = []
    if observations.get("plan_digest") != context:
        blockers.append("PLAN_BINDING_CHANGED")
    if observations.get("completed_order") != list(stages):
        blockers.append("STAGE_ORDER_OR_PROGRESS_INCOMPLETE")
    if observations.get("routine_state") != "NORMAL_RELEASE_COMPLETED":
        blockers.append("INTERRUPTED_PARTIAL_OR_RELEASE_INCOMPLETE")
    observed_stages = observations.get("stages", {})
    if set(observed_stages) != set(stages):
        blockers.append("STAGE_SET_MISMATCH")
    whole = plan["scope"] == "WHOLE_FACE_CONCEPTUAL"
    required = {"BENCH", "HUMAN"} if whole else {"BENCH"}
    if whole and not evidence_covers(required, observations.get("registration_evidence", []),
                                    evidence, context + "/whole_face_registration"):
        blockers.append("WHOLE_FACE_REGISTRATION_NOT_ESTABLISHED")
    for stage_id, stage in stages.items():
        if stage.get("product_binding"):
            p = profiles.get(stage["product_binding"], {})
            if (p.get("trust") != "VALIDATED" or p.get("context_digest") != context
                or p.get("promoted_by") in {"COMMUNITY", "AI"}):
                blockers.append(stage_id + ":UNSUPPORTED_PRODUCT_OR_CONTEXT")
        observed_regions = observed_stages.get(stage_id, {})
        if set(observed_regions) != set(stage["regions"]):
            blockers.append(stage_id + ":REGION_SET_MISMATCH")
        for region_id, obligation in stage["regions"].items():
            observed = observed_regions.get(region_id, {})
            req = obligation["requirement"]
            classes = required | ({"REG_CLAIM"} if stage["kind"] == "FACIAL_SPF" else set())
            scope = context + "/" + stage_id + "/" + region_id
            if req == "REQUIRED":
                ok = (observed.get("state") == "COMPLETE" and observed.get("uncovered_subregions") == []
                    and evidence_covers(classes, observed.get("evidence_ids", []), evidence, scope))
            elif req == "PROTECTED":
                ok = (observed.get("state") == "PROTECTED_PRESERVED"
                    and evidence_covers(classes, observed.get("evidence_ids", []), evidence, scope))
            else:
                ok = (observed.get("state") == "EXCLUDED"
                    and evidence_covers(classes, obligation["exclusion_records"], evidence, scope))
            rows.append({"stage": stage_id, "region": region_id, "obligation": req, "satisfied": ok})
            if not ok:
                blockers.append(stage_id + ":" + region_id + ":UNRESOLVED")
    return result(blockers, plan_digest=context, spatial_results=rows,
        whole_routine_complete=whole and not blockers,
        reduced_sequence_complete=(not whole and not blockers))


def assess_contacts(contacts: list[dict], required_regions: set[str], evidence: list[dict]) -> dict:
    by_id = unique(contacts)
    if set(by_id) != CONTACT_CLASSES:
        raise CoreSketchError("all face-facing contact classes must be inventoried")
    blockers = []
    for ident, c in by_id.items():
        if set(c.get("states", {})) != set(PHASES):
            raise CoreSketchError(ident + ": missing phase state")
        if c.get("presence") == "PROVED_ABSENT":
            if not evidence_covers({"DIGITAL"}, c.get("absence_evidence", []), evidence, digest(c["source_binding"])):
                blockers.append(ident + ":ABSENCE_UNPROVED")
            continue
        if c.get("presence") != "INVENTORIED" or not c.get("instance_ids"):
            blockers.append(ident + ":INSTANCE_INVENTORY_UNRESOLVED")
        footprint = c.get("affected_regions")
        if footprint is None:
            blockers.append(ident + ":FOOTPRINT_UNRESOLVED")
            footprint = list(required_regions)
        if not set(footprint) <= required_regions:
            raise CoreSketchError("contact footprint outside declared conceptual skin domain")
        for phase in PHASES:
            state = c["states"][phase]
            if state not in {"CLEAR", "CONTACT", "OCCLUDING", "TRANSFER", "UNKNOWN"}:
                raise CoreSketchError("unknown contact state")
            if state == "UNKNOWN":
                blockers.append(ident + ":" + phase + ":UNKNOWN")
        for region in footprint:
            strategy = c.get("coverage_strategies", {}).get(region, {})
            # A named concept alone is not a trajectory, support path or film proof.
            if not all(strategy.get(k) for k in ("uncover_phase", "application_phase", "support_path", "normal_release_path")):
                blockers.append(ident + ":" + region + ":NO_COMPLETE_TRANSFER_STRATEGY")
            uncover, application = strategy.get("uncover_phase"), strategy.get("application_phase")
            if (uncover not in PHASES or application != "LEAVE_ON"
                or PHASES.index(uncover) > PHASES.index("LEAVE_ON")):
                blockers.append(ident + ":" + region + ":INVALID_TRANSFER_ORDER")
            scope = digest({"source": c.get("source_binding"), "region": region, "strategy": strategy})
            if not evidence_covers({"DIGITAL", "BENCH"}, strategy.get("evidence_ids", []), evidence, scope):
                blockers.append(ident + ":" + region + ":SWEEP_OR_FILM_PROOF_MISSING")
        if c["states"]["RELEASE"] not in {"CLEAR", "TRANSFER"}:
            blockers.append(ident + ":RELEASE_STILL_BLOCKING")
    return result(blockers, contact_classes=len(by_id))


def invalidate(session: dict, event: str) -> dict:
    if event not in INVALIDATION_EVENTS:
        raise CoreSketchError("unknown invalidation event")
    updated = deepcopy(session)
    epoch = updated.get("epoch")
    if type(epoch) is not int or epoch < 0:
        raise CoreSketchError("epoch must be a nonnegative integer")
    updated["epoch"] = epoch + 1
    updated.setdefault("invalidations", []).append(event)
    updated.pop("cached_ready", None)
    return updated


def assess_readiness(request: dict, receipt: dict, current: dict, now_s: float) -> dict:
    """Recompute; never consume cached READY, internet state or an AI prediction."""
    digest([request, receipt, current])
    now = number(now_s, "now_s")
    blockers = []
    binding = request.get("binding", {})
    stages = validate_plan(request.get("plan", {}))
    fields = {"routine_id", "routine_revision", "schedule_context", "stage_ids", "product_bindings", "plan_digest",
              "hardware_revision", "profile_revision", "authority_digest"}
    if set(binding) != fields or not binding["stage_ids"]:
        raise CoreSketchError("incomplete execution binding")
    for key in fields - {"stage_ids", "product_bindings"}:
        text(binding[key], key)
    if len(set(binding["stage_ids"])) != len(binding["stage_ids"]):
        raise CoreSketchError("duplicate stage in readiness binding")
    if binding['plan_digest'] != digest(request['plan']) or binding['stage_ids'] != list(stages):
        blockers.append('ACTUAL_ROUTINE_PLAN_CHANGED')
    eligibility = current.get('stage_eligibility', {})
    if set(eligibility) != set(stages) or any(s != 'ELIGIBLE_FOR_EXACT_PLAN' for s in eligibility.values()):
        blockers.append('REQUIRED_STAGE_UNAVAILABLE_OR_UNSUPPORTED')
    if current.get("binding") != binding or receipt.get("binding_digest") != digest(binding):
        blockers.append("EXECUTION_BINDING_CHANGED")
    if receipt.get("dose_digest") != digest(current.get("doses")):
        blockers.append("PREPARED_DOSE_CONTENTS_CHANGED")
    if receipt.get("request_digest") != digest(request):
        blockers.append("EXECUTION_REQUIREMENTS_CHANGED")
    for field in ("service", "products", "resources", "stage_eligibility"):
        if receipt.get(field + "_digest") != digest(current.get(field)):
            blockers.append(field.upper() + "_OBSERVATION_CHANGED")
    if type(current.get("epoch")) is not int or current["epoch"] < 0:
        raise CoreSketchError("current epoch invalid")
    if receipt.get("epoch") != current["epoch"] or current.get("invalidations") != []:
        blockers.append("PREPARATION_INVALIDATED")
    for key in ("prepared_at_s", "expires_at_s", "observations_expire_at_s"):
        if receipt.get(key) is None:
            blockers.append(key + ":UNKNOWN")
        else:
            number(receipt[key], key)
    start, end, fresh = (receipt.get(k) for k in ("prepared_at_s", "expires_at_s", "observations_expire_at_s"))
    if None not in (start, end, fresh) and not start <= now < min(end, fresh):
        blockers.append("PREPARATION_OR_OBSERVATIONS_EXPIRED")
    if current.get("faults") != []:
        blockers.append("FAULT_OR_FAULT_STATE_UNKNOWN")
    required_local = {"clock_valid", "profile_cache_verified", "progress_known", "controller_available"}
    if any(current.get("local", {}).get(k) is not True for k in required_local):
        blockers.append("LOCAL_EXECUTION_STATE_INCOMPLETE")
    for task in ("cleaning", "changeover", "dry_path_service"):
        if current.get("service", {}).get(task) != "VERIFIED_COMPLETE" or not receipt.get("service_receipt_id"):
            blockers.append(task + ":SERVICE_INCOMPLETE")
    required = request.get("resources", {})
    if type(request.get("thermal_stage")) is not bool:
        raise CoreSketchError("thermal selection must be explicit")
    if not {"water_ml", "waste_free_ml", "usable_energy_Wh"} <= set(required):
        raise CoreSketchError("water/waste/energy requirements missing")
    if request.get("thermal_stage") is True and "thermal_available_J" not in required:
        raise CoreSketchError("scheduled thermal resource missing")
    for key, needed in required.items():
        available = current.get("resources", {}).get(key)
        if needed is None or available is None:
            blockers.append(key + ":RESOURCE_UNKNOWN")
        elif number(available, key) < number(needed, key):
            blockers.append(key + ":RESOURCE_INSUFFICIENT")
    expected_products = unique(binding["product_bindings"])
    if not expected_products:
        raise CoreSketchError("complete routine needs explicit product bindings")
    if set(expected_products) != {s['product_binding'] for s in stages.values() if s.get('product_binding')}:
        blockers.append('PRODUCT_SET_DOES_NOT_EXECUTE_PLAN')
    profiles = unique(current.get("products", []))
    doses = unique(current.get("doses", []), "product_binding")
    unique(current.get("doses", []), "dose_id")
    unique(binding["product_bindings"], "slot")
    demands = request.get("dose_requirements", {})
    if set(expected_products) != set(doses) or set(expected_products) != set(demands):
        blockers.append("PREPARED_PRODUCT_SET_MISMATCH")
    for ident, expected in expected_products.items():
        for key in ("sku", "market", "identity_version", "slot"):
            text(expected.get(key), key)
        p, d = profiles.get(ident, {}), doses.get(ident, {})
        if (p.get("binding") != expected or p.get("trust") != "VALIDATED"
            or p.get("context_digest") != digest(binding) or p.get("identity_status") != "RESOLVED"
            or p.get("promoted_by") in {"COMMUNITY", "AI"}):
            blockers.append(ident + ":PRODUCT_OR_PROFILE_UNSUPPORTED")
        if (d.get("binding") != expected or d.get("state") != "SEALED_PREPARED"
            or not d.get("dose_id") or d.get("preservation") != "VERIFIED"):
            blockers.append(ident + ":DOSE_IDENTITY_OR_PRESERVATION_INVALID")
        if d.get("expires_at_s") is None or now >= number(d["expires_at_s"], "dose expiry"):
            blockers.append(ident + ":DOSE_AGE_UNKNOWN_OR_EXPIRED")
        demand = demands.get(ident, {})
        values = (d.get("quantity_ml"), demand.get("min_ml"), demand.get("max_ml"))
        if None in values:
            blockers.append(ident + ":QUANTITY_UNKNOWN")
        else:
            qty, lo, hi = (number(v, "dose quantity") for v in values)
            if not lo <= qty <= hi:
                blockers.append(ident + ":QUANTITY_OUTSIDE_PROFILE")
    prepared = not blockers
    start_ready = prepared and current.get("wear_state") == "CONFIRMED_ELIGIBLE"
    return result(blockers, prepared_ready=prepared, start_ready=start_ready,
        evaluated_binding_digest=digest(binding), evaluated_epoch=current["epoch"])


def assess_integrity(products: list[dict], paths: list[dict], evidence: list[dict], context: str) -> dict:
    """Product identity, physical behavior, preservation and application stay separate."""
    ps, routes = unique(products), unique(paths)
    if not ps or not routes:
        raise CoreSketchError("product/contact-path inventory cannot be empty")
    blockers = []
    uses: dict[str, set[str]] = {}
    for ident, p in ps.items():
        for key in ("identity", "behavior", "compatibility", "contamination", "application"):
            if not isinstance(p.get(key), dict):
                raise CoreSketchError("five independent product integrity records required")
        if p["identity"].get("status") != "RESOLVED":
            blockers.append(ident + ":IDENTITY_UNKNOWN")
        if p["behavior"].get("state") != "CHARACTERISED" or not p["behavior"].get("profile_binding"):
            blockers.append(ident + ":FLOW_BEHAVIOR_UNKNOWN")
        if p["application"].get("trust") != "VALIDATED" or p["application"].get("promoted_by") in {"COMMUNITY", "AI"}:
            blockers.append(ident + ":APPLICATION_UNSUPPORTED")
        if p["compatibility"].get("state") != "PRESERVATION_VERIFIED" or p["contamination"].get("state") != "VERIFIED_CLEAN":
            blockers.append(ident + ":PRESERVATION_OR_CHANGEOVER_UNPROVED")
        if not evidence_covers({"BENCH", "SUPPLIER"}, p.get("evidence_ids", []), evidence, context + "/" + ident):
            blockers.append(ident + ":INTEGRITY_EVIDENCE_MISSING")
    routed_products = set()
    for ident, route in routes.items():
        product = route.get("product")
        if product not in ps:
            raise CoreSketchError("route refers to unknown product")
        routed_products.add(product)
        nodes = route.get("nodes", [])
        if len(nodes) < 2 or len(nodes) != len(set(nodes)):
            raise CoreSketchError("route must declare a non-cyclic complete path")
        for n in nodes:
            text(n, "path node")
            uses.setdefault(n, set()).add(product)
        if route.get("dead_volume_ml") is None:
            blockers.append(ident + ":DEAD_VOLUME_UNKNOWN")
        else:
            number(route["dead_volume_ml"], "dead volume")
        if route.get("kind") not in {"DELIVERY", "SERVICE", "MIXED_WASTE"}:
            raise CoreSketchError("unknown route role")
        if route["kind"] == "MIXED_WASTE" and "PASSIVE_MIXED_WASTE_BARRIER" not in nodes[1:-1]:
            blockers.append(ident + ":PASSIVE_BARRIER_BYPASSED")
        if route.get("source_binding_verified") is not True:
            blockers.append(ident + ":PATH_SOURCE_OR_BACKFLOW_PROOF_MISSING")
    if routed_products != set(ps):
        blockers.append("PRODUCT_PATH_INVENTORY_INCOMPLETE")
    for node, products_at_node in uses.items():
        if len(products_at_node) > 1:
            for first in products_at_node:
                for second in products_at_node - {first}:
                    scope = context + "/carryover/" + node + "/" + first + "/" + second
                    ids = [e["id"] for e in evidence if e.get("scope") == scope]
                    if not evidence_covers({"BENCH"}, ids, evidence, scope):
                        blockers.append(node + ":" + first + "->" + second + ":CARRYOVER_UNPROVED")
    return result(blockers)


def backlog_p0_ids(content: str) -> set[str]:
    sections = re.split(r"(?=^## CS-)", content, flags=re.M)
    return {re.match(r"## (CS-\d{3})", s).group(1) for s in sections
            if re.match(r"## CS-\d{3}", s) and re.search(r"\*\*Priority:\*\* P0\b", s)}


def validate_convergence(manifest: dict, backlog: str) -> dict:
    digest(manifest)
    if manifest.get("classification") != CLASSIFICATION or manifest.get("hardware_execution_authorized") is not False:
        raise CoreSketchError("concept manifest cannot authorize hardware")
    items, interfaces = unique(manifest.get("p0_items")), unique(manifest.get("interfaces"))
    if set(items) != backlog_p0_ids(backlog):
        raise CoreSketchError("P0 manifest/backlog membership drift")
    all_ids = set(re.findall(r"^## (CS-\d{3})\b", backlog, re.M))
    for ident, interface in interfaces.items():
        writer = interface.get("writing_owner")
        text(writer, "single writing_owner")
        if type(interface.get("lane")) is not int or interface["lane"] not in range(1, 6):
            raise CoreSketchError("invalid interface lane")
    owned_paths = {}
    for interface in interfaces.values():
        for path in interface.get("contract_paths", []):
            if path in owned_paths and owned_paths[path] != interface["writing_owner"]:
                raise CoreSketchError("shared interface has two writing owners")
            owned_paths[path] = interface["writing_owner"]
    for ident, item in items.items():
        if type(item.get("lane")) is not int or item["lane"] not in range(1, 6):
            raise CoreSketchError("P0 lane must be one of five")
        text(item.get("writing_owner"), "writing_owner")
        if item.get("priority") != "P0" or item.get("state") not in {"LOCKED", "SELECTED", "PROVE", "EXPLORE", "INTEGRATE", "BLOCKED", "REJECTED", "CLOSED"}:
            raise CoreSketchError("invalid P0 state")
        if type(item.get("digitally_actionable")) is not bool:
            raise CoreSketchError("digitally_actionable must be explicit bool")
        if not set(item.get("dependencies", [])) <= all_ids:
            raise CoreSketchError("dangling P0 dependency")
        required = set(item.get("evidence_required", []))
        if not required or not required <= EVIDENCE_CLASSES:
            raise CoreSketchError("missing evidence classes")
        if item.get("requires") != {k: k in required for k in ("BENCH", "HUMAN", "REG_CLAIM", "SUPPLIER")}:
            raise CoreSketchError("physical evidence flags disagree with requirements")
        text(item.get("promotion_condition"), "promotion_condition")
        if item["state"] != "CLOSED":
            text(item.get("blocker"), "blocker")
        elif not evidence_covers(required, item.get("accepted_evidence", []), manifest.get("evidence", []), ident):
            raise CoreSketchError("physical proof cannot be closed by docs/CAD/CI")
        if item.get("physical_validation") == "VALIDATED":
            if not evidence_covers(required | {"BENCH"}, item.get("accepted_evidence", []), manifest.get("evidence", []), ident):
                raise CoreSketchError("subsystem CI cannot promote physical validation")
    return result([], p0_count=len(items), interface_count=len(interfaces))


def load_manifest(root: Path) -> dict:
    return json.loads((root / "docs/contracts/core_sketch_convergence.json").read_text())


def main() -> None:
    """Emit reproducible concept screens, never a product readiness certificate."""
    import argparse
    from .authority import load_authority
    from .core_sketch_resources import assess_resources
    from .core_sketch_trial import assess_trial
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--trial', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = load_manifest(root)
    authority = load_authority(root / 'config/masck_one_authority.yaml')
    integrity = validate_convergence(manifest, (root / 'docs/CORE_SKETCH_EXECUTION_BACKLOG.md').read_text())
    report = {'contract_integrity': integrity,
        'product_completion': 'BLOCKED_PHYSICAL_PROOF_AND_UNRESOLVED_INTERFACES',
        'resources': [assess_resources(authority, s) for s in manifest['resources']['scenarios']],
        'contacts': assess_contacts(manifest['contact']['classes'],
            {r['id'] for r in manifest['completion']['region_catalog'] if r['kind'] == 'CONCEPTUAL_SKIN'}, []),
        'source_sha256': {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in (
            'config/masck_one_authority.yaml', 'docs/contracts/core_sketch_convergence.json',
            'src/masck_one/core_sketch_contracts.py', 'src/masck_one/core_sketch_resources.py',
            'src/masck_one/core_sketch_trial.py', 'src/masck_one/mass_balance.py',
            'docs/CORE_SKETCH_EXECUTION_BACKLOG.md')}}
    if args.trial:
        report['trial'] = assess_trial(json.loads((root / 'docs/contracts/reduced_region_protocol.json').read_text()),
                                      json.loads(args.trial.read_text()))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'core_sketch_screen.json').write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print('Contract logic consistent; product feasibility remains BLOCKED. Output: ' + str(args.output))


if __name__ == '__main__':
    main()
