"""Host orchestration of existing preparation, resource and offline contracts.

The pipeline recomputes producers from declared source records. Its receipt is
an internally bound host snapshot, not an observed dock preparation or a device
command. Neither ordered software reports nor an admissible reported-state
completion claim establish physical execution. Hashes detect accidental drift;
they do not authenticate evidence or an untrusted writer.
"""
from __future__ import annotations

from copy import deepcopy

from .authority import Authority
from .core_sketch_contracts import (
    CoreSketchError, assess_completion, assess_readiness, digest, number, result,
    text, validate_plan,
)
from .dock_preparation import derive_session_doses
from .offline_session import (
    interrupt_session, plan_session, record_intent, record_stage_report,
    validate_journal,
)
from .product_lifecycle import APPLICATION_CLASSES, session_product_records
from .session_resource_binding import assess_session_resources

SCHEMA_VERSION = "1.0.0"
EVIDENCE_STATUS = "HOST_SESSION_ORCHESTRATION_NOT_PHYSICAL_EXECUTION"


def _object(value: object, name: str) -> dict:
    if type(value) is not dict:
        raise CoreSketchError(name + " must be an object")
    return value


def _seal(value: dict) -> dict:
    value["pipeline_digest"] = digest({k: v for k, v in value.items() if k != "pipeline_digest"})
    return value


def validate_pipeline(pipeline: dict) -> dict:
    """Validate stored host context before any operation; not authentication."""
    _object(pipeline, "pipeline")
    if pipeline.get("schema_version") != SCHEMA_VERSION:
        raise CoreSketchError("unsupported session pipeline schema")
    if pipeline.get("pipeline_digest") != digest({k: v for k, v in pipeline.items() if k != "pipeline_digest"}):
        raise CoreSketchError("session pipeline contents changed")
    if pipeline.get("hardware_execution_authorized") is not False or pipeline.get("physical_routine_complete") is not False:
        raise CoreSketchError("host pipeline may not authorize physical execution")
    journal = validate_journal(pipeline.get("journal"))
    for field in ("request", "receipt", "manifest"):
        if journal[field + "_digest"] != digest(pipeline.get(field)):
            raise CoreSketchError("pipeline context differs from journal " + field)
    text(pipeline.get("source_digest"), "source_digest")
    number(pipeline.get("prepared_at_s"), "prepared_at_s")
    return deepcopy(pipeline)


def _produce(authority: Authority, source: dict, prepared_at_s: float) -> dict:
    _object(source, "source")
    digest(source)
    for field in ("request", "demands", "resource_scenario", "electrical_envelope", "current", "preparation", "manifest", "cache"):
        _object(source.get(field), field)
    for field in ("reservoirs", "products", "product_evidence"):
        if type(source.get(field)) is not list:
            raise CoreSketchError(field + " must be a list")
    request = deepcopy(_object(source.get("request"), "request"))
    plan, binding = request.get("plan"), request.get("binding")
    _object(request.get("dose_requirements"), "dose_requirements")
    stages = validate_plan(_object(plan, "plan"))
    _object(binding, "binding")
    applications = {}
    for stage in stages.values():
        if stage["kind"] in APPLICATION_CLASSES:
            ident = stage["product_binding"]
            if ident in applications and applications[ident] != stage["kind"]:
                raise CoreSketchError("each product binding must have one exact application class")
            applications[ident] = stage["kind"]
    demands = _object(source.get("demands"), "demands")
    if set(demands) != set(applications):
        raise CoreSketchError("demands must exactly cover selected applications")
    for ident, application in applications.items():
        demand = _object(demands[ident], "dose demand")
        if demand.get("application") != application:
            raise CoreSketchError("dose application differs from selected stage")
        window = request.get("dose_requirements", {}).get(ident)
        if window != {k: demand.get(k) for k in ("min_ml", "max_ml")}:
            raise CoreSketchError("preparation demand and execution dose window differ")
    products = session_product_records(binding, source.get("products"), source.get("product_evidence"),
        source.get("product_context"), applications)
    doses = derive_session_doses(demands, source.get("reservoirs"), binding, prepared_at_s)
    resources = assess_session_resources(authority, plan=plan, binding=binding,
        dose_result=doses, reservoirs=source.get("reservoirs"),
        scenario=source.get("resource_scenario"), electrical_envelope=source.get("electrical_envelope"))
    blockers = products["blockers"] + doses["blockers"] + resources["blockers"]
    if resources.get("whole_product_closed") is not True:
        blockers += resources["resource_report"]["blockers"] + ["WHOLE_PRODUCT_RESOURCE_ENVELOPE_UNCLOSED"]
    if request.get("thermal_stage") is not resources["thermal_selected"]:
        blockers.append("THERMAL_SELECTION_DIFFERS_FROM_RESOURCE_SCENARIO")
    request["resources"] = deepcopy(resources["readiness_requirements"])
    current = deepcopy(_object(source.get("current"), "current observations"))
    available = _object(current.get("resources"), "available resources")
    water = available.get("water_ml")
    if water is not None:
        water = number(water, "available water")
        charge = resources["resource_report"]["bounds"]["prepared_water_charge_ml"]["high"]
        if water > authority.number("fluid", "water_reservoir", "gross_mL") or charge is not None and water > charge:
            blockers.append("AVAILABLE_WATER_EXCEEDS_PREPARED_INVENTORY")
    battery = source["resource_scenario"].get("inputs", {}).get("usable_battery_energy_Wh")
    if battery is not None and available.get("usable_energy_Wh") != battery:
        blockers.append("AVAILABLE_ENERGY_DIFFERS_FROM_RESOURCE_SCENARIO")
    # Derived records replace every caller-supplied cached product/dose claim.
    current["products"], current["doses"] = products["products"], doses["prepared_doses"]
    preparation = _object(source.get("preparation"), "preparation")
    receipt = {"epoch": current.get("epoch"), "binding_digest": digest(binding),
        "dose_digest": digest(current["doses"]), "request_digest": digest(request),
        "prepared_at_s": prepared_at_s,
        "expires_at_s": preparation.get("expires_at_s"),
        "observations_expire_at_s": preparation.get("observations_expire_at_s"),
        "service_receipt_id": preparation.get("service_receipt_id")}
    for field in ("service", "products", "resources", "stage_eligibility"):
        receipt[field + "_digest"] = digest(current.get(field))
    return dict(request=request, receipt=receipt, current=current, dose_result=doses,
        product_result=products, resource_result=resources, producer_blockers=sorted(set(blockers)))


