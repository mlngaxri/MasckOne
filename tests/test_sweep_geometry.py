from dataclasses import replace

import pytest

from masck_one.sweep_geometry import AABB, LinearSweep, SweepGeometryError, require_fresh_sweep_source


SOURCE_SHA = "1" * 64


def _sweep() -> LinearSweep:
    return LinearSweep(
        source_id="ACTUATOR_TEST_ENVELOPE",
        start_box=AABB((0.0, 0.0, 0.0), (2.0, 2.0, 2.0)),
        translation_xyz_mm=(10.0, 0.0, 0.0),
        source_geometry_sha256=SOURCE_SHA,
        rotation_invariant=True,
    )


def test_continuous_translation_envelope_contains_interior_path_not_only_endpoints():
    sweep = _sweep()
    interior_keepout = AABB((5.0, 0.5, 0.5), (5.5, 1.5, 1.5))
    assert not sweep.start_box.intersects(interior_keepout)
    assert not sweep.end_box.intersects(interior_keepout)
    assert sweep.collides_with(interior_keepout)
    assert sweep.continuous_envelope == AABB((0.0, 0.0, 0.0), (12.0, 2.0, 2.0))


def test_touching_closed_keepout_boundary_counts_as_collision():
    sweep = _sweep()
    touching = AABB((12.0, 0.0, 0.0), (13.0, 1.0, 1.0))
    assert sweep.collides_with(touching)


def test_clearance_expands_collision_guard_without_changing_geometry():
    sweep = _sweep()
    near = AABB((12.2, 0.0, 0.0), (13.0, 1.0, 1.0))
    assert not sweep.collides_with(near)
    assert sweep.collides_with(near, clearance_mm=0.2)
    with pytest.raises(SweepGeometryError, match="non-negative"):
        sweep.collides_with(near, clearance_mm=-0.01)


def test_rotating_body_cannot_be_misrepresented_as_linear_sweep():
    with pytest.raises(SweepGeometryError, match="cannot certify changing orientation"):
        replace(_sweep(), rotation_invariant=False)


def test_valid_but_stale_source_hash_is_rejected_before_collision_use():
    sweep = _sweep()
    with pytest.raises(SweepGeometryError, match="provenance is stale"):
        require_fresh_sweep_source(sweep, expected_geometry_sha256="2" * 64)


def test_manifest_identity_changes_for_mechanical_path_change():
    first = _sweep()
    changed = replace(first, translation_xyz_mm=(10.001, 0.0, 0.0))
    assert first.manifest_sha256 != changed.manifest_sha256


def test_nonfinite_and_inverted_geometry_are_hard_failures():
    with pytest.raises(SweepGeometryError, match="finite"):
        AABB((0.0, float("nan"), 0.0), (1.0, 1.0, 1.0))
    with pytest.raises(SweepGeometryError, match="minimum cannot exceed"):
        AABB((2.0, 0.0, 0.0), (1.0, 1.0, 1.0))
