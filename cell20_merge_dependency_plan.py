from __future__ import annotations

"""Machine-checkable Cell 20 merge/dependency plan.

This is a deterministic live-navigation receipt, not subsystem release authority.
Every downstream candidate must be reconstructed on the main produced by its
predecessors, rebound to exact source blobs, and rerun before promotion.
"""

from dataclasses import asdict, dataclass
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re
from typing import Iterable

SCHEMA = "MASCK_ONE_CELL20_MERGE_DEPENDENCY_PLAN_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
OBSERVED_AT_UTC = "2026-09-06T04:38:00Z"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
ROOT_PR = 121
ROOT_HEAD_SHA = "762e682e0d0d3ec9ff77edf2fc4dba2ee706bd01"
ROOT_RUN_ID = 34010264572
ROOT_ARTIFACT_ID = 9982589534
ROOT_ARTIFACT_SHA256 = "1dac6d1933e0b09b746e5fa1917792eb1acbb65625bab00551932eac5e13cf94"
ROOT_TESTED_TREE_SHA = "862eb97560228e619d82202fc4728715ee5fa13a"
ROOT_PR_IS_DRAFT = True
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

CI_SUCCESS = "SUCCESS"
CI_IN_PROGRESS = "IN_PROGRESS"
CI_FAILURE = "FAILURE"
CI_CANCELLED = "CANCELLED"

ACTION_ROOT_FIRST = "OWNER_MARK_READY_THEN_EXPECTED_HEAD_MERGE_AFTER_LIVE_MAIN_RECHECK"
ACTION_REBASE_RETEST = "REBASE_RECONSTRUCT_RETEST_AFTER_DEPENDENCIES"
ACTION_REPAIR_REBASE_RETEST = "REPAIR_THEN_REBASE_RECONSTRUCT_RETEST"
ACTION_HOLD_REDESIGN = "HOLD_FOR_OWNING_GEOMETRY_REDESIGN"
ACTION_LATE_REBIND = "LATE_REBIND_AFTER_GEOMETRY_STABILIZES"


class MergePlanError(ValueError):
    pass


@dataclass(frozen=True)
class MergeCandidate:
    pr_number: int
    head_sha: str
    phase: int
    role: str
    ci_state: str
    action: str
    depends_on: tuple[int, ...] = ()
    blockers: tuple[str, ...] = ()
    release_evidence_complete: bool = False
    merge_permitted_now: bool = False

    @property
    def exact_head_green(self) -> bool:
        return self.ci_state == CI_SUCCESS

    def __post_init__(self) -> None:
        if self.pr_number <= 0 or SHA_RE.fullmatch(self.head_sha) is None:
            raise MergePlanError("candidate identity must contain a positive PR and exact 40-character SHA")
        if self.phase < 0 or self.pr_number in self.depends_on:
            raise MergePlanError(f"PR #{self.pr_number} has invalid phase/dependency data")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise MergePlanError(f"PR #{self.pr_number} has duplicate dependencies")
        if self.release_evidence_complete and not (
            self.pr_number == ROOT_PR
            and self.head_sha == ROOT_HEAD_SHA
            and self.phase == 0
            and self.ci_state == CI_SUCCESS
        ):
            raise MergePlanError("only the verified exact-head release-control root may carry complete release evidence")
        if self.merge_permitted_now and not self.release_evidence_complete:
            raise MergePlanError("merge permission requires complete exact-head release evidence")
        if self.merge_permitted_now and ROOT_PR_IS_DRAFT:
            raise MergePlanError("a draft release root cannot be merge-permitted")


@dataclass(frozen=True)
class CollapseGroup:
    source_prs: tuple[int, ...]
    successor_pr: int | None
    action: str
    reason: str

    def __post_init__(self) -> None:
        if not self.source_prs or len(set(self.source_prs)) != len(self.source_prs):
            raise MergePlanError("collapse group must contain unique source PRs")
        if any(number <= 0 for number in self.source_prs):
            raise MergePlanError("collapse group PRs must be positive")
        if self.successor_pr in self.source_prs:
            raise MergePlanError("collapse successor cannot also be a source")


