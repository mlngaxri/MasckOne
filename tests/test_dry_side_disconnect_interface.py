from dataclasses import replace

import pytest

from masck_one.dry_side_disconnect_interface import (
    DISCONNECT_TRAVEL_MM,
    MATING_AXIS_WORLD,
    MATING_DATUM_WORLD_MM,
    DrySideDisconnectError,
    build_battery_disconnect_interface,
)


def test_disconnect_interface_is_valid_and_deterministic():
    first = build_battery_disconnect_interface()
    second = build_battery_disconnect_interface()
    assert first.manifest() == second.manifest()
    assert first.manifest()["mating_datum_world_mm"] == list(MATING_DATUM_WORLD_MM)
    assert first.manifest()["mating_axis_world"] == list(MATING_AXIS_WORLD)
    assert first.manifest()["disconnect_travel_mm"] == DISCONNECT_TRAVEL_MM


def test_disconnect_sweep_contains_installed_connector_and_stays_in_dry_bay():
    interface = build_battery_disconnect_interface()
    assert interface.connector_reservation.val().cut(interface.disconnect_service_sweep.val()).Volume() < 1e-7
    bb = interface.disconnect_service_sweep.val().BoundingBox()
    assert -24.0 <= bb.xmin <= bb.xmax <= 24.0
    assert -33.0 <= bb.ymin <= bb.ymax <= 33.0
    assert -47.0 <= bb.zmin <= bb.zmax <= -25.0


def test_disconnect_manifest_cannot_promote_unselected_electrical_evidence():
    manifest = build_battery_disconnect_interface().manifest()
    assert manifest["connector_selected"] is False
    assert manifest["electrical_ratings_selected"] is False
    assert manifest["retention_force_validated"] is False
    assert manifest["ingress_validated"] is False
    assert manifest["physical_service_validated"] is False
    assert manifest["evidence_status"] == "DIGITAL_PACKAGING_AND_SERVICE_GEOMETRY_ONLY"


def test_hostile_service_sweep_escape_is_rejected():
    interface = build_battery_disconnect_interface()
    escaped = interface.disconnect_service_sweep.translate((0, 30, 0))
    with pytest.raises(DrySideDisconnectError, match="escapes current dry-bay package"):
        replace(interface, disconnect_service_sweep=escaped).validate()


def test_hostile_disconnected_sweep_is_rejected():
    interface = build_battery_disconnect_interface()
    displaced = interface.disconnect_service_sweep.translate((-20, 0, 0))
    with pytest.raises(DrySideDisconnectError, match="does not contain installed connector reservation"):
        replace(interface, disconnect_service_sweep=displaced).validate()