def prepare_session(authority: Authority, session_id: str, source: dict, *, now_s: float,
                    network_reachable: bool) -> dict:
    """Bind a host session to current producer outputs and local control cache."""
    now = number(now_s, "now_s")
    values = _produce(authority, source, now)
    journal = plan_session(session_id, values["request"], values["receipt"], values["current"],
        source.get("manifest"), source.get("cache"), now_s=now, network_reachable=network_reachable,
        preparation_blockers=values["producer_blockers"])
    readiness = assess_readiness(values["request"], values["receipt"], values["current"], now)
    blockers = values["producer_blockers"] + journal["blockers"]
    return _seal(result(blockers, schema_version=SCHEMA_VERSION, evidence_status=EVIDENCE_STATUS,
        physical_routine_complete=False, source_digest=digest(source), prepared_at_s=now,
        whole_product_resource_closed=values["resource_result"].get("whole_product_closed") is True,
        model_start_ready=not blockers and readiness["start_ready"],
        manifest=deepcopy(source["manifest"]), cache=deepcopy(source["cache"]),
        readiness=readiness, journal=journal, **values))


def _recheck(authority: Authority, pipeline: dict, source: dict, now_s: float) -> tuple[dict, list[str]]:
    values = _produce(authority, source, pipeline["prepared_at_s"])
    blockers = list(values["producer_blockers"])
    if digest(source) != pipeline["source_digest"]:
        blockers.append("SOURCE_CHANGED_AFTER_PREPARATION")
    for field in ("request", "receipt", "current"):
        if digest(values[field]) != digest(pipeline[field]):
            blockers.append(field.upper() + "_CHANGED_AFTER_PREPARATION")
    readiness = assess_readiness(values["request"], pipeline["receipt"], values["current"], now_s)
    blockers += readiness["blockers"]
    if not readiness["start_ready"]:
        blockers.append("START_PRECONDITIONS_NOT_SATISFIED")
    return values, sorted(set(blockers))


def _updated(pipeline: dict, journal: dict, blockers: list[str]) -> dict:
    pipeline.update(journal=journal, blockers=sorted(set(blockers + journal["blockers"])),
        model_consistent=not blockers and journal["model_consistent"],
        model_start_ready=not blockers and journal["state"] == "PLANNED" and journal["model_consistent"])
    return _seal(pipeline)


