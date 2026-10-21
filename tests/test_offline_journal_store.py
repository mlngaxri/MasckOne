"""SQLite host persistence tests; synthetic reports never authorize hardware."""
from copy import deepcopy
import json
import os
import sqlite3
import subprocess
import sys

import pytest

from masck_one.core_sketch_contracts import CoreSketchError, digest
from masck_one.offline_journal_store import JournalConflictError, OfflineJournalStore
from masck_one.offline_session import interrupt_session, record_stage_report
from test_offline_session import intent, planned


def reseal(record):
    record['journal_digest'] = digest({k: v for k, v in record.items() if k != 'journal_digest'})
    return record


def report(pending):
    return record_stage_report(pending, pending['pending_stage_id'], report_id='report', now_s=12)


def test_close_reopen_latches_and_durably_preserves_uncertain_intent(tmp_path):
    path = tmp_path / 'session.sqlite'
    with OfflineJournalStore(path) as store:
        baseline = store.create(planned())
        pending = store.save(intent(baseline), expected_revision=0)
        assert pending['state'] == 'INTENT_RECORDED'
    with OfflineJournalStore(path) as store:
        restored = store.load(baseline['session_id'])
        assert restored['state'] == 'SERVICE_REQUIRED'
        assert restored['revision'] == 2
        assert restored['uncertain_stage_id'] == pending['pending_stage_id']
        assert restored['reported_stage_ids'] == []
        assert 'RESTART_WITH_UNCERTAIN_DELIVERY' in restored['blockers']
        assert not restored['hardware_execution_authorized']
        assert not restored['physical_routine_complete']
    with OfflineJournalStore(path) as store:
        assert store.load(baseline['session_id']) == restored


def test_clean_report_and_identity_round_trip(tmp_path):
    path = tmp_path / 'session.sqlite'
    with OfflineJournalStore(path) as store:
        baseline = store.create(planned())
        pending = store.save(intent(baseline), expected_revision=0)
        finished = store.save(report(pending), expected_revision=1)
    with OfflineJournalStore(path) as store:
        assert store.load(baseline['session_id']) == finished
        with pytest.raises(JournalConflictError):
            store.create(baseline)


def test_reopened_writer_cannot_bypass_uncertainty_with_saved_report(tmp_path):
    path = tmp_path / 'session.sqlite'
    with OfflineJournalStore(path) as store:
        baseline = store.create(planned())
        pending = store.save(intent(baseline), expected_revision=0)
    with OfflineJournalStore(path) as store:
        with pytest.raises(CoreSketchError, match='prior flow'):
            store.save(report(pending), expected_revision=1)
        assert store.load(baseline['session_id'])['state'] == 'SERVICE_REQUIRED'


def test_two_writers_compare_and_swap_rejects_stale_intent(tmp_path):
    path = tmp_path / 'session.sqlite'
    with OfflineJournalStore(path) as first, OfflineJournalStore(path) as second:
        baseline = first.create(planned())
        stale = second.load(baseline['session_id'])
        first.save(intent(baseline), expected_revision=0)
        with pytest.raises(JournalConflictError):
            second.save(intent(stale), expected_revision=0)
        latched = second.load(baseline['session_id'])
        assert latched['state'] == 'SERVICE_REQUIRED'
        with pytest.raises(JournalConflictError):
            first.save(report(intent(baseline)), expected_revision=1)


def test_rollback_after_both_row_updates_preserves_previous_commit(tmp_path):
    path = tmp_path / 'session.sqlite'
    class BrokenStore(OfflineJournalStore):
        def _write(self, record, expected_revision):
            super()._write(record, expected_revision)
            raise RuntimeError('simulated process error before commit')
    with BrokenStore(path) as store:
        baseline = store.create(planned())
        with pytest.raises(RuntimeError):
            store.save(intent(baseline), expected_revision=0)
    with OfflineJournalStore(path) as store:
        assert store.load(baseline['session_id']) == baseline


def test_restore_latch_failure_does_not_return_or_erase_pending(tmp_path):
    path = tmp_path / 'session.sqlite'
    class BrokenStore(OfflineJournalStore):
        def _write(self, record, expected_revision):
            super()._write(record, expected_revision)
            raise RuntimeError('simulated restore write error')
    with OfflineJournalStore(path) as store:
        baseline = store.create(planned())
        store.save(intent(baseline), expected_revision=0)
    with BrokenStore(path) as store:
        with pytest.raises(RuntimeError):
            store.load(baseline['session_id'])
    with sqlite3.connect(path) as db:
        record = json.loads(db.execute('SELECT serialized FROM session_journals').fetchone()[0])
        assert record['state'] == 'INTENT_RECORDED'
        assert db.execute('SELECT revision FROM session_cursors').fetchone()[0] == 1
    with OfflineJournalStore(path) as store:
        assert store.load(baseline['session_id'])['state'] == 'SERVICE_REQUIRED'


def test_process_exit_before_commit_cannot_publish_an_intent(tmp_path):
    path = tmp_path / 'session.sqlite'
    baseline = planned()
    with OfflineJournalStore(path) as store:
        store.create(baseline)
    child = '''
import json, os, sys
from masck_one.offline_journal_store import OfflineJournalStore
store = OfflineJournalStore(sys.argv[1])
store._connection.execute("BEGIN IMMEDIATE")
store._write(json.loads(sys.argv[2]), 0)
os._exit(17)
'''
    completed = subprocess.run([sys.executable, '-c', child, str(path), json.dumps(intent(baseline))],
                               env={**os.environ, 'PYTHONPATH': 'src'}, check=False)
    assert completed.returncode == 17
    with OfflineJournalStore(path) as store:
        assert store.load(baseline['session_id']) == baseline


