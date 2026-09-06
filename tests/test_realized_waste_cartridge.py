from dataclasses import replace

import cadquery as cq
import pytest

import masck_one.realized_waste_cartridge as cartridge_module
from masck_one.export import export_release
from masck_one.realized_waste_cartridge import (
    AUTHORED_AGAINST_MAIN_SHA,
    BODY_INLET_WALL_WORLD_MM,
    CAPACITY_STATUS,
    EVIDENCE_STATUS,
    EXPECTED_INSTALLED_GEOMETRIC_FREE_CAPACITY_ML,
    HYGIENE_CLASSIFICATION,
    INLET_HANDOFF_GAP_MM,
    KEY_STATUS,
    PACKAGE_BOUNDS_WORLD_MM,
    PACKAGE_ENVELOPE_XYZ_MM,
    PROTECTED_FACE_STATUS,
    RETAINED_CAPACITY_REQUIREMENT_ML,
    ROUTE_HANDOFF_WORLD_MM,
    SERVICE_STATUS,
    VENT_STATUS,
    RealizedWasteCartridgeError,
    build_realized_waste_cartridge,
)
from masck_one.waste_acquisition import PHASE_MIXED_WASTE
from masck_one.waste_pump_architecture import (
    INTERFACE_CARTRIDGE_INLET_I27,
    ROUTE_BARRIER_TO_CARTRIDGE,
)


@pytest.fixture(scope="module")
def cartridge():
    return build_realized_waste_cartridge()


def _bounds(shape: cq.Workplane):
    box = shape.val().BoundingBox()
    return {
        "x": (float(box.xmin), float(box.xmax)),
        "y": (float(box.ymin), float(box.ymax)),
        "z": (float(box.zmin), float(box.zmax)),
    }


def test_realization_binds_exact_released_route_identity_and_package(cartridge):
    manifest = cartridge.manifest()
    assert manifest["authored_against_main_sha"] == AUTHORED_AGAINST_MAIN_SHA
    assert manifest["coordinate_frame_id"] == "MASCK_ONE_AUTHORITY_WORLD_MM"
    assert manifest["fluid_identity"] == PHASE_MIXED_WASTE
    assert manifest["route_id"] == ROUTE_BARRIER_TO_CARTRIDGE
    assert manifest["inlet_interface_id"] == INTERFACE_CARTRIDGE_INLET_I27
    assert tuple(manifest["released_route_handoff_world_mm"]) == ROUTE_HANDOFF_WORLD_MM
    assert tuple(manifest["body_inlet_wall_world_mm"]) == BODY_INLET_WALL_WORLD_MM
    assert manifest["inlet_handoff_gap_mm"] == INLET_HANDOFF_GAP_MM
    assert tuple(manifest["package_envelope_xyz_mm"]) == PACKAGE_ENVELOPE_XYZ_MM
    assert {
        axis: tuple(values) for axis, values in manifest["package_bounds_world_mm"].items()
    } == PACKAGE_BOUNDS_WORLD_MM


def test_body_closure_and_cavity_are_valid_nonoverlapping_breps_inside_package(cartridge):
    for shape in (
        cartridge.body_solid,
        cartridge.closure_solid,
        cartridge.installed_free_cavity_reference,
    ):
        assert shape.solids().size() == 1
        assert shape.val().isValid()
        assert shape.val().Volume() > 0.0

    assert cartridge.body_solid.val().intersect(cartridge.closure_solid.val()).Volume() == pytest.approx(0.0, abs=1e-7)
    assert cartridge.body_solid.val().intersect(cartridge.installed_free_cavity_reference.val()).Volume() == pytest.approx(0.0, abs=1e-7)
    assert cartridge.closure_solid.val().intersect(cartridge.installed_free_cavity_reference.val()).Volume() == pytest.approx(0.0, abs=1e-7)

    for shape in (cartridge.body_solid, cartridge.closure_solid, cartridge.installed_free_cavity_reference):
        bounds = _bounds(shape)
        for axis in ("x", "y", "z"):
            assert bounds[axis][0] >= PACKAGE_BOUNDS_WORLD_MM[axis][0] - 1e-7
            assert bounds[axis][1] <= PACKAGE_BOUNDS_WORLD_MM[axis][1] + 1e-7


