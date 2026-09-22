from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v39 as v39


def test_v39_binds_named_layers_to_exact_ordered_schedules():
    model = v39.build_retention_quick_release_tactile_v39()
    assert tuple(record[0] for record in model.layer_identities) == (
        "stations", "midpoints", "quarters", "eighths", "odd_sixteenths"
    )
    assert model.manifest()["collision_layer_schedule_identity_binding"]["criterion"] == (
        "EACH_COLLISION_LAYER_IS_BOUND_TO_ITS_EXACT_ORDERED_LONGITUDINAL_SCHEDULE"
    )


def test_v39_rejects_schedule_reassignment_with_same_cardinality(monkeypatch):
    model = v39.build_retention_quick_release_tactile_v39()
    original = v39.v32._midpoint_positions
    positions = tuple(original())
    monkeypatch.setattr(v39.v32, "_midpoint_positions", lambda: tuple(reversed(positions)))
    records, digest = v39._layer_identity_evidence(model.prior)
    assert records != model.layer_identities
    assert digest != model.layer_identity_sha256
    with pytest.raises(v39.RetentionQuickReleaseTactileV39Error, match="identity evidence is stale"):
        model.validate()


def test_v39_rejects_layer_owner_cardinality_drift():
    model = v39.build_retention_quick_release_tactile_v39()
    bad = list(model.prior.layer_cardinalities)
    bad[1] = ("quarters", bad[1][1], bad[1][2])
    with pytest.raises(v39.RetentionQuickReleaseTactileV39Error, match="midpoints owner/cardinality binding drifted"):
        v39._layer_identity_evidence(replace(model.prior, layer_cardinalities=tuple(bad)))


def test_v39_rejects_stale_identity_digest():
    model = v39.build_retention_quick_release_tactile_v39()
    with pytest.raises(v39.RetentionQuickReleaseTactileV39Error, match="identity digest is stale"):
        replace(model, layer_identity_sha256="0" * 64).validate()
