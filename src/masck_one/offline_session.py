"""Versioned host-only journal for CS-016 interruption and offline start checks.

No command is sent to hardware. A persisted intent is uncertain after restart,
not proof of delivery and never permission to retry. Digests detect accidental
record/context changes; they are not signatures or proof of durable storage.
The actual controller/HMI and physical completion predicate remain separate.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .core_sketch_contracts import (
    CLASSIFICATION, CoreSketchError, assess_readiness, digest, number, result, text,
)
from .routine_schedule import assess_offline_execution

SCHEMA_VERSION = "1.0.0"
EVIDENCE_STATUS = "VERIFIED_HOST_JOURNAL_LOGIC_NOT_PHYSICAL_EXECUTION"
STATES = frozenset({"PLANNED", "INTENT_RECORDED", "REPORT_SEQUENCE_FINISHED", "SERVICE_REQUIRED"})


def _seal(record: dict) -> dict:
    record["journal_digest"] = digest({k: v for k, v in record.items() if k != "journal_digest"})
    return record


def validate_journal(record: dict) -> dict:
    """Validate a restored journal before considering any transition."""
    if not isinstance(record, dict) or record.get("schema_version") != SCHEMA_VERSION:
        raise CoreSketchError("unsupported offline journal schema")
    digest(record)
    if record.get("journal_digest") != digest({k: v for k, v in record.items() if k != "journal_digest"}):
        raise CoreSketchError("offline journal contents changed")
    if (record.get("classification") != CLASSIFICATION
        or record.get("hardware_execution_authorized") is not False
        or record.get("physical_routine_complete") is not False):
        raise CoreSketchError("host journal may not authorize hardware or physical completion")
    if record.get("state") not in STATES:
        raise CoreSketchError("unknown offline journal state")
    for field in ("session_id", "request_digest", "receipt_digest", "manifest_digest"):
        text(record.get(field), field)
    ids, reported = record.get("stage_ids"), record.get("reported_stage_ids")
    if (type(ids) is not list or not ids or any(type(s) is not str or not s for s in ids)
        or len(ids) != len(set(ids)) or type(reported) is not list or reported != ids[:len(reported)]):
        raise CoreSketchError("journal progress must be a unique ordered stage prefix")
    pending = record.get("pending_stage_id")
    expected = ids[len(reported)] if len(reported) < len(ids) else None
    if record["state"] == "INTENT_RECORDED" and (pending is None or pending != expected):
        raise CoreSketchError("pending intent must name the next stage")
    if record["state"] != "INTENT_RECORDED" and pending is not None:
        raise CoreSketchError("inactive journal may not carry a pending intent")
    if (record["state"] == "REPORT_SEQUENCE_FINISHED") != (len(reported) == len(ids)) and record["state"] != "SERVICE_REQUIRED":
        raise CoreSketchError("journal finish state contradicts progress")
    number(record.get("last_time_s"), "last_time_s")
    if type(record.get("revision")) is not int or record["revision"] < 0:
        raise CoreSketchError("journal revision invalid")
    if type(record.get("blockers")) is not list or any(type(b) is not str for b in record["blockers"]):
        raise CoreSketchError("journal blockers invalid")
    reports = record.get("stage_report_ids")
    if (type(reports) is not list or len(reports) != len(reported)
        or any(type(r) is not str or not r for r in reports) or len(reports) != len(set(reports))):
        raise CoreSketchError("each reported stage requires a unique software report")
    if record.get("uncertain_stage_id") is not None and record["state"] != "SERVICE_REQUIRED":
        raise CoreSketchError("uncertain progress cannot resume")
    return deepcopy(record)


def _gates(request: dict, receipt: dict, current: dict, manifest: dict, cache: dict,
           now_s: float, network_reachable: bool) -> list[str]:
    readiness = assess_readiness(request, receipt, current, now_s)
    offline = assess_offline_execution(manifest, cache, network_reachable)
    blockers = list(readiness["blockers"]) + list(offline["blockers"])
    if not readiness["start_ready"]:
        blockers.append("START_PRECONDITIONS_NOT_SATISFIED")
    binding = request["binding"]
    if (manifest.get("routine_id") != binding["routine_id"]
        or manifest.get("routine_revision") != binding["routine_revision"]
        or manifest.get("context") != binding["schedule_context"]):
        blockers.append("OFFLINE_MANIFEST_SESSION_MISMATCH")
    # Equality between cache and manifest alone does not establish applicability:
    # both can be identically stale relative to the execution binding.
    entries = manifest["entries"]
    for key in ("routine_revision", "profile_revision", "hardware_revision", "authority_digest"):
        resident = entries[key]
        if isinstance(resident, dict):
            resident = resident.get("digest" if key == "authority_digest" else "revision")
        if type(resident) is not str or not resident or resident != binding[key]:
            blockers.append(key + ":NOT_BOUND_TO_EXECUTION")
    for key, field, expected in (
        ("stage_parameters", "plan_digest", binding["plan_digest"]),
        ("dose_windows", "dose_requirements_digest", digest(request["dose_requirements"])),
        ("protected_region_map", "plan_digest", binding["plan_digest"]),
        ("fault_response_table", "hardware_revision", binding["hardware_revision"]),
        ("fault_response_table", "authority_digest", binding["authority_digest"]),
    ):
        if not isinstance(entries[key], dict) or entries[key].get(field) != expected:
            blockers.append(key + ":" + field + ":NOT_BOUND_TO_EXECUTION")
    return sorted(set(blockers))


def plan_session(session_id: str, request: dict, receipt: dict, current: dict,
                 manifest: dict, cache: dict, *, now_s: float,
                 network_reachable: bool) -> dict:
    """Build a local simulation journal only after current readiness checks."""
    session_id = text(session_id, "session_id")
    blockers = _gates(request, receipt, current, manifest, cache, now_s, network_reachable)
    return _seal(result(blockers, schema_version=SCHEMA_VERSION, session_id=session_id,
        state="SERVICE_REQUIRED" if blockers else "PLANNED", revision=0,
        request_digest=digest(request), receipt_digest=digest(receipt), manifest_digest=digest(manifest),
        stage_ids=list(request["binding"]["stage_ids"]), reported_stage_ids=[], stage_report_ids=[], pending_stage_id=None,
        last_time_s=number(now_s, "now_s"), physical_routine_complete=False,
        evidence_status=EVIDENCE_STATUS))


def record_intent(journal: dict, stage_id: str, request: dict, receipt: dict,
                  current: dict, manifest: dict, cache: dict, *, now_s: float,
                  network_reachable: bool) -> dict:
    """Record the next simulated action before its report; recheck every gate.

    An adapter must durably persist this returned intent before any future
    separately authorized controller dispatch. This module supplies no adapter.
    """
    out = validate_journal(journal)
    if out["state"] != "PLANNED":
        raise CoreSketchError("only a planned session can record a new intent")
    if stage_id != out["stage_ids"][len(out["reported_stage_ids"])]:
        raise CoreSketchError("cannot skip, reorder or replay a stage")
    now = number(now_s, "now_s")
    blockers = _gates(request, receipt, current, manifest, cache, now, network_reachable)
    for name, value in (("request", request), ("receipt", receipt), ("manifest", manifest)):
        if digest(value) != out[name + "_digest"]:
            blockers.append(name.upper() + "_CHANGED_AFTER_PLAN")
    if now < out["last_time_s"]:
        blockers.append("CLOCK_ROLLBACK")
    out.update(state="SERVICE_REQUIRED" if blockers else "INTENT_RECORDED",
               pending_stage_id=None if blockers else stage_id, blockers=sorted(set(blockers)),
               model_consistent=not blockers, revision=out["revision"] + 1, last_time_s=now)
    return _seal(out)


def record_stage_report(journal: dict, stage_id: str, *, report_id: str, now_s: float) -> dict:
    """Record an ordered software report. This never proves deposition/coverage."""
    out = validate_journal(journal)
    if out["state"] != "INTENT_RECORDED" or stage_id != out["pending_stage_id"]:
        raise CoreSketchError("report does not match the outstanding intent")
    text(report_id, "report_id")
    if report_id in out["stage_report_ids"]:
        raise CoreSketchError("cannot reuse a software report for another stage")
    now = number(now_s, "now_s")
    if now < out["last_time_s"]:
        return interrupt_session(out, reason="CLOCK_ROLLBACK")
    out["reported_stage_ids"].append(stage_id)
    out["stage_report_ids"].append(report_id)
    out.update(pending_stage_id=None, last_time_s=now, revision=out["revision"] + 1,
               state="REPORT_SEQUENCE_FINISHED" if len(out["reported_stage_ids"]) == len(out["stage_ids"]) else "PLANNED")
    return _seal(out)


def interrupt_session(journal: dict, *, reason: str) -> dict:
    """Latch service required. There is deliberately no replay/resume operation."""
    out = validate_journal(journal)
    reason = text(reason, "interruption reason")
    pending = out["pending_stage_id"]
    if pending is not None:
        out["uncertain_stage_id"] = pending
    out.update(state="SERVICE_REQUIRED", pending_stage_id=None, model_consistent=False,
        blockers=sorted(set(out["blockers"]) | {reason, "REPREPARATION_AND_SERVICE_REQUIRED"}),
        revision=out["revision"] + 1)
    return _seal(out)


def restore_session(serialized: str, *, expected_session_id: str | None = None,
                    minimum_revision: int | None = None) -> dict:
    """Restore a journal; optionally enforce a separately trusted restore cursor.

    The cursor must come from the durable adapter, not the record being read.
    Without it, an intact older journal cannot be distinguished from the latest.
    """
    try:
        restored = json.loads(serialized)
    except (TypeError, ValueError) as exc:
        raise CoreSketchError("invalid serialized offline journal") from exc
    out = validate_journal(restored)
    if expected_session_id is not None:
        if out["session_id"] != text(expected_session_id, "expected_session_id"):
            raise CoreSketchError("restored journal belongs to another session")
    if minimum_revision is not None:
        if type(minimum_revision) is not int or minimum_revision < 0:
            raise CoreSketchError("trusted minimum revision must be a nonnegative integer")
        if out["revision"] < minimum_revision:
            raise CoreSketchError("restored journal is older than the trusted restore cursor")
    if out["state"] == "INTENT_RECORDED":
        return interrupt_session(out, reason="RESTART_WITH_UNCERTAIN_DELIVERY")
    return out
