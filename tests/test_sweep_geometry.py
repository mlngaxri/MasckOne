from dataclasses import replace
import pytest
from masck_one.sweep_geometry import AABB, LinearSweep, SweepGeometryError, require_fresh_sweep_source
SOURCE_SHA = "1" * 64
WORLD_FRAME = "MASCK_ONE_WORLD"
def _sweep(): return LinearSweep("ACTUATOR_TEST_ENVELOPE", AABB((0.,0.,0.),(2.,2.,2.),WORLD_FRAME),(10.,0.,0.),SOURCE_SHA,True)
def test_continuous_translation_envelope_contains_interior_path_not_only_endpoints():
    sweep=_sweep(); interior=AABB((5.,.5,.5),(5.5,1.5,1.5),WORLD_FRAME)
    assert not sweep.start_box.intersects(interior) and not sweep.end_box.intersects(interior)
    assert sweep.collides_with(interior, expected_geometry_sha256=SOURCE_SHA)
    assert sweep.continuous_envelope==AABB((0.,0.,0.),(12.,2.,2.),WORLD_FRAME)
def test_touching_boundary_and_clearance_are_conservative():
    sweep=_sweep(); near=AABB((12.2,0.,0.),(13.,1.,1.),WORLD_FRAME)
    assert sweep.collides_with(AABB((12.,0.,0.),(13.,1.,1.),WORLD_FRAME),expected_geometry_sha256=SOURCE_SHA)
    assert not sweep.collides_with(near,expected_geometry_sha256=SOURCE_SHA)
    assert sweep.collides_with(near,expected_geometry_sha256=SOURCE_SHA,clearance_mm=.2)
    with pytest.raises(SweepGeometryError,match="non-negative"): sweep.collides_with(near,expected_geometry_sha256=SOURCE_SHA,clearance_mm=-.01)
def test_coordinate_frame_mismatch_is_hard_failure():
    with pytest.raises(SweepGeometryError,match="coordinate-frame mismatch"): _sweep().collides_with(AABB((5.,.5,.5),(5.5,1.5,1.5),"ACTUATOR_LOCAL_FOREHEAD"),expected_geometry_sha256=SOURCE_SHA)
def test_collision_api_cannot_bypass_source_freshness():
    keepout=AABB((5.,.5,.5),(5.5,1.5,1.5),WORLD_FRAME)
    with pytest.raises(TypeError): _sweep().collides_with(keepout)
    with pytest.raises(SweepGeometryError,match="provenance is stale"): _sweep().collides_with(keepout,expected_geometry_sha256="2"*64)
def test_frame_identity_is_preserved_and_explicit():
    sweep=_sweep(); assert sweep.end_box.frame_id==WORLD_FRAME and sweep.continuous_envelope.frame_id==WORLD_FRAME and sweep.manifest()["coordinate_frame_id"]==WORLD_FRAME
    with pytest.raises(TypeError): AABB((0.,0.,0.),(1.,1.,1.))
def test_rotating_body_cannot_be_misrepresented_as_linear_sweep():
    with pytest.raises(SweepGeometryError,match="cannot certify changing orientation"): replace(_sweep(),rotation_invariant=False)
def test_sha256_identity_requires_exact_canonical_form():
    alpha="ab"*32; canonical=replace(_sweep(),source_geometry_sha256=alpha)
    for invalid in (alpha.upper(),f" {alpha}",f"{alpha} "):
        with pytest.raises(SweepGeometryError,match="lowercase canonical SHA-256"): replace(canonical,source_geometry_sha256=invalid)
        with pytest.raises(SweepGeometryError,match="lowercase canonical SHA-256"): require_fresh_sweep_source(canonical,expected_geometry_sha256=invalid)
def test_manifest_identity_changes_for_mechanical_path_or_frame_change():
    first=_sweep(); assert first.manifest_sha256!=replace(first,translation_xyz_mm=(10.001,0.,0.)).manifest_sha256
    assert first.manifest_sha256!=replace(first,start_box=AABB(first.start_box.minimum_xyz_mm,first.start_box.maximum_xyz_mm,"OTHER_WORLD")).manifest_sha256
def test_nonfinite_inverted_blank_and_noncanonical_identity_are_hard_failures():
    with pytest.raises(SweepGeometryError,match="finite"): AABB((0.,float("nan"),0.),(1.,1.,1.),WORLD_FRAME)
    with pytest.raises(SweepGeometryError,match="minimum cannot exceed"): AABB((2.,0.,0.),(1.,1.,1.),WORLD_FRAME)
    for frame in ("","  "," MASCK_ONE_WORLD"):
        with pytest.raises(SweepGeometryError,match="canonical string"): AABB((0.,0.,0.),(1.,1.,1.),frame)
def test_boolean_and_coercible_aliases_cannot_enter_mechanical_geometry():
    with pytest.raises(SweepGeometryError,match="not a boolean or coercible alias"): AABB((True,0.,0.),(1.,1.,1.),WORLD_FRAME)
    with pytest.raises(SweepGeometryError,match="not a boolean or coercible alias"): replace(_sweep(),translation_xyz_mm=("10.0",0.,0.))
    with pytest.raises(SweepGeometryError,match="explicit boolean"): replace(_sweep(),rotation_invariant=1)
def test_mutable_coordinate_sequences_are_snapshotted_to_immutable_tuples():
    lo=[0.,0.,0.]; hi=[1.,1.,1.]; box=AABB(lo,hi,WORLD_FRAME); before=box.manifest(); lo[0]=-999.; hi[2]=999.; assert box.manifest()==before
    delta=[10.,0.,0.]; sweep=LinearSweep("MUTABILITY_TEST",box,delta,SOURCE_SHA,True); digest=sweep.manifest_sha256; delta[0]=999.; assert sweep.translation_xyz_mm==(10.,0.,0.) and sweep.manifest_sha256==digest
def test_wrong_object_types_fail_closed_at_geometry_boundaries():
    with pytest.raises(SweepGeometryError,match="exactly three coordinates"): AABB(1.,(1.,1.,1.),WORLD_FRAME)
    with pytest.raises(SweepGeometryError,match="start_box must be an AABB"): LinearSweep("BAD",object(),(1.,0.,0.),SOURCE_SHA,True)
    with pytest.raises(SweepGeometryError,match="Collision geometry must be an AABB"): _sweep().collides_with(object(),expected_geometry_sha256=SOURCE_SHA)
