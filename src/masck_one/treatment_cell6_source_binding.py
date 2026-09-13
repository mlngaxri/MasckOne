from __future__ import annotations

"""Exact source identity for the treatment stack's consumed Cell 6 counterfaces.

This module supersedes only the stale source bindings embedded in the earlier
live117 reconciliation study. The earlier treatment calculations remain prior
digital evidence and are not reclassified as current physical evidence.
"""

import hashlib
import json
from pathlib import Path

SCHEMA = "MASCK_ONE_TREATMENT_CELL6_SOURCE_BINDING_V2"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
RELEASED_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
CELL6_HEAD_SHA = "2d5ace19e2f87a8bd92f4620d8e6b225ba3826be"
TREATMENT_PREMERGE_HEAD_SHA = "0073fc33d0605ea84e5322111d10a457585bdb59"
TREATMENT_CELL6_MERGE_CHECKPOINT_SHA = "d070d927d03aa995fd7d34e86dc2629a5b37a5b4"
SUPERSEDES_SOURCE_BINDING = "MASCK_ONE_TREATMENT_LIVE117_RECONCILIATION_V1_SOURCE_IDENTITY_ONLY"

CONSUMED_COUNTERFACE_BLOB_SHA1 = {
    "src/masck_one/structural_frame_actuator_mates.py": "3cedc1a0032b418d9e02592bb4996e29dc9632b7",
    "src/masck_one/structural_frame_actuator_reactions.py": "dae953807584b97747cf3f936271e019b6746d4f",
    "src/masck_one/structural_frame_carrier_interfaces.py": "81ecaa0e6b924d128d8c83bcde6a12c868f0f318",
    "src/masck_one/structural_frame_carrier_preload.py": "83338cceb2adde4855e7e67ba9e96255d32ca00b",
    "src/masck_one/structural_frame_carrier_landing.py": "a7497537b3851883dc3efa2766f395c2f4b070a0",
    "src/masck_one/structural_frame_carrier_detent.py": "693d4f6cbbc915ec2e6e6ea8ae069f0f8969cb5d",
}

HISTORICAL_STALE_BINDINGS = {
    "studies/treatment_live117_reconciliation.py:CELL6_HEAD_SHA": "3e840d52d641b429669928ab9e4c207f08086ca1",
    "src/masck_one/treatment_terminal_kinematic_seat.py:SOURCE_CELL6_HEAD_SHA": "fcccde02b31cc1c4e01136630d92e550e4e09a11",
}

PUSHED_EVIDENCE_STATUS = {
    "contact_equilibrium_zero_preload_wrench_screen": "PUSHED_PRIOR_DIGITAL_EVIDENCE",
    "exact_bezier_terminal_cam_plus_flat_land": "NO_PUSHED_EVIDENCE_FOUND_IN_LIVE_TREATMENT_OWNER_OR_DISCOVERED_TREATMENT_BRANCHES",
    "moved_opposed_z_contacts_clearing_central_bridge": "NO_PUSHED_EVIDENCE_FOUND_IN_LIVE_TREATMENT_OWNER_OR_DISCOVERED_TREATMENT_BRANCHES",
    "corrected_spring_clamp_exits": "NO_PUSHED_EVIDENCE_FOUND_IN_LIVE_TREATMENT_OWNER_OR_DISCOVERED_TREATMENT_BRANCHES",
}

PHYSICAL_VALIDATION_ELIGIBLE = False


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def verify_consumed_counterface_blobs(repo_root: str | Path) -> dict[str, str]:
    root = Path(repo_root)
    observed: dict[str, str] = {}
    for relative, expected in CONSUMED_COUNTERFACE_BLOB_SHA1.items():
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        actual = git_blob_sha1(path.read_bytes())
        if actual != expected:
            raise ValueError(f"source binding mismatch for {relative}: expected {expected}, got {actual}")
        observed[relative] = actual
    return observed


def manifest() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "coordinate_frame_id": WORLD_FRAME_ID,
        "released_main_sha": RELEASED_MAIN_SHA,
        "cell6_head_sha": CELL6_HEAD_SHA,
        "treatment_premerge_head_sha": TREATMENT_PREMERGE_HEAD_SHA,
        "treatment_cell6_merge_checkpoint_sha": TREATMENT_CELL6_MERGE_CHECKPOINT_SHA,
        "consumed_counterface_blob_sha1": dict(CONSUMED_COUNTERFACE_BLOB_SHA1),
        "supersedes_source_binding": SUPERSEDES_SOURCE_BINDING,
        "historical_stale_bindings": dict(HISTORICAL_STALE_BINDINGS),
        "pushed_evidence_status": dict(PUSHED_EVIDENCE_STATUS),
        "authority_rule": "V2_IS_CURRENT_FOR_SOURCE_IDENTITY_ONLY; PRIOR_RECONCILIATION_CALCULATIONS_REMAIN_PRIOR_DIGITAL_EVIDENCE",
        "physical_validation_eligible": PHYSICAL_VALIDATION_ELIGIBLE,
        "physical_validation": "OPEN; SOURCE_PROVENANCE_IS_NOT_FORCE_COMFORT_FATIGUE_WEAR_ACOUSTIC_OR_SUPPLIER_EVIDENCE",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["binding_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload
