import hashlib
import math

import pytest

from masck_one.rotational_sweep import ConservativeRotationalSweep, RotationalSweepError
from masck_one.sweep_geometry import AABB

SHA = hashlib.sha256(b"geometry-a").hexdigest()
OTHER_SHA = hashlib.sha256(b"geometry-b").hexdigest()


def sweep(**overrides):
    values = dict(source_id="ACTUATOR_TEST", source_box=AABB((-1.0,-2.0,-3.0),(1.0,2.0,3.0),"MASCK_ONE_WORLD"), pivot_xyz_mm=(0.0,0.0,0.0), pivot_frame_id="MASCK_ONE_WORLD", angle_min_deg=-15.0, angle_max_deg=15.0, source_geometry_sha256=SHA)
    values.update(overrides)
    return ConservativeRotationalSweep(**values)


def test_envelope_contains_every_source_corner_radius():
    s=sweep(); exact_r=math.sqrt(14.0); env=s.conservative_envelope
    assert s.maximum_radius_mm >= exact_r
    assert all(v <= -exact_r for v in env.minimum_xyz_mm)
    assert all(v >= exact_r for v in env.maximum_xyz_mm)


def test_large_positive_offset_bound_is_rounded_outward():
    p=(1e15,1e15,1e15); source=AABB((1e15+1,1e15,1e15),(1e15+2,1e15,1e15),"MASCK_ONE_WORLD")
    env=sweep(source_box=source,pivot_xyz_mm=p).conservative_envelope
    assert env.minimum_xyz_mm[0] < p[0]-2 and env.maximum_xyz_mm[0] > p[0]+2


def test_large_negative_offset_bound_is_rounded_outward():
    p=(-1e15,-1e15,-1e15); source=AABB((-1e15-2,-1e15,-1e15),(-1e15-1,-1e15,-1e15),"MASCK_ONE_WORLD")
    env=sweep(source_box=source,pivot_xyz_mm=p).conservative_envelope
    assert env.minimum_xyz_mm[0] < p[0]-2 and env.maximum_xyz_mm[0] > p[0]+2


def test_unrepresentable_conservative_envelope_fails_closed():
    huge=float.fromhex("0x1.fffffffffffffp+1023"); source=AABB((huge,0,0),(huge,1,1),"MASCK_ONE_WORLD")
    with pytest.raises(RotationalSweepError,match="not finitely representable"): _=sweep(source_box=source,pivot_xyz_mm=(-huge,0,0)).conservative_envelope


def test_continuous_mid_rotation_collision_cannot_hide_between_endpoint_samples():
    s=sweep(source_box=AABB((2,-.1,-.1),(3,.1,.1),"MASCK_ONE_WORLD"),angle_min_deg=0,angle_max_deg=180)
    assert s.collides(AABB((-.1,2.4,-.1),(.1,2.6,.1),"MASCK_ONE_WORLD"),current_source_geometry_sha256=SHA)


def test_stale_geometry_rejected_before_collision_result():
    with pytest.raises(RotationalSweepError,match="stale"): sweep().collides(AABB((10,10,10),(11,11,11),"MASCK_ONE_WORLD"),current_source_geometry_sha256=OTHER_SHA)


def test_coordinate_frame_mismatch_fails_closed():
    with pytest.raises(RotationalSweepError,match="coordinate-frame mismatch"): sweep().collides(AABB((0,0,0),(1,1,1),"ACTUATOR_LOCAL"),current_source_geometry_sha256=SHA)


def test_pivot_frame_must_match_source_frame_before_geometry_execution():
    with pytest.raises(RotationalSweepError,match="pivot/source coordinate-frame mismatch"): sweep(pivot_frame_id="ACTUATOR_LOCAL")


def test_pivot_frame_is_provenance_bearing_and_propagates_to_envelope():
    local=sweep(source_box=AABB((-1,-1,-1),(1,1,1),"ACTUATOR_LOCAL"),pivot_frame_id="ACTUATOR_LOCAL")
    assert local.conservative_envelope.frame_id == "ACTUATOR_LOCAL" and local.sweep_sha256 != sweep().sweep_sha256


@pytest.mark.parametrize("field,value",[("angle_min_deg",True),("angle_max_deg","15"),("angle_max_deg",float("nan")),("pivot_xyz_mm",(0,False,0)),("pivot_frame_id"," MASCK_ONE_WORLD"),("pivot_frame_id","")])
def test_numeric_aliases_nonfinite_and_noncanonical_frame_inputs_rejected(field,value):
    with pytest.raises(RotationalSweepError): sweep(**{field:value})


@pytest.mark.parametrize("source_id",["actuator_test","ACTUATOR TEST"," ACTUATOR_TEST","ACTUATOR_TEST ","ACTUATOR/TEST","ＡＣＴＵＡＴＯＲ_TEST",""])
def test_source_identity_aliases_and_noncanonical_namespace_rejected(source_id):
    with pytest.raises(RotationalSweepError,match="source_id"): sweep(source_id=source_id)


def test_reversed_angle_interval_rejected():
    with pytest.raises(RotationalSweepError,match="minimum angle"): sweep(angle_min_deg=10,angle_max_deg=-10)


def test_manifest_is_deterministic_and_explicitly_not_physical_evidence():
    a=sweep(); b=sweep(); assert a.sweep_sha256 == b.sweep_sha256; assert a.manifest()["physical_validation_eligible"] is False


def test_angle_interval_changes_provenance_even_when_conservative_box_is_same():
    assert sweep(angle_min_deg=-5,angle_max_deg=5).sweep_sha256 != sweep().sweep_sha256


def test_whitespace_or_noncanonical_digest_rejected():
    with pytest.raises(RotationalSweepError): sweep(source_geometry_sha256=SHA.upper())
    with pytest.raises(RotationalSweepError): sweep(source_geometry_sha256=f" {SHA}")


def test_signed_zero_aliases_do_not_split_rotational_sweep_identity():
    positive=sweep(source_box=AABB((0.0,0.0,0.0),(1,2,3),"MASCK_ONE_WORLD"),pivot_xyz_mm=(0.0,0.0,0.0),angle_min_deg=0.0,angle_max_deg=0.0)
    negative=sweep(source_box=AABB((-0.0,-0.0,-0.0),(1,2,3),"MASCK_ONE_WORLD"),pivot_xyz_mm=(-0.0,-0.0,-0.0),angle_min_deg=-0.0,angle_max_deg=-0.0)
    assert positive.sweep_sha256 == negative.sweep_sha256
    assert negative.manifest()["pivot_xyz_mm"] == [0.0,0.0,0.0]
