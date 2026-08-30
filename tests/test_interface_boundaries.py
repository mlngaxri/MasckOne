from __future__ import annotations

from collections import defaultdict

import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.coverage import build_facial_coverage_mesh
from masck_one.facial_surface import build_planar_development_surface
from masck_one.interface_boundaries import (
    EDGE_CONTACT_PARAMETER,
    EDGE_NASAL_MAIN,
    EDGE_NASAL_ROLE,
    EDGE_OUTER_PERIMETER,
    EDGE_PROTECTED_APERTURE,
    EyeInnerEdgeRollAuthority,
    InterfaceBoundaryError,
    PerimeterComplianceIntent,
    VisibleSeamAuthority,
    build_interface_boundary_topology,
)
from masck_one.interface_topology import build_compliant_interface_topology
from masck_one.nasal_subsystem import build_nasal_subsystem_topology
from masck_one.protected_volumes import build_protected_volumes
from masck_one.spatial import CanonicalDatums


def _build():
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)
    reference = build_facial_reference(authority, datums)
    surface = build_planar_development_surface(authority)
    protected = build_protected_volumes(authority, reference, surface)
    coverage = build_facial_coverage_mesh(authority, reference, surface, protected)
    interface = build_compliant_interface_topology(authority, coverage)
    nasal = build_nasal_subsystem_topology(authority, coverage, interface, protected)
    boundaries = build_interface_boundary_topology(authority, surface, coverage, interface, nasal)
    return authority, surface, coverage, interface, nasal, boundaries


def test_boundary_topology_preserves_exact_upstream_source_chain():
    _, surface, coverage, interface, nasal, boundaries = _build()

    assert boundaries.source_surface_id == surface.descriptor.surface_id
    assert boundaries.source_surface_sha256 == surface.descriptor.source_sha256
    assert boundaries.source_coverage_sha256 == coverage.segmentation_sha256
    assert boundaries.source_interface_sha256 == interface.topology_sha256
    assert boundaries.source_nasal_sha256 == nasal.topology_sha256
    assert len(boundaries.topology_sha256) == 64


def test_every_mesh_edge_is_manifold_and_every_outer_edge_is_perimeter_seal_intent():
    _, _, coverage, _, _, boundaries = _build()
    incidence: dict[tuple[int, int], int] = defaultdict(int)
    for triangle in coverage.triangles:
        a, b, c = triangle.vertex_indices
        for u, v in ((a, b), (b, c), (c, a)):
            incidence[tuple(sorted((u, v)))] += 1

    assert all(count in {1, 2} for count in incidence.values())
    assert boundaries.mesh_unique_edge_count == len(incidence)
    assert boundaries.mesh_outer_edge_count == sum(count == 1 for count in incidence.values())
    assert len(boundaries.outer_perimeter_edges) == boundaries.mesh_outer_edge_count
    assert all(edge.kind == EDGE_OUTER_PERIMETER for edge in boundaries.outer_perimeter_edges)
    assert all(edge.seal_intent for edge in boundaries.outer_perimeter_edges)


def test_perimeter_intent_does_not_invent_seal_dimensions_compression_or_preload():
    _, _, _, _, _, boundaries = _build()
    intent = boundaries.perimeter_intent

    assert intent.seal_intent is True
    assert intent.seal_width_mm is None
    assert intent.seal_thickness_mm is None
    assert intent.compression_mm is None
    assert intent.compression_ratio is None
    assert intent.preload_N is None
    assert "UNRESOLVED" in intent.geometry_status


def test_all_five_protected_regions_have_material_free_transition_edges():
    _, _, coverage, _, _, boundaries = _build()
    protected_ids = {
        triangle.protected_zone_id
        for triangle in coverage.protected_triangles
        if triangle.protected_zone_id is not None
    }
    transition_ids = {edge.protected_zone_id for edge in boundaries.protected_aperture_edges}

    assert transition_ids == protected_ids
    assert len(transition_ids) == 5
    assert all(edge.kind == EDGE_PROTECTED_APERTURE for edge in boundaries.protected_aperture_edges)
    assert all(edge.material_bridge_allowed is False for edge in boundaries.protected_aperture_edges)
    assert all(edge.seal_intent is False for edge in boundaries.protected_aperture_edges)


