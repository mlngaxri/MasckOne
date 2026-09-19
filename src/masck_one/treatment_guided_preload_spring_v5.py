from __future__ import annotations

"""Guided preload spring V5 integration on terminal datum V5.

This module changes no spring, shoe, terminal, service-motion, or source geometry. It
moves the guided-spring integration path onto terminal datum V5 so the four source-
bound stations are first verified with the fail-closed collision-kernel V2 before
spring cassettes are generated from them.
"""

from dataclasses import dataclass

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


def build_guided_preload_spring_v5_architecture(**terminal_kwargs) -> GuidedPreloadSpringV5Architecture:
    """Build all guided cassettes from terminal stations qualified by kernel V2."""
    terminal = build_terminal_datum_preload_v5_architecture(**terminal_kwargs)
    if terminal.source_cell6_head_sha != SOURCE_CELL6_HEAD_SHA:
        raise ValueError("guided spring V5 source binding drifted")
    stations = tuple(build_guided_preload_spring_station(station) for station in terminal.stations)
    if len(stations) != len(terminal.stations):
        raise ValueError("guided spring V5 station count drifted")
    return GuidedPreloadSpringV5Architecture(stations, terminal.source_cell6_head_sha)
