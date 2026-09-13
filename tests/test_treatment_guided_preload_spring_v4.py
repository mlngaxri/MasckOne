from __future__ import annotations

import pytest

from masck_one.treatment_guided_preload_spring import build_guided_preload_spring_station
from masck_one.treatment_terminal_datum_preload_v4 import build_terminal_datum_preload_v4_architecture


@pytest.fixture(scope="module")
def guided_stations_v4():
    architecture = build_terminal_datum_preload_v4_architecture()
    return tuple(build_guided_preload_spring_station(station) for station in architecture.stations)


def test_guided_spring_v4_cassettes_are_captive_and_separate_free_from_installed_state(guided_stations_v4):
    assert len(guided_stations_v4) == 4
    for guided in guided_stations_v4:
        assert min(guided.capture_screen.values()) > 0.0
        assert dict(guided.installed_springs)["terminal_x_spring_installed"].isValid()
        assert dict(guided.installed_springs)["terminal_z_spring_installed"].isValid()
        assert dict(guided.free_springs)["terminal_x_spring_free"].isValid()
        assert dict(guided.free_springs)["terminal_z_spring_free"].isValid()


def test_guided_spring_v4_manifest_keeps_physical_validation_open(guided_stations_v4):
    for guided in guided_stations_v4:
        manifest = guided.manifest()
        assert manifest["architecture"].startswith("AXIS_SEPARATED_TWO_LEAF_PARALLELOGRAM")
        assert manifest["manufacturing_state"].startswith("FREE_SPRING_GEOMETRY")
        assert manifest["physical_validation"].startswith("OPEN_")
