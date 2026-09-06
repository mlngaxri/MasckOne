from dataclasses import replace

import pytest

from masck_one.harness_endpoint_inventory import (
    AUTHORITY_BLOB_SHA,
    ENDPOINT_IDS,
    EP_BATTERY,
    EP_COOL_OPTIONAL,
    EP_PCB,
    EVIDENCE_STATUS,
    LEGACY_DONOR_FILE_BLOB_SHA,
    LEGACY_DONOR_HEAD_SHA,
    LEGACY_ROUTE_DISPOSITION,
    LEGACY_ROUTE_IDS,
    OPTIONAL_UNRESOLVED,
    SCHEMA,
    SOURCE_GIT_BLOB_IDENTITIES,
    SOURCE_MAIN_SHA,
    WORLD_FRAME_ID,
    HarnessEndpointInventoryError,
    build_harness_endpoint_inventory,
)


@pytest.fixture(scope="module")
def inventory():
    return build_harness_endpoint_inventory()


def test_inventory_binds_current_main_authority_and_source_graph(inventory):
    assert inventory.schema == SCHEMA
    assert inventory.authored_against_main_sha == SOURCE_MAIN_SHA
    assert inventory.authority_blob_sha == AUTHORITY_BLOB_SHA
    assert inventory.coordinate_frame_id == WORLD_FRAME_ID
    assert inventory.source_git_blob_identities == SOURCE_GIT_BLOB_IDENTITIES
    assert tuple(endpoint.endpoint_id for endpoint in inventory.endpoints) == ENDPOINT_IDS
    assert tuple(route.route_id for route in inventory.legacy_routes) == LEGACY_ROUTE_IDS
    assert len(inventory.endpoints) == 14
    assert len(inventory.legacy_routes) == 13


def test_released_package_anchors_are_not_spoofed_as_electrical_datums(inventory):
    by_id = {endpoint.endpoint_id: endpoint for endpoint in inventory.endpoints}
    battery = by_id[EP_BATTERY]
    assert battery.package_anchor_xyz_mm == (0.0, 0.0, -15.0)
    assert battery.electrical_interface_datum_xyz_mm is None
    assert battery.route_ready is False
    assert by_id[EP_PCB].package_anchor_xyz_mm is None
    assert by_id[EP_PCB].electrical_interface_datum_xyz_mm is None
    actuator_anchors = tuple(
        endpoint.package_anchor_xyz_mm
        for endpoint in inventory.endpoints
        if "ACTUATOR" in endpoint.endpoint_id
    )
    assert actuator_anchors == (
        (-48.0, 52.0, 2.0),
        (48.0, 52.0, 2.0),
        (-50.0, -38.0, 2.0),
        (50.0, -38.0, 2.0),
    )
    assert all(endpoint.electrical_interface_datum_xyz_mm is None for endpoint in inventory.endpoints)


def test_current_pump_hmi_warm_cool_and_charging_endpoints_remain_honestly_unready(inventory):
    by_id = {endpoint.endpoint_id: endpoint for endpoint in inventory.endpoints}
    for endpoint_id in (
        "MASCK_ONE-ELEC-EP-PUMP-WATER",
        "MASCK_ONE-ELEC-EP-PUMP-CLEANSER",
        "MASCK_ONE-ELEC-EP-PUMP-WASTE",
        "MASCK_ONE-ELEC-EP-HMI",
        "MASCK_ONE-ELEC-EP-WARM-LEFT",
        "MASCK_ONE-ELEC-EP-WARM-RIGHT",
        "MASCK_ONE-ELEC-EP-CHARGING",
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


def test_nonfinite_identity_duplication_and_bool_coercion_fail_closed(inventory):
    endpoint = inventory.endpoints[2]
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(HarnessEndpointInventoryError, match="finite"):
            replace(endpoint, package_anchor_xyz_mm=(value, 0.0, 0.0))
    for field in ("mvp_required", "route_ready"):
        with pytest.raises(HarnessEndpointInventoryError, match="exact bool"):
            replace(endpoint, **{field: 0})
    duplicated_endpoints = (inventory.endpoints[0], inventory.endpoints[0], *inventory.endpoints[2:])
    with pytest.raises(HarnessEndpointInventoryError):
        replace(inventory, endpoints=duplicated_endpoints)
    duplicated_routes = (inventory.legacy_routes[0], inventory.legacy_routes[0], *inventory.legacy_routes[2:])
    with pytest.raises(HarnessEndpointInventoryError):
        replace(inventory, legacy_routes=duplicated_routes)


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
