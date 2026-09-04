from dataclasses import replace

import pytest

from masck_one.authority import load_authority
from masck_one.electronics_package import (
    BATTERY_FAULT_CLEARANCE_XY_MM,
    BATTERY_FAULT_CLEARANCE_Z_MM,
    CAD_PLACEHOLDER,
    CONTROL_IDS,
    DECISION_GATED,
    DRY_BAY_OUTER_MM,
    LOAD_IDS,
    PCB_PLACEHOLDER_ENVELOPE_MM,
    SOURCE_EXTERIOR_HEAD_SHA,
    SOURCE_FLUID_HEAD_SHA,
    SOURCE_MAIN_SHA,
    SOURCE_MANUAL_A_HEAD_SHA,
    ElectronicsPackageError,
    build_electronics_package,
)


@pytest.fixture(scope="module")
def built():
    authority = load_authority()
    package = build_electronics_package(authority)
    return authority, package


def _part(package, part_id):
    matches = [part for part in package.parts if part.part_id == part_id]
    assert len(matches) == 1
    return matches[0]


def _spans(part):
    bb = part.solid.val().BoundingBox()
    return (float(bb.xlen), float(bb.ylen), float(bb.zlen))


def test_source_heads_are_exact_live_integration_inputs(built):
    _, package = built
    assert package.source_main_sha == SOURCE_MAIN_SHA
    assert package.source_manual_a_head_sha == SOURCE_MANUAL_A_HEAD_SHA
    assert package.source_exterior_head_sha == SOURCE_EXTERIOR_HEAD_SHA
    assert package.source_fluid_head_sha == SOURCE_FLUID_HEAD_SHA
    assert package.physical_validation_eligible is False


def test_battery_remains_exact_packaging_benchmark_with_fault_clearance(built):
    authority, package = built
    battery = _part(package, "BATTERY_REFERENCE")
    fault = _part(package, "BATTERY_FAULT_CLEARANCE")
    carrier = _part(package, "BATTERY_CARRIER")
    expected = tuple(float(v) for v in authority.get("battery_reference", "envelope_mm"))
    assert _spans(battery) == pytest.approx(expected)
    assert battery.geometry_status == authority.get("battery_reference", "status")
    assert _spans(fault) == pytest.approx(
        (
            expected[0] + 2 * BATTERY_FAULT_CLEARANCE_XY_MM,
            expected[1] + 2 * BATTERY_FAULT_CLEARANCE_XY_MM,
            expected[2] + 2 * BATTERY_FAULT_CLEARANCE_Z_MM,
        )
    )
    assert float(carrier.solid.val().intersect(battery.solid.val()).Volume()) == pytest.approx(0.0, abs=1e-9)
    assert float(carrier.solid.val().intersect(fault.solid.val()).Volume()) == pytest.approx(0.0, abs=1e-9)
    assert package.battery_service_trajectory_xyz_mm[0][2] > package.battery_service_trajectory_xyz_mm[-1][2]


def test_dry_bay_is_shallow_and_separate_from_wet_packages(built):
    _, package = built
    dry_bay = _part(package, "DRY_BAY_SHELL")
    assert _spans(dry_bay) == pytest.approx(DRY_BAY_OUTER_MM)
    assert dry_bay.wet_dry_class == "DRY_ALWAYS"
    wet_checks = [
        check
        for check in package.interference_checks
        if check.first_id == "DRY_BAY_SHELL" and check.second_id in {"WATER_RESERVOIR_ENVELOPE", "WASTE_CARTRIDGE_ENVELOPE"}
    ]
    assert len(wet_checks) == 2
    assert all(check.passes for check in wet_checks)


def test_pcb_placeholder_mounting_datums_and_power_protection_are_realized(built):
    _, package = built
    pcb = _part(package, "PCB_CONTROL_PLACEHOLDER")
    protection = _part(package, "PCB_POWER_PROTECTION_ZONE")
    assert _spans(pcb) == pytest.approx(PCB_PLACEHOLDER_ENVELOPE_MM)
    assert pcb.geometry_status == CAD_PLACEHOLDER
    assert len(package.pcb_mounting_datums_xyz_mm) == 4
    assert len(set(package.pcb_mounting_datums_xyz_mm)) == 4
    assert "UNSELECTED" in protection.geometry_status


def test_interface_ledger_covers_battery_pcb_actuators_pumps_hmi_thermal_and_charging(built):
    _, package = built
    ids = {item.interface_id for item in package.interfaces}
    required = {
        "BATTERY-CONNECTOR-ACCESS",
        "PCB-POWER-EDGE",
        "ACTUATOR-A-ELECTRICAL",
        "ACTUATOR-B-ELECTRICAL",
        "ACTUATOR-C-ELECTRICAL",
        "ACTUATOR-D-ELECTRICAL",
        "WATER-PUMP-DRY-BULKHEAD",
        "CLEANSER-PUMP-DRY-BULKHEAD",
        "WASTE-PUMP-DRY-BULKHEAD",
        "HMI-SIDE-PANEL",
        "WARM-LEFT-SEALED-FEED",
        "WARM-RIGHT-SEALED-FEED",
        "COOL-RESERVATION",
        "CHARGING-DRY-SIDE",
        "CHARGING-USER-ACCESS",
        "STATUS-OPTICAL-WINDOW",
    }
    assert required <= ids
    assert len(ids) == len(package.interfaces)