CANDIDATES: tuple[MergeCandidate, ...] = (
    MergeCandidate(
        121, ROOT_HEAD_SHA, 0, "exact source-tree CI provenance repair", CI_SUCCESS,
        ACTION_ROOT_FIRST,
        blockers=("PR is still draft; Cell 20 will not change another cell's PR state",),
        release_evidence_complete=True,
        merge_permitted_now=False,
    ),
    MergeCandidate(
        120, "90d20231710a24bbf02ba0c9ae52ef8b37f0ce73", 1,
        "canonical component/material composer", CI_SUCCESS, ACTION_REBASE_RETEST,
        depends_on=(121,),
        blockers=("current green run predates the released #121 exact-source gate and must be rerun after #121 lands",),
    ),
    MergeCandidate(
        107, "22d2e5baccbcfa56aa4a70e4e4dd59693e15affd", 2,
        "fresh-water source body/lid and datums", CI_SUCCESS, ACTION_REBASE_RETEST,
        depends_on=(120,), blockers=("pump/manifold route realization remains unresolved",),
    ),
    MergeCandidate(
        117, "34273de3bd86294080e51873c212e988b4a966f4", 2,
        "structural reaction-loop B-rep producer", CI_SUCCESS, ACTION_REBASE_RETEST,
        depends_on=(120,), blockers=("shell/frame, actuator and retention counterpart joins remain unresolved",),
    ),
    MergeCandidate(
        70, "7361ad3ae3aa91373cd9e723179e19b0554ec1b4", 3,
        "five-station exterior and rear service skin", CI_FAILURE, ACTION_REPAIR_REBASE_RETEST,
        depends_on=(120,), blockers=(
            "exact-head CI fails because bilateral protected-eye roll processing produces an invalid solid",
            "tooling/part split/draft and real dry-side nesting/service remain unresolved",
        ),
    ),
    MergeCandidate(
        118, "37e03df4b6abbd222422c8bfd4e70b03a4e5ae07", 3,
        "local actuator carrier split/capture template", CI_SUCCESS, ACTION_REBASE_RETEST,
        depends_on=(117, 120), blockers=("current world placements remain protected-conflicted and world_mount_eligible=false",),
    ),
    MergeCandidate(
        123, "25686766238b66ecf900009042d721c08e042592", 3,
        "current-main occipital yoke producer", CI_IN_PROGRESS, ACTION_REBASE_RETEST,
        depends_on=(117, 120), blockers=("positive frame root counterpart remains unresolved",),
    ),
    MergeCandidate(
        125, "3703f9b45defc91e05fbbe4516d28cd012db2efd", 3,
        "cleanser cassette/body with bayonet retention", CI_IN_PROGRESS, ACTION_REBASE_RETEST,
        depends_on=(120,), blockers=("cradle-to-frame positive attachment remains unresolved",),
    ),
    MergeCandidate(
        109, "fb586cc1ea1cde92526417593f9e5aa990d2ae4f", 4,
        "retention hazard guards and factory-install sweeps", CI_SUCCESS, ACTION_REPAIR_REBASE_RETEST,
        depends_on=(117, 123), blockers=(
            "PR #123 measures about 39.840676 mm3 yoke interference per side with the pure-X adjustment-guard factory installation sweep",
            "factory order/trajectory and positive frame attachment remain unresolved",
        ),
    ),
    MergeCandidate(
        92, "ce1a175a79f87da65d88a40eca146f3dc5419528", 5,
        "retention fit/hair/load-path integration lineage", CI_CANCELLED, ACTION_REPAIR_REBASE_RETEST,
        depends_on=(117, 118, 123, 109), blockers=(
            "reconstruct after yoke/guard producers to avoid duplicate geometry truth",
            "carrier separation/reassembly and whole retention path remain open",
        ),
    ),
    MergeCandidate(
        111, "fa017c8379dabaefeecf53bf770858bebfde3067", 5,
        "compact dry-side carrier and battery service package", CI_IN_PROGRESS, ACTION_REBASE_RETEST,
        depends_on=(121, 120, 117, 70), blockers=(
            "promotion evidence must be regenerated after #121 release",
            "visible rear closure is owned by Cell 2 and requires repaired exterior reconciliation",
        ),
    ),
    MergeCandidate(
        110, "7b32c674860cab87cbdd1f7e3303a4ce53515e95", 6,
        "HMI/WARM physical-package decision state", CI_SUCCESS, ACTION_REBASE_RETEST,
        depends_on=(111,), blockers=("final control hardware, optics and thermal interfaces remain unselected/unrealized",),
    ),
    MergeCandidate(
        113, "dde7348002d13da77049dc1d540d79d389aac09f", 6,
        "canonical electrical interconnect endpoint registry", CI_IN_PROGRESS, ACTION_REBASE_RETEST,
        depends_on=(111,), blockers=("current registry has zero route-ready electrical mating datums",),
    ),
    MergeCandidate(
        115, "4da053e57534c98617b9e8abfae7a35436a3718c", 6,
        "waste-cartridge body/closure and cavity realization", CI_IN_PROGRESS, ACTION_HOLD_REDESIGN,
        depends_on=(70, 120), blockers=(
            "released shell intersects cartridge body+closure by about 331.73801062482534 mm3",
            "free cavity is 27.401629 mL, 7.598371 mL below the 35 mL retained requirement",
            "current 1.2 mm wall zero-floor/lid-ceiling topology reaches only about 34.887932 mL",
        ),
    ),
    MergeCandidate(
        104, "71905a2682764893fe907417948132a9694e8448", 7,
        "canonical wet/electrical released-source graph receipt", CI_IN_PROGRESS, ACTION_LATE_REBIND,
        depends_on=(107, 125, 111, 113, 115),
        blockers=("specialist-head receipt is stale to moved #111/#113/#115 heads",),
    ),
    MergeCandidate(
        124, "330a37dc18d751852deec497ab806dda98d356ee", 8,
        "mechanical component/interface graph", CI_FAILURE, ACTION_REPAIR_REBASE_RETEST,
        depends_on=(92, 117, 118, 123, 111), blockers=(
            "exact run 34010753193 fails 3 tests and skips CAD smoke",
            "graph carries a stale #123 candidate receipt and inconsistent guard factory-motion status expectations",
            "whole-head hostile fixture attempts candidate-continuous motion while retaining unresolved blocker IDs",
        ),
    ),
    MergeCandidate(
        106, "2b2b4805405e4969d316f0cdbef7631d9da4322c", 9,
        "DFM part-family to producer reconciliation", CI_SUCCESS, ACTION_LATE_REBIND,
        depends_on=(70, 92, 104, 107, 111, 115, 117, 118, 125),
        blockers=("manufacturing maturity must be rebound after geometry stabilizes",),
    ),
    MergeCandidate(
        108, "0bf6c73028284ba9a5715ef5235bb2be1c298403", 9,
        "mass/CG/pitch/power/fluid ledger", CI_SUCCESS, ACTION_LATE_REBIND,
        depends_on=(70, 92, 104, 107, 111, 115, 117, 118, 125),
        blockers=("whole-product totals remain null until final material/component sources release",),
    ),
    MergeCandidate(
        116, "1f769016efb6034c1708a275465fbac6910a75da", 9,
        "datum/CTQ inventory", CI_SUCCESS, ACTION_LATE_REBIND,
        depends_on=(70, 92, 104, 107, 111, 115, 117, 118, 125),
        blockers=("geometry-dependent datum stacks must bind final producers",),
    ),
    MergeCandidate(
        114, "630cc19497661ae834032eb8ea06e28dfd6100b7", 10,
        "assembly/service-motion inventory", CI_SUCCESS, ACTION_LATE_REBIND,
        depends_on=(92, 104, 111, 115, 123, 125),
        blockers=("inventory binds stale retention candidate evidence and lacks released objective-domain motions",),
    ),
    MergeCandidate(
        112, "831619d5dd0386b709f415fb6de2161b282e5d1f", 11,
        "whole-product collision/protected-region matrix successor", CI_SUCCESS, ACTION_LATE_REBIND,
        depends_on=(70, 92, 104, 107, 111, 114, 115, 117, 118, 123, 125),
        blockers=("matrix must run only after accepted material and service-sweep bodies stabilize",),
    ),
)

