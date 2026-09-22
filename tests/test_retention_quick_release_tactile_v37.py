from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v37 as v37


def test_v37_binds_complete_lattice_to_collision_pose_evidence():
    model = v37.build_retention_quick_release_tactile_v37()
    assert model.complete_lattice_collision_pose_count == (
        model.transverse_sample_count * model.prior.complete_lattice_position_count
    )
    assert model.manifest()["complete_lattice_collision_binding"]["criterion"] == (
        "EVERY_COMPLETE_SIXTEENTH_LATTICE_POSITION_IS_BOUND_TO_VALIDATED_COLLISION_SCREEN_POSE_EVIDENCE"
    )


def test_v37_rejects_stale_collision_pose_count():
    model = v37.build_retention_quick_release_tactile_v37()
    with pytest.raises(v37.RetentionQuickReleaseTactileV37Error, match="collision pose count is stale"):
        replace(model, complete_lattice_collision_pose_count=model.complete_lattice_collision_pose_count - 1).validate()


def test_v37_rejects_stale_collision_coverage_digest():
    model = v37.build_retention_quick_release_tactile_v37()
    with pytest.raises(v37.RetentionQuickReleaseTactileV37Error, match="collision coverage digest is stale"):
        replace(model, collision_coverage_sha256="0" * 64).validate()


def test_v37_rejects_layer_pose_loss(monkeypatch):
    model = v37.build_retention_quick_release_tactile_v37()
    layers = list(v37._collision_layers(model.prior))
    layers[-1] = replace(layers[-1], pose_count=layers[-1].pose_count - 1)
    monkeypatch.setattr(v37, "_collision_layers", lambda prior: tuple(layers))
    with pytest.raises(v37.RetentionQuickReleaseTactileV37Error, match="does not cover every complete-lattice pose"):
        v37._collision_coverage_evidence(model.prior)


def test_v37_rejects_transverse_authority_drift(monkeypatch):
    model = v37.build_retention_quick_release_tactile_v37()
    layers = list(v37._collision_layers(model.prior))
    layers[-1] = replace(layers[-1], transverse_sample_count=layers[-1].transverse_sample_count + 1)
    monkeypatch.setattr(v37, "_collision_layers", lambda prior: tuple(layers))
    with pytest.raises(v37.RetentionQuickReleaseTactileV37Error, match="disagree on transverse sample authority"):
        v37._collision_coverage_evidence(model.prior)
