from __future__ import annotations

import pytest

from masck_one.structural_frame_actuator_reactions import REACTION_IDS
from masck_one.treatment_terminal_datum_preload_v3 import (
    SCHEMA,
    build_terminal_datum_preload_v3_architecture,
)


@pytest.fixture(scope="module")
def datum_v3():
    return build_terminal_datum_preload_v3_architecture()


def test_v3_builds_all_four_moment_balanced_terminal_stations(datum_v3):
    architecture = datum_v3
    assert tuple(station.reaction_id for station in architecture.stations) == REACTION_IDS
    assert architecture.manifest()["schema"] == SCHEMA
    for station in architecture.stations:
        row = station.manifest()
        alignment = row["contact_resultant_alignment"]
        assert alignment["X_pair_Z_offset_mm"] == 0.0
        assert alignment["Z_pair_X_offset_mm"] == 0.0
        assert alignment["preload_couple_proxy_Nmm"] == 0.0
        assert station.nominal_source_intersection_mm3 == 0.0
        assert min(station.master_probe_intersections_mm3) > 0.0
        assert station.service_source_intersection_mm3 == 0.0


def test_v3_preserves_rigid_working_load_path_and_physical_firewall(datum_v3):
    manifest = datum_v3.manifest()
    assert manifest["selected_v1_direction"].startswith("MOMENT_BALANCED")
    assert manifest["supersedes"].endswith("V2")
    assert manifest["physical_validation_eligible"] is False
    for station in manifest["stations"]:
        assert station["load_path"].startswith("RIGID_MASTER_DATUMS")
        assert station["physical_validation"].startswith("OPEN_")
