from __future__ import annotations

from dataclasses import replace
import json
import math

import cadquery as cq
import pytest

from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import build_structural_frame_topology
from masck_one import structural_frame_realization as realization_module
from masck_one.structural_frame_realization import (
    AXIAL_DEPTH_PROVENANCE,
    CAPTURE_SEMANTICS,
    CROSS_SECTION_INTENT,
    EVIDENCE_STATUS,
    FRAME_SHELL_JOIN_STATUS,
    GEOMETRY_ROLE,
    PACKAGE_CLEARANCE_SEED_MM,
    RETENTION_ROOT_STATUS,
    StructuralFrameRealizationError,
    WORLD_FRAME_ID,
    build_structural_frame_realization,
)


@pytest.fixture(scope="module")
def current_sources():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    realization = build_structural_frame_realization(
        model=model,
        structural_frame=frame,
    )
    return model, attachment, frame, realization


def test_current_main_reaction_loop_is_one_valid_source_bound_brep(current_sources):
    model, attachment, frame, realization = current_sources
    shape = realization.solid.val()

    assert shape.isValid()
    assert len(shape.Solids()) == 1
    assert realization.coordinate_frame_id == WORLD_FRAME_ID
    assert realization.geometry_role == GEOMETRY_ROLE
    assert realization.capture_semantics == CAPTURE_SEMANTICS
    assert realization.cross_section_intent == CROSS_SECTION_INTENT
    assert realization.axial_depth_provenance == AXIAL_DEPTH_PROVENANCE
    assert realization.material_selection is None
    assert realization.physical_validation_eligible is False
    assert realization.evidence_status == EVIDENCE_STATUS

    assert realization.source_structural_frame_sha256 == frame.topology_sha256
    assert realization.source_attachment_topology_sha256 == attachment.topology_sha256
    assert (
        realization.source_capture_edge_indices
        == frame.perimeter_reaction_path.source_attachment_edge_indices
    )
    assert realization.source_capture_vertex_count == len(attachment.assignments)
    assert realization.source_capture_path_length_mm == pytest.approx(
        attachment.total_path_length_mm,
        abs=1e-7,
    )

    outer_w, outer_h = model.authority.pair("geometry", "outer_xy_envelope_mm")
    bbox = shape.BoundingBox()
    assert bbox.xmin == pytest.approx(-outer_w / 2.0, abs=2e-6)
    assert bbox.xmax == pytest.approx(outer_w / 2.0, abs=2e-6)
    assert bbox.ymin == pytest.approx(-outer_h / 2.0, abs=2e-6)
    assert bbox.ymax == pytest.approx(outer_h / 2.0, abs=2e-6)
    assert bbox.zmin == pytest.approx(realization.z_range_mm[0], abs=2e-6)
    assert bbox.zmax == pytest.approx(realization.z_range_mm[1], abs=2e-6)

    horizontal_faces = [
        face
        for face in shape.Faces()
        if face.geomType() == "PLANE"
        and abs(abs(float(face.normalAt().z)) - 1.0) <= 1e-9
    ]
    assert max(len(face.Wires()) for face in horizontal_faces) >= 2


def test_reaction_loop_is_noncontacting_with_current_material_packages_and_hard_protected_envelopes(
    current_sources,
):
    _model, _attachment, _frame, realization = current_sources

    by_id = {record.target_id: record for record in realization.component_clearances}
    assert "rigid_shell" in by_id
    assert "waste_cartridge_envelope" in by_id
    assert by_id["rigid_shell"].target_role == "CURRENT_MAIN_PHYSICAL_MATERIAL"
    assert by_id["waste_cartridge_envelope"].target_role == "PACKAGE_REFERENCE"
    assert by_id["waste_cartridge_envelope"].minimum_distance_mm >= PACKAGE_CLEARANCE_SEED_MM - 1e-6

    for record in realization.component_clearances:
        assert record.intersection_volume_mm3 == 0.0
        assert record.minimum_distance_mm > 0.0

    assert len(realization.protected_clearances) == 5
    for record in realization.protected_clearances:
        assert record.intersection_volume_mm3 == 0.0
        assert record.minimum_distance_mm > 0.0


