from __future__ import annotations

import math

import cadquery as cq
import pytest

import masck_one.dry_side_package as dsp
from masck_one.authority import load_authority
from masck_one.model import build_model


@pytest.fixture(scope="module")
def package():
    authority = load_authority()
    return dsp.build_dry_side_package(authority, build_model(authority))


def _by_id(items, geometry_id: str):
    matches = tuple(item for item in items if item.geometry_id == geometry_id)
    assert len(matches) == 1
    return matches[0]


def test_package_is_canonical_source_bound_and_deterministic(package) -> None:
    manifest = package.manifest()
    assert manifest["schema"] == dsp.SCHEMA
    assert manifest["world_frame_id"] == "MASCK_ONE_AUTHORITY_WORLD_MM"
    assert manifest["authority_revision"] == "2026-08-30-R1"
    assert manifest["sources"]["main_sha"] == dsp.SOURCE_MAIN_SHA
    assert manifest["sources"]["legacy_donor_pr"] == 64
    assert manifest["sources"]["legacy_donor_head_sha"] == "49a32d0c61bd1057ee707ee2ef20b8ff4e6ede01"
    assert manifest["sources"]["donor_semantics"].endswith("NOT_AUTHORITY")
    assert manifest["package_sha256"] == package.package_sha256
    assert package.package_sha256 == dsp.build_dry_side_package().package_sha256


def test_local_frame_is_explicit_identity_rotation_plus_world_translation(package) -> None:
    frame = package.manifest()["dry_bay_local_frame"]
    assert frame["frame_id"] == "MASCK_ONE_DRY_BAY_LOCAL_MM"
    assert frame["parent_frame_id"] == "MASCK_ONE_AUTHORITY_WORLD_MM"
    assert frame["origin_in_parent_mm"] == list(dsp.DRY_BAY_CENTER_MM)
    assert frame["x_axis_in_parent"] == [1.0, 0.0, 0.0]
    assert frame["y_axis_in_parent"] == [0.0, 1.0, 0.0]
    assert frame["z_axis_in_parent"] == [0.0, 0.0, 1.0]


def test_battery_benchmark_and_power_runtime_evidence_stay_honest(package) -> None:
    authority = load_authority()
    manifest = package.manifest()
    assert package.battery_nominal_voltage_V == authority.number("battery_reference", "nominal_voltage_V")
    assert package.battery_capacity_mAh == authority.number("battery_reference", "capacity_mAh")
    assert package.battery_mass_g == authority.number("battery_reference", "mass_g")
    assert manifest["power_ledger"]["total_dry_side_mass_g"] is None
    assert manifest["power_ledger"]["total_power_W"] is None
    assert manifest["power_ledger"]["runtime_estimate_h"] is None
    assert manifest["power_ledger"]["runtime_validated"] is False
    assert all(load["nominal_power_W"] is None for load in manifest["power_ledger"]["loads"])
    assert manifest["integration"]["electrical_safety_validated"] is False
    assert manifest["integration"]["ingress_validated"] is False


def test_physical_reference_and_service_firewall_is_explicit(package) -> None:
    assert tuple(item.geometry_id for item in package.physical_geometry) == ("DRY_BAY_CARRIER_STRUCTURE",)
    assert {item.material_class for item in package.physical_geometry} == {"PHYSICAL_MATERIAL_CANDIDATE"}
    assert all(item.material_class != "PHYSICAL_MATERIAL_CANDIDATE" for item in package.reference_geometry)
    assert all(item.material_class == "SERVICE_SWEEP_REFERENCE" for item in package.service_geometry)
    manifest = package.manifest()
    assert manifest["integration"]["development_assembly_status"] == "REVIEW_ONLY_NOT_INSERTED_INTO_RELEASED_PHYSICAL_ASSEMBLY"
    assert manifest["interfaces"]["frame_attachment"]["relationship"] == "POSITIVE_ATTACHMENT_REQUIRED_COUNTERPART_UNRELEASED"


def test_rear_closure_has_exactly_one_external_owner_and_no_cell12_door_material(package) -> None:
    manifest = package.manifest()
    closure = _by_id(package.reference_geometry, "REAR_CLOSURE_SEAL_INTERFACE_RESERVATION")
    assert closure.material_class == "SEAL_INTERFACE_RESERVATION"
    assert not any(item.geometry_id == "REAR_SERVICE_DOOR_CANDIDATE" for item in package.physical_geometry)
    assert not any("DOOR" in item.geometry_id for item in package.service_geometry)
    assert manifest["interfaces"]["rear_service_closure"]["owner"] == "CELL2_EXTERIOR"
    assert manifest["interfaces"]["rear_service_closure"]["cell12_visible_door_material_exists"] is False
    assert manifest["integration"]["cell12_visible_door_material_exists"] is False
    assert manifest["service_sequence"]["battery_removal"][1] == "CELL2_EXTERIOR_REAR_COVER_REMOVED"
    structure = _by_id(package.physical_geometry, "DRY_BAY_CARRIER_STRUCTURE")
    assert dsp._intersection(structure.solid, closure.solid) == 0.0
    closure_bb = closure.solid.val().BoundingBox()
    assert closure_bb.zmax == pytest.approx(-47.0)
    assert closure_bb.zmin == pytest.approx(-47.4)


