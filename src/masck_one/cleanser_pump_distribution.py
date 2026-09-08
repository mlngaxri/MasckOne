"""Cell 10 source-bound CLEANSER pump package and cassette-to-pump route.

Digital geometry only. This module deliberately does not select a supplier pump, tubing,
connector, cleanser chemistry, flow, pressure, priming, leakage, or orientation capability.
The downstream manifold datum remains unresolved and is therefore not fabricated here.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .realized_cleanser_storage import CENTER_X_MM, BODY_X_MM, OUTLET_Y_MM, OUTLET_Z_MM

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
FLUID_IDENTITY = "CLEANSER"
SOURCE_MAIN_SHA = "a0ea51874d8967c512468932fac627e8bba5f95f"
DONOR_PR = 94
DONOR_HEAD_SHA = "1eb826fe859c6d5ee6dc0097aa58a67944bb530b"

PACKAGE_CENTER_WORLD_MM = (46.0, -10.0, 7.0)
PACKAGE_ENVELOPE_XYZ_MM = (30.0, 25.0, 8.2)
PUMP_INLET_WORLD_MM = (31.0, -7.0, 7.0)
PUMP_OUTLET_WORLD_MM = (31.0, -13.0, 7.0)
CASSETTE_OUTLET_WORLD_MM = (CENTER_X_MM + BODY_X_MM / 2.0, OUTLET_Y_MM, OUTLET_Z_MM)
LUMEN_DIAMETER_SEED_MM = 2.0
ROUTE_ID = "ROUTE-CLEANSER-STORAGE-TO-PUMP-CELL10"
PUMP_ID = "PUMP-STATION-CLEANSER-CELL10-DIMENSIONAL-SCREEN"
HYGIENE_CLASS = "WET_DRAINABLE"

# Deliberately routed outside the cassette service body before descending in Y.
# This is a geometric centerline seed, not selected tubing or a validated bend radius.
ROUTE_POINTS_WORLD_MM = (
    CASSETTE_OUTLET_WORLD_MM,
    (40.0, 65.0, 5.0),
    (40.0, -7.0, 5.0),
    (31.0, -7.0, 5.0),
    PUMP_INLET_WORLD_MM,
)


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> cq.Workplane:
    return cq.Workplane("XY").box(*size, centered=(True, True, True)).translate(center)


def _segment(a: tuple[float, float, float], b: tuple[float, float, float], diameter: float) -> cq.Workplane:
    ax, ay, az = a
    bx, by, bz = b
    dx, dy, dz = bx - ax, by - ay, bz - az
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length <= 0.0:
        raise ValueError("route segment must have positive length")
    direction = cq.Vector(dx / length, dy / length, dz / length)
    # Build on a plane normal to the segment, with a small overlap at each end so
    # successive orthogonal cylinders fuse into one connected route reference.
    plane = cq.Plane(origin=cq.Vector(ax, ay, az), normal=direction)
    return cq.Workplane(plane).circle(diameter / 2.0).extrude(length + 0.02, both=False)


def _route_solid() -> cq.Workplane:
    solid = _segment(ROUTE_POINTS_WORLD_MM[0], ROUTE_POINTS_WORLD_MM[1], LUMEN_DIAMETER_SEED_MM)
    for a, b in zip(ROUTE_POINTS_WORLD_MM[1:-1], ROUTE_POINTS_WORLD_MM[2:]):
        solid = solid.union(_segment(a, b, LUMEN_DIAMETER_SEED_MM))
    return solid


@dataclass(frozen=True, slots=True)
class CleanserPumpDistribution:
    package_reference_solid: cq.Workplane
    route_reference_solid: cq.Workplane

    @property
    def route_centerline_length_mm(self) -> float:
        return sum(math.dist(a, b) for a, b in zip(ROUTE_POINTS_WORLD_MM[:-1], ROUTE_POINTS_WORLD_MM[1:]))

    @property
    def neutral_geometric_lumen_volume_mL(self) -> float:
        return math.pi * (LUMEN_DIAMETER_SEED_MM / 2.0) ** 2 * self.route_centerline_length_mm / 1000.0

    def validate(self) -> None:
        if FLUID_IDENTITY != "CLEANSER":
            raise ValueError("cleanser pump route identity drifted")
        if ROUTE_POINTS_WORLD_MM[0] != CASSETTE_OUTLET_WORLD_MM or ROUTE_POINTS_WORLD_MM[-1] != PUMP_INLET_WORLD_MM:
            raise ValueError("cleanser source route endpoint binding drifted")
        for label, shape in (("pump package", self.package_reference_solid), ("source route", self.route_reference_solid)):
            if shape.solids().size() != 1 or not shape.val().isValid() or shape.val().Volume() <= 0.0:
                raise ValueError(f"{label} must be one valid positive B-rep")
        if not math.isclose(self.package_reference_solid.val().Volume(), 6150.0, abs_tol=1e-7):
            raise ValueError("cleanser pump screening package volume drifted")
        if self.route_centerline_length_mm <= 0.0 or self.neutral_geometric_lumen_volume_mL <= 0.0:
            raise ValueError("cleanser route geometric accounting must remain positive")

    def manifest(self) -> dict[str, object]:
        payload = {
            "schema": "MASCK_ONE_CELL10_CLEANSER_PUMP_DISTRIBUTION_V1",
            "world_frame_id": WORLD_FRAME_ID,
            "source_main_sha": SOURCE_MAIN_SHA,
            "donor_pr": DONOR_PR,
            "donor_head_sha": DONOR_HEAD_SHA,
            "fluid_identity": FLUID_IDENTITY,
            "pump": {
                "id": PUMP_ID,
                "center_world_mm": list(PACKAGE_CENTER_WORLD_MM),
                "envelope_xyz_mm": list(PACKAGE_ENVELOPE_XYZ_MM),
                "inlet_world_mm": list(PUMP_INLET_WORLD_MM),
                "outlet_world_mm": list(PUMP_OUTLET_WORLD_MM),
                "selection_status": "DIMENSIONAL_SCREEN_ONLY_NOT_SUPPLIER_SELECTED",
                "hygiene_class": HYGIENE_CLASS,
            },
            "source_route": {
                "route_id": ROUTE_ID,
                "points_world_mm": [list(p) for p in ROUTE_POINTS_WORLD_MM],
                "lumen_diameter_seed_mm": LUMEN_DIAMETER_SEED_MM,
                "centerline_length_mm": self.route_centerline_length_mm,
                "neutral_geometric_lumen_volume_mL": self.neutral_geometric_lumen_volume_mL,
                "status": "REALIZED_CENTERLINE_AND_BREP_REFERENCE_NOT_SELECTED_TUBING_OR_HYDRAULIC_EVIDENCE",
                "support_status": "BLOCKED_PENDING_RELEASED_FRAME_MEMBER_GEOMETRY",
            },
            "downstream": {
                "pump_outlet_world_mm": list(PUMP_OUTLET_WORLD_MM),
                "manifold_interface_id": "MANIFOLD-INLET-CLEANSER-I23",
                "status": "BLOCKED_PENDING_RELEASED_WORLD_COORDINATE_MANIFOLD_DATUM_AND_SIX_OUTLET_PATHS",
            },
            "evidence_firewall": "NO_CHEMISTRY_VISCOSITY_FLOW_PRESSURE_PRIMING_LEAKAGE_ORIENTATION_CONNECTOR_TUBING_OR_PUMP_SELECTION_CLAIMS",
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        payload["manifest_sha256"] = sha256(raw).hexdigest()
        return payload


def build_cleanser_pump_distribution() -> CleanserPumpDistribution:
    result = CleanserPumpDistribution(
        package_reference_solid=_box(PACKAGE_ENVELOPE_XYZ_MM, PACKAGE_CENTER_WORLD_MM),
        route_reference_solid=_route_solid(),
    )
    result.validate()
    return result
