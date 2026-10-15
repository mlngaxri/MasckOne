"""Synthetic host journal tests; no record here is physical evidence."""
from copy import deepcopy
import json

import pytest

from masck_one.core_sketch_contracts import CoreSketchError, digest
from masck_one.offline_session import (
    interrupt_session, plan_session, record_intent, record_stage_report,
    restore_session, validate_journal,
)
from masck_one.routine_schedule import OFFLINE_RESIDENCY_KEYS, offline_manifest
from test_core_sketch_contracts import ready


def inputs():
    request, receipt, current = ready()
    # Fixture includes SPF: resolve the session into the matching AM context.
    request["binding"]["schedule_context"] = "AM"
    current["binding"] = deepcopy(request["binding"])
    for product in current["products"]:
        product["context_digest"] = digest(request["binding"])
    receipt.update(binding_digest=digest(request["binding"]), request_digest=digest(request),
                   products_digest=digest(current["products"]))
    routine = {"id": request["binding"]["routine_id"], "revision": "1", "contexts": {
        "AM": [{k: v for k, v in stage.items() if k in {"id", "kind", "product_binding"}}
               for stage in request["plan"]["stages"]]}}
    bound = request["binding"]
    cache = {key: bound[key] for key in (
        "routine_revision", "profile_revision", "hardware_revision", "authority_digest")}
    cache.update(stage_parameters={"plan_digest": bound["plan_digest"]},
                 dose_windows={"dose_requirements_digest": digest(request["dose_requirements"])},
                 protected_region_map={"plan_digest": bound["plan_digest"]},
                 fault_response_table={"hardware_revision": bound["hardware_revision"],
                                       "authority_digest": bound["authority_digest"]})
    manifest = offline_manifest(routine, "AM", cache)
    return request, receipt, current, manifest, cache


def planned():
    return plan_session("synthetic-session", *inputs(), now_s=10, network_reachable=False)


def intent(journal=None, values=None, now=11, stage=None):
    journal = planned() if journal is None else journal
    return record_intent(journal, stage or journal["stage_ids"][len(journal["reported_stage_ids"])],
                         *(values or inputs()), now_s=now, network_reachable=False)


def test_offline_and_online_produce_identical_journals():
    args = inputs()
    offline = plan_session("session", *args, now_s=10, network_reachable=False)
    online = plan_session("session", *args, now_s=10, network_reachable=True)
    assert offline == online
    assert offline["state"] == "PLANNED"
    assert not offline["hardware_execution_authorized"]


def test_all_stage_reports_do_not_become_physical_completion():
    out = planned()
    for index, stage in enumerate(out["stage_ids"]):
        out = intent(out, now=11 + index * 2)
        out = record_stage_report(out, stage, report_id="report-" + stage, now_s=12 + index * 2)
    assert out["state"] == "REPORT_SEQUENCE_FINISHED"
    assert out["reported_stage_ids"] == out["stage_ids"]
    assert not out["physical_routine_complete"]
    assert not out["hardware_execution_authorized"]
    with pytest.raises(CoreSketchError):
        intent(out, stage=out["stage_ids"][0])


def test_expired_preparation_cannot_start_with_cached_ready():
    args = inputs()
    args[2]["cached_ready"] = True
    out = plan_session("session", *args, now_s=50, network_reachable=True)
    assert out["state"] == "SERVICE_REQUIRED"
    assert "PREPARATION_OR_OBSERVATIONS_EXPIRED" in out["blockers"]


@pytest.mark.parametrize("field", ["doses", "products", "service", "resources", "binding"])
def test_changed_current_state_between_plan_and_intent_is_rechecked(field):
    out, args = planned(), inputs()
    if field == "doses":
        args[2][field][0]["dose_id"] = "swapped"
    elif field == "products":
        args[2][field][0]["trust"] = "UNSUPPORTED"
    elif field == "service":
        args[2][field]["cleaning"] = "INTERRUPTED"
    elif field == "resources":
        args[2][field]["water_ml"] = None
    else:
        args[2][field]["routine_revision"] = "2"
    assert intent(out, args)["state"] == "SERVICE_REQUIRED"


