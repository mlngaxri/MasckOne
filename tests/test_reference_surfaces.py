from __future__ import annotations

import pytest

from masck_one.reference_surfaces import (
    ReferenceSurfaceAsset,
    ReferenceSurfaceError,
    SurfaceProvenance,
    SurfaceRegistration,
    TriangleMesh,
    identity_registration,
    mesh_from_payload,
    verify_source_digest,
)
from masck_one.spatial import Matrix3, Point3, RigidTransform, Vector3


def _mesh() -> TriangleMesh:
    return TriangleMesh(
        vertices=(
            Point3(0.0, 0.0, 0.0),
            Point3(1.0, 0.0, 0.0),
            Point3(0.0, 2.0, 0.0),
            Point3(0.0, 0.0, 3.0),
        ),
        triangles=((0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)),
    )


def _provenance(mesh: TriangleMesh, *, units: str = "mm", handedness: str = "right") -> SurfaceProvenance:
    return SurfaceProvenance(
        asset_id="TEST-HEADFORM-001",
        source_kind="SYNTHETIC_TEST_FIXTURE",
        source_label="unit-test tetrahedron",
        source_revision="r1",
        source_units=units,
        handedness=handedness,
        x_positive="source +X explicitly documented",
        y_positive="source +Y explicitly documented",
        z_positive="source +Z explicitly documented",
        source_sha256=mesh.normalized_sha256(),
        evidence_status="SYNTHETIC_TEST_ONLY",
    )


def test_normalized_mesh_hash_is_deterministic():
    mesh = _mesh()
    assert mesh.normalized_sha256() == _mesh().normalized_sha256()
    assert len(mesh.normalized_sha256()) == 64


def test_normalized_payload_digest_verification_passes_and_fails_deterministically():
    mesh = _mesh()
    verify_source_digest(mesh, mesh.normalized_sha256())
    with pytest.raises(ReferenceSurfaceError, match="digest mismatch"):
        verify_source_digest(mesh, "0" * 64)


def test_unit_conversion_occurs_before_registration():
    mesh = _mesh()
    registration = SurfaceRegistration(
        source_to_global=RigidTransform.from_translation(Vector3(10.0, -5.0, 7.0)),
        method="UNIT_TEST_TRANSLATION",
        registration_revision="r1",
    )
    asset = ReferenceSurfaceAsset(_provenance(mesh, units="m"), mesh, registration)

    assert asset.source_point_to_global(Point3(1.0, 2.0, 3.0)) == Point3(1010.0, 1995.0, 3007.0)


def test_inches_are_converted_exactly_to_mm():
    mesh = _mesh()
    asset = ReferenceSurfaceAsset(_provenance(mesh, units="in"), mesh, identity_registration())
    point = asset.source_point_to_global(Point3(1.0, 0.0, 0.0))
    assert point.x == pytest.approx(25.4)


def test_rigid_registration_preserves_post_unit_normalized_lengths():
    mesh = _mesh()
    transform = RigidTransform(
        Matrix3.rotation_z(37.0).multiply(Matrix3.rotation_y(-12.0)),
        Vector3(31.0, -14.0, 8.0),
    )
    asset = ReferenceSurfaceAsset(
        _provenance(mesh, units="cm"),
        mesh,
        SurfaceRegistration(transform, "LANDMARK_RIGID_FIT", "r2"),
    )

    a = asset.source_point_to_global(mesh.vertices[0])
    b = asset.source_point_to_global(mesh.vertices[1])
    assert a.vector_to(b).norm() == pytest.approx(10.0, abs=1e-10)


def test_registered_mesh_keeps_triangle_connectivity():
    mesh = _mesh()
    asset = ReferenceSurfaceAsset(_provenance(mesh), mesh, identity_registration())
    registered = asset.registered_mesh
    assert registered.triangles == mesh.triangles
    assert registered.vertex_count == mesh.vertex_count
    assert registered.triangle_count == mesh.triangle_count


def test_registration_manifest_records_units_axes_hash_and_transform():
    mesh = _mesh()
    asset = ReferenceSurfaceAsset(_provenance(mesh), mesh, identity_registration())
    manifest = asset.registration_manifest()

    assert manifest["asset_id"] == "TEST-HEADFORM-001"
    assert manifest["source_sha256"] == mesh.normalized_sha256()
    assert manifest["source_scale_to_mm"] == 1.0
    assert manifest["source_handedness"] == "right"
    assert manifest["registration"]["translation_mm"] == [0.0, 0.0, 0.0]
    assert manifest["mesh"]["vertex_count"] == 4


def test_left_handed_sources_are_rejected_instead_of_silently_reflected():
    mesh = _mesh()
    with pytest.raises(ReferenceSurfaceError, match="Left-handed sources"):
        ReferenceSurfaceAsset(_provenance(mesh, handedness="left"), mesh, identity_registration())


def test_unknown_units_are_rejected():
    mesh = _mesh()
    with pytest.raises(ReferenceSurfaceError, match="Unsupported source_units"):
        _provenance(mesh, units="furlong")


def test_invalid_source_digest_format_is_rejected():
    mesh = _mesh()
    with pytest.raises(ReferenceSurfaceError, match="64-character"):
        SurfaceProvenance(
            asset_id="TEST",
            source_kind="SYNTHETIC_TEST_FIXTURE",
            source_label="test",
            source_revision="r1",
            source_units="mm",
            handedness="right",
            x_positive="x",
            y_positive="y",
            z_positive="z",
            source_sha256="not-a-hash",
            evidence_status="TEST",
        )


def test_degenerate_triangles_are_rejected():
    with pytest.raises(ReferenceSurfaceError, match="degenerate"):
        TriangleMesh(
            vertices=(Point3(0.0, 0.0, 0.0), Point3(1.0, 0.0, 0.0), Point3(2.0, 0.0, 0.0)),
            triangles=((0, 1, 2),),
        )


def test_out_of_range_triangle_indices_are_rejected():
    with pytest.raises(ReferenceSurfaceError, match="outside the mesh"):
        TriangleMesh(
            vertices=(Point3(0.0, 0.0, 0.0), Point3(1.0, 0.0, 0.0), Point3(0.0, 1.0, 0.0)),
            triangles=((0, 1, 3),),
        )


def test_mesh_payload_rejects_unknown_fields_instead_of_ignoring_them():
    with pytest.raises(ReferenceSurfaceError, match="exactly"):
        mesh_from_payload(
            {
                "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                "triangles": [[0, 1, 2]],
                "mystery_scale": 1000,
            }
        )


def test_registration_error_metrics_must_be_ordered():
    with pytest.raises(ReferenceSurfaceError, match="RMS error"):
        SurfaceRegistration(
            source_to_global=RigidTransform.identity(),
            method="TEST",
            registration_revision="r1",
            rms_error_mm=2.0,
            max_error_mm=1.0,
        )
