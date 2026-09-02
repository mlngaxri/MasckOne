from engineering.cell3.retention_adjustment_sweep import evaluate_adjustment_sweep
from engineering.cell3.retention_member_envelope import MemberEnvelope
from engineering.cell3.retention_package_contract import AABB, RetentionDatums


def _datums(y: float) -> RetentionDatums:
    return RetentionDatums(
        left_yoke=(-30.0, y, 0.0), right_yoke=(30.0, y, 0.0),
        left_junction=(-35.0, y, 30.0), right_junction=(35.0, y, 30.0),
        crown_apex=(0.0, y, 70.0), occipital_center=(0.0, y, 45.0),
    )


def _envs(radius: float = 1.0):
    names = ("left_yoke_link", "right_yoke_link", "crown_left", "crown_right", "occipital_left", "occipital_right")
    return {name: MemberEnvelope(radius, 0.0, 0.0) for name in names}


def test_clear_adjustment_interval_passes():
    result = evaluate_adjustment_sweep(_datums(-10.0), _datums(10.0), _envs(), {"electronics": AABB((80.0, -5.0, -5.0), (90.0, 5.0, 80.0))}, minimum_residual_clearance_mm=2.0)
    assert result.passed


def test_midstroke_collision_cannot_hide_behind_clear_endpoints():
    result = evaluate_adjustment_sweep(_datums(-20.0), _datums(20.0), _envs(), {"service": AABB((-40.0, -0.2, 20.0), (-30.0, 0.2, 40.0))}, minimum_residual_clearance_mm=0.5)
    assert not result.passed
    assert any("adjustment_keepout:service" in f for f in result.failures)


def test_member_envelope_turns_centerline_near_miss_into_failure():
    result = evaluate_adjustment_sweep(_datums(-10.0), _datums(10.0), _envs(3.0), {"harness": AABB((-29.0, -0.1, 10.0), (-28.0, 0.1, 20.0))}, minimum_residual_clearance_mm=0.25)
    assert not result.passed


def test_invalid_keepout_fails_closed():
    try:
        evaluate_adjustment_sweep(_datums(0.0), _datums(1.0), _envs(), {"bad": AABB((1.0, 0.0, 0.0), (0.0, 1.0, 1.0))}, minimum_residual_clearance_mm=0.0)
    except ValueError:
        pass
    else:
        raise AssertionError("inverted keepout must fail closed")


def test_missing_member_envelope_fails_closed():
    envs = _envs()
    envs.pop("crown_left")
    try:
        evaluate_adjustment_sweep(_datums(0.0), _datums(1.0), envs, {}, minimum_residual_clearance_mm=0.0)
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete envelope mapping must fail closed")


def test_nonfinite_minimum_fit_datum_fails_closed_before_geometry():
    bad = _datums(0.0)
    bad = RetentionDatums(**{**bad.__dict__, "left_yoke": (-30.0, float("nan"), 0.0)})
    try:
        evaluate_adjustment_sweep(bad, _datums(1.0), _envs(), {}, minimum_residual_clearance_mm=0.0)
    except ValueError:
        pass
    else:
        raise AssertionError("nonfinite minimum-fit datum must fail closed")


def test_boolean_coordinate_fails_closed_before_geometry():
    bad = _datums(1.0)
    bad = RetentionDatums(**{**bad.__dict__, "crown_apex": (0.0, True, 70.0)})
    try:
        evaluate_adjustment_sweep(_datums(0.0), bad, _envs(), {}, minimum_residual_clearance_mm=0.0)
    except ValueError:
        pass
    else:
        raise AssertionError("boolean maximum-fit coordinate must fail closed")
