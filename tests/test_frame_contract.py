from __future__ import annotations

import copy

import pytest

from masck_one.authority import Authority, load_authority
from masck_one.frame_contract import (
    CANONICAL_FRAME_ID,
    CANONICAL_LENGTH_UNIT,
    CrossSystemFrameContract,
    FrameBinding,
    FrameContractError,
)
from masck_one.spatial import Matrix3, RigidTransform, Vector3


def _mutated_authority(*, length_unit: str | None = None, x_positive: str | None = None) -> Authority:
    source = load_authority()
    data = copy.deepcopy(source.data)
    if length_unit is not None:
        data["project"]["units"]["length"] = length_unit
    if x_positive is not None:
        data["coordinate_system"]["x_positive"] = x_positive
    return Authority(data=data, source=source.source, validation_report=source.validation_report)


def test_authority_world_contract_is_mm_right_handed_and_explicit() -> None:
    contract = CrossSystemFrameContract.from_authority(load_authority())

    assert contract.canonical_frame_id == "MASCK_ONE_AUTHORITY_WORLD_MM"
    assert contract.length_unit == "mm"
    assert contract.angle_unit == "deg"
    assert contract.handedness == "right"
    assert contract.axis_semantics == ("wearer_right", "superior", "anterior")
    assert contract.origin_xyz_mm == (0.0, 0.0, 0.0)
    assert contract.physical_validation_eligible is False


def test_released_spatial_global_alias_is_reconciled_only_by_explicit_identity() -> None:
    contract = CrossSystemFrameContract.from_authority(load_authority())
    binding = contract.legacy_spatial_alias_binding()

    assert contract.spatial_datum_frame_id == "MASCK_ONE_GLOBAL"
    assert binding.source_frame_id == "MASCK_ONE_GLOBAL"
    assert binding.target_frame_id == CANONICAL_FRAME_ID
    assert binding.binding_kind == "LEGACY_INTERNAL_ALIAS_EXPLICIT_IDENTITY"
    assert binding.transform == RigidTransform.identity()
    assert binding.source_length_unit == CANONICAL_LENGTH_UNIT
    assert binding.target_length_unit == CANONICAL_LENGTH_UNIT


def test_authority_world_binding_rejects_hidden_repositioning() -> None:
    with pytest.raises(FrameContractError, match="hidden repositioning"):
        FrameBinding(
            source_frame_id=CANONICAL_FRAME_ID,
            target_frame_id=CANONICAL_FRAME_ID,
            source_length_unit="mm",
            target_length_unit="mm",
            transform=RigidTransform.from_translation(Vector3(1.0, 0.0, 0.0)),
            binding_kind="AUTHORITY_WORLD_IDENTITY",
        )


def test_legacy_global_alias_rejects_hidden_repositioning() -> None:
    with pytest.raises(FrameContractError, match="legacy global alias"):
        FrameBinding(
            source_frame_id="MASCK_ONE_GLOBAL",
            target_frame_id=CANONICAL_FRAME_ID,
            source_length_unit="mm",
            target_length_unit="mm",
            transform=RigidTransform.from_translation(Vector3(0.0, 2.0, 0.0)),
            binding_kind="LEGACY_INTERNAL_ALIAS_EXPLICIT_IDENTITY",
        )


def test_cross_system_rigid_binding_rejects_hidden_unit_conversion() -> None:
    with pytest.raises(FrameContractError, match="unit conversion"):
        FrameBinding(
            source_frame_id="MASCK_ONE_LOCAL_TEST",
            target_frame_id=CANONICAL_FRAME_ID,
            source_length_unit="cm",
            target_length_unit="mm",
            transform=RigidTransform.identity(),
            binding_kind="EXPLICIT_LOCAL_TO_AUTHORITY_WORLD",
        )


def test_unknown_frame_names_fail_closed() -> None:
    with pytest.raises(FrameContractError, match="unknown source frame"):
        FrameBinding(
            source_frame_id="DEVICE_FRAME",
            target_frame_id=CANONICAL_FRAME_ID,
            source_length_unit="mm",
            target_length_unit="mm",
            transform=RigidTransform.identity(),
            binding_kind="EXPLICIT_LOCAL_TO_AUTHORITY_WORLD",
        )


def test_explicit_local_frame_can_use_a_proper_rigid_transform() -> None:
    contract = CrossSystemFrameContract.from_authority(load_authority())
    transform = RigidTransform(
        Matrix3.rotation_y(61.0),
        Vector3(50.0, -38.0, 2.0),
    )
    binding = contract.local_to_world_binding(
        local_frame_id="MASCK_ONE_LOCAL_ACTUATOR_TEST",
        transform=transform,
    )

    assert binding.transform.rotation.determinant() == pytest.approx(1.0)
    assert binding.binding_kind == "EXPLICIT_LOCAL_TO_AUTHORITY_WORLD"
    assert binding.target_frame_id == CANONICAL_FRAME_ID


def test_authority_length_unit_drift_fails_cross_system_contract() -> None:
    with pytest.raises(FrameContractError, match="length unit drifted"):
        CrossSystemFrameContract.from_authority(_mutated_authority(length_unit="cm"))


def test_authority_axis_semantic_drift_fails_cross_system_contract() -> None:
    with pytest.raises(FrameContractError):
        CrossSystemFrameContract.from_authority(_mutated_authority(x_positive="wearer_left"))


def test_manifest_is_deterministic_and_preserves_evidence_firewall() -> None:
    contract = CrossSystemFrameContract.from_authority(load_authority())
    first = contract.manifest()
    second = CrossSystemFrameContract.from_authority(load_authority()).manifest()

    assert first == second
    assert first["contract_sha256"] == second["contract_sha256"]
    assert first["physical_validation_eligible"] is False
    assert first["cross_system_rule"].startswith("EXTERNAL_GEOMETRY_MUST_DECLARE_")
    assert first["unit_ingestion_rule"] == "CONVERT_TO_MM_BEFORE_RIGID_CROSS_SYSTEM_BINDING"
