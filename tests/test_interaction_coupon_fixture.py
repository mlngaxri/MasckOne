import math
from dataclasses import replace

import pytest

from masck_one.interaction_coupon_fixture import FixtureDimensions, build_fixture


def test_nest_volume_floor_and_separate_pusher():
    d = FixtureDimensions()
    parts = build_fixture(d)
    nest = parts["coupon_nest"]
    expected = d.base_width_mm * d.base_length_mm * d.base_height_mm - math.pi * ((d.coupon_diameter_mm + d.diametral_clearance_mm) / 2)**2 * d.nest_depth_mm
    assert nest.isValid()
    assert nest.Volume() == pytest.approx(expected)
    assert len(nest.Solids()) == 1
    assert parts["coupon_reference_only"].intersect(nest).Volume() < 1e-8
    assert parts["flat_pusher"].BoundingBox().zmin - parts["coupon_reference_only"].BoundingBox().zmax == pytest.approx(d.pusher_gap_mm)
    assert all(s.isValid() and len(s.Solids()) == 1 for s in parts.values())


@pytest.mark.parametrize("changes", [{"nest_depth_mm": 6}, {"nest_depth_mm": 4},
    {"base_width_mm": 12}, {"pusher_diameter_mm": 12}, {"pusher_gap_mm": -1},
    {"base_height_mm": math.nan}, {"coupon_height_mm": True}])
def test_invalid_geometry_rejected(changes):
    with pytest.raises(ValueError):
        build_fixture(replace(FixtureDimensions(), **changes))
