"""Cell 12 battery disconnect mating and service geometry.

Digital packaging geometry only. This module defines a deterministic dry-side
mating datum, keyed connector reservation, strain-relief support reservation and
non-teleporting disconnect sweep. It does not select a connector or establish
current, voltage, ingress, retention-force, cycle-life or electrical-safety ratings.

The disconnect geometry was carried forward from an older donor head but is now
revalidated on the current released-main owner lineage. Donor provenance and current
release ancestry are therefore recorded separately rather than presenting the donor
head as current main.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

SCHEMA = "MASCK_ONE_CELL12_BATTERY_DISCONNECT_INTERFACE_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_DONOR_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
SOURCE_MAIN_SHA = "ac59fcd59f50b019cb972bfc526c2daea784bd17"

# Kept wholly inside the current 48 x 66 x 22 mm dry-bay package.
MATING_DATUM_WORLD_MM = (17.0, -20.0, -39.0)
MATING_AXIS_WORLD = (0.0, 1.0, 0.0)
CONNECTOR_RESERVATION_MM = (8.0, 10.0, 5.0)
KEY_RIB_MM = (1.2, 4.0, 1.0)
STRAIN_RELIEF_RESERVATION_MM = (10.0, 7.0, 6.0)
DISCONNECT_TRAVEL_MM = 12.0


class DrySideDisconnectError(ValueError):
    pass


def _box(size, center):
    return cq.Workplane("XY").box(*size).translate(center)


def _geometry(shape):
    solid = shape.val()
    if not solid.isValid() or len(solid.Solids()) != 1:
        raise DrySideDisconnectError("disconnect geometry must be one valid B-rep solid")
    volume = float(solid.Volume())
    if not math.isfinite(volume) or volume <= 0.0:
        raise DrySideDisconnectError("disconnect geometry must have finite positive volume")
    bb = solid.BoundingBox()
    return {
        "bounds_world_mm": [
            float(bb.xmin), float(bb.xmax), float(bb.ymin), float(bb.ymax),
            float(bb.zmin), float(bb.zmax),
        ],
        "volume_mm3": volume,
    }


@dataclass(frozen=True, slots=True)
class BatteryDisconnectInterface:
    connector_reservation: cq.Workplane
    key_reservation: cq.Workplane
    strain_relief_reservation: cq.Workplane
    disconnect_service_sweep: cq.Workplane

    def validate(self):
        for shape in (
            self.connector_reservation,
            self.key_reservation,
            self.strain_relief_reservation,
            self.disconnect_service_sweep,
        ):
            _geometry(shape)
        bb = self.disconnect_service_sweep.val().BoundingBox()
        if (
            bb.ymax > 33.0 + 1e-7
            or bb.ymin < -33.0 - 1e-7
            or bb.xmin < -24.0 - 1e-7
            or bb.xmax > 24.0 + 1e-7
            or bb.zmin < -47.0 - 1e-7
            or bb.zmax > -25.0 + 1e-7
        ):
            raise DrySideDisconnectError(
                "disconnect service sweep escapes current dry-bay package"
            )
        if float(
            self.connector_reservation.val().cut(self.disconnect_service_sweep.val()).Volume()
        ) > 1e-7:
            raise DrySideDisconnectError(
                "disconnect sweep does not contain installed connector reservation"
            )
        return self

    def manifest(self):
        self.validate()
        payload = {
            "schema": SCHEMA,
            "source_main_sha": SOURCE_MAIN_SHA,
            "source_donor_sha": SOURCE_DONOR_SHA,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "mating_datum_world_mm": list(MATING_DATUM_WORLD_MM),
            "mating_axis_world": list(MATING_AXIS_WORLD),
            "disconnect_travel_mm": DISCONNECT_TRAVEL_MM,
            "geometry": {
                "connector_reservation": _geometry(self.connector_reservation),
                "key_reservation": _geometry(self.key_reservation),
                "strain_relief_reservation": _geometry(self.strain_relief_reservation),
                "disconnect_service_sweep": _geometry(self.disconnect_service_sweep),
            },
            "interface_status": "GEOMETRIC_MATING_AND_SERVICE_DATUM_REALIZED_CONNECTOR_UNSELECTED",
            "electrical_ratings_selected": False,
            "connector_selected": False,
            "retention_force_validated": False,
            "ingress_validated": False,
            "physical_service_validated": False,
            "evidence_status": "DIGITAL_PACKAGING_AND_SERVICE_GEOMETRY_ONLY",
        }
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_battery_disconnect_interface():
    x, y, z = MATING_DATUM_WORLD_MM
    connector = _box(
        CONNECTOR_RESERVATION_MM,
        (x, y + CONNECTOR_RESERVATION_MM[1] / 2.0, z),
    )
    key = _box(
        KEY_RIB_MM,
        (
            x + CONNECTOR_RESERVATION_MM[0] / 2.0 - KEY_RIB_MM[0] / 2.0,
            y + 2.0,
            z + CONNECTOR_RESERVATION_MM[2] / 2.0 + KEY_RIB_MM[2] / 2.0,
        ),
    )
    strain = _box(
        STRAIN_RELIEF_RESERVATION_MM,
        (x, y + CONNECTOR_RESERVATION_MM[1] + STRAIN_RELIEF_RESERVATION_MM[1] / 2.0, z),
    )
    sweep = _box(
        (CONNECTOR_RESERVATION_MM[0], CONNECTOR_RESERVATION_MM[1] + DISCONNECT_TRAVEL_MM, CONNECTOR_RESERVATION_MM[2]),
        (x, y + (CONNECTOR_RESERVATION_MM[1] + DISCONNECT_TRAVEL_MM) / 2.0, z),
    )
    return BatteryDisconnectInterface(connector, key, strain, sweep).validate()