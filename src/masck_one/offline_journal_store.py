"""Atomic SQLite persistence for host-only offline session journals.

``save`` commits the intent before returning it to a caller. This adapter never
sends device commands or authorizes device execution. ``load`` is a restore
boundary: an outstanding intent is atomically latched SERVICE_REQUIRED before
it is returned. Keep the value returned by ``save`` to report within the same
uninterrupted host flow instead of reloading an outstanding intent.

The separate cursor detects stale/resealed journal rows within this database.
It is not cryptographic authentication, and cannot detect replacement/rollback
of the *entire* database (including its cursor). Durability requires a working
SQLite filesystem and storage stack honoring synchronization requests.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import sqlite3
from pathlib import Path

from .core_sketch_contracts import CoreSketchError, text
from .offline_session import restore_session, validate_journal

_MUTABLE = frozenset({"state", "revision", "pending_stage_id", "reported_stage_ids",
    "stage_report_ids", "last_time_s", "blockers", "model_consistent",
    "uncertain_stage_id", "journal_digest"})


class JournalConflictError(CoreSketchError):
    """The expected revision no longer identifies the latest stored journal."""


def _json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _identity(record: dict) -> str:
    return _json({key: value for key, value in record.items() if key not in _MUTABLE})


def _checked(record: dict) -> dict:
    out = validate_journal(record)
    service = out["state"] == "SERVICE_REQUIRED"
    if (out.get("model_consistent") is not (not service)
        or bool(out["blockers"]) is not service):
        raise CoreSketchError("journal state contradicts its blockers or consistency")
    uncertain = out.get("uncertain_stage_id")
    if uncertain is not None:
        reported = out["reported_stage_ids"]
        if len(reported) >= len(out["stage_ids"]) or uncertain != out["stage_ids"][len(reported)]:
            raise CoreSketchError("uncertainty must identify the next unreported stage")
    return out


def _transition(previous: dict, following: dict) -> None:
    if _identity(previous) != _identity(following):
        raise CoreSketchError("stored session identity and bindings are immutable")
    if following["revision"] != previous["revision"] + 1:
        raise JournalConflictError("journal must advance exactly one revision")
    if following["last_time_s"] < previous["last_time_s"]:
        raise CoreSketchError("stored journal time cannot roll back")
    before, after = previous["state"], following["state"]
    if before == "SERVICE_REQUIRED":
        if (after != before or previous.get("uncertain_stage_id") != following.get("uncertain_stage_id")
            or not set(previous["blockers"]) <= set(following["blockers"])):
            raise CoreSketchError("service requirement and uncertainty cannot be cleared")
    elif after == "SERVICE_REQUIRED":
        if following.get("uncertain_stage_id") != previous.get("pending_stage_id"):
            raise CoreSketchError("service transition must preserve outstanding uncertainty")
    elif before == "PLANNED":
        if after != "INTENT_RECORDED":
            raise CoreSketchError("planned session requires a durable intent first")
    elif before == "INTENT_RECORDED":
        if after not in {"PLANNED", "REPORT_SEQUENCE_FINISHED"}:
            raise CoreSketchError("outstanding intent requires its report or service")
        expected = previous["reported_stage_ids"] + [previous["pending_stage_id"]]
        if (following["reported_stage_ids"] != expected
            or following["stage_report_ids"][:-1] != previous["stage_report_ids"]):
            raise CoreSketchError("report must extend the outstanding intent exactly once")
        return
    else:
        raise CoreSketchError("finished journal cannot resume execution")
    if (following["reported_stage_ids"] != previous["reported_stage_ids"]
        or following["stage_report_ids"] != previous["stage_report_ids"]):
        raise CoreSketchError("only an outstanding intent can advance reported progress")


class OfflineJournalStore:
    """Single-transaction host store; independent writers use revision CAS.

    Each instance uses one SQLite connection; use one instance per thread.
    ``create`` accepts a new revision-zero baseline exactly once per session ID.
    ``save`` requires the latest expected revision and a legal next transition.
    Existing session IDs cannot be reset, rebound or replaced with a baseline.
    """

    def __init__(self, path: str | Path):
        if not isinstance(path, (str, Path)) or str(path) in {"", ":memory:"}:
            raise CoreSketchError("journal store requires a persistent database path")
        self._owned_intents: dict[str, str] = {}
        self._connection = sqlite3.connect(str(path), isolation_level=None, timeout=5)
        try:
            self._connection.execute("PRAGMA foreign_keys=ON")
            mode = self._connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            if mode != "wal":
                raise CoreSketchError("journal store requires SQLite write-ahead logging")
            self._connection.execute("PRAGMA synchronous=FULL")
            with self._transaction():
                version = self._connection.execute("PRAGMA user_version").fetchone()[0]
                if version not in (0, 1):
                    raise CoreSketchError("unsupported journal database schema")
                self._connection.execute("""CREATE TABLE IF NOT EXISTS session_cursors (
                    session_id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
                    identity TEXT NOT NULL, journal_digest TEXT NOT NULL)""")
                self._connection.execute("""CREATE TABLE IF NOT EXISTS session_journals (
                    session_id TEXT PRIMARY KEY REFERENCES session_cursors(session_id),
                    serialized TEXT NOT NULL)""")
                self._connection.execute("PRAGMA user_version=1")
        except BaseException:
            self.close()
            raise

    @contextmanager
    def _transaction(self):
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            yield
            self._connection.execute("COMMIT")
        except BaseException:
            self._connection.execute("ROLLBACK")
            raise

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> OfflineJournalStore:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _read(self, session_id: str) -> dict:
        cursor = self._connection.execute(
            "SELECT revision, identity, journal_digest FROM session_cursors WHERE session_id=?",
            (session_id,)).fetchone()
        row = self._connection.execute(
            "SELECT serialized FROM session_journals WHERE session_id=?", (session_id,)).fetchone()
        if cursor is None or row is None:
            raise CoreSketchError("session journal or restore cursor is missing")
        try:
            record = _checked(json.loads(row[0]))
        except (TypeError, ValueError) as exc:
            raise CoreSketchError("stored journal is invalid") from exc
        if (record["session_id"] != session_id or record["revision"] != cursor[0]
            or _identity(record) != cursor[1] or record["journal_digest"] != cursor[2]):
            raise CoreSketchError("stored journal disagrees with its restore cursor")
        return record

    def _write(self, record: dict, expected_revision: int) -> None:
        updated = self._connection.execute(
            "UPDATE session_cursors SET revision=?, journal_digest=? WHERE session_id=? AND revision=?",
            (record["revision"], record["journal_digest"], record["session_id"], expected_revision))
        if updated.rowcount != 1:
            raise JournalConflictError("another writer changed the session revision")
        self._connection.execute("UPDATE session_journals SET serialized=? WHERE session_id=?",
                                 (_json(record), record["session_id"]))

    def create(self, journal: dict) -> dict:
        record = _checked(journal)
        if (record["revision"] != 0 or record["state"] not in {"PLANNED", "SERVICE_REQUIRED"}
            or record["reported_stage_ids"] or record.get("uncertain_stage_id") is not None):
            raise CoreSketchError("new session requires an unused revision-zero baseline")
        with self._transaction():
            if self._connection.execute("SELECT 1 FROM session_cursors WHERE session_id=?",
                                        (record["session_id"],)).fetchone():
                raise JournalConflictError("session identity already exists; baseline cannot be resealed")
            self._connection.execute("INSERT INTO session_cursors VALUES (?, ?, ?, ?)",
                (record["session_id"], 0, _identity(record), record["journal_digest"]))
            self._connection.execute("INSERT INTO session_journals VALUES (?, ?)",
                                     (record["session_id"], _json(record)))
        return record

    def save(self, journal: dict, *, expected_revision: int) -> dict:
        if type(expected_revision) is not int or expected_revision < 0:
            raise CoreSketchError("expected revision must be a nonnegative integer")
        record = _checked(journal)
        with self._transaction():
            previous = self._read(record["session_id"])
            if previous["revision"] != expected_revision:
                raise JournalConflictError("stale writer; read the latest journal before proceeding")
            if (previous["state"] == "INTENT_RECORDED"
                and self._owned_intents.get(previous["session_id"]) != previous["journal_digest"]):
                raise CoreSketchError("outstanding intent belongs to a prior flow; restore it before proceeding")
            _transition(previous, record)
            self._write(record, expected_revision)
        if record["state"] == "INTENT_RECORDED":
            self._owned_intents[record["session_id"]] = record["journal_digest"]
        else:
            self._owned_intents.pop(record["session_id"], None)
        return record

    def load(self, session_id: str) -> dict:
        """Restore and commit any uncertain-intent latch in the same transaction."""
        session_id = text(session_id, "session_id")
        with self._transaction():
            previous = self._read(session_id)
            record = restore_session(_json(previous), expected_session_id=session_id,
                                     minimum_revision=previous["revision"])
            record = _checked(record)
            if record != previous:
                _transition(previous, record)
                self._write(record, previous["revision"])
        self._owned_intents.pop(session_id, None)
        return record
