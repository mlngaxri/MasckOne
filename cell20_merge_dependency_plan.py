from __future__ import annotations

"""Machine-checkable Cell 20 merge/dependency plan.

This module is a deterministic snapshot of live GitHub navigation evidence. It does
not promote candidate branches into release authority. Every candidate must be
reconstructed against live main and rerun after any upstream merge before promotion.
"""

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re
from typing import Iterable


SCHEMA = "MASCK_ONE_CELL20_MERGE_DEPENDENCY_PLAN_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
OBSERVED_AT_UTC = "2026-09-06T04:23:00Z"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

CI_SUCCESS = "SUCCESS"
CI_IN_PROGRESS = "IN_PROGRESS"
CI_QUEUED = "QUEUED"
CI_FAILURE = "FAILURE"
CI_CANCELLED = "CANCELLED"

ACTION_ROOT_FIRST = "ROOT_FIRST_AFTER_EXACT_HEAD_GREEN_REVIEW"
ACTION_REBASE_RETEST = "REBASE_RECONSTRUCT_RETEST_AFTER_DEPENDENCIES"
ACTION_REPAIR_REBASE_RETEST = "REPAIR_THEN_REBASE_RECONSTRUCT_RETEST"
ACTION_HOLD_REDESIGN = "HOLD_FOR_OWNING_GEOMETRY_REDESIGN"
ACTION_LATE_REBIND = "LATE_REBIND_AFTER_GEOMETRY_STABILIZES"


class MergePlanError(ValueError):
    """Raised when merge ordering could permit stale or dependency-invalid release."""


@dataclass(frozen=True)
class MergeCandidate:
    pr_number: int
    head_sha: str
    phase: int
    role: str
    ci_state: str
    exact_head_green: bool
    action: str
    depends_on: tuple[int, ...] = ()
    blockers: tuple[str, ...] = ()
    release_eligible_now: bool = False

    def __post_init__(self) -> None:
        if self.pr_number <= 0:
            raise MergePlanError("PR number must be positive")
        if SHA_RE.fullmatch(self.head_sha) is None:
            raise MergePlanError(f"PR #{self.pr_number} head must be an exact 40-character SHA")
        if self.phase < 0:
            raise MergePlanError(f"PR #{self.pr_number} phase must be non-negative")
        if self.pr_number in self.depends_on:
            raise MergePlanError(f"PR #{self.pr_number} cannot depend on itself")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise MergePlanError(f"PR #{self.pr_number} has duplicate dependencies")
        if self.exact_head_green != (self.ci_state == CI_SUCCESS):
            raise MergePlanError(f"PR #{self.pr_number} green state must match CI state")
        if self.release_eligible_now:
            raise MergePlanError(
                f"PR #{self.pr_number} cannot be merge-now eligible while release-control root #121 is unreleased"
            )


@dataclass(frozen=True)
class CollapseGroup:
    source_prs: tuple[int, ...]
    successor_pr: int | None
    action: str
    reason: str

    def __post_init__(self) -> None:
        if not self.source_prs or any(number <= 0 for number in self.source_prs):
            raise MergePlanError("collapse groups require positive source PR numbers")
        if len(set(self.source_prs)) != len(self.source_prs):
            raise MergePlanError("collapse groups cannot repeat a source PR")
        if self.successor_pr is not None and self.successor_pr in self.source_prs:
            raise MergePlanError("collapse successor cannot also be a collapsed source")


