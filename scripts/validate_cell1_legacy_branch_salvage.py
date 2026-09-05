#!/usr/bin/env python3
"""Validate Cell 1 legacy-branch salvage and successor dispositions.

This is release-control validation, not product or physical evidence. It prevents stale,
self-certified, partial-port, or otherwise non-release-safe work from being promoted merely
because GitHub can mechanically merge it or because a successor branch exists.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = ROOT / "config" / "cell1_legacy_branch_salvage_map.json"
SCHEMA = "MASCK_ONE_CELL1_LEGACY_BRANCH_SALVAGE_MAP_V2"
CLASSIFICATIONS = {"MERGEABLE", "PORTABLE", "SUPERSEDED", "REJECT"}
CI_CONCLUSIONS = {"SUCCESS", "FAILURE", "IN_PROGRESS", "NOT_RUN", "NOT_APPLICABLE"}
SUCCESSOR_COVERAGE = {"FULL_PORT", "PARTIAL_PORT"}
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class SalvageMapError(ValueError):
    """Raised when the salvage map would permit stale or overstated release truth."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SalvageMapError(message)


def _sha(value: object, label: str) -> str:
    _require(
        isinstance(value, str) and _SHA_RE.fullmatch(value) is not None,
        f"{label} must be a canonical 40-character lowercase git SHA",
    )
    return value


def _nonblank(value: object, label: str) -> str:
    _require(
        isinstance(value, str) and value == value.strip() and bool(value),
        f"{label} must be exact nonblank text",
    )
    return value


def load_salvage_map(path: Path = DEFAULT_MAP) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    _require(type(data) is dict, "salvage map root must be an object")
    return data