def test_exact_authority_protected_face_envelopes_are_clear(cartridge):
    manifest = cartridge.manifest()
    protected = manifest["protected_zone_intersections_mm3"]
    assert manifest["protected_face_status"] == PROTECTED_FACE_STATUS
    assert len(protected) == 5
    assert set(protected) == {
        "MASCK_ONE-PROTECTED-EYE-LEFT",
        "MASCK_ONE-PROTECTED-EYE-RIGHT",
        "MASCK_ONE-PROTECTED-MOUTH",
        "MASCK_ONE-PROTECTED-NOSTRIL-LEFT",
        "MASCK_ONE-PROTECTED-NOSTRIL-RIGHT",
    }
    assert all(volume == pytest.approx(0.0, abs=1e-7) for volume in protected.values())
    assert "2P5D" in manifest["protected_face_policy"]


def test_geometric_capacity_deficit_is_explicit_and_never_promoted_to_retained_or_usable(cartridge):
    manifest = cartridge.manifest()
    assert cartridge.installed_geometric_free_capacity_mL == pytest.approx(
        EXPECTED_INSTALLED_GEOMETRIC_FREE_CAPACITY_ML,
        abs=1e-6,
    )
    assert cartridge.geometric_capacity_delta_to_retained_requirement_mL == pytest.approx(
        EXPECTED_INSTALLED_GEOMETRIC_FREE_CAPACITY_ML - RETAINED_CAPACITY_REQUIREMENT_ML,
        abs=1e-6,
    )
    assert cartridge.geometric_margin_over_retained_requirement_mL < 0.0
    assert manifest["retained_capacity_requirement_mL"] == RETAINED_CAPACITY_REQUIREMENT_ML
    assert manifest["geometric_capacity_requirement_met"] is False
    assert manifest["digital_capacity_ready"] is False
    assert manifest["capacity_status"] == CAPACITY_STATUS
    assert "BELOW_RETAINED_REQUIREMENT" in manifest["capacity_status"]
    assert "NOT_USABLE_OR_RETAINED" in manifest["capacity_status"]
    assert manifest["physical_validation_eligible"] is False
    assert manifest["development_assembly_material_eligible"] is False


def test_inlet_key_vent_hygiene_and_service_boundaries_remain_honest(cartridge):
    manifest = cartridge.manifest()
    assert manifest["hygiene_classification"] == HYGIENE_CLASSIFICATION == "WET_REMOVABLE"
    assert manifest["key_status"] == KEY_STATUS
    assert manifest["device_key_counterpart_realized"] is False
    assert manifest["positive_retention_realized"] is False
    assert manifest["vent_status"] == VENT_STATUS
    assert manifest["service_status"] == SERVICE_STATUS
    assert manifest["service_condition"] == "MASK_REMOVED_UNPOWERED"
    assert manifest["continuous_service_motion_realized"] is False
    assert manifest["evidence_status"] == EVIDENCE_STATUS
    assert manifest["inlet_bore_diameter_mm"] == 2.4
    assert manifest["inlet_reference_diameter_mm"] == 4.0


def test_reference_geometry_is_explicit_and_not_silently_material(cartridge):
    for shape in (
        cartridge.inlet_connector_clearance_reference,
        cartridge.seal_land_reference,
        cartridge.vent_clearance_reference,
        cartridge.service_reservation_reference,
    ):
        assert shape.solids().size() == 1
        assert shape.val().isValid()
        assert shape.val().Volume() > 0.0
    inlet_bounds = _bounds(cartridge.inlet_connector_clearance_reference)
    assert inlet_bounds["x"] == pytest.approx((-41.0, -37.0), abs=1e-7)
    assert cartridge.inlet_connector_clearance_reference.val().intersect(cartridge.body_solid.val()).Volume() == pytest.approx(0.0, abs=1e-7)