# CI state is exact-head navigation evidence only. A green head is not merge-now
# evidence because #121 intentionally changes the provenance gate and therefore
# invalidates downstream promotion evidence once released.
CANDIDATES: tuple[MergeCandidate, ...] = (
    MergeCandidate(
        121, "762e682e0d0d3ec9ff77edf2fc4dba2ee706bd01", 0,
        "exact source-tree CI provenance repair", CI_IN_PROGRESS, False, ACTION_ROOT_FIRST,
        blockers=("exact-head engineering CI and independent review are not complete",),
    ),
    MergeCandidate(
        120, "90d20231710a24bbf02ba0c9ae52ef8b37f0ce73", 1,
        "canonical component/material composer", CI_SUCCESS, True, ACTION_REBASE_RETEST,
        depends_on=(121,),
        blockers=("current green run predates the #121 exact-source provenance gate",),
    ),
    MergeCandidate(
        117, "34273de3bd86294080e51873c212e988b4a966f4", 2,
        "structural reaction-loop B-rep producer", CI_SUCCESS, True, ACTION_REBASE_RETEST,
        depends_on=(120,),
        blockers=("frame-shell joins and actuator/retention counterparts remain unresolved",),
    ),
    MergeCandidate(
        107, "22d2e5baccbcfa56aa4a70e4e4dd59693e15affd", 2,
        "fresh-water source body/lid and source datums", CI_SUCCESS, True, ACTION_REBASE_RETEST,
        depends_on=(120,),
        blockers=("selected pump/manifold route realization remains unresolved",),
    ),
    MergeCandidate(
        118, "37e03df4b6abbd222422c8bfd4e70b03a4e5ae07", 3,
        "local actuator carrier split/capture template", CI_SUCCESS, True, ACTION_REBASE_RETEST,
        depends_on=(117, 120),
        blockers=("all current world placements remain protected-conflicted and world_mount_eligible=false",),
    ),
    MergeCandidate(
        123, "25686766238b66ecf900009042d721c08e042592", 3,
        "current-main occipital yoke producer", CI_QUEUED, False, ACTION_REBASE_RETEST,
        depends_on=(117, 120),
        blockers=("positive frame root counterpart remains unresolved",),
    ),
    MergeCandidate(
        125, "3703f9b45defc91e05fbbe4516d28cd012db2efd", 3,
        "cleanser cassette/body with bayonet retention", CI_QUEUED, False, ACTION_REBASE_RETEST,
        depends_on=(120,),
        blockers=("cradle-to-frame positive attachment remains unresolved",),
    ),
    MergeCandidate(
        70, "7361ad3ae3aa91373cd9e723179e19b0554ec1b4", 3,
        "five-station exterior and rear service skin", CI_FAILURE, False, ACTION_REPAIR_REBASE_RETEST,
        depends_on=(120,),
        blockers=(
            "exact-head CI fails: eye-rolled exterior becomes invalid after protected eye 1/second-eye operation",
            "tooling/part split/draft and real dry-side nesting/service remain unresolved",
        ),
    ),
    MergeCandidate(
        109, "fb586cc1ea1cde92526417593f9e5aa990d2ae4f", 4,
        "retention hazard guards and factory-install sweeps", CI_SUCCESS, True, ACTION_REPAIR_REBASE_RETEST,
        depends_on=(117, 123),
        blockers=(
            "PR #123 measured about 39.840676 mm3 interference per side between the pure-X adjustment-guard installation sweep and yoke",
            "factory order/trajectory and positive frame attachment must be resolved before promotion",
        ),
    ),
    MergeCandidate(
        92, "ce1a175a79f87da65d88a40eca146f3dc5419528", 5,
        "retention fit/hair/load-path integration lineage", CI_CANCELLED, False, ACTION_REPAIR_REBASE_RETEST,
        depends_on=(117, 118, 123, 109),
        blockers=(
            "reconstruct after released yoke/guard producers to avoid duplicate geometry truth",
            "carrier separation/reassembly and whole retention path remain open",
        ),
    ),
    MergeCandidate(
        111, "fa017c8379dabaefeecf53bf770858bebfde3067", 5,
        "compact dry-side carrier and battery service package", CI_IN_PROGRESS, False, ACTION_REBASE_RETEST,
        depends_on=(121, 120, 117, 70),
        blockers=(
            "PR explicitly requires #121 to release before promotion evidence is valid",
            "rear closure is owned by Cell 2, so repaired exterior/dry-side reconciliation must precede promotion",
        ),
    ),
    MergeCandidate(
        110, "7b32c674860cab87cbdd1f7e3303a4ce53515e95", 6,
        "HMI/WARM physical-package decision state", CI_SUCCESS, True, ACTION_REBASE_RETEST,
        depends_on=(111,),
        blockers=("final control hardware, optics and thermal interfaces remain unselected/unrealized",),
    ),
    MergeCandidate(
        113, "dde7348002d13da77049dc1d540d79d389aac09f", 6,
        "canonical electrical interconnect endpoint registry", CI_IN_PROGRESS, False, ACTION_REBASE_RETEST,
        depends_on=(111,),
        blockers=("current registry has zero route-ready electrical mating datums",),
    ),
    MergeCandidate(
        115, "4da053e57534c98617b9e8abfae7a35436a3718c", 6,
        "waste-cartridge body/closure and cavity realization", CI_QUEUED, False, ACTION_HOLD_REDESIGN,
        depends_on=(70, 120),
        blockers=(
            "current released shell intersects cartridge body+closure by about 331.73801062482534 mm3",
            "free cavity is 27.401629 mL, 7.598371 mL below the 35 mL retained requirement",
            "even the current 1.2 mm wall zero-floor/lid-ceiling topology is about 34.887932 mL, still below 35 mL",
        ),
    ),
    MergeCandidate(
        104, "71905a2682764893fe907417948132a9694e8448", 7,
        "canonical wet/electrical released-source graph receipt", CI_IN_PROGRESS, False, ACTION_LATE_REBIND,
        depends_on=(107, 125, 111, 113, 115),
        blockers=("its specialist-head receipt is already stale to moved #111/#113/#115 heads",),
    ),
    MergeCandidate(
        105, "8d5762f35c0b64b736648ef3541377b43a168952", 7,
        "cleanser source-graph receipt", CI_SUCCESS, True, ACTION_LATE_REBIND,
        depends_on=(125,),
        blockers=("consolidate source-receipt semantics into the current Cell 4 integration graph rather than create a second route truth",),
    ),
    MergeCandidate(
        124, "330a37dc18d751852deec497ab806dda98d356ee", 8,
        "mechanical component/interface graph", CI_QUEUED, False, ACTION_LATE_REBIND,
        depends_on=(92, 117, 118, 123, 111),
        blockers=("candidate bindings self-invalidate when any producer head moves",),
    ),
    MergeCandidate(
        106, "2b2b4805405e4969d316f0cdbef7631d9da4322c", 9,
        "DFM part-family to producer reconciliation", CI_SUCCESS, True, ACTION_LATE_REBIND,
        depends_on=(70, 92, 104, 107, 111, 115, 117, 118, 125),
        blockers=("source-bound manufacturing maturity should be rebuilt after product geometry stabilizes",),
    ),
    MergeCandidate(
        116, "1f769016efb6034c1708a275465fbac6910a75da", 9,
        "datum/CTQ inventory", CI_SUCCESS, True, ACTION_LATE_REBIND,
        depends_on=(70, 92, 104, 107, 111, 115, 117, 118, 125),
        blockers=("geometry-dependent datum stacks remain unresolved and should bind final producers",),
    ),
    MergeCandidate(
        108, "0bf6c73028284ba9a5715ef5235bb2be1c298403", 9,
        "mass/CG/pitch/power/fluid ledger", CI_SUCCESS, True, ACTION_LATE_REBIND,
        depends_on=(70, 92, 104, 107, 111, 115, 117, 118, 125),
        blockers=("whole-product totals remain null until final material/component sources are released",),
    ),
    MergeCandidate(
        114, "630cc19497661ae834032eb8ea06e28dfd6100b7", 10,
        "assembly/service-motion inventory", CI_SUCCESS, True, ACTION_LATE_REBIND,
        depends_on=(92, 104, 111, 115, 123, 125),
        blockers=("current inventory binds stale retention candidate evidence and lacks released objective-domain motions",),
    ),
    MergeCandidate(
        112, "831619d5dd0386b709f415fb6de2161b282e5d1f", 10,
        "whole-product collision/protected-region matrix successor", CI_SUCCESS, True, ACTION_LATE_REBIND,
        depends_on=(70, 92, 104, 107, 111, 114, 115, 117, 118, 123, 125),
        blockers=("matrix still reports absent geometry and must run after accepted material/service bodies stabilize",),
    ),
)


