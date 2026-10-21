"""Synthetic Git producers test provenance and refusal, never physical capability."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
import sys

import pytest

from masck_one.cleansing_capabilities import (
    CAPABILITY_PATH, CAPABILITY_SCHEMA, REQUIRED_OWNERS, SNAPSHOT_SCHEMA,
    CapabilityError, bind_capabilities, compile_source_bound_plan, source_blob,
)
from masck_one.regional_cleansing import Burden, Envelope, Region

DOMAIN = "SYNTHETIC_GIT_CELLS_NOT_ANATOMY"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE).decode().strip()


class Producers:
    def __init__(self, root):
        self.root = root
        git(root, "init", "-q")
        git(root, "config", "user.name", "Synthetic Test")
        git(root, "config", "user.email", "synthetic@example.invalid")
        self.source = root / "registered_cells.json"
        self.source.write_text('{"scope":"SYNTHETIC","cells":["a","b"]}\n')
        git(root, "add", ".")
        git(root, "commit", "-qm", "synthetic registration")
        _, self.identity = source_blob(root, git(root, "rev-parse", "HEAD"), self.source.name)
        self.path = root / CAPABILITY_PATH
        self.path.parent.mkdir(parents=True)
        self.snapshot = {"schema": SNAPSHOT_SCHEMA, "owners": {}}
        self.heads = {}
        self.records = {}
        self.regions = {c: Region(c, frozenset({c}), domain_id=DOMAIN) for c in ("a", "b")}
        for owner in REQUIRED_OWNERS:
            rows = []
            for kind in ("CLEAN", "RINSE", "RECOVER"):
                target = ["a"] if owner == "treatment" else []
                incidental = ["b"] if owner == "frame" else []
                rows.append({"action_id": kind.lower(), "kind": kind, "channel_id": "synthetic",
                             "role": "ACTUATOR" if owner == "treatment" else "SUPPORT",
                             "motion": "MOVING" if owner == "treatment" else "STATIONARY",
                             "evidence_status": "DIGITAL_REGISTERED",
                             "evidence_paths": [self.source.name],
                             "target_cells": target, "incidental_cells": incidental,
                             "affected_cells": target + incidental, "blocked_cells": [],
                             "increment": asdict(Burden(water_ml=1, passes=1)) if owner == "treatment" else None,
                             "complexity": 1})
            self.records[owner] = {"schema": CAPABILITY_SCHEMA, "owner": owner,
                                   "status": "DIGITAL_REGISTERED", "evidence": "DIGITAL",
                                   "physical_result": None, "domain_id": DOMAIN,
                                   "source_files": [self.identity], "actions": rows}
            self.commit(owner)

    def commit(self, owner, raw=None):
        self.path.write_text(raw if raw is not None else json.dumps(self.records[owner], sort_keys=True))
        git(self.root, "add", ".")
        git(self.root, "commit", "--allow-empty", "-qm", "synthetic " + owner)
        head = git(self.root, "rev-parse", "HEAD")
        self.heads[owner] = head
        self.snapshot["owners"][owner] = {"head": head, "sources": [deepcopy(self.identity)]}
        return head

    def bind(self):
        return bind_capabilities(self.root, self.snapshot, self.heads, self.regions)

    def compile(self, **kwargs):
        maximum = Burden(water_ml=10, passes=10)
        policy = Envelope("synthetic", "a" * 64, "BASELINE", maximum, 1, 1, 1, 1)
        return compile_source_bound_plan(self.root, self.snapshot, self.heads, self.regions,
                                         envelopes={k: policy for k in self.regions},
                                         session_water_ml=10, session_cleanser_ml=10, **kwargs)


@pytest.fixture
def p(tmp_path):
    return Producers(tmp_path)


def blocked(p, reason):
    binding = p.bind()
    assert binding.actions == ()
    assert binding.receipt["actions"] == []
    assert any(reason in b["reason"] for b in binding.receipt["blockers"]), binding.receipt
    out = p.compile()
    assert out["outcome"] == "BLOCKED_UNQUALIFIED"
    assert out["steps"] == []
    assert out["human_use_eligible"] is False
    assert out["physical_result"] is None


def test_committed_incidental_contact_reaches_compiler(p):
    out = p.compile()
    assert out["outcome"] == "PLAN_COMPILED"
    assert len(out["steps"]) == 3
    assert all(row["cells"] == ["a", "b"] for row in out["steps"])
    assert all(row["regions"] == ["a", "b"] for row in out["steps"])
    assert len(out["capability_binding"]["owners"]) == len(REQUIRED_OWNERS)
    assert out["physical_result"] is None and out["human_use_eligible"] is False


def test_no_caller_action_override_exists(p):
    with pytest.raises(TypeError):
        p.compile(actions=[])


def test_local_footprint_edits_cannot_narrow_committed_reach(p):
    p.path.write_text('{"actions":[]}')
    p.source.write_text('{}')
    assert all(a.cells == frozenset({"a", "b"}) for a in p.bind().actions)


@pytest.mark.parametrize("owner", REQUIRED_OWNERS)
def test_omitted_owner_never_means_clear(p, owner):
    del p.snapshot["owners"][owner]
    blocked(p, "REQUIRED_OWNER_SET_MISMATCH")


def test_missing_current_head_is_not_a_historical_pass(p):
    del p.heads["frame"]
    blocked(p, "CURRENT_PRODUCER_HEAD_REQUIRED")


def test_producer_movement_invalidates_even_when_source_bytes_unchanged(p):
    old = deepcopy(p.snapshot["owners"]["frame"])
    p.commit("frame")
    p.snapshot["owners"]["frame"] = old
    blocked(p, "STALE_PRODUCER_HEAD")


@pytest.mark.parametrize("field,value", [("head", "123abc"), ("git_blob", "f" * 40), ("sha256", "f" * 64)])
def test_wrong_source_identity_cannot_bind(p, field, value):
    if field == "head":
        p.heads["frame"] = p.snapshot["owners"]["frame"][field] = value
        reason = "CURRENT_PRODUCER_HEAD_REQUIRED"
    else:
        p.snapshot["owners"]["frame"]["sources"][0][field] = value
        reason = "SOURCE_BINDING_MISMATCH"
    blocked(p, reason)


def test_absent_capability_artifact_reports_an_unresolved_owner(p):
    head = git(p.root, "rev-list", "--max-parents=0", "HEAD")
    p.heads["thermal"] = p.snapshot["owners"]["thermal"]["head"] = head
    blocked(p, "SOURCE_PATH_MISSING")
    row = next(r for r in p.bind().receipt["owners"] if r["owner"] == "thermal")
    assert row["status"] == "UNRESOLVED_OWNER_CAPABILITY"
    assert row["source_binding_status"] == "EXACT_COMMIT_BLOBS_VERIFIED"


@pytest.mark.parametrize("field,value,reason", [
    ("owner", "treatment", "IDENTITY_MISMATCH"),
    ("status", "UNKNOWN", "UNRESOLVED_OWNER_CAPABILITY"),
    ("evidence", "BENCH", "UNRESOLVED_OWNER_CAPABILITY"),
    ("physical_result", "PASS", "UNRESOLVED_OWNER_CAPABILITY"),
    ("domain_id", "different", "REGION_DOMAIN_MISMATCH"),
    ("actions", [], "OWNER_ACTION_CATALOG_REQUIRED"),
])
def test_unregistered_owner_record_cannot_be_promoted(p, field, value, reason):
    p.records["frame"][field] = value
    p.commit("frame")
    blocked(p, reason)


@pytest.mark.parametrize("field,value,reason", [
    ("incidental_cells", [], "INCOMPLETE_AFFECTED_FOOTPRINT"),
    ("affected_cells", [], "INCOMPLETE_AFFECTED_FOOTPRINT"),
    ("incidental_cells", None, "UNKNOWN_OR_INVALID_CELLS"),
    ("blocked_cells", None, "UNKNOWN_OR_INVALID_CELLS"),
    ("blocked_cells", ["a"], "SOURCE_BLOCKED_ACTION"),
    ("evidence_status", "UNKNOWN", "UNRESOLVED_ACTION_CAPABILITY"),
    ("motion", "UNKNOWN", "UNRESOLVED_MOTION_OR_ROLE"),
    ("evidence_paths", [], "UNBOUND_FOOTPRINT_EVIDENCE"),
    ("evidence_paths", ["unbound.json"], "UNBOUND_FOOTPRINT_EVIDENCE"),
    ("channel_id", "other", "OWNER_ACTION_IDENTITY_MISMATCH"),
    ("role", "NO_CONTACT", "NO_CONTACT_HAS_FOOTPRINT"),
])
def test_hostile_owner_footprint_rows_fail_closed(p, field, value, reason):
    p.records["frame"]["actions"][0][field] = value
    p.commit("frame")
    blocked(p, reason)


def test_omitting_one_owners_action_does_not_erase_its_contact(p):
    p.records["frame"]["actions"].pop()
    p.commit("frame")
    blocked(p, "OWNER_ACTION_FOOTPRINT_OMITTED")


def test_removing_incidental_region_from_caller_map_fails(p):
    del p.regions["b"]
    blocked(p, "unregistered cells: b")


@pytest.mark.parametrize("classification", ["PROTECTED", "EXCLUDED"])
def test_incidental_protected_or_excluded_contact_fails(p, classification):
    p.regions["b"] = replace(p.regions["b"], classification=classification, exclusion_reason="synthetic")
    blocked(p, "PROTECTED_OR_EXCLUDED_CELL_AFFECTED")


@pytest.mark.parametrize("value", [None, {}, {"water_ml": 1}])
def test_unknown_burden_is_not_zero_filled(p, value):
    p.records["treatment"]["actions"][0]["increment"] = value
    p.commit("treatment")
    blocked(p, "COMPLETE_BURDEN_REQUIRED")


def test_source_update_cannot_reuse_old_registration_receipt(p):
    p.source.write_text('{"scope":"CHANGED_SYNTHETIC"}')
    head = p.commit("frame")
    _, identity = source_blob(p.root, head, p.source.name)
    p.snapshot["owners"]["frame"]["sources"] = [identity]
    blocked(p, "SOURCE_BINDING_MISMATCH")


def test_committed_symlink_cannot_replace_capability_data(p):
    p.path.unlink()
    p.path.symlink_to(p.source)
    git(p.root, "add", ".")
    git(p.root, "commit", "-qm", "synthetic symlink")
    p.heads["frame"] = p.snapshot["owners"]["frame"]["head"] = git(p.root, "rev-parse", "HEAD")
    blocked(p, "SOURCE_NOT_REGULAR_BLOB")


def test_duplicate_json_key_is_not_silently_last_writer_wins(p):
    raw = json.dumps(p.records["frame"])
    p.commit("frame", raw[:-1] + ',"owner":"frame"}')
    blocked(p, "DUPLICATE_JSON_KEY")


def test_reordered_inventory_does_not_change_plan(p):
    before = p.compile()
    p.snapshot["owners"] = dict(reversed(list(p.snapshot["owners"].items())))
    p.regions = dict(reversed(list(p.regions.items())))
    assert p.compile() == before


@pytest.mark.parametrize("path", ["../registered_cells.json", "/registered_cells.json", "a//b", "a/./b"])
def test_invalid_source_path_is_rejected_before_git(p, path):
    with pytest.raises(CapabilityError, match="INVALID_SOURCE_PATH"):
        source_blob(p.root, p.heads["frame"], path)


@pytest.mark.parametrize("missing", [False, True])
def test_preflight_cli_preserves_blockers_and_exit_status(p, missing):
    if missing:
        del p.snapshot["owners"]["frame"]
    snapshot = p.root / "snapshot.json"
    heads = p.root / "heads.json"
    regions = p.root / "regions.json"
    snapshot.write_text(json.dumps(p.snapshot))
    heads.write_text(json.dumps(p.heads))
    regions.write_text(json.dumps([{**asdict(r), "cells": sorted(r.cells)} for r in p.regions.values()]))
    tool = Path(__file__).resolve().parents[1] / "tools/cs018_capability_preflight.py"
    result = subprocess.run([sys.executable, str(tool), "--repo", str(p.root),
                             "--snapshot", str(snapshot), "--live-heads", str(heads),
                             "--regions", str(regions)], capture_output=True, text=True)
    out = json.loads(result.stdout)
    assert result.returncode == (2 if missing else 0), result.stderr
    assert bool(out["blockers"]) is missing
    assert len(out["actions"]) == (0 if missing else 3)
    assert out["physical_result"] is None and out["human_use_eligible"] is False
