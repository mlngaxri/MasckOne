from dataclasses import replace

import pytest

import masck_one.structural_frame_dfm as frame_dfm
from masck_one.structural_frame_dfm import (
    AUTHORITY_BLOB_SHA,
    REQUIREMENT_IDS,
    SOURCE_GIT_BLOB_IDENTITIES,
    SOURCE_MAIN_SHA,
    StructuralFrameDfmError,
    build_structural_frame_dfm_audit,
)


def test_current_main_frame_is_fail_closed_at_topology_only_maturity():
    audit = build_structural_frame_dfm_audit()
    assert audit.source_main_sha == SOURCE_MAIN_SHA
    assert audit.authority_blob_sha == AUTHORITY_BLOB_SHA
    assert audit.current_maturity == "TOPOLOGY_ONLY_3D_FRAME_AND_JOINS_UNRESOLVED"
    assert audit.digital_mvp_frame_dfm_ready is False
    assert audit.physical_validation_eligible is False
    assert tuple(item.requirement_id for item in audit.requirements) == REQUIREMENT_IDS
    assert set(audit.manifest()["blocking_requirement_ids"]) == set(REQUIREMENT_IDS)


def test_frame_dfm_binds_exact_released_source_blob_graph():
    audit = build_structural_frame_dfm_audit()
    manifest_pairs = tuple(
        (item["path"], item["git_blob_sha"])
        for item in audit.manifest()["source_git_blob_identities"]
    )
    assert manifest_pairs == SOURCE_GIT_BLOB_IDENTITIES
    assert len(SOURCE_GIT_BLOB_IDENTITIES) >= 10
    assert len({path for path, _ in SOURCE_GIT_BLOB_IDENTITIES}) == len(SOURCE_GIT_BLOB_IDENTITIES)
    assert all(len(blob_sha) == 40 for _, blob_sha in SOURCE_GIT_BLOB_IDENTITIES)


def test_source_blob_mismatch_fails_closed(monkeypatch):
    path, _ = SOURCE_GIT_BLOB_IDENTITIES[0]
    moved = ((path, "0" * 40),) + SOURCE_GIT_BLOB_IDENTITIES[1:]
    monkeypatch.setattr(frame_dfm, "SOURCE_GIT_BLOB_IDENTITIES", moved)
    with pytest.raises(StructuralFrameDfmError, match="structural DFM source moved"):
        build_structural_frame_dfm_audit()


def test_frame_dfm_carries_only_authority_manufacturing_rules():
    audit = build_structural_frame_dfm_audit()
    assert audit.mold_draft_nominal_deg == 1.0
    assert audit.rib_thickness_ratio_range == (0.40, 0.60)
    manifest = audit.manifest()
    assert manifest["manufacturing_rules"]["status"] == "AUTHORITY_RULES_ONLY_NOT_TOOLING_VALIDATION"
    assert "NOT_STRENGTH_STIFFNESS_FATIGUE" in audit.evidence_status
    assert "MOLDABILITY_TOOLING_SUPPLIER" in audit.evidence_status


def test_structural_dfm_requirements_capture_real_join_and_assembly_boundaries():
    audit = build_structural_frame_dfm_audit()
    by_id = {item.requirement_id: item for item in audit.requirements}
    assert "raw positive B-rep overlap alone is not an assembly method" in by_id["FRAME_SHELL_JOIN_ARCHITECTURE"].closure_required
    assert "tool access" in by_id["FRAME_ATTACHMENT_TOOL_ACCESS"].closure_required
    assert "hard stops" in by_id["ACTUATOR_REACTION_ATTACHMENT"].current_state
    assert "left and right" in by_id["RETENTION_FRAME_ATTACHMENT"].closure_required
    assert "collision-free frame insertion" in by_id["FRAME_NONTELEPORTING_ASSEMBLY_SEQUENCE"].closure_required


def test_stale_main_binding_is_rejected():
    audit = build_structural_frame_dfm_audit()
    with pytest.raises(StructuralFrameDfmError, match="stale for released main"):
        replace(audit, source_main_sha="0" * 40)


def test_bool_coercion_cannot_promote_dfm_or_physical_readiness():
    audit = build_structural_frame_dfm_audit()
    with pytest.raises(StructuralFrameDfmError, match="exact bool"):
        replace(audit, digital_mvp_frame_dfm_ready=0)
    with pytest.raises(StructuralFrameDfmError, match="exact bool"):
        replace(audit, physical_validation_eligible=0)


def test_nonfinite_manufacturing_values_fail_closed():
    audit = build_structural_frame_dfm_audit()
    for bad_value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(StructuralFrameDfmError, match="positive finite numeric"):
            replace(audit, mold_draft_nominal_deg=bad_value)
        with pytest.raises(StructuralFrameDfmError, match="finite increasing tuple"):
            replace(audit, rib_thickness_ratio_range=(0.40, bad_value))


def test_requirement_reordering_or_duplication_fails_closed():
    audit = build_structural_frame_dfm_audit()
    reordered = tuple(reversed(audit.requirements))
    with pytest.raises(StructuralFrameDfmError, match="controlled deterministic order"):
        replace(audit, requirements=reordered)
    duplicated = (audit.requirements[0],) + audit.requirements[:-1]
    with pytest.raises(StructuralFrameDfmError, match="controlled deterministic order"):
        replace(audit, requirements=duplicated)


def test_audit_manifest_and_digest_are_deterministic():
    first = build_structural_frame_dfm_audit()
    second = build_structural_frame_dfm_audit()
    assert first.manifest() == second.manifest()
    assert first.audit_sha256 == second.audit_sha256
    assert len(first.audit_sha256) == 64
