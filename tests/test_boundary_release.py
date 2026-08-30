import pytest

from masck_one.boundary_release import (
    boundary_release_manifest,
    build_verified_interface_boundary_topology,
    validate_registered_mesh_binding,
)
from masck_one.facial_surface import FacialSurface, FacialSurfaceDescriptor
from masck_one.interface_boundaries import InterfaceBoundaryError
from masck_one.model import build_model
from masck_one.reference_surfaces import TriangleMesh
from masck_one.spatial import Point3


def test_verified_boundary_release_records_registered_mesh_and_edge_identities():
    model = build_model()
    manifest = boundary_release_manifest(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    assert manifest["source_registered_mesh_sha256"] == model.facial_surface.mesh.normalized_sha256()
    assert manifest["source_surface_revision"] == model.facial_surface.descriptor.source_revision
    assert manifest["edges"]
    assert all("vertex_indices" in edge for edge in manifest["edges"])
    assert all("incident_triangle_indices" in edge for edge in manifest["edges"])
    assert all("contact_triangle_index" in edge for edge in manifest["edges"])
    assert all("physical_boundary_id" in edge for edge in manifest["edges"])


def test_registered_reference_can_have_distinct_source_asset_and_registered_mesh_hashes():
    model = build_model()
    original = model.facial_surface
    registered_descriptor = FacialSurfaceDescriptor(
        surface_id=original.descriptor.surface_id,
        kind="REGISTERED_EXTERNAL_REFERENCE",
        evidence_status="SYNTHETIC_REGISTERED_REFERENCE_TEST_ONLY",
        source_asset_id="TEST-ASSET-REGISTERED",
        source_revision="registration-r2",
        source_sha256="0" * 64,
        anatomical_validation_eligible=False,
    )
    registered_surface = FacialSurface(registered_descriptor, original.mesh)

    assert registered_surface.descriptor.source_sha256 != registered_surface.mesh.normalized_sha256()
    assert model.coverage_mesh.source_surface_sha256 == registered_surface.mesh.normalized_sha256()

    validate_registered_mesh_binding(registered_surface, model.coverage_mesh)


def test_same_source_asset_with_different_registered_geometry_is_rejected():
    model = build_model()
    original = model.facial_surface
    translated_vertices = tuple(Point3(v.x + 1.0, v.y, v.z) for v in original.mesh.vertices)
    translated = FacialSurface(
        original.descriptor,
        TriangleMesh(translated_vertices, original.mesh.triangles),
    )

    assert translated.descriptor.source_sha256 == original.descriptor.source_sha256
    assert translated.mesh.normalized_sha256() != original.mesh.normalized_sha256()

    with pytest.raises(InterfaceBoundaryError, match="registered-mesh hashes differ"):
        build_verified_interface_boundary_topology(
            model.authority,
            translated,
            model.coverage_mesh,
            model.compliant_interface_topology,
        )


def test_release_source_chain_remains_digital_evidence_only():
    model = build_model()
    manifest = boundary_release_manifest(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    assert manifest["source_chain_evidence_status"] == (
        "DIGITAL_REGISTERED_MESH_BINDING_ONLY_NOT_ANATOMICAL_OR_PHYSICAL_VALIDATION"
    )
    assert manifest["anatomical_validation_eligible"] is False
