from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
import math

import pytest

import masck_one.actuator_mount_dfm as amd
from masck_one.actuator_mount_dfm import (
    EVIDENCE_STATUS,
    LEGACY_DONOR_HEAD_SHA,
    LEGACY_DONOR_PR,
    REQUIREMENT_IDS,
    ActuatorMountDfmError,
    build_actuator_mount_dfm_audit,
    export_actuator_mount_dfm_audit,
)
from masck_one.authority import load_authority


def test_current_main_mount_maturity_is_fail_closed_and_source_bound() -> None:
    audit = build_actuator_mount_dfm_audit()
    manifest = audit.manifest()

    assert manifest["source_main_sha"] == amd.SOURCE_MAIN_SHA
    assert manifest["authority_blob_sha"] == amd.AUTHORITY_BLOB_SHA
    assert manifest["coordinate_frame_id"] == amd.WORLD_FRAME_ID
    assert tuple(item["requirement_id"] for item in manifest["requirements"]) == REQUIREMENT_IDS
    assert tuple(manifest["blocking_requirement_ids"]) == REQUIREMENT_IDS
    assert manifest["current_maturity"] == "TOPOLOGY_ONLY_NO_RELEASED_ACTUATOR_MOUNT_REACTION_OR_STOP_BREP"
    assert manifest["digital_mvp_actuator_mount_dfm_ready"] is False
    assert manifest["physical_validation_eligible"] is False
    assert manifest["evidence_status"] == EVIDENCE_STATUS
    assert len(manifest["audit_sha256"]) == 64


def test_legacy_manual_a_donor_is_never_promoted_and_records_real_collision_defects() -> None:
    audit = build_actuator_mount_dfm_audit()
    donor = audit.legacy_donor
    manifest = donor.manifest()

    assert donor.donor_pr == LEGACY_DONOR_PR == 63
    assert donor.donor_head_sha == LEGACY_DONOR_HEAD_SHA
    assert manifest["authority_status"] == "STALE_SOURCE_MATERIAL_ONLY_NOT_RELEASE_AUTHORITY"
    assert manifest["attachment_semantics_observed"] == "POSITIVE_BREP_OVERLAP_USED_AS_COLLAR_TO_SHOE_AND_SHOE_TO_FRAME_ATTACHMENT"
    assert manifest["fastener_split_clamp_keyed_orientation_and_final_stop_geometry_observed"] is False

    observed = manifest["independent_collision_observations_mm3"]
    expected = {
        "baseline_61deg_actuator_vs_shoe": 21.993454,
        "baseline_61deg_actuator_vs_frame_max": 2.664932,
        "doe_50_to_72deg_actuator_vs_shoe_max": 43.628465,
        "doe_50_to_72deg_actuator_vs_frame_max": 8.185202,
    }
    assert set(observed) == set(expected)
    for key, value in expected.items():
        assert math.isclose(float(observed[key]), value, rel_tol=0.0, abs_tol=1e-12)

    assert math.isclose(manifest["derived_candidate_margins_mm"]["collar_radial_wall"], 1.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(manifest["derived_candidate_margins_mm"]["collar_actuator_radial_clearance"], 0.2, rel_tol=0.0, abs_tol=1e-12)


def test_released_source_blob_drift_fails_closed(monkeypatch) -> None:
    first_path, _ = amd.SOURCE_GIT_BLOB_IDENTITIES[0]
    changed = ((first_path, "0" * 40),) + amd.SOURCE_GIT_BLOB_IDENTITIES[1:]
    monkeypatch.setattr(amd, "SOURCE_GIT_BLOB_IDENTITIES", changed)
    with pytest.raises(ActuatorMountDfmError, match="source moved"):
        build_actuator_mount_dfm_audit()


def test_same_revision_authority_mutation_is_rejected() -> None:
    authority = load_authority()
    data = deepcopy(authority.data)
    data["actuation"]["clean"]["axis_angle_baseline_deg"] = 67.0
    mutated = replace(authority, data=data)
    with pytest.raises(ActuatorMountDfmError, match="differs from the released machine authority"):
        build_actuator_mount_dfm_audit(mutated)


def test_readiness_and_physical_evidence_bool_coercion_fail_closed() -> None:
    audit = build_actuator_mount_dfm_audit()
    with pytest.raises(ActuatorMountDfmError, match="exact bool"):
        replace(audit, digital_mvp_actuator_mount_dfm_ready=0)
    with pytest.raises(ActuatorMountDfmError, match="exact bool"):
        replace(audit, physical_validation_eligible=0)


def test_requirement_order_duplication_and_nonfinite_manufacturing_values_are_rejected() -> None:
    audit = build_actuator_mount_dfm_audit()
    reordered = (audit.requirements[1], audit.requirements[0], *audit.requirements[2:])
    with pytest.raises(ActuatorMountDfmError, match="controlled deterministic order"):
        replace(audit, requirements=reordered)

    duplicated = (audit.requirements[0], audit.requirements[0], *audit.requirements[2:])
    with pytest.raises(ActuatorMountDfmError, match="controlled deterministic order"):
        replace(audit, requirements=duplicated)

    with pytest.raises(ActuatorMountDfmError, match="mold draft"):
        replace(audit, mold_draft_nominal_deg=float("nan"))
    with pytest.raises(ActuatorMountDfmError, match="rib ratio"):
        replace(audit, rib_thickness_ratio_range=(0.4, float("inf")))


def test_manifest_and_export_are_deterministic_and_json_safe(tmp_path) -> None:
    first = build_actuator_mount_dfm_audit()
    second = build_actuator_mount_dfm_audit()
    assert first.audit_sha256 == second.audit_sha256
    assert first.manifest() == second.manifest()

    path = export_actuator_mount_dfm_audit(tmp_path, first)
    assert path.name == "actuator_mount_dfm_audit.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == first.manifest()
    encoded = json.dumps(payload, sort_keys=True, allow_nan=False)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded
