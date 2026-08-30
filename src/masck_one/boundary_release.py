from __future__ import annotations

import math

from .authority import Authority
from .coverage import FacialCoverageMesh
from .facial_surface import FacialSurface
from .interface_boundaries import (
    InterfaceBoundaryError,
    InterfaceBoundaryTopology,
    build_interface_boundary_topology,
)
from .interface_topology import CompliantInterfaceTopology


_GEOMETRY_MATCH_TOLERANCE_MM = 1e-9


def validate_registered_mesh_binding(surface: FacialSurface, coverage: FacialCoverageMesh) -> None:
    """Reject coverage produced from a different registration of the same source asset.

    The descriptor source hash identifies the source artifact, not the transformed
    registered mesh. Triangle centroids therefore provide an explicit geometry binding
    between the coverage revision and the current registered mesh. This tolerance is a
    software identity check only and is not a manufacturing or physical tolerance.
    """

    if coverage.source_surface_id != surface.descriptor.surface_id:
        raise InterfaceBoundaryError("Coverage and facial surface identities differ")
    if coverage.source_surface_sha256 != surface.descriptor.source_sha256:
        raise InterfaceBoundaryError("Coverage and facial source-asset hashes differ")
    if len(coverage.triangles) != surface.mesh.triangle_count:
        raise InterfaceBoundaryError("Coverage triangle count does not match current registered mesh")

    for coverage_triangle in coverage.triangles:
        triangle_index = coverage_triangle.triangle_index
        try:
            vertex_indices = tuple(surface.mesh.triangles[triangle_index])
        except IndexError as exc:
            raise InterfaceBoundaryError(
                f"Coverage triangle {triangle_index} is absent from the current registered mesh"
            ) from exc
        if tuple(coverage_triangle.vertex_indices) != vertex_indices:
            raise InterfaceBoundaryError(
                f"Coverage triangle {triangle_index} vertex identity is stale for the current registered mesh"
            )
        points = [surface.mesh.vertices[index] for index in vertex_indices]
        centroid = (
            sum(point.x for point in points) / 3.0,
            sum(point.y for point in points) / 3.0,
            sum(point.z for point in points) / 3.0,
        )
        observed = (
            coverage_triangle.centroid.x,
            coverage_triangle.centroid.y,
            coverage_triangle.centroid.z,
        )
        if any(
            not math.isclose(actual, expected, rel_tol=0.0, abs_tol=_GEOMETRY_MATCH_TOLERANCE_MM)
            for actual, expected in zip(observed, centroid)
        ):
            raise InterfaceBoundaryError(
                f"Coverage triangle {triangle_index} centroid is stale for the current registered mesh"
            )


def build_verified_interface_boundary_topology(
    authority: Authority,
    surface: FacialSurface,
    coverage: FacialCoverageMesh,
    interface: CompliantInterfaceTopology,
) -> InterfaceBoundaryTopology:
    validate_registered_mesh_binding(surface, coverage)
    topology = build_interface_boundary_topology(authority, surface, coverage, interface)
    if topology.source_registered_mesh_sha256 != surface.mesh.normalized_sha256():
        raise InterfaceBoundaryError("Boundary topology registered-mesh hash does not match current surface")
    if topology.source_surface_revision != surface.descriptor.source_revision:
        raise InterfaceBoundaryError("Boundary topology registration revision does not match current surface")
    return topology


def boundary_release_manifest(
    authority: Authority,
    surface: FacialSurface,
    coverage: FacialCoverageMesh,
    interface: CompliantInterfaceTopology,
) -> dict[str, object]:
    topology = build_verified_interface_boundary_topology(authority, surface, coverage, interface)
    manifest = topology.manifest()
    manifest["source_chain_evidence_status"] = (
        "DIGITAL_REGISTERED_MESH_BINDING_ONLY_NOT_ANATOMICAL_OR_PHYSICAL_VALIDATION"
    )
    manifest["geometry_identity_tolerance_mm"] = _GEOMETRY_MATCH_TOLERANCE_MM
    return manifest