def test_process_exit_after_save_preserves_committed_intent(tmp_path):
    path = tmp_path / 'session.sqlite'
    baseline = planned()
    with OfflineJournalStore(path) as store:
        store.create(baseline)
    child = '''
import json, os, sys
from masck_one.offline_journal_store import OfflineJournalStore
store = OfflineJournalStore(sys.argv[1])
store.save(json.loads(sys.argv[2]), expected_revision=0)
os._exit(17)
'''
    completed = subprocess.run([sys.executable, '-c', child, str(path), json.dumps(intent(baseline))],
                               env={**os.environ, 'PYTHONPATH': 'src'}, check=False)
    assert completed.returncode == 17
    with OfflineJournalStore(path) as store:
        restored = store.load(baseline['session_id'])
        assert restored['state'] == 'SERVICE_REQUIRED'
        assert restored['revision'] == 2


@pytest.mark.parametrize('mutation', ['old', 'same_revision_reseal', 'unknown', 'wrong_session', 'missing_cursor'])
def test_journal_row_replacement_cannot_replace_cursor(tmp_path, mutation):
    path = tmp_path / 'session.sqlite'
    baseline = planned()
    with OfflineJournalStore(path) as store:
        store.create(baseline)
        pending = store.save(intent(baseline), expected_revision=0)
        latest = store.save(report(pending), expected_revision=1)
    replacement = deepcopy(latest)
    if mutation == 'old':
        replacement = baseline
    elif mutation == 'same_revision_reseal':
        replacement['last_time_s'] += 1
    elif mutation == 'unknown':
        replacement['state'] = 'UNKNOWN'
    elif mutation == 'wrong_session':
        replacement['session_id'] = 'another'
    with sqlite3.connect(path) as db:
        db.execute('UPDATE session_journals SET serialized=?', (json.dumps(reseal(replacement)),))
        if mutation == 'missing_cursor':
            db.execute('DELETE FROM session_cursors')
    with OfflineJournalStore(path) as store:
        with pytest.raises(CoreSketchError):
            store.load(baseline['session_id'])


@pytest.mark.parametrize('mutation', ['request_digest', 'receipt_digest', 'manifest_digest', 'stage_ids',
                                      'evidence_status', 'schema_version'])
def test_resealed_binding_changes_are_not_session_transitions(tmp_path, mutation):
    with OfflineJournalStore(tmp_path / 'session.sqlite') as store:
        baseline = store.create(planned())
        changed = intent(baseline)
        changed[mutation] = ['different'] if mutation == 'stage_ids' else 'different'
        with pytest.raises(CoreSketchError):
            store.save(reseal(changed), expected_revision=0)
        assert store.load(baseline['session_id']) == baseline


def test_sticky_service_cannot_be_resealed_as_new_planned_revision(tmp_path):
    with OfflineJournalStore(tmp_path / 'session.sqlite') as store:
        baseline = store.create(planned())
        blocked = store.save(interrupt_session(baseline, reason='FAULT'), expected_revision=0)
        changed = deepcopy(baseline)
        changed['revision'] = 2
        with pytest.raises(CoreSketchError, match='cannot be cleared'):
            store.save(reseal(changed), expected_revision=1)
        assert store.load(baseline['session_id']) == blocked


@pytest.mark.parametrize('mutation', ['skip_revision', 'rewind', 'skip_intent', 'blockers', 'consistency', 'uncertainty'])
def test_contradictory_resealed_transitions_are_rejected(tmp_path, mutation):
    with OfflineJournalStore(tmp_path / 'session.sqlite') as store:
        baseline = store.create(planned())
        changed = intent(baseline)
        if mutation == 'skip_revision':
            changed['revision'] = 2
        elif mutation == 'rewind':
            changed['last_time_s'] = 1
        elif mutation == 'skip_intent':
            changed = report(changed)
            changed['revision'] = 1
        elif mutation == 'blockers':
            changed['blockers'] = ['FAULT']
        elif mutation == 'consistency':
            changed['model_consistent'] = False
        else:
            changed = interrupt_session(changed, reason='FAULT')
            changed['revision'] = 1
            changed['uncertain_stage_id'] = changed['stage_ids'][-1]
        with pytest.raises(CoreSketchError):
            store.save(reseal(changed), expected_revision=0)
        assert store.load(baseline['session_id']) == baseline


@pytest.mark.parametrize('revision', [True, -1, '0'])
def test_expected_revision_requires_an_explicit_integer(tmp_path, revision):
    with OfflineJournalStore(tmp_path / 'session.sqlite') as store:
        baseline = store.create(planned())
        with pytest.raises(CoreSketchError):
            store.save(intent(baseline), expected_revision=revision)


def test_unknown_session_is_not_a_new_baseline(tmp_path):
    with OfflineJournalStore(tmp_path / 'session.sqlite') as store:
        with pytest.raises(CoreSketchError):
            store.load('missing')
        with pytest.raises(CoreSketchError):
            store.create(intent())


@pytest.mark.parametrize('path', ['', ':memory:', None])
def test_ephemeral_database_cannot_claim_durable_store(path):
    with pytest.raises(CoreSketchError, match='persistent database path'):
        OfflineJournalStore(path)
