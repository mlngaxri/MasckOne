from __future__ import annotations

"""Guided preload spring V5 integration on terminal datum V5.

This module changes no spring, shoe, terminal, service-motion, or source geometry. It
moves the guided-spring integration path onto terminal datum V5 so the four source-
bound stations are first verified with the fail-closed collision-kernel V2 before
spring cassettes are generated from them.
"""

from collections.abc import Mapping
from dataclasses import dataclass
import math
from numbers import Real

from .structural_frame_actuator_reactions import REACTION_IDS
from .treatment_guided_preload_spring import (
    GuidedPreloadSpringStation,
    _INTERSECTION_TOLERANCE_MM3,
    build_guided_preload_spring_station,
)
from .treatment_terminal_datum_preload_v5 import (
    COLLISION_KERNEL,
    SOURCE_CELL6_HEAD_SHA,
    build_terminal_datum_preload_v5_architecture,
)

SCHEMA = "MASCK_ONE_TREATMENT_GUIDED_PRELOAD_SPRING_V5"
_CAPTURE_KEYS = frozenset(("X_root", "Z_root", "X_tip", "Z_tip"))


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
    try:
        actual = tuple(station.reaction_id for station in stations)
    except (AttributeError, TypeError) as exc:
        raise ValueError(f"guided spring V5 {stage} station identity is not readable") from exc
    expected = tuple(REACTION_IDS)
    if actual != expected:
        raise ValueError(
            f"guided spring V5 {stage} station identity drifted: "
            f"expected {expected!r}, got {actual!r}"
        )


def _require_capture_screen(station) -> None:
    """Fail closed on incomplete, mistyped, or non-finite geometric capture evidence."""
    reaction_id = getattr(station, "reaction_id", "<unreadable>")
    capture_screen = getattr(station, "capture_screen", None)
    if not isinstance(capture_screen, Mapping):
        raise ValueError(
            f"guided spring V5 {reaction_id} capture screen must be a mapping; "
            f"got {type(capture_screen).__name__}"
        )
    actual_keys = frozenset(capture_screen)
    if actual_keys != _CAPTURE_KEYS:
        raise ValueError(
            f"guided spring V5 {reaction_id} capture screen keys drifted: "
            f"expected {sorted(_CAPTURE_KEYS)!r}, got {sorted(actual_keys)!r}"
        )
    for name, value in capture_screen.items():
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(
                f"guided spring V5 {reaction_id} {name} capture evidence "
                f"must be a real numeric volume; got {value!r}"
            )
        numeric = float(value)
        if not math.isfinite(numeric) or numeric <= _INTERSECTION_TOLERANCE_MM3:
            raise ValueError(
                f"guided spring V5 {reaction_id} {name} capture evidence "
                f"must be finite and > {_INTERSECTION_TOLERANCE_MM3} mm^3; got {value!r}"
            )


def build_guided_preload_spring_v5_architecture(**terminal_kwargs) -> GuidedPreloadSpringV5Architecture:
    """Build all guided cassettes from terminal stations qualified by kernel V2."""
    terminal = build_terminal_datum_preload_v5_architecture(**terminal_kwargs)
    if terminal.source_cell6_head_sha != SOURCE_CELL6_HEAD_SHA:
        raise ValueError("guided spring V5 source binding drifted")

    _require_exact_station_identity(terminal.stations, stage="terminal input")
    generated: list[GuidedPreloadSpringStation] = []
    for terminal_station in terminal.stations:
        station = build_guided_preload_spring_station(terminal_station)
        reaction_id = getattr(station, "reaction_id", None)
        if reaction_id != terminal_station.reaction_id:
            raise ValueError(
                "guided spring V5 generated station identity drifted: "
                f"expected {terminal_station.reaction_id!r}, got {reaction_id!r}"
            )
        # Preserve specific capture diagnostics for duck-typed hostile fixtures, but
        # make the evidence boundary itself total: missing or malformed attributes
        # now fail closed with ValueError instead of leaking AttributeError/TypeError.
        _require_capture_screen(station)
        if not isinstance(station, GuidedPreloadSpringStation):
            raise ValueError(
                "guided spring V5 generator returned invalid station type: "
                f"expected GuidedPreloadSpringStation, got {type(station).__name__}"
            )
        generated.append(station)
    stations = tuple(generated)
    _require_exact_station_identity(stations, stage="generated output")
    return GuidedPreloadSpringV5Architecture(stations, terminal.source_cell6_head_sha)
