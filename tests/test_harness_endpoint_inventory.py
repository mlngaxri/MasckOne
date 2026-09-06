from dataclasses import replace

import pytest

from masck_one.harness_endpoint_inventory import (
    AUTHORITY_BLOB_SHA,
    ENDPOINT_IDS,
    EP_ACTUATOR_01,
    EP_ACTUATOR_02,
    EP_ACTUATOR_03,
    EP_ACTUATOR_04,
    EP_BATTERY,
    EP_CHARGING,
    EP_COOL_OPTIONAL,
    EP_HMI,
    EP_PCB,
    EP_PUMP_CLEANSER,
    EP_PUMP_WASTE,
    EP_PUMP_WATER,
    EP_WARM_LEFT,
    EP_WARM_RIGHT,
    EVIDENCE_STATUS,
    LEGACY_DONOR_FILE_BLOB_SHA,
    LEGACY_DONOR_HEAD_SHA,
    LEGACY_ROUTE_DISPOSITION,
    LEGACY_ROUTE_IDS,
    OPTIONAL_UNRESOLVED,
    ROLE_ACTUATION_LOAD,
    ROLE_CHARGING_INTERFACE,
    ROLE_FLUID_PUMP_LOAD,
    ROLE_HMI,
    ROLE_OPTIONAL_THERMAL_LOAD,
    ROLE_POWER_CONTROL_BACKBONE,
    ROLE_POWER_SOURCE,
    ROLE_THERMAL_LOAD,
    SCHEMA,
    SERVICE_DISCONNECT_REQUIRED,
    SERVICE_GEOMETRY_UNRESOLVED,
    SERVICE_INTERNAL_FIXED,
    SERVICE_OPTIONAL_UNRESOLVED,
    SERVICE_USER_INTERFACE,
    SIDE_DRY_INTENT,
    SIDE_UNRESOLVED,
    SIDE_WET_DRY_CROSSING_REQUIRED,
    SOURCE_GIT_BLOB_IDENTITIES,
    SOURCE_MAIN_SHA,
    WORLD_FRAME_ID,
    HarnessEndpointInventoryError,
    build_harness_endpoint_inventory,
)


@pytest.fixture(scope="module")
def inventory():
    return build_harness_endpoint_inventory()


def test_registry_binds_current_main_authority_and_source_graph(inventory):
    assert inventory.schema == SCHEMA
    assert inventory.authored_against_main_sha == SOURCE_MAIN_SHA
    assert inventory.authority_blob_sha == AUTHORITY_BLOB_SHA
    assert inventory.coordinate_frame_id == WORLD_FRAME_ID
    assert inventory.source_git_blob_identities == SOURCE_GIT_BLOB_IDENTITIES
    assert tuple(endpoint.endpoint_id for endpoint in inventory.endpoints) == ENDPOINT_IDS
    assert tuple(route.route_id for route in inventory.legacy_routes) == LEGACY_ROUTE_IDS
    assert len(inventory.endpoints) == 14
    assert len(inventory.legacy_routes) == 13


def test_released_package_anchors_are_not_spoofed_as_electrical_or_actuator_datums(inventory):
    by_id = {endpoint.endpoint_id: endpoint for endpoint in inventory.endpoints}
    battery = by_id[EP_BATTERY]
    assert battery.package_anchor_xyz_mm == (0.0, 0.0, -15.0)
    assert battery.electrical_interface_datum_xyz_mm is None
    assert battery.route_ready is False
    assert by_id[EP_PCB].package_anchor_xyz_mm is None
    assert by_id[EP_PCB].electrical_interface_datum_xyz_mm is None

    for endpoint_id in (EP_ACTUATOR_01, EP_ACTUATOR_02, EP_ACTUATOR_03, EP_ACTUATOR_04):
        endpoint = by_id[endpoint_id]
        assert endpoint.package_anchor_xyz_mm is None
        assert "MODEL_PACKAGE_REFERENCE_TRANSFORM_NOT_ENDPOINT_DATUM" in endpoint.package_anchor_status
        assert endpoint.electrical_interface_datum_xyz_mm is None
        assert endpoint.route_ready is False

    assert all(endpoint.electrical_interface_datum_xyz_mm is None for endpoint in inventory.endpoints)