COLLAPSE_GROUPS: tuple[CollapseGroup, ...] = (
    CollapseGroup((83, 87, 89), 92, "CLOSE_AS_EXACT_ANCESTORS", "#92 proves these closed retention branches are exact ancestors."),
    CollapseGroup((74, 101), 120, "CLOSE_AS_SUPERSEDED_COMPONENT_COMPOSERS", "#120 is the current component/material composer successor."),
    CollapseGroup((103,), 120, "CLOSE_AFTER_VERIFYING_SUCCESSOR_FIX", "#103 audits the material-boundary defect owned by #120."),
    CollapseGroup((75, 78), 107, "CLOSE_AFTER_CURRENT_MAIN_PORT", "#107 reconstructs the useful fresh-water geometry on current main."),
    CollapseGroup((80,), 125, "CLOSE_AFTER_CURRENT_MAIN_PORT", "#125 replaces the cleanser friction-pin concept with bounded bayonet retention."),
    CollapseGroup((105,), 104, "CONSOLIDATE_SOURCE_RECEIPT_THEN_CLOSE", "Consolidate useful cleanser source identity into #104 rather than merge a second route truth."),
    CollapseGroup((77,), 106, "CLOSE_AFTER_TAXONOMY_CONSUMPTION", "#106 reconciles useful DFM taxonomy to current producers."),
    CollapseGroup((90, 98), 112, "CLOSE_AFTER_SUCCESSOR_VERIFICATION", "#112 is the current-main collision/protected-region successor."),
    CollapseGroup((122,), 117, "CLOSE_DONOR_AUDIT_NOT_RELEASE_GEOMETRY", "Do not create a second structural producer once #117 is accepted."),
    CollapseGroup((85, 94, 96, 100), None, "PORT_USEFUL_PACKAGE_GEOMETRY_THEN_CLOSE", "Port only still-valid pump/backflow geometry from stale-base branches into current-main successors."),
    CollapseGroup((93,), None, "PORT_ONLY_STILL_VALID_SERVICE_KINEMATICS_THEN_CLOSE", "Preserve only continuous service evidence that survives current geometry."),
    CollapseGroup((63, 64), None, "DONOR_ONLY_NEVER_MERGE", "Legacy Manual A/B remain donor material only."),
)