def test_unresolved_join_actuator_retention_and_service_semantics_stay_fail_closed(
    current_sources,
):
    _model, _attachment, _frame, realization = current_sources
    manifest = realization.manifest()

    assert realization.frame_shell_join_status == FRAME_SHELL_JOIN_STATUS
    assert "UNRESOLVED" in realization.actuator_reaction_status
    assert realization.retention_root_status == RETENTION_ROOT_STATUS
    assert "UNRESOLVED" in realization.service_tool_access_status
    assert "STANDALONE" in realization.assembly_status
    assert manifest["physical_validation_eligible"] is False
    assert manifest["material_selection"] is None


def test_realization_manifest_and_geometry_identity_are_deterministic(current_sources):
    model, _attachment, frame, first = current_sources
    second = build_structural_frame_realization(model=model, structural_frame=frame)

    assert first.geometry_sha256 == second.geometry_sha256
    assert first.realization_sha256 == second.realization_sha256
    assert json.dumps(
        first.manifest(),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ) == json.dumps(
        second.manifest(),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def test_step_round_trip_preserves_single_solid_bounds_and_volume(current_sources, tmp_path):
    _model, _attachment, _frame, realization = current_sources
    target = tmp_path / "structural_frame_reaction_loop_v1.step"
    cq.exporters.export(realization.solid, str(target))
    imported = cq.importers.importStep(str(target))
    assert target.is_file() and target.stat().st_size > 0
    assert imported.val().isValid()
    assert len(imported.val().Solids()) == 1

    source_bbox = realization.solid.val().BoundingBox()
    imported_bbox = imported.val().BoundingBox()
    for actual, expected in (
        (imported_bbox.xmin, source_bbox.xmin),
        (imported_bbox.ymin, source_bbox.ymin),
        (imported_bbox.zmin, source_bbox.zmin),
        (imported_bbox.xmax, source_bbox.xmax),
        (imported_bbox.ymax, source_bbox.ymax),
        (imported_bbox.zmax, source_bbox.zmax),
    ):
        assert actual == pytest.approx(expected, abs=2e-5)
    assert imported.val().Volume() == pytest.approx(
        realization.solid.val().Volume(),
        rel=0.0,
        abs=1e-4,
    )


def test_stale_source_blob_binding_fails_before_geometry_is_trusted(
    current_sources,
    monkeypatch,
):
    model, _attachment, frame, _realization = current_sources
    bindings = list(realization_module.SOURCE_GIT_BLOB_IDENTITIES)
    path, _sha = bindings[-1]
    bindings[-1] = (path, "0" * 40)
    monkeypatch.setattr(
        realization_module,
        "SOURCE_GIT_BLOB_IDENTITIES",
        tuple(bindings),
    )
    with pytest.raises(StructuralFrameRealizationError, match="source moved"):
        build_structural_frame_realization(model=model, structural_frame=frame)


def test_stale_or_substituted_structural_topology_is_rejected(current_sources):
    model, _attachment, frame, _realization = current_sources
    stale = replace(
        frame,
        functional_frame_xy_mm=(
            frame.functional_frame_xy_mm[0] - 1.0,
            frame.functional_frame_xy_mm[1],
        ),
    )
    with pytest.raises(StructuralFrameRealizationError, match="topology is stale"):
        build_structural_frame_realization(model=model, structural_frame=stale)


def test_nonfinite_and_physical_evidence_drift_are_rejected(current_sources):
    _model, _attachment, _frame, realization = current_sources
    with pytest.raises(StructuralFrameRealizationError, match="axial depth"):
        replace(realization, axial_depth_mm=math.nan)
    with pytest.raises(StructuralFrameRealizationError, match="physical-validation"):
        replace(realization, physical_validation_eligible=True)


def test_illegal_full_plate_reference_mixing_is_rejected(
    current_sources,
    monkeypatch,
):
    model, _attachment, frame, _realization = current_sources

    def full_plate(**kwargs):
        outer_w, outer_h = kwargs["outer_xy_envelope_mm"]
        return (
            cq.Workplane("XY")
            .workplane(offset=kwargs["z_min_mm"])
            .ellipse(outer_w / 2.0, outer_h / 2.0)
            .extrude(kwargs["axial_depth_mm"])
        )

    monkeypatch.setattr(realization_module, "_build_member_solid", full_plate)
    with pytest.raises(
        StructuralFrameRealizationError,
        match="intersection|touches|capture opening",
    ):
        build_structural_frame_realization(model=model, structural_frame=frame)
