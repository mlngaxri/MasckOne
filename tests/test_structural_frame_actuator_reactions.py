from __future__ import annotations

from dataclasses import replace
import json

import cadquery as cq
import pytest

from masck_one.structural_frame_actuator_reactions import (
    REACTION_IDS,
    StructuralFrameActuatorReactionError,
    build_structural_frame_actuator_reactions,
)
from masck_one.structural_frame_actuator_reactions_export import (
    export_structural_frame_actuator_reactions,
)
from masck_one.structural_frame_shell_joints import build_structural_frame_shell_joints


def test_four_frame_side_reaction_counterparts_are_positive_source_bound_breps() -> None:
    source = build_structural_frame_shell_joints()
    architecture = build_structural_frame_actuator_reactions(shell_joints=source)

    assert tuple(reaction.reaction_id for reaction in architecture.reactions) == REACTION_IDS
    assert architecture.source_shell_joint_architecture_sha256 == source.architecture_sha256
    assert architecture.frame_with_reaction_counterparts.val().isValid()
    assert len(architecture.frame_with_reaction_counterparts.val().Solids()) == 1
    assert architecture.physical_validation_eligible is False

    for reaction in architecture.reactions:
        assert reaction.boss_capture_volume_mm3 > 0.0
        assert reaction.socket_removed_volume_mm3 > 0.0
        assert reaction.protected_intersection_volume_mm3 == 0.0


def test_reaction_architecture_is_deterministic_and_keeps_world_mount_unpromoted() -> None:
    first = build_structural_frame_actuator_reactions()
    second = build_structural_frame_actuator_reactions()

    assert first.architecture_sha256 == second.architecture_sha256
    assert first.manifest() == second.manifest()
    assert first.manifest()["reaction_count"] == 4
    assert "ACTUATOR_PACKAGE_PLACEMENT_NOT_PROMOTED" in first.manifest()["world_mount_status"]
    json.dumps(first.manifest(), sort_keys=True, allow_nan=False)


def test_reaction_export_round_trip_is_valid_and_source_bound(tmp_path) -> None:
    result = export_structural_frame_actuator_reactions(tmp_path)
    step_path = tmp_path / result["step_file"]
    manifest_path = tmp_path / result["manifest_file"]

    assert step_path.is_file() and step_path.stat().st_size > 0
    assert manifest_path.is_file() and manifest_path.stat().st_size > 0

    imported = cq.importers.importStep(str(step_path))
    assert imported.val().isValid()
    assert len(imported.val().Solids()) == 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["architecture_sha256"] == result["architecture_sha256"]
    assert manifest["reaction_count"] == 4
    assert tuple(item["reaction_id"] for item in manifest["reactions"]) == REACTION_IDS


def test_regression_rejects_reaction_counterpart_outside_source_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    import masck_one.structural_frame_actuator_reactions as reactions

    monkeypatch.setattr(
        reactions,
        "_reaction_centers",
        lambda: ((-500.0, 500.0), (500.0, 500.0), (-500.0, -500.0), (500.0, -500.0)),
    )
    with pytest.raises(StructuralFrameActuatorReactionError, match="positively intersect"):
        reactions.build_structural_frame_actuator_reactions()


def test_regression_rejects_source_identity_drift() -> None:
    architecture = build_structural_frame_actuator_reactions()
    with pytest.raises(StructuralFrameActuatorReactionError, match="canonical SHA-256"):
        replace(architecture, source_shell_joint_architecture_sha256="0" * 63)