def test_nostril_protected_transitions_can_never_be_material_bridged():
    _, _, _, _, _, boundaries = _build()
    nostril_edges = [
        edge
        for edge in boundaries.protected_aperture_edges
        if edge.protected_zone_id in {
            "MASCK_ONE-PROTECTED-NOSTRIL-LEFT",
            "MASCK_ONE-PROTECTED-NOSTRIL-RIGHT",
        }
    ]

    assert nostril_edges
    assert {edge.protected_zone_id for edge in nostril_edges} == {
        "MASCK_ONE-PROTECTED-NOSTRIL-LEFT",
        "MASCK_ONE-PROTECTED-NOSTRIL-RIGHT",
    }
    assert all(not edge.material_bridge_allowed for edge in nostril_edges)


def test_contact_and_nasal_transition_classes_are_present_without_becoming_physical_seams():
    _, _, _, _, _, boundaries = _build()
    counts = {kind: len(edges) for kind, edges in boundaries.edges_by_kind.items()}

    assert counts[EDGE_CONTACT_PARAMETER] > 0
    assert counts[EDGE_NASAL_MAIN] > 0
    assert counts[EDGE_NASAL_ROLE] > 0
    for kind in (EDGE_CONTACT_PARAMETER, EDGE_NASAL_MAIN, EDGE_NASAL_ROLE):
        assert all(edge.material_bridge_allowed for edge in boundaries.edges_by_kind[kind])
        assert all(not edge.seal_intent for edge in boundaries.edges_by_kind[kind])
        assert all("NOT_PHYSICAL_SEAM" in edge.evidence_status for edge in boundaries.edges_by_kind[kind])


def test_visible_seam_authority_is_preserved_but_not_applied_to_perimeter_seal_geometry():
    authority, _, _, _, _, boundaries = _build()
    seam = boundaries.visible_seam_authority

    assert seam.gap_mm == authority.number("geometry", "visible_seam", "gap_mm") == 0.40
    assert seam.tolerance_mm == authority.number("geometry", "visible_seam", "tolerance_mm") == 0.15
    assert seam.flush_mismatch_max_mm == authority.number("geometry", "visible_seam", "flush_mismatch_max_mm") == 0.15
    assert seam.allowed_gap_range_mm == pytest.approx((0.25, 0.55))
    assert "PLACEMENT_UNRESOLVED" in seam.application_status
    assert boundaries.perimeter_intent.seal_width_mm is None


def test_eye_inner_edge_roll_is_preserved_without_mapping_protected_envelope_edge_to_visual_aperture():
    authority, _, _, _, _, boundaries = _build()
    roll = boundaries.eye_inner_edge_roll_authority

    assert roll.radius_mm == authority.number("geometry", "eye", "inner_edge_roll_radius_mm") == 3.0
    assert "NOT_MAPPED_TO_CONSERVATIVE_PROTECTED_ENVELOPE_TRANSITION" in roll.application_status


def test_boundary_topology_is_deterministic():
    *_, first = _build()
    *_, second = _build()

    assert first.topology_sha256 == second.topology_sha256
    assert first.manifest() == second.manifest()


def test_boundary_edge_ids_are_unique_and_stably_sorted():
    *_, boundaries = _build()
    keys = [edge.vertex_indices for edge in boundaries.edges]
    ids = [edge.edge_id for edge in boundaries.edges]

    assert keys == sorted(keys)
    assert len(keys) == len(set(keys))
    assert len(ids) == len(set(ids))


def test_iteration_12_cannot_invent_numeric_perimeter_seal_parameters():
    with pytest.raises(InterfaceBoundaryError):
        PerimeterComplianceIntent(seal_width_mm=3.0)
    with pytest.raises(InterfaceBoundaryError):
        PerimeterComplianceIntent(compression_ratio=0.20)
    with pytest.raises(InterfaceBoundaryError):
        PerimeterComplianceIntent(preload_N=8.0)


def test_invalid_visible_seam_and_eye_roll_metadata_are_rejected():
    with pytest.raises(InterfaceBoundaryError):
        VisibleSeamAuthority(-0.1, 0.15, 0.15, "DESIGN_BASELINE")
    with pytest.raises(InterfaceBoundaryError):
        EyeInnerEdgeRollAuthority(0.0, "DESIGN_BASELINE")


def test_development_boundary_lengths_are_not_promoted_to_anatomical_validation():
    *_, boundaries = _build()

    assert boundaries.anatomical_validation_eligible is False
    assert "NOT_ANATOMICAL" in boundaries.evidence_status
    assert all(length > 0.0 for length in boundaries.kind_length_mm.values())