def test_harness_routes_have_real_centerlines_and_clearance_geometry(built):
    _, package = built
    assert len(package.harness_routes) == 13
    assert len({route.route_id for route in package.harness_routes}) == len(package.harness_routes)
    for route in package.harness_routes:
        assert len(route.centerline_xyz_mm) >= 2
        assert route.centerline_length_mm > 0.0
        assert route.clearance_solid.val().isValid()
        assert float(route.clearance_solid.val().Volume()) > 0.0
        assert "UNSELECTED" in route.conductor_spec_status
        assert "SEALED_BULKHEAD" in route.wet_boundary_status


def test_manual_a_release_and_cartridge_service_sweeps_are_consumed(built):
    _, package = built
    release = [check for check in package.interference_checks if "QUICK-RELEASE-OUTBOARD-WITHDRAWAL" in check.check_id]
    cartridge = [check for check in package.interference_checks if "CARTRIDGE-DOWNWARD-REMOVAL" in check.check_id]
    assert release
    assert cartridge
    assert all(check.passes for check in release + cartridge)


def test_four_control_geometry_preserves_clean_first_hierarchy_without_claiming_authority(built):
    _, package = built
    assert tuple(control.control_id for control in package.controls) == CONTROL_IDS
    clean = package.controls[0]
    assert clean.control_id == "CLEAN"
    assert clean.hierarchy == "PRIMARY_DOMINANT"
    assert clean.tactile_land_mm[0] > max(control.tactile_land_mm[0] for control in package.controls[1:])
    assert all(control.mapping_status == DECISION_GATED for control in package.controls)
    assert package.hmi_decision_status == DECISION_GATED
    assert "LED" in _part(package, "STATUS_WINDOW_RESERVATION").geometry_status


def test_charging_is_structurally_reserved_without_ip_or_wet_charging_claim(built):
    _, package = built
    charging = _part(package, "CHARGING_INTERFACE_RESERVATION")
    assert charging.wet_dry_class == "SEALED_NONUSER"
    assert "CONNECTOR_TYPE_UNSELECTED" in charging.geometry_status
    assert "IP_RATING" in package.charging_status
    assert "NOT_AUTHORIZED" in package.charging_status


def test_warm_is_realized_as_dual_sealed_reservation_and_cool_stays_experimental(built):
    _, package = built
    warm = [_part(package, "WARM_LEFT_RESERVATION"), _part(package, "WARM_RIGHT_RESERVATION")]
    assert all(part.wet_dry_class == "SEALED_NONUSER" for part in warm)
    assert "SKIN_SAFETY_PHYSICAL_GATE_OPEN" in package.warm_status
    cool = _part(package, "COOL_EXPERIMENTAL_RESERVATION")
    assert cool.wet_dry_class == "SEALED_NONUSER"
    assert "EXPERIMENTAL" in package.cool_status
    assert "NO_MVP_DEPENDENCY" in package.cool_status
    assert "NO_CONDENSATION" in package.cool_status


def test_power_ledger_does_not_fabricate_runtime_or_unknown_loads(built):
    authority, package = built
    ledger = package.power_ledger
    assert ledger.battery_nominal_voltage_V == pytest.approx(float(authority.get("battery_reference", "nominal_voltage_V")))
    assert ledger.battery_nameplate_capacity_mAh == pytest.approx(float(authority.get("battery_reference", "capacity_mAh")))
    assert ledger.battery_source_status == authority.get("battery_reference", "status")
    assert tuple(load.load_id for load in ledger.loads) == LOAD_IDS
    assert all(load.nominal_power_W is None for load in ledger.loads)
    assert all(load.measured is False for load in ledger.loads)
    assert ledger.total_power_W is None
    assert ledger.runtime_estimate_h is None
    assert ledger.runtime_validated is False


def test_all_required_interference_checks_are_digitally_clear(built):
    _, package = built
    assert package.interference_checks
    assert all(check.passes for check in package.interference_checks)
    assert all(check.status == "PASS_DIGITAL_CLEAR" for check in package.interference_checks)


def test_door_and_battery_have_nonteleporting_rearward_service_paths(built):
    _, package = built
    for trajectory in (package.battery_service_trajectory_xyz_mm, package.door_service_trajectory_xyz_mm):
        assert len(trajectory) >= 3
        assert all(trajectory[i + 1][2] < trajectory[i][2] for i in range(len(trajectory) - 1))


def test_manifest_is_deterministic_and_never_promotes_physical_validation(built):
    authority, package = built
    second = build_electronics_package(authority)
    assert package.manifest() == second.manifest()
    assert package.package_sha256 == second.package_sha256
    assert package.physical_validation_eligible is False
    assert "NOT_PHYSICAL_VALIDATION" in package.evidence_status


def test_duplicate_identity_and_runtime_promotion_fail_closed(built):
    _, package = built
    with pytest.raises(ElectronicsPackageError, match="part IDs cannot repeat"):
        replace(package, parts=package.parts + (package.parts[-1],))
    with pytest.raises(ElectronicsPackageError, match="harness route IDs cannot repeat"):
        replace(package, harness_routes=package.harness_routes + (package.harness_routes[-1],))
    with pytest.raises(ElectronicsPackageError, match="runtime/power total"):
        replace(package.power_ledger, total_power_W=3.0)
    with pytest.raises(ElectronicsPackageError, match="runtime cannot be marked validated"):
        replace(package.power_ledger, runtime_validated=True)


def test_hmi_mapping_cannot_be_silently_promoted(built):
    _, package = built
    with pytest.raises(ElectronicsPackageError, match="must remain decision gated"):
        replace(package, hmi_decision_status="FROZEN")
    with pytest.raises(ElectronicsPackageError, match="four-control geometry"):
        replace(package, controls=tuple(reversed(package.controls)))
