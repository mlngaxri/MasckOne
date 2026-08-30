from __future__ import annotations

import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.facial_surface import (
    FacialSurfaceDescriptor,
    FacialSurfaceError,
    build_planar_development_surface,
    facial_surface_from_registered_asset,
)
from masck_one.reference_surfaces import (
    ReferenceSurfaceAsset,
    SurfaceProvenance,
    TriangleMesh,
    identity_registration,
)
from masck_one.spatial import Point3


def test_planar_development_surface_is_deterministic_and_non_anatomical():
    authority = load_authority()
    a = build_planar_development_surface(authority)
    b = build_planar_development_surface(authority)

    assert a.mesh.normalized_sha256() == b.mesh.normalized_sha256()
    assert a.descriptor.surface_id == "MASCK_ONE-FACE-SURFACE-PLANAR-DEV-V1"
    assert a.descriptor.anatomical_validation_eligible is False
    assert a.is_planar is True
    assert a.z_bounds_mm == (0.0, 0.0)


def test_planar_surface_uses_functional_frame_envelope_without_exceeding_it():
    authority = load_authority()
    surface = build_planar_development_surface(authority)
    frame_w, frame_h = authority.pair("geometry", "functional_frame_xy_mm")
    min_x, max_x, min_y, max_y = surface.xy_bounds_mm

    assert min_x >= -frame_w / 2.0 - 1e-12
    assert max_x <= frame_w / 2.0 + 1e-12
    assert min_y >= -frame_h / 2.0 - 1e-12
    assert max_y <= frame_h / 2.0 + 1e-12
    assert surface.mesh.vertex_count > 1000
    assert surface.mesh.triangle_count > 1500


def test_landmark_projection_is_explicitly_development_only_on_planar_surface():
    authority = load_authority()
    reference = build_facial_reference(authority)
    surface = build_planar_development_surface(authority)
    projections = surface.project_reference_landmarks(reference)

    assert len(projections) == 5
    assert {projection.landmark_id for projection in projections} == {landmark.id for landmark in reference.landmarks}
    assert all(projection.surface_point.z == 0.0 for projection in projections)
    assert all(projection.evidence_status == "DEVELOPMENT_PROJECTION_NOT_ANATOMICAL_EVIDENCE" for projection in projections)
    assert max(projection.xy_error_mm for projection in projections) < 3.0


def test_surface_manifest_is_stable_and_traceable():
    surface = build_planar_development_surface(load_authority())
    manifest = surface.manifest()

    assert manifest["surface_id"] == surface.descriptor.surface_id
    assert manifest["kind"] == "PLANAR_DEVELOPMENT_REFERENCE"
    assert manifest["anatomical_validation_eligible"] is False
    assert manifest["mesh"]["mesh_sha256"] == surface.mesh.normalized_sha256()
    assert manifest["mesh"]["z_bounds_mm"] == [0.0, 0.0]


def test_planar_descriptor_cannot_be_misclassified_as_anatomical_evidence():
    with pytest.raises(FacialSurfaceError, match="never be anatomical-validation evidence"):
        FacialSurfaceDescriptor(
            surface_id="BAD",
            kind="PLANAR_DEVELOPMENT_REFERENCE",
            evidence_status="BAD",
            source_asset_id=None,
            source_revision="r1",
            source_sha256="0" * 64,
            anatomical_validation_eligible=True,
        )


def test_registered_external_surface_preserves_source_traceability_but_defaults_to_not_approved():
    mesh = TriangleMesh(
        vertices=(
            Point3(-10.0, -10.0, 2.0),
            Point3(10.0, -10.0, 3.0),
            Point3(0.0, 10.0, 8.0),
        ),
        triangles=((0, 1, 2),),
    )
    provenance = SurfaceProvenance(
        asset_id="TEST-FACE-SCAN",
        source_kind="FACE_SCAN",
        source_label="synthetic test face scan",
        source_revision="scan-r1",
        source_units="mm",
        handedness="right",
        x_positive="wearer right",
        y_positive="superior",
        z_positive="anterior",
        source_sha256=mesh.normalized_sha256(),
        evidence_status="TEST_ONLY",
    )
    asset = ReferenceSurfaceAsset(provenance, mesh, identity_registration())
    surface = facial_surface_from_registered_asset(asset, surface_id="TEST-REGISTERED")

    assert surface.descriptor.source_asset_id == "TEST-FACE-SCAN"
    assert surface.descriptor.source_sha256 == mesh.normalized_sha256()
    assert surface.descriptor.anatomical_validation_eligible is False
    assert surface.is_planar is False


def test_registered_surface_requires_explicit_promotion_for_validation_eligibility():
    mesh = TriangleMesh(
        vertices=(Point3(0.0, 0.0, 0.0), Point3(10.0, 0.0, 1.0), Point3(0.0, 10.0, 2.0)),
        triangles=((0, 1, 2),),
    )
    provenance = SurfaceProvenance(
        asset_id="TEST-HEADFORM",
        source_kind="HEADFORM_SCAN",
        source_label="synthetic test headform",
        source_revision="r1",
        source_units="mm",
        handedness="right",
        x_positive="wearer right",
        y_positive="superior",
        z_positive="anterior",
        source_sha256=mesh.normalized_sha256(),
        evidence_status="TEST_ONLY",
    )
    surface = facial_surface_from_registered_asset(
        ReferenceSurfaceAsset(provenance, mesh, identity_registration()),
        surface_id="TEST-PROMOTED",
        anatomical_validation_eligible=True,
        evidence_status="TEST_EXPLICIT_PROMOTION",
    )

    assert surface.descriptor.anatomical_validation_eligible is True
    assert surface.descriptor.evidence_status == "TEST_EXPLICIT_PROMOTION"


def test_grid_resolution_has_lower_bound():
    with pytest.raises(FacialSurfaceError, match="at least 5x5"):
        build_planar_development_surface(load_authority(), x_samples=4, y_samples=10)
