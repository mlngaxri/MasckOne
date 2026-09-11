import math
import pytest

from masck_one import primary_control_haptic as base
from masck_one.primary_control_touch_surface import (
    appearance_contract, dish_surface_z, refine_touch_surface,
)


@pytest.fixture(scope="module")
def cap():
    top = base._cylinder(base.CAP_DIAMETER_MM, base.CAP_THICKNESS_MM, 0)
    stem = base._cylinder(base.STEM_DIAMETER_MM, 0.8, -0.7)
    core = base._cylinder(base.INERTIA_CORE_DIAMETER_MM, base.INERTIA_CORE_THICKNESS_MM,
                          (base.CAP_THICKNESS_MM-base.INERTIA_CORE_THICKNESS_MM)/2)
    old = base._dish_cap(top.fuse(stem).cut(core), base.CAP_THICKNESS_MM)
    return old, refine_touch_surface(old, 0)


def test_cap_is_solid_polymer_with_no_remaining_insert_cavity(cap):
    old, new = cap
    assert new.isValid() and len(new.Solids()) == 1
    assert new.isInside((base.MOUNT_X_MM, base.MOUNT_Y_MM, 0.3))
    assert not old.isInside((base.MOUNT_X_MM, base.MOUNT_Y_MM, 0.3))
    lower = base._box(20, 20, 1, (base.MOUNT_X_MM, base.MOUNT_Y_MM, -0.5001))
    assert new.intersect(lower).Volume() == pytest.approx(old.intersect(lower).Volume(), abs=1e-7)
    # OCC bounding boxes include edge tolerances (the observed diameter is padded
    # by 2e-7 mm). Check the analytic rim and real material containment instead.
    circular_radii = [edge.radius() for edge in new.Edges() if edge.geomType() == "CIRCLE" and edge.BoundingBox().zlen < 1e-6]
    assert max(circular_radii) == pytest.approx(base.CAP_DIAMETER_MM / 2, abs=1e-9)
    envelope = base._cylinder(base.CAP_DIAMETER_MM, 2.0, -1.0)
    assert new.cut(envelope).Volume() < 1e-7


def test_mark_follows_dish_including_previously_missing_inner_tips(cap):
    _, new = cap
    points = [(-2.1, 0), (2.1, 0), (-0.42, 0.137), (0.42, 0.137), (-1.21, 0.825), (1.21, 0.825)]
    for x, y in points:
        floor = dish_surface_z(base.CAP_THICKNESS_MM, math.hypot(x, y)) - base.M_CUT_DEBOSS_MM
        assert new.isInside((base.MOUNT_X_MM+x, base.MOUNT_Y_MM+y, floor-0.002))
        assert not new.isInside((base.MOUNT_X_MM+x, base.MOUNT_Y_MM+y, floor+0.002))
        assert floor >= 0.50


def test_touch_surface_contract_preserves_colour_and_reduces_parts():
    spec = appearance_contract()
    assert spec["palette"]["hex"] == "#DED9CF"
    assert "no degradable rubberized" in spec["material_family"]
    assert spec["inertia_core_selected"] is False
    assert spec["former_minimum_skin_above_core_mm"] == pytest.approx(0.055)
    assert spec["new_conservative_polymer_below_mark_mm"] >= 0.50
    assert spec["rim_round_mm"] == 0.10
