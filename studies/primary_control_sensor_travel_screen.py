from __future__ import annotations

"""Geometric travel screen for primary-control contactless sensing.

This study exists to prevent a quiet packaging error from being mistaken for a valid
sensor architecture. The legacy Hall PCB and its support sit axially behind the stem.
At the full 1.07 mm hard-stop travel, both occupy positive volume with the moving stem.

The side-sensing candidate moves the magnetic target and Hall pickup to the barrel
sidewall. It is only a packaging screen: magnetic transfer, monotonicity, calibration,
temperature behavior and supplier selection remain PHYSICAL/ELECTRICAL VALIDATION.
"""

from dataclasses import dataclass, asdict
import json
import math

import cadquery as cq

from masck_one import primary_control_haptic as v1

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_SENSOR_TRAVEL_SCREEN_V1"

LEGACY_HALL_PCB_X_MM = v1.HALL_PCB_X_MM
LEGACY_HALL_PCB_Y_MM = v1.HALL_PCB_Y_MM
LEGACY_HALL_PCB_Z_MM = v1.HALL_PCB_Z_MM
LEGACY_SUPPORT_X_MM = v1.HALL_PCB_X_MM + 1.2
LEGACY_SUPPORT_Y_MM = v1.SENSOR_BRACKET_THICKNESS_MM
LEGACY_SUPPORT_Z_MM = 1.55
LEGACY_SUPPORT_Y_OFFSET_MM = 3.15

SIDE_HALL_SENSOR_RADIAL_MM = 0.80
SIDE_HALL_SENSOR_TANGENTIAL_MM = 2.40
SIDE_HALL_SENSOR_AXIAL_MM = 2.40
SIDE_HALL_SENSOR_CENTER_RADIUS_MM = 4.72
SIDE_HALL_SENSOR_CENTER_FROM_REST_MM = 4.35

SIDE_MAGNET_CENTER_RADIUS_MM = 2.75
SIDE_MAGNET_CENTER_FROM_REST_MM = 4.35
SIDE_MAGNET_DIAMETER_MM = v1.MAGNET_DIAMETER_MM
SIDE_MAGNET_RADIAL_LENGTH_MM = v1.MAGNET_LENGTH_MM


class SensorTravelScreenError(ValueError):
    pass


def _box(x: float, y: float, z: float, center: tuple[float, float, float]) -> cq.Shape:
    shape = cq.Workplane("XY").box(x, y, z).translate(center).val()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise SensorTravelScreenError("expected one valid box")
    return shape


def _stem_at_travel(travel_mm: float) -> cq.Shape:
    z0 = -v1.STEM_LENGTH_MM - travel_mm
    shape = cq.Workplane("XY").workplane(offset=z0).circle(v1.STEM_DIAMETER_MM / 2.0).extrude(v1.STEM_LENGTH_MM).val()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise SensorTravelScreenError("expected one valid stem")
    return shape


def _intersection_mm3(a: cq.Shape, b: cq.Shape) -> float:
    common = a.intersect(b)
    if not common.isValid():
        raise SensorTravelScreenError("invalid intersection")
    return sum(float(s.Volume()) for s in common.Solids())


def _legacy_geometry() -> tuple[cq.Shape, cq.Shape]:
    magnet_z0 = -v1.STEM_LENGTH_MM + 0.20
    pcb_center_z = magnet_z0 - v1.HALL_NOMINAL_AIR_GAP_MM - v1.HALL_PCB_Z_MM / 2.0
    board = _box(
        LEGACY_HALL_PCB_X_MM,
        LEGACY_HALL_PCB_Y_MM,
        LEGACY_HALL_PCB_Z_MM,
        (0.0, 0.0, pcb_center_z),
    )
    support = _box(
        LEGACY_SUPPORT_X_MM,
        LEGACY_SUPPORT_Y_MM,
        LEGACY_SUPPORT_Z_MM,
        (0.0, LEGACY_SUPPORT_Y_OFFSET_MM, pcb_center_z),
    )
    return board, support


def _side_sensor_reference() -> cq.Shape:
    return _box(
        SIDE_HALL_SENSOR_RADIAL_MM,
        SIDE_HALL_SENSOR_TANGENTIAL_MM,
        SIDE_HALL_SENSOR_AXIAL_MM,
        (
            -SIDE_HALL_SENSOR_CENTER_RADIUS_MM,
            0.0,
            -SIDE_HALL_SENSOR_CENTER_FROM_REST_MM,
        ),
    )