def test_even_newly_reissued_receipt_does_not_rebind_existing_session():
    args = inputs()
    out = planned()
    args[1]["service_receipt_id"] = "another-service"
    assert "RECEIPT_CHANGED_AFTER_PLAN" in intent(out, args)["blockers"]


def test_expiry_is_rechecked_before_each_intent():
    assert intent(now=50)["state"] == "SERVICE_REQUIRED"


def test_missing_local_state_is_not_fixed_by_network():
    args = inputs()
    del args[4]["dose_windows"]
    out = plan_session("session", *args, now_s=10, network_reachable=True)
    assert "dose_windows:NOT_CACHED_LOCALLY" in out["blockers"]
    assert out["state"] == "SERVICE_REQUIRED"


def test_manifest_for_another_routine_is_not_local_readiness():
    args = inputs()
    args[3]["routine_revision"] = "2"
    assert "OFFLINE_MANIFEST_SESSION_MISMATCH" in plan_session("session", *args, now_s=10,
                                                                  network_reachable=False)["blockers"]


@pytest.mark.parametrize("reason", ["POWER_LOSS", "PARTIAL_DELIVERY", "REMOVED_EARLY", "FAULT"])
def test_interruption_records_uncertainty_and_cannot_replay(reason):
    pending = intent()
    out = interrupt_session(pending, reason=reason)
    assert out["uncertain_stage_id"] == pending["pending_stage_id"]
    assert out["reported_stage_ids"] == []
    assert out["state"] == "SERVICE_REQUIRED"
    assert not out["physical_routine_complete"]
    with pytest.raises(CoreSketchError):
        intent(out)


def test_restore_after_intent_latches_unknown_delivery():
    out = restore_session(json.dumps(intent()))
    assert "RESTART_WITH_UNCERTAIN_DELIVERY" in out["blockers"]
    assert out["state"] == "SERVICE_REQUIRED"
    assert out["reported_stage_ids"] == []


def test_restore_clean_planned_journal_requires_new_readiness_before_intent():
    out = restore_session(json.dumps(planned()))
    assert out["state"] == "PLANNED"
    assert intent(out, now=50)["state"] == "SERVICE_REQUIRED"


def test_reordered_or_unsolicited_reports_are_rejected():
    pending = intent()
    with pytest.raises(CoreSketchError):
        record_stage_report(pending, pending["stage_ids"][1], report_id="r", now_s=12)
    with pytest.raises(CoreSketchError):
        record_stage_report(planned(), planned()["stage_ids"][0], report_id="r", now_s=12)
    with pytest.raises(CoreSketchError):
        intent(stage=planned()["stage_ids"][1])


def test_clock_rollback_latches_service_without_replay():
    assert "CLOCK_ROLLBACK" in intent(now=9)["blockers"]
    pending = intent()
    report = record_stage_report(pending, pending["pending_stage_id"], report_id="r", now_s=10)
    assert report["state"] == "SERVICE_REQUIRED"
    assert report["reported_stage_ids"] == []


@pytest.mark.parametrize("mutation", ["state", "schema_version", "hardware_execution_authorized", "physical_routine_complete"])
def test_corrupt_or_escalated_restored_journal_is_rejected(mutation):
    out = planned()
    out[mutation] = True if "authorized" in mutation or "complete" in mutation else "invalid"
    with pytest.raises(CoreSketchError):
        restore_session(json.dumps(out))