COLLAPSE_GROUPS: tuple[CollapseGroup, ...] = (
    CollapseGroup((83, 87, 89), 92, "CLOSE_AS_EXACT_ANCESTORS", "PR #92 proves these closed branches are exact ancestors; never merge them independently."),
    CollapseGroup((74, 101), 120, "CLOSE_AS_SUPERSEDED_COMPONENT_COMPOSERS", "PR #120 is the current component/material composer successor."),
    CollapseGroup((103,), 120, "CLOSE_AFTER_VERIFYING_SUCCESSOR_FIX", "PR #103 is an audit of the material-boundary defect owned by #120, not a competing release truth."),
    CollapseGroup((75, 78), 107, "CLOSE_AFTER_CURRENT_MAIN_PORT", "PR #107 reconstructs the fresh-water body/lid/source geometry on current main."),
    CollapseGroup((80,), 125, "CLOSE_AFTER_CURRENT_MAIN_PORT", "PR #125 replaces the cleanser cassette friction-pin concept with bounded rotate-to-release bayonet retention."),
    CollapseGroup((77,), 106, "CLOSE_AFTER_TAXONOMY_CONSUMPTION", "PR #106 reconciles useful DFM taxonomy to current released producers."),
    CollapseGroup((90, 98), 112, "CLOSE_AFTER_SUCCESSOR_VERIFICATION", "PR #112 is the current-main collision/protected-region successor."),
    CollapseGroup((122,), 117, "CLOSE_DONOR_AUDIT_NOT_RELEASE_GEOMETRY", "The legacy frame-donor audit should not become a second structural producer once #117 is accepted."),
    CollapseGroup((85, 94, 96, 100), None, "PORT_USEFUL_PACKAGE_GEOMETRY_THEN_CLOSE", "These pump/backflow branches sit on stale base 21cf...; port only still-valid bounded geometry into current-main successors after source/package identities stabilize."),
    CollapseGroup((93,), None, "PORT_ONLY_STILL_VALID_SERVICE_KINEMATICS_THEN_CLOSE", "Do not merge the stale-base service branch as authority; preserve only reproducible continuous-motion evidence that survives current geometry."),
    CollapseGroup((63, 64), None, "DONOR_ONLY_NEVER_MERGE", "Legacy Manual A/B remain source donors only by release policy."),
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
    if 121 not in by_pr or by_pr[121].phase != 0 or by_pr[121].action != ACTION_ROOT_FIRST:
        raise MergePlanError("PR #121 must remain the phase-0 release-control root")
    for row in rows:
        for dependency in row.depends_on:
            if dependency not in by_pr:
                raise MergePlanError(f"PR #{row.pr_number} depends on unknown PR #{dependency}")
            if by_pr[dependency].phase >= row.phase:
                raise MergePlanError(
                    f"PR #{row.pr_number} phase {row.phase} must be strictly after dependency #{dependency} phase {by_pr[dependency].phase}"
                )
    if any(row.release_eligible_now for row in rows):
        raise MergePlanError("no candidate may be merge-now eligible before #121 releases")
    return tuple(sorted(rows, key=lambda row: (row.phase, row.pr_number)))


def merge_dependency_manifest() -> dict[str, object]:
    rows = validate_plan()
    collapsed_sources = [number for group in COLLAPSE_GROUPS for number in group.source_prs]
    if len(collapsed_sources) != len(set(collapsed_sources)):
        raise MergePlanError("a legacy PR cannot belong to more than one collapse group")
    if any(number in collapsed_sources for number in PRESERVE_SEPARATELY):
        raise MergePlanError("preserve-separately PR cannot also be collapsed")
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "source_main_sha": SOURCE_MAIN_SHA,
        "observed_at_utc": OBSERVED_AT_UTC,
        "world_frame_id": WORLD_FRAME_ID,
        "release_control_root_pr": 121,
        "no_merge_now": True,
        "reason_no_merge_now": "PR #121 exact-head CI/review is incomplete; releasing it first intentionally invalidates downstream promotion evidence once, minimizing total rebase churn.",
        "candidate_sequence": [asdict(row) for row in rows],
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
    parser = argparse.ArgumentParser(description="Emit the Cell 20 machine-checkable MVP merge/dependency plan")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    output = write_manifest(args.output)
    payload = merge_dependency_manifest()
    print(json.dumps({
        "output": str(output),
        "source_main_sha": payload["source_main_sha"],
        "release_control_root_pr": payload["release_control_root_pr"],
        "no_merge_now": payload["no_merge_now"],
        "exact_head_green_prs": payload["exact_head_green_prs"],
        "manifest_sha256": payload["manifest_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