PRESERVE_SEPARATELY: tuple[int, ...] = (71,)
FINAL_AUDIT_ORDER: tuple[str, ...] = (
    "rebind DFM and CTQ inventories to final accepted producer blobs",
    "recompute mass/CG/pitch/power/fluid ledgers without filling unknowns",
    "rerun continuous assembly/service inventory",
    "rerun whole-product collision/protected matrix on final accepted material and sweeps",
    "reconstruct Cell 20 MVP completeness matrix on the resulting exact main",
    "run deterministic export/Fusion handoff and exact-head independent release review",
)


def validate_plan(candidates: Iterable[MergeCandidate] = CANDIDATES) -> tuple[MergeCandidate, ...]:
    rows = tuple(candidates)
    by_pr: dict[int, MergeCandidate] = {}
    for row in rows:
        row.__post_init__()
        if row.pr_number in by_pr:
            raise MergePlanError(f"duplicate PR #{row.pr_number}")
        by_pr[row.pr_number] = row
    root = by_pr.get(ROOT_PR)
    if root is None or root.phase != 0 or root.action != ACTION_ROOT_FIRST or not root.release_evidence_complete:
        raise MergePlanError("verified #121 must remain the sole phase-0 release root")
    if any(row.release_evidence_complete for row in rows if row.pr_number != ROOT_PR):
        raise MergePlanError("no downstream candidate may inherit root release evidence")
    if any(row.merge_permitted_now for row in rows):
        raise MergePlanError("no merge is permitted while the verified root remains draft")
    for row in rows:
        for dependency in row.depends_on:
            if dependency not in by_pr:
                raise MergePlanError(f"PR #{row.pr_number} depends on unknown PR #{dependency}")
            if by_pr[dependency].phase >= row.phase:
                raise MergePlanError(
                    f"PR #{row.pr_number} phase {row.phase} must be strictly after dependency #{dependency} phase {by_pr[dependency].phase}"
                )
    return tuple(sorted(rows, key=lambda row: (row.phase, row.pr_number)))


