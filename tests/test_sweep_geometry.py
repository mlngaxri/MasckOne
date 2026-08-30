from dataclasses import replace

import pytest

from masck_one.sweep_geometry import AABB, LinearSweep, SweepGeometryError, require_fresh_sweep_source


SOURCE_SHA = "1" * 64
WORLD_FRAME = "MASCK_ONE_WORLD"


def _sweep() -> LinearSweep:
    return LinearSweep(
        source_id="ACTUATOR_TEST_ENVELOPE",
        start_box=AABB((0.0, 0.0, 0.0), (2.0, 2.0, 2.0), frame_id=WORLD_FRAME),
        translation_xyz_mm=(10.0, 0.0, 0.0),
        source_geometry_sha256=SOURCE_SHA,
        rotation_invariant=True,
    )


def test_continuous_translation_envelope_contains_interior_path_not_only_endpoints():
    sweep = _sweep()
    interior_keepout = AABB((5.0, 0.5, 0.5), (5.5, 1.5, 1.5), frame_id=WORLD_FRAME)
    assert not sweep.start_box.intersects(interior_keepout)
    assert not sweep.end_box.intersects(interior_keepout)
    assert sweep.collides_with(interior_keepout, expected_geometry_sha256=SOURCE_SHA)
    assert sweep.continuous_envelope == AABB((0.0, 0.0, 0.0), (12.0, 2.0, 2.0), frame_id=WORLD_FRAME)


def test_touching_closed_keepout_boundary_counts_as_collision():
    sweep = _sweep()
    touching = AABB((12.0, 0.0, 0.0), (13.0, 1.0, 1.0), frame_id=WORLD_FRAME)
    assert sweep.collides_with(touching, expected_geometry_sha256=SOURCE_SHA)


def test_clearance_expands_collision_guard_without_changing_geometry():
    sweep = _sweep()
    near = AABB((12.2, 0.0, 0.0), (13.0, 1.0, 1.0), frame_id=WORLD_FRAME)
    assert not sweep.collides_with(near, expected_geometry_sha256=SOURCE_SHA)
    assert sweep.collides_with(near, expected_geometry_sha256=SOURCE_SHA, clearance_mm=0.2)
    with pytest.raises(SweepGeometryError, match="non-negative"):
        sweep.collides_with(near, expected_geometry_sha256=SOURCE_SHA, clearance_mm=-0.01)


def test_coordinate_frame_mismatch_is_a_hard_failure_not_a_collision_boolean():
    sweep = _sweep()
    local_keepout = AABB((5.0, 0.5, 0.5), (5.5, 1.5, 1.5), frame_id="ACTUATOR_LOCAL_FOREHEAD")
    with pytest.raises(SweepGeometryError, match="coordinate-frame mismatch"):
        sweep.collides_with(local_keepout, expected_geometry_sha256=SOURCE_SHA)
    with pytest.raises(SweepGeometryError, match="coordinate-frame mismatch"):
        sweep.start_box.union(local_keepout)


def test_collision_api_cannot_bypass_source_freshness():
    sweep = _sweep()
    keepout = AABB((5.0, 0.5, 0.5), (5.5, 1.5, 1.5), frame_id=WORLD_FRAME)
    with pytest.raises(TypeError):
        sweep.collides_with(keepout)  # type: ignore[call-arg]
    with pytest.raises(SweepGeometryError, match="provenance is stale"):
        sweep.collides_with(keepout, expected_geometry_sha256="2" * 64)


def test_frame_identity_is_preserved_through_translation_and_manifest():
    sweep = _sweep()
    assert sweep.end_box.frame_id == WORLD_FRAME
    assert sweep.continuous_envelope.frame_id == WORLD_FRAME
    manifest = sweep.manifest()
    assert manifest["coordinate_frame_id"] == WORLD_FRAME
    assert manifest["start_box"]["frame_id"] == WORLD_FRAME


def test_aabb_construction_requires_explicit_coordinate_frame():
    with pytest.raises(TypeError):
        AABB((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))  # type: ignore[call-arg]


