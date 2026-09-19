from __future__ import annotations

"""Guided preload spring V5 integration on terminal datum V5.

This module changes no spring, shoe, terminal, service-motion, or source geometry. It
moves the guided-spring integration path onto terminal datum V5 so the four source-
bound stations are first verified with the fail-closed collision-kernel V2 before
spring cassettes are generated from them.
"""

from dataclasses import dataclass

from .structural_frame_actuator_reactions import REACTION_IDS
from .treatment_guided_preload_spring import (
    GuidedPreloadSpringStation,
    build_guided_preload_spring_station,
)
from .treatment_terminal_datum_preload_v5 import (
    COLLISION_KERNEL,
    SOURCE_CELL6_HEAD_SHA,
    build_terminal_datum_preload_v5_architecture,
)

SCHEMA = "MASCK_ONE_TREATMENT_GUIDED_PRELOAD_SPRING_V5"


@dataclass(frozen=True, slots=True)
class GuidedPreloadSpringV5Architecture:
    stations: tuple[GuidedPreloadSpringStation, ...]
    source_cell6_head_sha: str

    def manifest(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "source_cell6_head_sha": self.source_cell6_head_sha,
            "collision_kernel": COLLISION_KERNEL,
            "station_ids": [station.reaction_id for station in self.stations],
            "physical_geometry_changed_from_guided_v4": False,
            "collision_threshold_weakened": False,
            "physical_validation_eligible": False,
        }


def _require_exact_station_identity(stations, *, stage: str) -> None:
    """Reject missing, duplicate, unexpected, or reordered four-zone station sets."""
    actual = tuple(station.reaction_id for station in stations)
    expected = tuple(REACTION_IDS)
    if actual != expected:
        raise ValueError(
            f"guided spring V5 {stage} station identity drifted: "
            f"expected {expected!r}, got {actual!r}"
        )


def build_guided_preload_spring_v5_architecture(**terminal_kwargs) -> GuidedPreloadSpringV5Architecture:
    """Build all guided cassettes from terminal stations qualified by kernel V2."""
    terminal = build_terminal_datum_preload_v5_architecture(**terminal_kwargs)
    if terminal.source_cell6_head_sha != SOURCE_CELL6_HEAD_SHA:
        raise ValueError("guided spring V5 source binding drifted")

    # Count-only validation can admit a duplicated station while silently omitting
    # another reaction zone. Require the exact structural reaction identity and order
    # before any spring cassette is generated, then recheck the generated outputs.
    _require_exact_station_identity(terminal.stations, stage="terminal input")
    stations = tuple(build_guided_preload_spring_station(station) for station in terminal.stations)
    _require_exact_station_identity(stations, stage="generated output")
    return GuidedPreloadSpringV5Architecture(stations, terminal.source_cell6_head_sha)
