"""Cross-system host-session persistence; synthetic records are not hardware proof."""
from copy import deepcopy

import pytest

from masck_one.core_sketch_contracts import CoreSketchError
from masck_one.offline_journal_store import JournalConflictError, OfflineJournalStore
from masck_one.session_pipeline import (
    prepare_session, record_session_intent, record_session_report, restore_pipeline,
)
from test_session_pipeline import isolated_closed_ledger, pipeline_inputs


def prepare():
    authority, source = pipeline_inputs()
    pipeline = prepare_session(authority, "persistent-session", source,
                               now_s=1, network_reachable=False)
    return authority, source, pipeline


def intent(authority, source, pipeline, now=2):
    journal = pipeline["journal"]
    stage = journal["stage_ids"][len(journal["reported_stage_ids"])]
    return record_session_intent(authority, pipeline, source, stage,
                                 now_s=now, network_reachable=False)


def report(authority, source, pipeline, now=3):
    stage = pipeline["journal"]["pending_stage_id"]
    return record_session_report(authority, pipeline, source, stage,
        report_id="synthetic-report-" + stage, now_s=now, network_reachable=False)


def test_canonical_blocked_preparation_is_a_persistable_terminal_baseline(tmp_path):
    _, _, pipeline = prepare()
    assert pipeline["journal"]["state"] == "SERVICE_REQUIRED"
    assert pipeline["journal"]["revision"] == 0
    path = tmp_path / "session.sqlite"
    with OfflineJournalStore(path) as store:
        store.create(pipeline["journal"])
    with OfflineJournalStore(path) as store:
        restored = restore_pipeline(pipeline, store.load("persistent-session"))
    assert "WHOLE_PRODUCT_RESOURCE_ENVELOPE_UNCLOSED" in restored["blockers"]
    assert not restored["model_start_ready"]
    assert not restored["physical_routine_complete"]
    assert not restored["hardware_execution_authorized"]


def test_durable_intent_restart_cannot_become_a_report(isolated_closed_ledger, tmp_path):
    authority, source, pipeline = prepare()
    assert pipeline["journal"]["state"] == "PLANNED", pipeline["blockers"]
    path = tmp_path / "session.sqlite"
    with OfflineJournalStore(path) as store:
        store.create(pipeline["journal"])
        pending = intent(authority, source, pipeline)
        store.save(pending["journal"], expected_revision=0)
    stale_report = report(authority, source, pending)
    with OfflineJournalStore(path) as store:
        restored = restore_pipeline(pending, store.load("persistent-session"))
        assert restored["journal"]["revision"] == 2
        assert restored["journal"]["state"] == "SERVICE_REQUIRED"
        assert restored["journal"]["uncertain_stage_id"] == pending["journal"]["pending_stage_id"]
        assert not restored["journal"]["reported_stage_ids"]
        assert not restored["model_start_ready"]
        with pytest.raises(JournalConflictError):
            store.save(stale_report["journal"], expected_revision=1)
        with pytest.raises(CoreSketchError):
            record_session_report(authority, restored, source,
                pending["journal"]["pending_stage_id"], report_id="late-report",
                now_s=4, network_reachable=False)
    assert not restored["physical_routine_complete"]


def test_live_source_change_during_durable_intent_preserves_uncertainty(isolated_closed_ledger, tmp_path):
    authority, source, pipeline = prepare()
    path = tmp_path / "session.sqlite"
    with OfflineJournalStore(path) as store:
        store.create(pipeline["journal"])
        pending = intent(authority, source, pipeline)
        store.save(pending["journal"], expected_revision=0)
        changed = deepcopy(source)
        changed["reservoirs"][0]["fill_epoch"] += 1
        blocked = report(authority, changed, pending)
        assert "SOURCE_CHANGED_AFTER_PREPARATION" in blocked["blockers"]
        assert not blocked["journal"]["reported_stage_ids"]
        assert blocked["journal"]["uncertain_stage_id"] == pending["journal"]["pending_stage_id"]
        store.save(blocked["journal"], expected_revision=1)
    with OfflineJournalStore(path) as store:
        restored = restore_pipeline(pending, store.load("persistent-session"))
    assert restored["journal"]["state"] == "SERVICE_REQUIRED"
    assert restored["journal"]["uncertain_stage_id"] == pending["journal"]["pending_stage_id"]
    assert not restored["model_start_ready"]


def test_clean_checkpoint_restores_prefix_but_unknown_capacity_stops_next_intent(isolated_closed_ledger, tmp_path):
    authority, source, pipeline = prepare()
    path = tmp_path / "session.sqlite"
    with OfflineJournalStore(path) as store:
        store.create(pipeline["journal"])
        pending = intent(authority, source, pipeline)
        store.save(pending["journal"], expected_revision=0)
        checkpoint = report(authority, source, pending)
        store.save(checkpoint["journal"], expected_revision=1)
    with OfflineJournalStore(path) as store:
        restored = restore_pipeline(pipeline, store.load("persistent-session"))
        assert restored["journal"]["state"] == "PLANNED"
        assert restored["journal"]["reported_stage_ids"] == [pipeline["journal"]["stage_ids"][0]]
        changed = deepcopy(source)
        changed["current"]["resources"]["usable_energy_Wh"] = None
        stopped = intent(authority, changed, restored, now=4)
        store.save(stopped["journal"], expected_revision=2)
        assert "usable_energy_Wh:RESOURCE_UNKNOWN" in stopped["blockers"]
        assert stopped["journal"]["reported_stage_ids"] == restored["journal"]["reported_stage_ids"]
        assert stopped["journal"]["pending_stage_id"] is None
        assert stopped["journal"].get("uncertain_stage_id") is None
        assert not stopped["model_start_ready"]
        assert not stopped["physical_routine_complete"]