def validate_salvage_map(data: dict[str, Any]) -> None:
    _require(data.get("schema") == SCHEMA, "unexpected salvage-map schema")
    _nonblank(data.get("authority_revision"), "authority_revision")
    _sha(data.get("authority_blob_sha"), "authority_blob_sha")
    reconstructed_main = _sha(data.get("reconstructed_main_sha"), "reconstructed_main_sha")
    _sha(data.get("released_baseline_repair_head_sha"), "released_baseline_repair_head_sha")
    _nonblank(data.get("snapshot_semantics"), "snapshot_semantics")
    _require(
        data.get("classifications") == ["MERGEABLE", "PORTABLE", "SUPERSEDED", "REJECT"],
        "classification vocabulary changed",
    )

    released = data.get("released_and_skipped")
    _require(type(released) is list, "released_and_skipped must be a list")
    released_prs: set[int] = set()
    for item in released:
        _require(type(item) is dict, "released entry must be an object")
        pr = item.get("pr")
        _require(type(pr) is int and pr > 0, "released PR must be a positive integer")
        _require(pr not in released_prs, "released PR appears more than once")
        released_prs.add(pr)
        _sha(item.get("head_sha"), f"released PR #{pr} head_sha")
        _sha(item.get("merge_sha"), f"released PR #{pr} merge_sha")
        _nonblank(item.get("reason"), f"released PR #{pr} reason")

    entries = data.get("entries")
    _require(type(entries) is list and entries, "entries must be a non-empty list")
    seen_prs: set[int] = set()
    entry_by_pr: dict[int, dict[str, Any]] = {}

    for entry in entries:
        _require(type(entry) is dict, "salvage entry must be an object")
        pr = entry.get("pr")
        _require(type(pr) is int and pr > 0, "PR must be a positive integer")
        _require(pr not in seen_prs, f"PR #{pr} appears more than once")
        _require(pr not in released_prs, f"released PR #{pr} must be skipped, not reclassified")
        seen_prs.add(pr)
        entry_by_pr[pr] = entry

        _nonblank(entry.get("title"), f"PR #{pr} title")
        _nonblank(entry.get("head_ref"), f"PR #{pr} head_ref")
        _sha(entry.get("head_sha"), f"PR #{pr} head_sha")
        _nonblank(entry.get("base_ref"), f"PR #{pr} base_ref")
        base_sha = _sha(entry.get("base_sha"), f"PR #{pr} base_sha")
        classification = entry.get("classification")
        _require(classification in CLASSIFICATIONS, f"PR #{pr} has uncontrolled classification")
        disposition = _nonblank(
            entry.get("release_disposition"), f"PR #{pr} release_disposition"
        )

        unique_work = entry.get("unique_work")
        _require(
            type(unique_work) is list and unique_work,
            f"PR #{pr} must identify unique work or explicit lack of it",
        )
        for index, item in enumerate(unique_work):
            _nonblank(item, f"PR #{pr} unique_work[{index}]")

        bindings = entry.get("source_bindings")
        _require(type(bindings) is list, f"PR #{pr} source_bindings must be a list")
        stale_geometry_bindings = 0
        unsafe_bindings = 0
        for index, binding in enumerate(bindings):
            _require(
                type(binding) is dict,
                f"PR #{pr} source binding {index} must be an object",
            )
            producer = _nonblank(
                binding.get("producer"), f"PR #{pr} source binding {index} producer"
            )
            observed = _sha(binding.get("observed_sha"), f"PR #{pr} {producer} observed_sha")
            required = _sha(binding.get("required_sha"), f"PR #{pr} {producer} required_sha")
            status = _nonblank(binding.get("status"), f"PR #{pr} {producer} status")
            geometry_dependency = binding.get("geometry_dependency")
            _require(
                type(geometry_dependency) is bool,
                f"PR #{pr} {producer} geometry_dependency must be boolean",
            )
            digest_status = _nonblank(
                binding.get("digest_status"), f"PR #{pr} {producer} digest_status"
            )
            release_safe = binding.get("release_safe")
            _require(
                type(release_safe) is bool,
                f"PR #{pr} {producer} release_safe must be boolean",
            )
            if not release_safe:
                unsafe_bindings += 1

            if observed == required:
                _require(
                    status != "STALE",
                    f"PR #{pr} {producer} cannot be stale when exact SHAs match",
                )
            else:
                _require(
                    status == "STALE",
                    f"PR #{pr} {producer} mismatched SHAs must be marked STALE",
                )
                _require(
                    not release_safe,
                    f"PR #{pr} {producer} mismatched SHAs cannot be release-safe",
                )
                if geometry_dependency:
                    stale_geometry_bindings += 1
                    _require(
                        "RECOMPUTE" in digest_status,
                        f"PR #{pr} stale geometry source {producer} must explicitly require digest recomputation",
                    )

        ci = entry.get("exact_head_ci")
        _require(type(ci) is dict, f"PR #{pr} exact_head_ci must be an object")
        run_id = ci.get("run_id")
        _require(
            type(run_id) is int and run_id > 0,
            f"PR #{pr} exact_head_ci.run_id must be positive",
        )
        conclusion = ci.get("conclusion")
        _require(
            conclusion in CI_CONCLUSIONS,
            f"PR #{pr} has uncontrolled CI conclusion",
        )
        _nonblank(ci.get("attribution"), f"PR #{pr} CI attribution")
        independent_review = _nonblank(
            entry.get("independent_review"), f"PR #{pr} independent_review"
        )
        _require(
            entry.get("physical_validation_status") == "NOT_CLAIMED",
            f"PR #{pr} cannot promote digital work to physical validation",
        )

        blockers = entry.get("blockers")
        _require(type(blockers) is list, f"PR #{pr} blockers must be a list")
        for index, blocker in enumerate(blockers):
            _nonblank(blocker, f"PR #{pr} blockers[{index}]")

        if classification == "MERGEABLE":
            _require(
                base_sha == reconstructed_main,
                f"PR #{pr} cannot be MERGEABLE from a stale main base",
            )
            _require(bindings, f"PR #{pr} cannot be MERGEABLE without explicit source bindings")
            _require(
                stale_geometry_bindings == 0,
                f"PR #{pr} cannot be MERGEABLE with stale geometry bindings",
            )
            _require(
                unsafe_bindings == 0,
                f"PR #{pr} cannot be MERGEABLE with non-release-safe source bindings",
            )
            _require(
                conclusion == "SUCCESS",
                f"PR #{pr} cannot be MERGEABLE without successful exact-head CI",
            )
            _require(
                independent_review == "APPROVED",
                f"PR #{pr} cannot be MERGEABLE without independent approval",
            )
            _require(not blockers, f"PR #{pr} cannot be MERGEABLE with open blockers")
        elif classification == "PORTABLE":
            _require(
                blockers,
                f"PR #{pr} PORTABLE work must preserve explicit release blockers",
            )
            _require(
                "MERGE" not in disposition
                or "DO_NOT_MERGE" in disposition
                or "HOLD" in disposition
                or "PORT" in disposition,
                f"PR #{pr} portable disposition must not imply unconditional merge",
            )
        elif classification == "SUPERSEDED":
            superseded_by = entry.get("superseded_by_pr")
            _require(
                type(superseded_by) is int and superseded_by > 0,
                f"PR #{pr} SUPERSEDED entry requires superseded_by_pr",
            )
        elif classification == "REJECT":
            _require(
                "DO_NOT_MERGE" in disposition,
                f"PR #{pr} REJECT entry must explicitly say DO_NOT_MERGE",
            )

    relations = data.get("successor_relations")
    _require(
        type(relations) is list and relations,
        "successor_relations must be a non-empty list",
    )
    seen_relations: set[tuple[int, int]] = set()
    full_port_legacy_prs: set[int] = set()

    for index, relation in enumerate(relations):
        _require(type(relation) is dict, f"successor relation {index} must be an object")
        legacy_pr = relation.get("legacy_pr")
        candidate_pr = relation.get("candidate_pr")
        _require(
            type(legacy_pr) is int and legacy_pr > 0,
            f"successor relation {index} legacy_pr must be positive",
        )
        _require(
            type(candidate_pr) is int and candidate_pr > 0,
            f"successor relation {index} candidate_pr must be positive",
        )
        _require(
            legacy_pr != candidate_pr,
            f"successor relation {index} cannot self-reference",
        )
        pair = (legacy_pr, candidate_pr)
        _require(pair not in seen_relations, f"successor relation {pair} appears more than once")
        seen_relations.add(pair)
        coverage = relation.get("coverage")
        _require(
            coverage in SUCCESSOR_COVERAGE,
            f"successor relation {pair} has uncontrolled coverage",
        )
        _nonblank(relation.get("status"), f"successor relation {pair} status")
        _require(
            legacy_pr in entry_by_pr,
            f"successor relation {pair} references missing legacy PR",
        )
        _require(
            candidate_pr in entry_by_pr,
            f"successor relation {pair} references missing candidate PR",
        )

        legacy = entry_by_pr[legacy_pr]
        candidate = entry_by_pr[candidate_pr]
        _require(
            candidate.get("base_ref") == "main"
            and candidate.get("base_sha") == reconstructed_main,
            f"successor PR #{candidate_pr} must be rebuilt on reconstructed current main",
        )
        _require(
            candidate.get("classification") in {"PORTABLE", "MERGEABLE"},
            f"successor PR #{candidate_pr} must remain an active release candidate",
        )

        if coverage == "FULL_PORT":
            _require(
                legacy.get("classification") == "SUPERSEDED",
                f"FULL_PORT successor requires legacy PR #{legacy_pr} to be SUPERSEDED",
            )
            _require(
                legacy.get("superseded_by_pr") == candidate_pr,
                f"FULL_PORT successor for PR #{legacy_pr} must match superseded_by_pr",
            )
            full_port_legacy_prs.add(legacy_pr)
        else:
            _require(
                legacy.get("classification") == "PORTABLE",
                f"PARTIAL_PORT successor requires legacy PR #{legacy_pr} remainder to stay PORTABLE",
            )

    for pr, entry in entry_by_pr.items():
        if entry.get("classification") == "SUPERSEDED" and pr in full_port_legacy_prs:
            continue
        if entry.get("classification") == "SUPERSEDED":
            superseded_by = entry.get("superseded_by_pr")
            _require(
                superseded_by in released_prs or superseded_by in entry_by_pr,
                f"PR #{pr} superseded_by_pr must reference released or tracked work",
            )


def main() -> int:
    data = load_salvage_map()
    validate_salvage_map(data)
    print(
        f"validated {len(data['entries'])} legacy/new branch dispositions and "
        f"{len(data['successor_relations'])} successor relations against "
        f"reconstructed main {data['reconstructed_main_sha']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
