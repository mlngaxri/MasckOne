import math
import pytest

from engineering.cell3.quick_release_sweep import MovingMember, evaluate_release_sweep
from engineering.cell3.retention_package_contract import AABB


def member(y0: float, y1: float, radius: float = 0.5) -> MovingMember:
    return MovingMember((-5.0, y0, 0.0), (5.0, y0, 0.0), (-5.0, y1, 0.0), (5.0, y1, 0.0), radius)


def test_clear_release_motion_passes():
    result = evaluate_release_sweep(
        {"yoke_latch": member(5.0, 7.0)},
        {"hair_keepout": AABB((-2.0, -1.0, -1.0), (2.0, 1.0, 1.0))},
        minimum_residual_clearance_mm=1.0,
    )
    assert result.passed
    assert result.minimum_clearance_mm >= 3.5


def test_midstroke_collision_hidden_by_clear_endpoints_fails():
    # Endpoints clear on opposite sides. The continuous path crosses the keepout.
    result = evaluate_release_sweep(
        {"release_tab": member(-3.0, 3.0, 0.2)},
        {"shell": AABB((-1.0, -0.1, -1.0), (1.0, 0.1, 1.0))},
        minimum_residual_clearance_mm=0.0,
    )
    assert not result.passed
    assert any("release_keepout:shell" in f for f in result.failures)


def test_tolerance_envelope_can_fail_clear_centerline():
    result = evaluate_release_sweep(
        {"latch": MovingMember((-5.0, 2.0, 0.0), (5.0, 2.0, 0.0), (-5.0, 2.0, 0.0), (5.0, 2.0, 0.0), 0.5, 0.4, 0.2)},
        {"electronics": AABB((-1.0, 0.0, -1.0), (1.0, 1.0, 1.0))},
        minimum_residual_clearance_mm=0.0,
    )
    assert not result.passed


@pytest.mark.parametrize("bad", [math.nan, math.inf, True])
def test_invalid_motion_coordinates_fail_closed(bad):
    m = MovingMember((bad, 3.0, 0.0), (1.0, 3.0, 0.0), (0.0, 4.0, 0.0), (1.0, 4.0, 0.0), 0.2)
    with pytest.raises(ValueError):
        evaluate_release_sweep({"latch": m}, {}, minimum_residual_clearance_mm=0.0)


def test_inverted_keepout_fails_closed():
    with pytest.raises(ValueError):
        evaluate_release_sweep(
            {"latch": member(3.0, 4.0)},
            {"bad": AABB((1.0, 1.0, 1.0), (-1.0, -1.0, -1.0))},
            minimum_residual_clearance_mm=0.0,
        )


def test_empty_moving_geometry_is_not_proof():
    with pytest.raises(ValueError):
        evaluate_release_sweep({}, {}, minimum_residual_clearance_mm=0.0)
