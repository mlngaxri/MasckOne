from __future__ import annotations

import pytest
import cadquery as cq

import masck_one.treatment_reference_geometry as reference_geometry
from masck_one.treatment_reference_geometry import (
    TreatmentReferenceGeometryError,
    _explicit_list_common,
    _exact_shape_distance,
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


def test_exact_distance_skips_only_provably_separated_pairs_with_overlapping_aabbs(monkeypatch):
    ring = (
        cq.Workplane("XY")
        .circle(2.0)
        .circle(1.0)
        .extrude(1.0)
        .val()
    )
    inner = cq.Workplane("XY").circle(0.5).extrude(1.0).val()

    # Their axis-aligned boxes overlap in all axes, but the central cylinder remains
    # exactly separated from the ring's inner wall. Common must not be needed.
    assert _exact_shape_distance(ring, inner) > 0.0

    def forbidden_common(_left: cq.Shape, _right: cq.Shape) -> cq.Shape:
        raise AssertionError("provably separated pair should not execute Boolean Common")

    monkeypatch.setattr(reference_geometry, "_direct_common", forbidden_common)
    assert intersection_volume_mm3(ring, inner) == 0.0


def test_exact_distance_does_not_hide_touching_or_positive_overlap(monkeypatch):
    base = _box(0.0)
    overlapping = _box(0.75)
    assert _exact_shape_distance(base, overlapping) == 0.0

    calls = 0
    original = reference_geometry._direct_common

    def counted_common(left: cq.Shape, right: cq.Shape) -> cq.Shape:
        nonlocal calls
        calls += 1
        return original(left, right)

    monkeypatch.setattr(reference_geometry, "_direct_common", counted_common)
    assert intersection_volume_mm3(base, overlapping) == pytest.approx(0.25, abs=1e-9)
    assert calls > 0


def test_exact_cut_volume_fallback_distinguishes_contact_from_penetration(monkeypatch):
    base = _box(0.0)

    def failed_common(_left: cq.Shape, _right: cq.Shape) -> cq.Shape:
        raise TreatmentReferenceGeometryError("forced Common failure")

    monkeypatch.setattr(reference_geometry, "_direct_common", failed_common)

    # Exact face contact removes no volume from A, while the 0.25 mm overlap does.
    assert intersection_volume_mm3(base, _box(1.0)) == 0.0
    assert intersection_volume_mm3(base, _box(0.75)) == pytest.approx(0.25, abs=1e-9)


def test_exact_cut_volume_fallback_tries_reverse_subtraction_when_first_direction_fails(monkeypatch):
    base = _box(0.0)
    touching = _box(1.0)
    original_cut = reference_geometry._direct_cut
    cut_calls = 0

    def failed_common(_left: cq.Shape, _right: cq.Shape) -> cq.Shape:
        raise TreatmentReferenceGeometryError("forced Common failure")

    def fail_first_cut(left: cq.Shape, right: cq.Shape) -> cq.Shape:
        nonlocal cut_calls
        cut_calls += 1
        if cut_calls == 1:
            raise TreatmentReferenceGeometryError("forced first subtraction failure")
        return original_cut(left, right)

    monkeypatch.setattr(reference_geometry, "_direct_common", failed_common)
    monkeypatch.setattr(reference_geometry, "_direct_cut", fail_first_cut)

    assert intersection_volume_mm3(base, touching) == 0.0
    assert cut_calls == 2


def test_exact_partition_keeps_initial_operand_side_locked_through_recursion(monkeypatch):
    left = cq.Workplane("XY").box(4.0, 1.0, 1.0).val()
    right = cq.Workplane("XY").box(8.0, 1.0, 1.0).val()
    original_common = reference_geometry._direct_common
    original_partition = reference_geometry._partition_solid_once
    partition_sources: list[tuple[float, float]] = []

    def fail_common_until_right_piece_is_small(
        left_operand: cq.Shape,
        right_operand: cq.Shape,
    ) -> cq.Shape:
        right_bounds = right_operand.BoundingBox()
        right_x_span = right_bounds.xmax - right_bounds.xmin
        if right_x_span > 1.05:
            raise TreatmentReferenceGeometryError("forced Common failure until right partition is small")
        return original_common(left_operand, right_operand)

    def failed_cut(_left: cq.Shape, _right: cq.Shape) -> cq.Shape:
        raise TreatmentReferenceGeometryError("forced Cut failure")

    def recorded_partition(source: cq.Shape) -> list[cq.Shape]:
        bounds = source.BoundingBox()
        partition_sources.append(
            (
                bounds.xmax - bounds.xmin,
                (bounds.xmin + bounds.xmax) / 2.0,
            )
        )
        return original_partition(source)

    monkeypatch.setattr(reference_geometry, "_direct_common", fail_common_until_right_piece_is_small)
    monkeypatch.setattr(reference_geometry, "_direct_cut", failed_cut)
    monkeypatch.setattr(reference_geometry, "_partition_solid_once", recorded_partition)

    assert intersection_volume_mm3(left, right) == pytest.approx(4.0, abs=1e-8)
    assert partition_sources[0][0] == pytest.approx(8.0, abs=1e-9)
    # Under the old role-flipping recursion, once a right-hand partition became
    # narrower than the unchanged left operand the algorithm switched sides and
    # partitioned the original 4 mm left box at center X=0. The selected partition
    # operand must now stay on the original right side for the entire recursion.
    assert not any(
        span == pytest.approx(4.0, abs=1e-9)
        and center == pytest.approx(0.0, abs=1e-9)
        for span, center in partition_sources[1:]
    )


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

def _solid(dx: float, dy: float, dz: float, at: tuple[float, float, float]) -> cq.Shape:
    return cq.Workplane("XY").box(dx, dy, dz, centered=False).translate(at).val()


def test_kernel_common_reaching_outside_the_operand_overlap_is_refused() -> None:
    """A common must lie inside both operands; anything else is not an intersection."""
    left = _solid(2.0, 2.0, 2.0, (0.0, 0.0, 0.0))
    right = _solid(2.0, 2.0, 2.0, (1.0, 0.0, 0.0))
    escaped = _solid(2.0, 2.0, 2.0, (50.0, 50.0, 50.0))
    with pytest.raises(TreatmentReferenceGeometryError, match="lies outside the operand overlap"):
        reference_geometry._common_positive_volume_mm3(escaped, left, right)


def test_observed_ocp_signature_returning_the_whole_opposite_operand_is_refused() -> None:
    """Measured on OCP 7.9.3.1: Common(sliver, slab) returned the entire slab.

    The sliver holds 0.000135 mm3 inside a 15x33x9 mm box; Common reported IsDone()
    and returned a 121799 mm3 invalid shape, about 9e8 times any possible
    intersection. The overlap screen catches it on extent alone.
    """
    sliver = _solid(15.1, 32.8, 8.9, (-47.2, 69.7, -4.9))
    slab = _solid(200.0, 300.0, 2.03, (-100.0, -150.0, 2.0))
    with pytest.raises(TreatmentReferenceGeometryError, match="lies outside the operand overlap"):
        reference_geometry._common_positive_volume_mm3(slab, sliver, slab)


def test_kernel_common_exceeding_the_overlap_volume_is_refused() -> None:
    """Double-counted material stays inside the overlap box but cannot be a common."""
    left = _solid(2.0, 2.0, 2.0, (0.0, 0.0, 0.0))
    right = _solid(2.0, 2.0, 2.0, (0.0, 0.0, 0.0))
    doubled = cq.Compound.makeCompound([left.Solids()[0], right.Solids()[0]])
    assert float(doubled.Volume()) == pytest.approx(16.0)
    with pytest.raises(TreatmentReferenceGeometryError, match="exceeds the operand overlap volume"):
        reference_geometry._common_positive_volume_mm3(doubled, left, right)


def test_legitimate_overlapping_common_is_still_counted() -> None:
    """The guard screens impossible results only; a real intersection is unaffected."""
    left = _solid(2.0, 2.0, 2.0, (0.0, 0.0, 0.0))
    right = _solid(2.0, 2.0, 2.0, (1.0, 0.0, 0.0))
    common = _explicit_list_common(left, right)
    assert reference_geometry._common_positive_volume_mm3(common, left, right) == pytest.approx(4.0)
    assert intersection_volume_mm3(left, right) == pytest.approx(4.0)


def test_empty_common_remains_zero_without_tripping_the_guard() -> None:
    left = _solid(1.0, 1.0, 1.0, (0.0, 0.0, 0.0))
    right = _solid(1.0, 1.0, 1.0, (10.0, 0.0, 0.0))
    empty = _explicit_list_common(left, right)
    assert reference_geometry._common_positive_volume_mm3(empty, left, right) == 0.0


def test_guard_refuses_a_common_for_provably_separated_operands() -> None:
    left = _solid(1.0, 1.0, 1.0, (0.0, 0.0, 0.0))
    right = _solid(1.0, 1.0, 1.0, (10.0, 0.0, 0.0))
    bogus = _solid(1.0, 1.0, 1.0, (0.0, 0.0, 0.0))
    with pytest.raises(TreatmentReferenceGeometryError, match="bounding boxes do not overlap"):
        reference_geometry._common_positive_volume_mm3(bogus, left, right)


# left x[0,2] y[0,2] z[0,2] and right x[1,3] y[0,2] z[0,2] overlap in x[1,2] y[0,2] z[0,2],
# so the overlap ceiling is 4 mm3. Each escape below stays under that ceiling, so only the
# containment screen for that one axis and side can reject it.
_GUARD_LEFT = (2.0, 2.0, 2.0, (0.0, 0.0, 0.0))
_GUARD_RIGHT = (2.0, 2.0, 2.0, (1.0, 0.0, 0.0))


@pytest.mark.parametrize(
    "axis_and_side, escape",
    [
        ("x-min", (1.0, 2.0, 1.0, (0.5, 0.0, 0.0))),
        ("x-max", (1.0, 1.0, 1.0, (1.5, 0.0, 0.0))),
        ("y-min", (1.0, 1.0, 1.0, (1.0, -0.5, 0.0))),
        ("y-max", (1.0, 1.0, 1.0, (1.0, 1.5, 0.0))),
        ("z-min", (1.0, 1.0, 1.0, (1.0, 0.0, -0.5))),
        ("z-max", (1.0, 1.0, 1.0, (1.0, 0.0, 1.5))),
    ],
)
def test_containment_screen_rejects_each_axis_and_side_independently(axis_and_side, escape) -> None:
    left = _solid(*_GUARD_LEFT)
    right = _solid(*_GUARD_RIGHT)
    bogus = _solid(*escape)
    assert float(bogus.Volume()) <= 4.0, axis_and_side
    with pytest.raises(TreatmentReferenceGeometryError, match="lies outside the operand overlap"):
        reference_geometry._common_positive_volume_mm3(bogus, left, right)


def test_containment_screen_accepts_a_common_inside_the_overlap() -> None:
    left = _solid(*_GUARD_LEFT)
    right = _solid(*_GUARD_RIGHT)
    inside = _solid(1.0, 1.0, 1.0, (1.0, 0.0, 0.0))
    assert reference_geometry._common_positive_volume_mm3(inside, left, right) == pytest.approx(1.0)
