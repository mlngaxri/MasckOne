from __future__ import annotations

import math

import pytest

from masck_one.structural_frame_actuator_reactions import REACTION_IDS
from masck_one.treatment_terminal_datum_preload_v2 import (
    TERMINAL_SERVICE_RETRACTION_PROBE_MM,
)
from masck_one.treatment_terminal_datum_preload_v4 import (
    SCHEMA,
    SERVICE_REMAINING_RETRACTION_MM,
    SERVICE_UNSEAT_MM,
    SOURCE_CELL6_HEAD_SHA,
    build_terminal_datum_preload_v4_architecture,
)


@pytest.fixture(scope="module")
def datum_v4():
    return build_terminal_datum_preload_v4_architecture()


def test_v4_builds_all_four_live_source_bound_terminal_stations(datum_v4):
    assert datum_v4.source_cell6_head_sha == SOURCE_CELL6_HEAD_SHA
    assert tuple(station.reaction_id for station in datum_v4.stations) == REACTION_IDS
    assert datum_v4.manifest()["schema"] == SCHEMA
    assert datum_v4.manifest()["supersedes"].endswith("V3")

    for station in datum_v4.stations:
        assert station.nominal_source_intersection_mm3 == 0.0
        assert min(station.master_probe_intersections_mm3) > 0.0
        assert station.service_source_intersection_mm3 == 0.0
        assert station.preload_couple_proxy_Nmm == 0.0


def test_v4_keeps_reference_motion_and_physical_validation_firewall(datum_v4):
    manifest = datum_v4.manifest()
    assert manifest["verification_revision"].startswith("BOOLEAN_FREE")
    assert manifest["physical_validation_eligible"] is False
    for station in manifest["stations"]:
        assert station["load_path"].startswith("RIGID_MASTER_DATUMS")
        assert station["physical_validation"].startswith("OPEN_")


def test_v4_service_sequence_unseats_before_low_drag_withdrawal(datum_v4):
    manifest = datum_v4.manifest()
    service = manifest["service_motion"]

    assert 0.0 < SERVICE_UNSEAT_MM < TERMINAL_SERVICE_RETRACTION_PROBE_MM
    assert math.isclose(
        SERVICE_UNSEAT_MM + SERVICE_REMAINING_RETRACTION_MM,
        TERMINAL_SERVICE_RETRACTION_PROBE_MM,
        rel_tol=0.0,
        abs_tol=1e-12,
    )
    assert service["sequence"] == [
        "CHECK_SEATED_CONTACT_SEPARATELY",
        "UNLOAD_AND_UNSEAT_PLUS_Y",
        "LOW_DRAG_WITHDRAWAL_PLUS_Y",
    ]
    assert service["unseat_mm"] == SERVICE_UNSEAT_MM
    assert service["full_reference_endpoint_mm"] == TERMINAL_SERVICE_RETRACTION_PROBE_MM
    assert service["tangent_t0_prism_sweep_prohibited"] is True
    assert service["collision_threshold_weakened"] is False