def test_noncompressive_carrier_and_internal_nesting_are_geometrically_real(package) -> None:
    structure = _by_id(package.physical_geometry, "DRY_BAY_CARRIER_STRUCTURE").solid
    battery = _by_id(package.reference_geometry, "BATTERY_PACKAGING_BENCHMARK").solid
    fault = _by_id(package.reference_geometry, "BATTERY_FAULT_CLEARANCE_RESERVATION").solid
    pcb = _by_id(package.reference_geometry, "PCB_BARE_BOARD_REFERENCE").solid
    power = _by_id(package.reference_geometry, "PCB_POWER_PROTECTION_CHARGING_ZONE").solid
    assert dsp._intersection(battery, fault) > 0.0
    assert dsp._intersection(structure, battery) == 0.0
    assert dsp._intersection(structure, fault) == 0.0
    assert dsp._intersection(structure, pcb) == 0.0
    assert dsp._intersection(pcb, power) > 0.0
    assert dsp._geometry(structure)["spans_mm"] == pytest.approx(list(dsp.DRY_BAY_OUTER_MM), abs=1e-6)


def test_battery_service_sweep_is_continuous_negative_z_and_required_clear(package) -> None:
    assert len(package.service_geometry) == 1
    battery_sweep = _by_id(package.service_geometry, "BATTERY_REARWARD_SERVICE_SWEEP")
    bb = battery_sweep.solid.val().BoundingBox()
    authority = load_authority()
    battery_depth = float(authority.get("battery_reference", "envelope_mm")[2])
    fault_depth = battery_depth + 2.0 * dsp.BATTERY_FAULT_CLEARANCE_Z_MM
    assert bb.zmin == pytest.approx(dsp.BATTERY_SERVICE_END_Z_MM - fault_depth / 2.0)
    assert bb.zmax == pytest.approx(dsp.BATTERY_CENTER_MM[2] + fault_depth / 2.0)
    assert all(check.intersection_volume_mm3 == 0.0 for check in package.collision_checks)
    assert all(math.isfinite(check.minimum_distance_mm) and check.minimum_distance_mm >= 0.0 for check in package.collision_checks)


def test_current_released_and_protected_geometry_is_clear(package) -> None:
    ids = {check.second_id for check in package.collision_checks}
    for expected in (
        "rigid_shell",
        "actuator_envelope_1",
        "actuator_envelope_2",
        "actuator_envelope_3",
        "actuator_envelope_4",
        "water_reservoir_envelope",
        "waste_cartridge_envelope",
        "battery_reference_envelope",
        "visual_eye_left",
        "visual_eye_right",
        "visual_mouth",
        "visual_nostril_left",
        "visual_nostril_right",
    ):
        assert expected in ids


def test_dfm_records_wall_and_rib_baseline_without_false_maturity(package) -> None:
    authority = load_authority()
    manifest = package.manifest()
    low, high = authority.get("manufacturing", "rib_thickness_ratio_range")
    assert low <= package.rib_ratio <= high
    assert manifest["dfm"]["dry_bay_wall_mm"] >= authority.number("geometry", "shell_absolute_development_min_mm")
    assert manifest["dfm"]["draft_geometry_realized"] is False
    assert manifest["dfm"]["material_status"] == "UNSELECTED"
    assert manifest["dfm"]["tolerance_stack_status"] == "PROVISIONAL_DIGITAL_CLEARANCES_ONLY"


def test_hmi_thermal_electrical_handoff_does_not_invent_connector_datum(package) -> None:
    handoff = package.manifest()["interfaces"]["hmi_thermal_electrical_handoff"]
    assert handoff["owner"] == "CELL14_HMI_THERMAL"
    assert handoff["datum_xyz_mm"] is None
    assert handoff["status"].startswith("BLOCKED_")


def test_step_round_trip_preserves_physical_candidate_bounds(tmp_path, package) -> None:
    for item in package.physical_geometry:
        path = tmp_path / f"{item.geometry_id}.step"
        cq.exporters.export(item.solid, str(path))
        imported = cq.importers.importStep(str(path))
        before = item.solid.val().BoundingBox()
        after = imported.val().BoundingBox()
        assert imported.val().isValid()
        assert len(imported.val().Solids()) == 1
        assert after.xlen == pytest.approx(before.xlen, abs=1e-4)
        assert after.ylen == pytest.approx(before.ylen, abs=1e-4)
        assert after.zlen == pytest.approx(before.zlen, abs=1e-4)


def test_source_movement_fails_closed(monkeypatch) -> None:
    original = dsp.SOURCE_GIT_BLOB_IDENTITIES
    monkeypatch.setattr(dsp, "SOURCE_GIT_BLOB_IDENTITIES", ((original[0][0], "0" * 40), *original[1:]))
    with pytest.raises(dsp.DrySidePackageError, match="source moved"):
        dsp._require_sources()


def test_hostile_invalid_geometry_and_wrong_service_sign_fail_closed() -> None:
    with pytest.raises(dsp.DrySidePackageError, match="finite"):
        dsp._box((1.0, 1.0, float("nan")), (0.0, 0.0, 0.0))
    with pytest.raises(dsp.DrySidePackageError, match="-Z"):
        dsp._z_sweep((1.0, 1.0, 1.0), (0.0, 0.0, -10.0), -9.0)
    with pytest.raises(dsp.DrySidePackageError, match="material class"):
        dsp.PackageGeometry(
            "BAD",
            "hostile invalid material class",
            cq.Workplane("XY").box(1.0, 1.0, 1.0),
            "REFERENCE_PRETENDING_TO_BE_MATERIAL",
            "DRY_ALWAYS",
            "INVALID",
        )
