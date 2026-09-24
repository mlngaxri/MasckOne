from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v38 as v38


def test_v38_binds_each_collision_layer_to_its_longitudinal_authority():
    model = v38.build_retention_quick_release_tactile_v38()
    assert tuple(name for name, _, _ in model.layer_cardinalities) == (
        "stations", "midpoints", "quarters", "eighths", "odd_sixteenths"
    )
    assert sum(poses for _, _, poses in model.layer_cardinalities) == model.prior.complete_lattice_collision_pose_count
    assert model.manifest()["per_layer_collision_cardinality_binding"]["criterion"] == (
        "EACH_LONGITUDINAL_AUTHORITY_CONTRIBUTES_EXACTLY_ITS_EXPECTED_COLLISION_POSES"
    )


def test_v38_rejects_pose_redistribution_that_preserves_aggregate(monkeypatch):
    model = v38.build_retention_quick_release_tactile_v38()
    layers = list(v38.v37._collision_layers(model.prior.prior))
    layers[0] = replace(layers[0], pose_count=layers[0].pose_count - 1)
    layers[1] = replace(layers[1], pose_count=layers[1].pose_count + 1)
    monkeypatch.setattr(v38.v37, "_collision_layers", lambda prior: tuple(layers))
    with pytest.raises(v38.RetentionQuickReleaseTactileV38Error, match="stations collision pose cardinality is incomplete"):
        v38._layer_cardinality_evidence(model.prior)


def test_v38_rejects_layer_transverse_drift(monkeypatch):
    model = v38.build_retention_quick_release_tactile_v38()
    layers = list(v38.v37._collision_layers(model.prior.prior))
    layers[2] = replace(layers[2], transverse_sample_count=layers[2].transverse_sample_count + 1)
    monkeypatch.setattr(v38.v37, "_collision_layers", lambda prior: tuple(layers))
    with pytest.raises(v38.RetentionQuickReleaseTactileV38Error, match="quarters transverse authority drifted"):
        v38._layer_cardinality_evidence(model.prior)


def test_v38_rejects_stale_cardinality_digest():
    model = v38.build_retention_quick_release_tactile_v38()
    with pytest.raises(v38.RetentionQuickReleaseTactileV38Error, match="cardinality digest is stale"):
        replace(model, layer_cardinality_sha256="0" * 64).validate()
