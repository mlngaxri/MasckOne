"""Executable lower-face and chin-field industrial-design gates.

These checks prevent a mechanically valid mouth/chin region from collapsing into a
heavy lower bumper, pointed chin tab, or asymmetric jaw transition. Measurements
must come from stable named CAD evidence, not kernel face or edge indices.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class ChinFieldLimits:
    min_mouth_to_chin_blend_run_mm: float = 10.0
    max_chin_projection_above_lower_field_mm: float = 2.0
    min_jaw_transition_run_mm: float = 12.0
    max_jaw_transition_depth_mm: float = 3.0
    max_jaw_run_asymmetry_mm: float = 1.5
    max_jaw_depth_asymmetry_mm: float = 0.75
    max_lower_edge_height_asymmetry_mm: float = 1.0


REQUIRED_MEASUREMENTS = (
    "ID_MOUTH_TO_CHIN_BLEND_RUN",
    "ID_CHIN_PROJECTION_ABOVE_LOWER_FIELD",
    "ID_JAW_TRANSITION_RUN_L",
    "ID_JAW_TRANSITION_RUN_R",
    "ID_JAW_TRANSITION_DEPTH_L",
    "ID_JAW_TRANSITION_DEPTH_R",
    "ID_LOWER_EDGE_HEIGHT_L",
    "ID_LOWER_EDGE_HEIGHT_R",
)


class ChinFieldContractError(ValueError):
    """Raised when lower-face geometry violates the chin-field contract."""


def _nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise ChinFieldContractError(f"{name} must be finite")
    if value < 0:
        raise ChinFieldContractError(f"{name} must be >= 0")
    return value


def validate_chin_field(values: Mapping[str, float], limits: ChinFieldLimits = ChinFieldLimits()) -> None:
    """Fail closed on abrupt, heavy or asymmetric lower-face geometry."""
    missing = sorted(set(REQUIRED_MEASUREMENTS) - set(values))
    if missing:
        raise ChinFieldContractError("missing stable chin-field measurements: " + ", ".join(missing))
    v = {name: _nonnegative(name, values[name]) for name in REQUIRED_MEASUREMENTS}

    if v["ID_MOUTH_TO_CHIN_BLEND_RUN"] < limits.min_mouth_to_chin_blend_run_mm:
        raise ChinFieldContractError("mouth-to-chin transition is too abrupt and reads as a lower bumper")
    if v["ID_CHIN_PROJECTION_ABOVE_LOWER_FIELD"] > limits.max_chin_projection_above_lower_field_mm:
        raise ChinFieldContractError("chin projects as a separate tab rather than continuing the lower facial field")

    for side in ("L", "R"):
        if v[f"ID_JAW_TRANSITION_RUN_{side}"] < limits.min_jaw_transition_run_mm:
            raise ChinFieldContractError(f"{side} jaw transition is too short for a broad lower-face blend")
        if v[f"ID_JAW_TRANSITION_DEPTH_{side}"] > limits.max_jaw_transition_depth_mm:
            raise ChinFieldContractError(f"{side} jaw transition has excessive local depth and reads as a lower pod")

    if abs(v["ID_JAW_TRANSITION_RUN_L"] - v["ID_JAW_TRANSITION_RUN_R"]) > limits.max_jaw_run_asymmetry_mm:
        raise ChinFieldContractError("jaw transition run asymmetry creates unintended lower-face expression")
    if abs(v["ID_JAW_TRANSITION_DEPTH_L"] - v["ID_JAW_TRANSITION_DEPTH_R"]) > limits.max_jaw_depth_asymmetry_mm:
        raise ChinFieldContractError("jaw transition depth asymmetry creates unintended lower-face visual weight")
    if abs(v["ID_LOWER_EDGE_HEIGHT_L"] - v["ID_LOWER_EDGE_HEIGHT_R"]) > limits.max_lower_edge_height_asymmetry_mm:
        raise ChinFieldContractError("lower edge height asymmetry creates a visibly tilted chin silhouette")
