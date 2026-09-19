"""CS-018 committed owner records -> the existing declared-footprint compiler.

This binds digital assertions to source, not to physical performance. Producer
records and an independently refreshed head inventory are required. Local files
and caller-supplied Action objects cannot replace committed owner footprints.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

from .cleansing_scheduler import Action, BLOCKED_UNQUALIFIED, compile_plan, map_footprints
from .regional_cleansing import Burden, ControlError, Region

REQUIRED_OWNERS = ("main", "treatment", "thermal", "retention", "frame", "exterior", "fluid")
SNAPSHOT_SCHEMA = "CS018_CLEANSING_SOURCES_V1"
CAPABILITY_SCHEMA = "CS018_OWNER_CLEANSING_CAPABILITIES_V1"
CAPABILITY_PATH = "docs/contracts/cs018_cleansing_capabilities_v1.json"
EVIDENCE = "SOURCE_BOUND_DIGITAL_ASSERTIONS_NOT_PHYSICAL_VALIDATION"
ROLES = {"ACTUATOR", "SUPPORT", "OCCLUDER", "FLUID_SEAL", "NO_CONTACT"}


class CapabilityError(ControlError):
    pass


def _require(ok, message):
    if not ok:
        raise CapabilityError(message)


def _hex(value, length):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{" + str(length) + "}", value) is not None


def _json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, "DUPLICATE_JSON_KEY: " + key)
            result[key] = value
        return result
    try:
        return json.loads(data, object_pairs_hook=unique)
    except (ValueError, UnicodeError) as exc:
        raise CapabilityError("INVALID_JSON: " + str(exc)) from exc


def _git(repository, *args):
    try:
        return subprocess.check_output(
            ["git", "--no-replace-objects", "--literal-pathspecs", "-C", str(repository), *args],
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        raise CapabilityError("SOURCE_OBJECT_UNAVAILABLE") from exc


def source_blob(repository, head, path):
    """Read one regular blob from an exact commit, never from the worktree."""
    _require(_hex(head, 40), "FULL_SOURCE_COMMIT_REQUIRED")
    _require(isinstance(path, str) and bool(path) and "\\" not in path
             and not PurePosixPath(path).is_absolute()
             and all(p not in ("", ".", "..") for p in path.split("/")), "INVALID_SOURCE_PATH")
    _require(_git(repository, "cat-file", "-t", head).strip() == b"commit", "SOURCE_NOT_COMMIT")
    entries = _git(repository, "ls-tree", "-z", head, "--", path).split(b"\0")
    entries = [entry for entry in entries if entry]
    _require(len(entries) == 1, "SOURCE_PATH_MISSING: " + path)
    metadata, actual_path = entries[0].split(b"\t", 1)
    mode, kind, blob = metadata.decode().split()
    _require(mode in ("100644", "100755") and kind == "blob"
             and actual_path.decode() == path, "SOURCE_NOT_REGULAR_BLOB: " + path)
    data = _git(repository, "cat-file", "blob", blob)
    return data, {"path": path, "git_blob": blob, "sha256": sha256(data).hexdigest()}


def _sources(repository, head, bindings):
    _require(isinstance(bindings, list) and bool(bindings), "SOURCE_BINDINGS_REQUIRED")
    result = {}
    for binding in bindings:
        _require(isinstance(binding, dict), "INVALID_SOURCE_BINDING")
        path = binding.get("path")
        _require(isinstance(path, str) and path not in result, "DUPLICATE_OR_MISSING_SOURCE_PATH")
        _require(_hex(binding.get("git_blob"), 40) and _hex(binding.get("sha256"), 64),
                 "FULL_SOURCE_HASHES_REQUIRED")
        _, actual = source_blob(repository, head, path)
        _require(actual == binding, "SOURCE_BINDING_MISMATCH: " + path)
        result[path] = actual
    return result


def _cells(value, label):
    _require(isinstance(value, list) and all(isinstance(c, str) and c for c in value),
             "UNKNOWN_OR_INVALID_CELLS: " + label)
    _require(len(set(value)) == len(value), "DUPLICATE_CELLS: " + label)
    return frozenset(value)


def _owner_record(repository, owner, context, live_head, bound):
    _require(isinstance(context, dict), "UNRESOLVED_OWNER_CAPABILITY")
    head = context.get("head")
    _require(_hex(head, 40) and _hex(live_head, 40), "CURRENT_PRODUCER_HEAD_REQUIRED")
    _require(head == live_head, "STALE_PRODUCER_HEAD")
    expected = _sources(repository, head, context.get("sources"))
    bound.update(head=head, source_files=[expected[p] for p in sorted(expected)],
                 source_binding_status="EXACT_COMMIT_BLOBS_VERIFIED")
    data, identity = source_blob(repository, head, CAPABILITY_PATH)
    bound["capability_source"] = identity
    record = _json(data)
    _require(isinstance(record, dict) and record.get("schema") == CAPABILITY_SCHEMA
             and record.get("owner") == owner, "OWNER_CAPABILITY_IDENTITY_MISMATCH")
    _require(record.get("status") == "DIGITAL_REGISTERED"
             and record.get("evidence") == "DIGITAL"
             and "physical_result" in record and record["physical_result"] is None,
             "UNRESOLVED_OWNER_CAPABILITY")
    consumed = _sources(repository, head, record.get("source_files"))
    _require(all(consumed.get(path) == binding for path, binding in expected.items()),
             "REQUIRED_SOURCE_OMITTED")
    domain = record.get("domain_id")
    _require(isinstance(domain, str) and bool(domain), "REGISTERED_DOMAIN_REQUIRED")
    rows = record.get("actions")
    _require(isinstance(rows, list) and bool(rows), "OWNER_ACTION_CATALOG_REQUIRED")
    indexed = {}
    for row in rows:
        _require(isinstance(row, dict), "INVALID_CAPABILITY_ROW")
        aid = row.get("action_id")
        _require(isinstance(aid, str) and bool(aid) and aid not in indexed,
                 "DUPLICATE_OR_MISSING_ACTION_ID")
        _require(isinstance(row.get("channel_id"), str) and bool(row["channel_id"]),
                 "CHANNEL_IDENTITY_REQUIRED: " + aid)
        _require(row.get("evidence_status") == "DIGITAL_REGISTERED",
                 "UNRESOLVED_ACTION_CAPABILITY: " + aid)
        _require(row.get("motion") in ("MOVING", "STATIONARY") and row.get("role") in ROLES,
                 "UNRESOLVED_MOTION_OR_ROLE: " + aid)
        refs = row.get("evidence_paths")
        _require(isinstance(refs, list) and bool(refs)
                 and all(isinstance(p, str) and p in consumed for p in refs),
                 "UNBOUND_FOOTPRINT_EVIDENCE: " + aid)
        target = _cells(row.get("target_cells"), aid + ".target")
        incidental = _cells(row.get("incidental_cells"), aid + ".incidental")
        affected = _cells(row.get("affected_cells"), aid + ".affected")
        _require(not target & incidental and target | incidental == affected,
                 "INCOMPLETE_AFFECTED_FOOTPRINT: " + aid)
        _require(not _cells(row.get("blocked_cells"), aid + ".blocked"),
                 "SOURCE_BLOCKED_ACTION: " + aid)
        _require(row["role"] != "NO_CONTACT" or not affected, "NO_CONTACT_HAS_FOOTPRINT: " + aid)
        if row["role"] != "ACTUATOR":
            _require("increment" in row and row["increment"] is None,
                     "NON_ACTUATOR_BURDEN: " + aid)
        indexed[aid] = row
    bound.update(status="SOURCE_BOUND_DIGITAL", domain_id=domain,
                 source_files=[consumed[p] for p in sorted(consumed)])
    return indexed, bound


@dataclass(frozen=True)
class CapabilityBinding:
    actions: tuple[Action, ...]
    receipt: dict


def bind_capabilities(repository: Path, snapshot: dict, live_heads: dict,
                      regions: dict[str, Region]) -> CapabilityBinding:
    """Require all declared owners, including stationary and fluid/seal effects.

    ``live_heads`` comes from a separate current GitHub owner inventory. A cached
    inventory only establishes validity at that observation, not future freshness.
    Snapshot data contains source identities only. Actions are loaded from Git.
    """
    receipt = {"schema": "CS018_CLEANSING_BINDING_V1", "evidence_status": EVIDENCE,
               "human_use_eligible": False, "physical_result": None,
               "owners": [], "blockers": [], "actions": []}
    blockers = receipt["blockers"]
    if (not isinstance(snapshot, dict) or snapshot.get("schema") != SNAPSHOT_SCHEMA
            or not isinstance(snapshot.get("owners"), dict) or not isinstance(live_heads, dict)):
        blockers.append({"owner": "integration", "reason": "INVALID_SOURCE_INVENTORY"})
        return CapabilityBinding((), receipt)
    receipt["source_inventory_sha256"] = sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    receipt["observed_heads"] = {k: live_heads.get(k) for k in REQUIRED_OWNERS}
    owners = snapshot["owners"]
    if set(owners) != set(REQUIRED_OWNERS):
        blockers.append({"owner": "integration", "reason": "REQUIRED_OWNER_SET_MISMATCH"})
    catalogs = {}
    for owner in REQUIRED_OWNERS:
        bound = {"owner": owner}
        try:
            rows, bound = _owner_record(repository, owner, owners.get(owner), live_heads.get(owner), bound)
            catalogs[owner] = rows
            receipt["owners"].append(bound)
        except CapabilityError as exc:
            reason = str(exc)
            blockers.append({"owner": owner, "reason": reason})
            receipt["owners"].append({**bound, "status": "UNRESOLVED_OWNER_CAPABILITY",
                                      "reason": reason})
    if blockers:
        return CapabilityBinding((), receipt)
    try:
        domains = {row["domain_id"] for row in receipt["owners"]}
        _require(len(domains) == 1 and all(r.domain_id in domains for r in regions.values()),
                 "REGION_DOMAIN_MISMATCH")
        action_ids = set.union(*(set(rows) for rows in catalogs.values()))
        _require(all(set(rows) == action_ids for rows in catalogs.values()),
                 "OWNER_ACTION_FOOTPRINT_OMITTED")
        actions = []
        for aid in sorted(action_ids):
            rows = [catalogs[o][aid] for o in REQUIRED_OWNERS]
            drivers = [r for r in rows if r["role"] == "ACTUATOR"]
            _require(len(drivers) == 1, "EXACTLY_ONE_ACTUATOR_REQUIRED: " + aid)
            driver = drivers[0]
            _require(all(r.get("channel_id") == driver.get("channel_id")
                         and r.get("kind") == driver.get("kind") for r in rows),
                     "OWNER_ACTION_IDENTITY_MISMATCH: " + aid)
            increment = driver.get("increment")
            _require(isinstance(increment, dict) and set(increment) == {f.name for f in fields(Burden)},
                     "COMPLETE_BURDEN_REQUIRED: " + aid)
            _require(all(type(v) in (int, float) for v in increment.values()), "INVALID_BURDEN: " + aid)
            affected = frozenset().union(*(r["affected_cells"] for r in rows))
            actions.append(Action(aid, driver.get("kind"), affected, Burden(**increment),
                                  driver.get("channel_id"), driver.get("complexity")))
        # The canonical compiler already checks unmapped and multiply owned cells.
        # Refuse non-required contact here; it must not enter its required ledger.
        reach = map_footprints(actions, regions)
        _require(all(regions[k].classification == "REQUIRED" for touched in reach.values() for k in touched),
                 "PROTECTED_OR_EXCLUDED_CELL_AFFECTED")
        receipt["actions"] = [{"action_id": a.action_id, "kind": a.kind,
                               "channel_id": a.channel_id, "cells": sorted(a.cells)} for a in actions]
        return CapabilityBinding(tuple(actions), receipt)
    except (ControlError, TypeError, ValueError) as exc:
        blockers.append({"owner": "integration", "reason": str(exc)})
        return CapabilityBinding((), receipt)


def compile_source_bound_plan(repository, snapshot, live_heads, regions, *, envelopes,
                              session_water_ml=None, session_cleanser_ml=None, max_steps=256):
    """The hardware-facing entry point. It intentionally has no Actions argument."""
    binding = bind_capabilities(repository, snapshot, live_heads, regions)
    if binding.receipt["blockers"]:
        return {"outcome": BLOCKED_UNQUALIFIED, "evidence_status": EVIDENCE,
                "steps": [], "witness": {"reason": "SOURCE_BOUND_CAPABILITY_INCOMPLETE",
                                           "blockers": binding.receipt["blockers"]},
                "human_use_eligible": False, "physical_result": None,
                "capability_binding": binding.receipt}
    out = compile_plan(regions, list(binding.actions), envelopes=envelopes,
                       session_water_ml=session_water_ml, session_cleanser_ml=session_cleanser_ml,
                       max_steps=max_steps)
    return {**out, "evidence_status": EVIDENCE, "physical_result": None,
            "capability_binding": binding.receipt}
