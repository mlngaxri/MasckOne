from __future__ import annotations

import math

from .coverage import FacialCoverageMesh
from .facial_surface import FacialSurface
from .interface_boundaries import InterfaceBoundaryTopology, InterfaceBoundaryError
from .interface_topology import CompliantInterfaceTopology


_GEOMETRY_ABS_TOL_MM = 1e-9
_AREA_ABS_TOL_MM2 = 1e-9


def _triangle_geometry(surface: FacialSurface, triangle_index: int) -> tuple[tuple[int, int, int], tuple[float, float, float], float]:
    try:
        vertex_indices = surface.mesh.triangles[triangle_index]
    except IndexError as exc:
        raise InterfaceBoundaryError(
            f"Coverage triangle {triangle_index} does not exist in the current registered surface mesh"
        ) from exc

    p0, p1, p2 = (surface.mesh.vertices[index] for index in vertex_indices)
    centroid = (
        (p0.x + p1.x + p2.x) / 3.0,
        (p0.y + p1.y + p2.y) / 3.0,
        (p0.z + p1.z + p2.z) / 3.0,
    )
    ux, uy, uz = p0.vector_to(p1).x, p0.vector_to(p1).y, p0.vector_to(p1).z
    vx, vy, vz = p0.vector_to(p2).x, p0.vector_to(p2).y, p0.vector_to(p2).z
    cx = uy * vz - uz * vy
    cy = uz * vx - ux * vz
    cz = ux * vy - uy * vx
    area = 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
    return tuple(vertex_indices), centroid, area


def validate_boundary_source_chain(
    surface: FacialSurface,
    coverage: FacialCoverageMesh,
    interface: CompliantInterfaceTopology,
    topology: InterfaceBoundaryTopology,
) -> dict[str, object]:
    """Verify that Iteration-12 topology is bound to the exact registered mesh revision.

    `FacialSurfaceDescriptor.source_sha256` intentionally identifies the source asset.
    That alone is insufficient to distinguish two rigid registrations of the same asset.
    This gate therefore verifies every coverage triangle against the current registered
    mesh geometry and records the registered mesh hash separately from the source asset
    hash. It does not assign any physical-validation status.
    """

    registered_mesh_sha256 = surface.mesh.normalized_sha256()
    if topology.source_surface_id != surface.descriptor.surface_id:
        raise InterfaceBoundaryError("Boundary topology and facial surface identities differ")
    if topology.source_surface_sha256 != surface.descriptor.source_sha256:
        raise InterfaceBoundaryError("Boundary topology and facial source-asset hashes differ")
    if topology.source_coverage_sha256 != coverage.segmentation_sha256:
        raise InterfaceBoundaryError("Boundary topology and coverage revisions differ")
    if topology.source_interface_sha256 != interface.topology_sha256:
        raise InterfaceBoundaryError("Boundary topology and compliant-interface revisions differ")
    if coverage.source_surface_id != surface.descriptor.surface_id:
        raise InterfaceBoundaryError("Coverage and facial surface identities differ")
    if coverage.source_surface_sha256 != surface.descriptor.source_sha256:
        raise InterfaceBoundaryError("Coverage and facial source-asset hashes differ")
    if len(coverage.triangles) != surface.mesh.triangle_count:
        raise InterfaceBoundaryError("Coverage triangle count does not match the current registered surface mesh")

    for triangle in coverage.triangles:
        vertex_indices, centroid, area = _triangle_geometry(surface, triangle.triangle_index)
        if tuple(triangle.vertex_indices) != vertex_indices:
            raise InterfaceBoundaryError(
                f"Coverage triangle {triangle.triangle_index} vertex identity is stale for the current registered mesh"
            )
        actual_centroid = (triangle.centroid.x, triangle.centroid.y, triangle.centroid.z)
        if any(abs(actual - expected) > _GEOMETRY_ABS_TOL_MM for actual, expected in zip(actual_centroid, centroid)):
            raise InterfaceBoundaryError(
                f"Coverage triangle {triangle.triangle_index} centroid is stale for the current registered mesh"
            )
        if abs(triangle.area_mm2 - area) > _AREA_ABS_TOL_MM2:
            raise InterfaceBoundaryError(
                f"Coverage triangle {triangle.triangle_index} area is stale for the current registered mesh"
            )

    return {
        "surface_id": surface.descriptor.surface_id,
        "source_asset_id": surface.descriptor.source_asset_id,
        "source_revision": surface.descriptor.source_revision,
        "source_asset_sha256": surface.descriptor.source_sha256,
        "registered_mesh_sha256": registered_mesh_sha256,
        "coverage_segmentation_sha256": coverage.segmentation_sha256,
        "compliant_interface_topology_sha256": interface.topology_sha256,
        "interface_boundary_topology_sha256": topology.topology_sha256,
        "geometry_match_tolerance_mm": _GEOMETRY_ABS_TOL_MM,
        "area_match_tolerance_mm2": _AREA_ABS_TOL_MM2,
        "evidence_status": "DIGITAL_SOURCE_CHAIN_INTEGRITY_ONLY_NOT_ANATOMICAL_OR_PHYSICAL_VALIDATION",
    }


def boundary_release_manifest(
    surface: FacialSurface,
    coverage: FacialCoverageMesh,
    interface: CompliantInterfaceTopology,
    topology: InterfaceBoundaryTopology,
) -> dict[str, object]:
    """Return the release manifest with exact source-chain and edge identities."""

    source_chain = validate_boundary_source_chain(surface, coverage, interface, topology)
    manifest = topology.manifest()
    manifest["source_chain"] = source_chain
    manifest["edges"] = [
        {
            "edge_index": edge.edge_index,
            "boundary_id": edge.boundary_id,
            "vertex_indices": list(edge.vertex_indices),
            "incident_triangle_indices": list(edge.incident_triangle_indices),
            "contact_triangle_index": edge.contact_triangle_index,
            "protected_triangle_index": edge.protected_triangle_index,
            "length_mm": edge.length_mm,
        }
        for edge in topology.edges
    ]
    return manifest
