import math
import pytest

from masck_one.mechanism_tolerance import ClearanceStack, ScalarTolerance

SHA = "a" * 64


def stack(**kw):
    base = dict(
        stack_id="ACTUATOR_EYE_CLEARANCE",
        coordinate_frame_id="ROOT_WORLD",
        source_geometry_sha256=SHA,
        nominal_clearance_mm=1.0,
        contributions=(("MOUNT_X", ScalarTolerance(10.0, 0.2, 0.3), -1), ("KEEP_OUT_X", ScalarTolerance(4.0, 0.1, 0.4), 1)),
    )
    base.update(kw)
    return ClearanceStack(**base)


def test_worst_case_enumerates_adverse_endpoints_and_rounds_conservatively():
    s = stack()
    got = s.worst_case_clearance_mm(current_geometry_sha256=SHA, coordinate_frame_id="ROOT_WORLD")
    assert got < 0.6
    assert math.isclose(got, 0.6, rel_tol=0.0, abs_tol=2e-16)


def test_nonpositive_worst_case_fails_closed():
    with pytest.raises(RuntimeError):
        stack(nominal_clearance_mm=0.3).assert_positive_clearance(current_geometry_sha256=SHA, coordinate_frame_id="ROOT_WORLD")


def test_stale_geometry_and_frame_mismatch_fail_closed():
    s = stack()
    with pytest.raises(RuntimeError, match="stale"):
        s.worst_case_clearance_mm(current_geometry_sha256="b" * 64, coordinate_frame_id="ROOT_WORLD")
    with pytest.raises(RuntimeError, match="frame"):
        s.worst_case_clearance_mm(current_geometry_sha256=SHA, coordinate_frame_id="ACTUATOR_LOCAL")


@pytest.mark.parametrize("value", [True, "1.0", float("nan"), float("inf"), -float("inf")])
def test_numeric_aliases_and_nonfinite_values_rejected(value):
    with pytest.raises((TypeError, ValueError)):
        ScalarTolerance(value, 0.1, 0.1)


@pytest.mark.parametrize("sensitivity", [True, 0, 2, -2, 1.0, "1"])
def test_sensitivity_is_exact_signed_axis_semantics(sensitivity):
    with pytest.raises((TypeError, ValueError)):
        stack(contributions=(("AXIS", ScalarTolerance(0.0, 0.1, 0.1), sensitivity),))


def test_mutable_input_is_snapshotted_and_duplicate_ids_rejected():
    items = [("AXIS", ScalarTolerance(0.0, 0.1, 0.1), 1)]
    s = stack(contributions=items)
    before = s.provenance_sha256
    items.append(("OTHER", ScalarTolerance(0.0, 0.2, 0.2), -1))
    assert s.provenance_sha256 == before
    with pytest.raises(ValueError, match="duplicate"):
        stack(contributions=(("AXIS", ScalarTolerance(0, 0, 0), 1), ("AXIS", ScalarTolerance(0, 0, 0), -1)))


def test_identity_and_sha_aliases_rejected():
    for bad in ("root_world", " ROOT_WORLD", "ROOT/WORLD", "ＲＯＯＴ"):
        with pytest.raises(ValueError):
            stack(coordinate_frame_id=bad)
    with pytest.raises(ValueError):
        stack(source_geometry_sha256="A" * 64)


def test_signed_zero_regenerates_deterministically():
    a = stack(contributions=(("AXIS", ScalarTolerance(-0.0, 0.0, 0.0), 1),))
    b = stack(contributions=(("AXIS", ScalarTolerance(0.0, -0.0, 0.0), 1),))
    assert a.provenance_sha256 == b.provenance_sha256


def test_provenance_changes_with_mechanical_semantics():
    a = stack()
    b = stack(contributions=(("MOUNT_X", ScalarTolerance(10.0, 0.2, 0.3), 1), ("KEEP_OUT_X", ScalarTolerance(4.0, 0.1, 0.4), 1)))
    assert a.provenance_sha256 != b.provenance_sha256
