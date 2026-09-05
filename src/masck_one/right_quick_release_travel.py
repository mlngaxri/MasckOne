from __future__ import annotations

"""Bounded kinematics for the Cell 3 right quick-release latch.

The latch geometry already contains a captive spool and guide cavity. This module turns
those solids into an explicit travel contract: the only admissible slider offsets are
between the two physical cavity-end stop faces, overtravel in either direction must
intersect positive guide material, and the released slider remains radially captive.

This is digital geometry/kinematics evidence only. It does not establish release force,
release time, wet usability, flexure fatigue, wear, comfort, or physical safety.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .right_quick_release_latch import (
    CAVITY_CENTER_X_MM,
    CAVITY_XYZ_MM,
    RELEASE_TRAVEL_MM,
    SPOOL_LEFT_LENGTH_MM,
    SPOOL_NECK_LENGTH_MM,
    SPOOL_RIGHT_LENGTH_MM,
    SPOOL_START_X_MM,
    WORLD_FRAME_ID,
    RightQuickReleaseLatch,
    build_right_quick_release_latch,
)

SCHEMA = "MASCK_ONE_CELL3_RIGHT_QUICK_RELEASE_TRAVEL_V1"
DIGITAL_ONLY = "DIGITAL_KINEMATIC_HARD_STOP_EVIDENCE_NOT_PHYSICAL_VALIDATION"
STOP_OVERTRAVEL_PROBE_MM = 0.05
KERNEL_ZERO_MM3 = 1e-8


class RightQuickReleaseTravelError(ValueError):
    pass


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise RightQuickReleaseTravelError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise RightQuickReleaseTravelError(f"{label} must be finite")
    return 0.0 if result == 0.0 else result


def _intersection_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise RightQuickReleaseTravelError(
            "intersection volume must be finite and nonnegative"
        )
    return 0.0 if value < KERNEL_ZERO_MM3 else value


def _bounds_mm(solid: cq.Workplane) -> list[float]:
    bb = solid.val().BoundingBox()
    return [
        float(bb.xmin),
        float(bb.xmax),
        float(bb.ymin),
        float(bb.ymax),
        float(bb.zmin),
        float(bb.zmax),
    ]


@dataclass(frozen=True, slots=True)
class SliderTravelState:
    state_id: str
    offset_mm: float
    solid: cq.Workplane

    def __post_init__(self) -> None:
        if type(self.state_id) is not str or not self.state_id.strip():
            raise RightQuickReleaseTravelError("state_id must be exact nonblank text")
        offset = _finite(self.offset_mm, "slider offset")
        if offset < 0.0 or offset > RELEASE_TRAVEL_MM:
            raise RightQuickReleaseTravelError(
                "slider offset lies outside the positive hard-stop travel interval"
            )
        shape = self.solid.val()
        if not shape.isValid() or float(shape.Volume()) <= 0.0:
            raise RightQuickReleaseTravelError(
                "bounded slider state must be a valid positive-volume solid"
            )
        if len(shape.Solids()) != 1:
            raise RightQuickReleaseTravelError(
                "bounded slider state must remain one connected solid"
            )

    def manifest(self) -> dict[str, object]:
        return {
            "state_id": self.state_id,
            "offset_mm": self.offset_mm,
            "solid_count": len(self.solid.val().Solids()),
            "bounds_mm": _bounds_mm(self.solid),
            "evidence_status": DIGITAL_ONLY,
        }


@dataclass(frozen=True, slots=True)
class CaptiveTravelContract:
    latch: RightQuickReleaseLatch
    inboard_stop_x_mm: float
    outboard_stop_x_mm: float
    spool_inboard_face_latched_x_mm: float
    spool_outboard_face_latched_x_mm: float
    overtravel_probe_mm: float
    inboard_overtravel_intersection_mm3: float
    outboard_overtravel_intersection_mm3: float
    captive_radial_worst_case_margin_mm: float
    hard_stop_wall_worst_case_margin_mm: float

    @property
    def spool_outboard_face_released_x_mm(self) -> float:
        return self.spool_outboard_face_latched_x_mm + RELEASE_TRAVEL_MM

    @property
    def package_sha256(self) -> str:
        return sha256(
            json.dumps(
                self.manifest(include_sha=False),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode()
        ).hexdigest()

    def state_at(self, offset_mm: object) -> SliderTravelState:
        offset = _finite(offset_mm, "slider offset")
        if offset < 0.0 or offset > RELEASE_TRAVEL_MM:
            raise RightQuickReleaseTravelError(
                f"slider offset must remain in [0, {RELEASE_TRAVEL_MM}] mm"
            )
        if math.isclose(offset, 0.0, rel_tol=0.0, abs_tol=1e-12):
            state_id = "LATCHED"
        elif math.isclose(
            offset, RELEASE_TRAVEL_MM, rel_tol=0.0, abs_tol=1e-12
        ):
            state_id = "RELEASED_RESET_REQUIRED"
        else:
            state_id = "RELEASE_TRAVEL_IN_PROGRESS"
        return SliderTravelState(
            state_id,
            offset,
            self.latch.slider_and_grip.solid.translate((offset, 0.0, 0.0)),
        )

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "source_latch_package_sha256": self.latch.package_sha256,
            "travel_limits": {
                "minimum_offset_mm": 0.0,
                "maximum_offset_mm": RELEASE_TRAVEL_MM,
                "release_direction_xyz": [1.0, 0.0, 0.0],
                "limit_source": "POSITIVE_GUIDE_CAVITY_END_WALLS",
                "out_of_range_state_rejected": True,
            },
            "inboard_hard_stop": {
                "guide_stop_face_x_mm": self.inboard_stop_x_mm,
                "spool_contact_face_x_mm_at_latched": (
                    self.spool_inboard_face_latched_x_mm
                ),
                "contact_at_latched_limit": math.isclose(
                    self.inboard_stop_x_mm,
                    self.spool_inboard_face_latched_x_mm,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                ),
                "negative_overtravel_probe_mm": self.overtravel_probe_mm,
                "positive_material_intersection_mm3": (
                    self.inboard_overtravel_intersection_mm3
                ),
            },
            "outboard_hard_stop": {
                "guide_stop_face_x_mm": self.outboard_stop_x_mm,
                "spool_contact_face_x_mm_at_released": (
                    self.spool_outboard_face_released_x_mm
                ),
                "contact_at_released_limit": math.isclose(
                    self.outboard_stop_x_mm,
                    self.spool_outboard_face_released_x_mm,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                ),
                "positive_overtravel_probe_mm": self.overtravel_probe_mm,
                "positive_material_intersection_mm3": (
                    self.outboard_overtravel_intersection_mm3
                ),
            },
            "continuous_axial_containment": {
                "proof_kind": "MONOTONIC_LINEAR_TRANSLATION_INTERVAL",
                "spool_inboard_face_expression": "SPOOL_XMIN_0_PLUS_OFFSET",
                "spool_outboard_face_expression": "SPOOL_XMAX_0_PLUS_OFFSET",
                "admissible_offset_interval_mm": [0.0, RELEASE_TRAVEL_MM],
                "cavity_interval_mm": [
                    self.inboard_stop_x_mm,
                    self.outboard_stop_x_mm,
                ],
                "endpoint_equalities_close_interval": True,
            },
            "captivity": {
                "no_loose_ejecting_slider_in_released_state": True,
                "worst_case_radial_capture_margin_mm": (
                    self.captive_radial_worst_case_margin_mm
                ),
                "worst_case_hard_stop_wall_margin_mm": (
                    self.hard_stop_wall_worst_case_margin_mm
                ),
                "capture_basis": (
                    "SPOOL_FLANGE_REMAINS_LARGER_THAN_EXIT_BORE_AND_END_WALLS_REMAIN_POSITIVE"
                ),
            },
            "states": [
                self.state_at(0.0).manifest(),
                self.state_at(RELEASE_TRAVEL_MM / 2.0).manifest(),
                self.state_at(RELEASE_TRAVEL_MM).manifest(),
            ],
            "physical_validation_eligible": False,
            "evidence_status": DIGITAL_ONLY,
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def build_captive_travel_contract(
    latch: RightQuickReleaseLatch | None = None,
) -> CaptiveTravelContract:
    latch = latch or build_right_quick_release_latch()

    cavity_xmin = CAVITY_CENTER_X_MM - CAVITY_XYZ_MM[0] / 2.0
    cavity_xmax = CAVITY_CENTER_X_MM + CAVITY_XYZ_MM[0] / 2.0
    spool_xmin = SPOOL_START_X_MM
    spool_xmax = (
        SPOOL_START_X_MM
        + SPOOL_LEFT_LENGTH_MM
        + SPOOL_NECK_LENGTH_MM
        + SPOOL_RIGHT_LENGTH_MM
    )

    if not math.isclose(spool_xmin, cavity_xmin, rel_tol=0.0, abs_tol=1e-12):
        raise RightQuickReleaseTravelError(
            "latched spool face must terminate exactly at the inboard hard stop"
        )
    if not math.isclose(
        spool_xmax + RELEASE_TRAVEL_MM,
        cavity_xmax,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise RightQuickReleaseTravelError(
            "released spool face must terminate exactly at the outboard hard stop"
        )

    tolerance_values = dict(latch.tolerance_values_mm)
    captive_margin = tolerance_values.get("LATCH_CAPTIVE_RADIAL_MARGIN")
    wall_margin = tolerance_values.get("LATCH_HARD_STOP_WALL_MARGIN")
    if captive_margin is None or captive_margin <= 0.0:
        raise RightQuickReleaseTravelError(
            "released slider cannot be called captive without positive worst-case radial margin"
        )
    if wall_margin is None or wall_margin <= 0.0:
        raise RightQuickReleaseTravelError(
            "hard stops require positive worst-case guide wall margin"
        )

    probe = STOP_OVERTRAVEL_PROBE_MM
    latched = latch.slider_and_grip.solid
    released = latched.translate((RELEASE_TRAVEL_MM, 0.0, 0.0))
    if _intersection_mm3(latched, latch.guide_capsule.solid) != 0.0:
        raise RightQuickReleaseTravelError(
            "latched state penetrates the captive guide at the inboard stop"
        )
    if _intersection_mm3(released, latch.guide_capsule.solid) != 0.0:
        raise RightQuickReleaseTravelError(
            "released state penetrates the captive guide at the outboard stop"
        )

    inboard_overtravel = latched.translate((-probe, 0.0, 0.0))
    outboard_overtravel = released.translate((probe, 0.0, 0.0))
    inboard_block = _intersection_mm3(inboard_overtravel, latch.guide_capsule.solid)
    outboard_block = _intersection_mm3(outboard_overtravel, latch.guide_capsule.solid)
    if inboard_block <= 0.0:
        raise RightQuickReleaseTravelError(
            "negative overtravel is not blocked by positive inboard guide material"
        )
    if outboard_block <= 0.0:
        raise RightQuickReleaseTravelError(
            "positive overtravel is not blocked by positive outboard guide material"
        )

    return CaptiveTravelContract(
        latch=latch,
        inboard_stop_x_mm=cavity_xmin,
        outboard_stop_x_mm=cavity_xmax,
        spool_inboard_face_latched_x_mm=spool_xmin,
        spool_outboard_face_latched_x_mm=spool_xmax,
        overtravel_probe_mm=probe,
        inboard_overtravel_intersection_mm3=inboard_block,
        outboard_overtravel_intersection_mm3=outboard_block,
        captive_radial_worst_case_margin_mm=float(captive_margin),
        hard_stop_wall_worst_case_margin_mm=float(wall_margin),
    )
