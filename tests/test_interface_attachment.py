from dataclasses import replace

import pytest

from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.interface_attachment import (
    LAYER_IDS,
    InterfaceAttachmentError,
    build_interface_attachment_architecture,
)
from masck_one.interface_boundaries import (
    BOUNDARY_OUTER_PERIMETER,
    PHYSICAL_BOUNDARY_OUTER_PERIMETER,
)
from masck_one.model import build_model


def _build():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    return model, boundaries, attachment


def test_attachment_maps_every_outer_perimeter_edge_exactly_once():
    _, boundaries, attachment = _build()
    source = tuple(
        sorted(
            boundaries.physical_edges_by_boundary[PHYSICAL_BOUNDARY_OUTER_PERIMETER],
            key=lambda edge: edge.edge_index,
        )
    )
    assert tuple(item.source_boundary_edge_index for item in attachment.assignments) == tuple(
        edge.edge_index for edge in source
    )
    assert tuple(item.vertex_indices for item in attachment.assignments) == tuple(
        edge.vertex_indices for edge in source
    )
    assert len({item.source_boundary_edge_index for item in attachment.assignments}) == len(source)
    assert attachment.total_path_length_mm == pytest.approx(sum(edge.length_mm for edge in source), abs=1e-12)


def test_attachment_uses_only_outer_perimeter_provenance():
    _, _, attachment = _build()
    assert all(item.source_boundary_id == BOUNDARY_OUTER_PERIMETER for item in attachment.assignments)
    assert all(
        item.physical_boundary_id == PHYSICAL_BOUNDARY_OUTER_PERIMETER
        for item in attachment.assignments
    )


def test_attachment_stack_roles_are_explicit_but_geometry_remains_unresolved():
    _, _, attachment = _build()
    assert tuple(layer.layer_id for layer in attachment.layers) == LAYER_IDS
    assert attachment.clamp_band_width_mm is None
    assert attachment.capture_depth_mm is None
    assert attachment.interface_preload_N is None
    assert attachment.fastener_count is None
    assert attachment.fastener_pitch_mm is None
    assert attachment.interface_compression_percent is None
    assert attachment.retention_member_material is None
    assert "DEFERRED_TO_ITERATION15" in attachment.structural_frame_topology_status


def test_structural_frame_reference_is_authority_backed_only():
    model, _, attachment = _build()
    assert attachment.structural_frame_reference_xy_mm == model.authority.pair(
        "geometry", "functional_frame_xy_mm"
    )
    assert attachment.structural_frame_reference_status == str(
        model.authority.get("geometry", "functional_frame_status")
    )


def test_unsourced_numeric_clamp_dimension_is_rejected():
    _, _, attachment = _build()
    with pytest.raises(InterfaceAttachmentError, match="cannot invent unresolved attachment"):
        replace(attachment, clamp_band_width_mm=2.0)


def test_unsourced_fastener_count_is_rejected():
    _, _, attachment = _build()
    with pytest.raises(InterfaceAttachmentError, match="cannot invent unresolved attachment"):
        replace(attachment, fastener_count=12)


def test_retention_material_selection_is_rejected_without_evidence():
    _, _, attachment = _build()
    with pytest.raises(InterfaceAttachmentError, match="cannot select a retention-member material"):
        replace(attachment, retention_member_material="UNSOURCED_TEST_MATERIAL")


def test_corrupted_source_without_outer_perimeter_is_rejected():
    model, boundaries, _ = _build()
    corrupted = replace(
        boundaries,
        edges=tuple(edge for edge in boundaries.edges if edge.boundary_id != BOUNDARY_OUTER_PERIMETER),
    )
    with pytest.raises(InterfaceAttachmentError, match="outer perimeter"):
        build_interface_attachment_architecture(model.authority, corrupted)


def test_attachment_architecture_is_deterministic_and_not_physical_evidence():
    _, _, first = _build()
    _, _, second = _build()
    assert first.topology_sha256 == second.topology_sha256
    assert first.manifest() == second.manifest()
    assert first.physical_validation_eligible is False
    assert "NOT_SEAL_RETENTION_LOAD_DURABILITY_ASSEMBLY_OR_PHYSICAL_VALIDATION" in first.evidence_status
