from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v40 as v40


def test_v40_binds_collision_authority_to_four_unique_clearance_corners():
    model = v40.build_retention_quick_release_tactile_v40()
    assert len(model.clearance_corner_identities) == 4
    assert len({name for name, _, _ in model.clearance_corner_identities}) == 4
    assert len({(radial, side) for _, radial, side in model.clearance_corner_identities}) == 4
    assert model.manifest()["clearance_corner_collision_authority_binding"]["criterion"] == (
        "ALL_COLLISION_LAYERS_ARE_BOUND_TO_THE_EXACT_FOUR_UNIQUE_CLEARANCE_AUTHORITY_CORNERS"
    )


def test_v40_rejects_stale_corner_identity_evidence():
    model = v40.build_retention_quick_release_tactile_v40()
    bad = list(model.clearance_corner_identities)
    name, radial, side = bad[0]
    bad[0] = (name, radial + 0.001, side)
    with pytest.raises(v40.RetentionQuickReleaseTactileV40Error, match="identity evidence is stale"):
        replace(model, clearance_corner_identities=tuple(bad)).validate()


def test_v40_rejects_stale_corner_binding_digest():
    model = v40.build_retention_quick_release_tactile_v40()
    with pytest.raises(v40.RetentionQuickReleaseTactileV40Error, match="binding digest is stale"):
        replace(model, clearance_corner_binding_sha256="0" * 64).validate()


def test_v40_rejects_duplicate_clearance_corner_pairs(monkeypatch):
    model = v40.build_retention_quick_release_tactile_v40()
    original = v40.v30._clearance_corners
    corners = tuple(original(v40.v1.build_retention_quick_release_tactile()))
    duplicate = (corners[1][0], corners[0][1], corners[0][2])
    monkeypatch.setattr(v40.v30, "_clearance_corners", lambda mechanism: (corners[0], duplicate, corners[2], corners[3]))
    with pytest.raises(v40.RetentionQuickReleaseTactileV40Error, match="coordinate pairs must be unique"):
        v40._clearance_corner_identity(model.prior)
