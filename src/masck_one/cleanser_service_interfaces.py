"""Realized cleanser fill, vent, pickup and purge-service geometry.

This successor layer consumes the exact Cell 4 cleanser-cassette realization and closes
remaining digital interfaces without selecting cleanser chemistry, viscosity limits,
seal materials, vent barrier hardware, fittings, or physical performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

import cadquery as cq

from .authority import Authority
from .cleanser_storage import PORT_IDS, PORT_OUTLET
from .realized_cleanser_storage import (
    AUTHORED_AGAINST_MAIN_SHA,
    BODY_X_MM,
    BODY_Z_MM,
    CENTER_X_MM,
    CENTER_Y_MM,
    CENTER_Z_MM,
    FLUID_IDENTITY,
    OUTLET_BORE_DIAMETER_MM,
    OUTLET_Y_MM,
    OUTLET_Z_MM,
    PURGE_BORE_DIAMETER_MM,
    PURGE_X_MM,
    PURGE_Y_MM,
    REFILL_BORE_DIAMETER_MM,
    REFILL_X_MM,
    REFILL_Y_MM,
    RealizedCleanserStorage,
    build_realized_cleanser_storage,
)

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_STORAGE_SCHEMA = "MASCK_ONE_CELL4_REALIZED_CLEANSER_STORAGE_V1"
SOURCE_STORAGE_BLOB_SHA = "7c7eca7a12b14526946f759740161c33c13e5cb4"
SCHEMA = "MASCK_ONE_CELL4_CLEANSER_SERVICE_INTERFACES_V1"
GEOMETRY_STATUS = "CELL4_PROVISIONAL_REALIZED_CAD_NOT_SUPPLIER_SELECTED"
EVIDENCE_STATUS = "DIGITAL_GEOMETRY_ONLY_NOT_VISCOSITY_SEAL_VENT_PICKUP_PURGE_OR_HYGIENE_PHYSICAL_EVIDENCE"

# Hidden posterior refill/purge closure. A separate transverse key blocks posterior
# withdrawal. Every dimension below is a provisional CAD seed, not supplier data.
SERVICE_CLOSURE_X_MM = 11.0
SERVICE_CLOSURE_Y_MM = 12.0
SERVICE_CLOSURE_Z_MM = 1.4
SERVICE_CLOSURE_CENTER_X_MM = 26.5
SERVICE_CLOSURE_CENTER_Y_MM = 72.0
SERVICE_CLOSURE_CENTER_Z_MM = -1.0
REFILL_PLUG_DIAMETER_MM = 3.6
PURGE_PLUG_DIAMETER_MM = 1.6
PLUG_Z_START_MM = -0.4
PLUG_Z_LENGTH_MM = 2.9

FILL_SEAL_GROOVE_OUTER_DIAMETER_MM = 5.6
FILL_SEAL_GROOVE_INNER_DIAMETER_MM = 4.3
PURGE_SEAL_GROOVE_OUTER_DIAMETER_MM = 3.5
PURGE_SEAL_GROOVE_INNER_DIAMETER_MM = 2.25
SEAL_GROOVE_DEPTH_MM = 0.25
SEAL_REFERENCE_AXIAL_MM = 0.35

# The closure key sits below the bridge through one connected closure lug and two
# body-integrated ears. This avoids cutting the thin bridge into separate pieces.
SERVICE_CLOSURE_LUG_X_MM = 4.0
SERVICE_CLOSURE_LUG_Y_MM = 3.0
SERVICE_CLOSURE_LUG_Z_MM = 2.4
SERVICE_CLOSURE_LUG_CENTER_X_MM = SERVICE_CLOSURE_CENTER_X_MM
SERVICE_CLOSURE_LUG_CENTER_Y_MM = SERVICE_CLOSURE_CENTER_Y_MM
SERVICE_CLOSURE_LUG_CENTER_Z_MM = -2.2
SERVICE_EAR_X_MM = 2.0
SERVICE_EAR_Y_MM = 3.0
SERVICE_EAR_Z_MM = 5.0
SERVICE_EAR_LEFT_X_MM = 20.0
SERVICE_EAR_RIGHT_X_MM = 33.0
SERVICE_EAR_CENTER_Y_MM = SERVICE_CLOSURE_CENTER_Y_MM
SERVICE_EAR_CENTER_Z_MM = -1.0
SERVICE_KEY_Y_MM = SERVICE_CLOSURE_CENTER_Y_MM
SERVICE_KEY_Z_MM = -2.6
SERVICE_KEY_BORE_DIAMETER_MM = 1.5
SERVICE_KEY_STEM_DIAMETER_MM = 1.2
SERVICE_KEY_HEAD_DIAMETER_MM = 3.0
SERVICE_KEY_X_MIN_MM = 18.5
SERVICE_KEY_X_MAX_MM = 35.0
SERVICE_KEY_HEAD_X_MIN_MM = 34.4
SERVICE_KEY_HEAD_X_MAX_MM = 36.4
SERVICE_CLOSURE_KEY_BORE_X_MIN_MM = 24.0
SERVICE_CLOSURE_KEY_BORE_X_MAX_MM = 29.0
SERVICE_KEY_WITHDRAWAL_TRAVEL_MM = 12.0
SERVICE_CLOSURE_WITHDRAWAL_TRAVEL_MM = 6.0

# Vent is a headspace feature, not a fourth controlled liquid port. The external
# barrier remains an unresolved package reservation.
VENT_FEATURE_ID = "MASCK_ONE-CLEANSER-HEADSPACE-VENT-PRIMARY"
VENT_X_MM = 34.0
VENT_Y_MM = 79.5
VENT_BORE_DIAMETER_MM = 1.2
VENT_SEAT_OUTER_DIAMETER_MM = 3.6
VENT_SEAT_PROJECTION_MM = 1.0
VENT_BARRIER_RESERVATION_DIAMETER_MM = 4.0
VENT_BARRIER_RESERVATION_DEPTH_MM = 1.5

# Robust single-axis pickup tube. It reaches from the cavity toward the existing
# dedicated lateral outlet. Its lumen equals the already-realized outlet bore. This is
# geometry only and creates no viscosity, priming, drawdown, pressure-drop or flow claim.
PICKUP_FEATURE_ID = "MASCK_ONE-CLEANSER-PICKUP-TUBE-PRIMARY"
PICKUP_TUBE_OUTER_DIAMETER_MM = 2.8
PICKUP_LUMEN_DIAMETER_MM = OUTLET_BORE_DIAMETER_MM
PICKUP_TIP_X_MM = 20.5
PICKUP_TIP_Y_MM = OUTLET_Y_MM
PICKUP_TIP_Z_MM = OUTLET_Z_MM
PICKUP_HANDOFF_X_MM = CENTER_X_MM + BODY_X_MM / 2.0
PICKUP_OUTER_X_END_MM = PICKUP_HANDOFF_X_MM + 0.8
PICKUP_LUMEN_X_START_MM = PICKUP_TIP_X_MM - 0.2
PICKUP_LUMEN_X_END_MM = PICKUP_HANDOFF_X_MM + 3.0

SERVICE_SEQUENCE_IDS = (
    "CLEANSER-INTERFACE-SERVICE-01-RETRACT-CLOSURE-KEY",
    "CLEANSER-INTERFACE-SERVICE-02-WITHDRAW-REFILL-PURGE-CLOSURE",
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_BLOB_RE = re.compile(r"[0-9a-f]{40}\Z")


class CleanserServiceGeometryError(ValueError):
    pass


def _box(dx: float, dy: float, dz: float, x: float, y: float, z: float) -> cq.Workplane:
    return cq.Workplane("XY").box(dx, dy, dz, centered=(True, True, True)).translate((x, y, z))


def _z_cylinder(x: float, y: float, z0: float, diameter: float, length: float) -> cq.Workplane:
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(diameter / 2.0).extrude(length)


def _x_cylinder(y: float, z: float, x0: float, diameter: float, length: float) -> cq.Workplane:
    return cq.Workplane("YZ").workplane(offset=x0).center(y, z).circle(diameter / 2.0).extrude(length)


def _z_ring(x: float, y: float, z0: float, outer_d: float, inner_d: float, length: float) -> cq.Workplane:
    return _z_cylinder(x, y, z0, outer_d, length).cut(
        _z_cylinder(x, y, z0 - 0.05, inner_d, length + 0.1)
    )


def _one_valid_solid(shape: cq.Workplane, *, label: str) -> None:
    if shape.solids().size() != 1 or not shape.val().isValid() or shape.val().Volume() <= 0.0:
        raise CleanserServiceGeometryError(f"{label} must be one positive valid deterministic solid")


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    return float(a.val().intersect(b.val()).Volume())


def _pickup_outer() -> cq.Workplane:
    return _x_cylinder(
        PICKUP_TIP_Y_MM,
        PICKUP_TIP_Z_MM,
        PICKUP_TIP_X_MM,
        PICKUP_TUBE_OUTER_DIAMETER_MM,
        PICKUP_OUTER_X_END_MM - PICKUP_TIP_X_MM,
    )


def _pickup_lumen() -> cq.Workplane:
    return _x_cylinder(
        PICKUP_TIP_Y_MM,
        PICKUP_TIP_Z_MM,
        PICKUP_LUMEN_X_START_MM,
        PICKUP_LUMEN_DIAMETER_MM,
        PICKUP_LUMEN_X_END_MM - PICKUP_LUMEN_X_START_MM,
    )


@dataclass(frozen=True, slots=True)
class CleanserInterfaceServiceStep:
    step_id: str
    moving_part: str
    translation_world_mm: tuple[float, float, float]
    precondition: str

    def __post_init__(self) -> None:
        if self.step_id not in SERVICE_SEQUENCE_IDS:
            raise CleanserServiceGeometryError(f"unknown cleanser interface service step {self.step_id!r}")
        if type(self.moving_part) is not str or not self.moving_part:
            raise CleanserServiceGeometryError("service moving part must be exact nonblank text")
        if type(self.translation_world_mm) is not tuple or len(self.translation_world_mm) != 3:
            raise CleanserServiceGeometryError("service translation must be an exact three-vector")
        if not all(type(value) in (int, float) and math.isfinite(float(value)) for value in self.translation_world_mm):
            raise CleanserServiceGeometryError("service translation must use finite numeric scalars")
        if math.sqrt(sum(float(value) ** 2 for value in self.translation_world_mm)) <= 0.0:
            raise CleanserServiceGeometryError("service translation must be nonzero")
        if type(self.precondition) is not str or not self.precondition:
            raise CleanserServiceGeometryError("service precondition must be exact nonblank text")

    def manifest(self) -> dict[str, object]:
        return {
            "step_id": self.step_id,
            "moving_part": self.moving_part,
            "translation_world_mm": list(self.translation_world_mm),
            "precondition": self.precondition,
            "evidence_status": "DIGITAL_SERVICE_TRAJECTORY_ONLY_NOT_WET_HAND_OR_HYGIENE_VALIDATION",
        }


@dataclass(frozen=True, slots=True)
class CleanserServiceGeometry:
    source_authority_revision: str
    source_storage_manifest_sha256: str
    source_storage_blob_sha: str
    ported_body_solid: cq.Workplane
    service_closure_solid: cq.Workplane
    service_retention_key_solid: cq.Workplane
    fill_seal_reference_solid: cq.Workplane
    purge_seal_reference_solid: cq.Workplane
    vent_lumen_solid: cq.Workplane
    vent_barrier_reservation_solid: cq.Workplane
    pickup_tube_solid: cq.Workplane
    pickup_lumen_solid: cq.Workplane
    service_closure_sweep_solid: cq.Workplane
    service_key_sweep_solid: cq.Workplane
    service_sequence: tuple[CleanserInterfaceServiceStep, ...]
    fluid_identity: str = FLUID_IDENTITY
    geometry_status: str = GEOMETRY_STATUS
    physical_validation_eligible: bool = False
    evidence_status: str = EVIDENCE_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    @property
    def pickup_centerline_length_mm(self) -> float:
        return PICKUP_HANDOFF_X_MM - PICKUP_TIP_X_MM

    @property
    def pickup_lumen_geometric_volume_mL(self) -> float:
        area_mm2 = math.pi * (PICKUP_LUMEN_DIAMETER_MM / 2.0) ** 2
        return area_mm2 * self.pickup_centerline_length_mm / 1000.0

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()

    def validate_invariants(self) -> None:
        if type(self.source_storage_manifest_sha256) is not str or _SHA256_RE.fullmatch(self.source_storage_manifest_sha256) is None:
            raise CleanserServiceGeometryError("source cleanser storage manifest must be canonical SHA-256")
        if type(self.source_storage_blob_sha) is not str or _BLOB_RE.fullmatch(self.source_storage_blob_sha) is None:
            raise CleanserServiceGeometryError("source cleanser storage blob must be exact lowercase 40-hex")
        if self.fluid_identity != "CLEANSER":
            raise CleanserServiceGeometryError("cleanser service geometry must retain exact CLEANSER identity")
        if self.geometry_status != GEOMETRY_STATUS or self.evidence_status != EVIDENCE_STATUS:
            raise CleanserServiceGeometryError("cleanser service geometry evidence boundary changed")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise CleanserServiceGeometryError("cleanser service CAD cannot become physical validation evidence")
        if tuple(step.step_id for step in self.service_sequence) != SERVICE_SEQUENCE_IDS:
            raise CleanserServiceGeometryError("cleanser interface service sequence changed")
        if not (REFILL_PLUG_DIAMETER_MM < REFILL_BORE_DIAMETER_MM and PURGE_PLUG_DIAMETER_MM < PURGE_BORE_DIAMETER_MM):
            raise CleanserServiceGeometryError("service closure plugs must retain running clearance")
        if not (SERVICE_KEY_STEM_DIAMETER_MM < SERVICE_KEY_BORE_DIAMETER_MM < SERVICE_KEY_HEAD_DIAMETER_MM):
            raise CleanserServiceGeometryError("service closure key clearance hierarchy changed")
        if PICKUP_LUMEN_DIAMETER_MM != OUTLET_BORE_DIAMETER_MM:
            raise CleanserServiceGeometryError("pickup lumen must preserve the controlled realized outlet bore diameter")
        for label, solid in (
            ("ported body", self.ported_body_solid),
            ("service closure", self.service_closure_solid),
            ("service retention key", self.service_retention_key_solid),
            ("fill seal reference", self.fill_seal_reference_solid),
            ("purge seal reference", self.purge_seal_reference_solid),
            ("vent lumen", self.vent_lumen_solid),
            ("vent barrier reservation", self.vent_barrier_reservation_solid),
            ("pickup tube", self.pickup_tube_solid),
            ("pickup lumen", self.pickup_lumen_solid),
            ("service closure sweep", self.service_closure_sweep_solid),
            ("service key sweep", self.service_key_sweep_solid),
        ):
            _one_valid_solid(solid, label=f"cleanser {label}")
        if _intersection_volume(self.ported_body_solid, self.vent_lumen_solid) > 1e-7:
            raise CleanserServiceGeometryError("vent lumen must remain an actual body void")
        if _intersection_volume(self.pickup_tube_solid, self.pickup_lumen_solid) > 1e-7:
            raise CleanserServiceGeometryError("pickup lumen must remain an actual tube void")
        for label, a, b in (
            ("body/closure", self.ported_body_solid, self.service_closure_solid),
            ("body/service key", self.ported_body_solid, self.service_retention_key_solid),
            ("closure/service key", self.service_closure_solid, self.service_retention_key_solid),
        ):
            if _intersection_volume(a, b) > 1e-7:
                raise CleanserServiceGeometryError(f"assembled cleanser {label} material overlaps")

    def validate_current_sources(self, authority: Authority) -> RealizedCleanserStorage:
        if type(authority) is not Authority:
            raise CleanserServiceGeometryError("authority must be an exact Authority contract")
        storage = build_realized_cleanser_storage(authority)
        storage.validate_current_sources(authority)
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise CleanserServiceGeometryError("cleanser service geometry is stale for current authority")
        if self.source_storage_manifest_sha256 != storage.manifest_sha256:
            raise CleanserServiceGeometryError("cleanser service geometry is stale for realized storage")
        if self.source_storage_blob_sha != SOURCE_STORAGE_BLOB_SHA:
            raise CleanserServiceGeometryError("cleanser service geometry source blob identity changed")
        if tuple(port["port_id"] for port in storage.manifest()["ports"]) != PORT_IDS:
            raise CleanserServiceGeometryError("cleanser controlled port IDs drifted")
        return storage

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        rear_z = CENTER_Z_MM - BODY_Z_MM / 2.0
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_authority_revision": self.source_authority_revision,
            "source_storage_schema": SOURCE_STORAGE_SCHEMA,
            "source_storage_manifest_sha256": self.source_storage_manifest_sha256,
            "source_storage_blob_sha": self.source_storage_blob_sha,
            "authored_against_main_sha": AUTHORED_AGAINST_MAIN_SHA,
            "world_frame_id": WORLD_FRAME_ID,
            "fluid_identity": self.fluid_identity,
            "controlled_port_ids": list(PORT_IDS),
            "service_closure": {
                "part_id": "MASCK_ONE-CLEANSER-REFILL-PURGE-SERVICE-CLOSURE",
                "center_world_mm": [SERVICE_CLOSURE_CENTER_X_MM, SERVICE_CLOSURE_CENTER_Y_MM, SERVICE_CLOSURE_CENTER_Z_MM],
                "bridge_xyz_mm": [SERVICE_CLOSURE_X_MM, SERVICE_CLOSURE_Y_MM, SERVICE_CLOSURE_Z_MM],
                "retention_lug_xyz_mm": [SERVICE_CLOSURE_LUG_X_MM, SERVICE_CLOSURE_LUG_Y_MM, SERVICE_CLOSURE_LUG_Z_MM],
                "refill_plug_diameter_mm": REFILL_PLUG_DIAMETER_MM,
                "purge_plug_diameter_mm": PURGE_PLUG_DIAMETER_MM,
                "retention": "TRANSVERSE_REMOVABLE_KEY_THROUGH_LOWER_LUG_POSITIVELY_BLOCKS_POSTERIOR_WITHDRAWAL",
                "seal_interface_status": "REALIZED_ANNULAR_GROOVES_SEAL_MATERIAL_AND_COMPRESSION_UNSELECTED",
                "refill_access_status": "CLOSURE_REMOVAL_EXPOSES_EXISTING_REALIZED_REFILL_BORE",
                "purge_access_status": "CLOSURE_REMOVAL_EXPOSES_EXISTING_REALIZED_PURGE_BORE",
            },
            "vent": {
                "feature_id": VENT_FEATURE_ID,
                "feature_role": "HEADSPACE_GAS_EXCHANGE_FEATURE_NOT_FOURTH_CONTROLLED_LIQUID_PORT",
                "center_world_mm": [VENT_X_MM, VENT_Y_MM, rear_z],
                "bore_diameter_mm": VENT_BORE_DIAMETER_MM,
                "seat_outer_diameter_mm": VENT_SEAT_OUTER_DIAMETER_MM,
                "barrier_reservation_diameter_mm": VENT_BARRIER_RESERVATION_DIAMETER_MM,
                "barrier_status": "PACKAGE_RESERVATION_ONLY_HARDWARE_MATERIAL_INGRESS_AND_FLOW_UNVALIDATED",
            },
            "pickup": {
                "feature_id": PICKUP_FEATURE_ID,
                "centerline_world_mm": [
                    [PICKUP_TIP_X_MM, PICKUP_TIP_Y_MM, PICKUP_TIP_Z_MM],
                    [PICKUP_HANDOFF_X_MM, PICKUP_TIP_Y_MM, PICKUP_TIP_Z_MM],
                ],
                "centerline_length_mm": self.pickup_centerline_length_mm,
                "tube_outer_diameter_mm": PICKUP_TUBE_OUTER_DIAMETER_MM,
                "lumen_diameter_mm": PICKUP_LUMEN_DIAMETER_MM,
                "lumen_internal_area_mm2": math.pi * (PICKUP_LUMEN_DIAMETER_MM / 2.0) ** 2,
                "geometric_lumen_volume_mL": self.pickup_lumen_geometric_volume_mL,
                "outlet_port_id": PORT_OUTLET,
                "geometry_role": "STRAIGHT_INTERNAL_PICKUP_TUBE_TO_EXISTING_DEDICATED_CLEANSER_OUTLET",
                "performance_status": "NO_VISCOSITY_PRIMING_FLOW_DRAWDOWN_OR_ORIENTATION_CLAIM",
            },
            "service_sequence": [step.manifest() for step in self.service_sequence],
            "service_closure_withdrawal_travel_mm": SERVICE_CLOSURE_WITHDRAWAL_TRAVEL_MM,
            "service_key_withdrawal_travel_mm": SERVICE_KEY_WITHDRAWAL_TRAVEL_MM,
            "viscosity_limit_mPa_s": None,
            "viscosity_status": "NOT_DEFINED_BY_DIGITAL_GEOMETRY_REQUIRES_SELECTED_CLEANSER_AND_PHYSICAL_FLOW_VALIDATION",
            "fresh_water_identity_unchanged": True,
            "mixed_waste_architecture_unchanged": "ACQUISITION_TO_WASTE_PUMP_TO_PASSIVE_BACKFLOW_PROTECTION_TO_CARTRIDGE",
            "geometry_status": self.geometry_status,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload


def build_cleanser_service_geometry(authority: Authority) -> CleanserServiceGeometry:
    if type(authority) is not Authority:
        raise CleanserServiceGeometryError("authority must be an exact Authority contract")
    storage = build_realized_cleanser_storage(authority)
    storage.validate_current_sources(authority)
    rear_z = CENTER_Z_MM - BODY_Z_MM / 2.0

    closure = _box(
        SERVICE_CLOSURE_X_MM,
        SERVICE_CLOSURE_Y_MM,
        SERVICE_CLOSURE_Z_MM,
        SERVICE_CLOSURE_CENTER_X_MM,
        SERVICE_CLOSURE_CENTER_Y_MM,
        SERVICE_CLOSURE_CENTER_Z_MM,
    )
    closure = closure.union(
        _z_cylinder(REFILL_X_MM, REFILL_Y_MM, PLUG_Z_START_MM, REFILL_PLUG_DIAMETER_MM, PLUG_Z_LENGTH_MM)
    )
    closure = closure.union(
        _z_cylinder(PURGE_X_MM, PURGE_Y_MM, PLUG_Z_START_MM, PURGE_PLUG_DIAMETER_MM, PLUG_Z_LENGTH_MM)
    )
    closure = closure.union(
        _box(
            SERVICE_CLOSURE_LUG_X_MM,
            SERVICE_CLOSURE_LUG_Y_MM,
            SERVICE_CLOSURE_LUG_Z_MM,
            SERVICE_CLOSURE_LUG_CENTER_X_MM,
            SERVICE_CLOSURE_LUG_CENTER_Y_MM,
            SERVICE_CLOSURE_LUG_CENTER_Z_MM,
        )
    )

    ear_left = _box(
        SERVICE_EAR_X_MM,
        SERVICE_EAR_Y_MM,
        SERVICE_EAR_Z_MM,
        SERVICE_EAR_LEFT_X_MM,
        SERVICE_EAR_CENTER_Y_MM,
        SERVICE_EAR_CENTER_Z_MM,
    )
    ear_right = _box(
        SERVICE_EAR_X_MM,
        SERVICE_EAR_Y_MM,
        SERVICE_EAR_Z_MM,
        SERVICE_EAR_RIGHT_X_MM,
        SERVICE_EAR_CENTER_Y_MM,
        SERVICE_EAR_CENTER_Z_MM,
    )
    body_key_bore = _x_cylinder(
        SERVICE_KEY_Y_MM,
        SERVICE_KEY_Z_MM,
        SERVICE_KEY_X_MIN_MM - 0.5,
        SERVICE_KEY_BORE_DIAMETER_MM,
        SERVICE_KEY_X_MAX_MM - SERVICE_KEY_X_MIN_MM + 1.0,
    )
    closure_key_bore = _x_cylinder(
        SERVICE_KEY_Y_MM,
        SERVICE_KEY_Z_MM,
        SERVICE_CLOSURE_KEY_BORE_X_MIN_MM,
        SERVICE_KEY_BORE_DIAMETER_MM,
        SERVICE_CLOSURE_KEY_BORE_X_MAX_MM - SERVICE_CLOSURE_KEY_BORE_X_MIN_MM,
    )
    closure = closure.cut(closure_key_bore)
    _one_valid_solid(closure, label="cleanser service closure")

    fill_groove = _z_ring(
        REFILL_X_MM,
        REFILL_Y_MM,
        rear_z - 0.05,
        FILL_SEAL_GROOVE_OUTER_DIAMETER_MM,
        FILL_SEAL_GROOVE_INNER_DIAMETER_MM,
        SEAL_GROOVE_DEPTH_MM + 0.05,
    )
    purge_groove = _z_ring(
        PURGE_X_MM,
        PURGE_Y_MM,
        rear_z - 0.05,
        PURGE_SEAL_GROOVE_OUTER_DIAMETER_MM,
        PURGE_SEAL_GROOVE_INNER_DIAMETER_MM,
        SEAL_GROOVE_DEPTH_MM + 0.05,
    )
    fill_seal_ref = _z_ring(
        REFILL_X_MM,
        REFILL_Y_MM,
        rear_z - SEAL_REFERENCE_AXIAL_MM,
        FILL_SEAL_GROOVE_OUTER_DIAMETER_MM - 0.15,
        FILL_SEAL_GROOVE_INNER_DIAMETER_MM + 0.15,
        SEAL_REFERENCE_AXIAL_MM,
    )
    purge_seal_ref = _z_ring(
        PURGE_X_MM,
        PURGE_Y_MM,
        rear_z - SEAL_REFERENCE_AXIAL_MM,
        PURGE_SEAL_GROOVE_OUTER_DIAMETER_MM - 0.12,
        PURGE_SEAL_GROOVE_INNER_DIAMETER_MM + 0.12,
        SEAL_REFERENCE_AXIAL_MM,
    )

    vent_lumen = _z_cylinder(VENT_X_MM, VENT_Y_MM, rear_z - 0.3, VENT_BORE_DIAMETER_MM, 2.8)
    vent_seat = _z_ring(
        VENT_X_MM,
        VENT_Y_MM,
        rear_z - VENT_SEAT_PROJECTION_MM,
        VENT_SEAT_OUTER_DIAMETER_MM,
        VENT_BORE_DIAMETER_MM,
        VENT_SEAT_PROJECTION_MM + 0.4,
    )
    vent_barrier_res = _z_cylinder(
        VENT_X_MM,
        VENT_Y_MM,
        rear_z - VENT_SEAT_PROJECTION_MM - VENT_BARRIER_RESERVATION_DEPTH_MM,
        VENT_BARRIER_RESERVATION_DIAMETER_MM,
        VENT_BARRIER_RESERVATION_DEPTH_MM,
    )

    pickup_outer = _pickup_outer()
    pickup_lumen = _pickup_lumen()
    pickup_tube = pickup_outer.cut(pickup_lumen)
    _one_valid_solid(pickup_tube, label="cleanser pickup tube")

    ported_body = storage.body_solid.union(ear_left).union(ear_right).union(vent_seat).union(pickup_outer)
    ported_body = (
        ported_body.cut(fill_groove)
        .cut(purge_groove)
        .cut(vent_lumen)
        .cut(pickup_lumen)
        .cut(body_key_bore)
    )
    _one_valid_solid(ported_body, label="cleanser service-ported body")

    service_key = _x_cylinder(
        SERVICE_KEY_Y_MM,
        SERVICE_KEY_Z_MM,
        SERVICE_KEY_X_MIN_MM,
        SERVICE_KEY_STEM_DIAMETER_MM,
        SERVICE_KEY_X_MAX_MM - SERVICE_KEY_X_MIN_MM,
    ).union(
        _x_cylinder(
            SERVICE_KEY_Y_MM,
            SERVICE_KEY_Z_MM,
            SERVICE_KEY_HEAD_X_MIN_MM,
            SERVICE_KEY_HEAD_DIAMETER_MM,
            SERVICE_KEY_HEAD_X_MAX_MM - SERVICE_KEY_HEAD_X_MIN_MM,
        )
    )
    _one_valid_solid(service_key, label="cleanser service closure key")

    closure_bb = closure.val().BoundingBox()
    closure_sweep = _box(
        float(closure_bb.xlen),
        float(closure_bb.ylen),
        float(closure_bb.zlen) + SERVICE_CLOSURE_WITHDRAWAL_TRAVEL_MM,
        (float(closure_bb.xmin) + float(closure_bb.xmax)) / 2.0,
        (float(closure_bb.ymin) + float(closure_bb.ymax)) / 2.0,
        (float(closure_bb.zmin) + float(closure_bb.zmax) - SERVICE_CLOSURE_WITHDRAWAL_TRAVEL_MM) / 2.0,
    )
    key_bb = service_key.val().BoundingBox()
    key_sweep = _box(
        float(key_bb.xlen) + SERVICE_KEY_WITHDRAWAL_TRAVEL_MM,
        float(key_bb.ylen),
        float(key_bb.zlen),
        (float(key_bb.xmin) + float(key_bb.xmax) + SERVICE_KEY_WITHDRAWAL_TRAVEL_MM) / 2.0,
        (float(key_bb.ymin) + float(key_bb.ymax)) / 2.0,
        (float(key_bb.zmin) + float(key_bb.zmax)) / 2.0,
    )

    sequence = (
        CleanserInterfaceServiceStep(
            SERVICE_SEQUENCE_IDS[0],
            "cleanser_refill_purge_service_key",
            (SERVICE_KEY_WITHDRAWAL_TRAVEL_MM, 0.0, 0.0),
            "CASSETTE_REMOVED_FROM_MASK_AND_UNPOWERED",
        ),
        CleanserInterfaceServiceStep(
            SERVICE_SEQUENCE_IDS[1],
            "cleanser_refill_purge_service_closure",
            (0.0, 0.0, -SERVICE_CLOSURE_WITHDRAWAL_TRAVEL_MM),
            "SERVICE_KEY_RETRACTED_AND_CASSETTE_REMOVED_FROM_MASK",
        ),
    )

    geometry = CleanserServiceGeometry(
        source_authority_revision=str(authority.get("project", "authority_revision")),
        source_storage_manifest_sha256=storage.manifest_sha256,
        source_storage_blob_sha=SOURCE_STORAGE_BLOB_SHA,
        ported_body_solid=ported_body,
        service_closure_solid=closure,
        service_retention_key_solid=service_key,
        fill_seal_reference_solid=fill_seal_ref,
        purge_seal_reference_solid=purge_seal_ref,
        vent_lumen_solid=vent_lumen,
        vent_barrier_reservation_solid=vent_barrier_res,
        pickup_tube_solid=pickup_tube,
        pickup_lumen_solid=pickup_lumen,
        service_closure_sweep_solid=closure_sweep,
        service_key_sweep_solid=key_sweep,
        service_sequence=sequence,
    )
    geometry.validate_current_sources(authority)
    return geometry