def test_resealed_unknown_state_and_inconsistent_progress_are_rejected():
    out = planned()
    out["state"] = "UNEXPECTED_DEVICE_STATE"
    out["journal_digest"] = digest({k: v for k, v in out.items() if k != "journal_digest"})
    with pytest.raises(CoreSketchError):
        validate_journal(out)
    out = planned()
    out["reported_stage_ids"] = [out["stage_ids"][1]]
    out["journal_digest"] = digest({k: v for k, v in out.items() if k != "journal_digest"})
    with pytest.raises(CoreSketchError):
        validate_journal(out)


@pytest.mark.parametrize("bad", ["not json", "{}", "null", "[]"])
def test_invalid_restore_fails_closed(bad):
    with pytest.raises(CoreSketchError):
        restore_session(bad)


def test_report_identifier_cannot_be_reused_for_another_stage():
    pending = intent()
    first = record_stage_report(pending, pending["pending_stage_id"], report_id="report", now_s=12)
    second = intent(first, now=13)
    with pytest.raises(CoreSketchError):
        record_stage_report(second, second["pending_stage_id"], report_id="report", now_s=14)


def test_report_log_survives_round_trip_without_becoming_physical_evidence():
    pending = intent()
    out = record_stage_report(pending, pending["pending_stage_id"], report_id="report", now_s=12)
    restored = restore_session(json.dumps(out))
    assert restored == out
    assert restored["stage_report_ids"] == ["report"]
    assert not restored["physical_routine_complete"]


@pytest.mark.parametrize("key", ["routine_revision", "profile_revision", "hardware_revision", "authority_digest"])
def test_manifest_and_cache_both_stale_cannot_match_execution_binding(key):
    args = inputs()
    args[4][key] = "old-revision"
    args[3]["entries"][key] = "old-revision"
    args[3]["residency_digest"] = digest(args[3]["entries"])
    out = plan_session("session", *args, now_s=10, network_reachable=False)
    assert key + ":NOT_BOUND_TO_EXECUTION" in out["blockers"]
    assert out["state"] == "SERVICE_REQUIRED"


@pytest.mark.parametrize("key,field", [("stage_parameters", "plan_digest"),
    ("dose_windows", "dose_requirements_digest"), ("protected_region_map", "plan_digest"),
    ("fault_response_table", "hardware_revision"), ("fault_response_table", "authority_digest")])
def test_locally_matching_inapplicable_control_records_are_refused(key, field):
    args = inputs()
    args[4][key][field] = "inapplicable"
    args[3]["entries"][key][field] = "inapplicable"
    args[3]["residency_digest"] = digest(args[3]["entries"])
    out = plan_session("session", *args, now_s=10, network_reachable=True)
    assert key + ":" + field + ":NOT_BOUND_TO_EXECUTION" in out["blockers"]


def test_typed_revision_records_are_accepted_when_bound():
    args = inputs()
    for key in ("routine_revision", "profile_revision", "hardware_revision", "authority_digest"):
        value = args[4][key]
        args[4][key] = {"digest" if key == "authority_digest" else "revision": value}
        args[3]["entries"][key] = deepcopy(args[4][key])
    args[3]["residency_digest"] = digest(args[3]["entries"])
    assert plan_session("session", *args, now_s=10, network_reachable=False)["state"] == "PLANNED"


def test_restore_cursor_rejects_intact_old_journal():
    old = planned()
    newer = intent(old)
    with pytest.raises(CoreSketchError):
        restore_session(json.dumps(old), expected_session_id=old["session_id"],
                        minimum_revision=newer["revision"])
    restored = restore_session(json.dumps(newer), expected_session_id=old["session_id"],
                               minimum_revision=newer["revision"])
    assert restored["state"] == "SERVICE_REQUIRED"


def test_restore_cursor_rejects_another_session():
    with pytest.raises(CoreSketchError):
        restore_session(json.dumps(planned()), expected_session_id="another-session")


@pytest.mark.parametrize("bad", [True, -1, "1"])
def test_restore_cursor_is_explicitly_typed(bad):
    with pytest.raises(CoreSketchError):
        restore_session(json.dumps(planned()), minimum_revision=bad)