def test_every_endpoint_has_stable_electrical_role_owner_side_and_service_class(inventory):
    by_id = {endpoint.endpoint_id: endpoint for endpoint in inventory.endpoints}
    expected = {
        EP_BATTERY: (ROLE_POWER_SOURCE, SIDE_DRY_INTENT, SERVICE_DISCONNECT_REQUIRED),
        EP_PCB: (ROLE_POWER_CONTROL_BACKBONE, SIDE_DRY_INTENT, SERVICE_INTERNAL_FIXED),
        EP_ACTUATOR_01: (ROLE_ACTUATION_LOAD, SIDE_UNRESOLVED, SERVICE_INTERNAL_FIXED),
        EP_ACTUATOR_02: (ROLE_ACTUATION_LOAD, SIDE_UNRESOLVED, SERVICE_INTERNAL_FIXED),
        EP_ACTUATOR_03: (ROLE_ACTUATION_LOAD, SIDE_UNRESOLVED, SERVICE_INTERNAL_FIXED),
        EP_ACTUATOR_04: (ROLE_ACTUATION_LOAD, SIDE_UNRESOLVED, SERVICE_INTERNAL_FIXED),
        EP_PUMP_WATER: (ROLE_FLUID_PUMP_LOAD, SIDE_WET_DRY_CROSSING_REQUIRED, SERVICE_DISCONNECT_REQUIRED),
        EP_PUMP_CLEANSER: (ROLE_FLUID_PUMP_LOAD, SIDE_WET_DRY_CROSSING_REQUIRED, SERVICE_DISCONNECT_REQUIRED),
        EP_PUMP_WASTE: (ROLE_FLUID_PUMP_LOAD, SIDE_WET_DRY_CROSSING_REQUIRED, SERVICE_DISCONNECT_REQUIRED),
        EP_HMI: (ROLE_HMI, SIDE_UNRESOLVED, SERVICE_USER_INTERFACE),
        EP_WARM_LEFT: (ROLE_THERMAL_LOAD, SIDE_UNRESOLVED, SERVICE_INTERNAL_FIXED),
        EP_WARM_RIGHT: (ROLE_THERMAL_LOAD, SIDE_UNRESOLVED, SERVICE_INTERNAL_FIXED),
        EP_COOL_OPTIONAL: (ROLE_OPTIONAL_THERMAL_LOAD, SIDE_UNRESOLVED, SERVICE_OPTIONAL_UNRESOLVED),
        EP_CHARGING: (ROLE_CHARGING_INTERFACE, SIDE_DRY_INTENT, SERVICE_USER_INTERFACE),
    }
    assert set(expected) == set(ENDPOINT_IDS)
    for endpoint_id, classification in expected.items():
        endpoint = by_id[endpoint_id]
        assert (endpoint.electrical_role, endpoint.side_class, endpoint.service_class) == classification
        assert endpoint.service_geometry_status == SERVICE_GEOMETRY_UNRESOLVED


def test_registry_does_not_invent_connector_pinout_conductor_count_or_ratings(inventory):
    for endpoint in inventory.endpoints:
        assert endpoint.connector_family is None
        assert endpoint.pinout is None
        assert endpoint.conductor_count is None
        assert endpoint.voltage_rating_V is None
        assert endpoint.current_rating_A is None
        assert endpoint.ingress_rating is None
        manifest = endpoint.manifest()
        for key in (
            "connector_family",
            "pinout",
            "conductor_count",
            "voltage_rating_V",
            "current_rating_A",
            "ingress_rating",
        ):
            assert manifest[key] is None


def test_current_pump_hmi_warm_cool_and_charging_endpoints_remain_honestly_unready(inventory):
    by_id = {endpoint.endpoint_id: endpoint for endpoint in inventory.endpoints}
    for endpoint_id in (
        EP_PUMP_WATER,
        EP_PUMP_CLEANSER,
        EP_PUMP_WASTE,
        EP_HMI,
        EP_WARM_LEFT,
        EP_WARM_RIGHT,
        EP_CHARGING,
    ):
        endpoint = by_id[endpoint_id]
        assert endpoint.package_anchor_xyz_mm is None
        assert endpoint.electrical_interface_datum_xyz_mm is None
        assert endpoint.route_ready is False
    cool = by_id[EP_COOL_OPTIONAL]
    assert cool.current_maturity == OPTIONAL_UNRESOLVED
    assert cool.mvp_required is False
    assert cool.package_anchor_xyz_mm is None
    assert cool.route_ready is False


def test_manual_b_13_route_graph_is_preserved_only_as_donor_delta(inventory):
    manifest = inventory.manifest()
    donor = manifest["legacy_manual_b_donor"]
    assert donor["pr_number"] == 64
    assert donor["head_sha"] == LEGACY_DONOR_HEAD_SHA
    assert donor["source_file_blob_sha"] == LEGACY_DONOR_FILE_BLOB_SHA
    assert donor["route_count"] == 13
    assert donor["clearance_radius_mm"] == 1.4
    assert all(route.current_disposition == LEGACY_ROUTE_DISPOSITION for route in inventory.legacy_routes)
    assert inventory.legacy_routes_reusable_without_rebind == 0
    assert inventory.current_route_ready_count == 0


def test_every_legacy_route_maps_to_live_endpoint_identity_without_promoting_geometry(inventory):
    endpoint_ids = set(ENDPOINT_IDS)
    by_id = {endpoint.endpoint_id: endpoint for endpoint in inventory.endpoints}
    for route in inventory.legacy_routes:
        assert route.current_source_endpoint_id in endpoint_ids
        assert route.current_target_endpoint_id in endpoint_ids
        assert by_id[route.current_source_endpoint_id].route_ready is False
        assert by_id[route.current_target_endpoint_id].route_ready is False
    manifest = inventory.manifest()
    assert manifest["current_harness_centerlines_released"] is False
    assert manifest["wet_dry_bulkhead_geometry_released"] is False
    assert manifest["development_assembly_material_eligible"] is False
    assert manifest["physical_validation_eligible"] is False
    assert manifest["evidence_status"] == EVIDENCE_STATUS


