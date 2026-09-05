from pathlib import Path

import cadquery as cq
import pytest

from masck_one.authority import load_authority
from masck_one.rear_service_skin import (
    CELL3_CARRIER_INNER_X_ABS_MM,
    CELL3_CENTRAL_REAR_KEEP_OUT_XYZ_MM,
    CELL3_CROWN_CORRIDOR_Y_MIN_MM,
    CELL3_OCCIPITAL_INNER_X_ABS_MM,
    PACKAGE_REFLOW_REQUIRED,
    REAR_COVER_REMOVAL_TRAVEL_MM,
    REAR_SKIN_FRONT_XY_MM,
    REAR_SKIN_REAR_XY_MM,
    SCHEMA,
    SOURCE_CELL3_RETENTION_HEAD_SHA,
    build_rear_service_skin,
)


def _box_from_bounds(bounds: tuple[float, float, float, float, float, float]) -> cq.Shape:
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    return (
        cq.Workplane("XY")
        .box(xmax - xmin, ymax - ymin, zmax - zmin, centered=(True, True, True))
        .translate(
            (
                (xmin + xmax) / 2.0,
                (ymin + ymax) / 2.0,
                (zmin + zmax) / 2.0,
            )
        )
        .val()
    )


def test_rear_service_skin_is_shallow_tapered_and_disjoint_from_current_package_keepout():
    authority = load_authority()
    skin = build_rear_service_skin(authority)
    shape = skin.cover.val()
    bb = shape.BoundingBox()

    assert shape.isValid()
    assert len(shape.Solids()) == 1
    assert float(shape.Volume()) > 0.0
    assert bb.xlen == pytest.approx(REAR_SKIN_FRONT_XY_MM[0], abs=1e-5)
    assert bb.ylen == pytest.approx(REAR_SKIN_FRONT_XY_MM[1], abs=1e-5)
    assert bb.zlen == pytest.approx(
        authority.number("geometry", "shell_nominal_wall_mm"),
        abs=1e-5,
    )
    assert REAR_SKIN_REAR_XY_MM[0] < REAR_SKIN_FRONT_XY_MM[0]
    assert REAR_SKIN_REAR_XY_MM[1] < REAR_SKIN_FRONT_XY_MM[1]
    assert float(shape.intersect(skin.package_keepout_reference.val()).Volume()) == pytest.approx(0.0, abs=1e-8)
    assert skin.seam_gap_mm == pytest.approx(
        authority.number("geometry", "visible_seam", "gap_mm")
    )


def test_cover_only_service_reference_clears_current_cell3_rear_interfaces():
    skin = build_rear_service_skin()
    service = skin.cover_removal_envelope_reference.val()

    obstacles = (
        _box_from_bounds((-75.5, -44.0, -20.0, 15.0, -52.5, -28.0)),
        _box_from_bounds((44.0, 75.5, -20.0, 15.0, -52.5, -28.0)),
        _box_from_bounds((-87.5, -56.0, 4.0, 64.0, -50.0, -19.0)),
        _box_from_bounds((56.0, 87.5, 4.0, 64.0, -50.0, -19.0)),
        _box_from_bounds((-68.0, 68.0, 56.0, 90.0, -54.0, -40.0)),
    )
    for obstacle in obstacles:
        assert float(service.intersect(obstacle).Volume()) == pytest.approx(0.0, abs=1e-8)

    manifest = skin.manifest()
    clearance = manifest["retention_clearance"]
    assert clearance["service_lateral_gap_to_occipital_inner_x_mm"] == pytest.approx(
        CELL3_OCCIPITAL_INNER_X_ABS_MM - REAR_SKIN_FRONT_XY_MM[0] / 2.0
    )
    assert clearance["service_lateral_gap_to_carrier_inner_x_mm"] == pytest.approx(
        CELL3_CARRIER_INNER_X_ABS_MM - REAR_SKIN_FRONT_XY_MM[0] / 2.0
    )
    assert clearance["service_superior_gap_to_crown_corridor_mm"] == pytest.approx(
        CELL3_CROWN_CORRIDOR_Y_MIN_MM - REAR_SKIN_FRONT_XY_MM[1] / 2.0
    )
    assert manifest["service_reference"]["travel_mm"] == REAR_COVER_REMOVAL_TRAVEL_MM


def test_manifest_forces_package_reflow_instead_of_claiming_current_keepout_is_hidden():
    skin = build_rear_service_skin()
    manifest = skin.manifest()
    assert manifest["schema"] == SCHEMA
    assert manifest["source_cell3_retention_head_sha"] == SOURCE_CELL3_RETENTION_HEAD_SHA
    assert manifest["current_cell3_package_interface"]["keepout_xyz_mm"] == list(
        CELL3_CENTRAL_REAR_KEEP_OUT_XYZ_MM
    )
    assert manifest["current_cell3_package_interface"]["fully_hidden_by_current_skin_projection"] is False
    assert manifest["current_cell3_package_interface"]["package_reflow_required"] is True
    assert manifest["current_cell3_package_interface"]["reflow_requirement"] == PACKAGE_REFLOW_REQUIRED
    assert manifest["package_screening"]["battery_projection_fits_visible_target"] is True
    assert manifest["package_screening"]["stale_manual_b_pcb_projection_fits_visible_target"] is True
    assert manifest["package_screening"]["simultaneous_internal_nesting_validated"] is False
    assert manifest["service_reference"]["battery_extraction_geometry_status"] == "UNRESOLVED"
    assert manifest["service_reference"]["dry_bay_attachment_geometry_status"] == "UNRESOLVED"


def test_rear_service_skin_step_round_trip_preserves_single_solid(tmp_path: Path):
    skin = build_rear_service_skin()
    path = tmp_path / "rear_service_skin.step"
    cq.exporters.export(skin.cover, str(path))
    imported = cq.importers.importStep(str(path))
    assert imported.solids().size() == 1
    assert imported.val().isValid()
    assert imported.val().BoundingBox().xlen == pytest.approx(
        skin.cover.val().BoundingBox().xlen,
        abs=1e-4,
    )
    assert float(imported.val().Volume()) == pytest.approx(
        float(skin.cover.val().Volume()),
        rel=1e-6,
    )


def test_cell2_visible_assembly_integrates_rear_skin_without_mutating_product_component_set():
    from masck_one.integrated_product import build_cell2_exterior_assembly

    assembly = build_cell2_exterior_assembly()
    compound = assembly.visible_compound
    assert compound.isValid()
    assert len(compound.Solids()) == 2
    assert assembly.model.shell.name == "rigid_shell"
    assert all(component.name != "rear_service_skin" for component in assembly.model.components)
