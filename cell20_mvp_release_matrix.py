from __future__ import annotations

"""Cell 20 live candidate overlay for the released-main MVP completeness baseline.

The source-bound baseline lives in ``masck_one.mvp_completeness`` and intentionally
fails closed if released ``src/masck_one`` producers, authority, or authority schema
move. This overlay adds only non-authoritative live PR observations and updated
closure text. Candidate heads cannot satisfy released-main maturity and cannot be
used as promotion review evidence.
"""

from dataclasses import replace
from hashlib import sha256
import argparse
import json
from pathlib import Path

from masck_one.mvp_completeness import (
    AUTHORITY_BLOB_SHA,
    AUTHORITY_REVISION,
    AUTHORITY_SCHEMA_BLOB_SHA,
    EVIDENCE_STATUS,
    SOURCE_MAIN_SHA,
    WORLD_FRAME_ID,
    CandidateObservation,
    MvpCompletenessMatrix,
    RequirementStatus,
    build_mvp_completeness_matrix,
)


SCHEMA = "MASCK_ONE_CELL20_MVP_COMPLETENESS_V2"
SUPERSEDES_SCHEMA = "MASCK_ONE_CELL20_MVP_COMPLETENESS_V1"
CANDIDATE_SNAPSHOT_OBSERVED_AT_UTC = "2026-09-06T01:03:25Z"
EVIDENCE_BOUNDARY = (
    "RELEASED_MAIN_MATURITY_PLUS_NON_AUTHORITATIVE_CANDIDATE_NAVIGATION_ONLY_"
    "NOT_PHYSICAL_VALIDATION_OR_PROMOTION_REVIEW_EVIDENCE"
)

NEW_CANDIDATE_OBSERVATIONS: tuple[CandidateObservation, ...] = (
    CandidateObservation(103, "76835d6239b53b2e5900678d2912eb1b7c8c2747", "independent current release-material truth audit"),
    CandidateObservation(104, "493b2d7a91a89865238574ad50be229c9bb1d23b", "current wet and electrical released-source graph receipt"),
    CandidateObservation(105, "8d5762f35c0b64b736648ef3541377b43a168952", "current cleanser released-source graph receipt without route realization"),
    CandidateObservation(106, "87d7521994ff2fafa2df61c570ec677f6142d379", "current DFM part-family to released-producer reconciliation"),
    CandidateObservation(107, "6454d98c658143d44ef29a00cf40d009d4191164", "current-main fresh-water reservoir body and lid source-geometry candidate"),
    CandidateObservation(108, "a74e0964706170a7e233846fd2f897744159aff7", "honest mass CG pitch power and fluid ledger candidate with unresolved totals"),
    CandidateObservation(109, "a27757eb4eda54a18b3d89db70f9534e492e588f", "retention hazard-guard B-reps and exact factory-installation sweeps candidate"),
    CandidateObservation(110, "7b32c674860cab87cbdd1f7e3303a4ce53515e95", "physical-HMI and WARM decision-state reservations with no final hardware selection"),
    CandidateObservation(111, "35e61d5fa8f9c62d810aca92f259122bc1173930", "compact dry-side carrier door and battery-service sweep candidate"),
    CandidateObservation(112, "8dd69738a675c291d71bf5a7157c92b0102983ea", "current-main whole-product collision and protected-region matrix successor"),
    CandidateObservation(113, "1e17bb50c00e94439fab09a477483950f8cd163f", "current harness endpoint inventory with zero route-ready electrical mating datums"),
    CandidateObservation(114, "2ffa6c661022e3a81da3fdda53adf88df81c8b09", "current part assembly and service-motion inventory with no released objective-domain motions"),
    CandidateObservation(115, "bd4f58c5da798d0d4a5968468fc17da19518b1b6", "source-bound waste-cartridge body closure and free-cavity geometry candidate"),
    CandidateObservation(116, "1f769016efb6034c1708a275465fbac6910a75da", "current datum and CTQ inventory with geometry-dependent stacks unresolved"),
)

CANDIDATE_ADDITIONS_BY_REQUIREMENT: dict[str, tuple[int, ...]] = {
    "ARCH-004": (112,),
    "ARCH-005": (112,),
    "ARCH-006": (112,),
    "ARCH-009": (107,),
    "ARCH-011": (115,),
    "ARCH-012": (115,),
    "ARCH-013": (109,),
    "ARCH-014": (111,),
    "ARCH-015": (108,),
    "ARCH-016": (106, 116),
    "ARCH-017": (104, 107, 110, 111, 115),
    "MVP-001": (111,),
    "MVP-002": (103, 112),
    "MVP-003": (109, 111),
    "MVP-004": (116,),
    "MVP-005": (109,),
    "MVP-006": (107,),
    "MVP-007": (105,),
    "MVP-008": (115,),
    "MVP-009": (115,),
    "MVP-010": (111,),
    "MVP-011": (113,),
    "MVP-012": (110,),
    "MVP-013": (104, 107, 110, 111, 115),
    "MVP-014": (109, 111, 114, 115),
    "MVP-015": (106, 115, 116),
    "MVP-016": (116,),
    "MVP-017": (108,),
    "MVP-018": (108,),
    "MVP-019": (103, 112),
    "MVP-020": (107, 109, 110, 111, 112, 115),
}