@dataclass(frozen=True, slots=True)
class SensorTravelScreen:
    legacy_pcb_hard_stop_intersection_mm3: float
    legacy_support_hard_stop_intersection_mm3: float
    side_sensor_hard_stop_intersection_mm3: float
    side_sensor_min_radial_clearance_to_stem_mm: float

    def validate(self) -> "SensorTravelScreen":
        if self.legacy_pcb_hard_stop_intersection_mm3 <= 0.0:
            raise SensorTravelScreenError("legacy rear PCB collision was not reproduced")
        if self.legacy_support_hard_stop_intersection_mm3 <= 0.0:
            raise SensorTravelScreenError("legacy rear support collision was not reproduced")
        if self.side_sensor_hard_stop_intersection_mm3 != 0.0:
            raise SensorTravelScreenError("side Hall package still intersects moving stem")
        if self.side_sensor_min_radial_clearance_to_stem_mm <= 0.50:
            raise SensorTravelScreenError("side Hall package lacks conservative radial travel clearance")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "legacy_axial_hall": {
                "pcb_hard_stop_intersection_mm3": self.legacy_pcb_hard_stop_intersection_mm3,
                "support_hard_stop_intersection_mm3": self.legacy_support_hard_stop_intersection_mm3,
                "status": "REJECTED_FULL_TRAVEL_COLLISION",
            },
            "side_hall_candidate": {
                "sensor_radial_mm": SIDE_HALL_SENSOR_RADIAL_MM,
                "sensor_tangential_mm": SIDE_HALL_SENSOR_TANGENTIAL_MM,
                "sensor_axial_mm": SIDE_HALL_SENSOR_AXIAL_MM,
                "sensor_center_radius_mm": SIDE_HALL_SENSOR_CENTER_RADIUS_MM,
                "sensor_center_from_rest_mm": SIDE_HALL_SENSOR_CENTER_FROM_REST_MM,
                "hard_stop_intersection_mm3": self.side_sensor_hard_stop_intersection_mm3,
                "minimum_radial_clearance_to_stem_mm": self.side_sensor_min_radial_clearance_to_stem_mm,
                "packaging_status": "DIGITALLY_CLEAR_OF_STEM_FULL_TRAVEL",
            },
            "side_magnet_candidate": {
                "diameter_mm": SIDE_MAGNET_DIAMETER_MM,
                "radial_length_mm": SIDE_MAGNET_RADIAL_LENGTH_MM,
                "center_radius_mm": SIDE_MAGNET_CENTER_RADIUS_MM,
                "center_from_rest_mm": SIDE_MAGNET_CENTER_FROM_REST_MM,
            },
            "physical_validation_eligible": False,
            "physical_validation": (
                "OPEN_MAGNET_GRADE_FIELD_MAP_SENSOR_TRANSFER_MONOTONICITY_CALIBRATION_TEMPERATURE_"
                "TOLERANCE_FPC_RETENTION_EMC_LIFETIME_AND_WET_DRY_PACKAGE_INTEGRATION"
            ),
        }


def build_screen() -> SensorTravelScreen:
    hard_stem = _stem_at_travel(v1.HARD_STOP_MM)
    board, support = _legacy_geometry()
    side_sensor = _side_sensor_reference()

    legacy_board_overlap = _intersection_mm3(hard_stem, board)
    legacy_support_overlap = _intersection_mm3(hard_stem, support)
    side_overlap = _intersection_mm3(hard_stem, side_sensor)
    side_inner_radius = SIDE_HALL_SENSOR_CENTER_RADIUS_MM - SIDE_HALL_SENSOR_RADIAL_MM / 2.0
    radial_clearance = side_inner_radius - v1.STEM_DIAMETER_MM / 2.0

    return SensorTravelScreen(
        round(legacy_board_overlap, 9),
        round(legacy_support_overlap, 9),
        round(side_overlap, 9),
        round(radial_clearance, 9),
    ).validate()


if __name__ == "__main__":
    print(json.dumps(build_screen().manifest(), indent=2, sort_keys=True))