def record_session_intent(authority: Authority, pipeline: dict, source: dict, stage_id: str, *,
                          now_s: float, network_reachable: bool) -> dict:
    """Recompute live inputs before recording the next host-only stage intent."""
    out = validate_pipeline(pipeline)
    values, blockers = _recheck(authority, out, source, now_s)
    if blockers:
        return _updated(out, interrupt_session(out["journal"], reason="LIVE_PREPARATION_INVALID"), blockers)
    journal = record_intent(out["journal"], stage_id, values["request"], out["receipt"],
        values["current"], source["manifest"], source["cache"], now_s=now_s,
        network_reachable=network_reachable)
    return _updated(out, journal, [])


def record_session_report(authority: Authority, pipeline: dict, source: dict, stage_id: str, *,
                          report_id: str, now_s: float, network_reachable: bool) -> dict:
    """Record a software report only while its prepared context remains current."""
    out = validate_pipeline(pipeline)
    _, blockers = _recheck(authority, out, source, now_s)
    # Re-use offline gates without dispatching or fabricating a new intent.
    checked = plan_session(out["journal"]["session_id"], out["request"], out["receipt"], out["current"],
        source["manifest"], source["cache"], now_s=now_s, network_reachable=network_reachable)
    blockers += checked["blockers"]
    if blockers:
        return _updated(out, interrupt_session(out["journal"], reason="LIVE_PREPARATION_INVALID"), blockers)
    return _updated(out, record_stage_report(out["journal"], stage_id, report_id=report_id, now_s=now_s), [])


def interrupt_pipeline(pipeline: dict, *, reason: str) -> dict:
    out = validate_pipeline(pipeline)
    return _updated(out, interrupt_session(out["journal"], reason=reason), out["blockers"])


def restore_pipeline(pipeline: dict, restored_journal: dict) -> dict:
    """Attach a durably restored journal to its original prepared host context.

    The journal store owns the trusted cursor. This function does not recover an
    old pipeline or prove that its records were durably committed.
    """
    out, restored = validate_pipeline(pipeline), validate_journal(restored_journal)
    old = out["journal"]
    for field in ("session_id", "request_digest", "receipt_digest", "manifest_digest", "stage_ids"):
        if restored[field] != old[field]:
            raise CoreSketchError("restored journal belongs to another prepared context")
    if restored["revision"] < old["revision"]:
        raise CoreSketchError("restored journal rolls back pipeline progress")
    if restored["revision"] == old["revision"] and restored != old:
        raise CoreSketchError("equal journal revision cannot change pipeline progress")
    previous = old["reported_stage_ids"]
    if restored["reported_stage_ids"][:len(previous)] != previous:
        raise CoreSketchError("restored journal rolls back reported stage prefix")
    if old["state"] == "SERVICE_REQUIRED" and restored["state"] != "SERVICE_REQUIRED":
        raise CoreSketchError("service latch cannot be cleared by restore")
    out = _updated(out, restored, out["producer_blockers"])
    # A stored PLANNED state is not a fresh readiness evaluation. The next
    # intent must recompute against live source/time before showing ready.
    out["model_start_ready"] = False
    return _seal(out)


def assess_session_completion(authority: Authority, pipeline: dict, source: dict,
                              observations: dict, evidence: list[dict], *, now_s: float,
                              network_reachable: bool) -> dict:
    """Assess independently supplied region evidence; never infer it from reports."""
    out = validate_pipeline(pipeline)
    values, blockers = _recheck(authority, out, source, now_s)
    checked = plan_session(out["journal"]["session_id"], out["request"], out["receipt"], values["current"],
        source["manifest"], source["cache"], now_s=now_s, network_reachable=network_reachable)
    blockers += checked["blockers"]
    if out["journal"]["state"] != "REPORT_SEQUENCE_FINISHED":
        blockers.append("REPORT_SEQUENCE_NOT_FINISHED")
    _object(observations, "completion observations")
    for field, expected in (("session_id", out["journal"]["session_id"]),
                            ("source_digest", out["source_digest"]),
                            ("receipt_digest", digest(out["receipt"]))):
        if observations.get(field) != expected:
            blockers.append("COMPLETION_" + field.upper() + "_MISMATCH")
    # Product trust is recomputed above for the exact execution binding, then
    # projected to the same selected plan required by the completion consumer.
    products = deepcopy(values["product_result"]["products"])
    for product in products:
        product["execution_context_digest"] = product["context_digest"]
        product["context_digest"] = digest(out["request"]["plan"])
    assessment = assess_completion(out["request"]["plan"], deepcopy(observations), products, deepcopy(evidence))
    blockers += assessment["blockers"]
    return result(blockers, evidence_status=EVIDENCE_STATUS, physical_routine_complete=False,
        scope=out["request"]["plan"]["scope"],
        completion_claim_admissible=not blockers, completion_assessment=assessment,
        journal_state=out["journal"]["state"], source_digest=digest(source))