CLOSURE_OVERRIDES: dict[str, str] = {
    "ARCH-009": "release the fresh-water source body and interfaces, then close selected pump and world-coordinate source-to-pump and pump-to-manifold route geometry",
    "ARCH-012": "consume the cartridge body and cavity only after release, then close device-side keying, seal, positive retention, continuous service motion and retained-capacity evidence",
    "ARCH-013": "release complete crown and front reaction counterparts, positive guard attachment, carrier reassembly and whole-head removal geometry",
    "MVP-001": "close exterior tooling, part split and draft and reconcile the compact rear skin with released dry-side nesting and service",
    "MVP-002": "release the corrected physical-material versus reference composer before collision or export promotion",
    "MVP-003": "realize frame members, sections, joins, mating counterparts and material before retention guards or dry-side carrier can enter accepted product material",
    "MVP-006": "consume the source-reservoir candidate only after release, then realize selected pump, manifold, route cross-sections and positive route supports",
    "MVP-007": "release cleanser storage and service geometry and selected pump interfaces, then realize source-to-pump and pump-to-manifold routes",
    "MVP-008": "retain the released mixed-waste centerline backbone while closing acquisition geometry, selected pump and passive-barrier packages, cartridge interface and service",
    "MVP-009": "consume released cartridge body and closure geometry, then close device-side keying, positive retention, seal stack and continuous insertion and removal motion",
    "MVP-010": "consume the compact dry-side candidate only after release, then close frame attachment, door retention and seal, selected PCB and charging hardware, and exterior reconciliation",
    "MVP-011": "use the endpoint inventory only as blocker identity, then realize electrical mating datums, endpoint-to-endpoint harness, connector retention, wet-dry bulkhead sealing and service",
    "MVP-012": "use HMI and WARM reservations only as capacity evidence, then realize final control hardware, status optics, thermal interfaces, guards, service and dry-wet relationships",
    "MVP-014": "consume exact candidate sweeps only after release and replace remaining reservations or sampled proxies with continuous collision-checked service motions",
    "MVP-016": "extend authority and mechanism CTQs to every final interface, seal, seam and service datum after the owning geometry is released",
    "MVP-017": "consume the honest ledger after release, then bind every final material and component mass source before computing dry, loaded, whole-product CG and pitch compliance",
    "MVP-018": "retain controlled fluid accounting and add selected electrical loads and duty cycles without inferring power total or runtime from missing evidence",
    "MVP-019": "release the corrected material boundary and current collision/protected successor, then rerun it against every newly accepted subsystem body and continuous service sweep",
    "MVP-020": "export the final physical hierarchy with references separated, stable IDs and transforms, source manifests and Fusion-ready handoff only after subsystem promotion",
}


def _updated_requirement(row: RequirementStatus) -> RequirementStatus | None:
    if row.requirement_id == "MVP-021":
        return None
    additions = CANDIDATE_ADDITIONS_BY_REQUIREMENT.get(row.requirement_id, ())
    candidates = tuple(sorted(set(row.candidate_prs).union(additions)))
    closure = CLOSURE_OVERRIDES.get(row.requirement_id, row.closure_required)
    updated = replace(row, candidate_prs=candidates, closure_required=closure)
    updated.__post_init__()
    return updated


def build_live_release_matrix() -> MvpCompletenessMatrix:
    baseline = build_mvp_completeness_matrix()
    requirements = tuple(updated for row in baseline.requirements if (updated := _updated_requirement(row)) is not None)
    candidates_by_pr = {item.pr_number: item for item in baseline.candidate_observations}
    for item in NEW_CANDIDATE_OBSERVATIONS:
        item.__post_init__()
        if item.pr_number in candidates_by_pr:
            raise ValueError(f"candidate PR {item.pr_number} duplicates released baseline observation")
        candidates_by_pr[item.pr_number] = item
    candidates = tuple(candidates_by_pr[number] for number in sorted(candidates_by_pr))
    matrix = MvpCompletenessMatrix(
        source_main_sha=SOURCE_MAIN_SHA,
        authority_revision=AUTHORITY_REVISION,
        authority_blob_sha=AUTHORITY_BLOB_SHA,
        authority_schema_blob_sha=AUTHORITY_SCHEMA_BLOB_SHA,
        world_frame_id=WORLD_FRAME_ID,
        candidate_snapshot_observed_at_utc=CANDIDATE_SNAPSHOT_OBSERVED_AT_UTC,
        requirements=requirements,
        candidate_observations=candidates,
        physical_gates=baseline.physical_gates,
        evidence_status=EVIDENCE_STATUS,
        physical_validation_eligible=False,
    )
    matrix.__post_init__()
    return matrix


def live_release_manifest() -> dict[str, object]:
    matrix = build_live_release_matrix()
    payload = matrix.manifest()
    payload["schema"] = SCHEMA
    payload["supersedes_schema"] = SUPERSEDES_SCHEMA
    payload["candidate_overlay_evidence_boundary"] = EVIDENCE_BOUNDARY
    payload["baseline_source_main_sha"] = SOURCE_MAIN_SHA
    payload["release_authoritative_candidate_prs"] = []
    payload["candidate_head_movement_requires_reconstruction"] = True
    payload["physical_validation_blocker_count"] = len(matrix.physical_gates)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    payload["manifest_sha256"] = sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def write_live_release_manifest(path: str | Path) -> Path:
    output = Path(path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(live_release_manifest(), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit the Cell 20 live MVP completeness and physical-blocker release matrix")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    output = write_live_release_manifest(args.output)
    payload = live_release_manifest()
    print(json.dumps({
        "output": str(output),
        "manifest_sha256": payload["manifest_sha256"],
        "digital_state_counts": payload["digital_state_counts"],
        "digital_mvp_freeze_ready": payload["digital_mvp_freeze_ready"],
        "physical_validation_complete": payload["physical_validation_complete"],
        "physical_validation_blocker_count": payload["physical_validation_blocker_count"],
        "candidate_observation_count": len(payload["candidate_observations"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
