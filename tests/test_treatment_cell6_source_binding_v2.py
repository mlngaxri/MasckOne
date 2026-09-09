from __future__ import annotations

from pathlib import Path

from masck_one.treatment_cell6_source_binding import (
    CELL6_HEAD_SHA,
    CONSUMED_COUNTERFACE_BLOB_SHA1,
    PHYSICAL_VALIDATION_ELIGIBLE,
    RELEASED_MAIN_SHA,
    TREATMENT_CELL6_MERGE_CHECKPOINT_SHA,
    TREATMENT_PREMERGE_HEAD_SHA,
    manifest,
    verify_consumed_counterface_blobs,
)


def test_treatment_cell6_v2_binding_is_exact_and_current() -> None:
    assert RELEASED_MAIN_SHA == "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
    assert CELL6_HEAD_SHA == "2d5ace19e2f87a8bd92f4620d8e6b225ba3826be"
    assert TREATMENT_PREMERGE_HEAD_SHA == "0073fc33d0605ea84e5322111d10a457585bdb59"
    assert TREATMENT_CELL6_MERGE_CHECKPOINT_SHA == "d070d927d03aa995fd7d34e86dc2629a5b37a5b4"
    assert len(CONSUMED_COUNTERFACE_BLOB_SHA1) == 6
    assert all(len(value) == 40 for value in CONSUMED_COUNTERFACE_BLOB_SHA1.values())

    repo_root = Path(__file__).resolve().parents[1]
    assert verify_consumed_counterface_blobs(repo_root) == CONSUMED_COUNTERFACE_BLOB_SHA1


def test_treatment_cell6_v2_binding_preserves_evidence_firewall_and_supersedes_only_identity() -> None:
    payload = manifest()
    assert payload["physical_validation_eligible"] is False
    assert PHYSICAL_VALIDATION_ELIGIBLE is False
    assert payload["supersedes_source_binding"].endswith("SOURCE_IDENTITY_ONLY")
    assert "PRIOR_RECONCILIATION_CALCULATIONS_REMAIN_PRIOR_DIGITAL_EVIDENCE" in payload["authority_rule"]
    assert len(payload["binding_sha256"]) == 64


def test_reported_astra_fixes_are_not_promoted_without_pushed_geometry() -> None:
    status = manifest()["pushed_evidence_status"]
    assert status["contact_equilibrium_zero_preload_wrench_screen"] == "PUSHED_PRIOR_DIGITAL_EVIDENCE"
    assert status["exact_bezier_terminal_cam_plus_flat_land"].startswith("NO_PUSHED_EVIDENCE_FOUND")
    assert status["moved_opposed_z_contacts_clearing_central_bridge"].startswith("NO_PUSHED_EVIDENCE_FOUND")
    assert status["corrected_spring_clamp_exits"].startswith("NO_PUSHED_EVIDENCE_FOUND")