def test_current_shell_interference_is_measured_not_hidden(cartridge):
    manifest = cartridge.manifest()
    assert manifest["current_released_shell_interference_mm3"] >= 0.0
    if manifest["current_released_shell_interference_mm3"] > 1e-7:
        assert manifest["current_released_shell_state"].startswith("CURRENT_RELEASED_SHELL_INTERFERENCE_PRESENT")
    else:
        assert manifest["current_released_shell_state"].startswith("NO_CURRENT_RELEASED_SHELL_INTERFERENCE")
    assert manifest["development_assembly_material_eligible"] is False


def test_manifest_is_deterministic_and_source_bound(cartridge):
    second = build_realized_waste_cartridge()
    assert second.manifest() == cartridge.manifest()
    assert second.manifest_sha256 == cartridge.manifest_sha256
    assert len(cartridge.manifest_sha256) == 64
    assert len(cartridge.source_backbone_manifest_sha256) == 64


def test_stale_source_binding_nonfinite_collision_and_protected_conflict_fail_closed(cartridge, monkeypatch):
    monkeypatch.setattr(
        cartridge_module,
        "SOURCE_GIT_BLOB_IDENTITIES",
        (("config/masck_one_authority.yaml", "0" * 40),),
    )
    with pytest.raises(RealizedWasteCartridgeError, match="source moved"):
        build_realized_waste_cartridge()
    monkeypatch.undo()

    bad_shell = replace(cartridge, current_released_shell_interference_mm3=float("nan"))
    with pytest.raises(RealizedWasteCartridgeError, match="shell interference must be finite"):
        bad_shell.validate()

    zones = list(cartridge.protected_zone_intersections_mm3)
    zones[2] = (zones[2][0], 0.01)
    bad_protected = replace(cartridge, protected_zone_intersections_mm3=tuple(zones))
    with pytest.raises(RealizedWasteCartridgeError, match="violates protected zone"):
        bad_protected.validate()


def test_step_round_trip_preserves_body_closure_and_cavity(tmp_path, cartridge):
    for name, shape in (
        ("body", cartridge.body_solid),
        ("closure", cartridge.closure_solid),
        ("cavity", cartridge.installed_free_cavity_reference),
    ):
        path = tmp_path / f"waste_cartridge_{name}.step"
        cq.exporters.export(shape, str(path))
        imported = cq.importers.importStep(str(path))
        assert imported.solids().size() == 1
        assert imported.val().isValid()
        assert imported.val().Volume() == pytest.approx(shape.val().Volume(), rel=0.0, abs=1e-4)
        original_bounds = _bounds(shape)
        imported_bounds = _bounds(imported)
        for axis in ("x", "y", "z"):
            assert imported_bounds[axis] == pytest.approx(original_bounds[axis], abs=1e-4)


def test_release_smoke_exports_candidate_and_reference_geometry_without_assembly_promotion(tmp_path, cartridge):
    report = export_release(tmp_path)
    manifest = report["digital_geometry"]["realized_waste_cartridge_v1"]
    assert manifest["manifest_sha256"] == cartridge.manifest_sha256
    assert manifest["development_assembly_material_eligible"] is False
    assert manifest["physical_validation_eligible"] is False
    assert manifest["geometric_capacity_requirement_met"] is False
    assert all(value == pytest.approx(0.0, abs=1e-7) for value in manifest["protected_zone_intersections_mm3"].values())
    assert "waste_cartridge_envelope" in report["development_assembly_exclusions"]

    expected = {
        "cell11_waste_cartridge_body_candidate.step",
        "cell11_waste_cartridge_closure_candidate.step",
        "cell11_waste_cartridge_installed_free_cavity_reference.step",
        "cell11_waste_cartridge_inlet_connector_clearance_reference.step",
        "cell11_waste_cartridge_seal_land_reference.step",
        "cell11_waste_cartridge_vent_clearance_reference.step",
        "cell11_waste_cartridge_service_reservation_reference.step",
    }
    assert expected.issubset(set(report["exported_step_files"]))
    for filename in expected:
        path = tmp_path / filename
        assert path.is_file()
        imported = cq.importers.importStep(str(path))
        assert imported.solids().size() == 1
        assert imported.val().isValid()
    assert (tmp_path / "masck_one_development_assembly.step").is_file()
