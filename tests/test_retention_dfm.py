from dataclasses import replace

import pytest

from masck_one.retention_dfm import (
    DIGITAL_ONLY,
    OPEN,
    SOURCE_MAIN_SHA,
    RetentionDfmError,
    build_retention_dfm_gate,
)
from masck_one.whole_product_dfm import (
    MATURITY_RELEASED_TOPOLOGY,
    build_whole_product_dfm_architecture,
)


def test_released_main_retention_gate_stays_open_on_real_digital_closure_items() -> None:
    gate = build_retention_dfm_gate()
    manifest = gate.manifest()
    assert gate.source_main_sha == SOURCE_MAIN_SHA
    assert gate.digital_retention_freeze_ready is False
    assert [item.requirement_id for item in gate.requirements] == [
        "RETENTION_OCCIPITAL_CONTACT_CARRIER",
        "RETENTION_WEARER_SIDE_EDGE_TREATMENT",
        "RETENTION_FRAME_SIDE_POSITIVE_CAPTURE",
        "RETENTION_CROWN_SUPPORT_ARCHITECTURE",
        "RETENTION_FIT_ACCOMMODATION_ARCHITECTURE",
        "RETENTION_NON_TELEPORTING_ASSEMBLY_ACCESS",
        "RETENTION_POST_RELEASE_WHOLE_HEAD_REMOVAL",
    ]
    assert all(item.status == OPEN for item in gate.requirements)
    assert "NO_FROZEN_ADJUSTMENT_MECHANISM_OR_ANTHROPOMETRIC_TRAVEL" in manifest["adjustment_authority_boundary"]
    assert gate.physical_validation_eligible is False
    assert gate.production_validation_eligible is False
    assert gate.evidence_status == DIGITAL_ONLY


def test_retention_gate_fails_closed_when_source_identity_or_requirement_contract_drifts() -> None:
    gate = build_retention_dfm_gate()
    with pytest.raises(RetentionDfmError, match="stale for released main"):
        replace(gate, source_main_sha="0" * 40)
    with pytest.raises(RetentionDfmError, match="canonical 64-hex"):
        replace(gate, source_dfm_architecture_sha256="not-a-digest")
    with pytest.raises(RetentionDfmError, match="set or order drifted"):
        replace(gate, requirements=tuple(reversed(gate.requirements)))
    with pytest.raises(RetentionDfmError, match="physical validation"):
        replace(gate, physical_validation_eligible=True)
    with pytest.raises(RetentionDfmError, match="production validation"):
        replace(gate, production_validation_eligible=True)


def test_retention_gate_requires_reaudit_if_released_part_maturity_moves() -> None:
    architecture = build_whole_product_dfm_architecture()
    target_id = "MASCK_ONE-DFM-RETENTION-HALO-LEFT"
    changed = tuple(
        replace(part, maturity=MATURITY_RELEASED_TOPOLOGY) if part.part_id == target_id else part
        for part in architecture.parts
    )
    changed_architecture = replace(architecture, parts=changed)
    with pytest.raises(RetentionDfmError, match="retention part maturity moved"):
        build_retention_dfm_gate(changed_architecture)


def test_retention_requirement_cannot_be_metadata_closed_without_rebind() -> None:
    gate = build_retention_dfm_gate()
    with pytest.raises(RetentionDfmError, match="cannot be marked closed"):
        replace(gate.requirements[0], status="CLOSED")
