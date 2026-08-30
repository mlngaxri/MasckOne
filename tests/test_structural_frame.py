from dataclasses import replace

import pytest

from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import (
    DATUM_IDS,
    RESERVATION_IDS,
    StructuralFrameError,
    build_structural_frame_topology,
)


def _build():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    return model, attachment, frame


def test_structural_frame_inherits_attachment_perimeter_exactly():
    _, attachment, frame = _build()
    assert frame.source_attachment_topology_sha256 == attachment.topology_sha256
    assert frame.source_registered_mesh_sha256 == attachment.source_registered_mesh_sha256
    assert frame.perimeter_reaction_path.source_attachment_edge_indices == tuple(
        item.source_boundary_edge_index for item in attachment.assignments
    )


def test_frame_datums_are_authority_derived_and_z_remains_unresolved():
    model, _, frame = _build()
    width, height = model.authority.pair("geometry", "functional_frame_xy_mm")
    datums = {datum.datum_id: datum for datum in frame.datums}
    assert tuple(datum.datum_id for datum in frame.datums) == DATUM_IDS
    assert (datums[DATUM_IDS[0]].x_mm, datums[DATUM_IDS[0]].y_mm) == (0.0, 0.0)
    assert datums[DATUM_IDS[1]].y_mm == height / 2.0
    assert datums[DATUM_IDS[2]].y_mm == -height / 2.0
    assert datums[DATUM_IDS[3]].x_mm == -width / 2.0
    assert datums[DATUM_IDS[4]].x_mm == width / 2.0
    assert all(datum.manifest()["z_mm"] is None for datum in frame.datums)


def test_frame_reserves_all_downstream_subsystem_interfaces_without_positions():
    model, _, frame = _build()
    assert tuple(item.reservation_id for item in frame.reservations) == RESERVATION_IDS
    assert frame.reservations[0].interface_count == int(model.authority.number("actuation", "count")) == 4
    assert all(item.placement_status for item in frame.reservations)
    assert all(item.envelope_status for item in frame.reservations)


def test_structural_requirements_are_carried_with_authority_statuses_only():
    model, _, frame = _build()
    assert frame.frame_deflection_p95_max_mm == float(model.authority.get("structure", "frame_deflection_p95_max_mm"))
    assert frame.frame_deflection_status == str(model.authority.get("structure", "frame_deflection_status"))
    assert frame.first_mode_preferred_min_hz == float(model.authority.get("structure", "frame_first_mode_preferred_min_hz"))
    assert frame.first_mode_status == str(model.authority.get("structure", "frame_first_mode_status"))
    assert "NOT_DEFLECTION_MODAL_LOAD_FATIGUE_FIT_OR_PHYSICAL_VALIDATION" in frame.evidence_status


def test_structural_cross_section_cannot_be_invented():
    _, _, frame = _build()
    with pytest.raises(StructuralFrameError, match="cannot invent structural-frame cross-section"):
        replace(frame, cross_section_dimensions_mm=(3.0, 4.0))


def test_structural_material_cannot_be_selected_without_evidence():
    _, _, frame = _build()
    with pytest.raises(StructuralFrameError, match="cannot select a frame material"):
        replace(frame, material_selection="UNSOURCED_TEST_POLYMER")


def test_duplicate_reaction_edges_are_rejected_by_load_path_contract():
    _, _, frame = _build()
    with pytest.raises(StructuralFrameError, match="cannot repeat"):
        replace(frame.perimeter_reaction_path, source_attachment_edge_indices=(0, 0))


def test_frame_topology_is_deterministic_and_not_physical_evidence():
    _, _, first = _build()
    _, _, second = _build()
    assert first.topology_sha256 == second.topology_sha256
    assert first.manifest() == second.manifest()
    assert first.physical_validation_eligible is False
