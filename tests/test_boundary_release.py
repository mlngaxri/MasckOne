import pytest

from masck_one.boundary_release import boundary_release_manifest, validate_boundary_source_chain
from masck_one.facial_surface import FacialSurface
from masck_one.interface_boundaries import InterfaceBoundaryError
from masck_one.model import build_model
from masck_one.reference_surfaces import TriangleMesh
from masck_one.spatial import Point3


def test_release_manifest_serializes_each_boundary_edge_identity():
    model = build_model()
    manifest = boundary_release_manifest(
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
        model.interface_boundary_topology,
    )

    edges = manifest["edges"]
    assert len(edges) == len(model.interface_boundary_topology.edges)
    assert [edge["edge_index"] for edge in edges] == list(range(len(edges)))
    required = {
        "edge_index",
        "boundary_id",
        "vertex_indices",
        "incident_triangle_indices",
        "contact_triangle_index",
        "protected_triangle_index",
        "length_mm",
    }
    assert all(set(edge) == required for edge in edges)
    assert manifest["source_chain"]["registered_mesh_sha256"] == model.facial_surface.mesh.normalized_sha256()


def test_source_chain_rejects_same_descriptor_with_different_registered_mesh_geometry():
    model = build_model()
    surface = model.facial_surface
    translated_vertices = tuple(Point3(vertex.x + 1.0, vertex.y, vertex.z) for vertex in surface.mesh.vertices)
    translated_surface = FacialSurface(
        surface.descriptor,
        TriangleMesh(translated_vertices, surface.mesh.triangles),
    )

    assert translated_surface.descriptor.source_sha256 == surface.descriptor.source_sha256
    assert translated_surface.mesh.normalized_sha256() != surface.mesh.normalized_sha256()

    with pytest.raises(InterfaceBoundaryError, match="stale for the current registered mesh"):
        validate_boundary_source_chain(
            translated_surface,
            model.coverage_mesh,
            model.compliant_interface_topology,
            model.interface_boundary_topology,
        )


def test_source_chain_validation_does_not_promote_physical_evidence():
    model = build_model()
    source_chain = validate_boundary_source_chain(
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
        model.interface_boundary_topology,
    )

    assert source_chain["evidence_status"] == "DIGITAL_SOURCE_CHAIN_INTEGRITY_ONLY_NOT_ANATOMICAL_OR_PHYSICAL_VALIDATION"
    assert model.interface_boundary_topology.anatomical_validation_eligible is False
