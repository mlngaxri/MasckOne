from dataclasses import replace

import pytest

from masck_one.distribution_geometry import (
    DistributionGeometryError,
    _direction_away_from_nearest,
    _protected_clearance_mm,
)
from masck_one.distribution_geometry_evidence import validate_canonical_distribution_geometry
from masck_one.spatial import Point2
from tests.test_distribution_geometry import built as built_fixture


@pytest.fixture(scope="module")
def built(request):
    return request.getfixturevalue("built_fixture")


def _validate(built, geometry):
    model, water, cleanser, frame, pump, manifold, _ = built
    return validate_canonical_distribution_geometry(
        geometry,
        authority=model.authority,
        manifold=manifold,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=model.coverage_mesh,
        protected=model.protected_volumes,
    )


def test_accepts_canonical_current_source_distribution_geometry(built):
    *_, geometry = built
    assert _validate(built, geometry) is geometry


def test_rejects_eligible_but_noncanonical_outlet_substitution(built):
    model, *_, geometry = built
    selected = {item.source_triangle_index for item in geometry.placements}
    replacement_triangle = next(
        triangle
        for triangle in model.coverage_mesh.target_triangles
        if triangle.triangle_index not in selected
        and triangle.region_id == geometry.placements[0].region_id
        and _protected_clearance_mm(
            Point2(triangle.centroid.x, triangle.centroid.y), model.protected_volumes
        )
        >= geometry.required_clearance_mm
    )

    original = geometry.placements[0]
    point = Point2(replacement_triangle.centroid.x, replacement_triangle.centroid.y)
    substituted = replace(
        original,
        source_triangle_index=replacement_triangle.triangle_index,
        region_id=replacement_triangle.region_id,
        center_xyz_mm=replacement_triangle.centroid.as_tuple(),
        lateral_direction_xyz=_direction_away_from_nearest(point, model.protected_volumes),
        protected_clearance_mm=_protected_clearance_mm(point, model.protected_volumes),
    )
    placements = (substituted, *geometry.placements[1:])
    grooves = list(geometry.grooves)
    grooves[0] = replace(
        grooves[0],
        origin_xyz_mm=substituted.center_xyz_mm,
        lateral_direction_xyz=substituted.lateral_direction_xyz,
    )
    altered = replace(geometry, placements=placements, grooves=tuple(grooves))

    # The existing per-placement source validator intentionally accepts any legal
    # current-source triangle.  The consumption boundary must additionally preserve
    # the deterministic distribution selection itself.
    model, water, cleanser, frame, pump, manifold, _ = built
    altered.validate_current_sources(
        authority=model.authority,
        manifold=manifold,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=model.coverage_mesh,
        protected=model.protected_volumes,
    )
    with pytest.raises(DistributionGeometryError, match="canonical current-source outlet selection"):
        _validate(built, altered)


def test_rejects_wrong_evidence_type(built):
    with pytest.raises(DistributionGeometryError, match="exact DistributionGeometryArchitecture"):
        _validate(built, object())
