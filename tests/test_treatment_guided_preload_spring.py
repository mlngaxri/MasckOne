from __future__ import annotations

import pytest

from masck_one.treatment_guided_preload_spring import build_guided_preload_spring_station
from masck_one.treatment_terminal_datum_preload_v3 import build_terminal_datum_preload_v3_architecture


@pytest.fixture(scope="module")
def guided_stations():
    architecture = build_terminal_datum_preload_v3_architecture()
    return tuple(build_guided_preload_spring_station(datum) for datum in architecture.stations)


def test_guided_spring_cassettes_are_captive_and_separate_free_from_installed_state(guided_stations):
    for spring in guided_stations:
        assert min(spring.capture_screen.values()) > 0.0
        installed = dict(spring.installed_springs)
        free = dict(spring.free_springs)
        assert installed.keys() != free.keys()
        assert len(installed) == 2
        assert len(free) == 2
        assert spring.manifest()["manufacturing_state"].startswith("FREE_SPRING_GEOMETRY")
        for _name, shape in spring.root_polymer + spring.installed_shoes + spring.free_shoes:
            assert shape.isValid()
            assert shape.Solids()


def test_guided_spring_manifest_keeps_physical_validation_open(guided_stations):
    row = guided_stations[0].manifest()
    assert row["architecture"].startswith("AXIS_SEPARATED_TWO_LEAF_PARALLELOGRAM")
    assert row["guide_pair_separation_mm"] > 0.0
    assert row["physical_validation"].startswith("OPEN_")