def merge_dependency_manifest() -> dict[str, object]:
    rows = validate_plan()
    collapsed = [number for group in COLLAPSE_GROUPS for number in group.source_prs]
    if len(collapsed) != len(set(collapsed)):
        raise MergePlanError("a legacy PR cannot belong to more than one collapse group")
    if any(number in collapsed for number in PRESERVE_SEPARATELY):
        raise MergePlanError("preserve-separately PR cannot also be collapsed")
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "source_main_sha": SOURCE_MAIN_SHA,
        "observed_at_utc": OBSERVED_AT_UTC,
        "world_frame_id": WORLD_FRAME_ID,
        "next_release_root_pr": ROOT_PR,
        "next_release_expected_head_sha": ROOT_HEAD_SHA,
        "next_release_root_evidence_complete": True,
        "next_release_pr_is_draft": ROOT_PR_IS_DRAFT,
        "merge_permitted_now_prs": [],
        "required_owner_transition": "MARK_PR_121_READY_FOR_REVIEW_WITHOUT_MOVING_ITS_HEAD",
        "required_post_transition_check": "RECHECK_LIVE_MAIN_AND_EXACT_HEAD_BEFORE_EXPECTED_HEAD_MERGE",
        "downstream_merge_hold": True,
        "verified_root_evidence": {
            "workflow_run_id": ROOT_RUN_ID,
            "artifact_id": ROOT_ARTIFACT_ID,
            "artifact_sha256": ROOT_ARTIFACT_SHA256,
            "tested_tree_sha": ROOT_TESTED_TREE_SHA,
            "source_base_is_ancestor_of_source_head": True,
            "source_head_tree_equals_tested_tree": True,
        },
        "candidate_sequence": [asdict(row) | {"exact_head_green": row.exact_head_green} for row in rows],
        "exact_head_green_prs": [row.pr_number for row in rows if row.exact_head_green],
        "collapse_groups": [asdict(group) for group in COLLAPSE_GROUPS],
        "preserve_separately": list(PRESERVE_SEPARATELY),
        "final_audit_order": list(FINAL_AUDIT_ORDER),
        "stale_evidence_policy": "ANY_MAIN_OR_UPSTREAM_HEAD_MOVEMENT_INVALIDATES_PROMOTION_CI_REVIEW_COLLISION_SERVICE_DFM_LEDGER_AND_PROVENANCE_EVIDENCE",
        "physical_evidence_policy": "DIGITAL_SEQUENCE_DOES_NOT_CLOSE_PHYSICAL_SUPPLIER_HUMAN_MATERIAL_SAFETY_OR_PERFORMANCE_GATES",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    payload["manifest_sha256"] = sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def write_manifest(path: str | Path) -> Path:
    output = Path(path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(merge_dependency_manifest(), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit Cell 20 MVP merge/dependency plan")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    output = write_manifest(args.output)
    payload = merge_dependency_manifest()
    print(json.dumps({
        "output": str(output),
        "source_main_sha": payload["source_main_sha"],
        "next_release_root_pr": payload["next_release_root_pr"],
        "next_release_pr_is_draft": payload["next_release_pr_is_draft"],
        "merge_permitted_now_prs": payload["merge_permitted_now_prs"],
        "manifest_sha256": payload["manifest_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