def test_rotating_body_cannot_be_misrepresented_as_linear_sweep():
    with pytest.raises(SweepGeometryError, match="cannot certify changing orientation"):
        replace(_sweep(), rotation_invariant=False)


def test_valid_but_stale_source_hash_is_rejected_before_collision_use():
    sweep = _sweep()
    with pytest.raises(SweepGeometryError, match="provenance is stale"):
        require_fresh_sweep_source(sweep, expected_geometry_sha256="2" * 64)


def test_sha256_identity_requires_lowercase_canonical_form():
    alpha_digest = "ab" * 32
    canonical = LinearSweep(
        source_id="CANONICAL_DIGEST",
        start_box=AABB((0.0, 0.0, 0.0), (1.0, 1.0, 1.0), frame_id=WORLD_FRAME),
        translation_xyz_mm=(1.0, 0.0, 0.0),
        source_geometry_sha256=alpha_digest,
        rotation_invariant=True,
    )
    assert canonical.source_geometry_sha256 == alpha_digest
    with pytest.raises(SweepGeometryError, match="lowercase canonical SHA-256"):
        replace(canonical, source_geometry_sha256=alpha_digest.upper())
    with pytest.raises(SweepGeometryError, match="lowercase canonical SHA-256"):
        require_fresh_sweep_source(canonical, expected_geometry_sha256=alpha_digest.upper())


def test_manifest_identity_changes_for_mechanical_path_or_frame_change():
    first = _sweep()
    changed_path = replace(first, translation_xyz_mm=(10.001, 0.0, 0.0))
    changed_frame = replace(
        first,
        start_box=AABB(first.start_box.minimum_xyz_mm, first.start_box.maximum_xyz_mm, frame_id="OTHER_WORLD"),
    )
    assert first.manifest_sha256 != changed_path.manifest_sha256
    assert first.manifest_sha256 != changed_frame.manifest_sha256


def test_nonfinite_inverted_and_blank_frame_geometry_are_hard_failures():
    with pytest.raises(SweepGeometryError, match="finite"):
        AABB((0.0, float("nan"), 0.0), (1.0, 1.0, 1.0), frame_id=WORLD_FRAME)
    with pytest.raises(SweepGeometryError, match="minimum cannot exceed"):
        AABB((2.0, 0.0, 0.0), (1.0, 1.0, 1.0), frame_id=WORLD_FRAME)
    with pytest.raises(SweepGeometryError, match="explicit nonblank string"):
        AABB((0.0, 0.0, 0.0), (1.0, 1.0, 1.0), frame_id="  ")


def test_boolean_and_coercible_aliases_cannot_enter_mechanical_geometry():
    with pytest.raises(SweepGeometryError, match="not a boolean or coercible alias"):
        AABB((True, 0.0, 0.0), (1.0, 1.0, 1.0), frame_id=WORLD_FRAME)  # type: ignore[arg-type]
    with pytest.raises(SweepGeometryError, match="not a boolean or coercible alias"):
        replace(_sweep(), translation_xyz_mm=("10.0", 0.0, 0.0))  # type: ignore[arg-type]
    keepout = AABB((20.0, 0.0, 0.0), (21.0, 1.0, 1.0), frame_id=WORLD_FRAME)
    with pytest.raises(SweepGeometryError, match="not a boolean or coercible alias"):
        _sweep().collides_with(keepout, expected_geometry_sha256=SOURCE_SHA, clearance_mm=True)  # type: ignore[arg-type]


def test_rotation_invariant_requires_literal_boolean_and_source_identity_is_canonicalized():
    with pytest.raises(SweepGeometryError, match="explicit boolean"):
        replace(_sweep(), rotation_invariant=1)  # type: ignore[arg-type]
    normalized = replace(_sweep(), source_id="  ACTUATOR_TEST_ENVELOPE  ")
    assert normalized.source_id == "ACTUATOR_TEST_ENVELOPE"
    assert normalized.manifest()["source_id"] == "ACTUATOR_TEST_ENVELOPE"
