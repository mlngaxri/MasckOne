from masck_one.authority import load_authority
from masck_one.manual_b_architecture import build_manual_b_architecture


def test_manual_b_architecture_binds_authority_and_hygiene_classes():
    authority = load_authority()
    architecture = build_manual_b_architecture(authority)
    architecture.validate_current_authority(authority)
    allowed = set(authority.get("manufacturing", "hygiene_classes"))
    assert all(package.wet_dry_class in allowed for package in architecture.packages)


def test_power_electronics_reservations_do_not_invent_unselected_hardware():
    architecture = build_manual_b_architecture(load_authority())
    packages = {item.package_id: item for item in architecture.packages}
    assert packages["BATTERY_REFERENCE"].envelope_mm == (34.5, 52.0, 6.3)
    assert packages["BATTERY_REFERENCE"].status == "PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE"
    assert packages["PCB_CONTROL"].envelope_mm is None
    assert "BLOCKED_PENDING_SELECTED_PCB_ENVELOPE" in packages["PCB_CONTROL"].status
    assert packages["CHARGING_INTERFACE"].envelope_mm is None
    assert "BLOCKED_PENDING_SELECTED_CONNECTOR" in packages["CHARGING_INTERFACE"].status
    assert packages["WARM_RESERVATION"].envelope_mm is None
    assert packages["COOL_RESERVATION"].envelope_mm is None
    assert architecture.active_wet_cycle_charging_authorized is False


def test_hmi_is_clean_first_app_independent_and_recess_limited():
    hmi = build_manual_b_architecture(load_authority()).hmi
    assert hmi.primary_action == "CLEAN"
    assert hmi.primary_tactile_land_min_mm >= 10.0
    assert hmi.primary_tactile_land_min_mm > hmi.secondary_tactile_land_min_mm
    assert hmi.status_window_recess_max_mm <= 0.60
    assert hmi.app_independent is True


def test_cmf_hierarchy_is_restrained_and_not_promoted_to_production_evidence():
    architecture = build_manual_b_architecture(load_authority())
    roles = {item.role_id: item for item in architecture.cmf_roles}
    assert roles["rigid_shell"].visual_role == "PRIMARY_CALM_CONTINUOUS_FIELD"
    assert "LOW_SATIN" in roles["rigid_shell"].finish_intent
    assert roles["retention"].finish_intent == "QUIET_MATTE_NON_METALLIC_INTENT"
    assert "ONE_RESTRAINED_COOL_ACCENT" in roles["control_status"].colour_intent
    assert architecture.physical_validation_eligible is False


def test_wet_dry_split_keeps_electronics_dry_and_service_modules_removable():
    architecture = build_manual_b_architecture(load_authority())
    packages = {item.package_id: item for item in architecture.packages}
    assert packages["PCB_CONTROL"].wet_dry_class == "DRY_ALWAYS"
    assert packages["BATTERY_REFERENCE"].wet_dry_class == "DRY_ALWAYS"
    assert packages["WATER_RESERVOIR"].wet_dry_class == "WET_REMOVABLE"
    assert packages["WASTE_CARTRIDGE"].wet_dry_class == "WET_REMOVABLE"
    assert packages["FRESH_DISTRIBUTION"].wet_dry_class == "WET_DRAINABLE"
    assert packages["WASTE_ROUTES"].wet_dry_class == "WET_DRAINABLE"
    assert "NO_BLIND_WELLS" in architecture.drainage_policy