def test_illegal_datum_route_ready_material_and_evidence_promotions_fail_closed(inventory):
    endpoint = inventory.endpoints[0]
    with pytest.raises(HarnessEndpointInventoryError, match="electrical mating datum"):
        replace(endpoint, electrical_interface_datum_xyz_mm=(0.0, 0.0, 0.0))
    with pytest.raises(HarnessEndpointInventoryError, match="route-ready"):
        replace(endpoint, route_ready=True)
    with pytest.raises(HarnessEndpointInventoryError, match="does not release Cell 13 harness centerlines"):
        replace(inventory, current_harness_centerlines_released=True)
    with pytest.raises(HarnessEndpointInventoryError, match="does not release wet/dry"):
        replace(inventory, wet_dry_bulkhead_geometry_released=True)
    with pytest.raises(HarnessEndpointInventoryError, match="not physical assembly material"):
        replace(inventory, development_assembly_material_eligible=True)
    with pytest.raises(HarnessEndpointInventoryError, match="cannot be physical validation"):
        replace(inventory, physical_validation_eligible=True)
    with pytest.raises(HarnessEndpointInventoryError, match="evidence status changed"):
        replace(inventory, evidence_status="PHYSICAL_VALIDATION")


def test_role_side_service_and_unreleased_electrical_details_fail_closed(inventory):
    battery = inventory.endpoints[0]
    with pytest.raises(HarnessEndpointInventoryError, match="role/side/service"):
        replace(battery, electrical_role=ROLE_CHARGING_INTERFACE)
    with pytest.raises(HarnessEndpointInventoryError, match="role/side/service"):
        replace(battery, side_class=SIDE_UNRESOLVED)
    with pytest.raises(HarnessEndpointInventoryError, match="role/side/service"):
        replace(battery, service_class=SERVICE_INTERNAL_FIXED)
    with pytest.raises(HarnessEndpointInventoryError, match="service class cannot imply"):
        replace(battery, service_geometry_status="SERVICE_PATH_RELEASED")
    for field, value in (
        ("connector_family", "UNSOURCED_CONNECTOR"),
        ("pinout", "1=VBAT,2=GND"),
        ("conductor_count", 2),
        ("voltage_rating_V", 5.0),
        ("current_rating_A", 1.0),
        ("ingress_rating", "IPX7"),
    ):
        with pytest.raises(HarnessEndpointInventoryError, match="must remain unresolved"):
            replace(battery, **{field: value})


def test_nonfinite_noncanonical_identity_frame_and_bool_coercion_fail_closed(inventory):
    battery = inventory.endpoints[0]
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(HarnessEndpointInventoryError, match="finite"):
            replace(battery, package_anchor_xyz_mm=(value, 0.0, -15.0))
    with pytest.raises(HarnessEndpointInventoryError, match="canonical mm precision"):
        replace(battery, package_anchor_xyz_mm=(1e-13, 0.0, -15.0))
    for field in ("mvp_required", "route_ready"):
        with pytest.raises(HarnessEndpointInventoryError, match="exact bool"):
            replace(battery, **{field: 0})
    duplicated_endpoints = (inventory.endpoints[0], inventory.endpoints[0], *inventory.endpoints[2:])
    with pytest.raises(HarnessEndpointInventoryError):
        replace(inventory, endpoints=duplicated_endpoints)
    duplicated_routes = (inventory.legacy_routes[0], inventory.legacy_routes[0], *inventory.legacy_routes[2:])
    with pytest.raises(HarnessEndpointInventoryError):
        replace(inventory, legacy_routes=duplicated_routes)
    with pytest.raises(HarnessEndpointInventoryError, match="canonical authority world frame"):
        replace(inventory, coordinate_frame_id="MASCK_ONE_NONCANONICAL_FRAME")


def test_source_and_donor_identity_spoofing_fail_closed(inventory):
    endpoint = inventory.endpoints[0]
    with pytest.raises(HarnessEndpointInventoryError, match="source blob"):
        replace(endpoint, source_git_blob_sha="0" * 40)
    with pytest.raises(HarnessEndpointInventoryError, match="main identity is stale"):
        replace(inventory, authored_against_main_sha="0" * 40)
    with pytest.raises(HarnessEndpointInventoryError, match="source graph identity changed"):
        replace(inventory, source_git_blob_identities=inventory.source_git_blob_identities[:-1])
    with pytest.raises(HarnessEndpointInventoryError, match="cannot be promoted"):
        replace(inventory.legacy_routes[0], current_disposition="CURRENT_ROUTE")


def test_inventory_manifest_is_deterministic_and_nested_mutation_revalidates(inventory):
    second = build_harness_endpoint_inventory()
    assert second.manifest() == inventory.manifest()
    assert second.inventory_sha256 == inventory.inventory_sha256
    assert len(inventory.inventory_sha256) == 64

    object.__setattr__(second.endpoints[0], "route_ready", True)
    with pytest.raises(HarnessEndpointInventoryError, match="route-ready"):
        second.endpoints[0].__post_init__()
