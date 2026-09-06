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
CANDIDATE_SNAPSHOT_OBSERVED_AT_UTC = "2026-09-06T01:10:52Z"
EVIDENCE_BOUNDARY = (
    "RELEASED_MAIN_MATURITY_PLUS_NON_AUTHORITATIVE_CANDIDATE_NAVIGATION_ONLY_"
    "NOT_PHYSICAL_VALIDATION_OR_PROMOTION_REVIEW_EVIDENCE"
)

HEAD_REBINDS: dict[int, str] = {
    92: "abb806a8e15a1557c8b5a4c754af1bfeea8b6d70",
}

NEW_CANDIDATE_OBSERVATIONS: tuple[CandidateObservation, ...] = (
    CandidateObservation(103, "76835d6239b53b2e5900678d2912eb1b7c8c2747", "independent current release-material truth audit"),
    CandidateObservation(104, "1b4411fd2759bf92af2eccef4b1325b0897b7f72", "current wet and electrical released-source graph receipt"),
    CandidateObservation(105, "8d5762f35c0b64b736648ef3541377b43a168952", "current cleanser released-source graph receipt without route realization"),
    CandidateObservation(106, "87d7521994ff2fafa2df61c570ec677f6142d379", "current DFM part-family to released-producer reconciliation"),
    CandidateObservation(107, "22d2e5baccbcfa56aa4a70e4e4dd59693e15affd", "current-main fresh-water reservoir body and lid source-geometry candidate"),
    CandidateObservation(108, "0bf6c73028284ba9a5715ef5235bb2be1c298403", "honest mass CG pitch power and fluid ledger candidate with unresolved totals"),
    CandidateObservation(109, "fb586cc1ea1cde92526417593f9e5aa990d2ae4f", "retention hazard-guard B-reps and exact factory-installation sweeps candidate"),
    CandidateObservation(110, "7b32c674860cab87cbdd1f7e3303a4ce53515e95", "physical-HMI and WARM decision-state reservations with no final hardware selection"),
    CandidateObservation(111, "6899b61db8cd549c44a82b12e78fe4028a2e7048", "compact dry-side carrier door and battery-service sweep candidate"),
    CandidateObservation(112, "abbfa427660a3752cce7d18b86faa44654884936", "current-main whole-product collision and protected-region matrix successor"),
    CandidateObservation(113, "1e17bb50c00e94439fab09a477483950f8cd163f", "current harness endpoint inventory with zero route-ready electrical mating datums"),
    CandidateObservation(114, "630cc19497661ae834032eb8ea06e28dfd6100b7", "current part assembly and service-motion inventory with no released objective-domain motions"),
    CandidateObservation(115, "b61d71433f81e3f3e03307a350334a76e9dbf361", "source-bound waste-cartridge body closure and protected-compliant free-cavity geometry candidate with capacity deficit"),
    CandidateObservation(116, "1f769016efb6034c1708a275465fbac6910a75da", "current datum and CTQ inventory with geometry-dependent stacks unresolved"),
    CandidateObservation(117, "6e3e1385f350735731ac08ff107a3c1d0f76189e", "first current-main structural reaction-loop B-rep candidate with joins and counterparts open"),
    CandidateObservation(118, "37e03df4b6abbd222422c8bfd4e70b03a4e5ae07", "local actuator carrier split capture and positive-stop B-rep candidate with world mounting blocked"),
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
    "MVP-003": (109, 111, 117),
    "MVP-004": (116, 118),
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
    "MVP-003": "consume the structural reaction-loop candidate only after release, then close shell-frame joins, retention and actuator counterparts, tool access and material definition",
    "MVP-004": "consume the local carrier template only after release, then resolve protected-conflict-free world placement, frame reaction attachment, coupling, final stops and service access",
    "MVP-006": "consume the source-reservoir candidate only after release, then realize selected pump, manifold, route cross-sections and positive route supports",
    "MVP-007": "release cleanser storage and service geometry and selected pump interfaces, then realize source-to-pump and pump-to-manifold routes",
    "MVP-008": "retain the released mixed-waste centerline backbone while closing acquisition geometry, selected pump and passive-barrier packages, cartridge interface and service",
    "MVP-009": "consume released cartridge body and closure geometry, then close capacity deficit, device-side keying, positive retention, seal stack and continuous insertion and removal motion",
    "MVP-010": "consume the compact dry-side candidate only after release, then close frame attachment, single-owner exterior closure seal and retention, selected PCB and charging hardware, and exterior reconciliation",
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
    for pr_number, head_sha in HEAD_REBINDS.items():
        if pr_number not in candidates_by_pr:
            raise ValueError(f"candidate PR {pr_number} is missing from released baseline observations")
        candidates_by_pr[pr_number] = replace(candidates_by_pr[pr_number], observed_head_sha=head_sha)
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
