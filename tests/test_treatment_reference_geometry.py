from __future__ import annotations

import pytest
import cadquery as cq

from masck_one.treatment_reference_geometry import (
    _explicit_list_common,
    intersection_volume_mm3,
    translation_reference_compound,
)


def _box(center_x: float) -> cq.Shape:
    return (
        cq.Workplane("XY")
        .box(1.0, 1.0, 1.0)
        .translate((center_x, 0.0, 0.0))
        .val()
    )


def test_pairwise_intersection_distinguishes_gap_touch_and_positive_overlap():
    base = _box(0.0)
    assert intersection_volume_mm3(base, _box(1.01)) == 0.0
    assert intersection_volume_mm3(base, _box(1.0)) == 0.0
    assert intersection_volume_mm3(base, _box(0.75)) == pytest.approx(0.25, abs=1e-9)


def test_explicit_list_common_preserves_exact_positive_common_semantics():
    common = _explicit_list_common(_box(0.0), _box(0.75))
    assert common.isValid()
    assert common.Solids()
    assert sum(float(solid.Volume()) for solid in common.Solids()) == pytest.approx(0.25, abs=1e-9)


def test_translation_reference_is_boolean_free_and_covers_midpath_collision():
    moving = (
        cq.Workplane("XY")
        .box(1.0, 1.0, 1.0)
        .translate((0.0, -2.0, 0.0))
        .val()
    )
    sweep = translation_reference_compound(moving, (0.0, 4.0, 0.0))
    obstacle = cq.Workplane("XY").box(0.4, 0.4, 0.4).val()
    assert len(sweep.Solids()) > 1
    assert intersection_volume_mm3(sweep, obstacle) > 0.0


def test_translation_reference_does_not_require_fusing_swept_pieces():
    ring = (
        cq.Workplane("XY")
        .circle(2.0)
        .circle(1.2)
        .extrude(0.25)
        .val()
    )
    sweep = translation_reference_compound(ring, (0.0, 3.0, 0.0))
    assert sweep.Solids()
    assert all(solid.isValid() for solid in sweep.Solids())


def test_translation_reference_skips_zero_volume_axial_cylinder_side_sweep():
    cylinder = cq.Workplane("XY").circle(1.5).extrude(2.0).val()
    sweep = translation_reference_compound(cylinder, (0.0, 0.0, 3.0))

    assert sweep.Solids()
    assert all(solid.isValid() and solid.Volume() > 0.0 for solid in sweep.Solids())
    bounds = sweep.BoundingBox()
    assert bounds.zmin == pytest.approx(0.0, abs=1e-9)
    assert bounds.zmax == pytest.approx(5.0, abs=1e-9)

    midpath_obstacle = (
        cq.Workplane("XY")
        .circle(0.25)
        .extrude(0.25)
        .translate((0.0, 0.0, 3.0))
        .val()
    )
    assert intersection_volume_mm3(sweep, midpath_obstacle) > 0.0
