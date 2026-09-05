"""Deterministic realized CAD for the dedicated cleanser-storage architecture.

All geometry added here is a provisional Cell 4 CAD baseline. It is digital closure,
not supplier selection or physical evidence for dosing, sealing, leakage, compatibility,
hygiene, drying, serviceability, durability, or purge/backflow performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

import cadquery as cq

from .authority import Authority
from .cleanser_storage import (
    CLEANSER_STORAGE_ID,
    PORT_IDS,
    PORT_OUTLET,
    PORT_PURGE,
    PORT_REFILL,
    CleanserStorageArchitecture,
    build_cleanser_storage_architecture,
)

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
AUTHORED_AGAINST_MAIN_SHA = "628ec5f5766937433b1bdf8f30edc372924cf41e"
FLUID_IDENTITY = "CLEANSER"
RESERVOIR_CAVITY_CLASS = "WET_REMOVABLE"
MOUNT_CAVITY_CLASS = "WET_DRAINABLE"
GEOMETRY_STATUS = "CELL4_PROVISIONAL_REALIZED_CAD_NOT_SUPPLIER_SELECTED"
SERVICE_STATUS = "MASK_REMOVED_UNPOWERED_DIGITAL_SERVICE_SEQUENCE_NOT_WET_USE_VALIDATION"
COMPATIBILITY_STATUS = "BLOCKED_PENDING_SELECTED_CLEANSER_CHEMISTRY_WETTED_MATERIALS_AND_CONTROLLED_EVIDENCE"
PHYSICAL_EVIDENCE_STATUS = "DIGITAL_GEOMETRY_ONLY_NOT_PHYSICAL_PERFORMANCE_EVIDENCE"

CAVITY_X_MM = 16.0
CAVITY_Y_MM = 16.0
CAVITY_Z_MM = 12.0
WALL_MM = 1.0
BODY_X_MM = 18.0
BODY_Y_MM = 18.0
BODY_Z_MM = 14.0
CENTER_X_MM = 26.5
CENTER_Y_MM = 72.0
CENTER_Z_MM = 8.0

CRADLE_OUTER_X_MM = 22.0
CRADLE_OUTER_Y_MM = 22.0
CRADLE_OUTER_Z_MM = 16.0
CRADLE_INNER_X_MM = 19.0
CRADLE_INNER_Y_MM = 19.0
CRADLE_INNER_Z_MIN_MM = -0.50
CRADLE_INNER_Z_MAX_MM = 15.25
CRADLE_WALL_MIN_MM = 1.5
DRAIN_SLOT_X_MM = 3.0
DRAIN_SLOT_Y_MM = 4.0
DRAIN_SLOT_Z_MM = 5.0
DRAIN_SLOT_CENTER_X_MM = 21.5
DRAIN_SLOT_CENTER_Y_MM = 61.5
DRAIN_SLOT_CENTER_Z_MM = 1.5

REFILL_X_MM = 23.5
REFILL_Y_MM = 76.0
REFILL_BORE_DIAMETER_MM = 4.0
REFILL_BOSS_OUTER_DIAMETER_MM = 7.0
REFILL_CLOSURE_RESERVATION_DIAMETER_MM = 9.0
REFILL_CLOSURE_RESERVATION_DEPTH_MM = 3.0
PURGE_X_MM = 29.5
PURGE_Y_MM = 68.0
PURGE_BORE_DIAMETER_MM = 2.0
PURGE_BOSS_OUTER_DIAMETER_MM = 4.0
PURGE_CONNECTOR_RESERVATION_DIAMETER_MM = 5.0
PURGE_CONNECTOR_RESERVATION_DEPTH_MM = 3.0
OUTLET_Y_MM = 65.0
OUTLET_Z_MM = 5.0
OUTLET_BORE_DIAMETER_MM = 2.0
OUTLET_BOSS_OUTER_DIAMETER_MM = 4.0
OUTLET_CONNECTOR_RESERVATION_DIAMETER_MM = 5.0
OUTLET_CONNECTOR_RESERVATION_DEPTH_MM = 3.0
OUTLET_CRADLE_PASSAGE_DIAMETER_MM = 5.0
BOSS_PROJECTION_MM = 1.0
BOSS_BODY_OVERLAP_MM = 1.0

RETENTION_LUG_X_MM = 4.0
RETENTION_LUG_Y_MM = 1.4
RETENTION_LUG_Z_MM = 3.0
RETENTION_LUG_CENTER_Y_MM = 62.7
RETENTION_LUG_CENTER_Z_MM = 1.8
RETENTION_KEY_Y_MM = RETENTION_LUG_CENTER_Y_MM
RETENTION_KEY_Z_MM = RETENTION_LUG_CENTER_Z_MM
RETENTION_KEY_STEM_DIAMETER_MM = 1.4
RETENTION_KEY_BORE_DIAMETER_MM = 1.8
RETENTION_KEY_HEAD_DIAMETER_MM = 3.5
RETENTION_KEY_X_MIN_MM = 15.2
RETENTION_KEY_X_MAX_MM = 38.5
RETENTION_KEY_HEAD_X_MIN_MM = 37.5
RETENTION_KEY_HEAD_X_MAX_MM = 39.5
RETENTION_LUG_CHANNEL_X_MM = 6.0
RETENTION_LUG_CHANNEL_Y_MM = 3.0
RETENTION_LUG_CHANNEL_Z_MM = 4.5

PACKAGE_CLEARANCE_RESERVATION_MM = 2.0
CASSETTE_WITHDRAWAL_TRAVEL_MM = 18.0
RETENTION_KEY_WITHDRAWAL_TRAVEL_MM = 14.0
SERVICE_SEQUENCE_IDS = (
    "CLEANSER-SERVICE-01-RETRACT-RETENTION-KEY",
    "CLEANSER-SERVICE-02-WITHDRAW-CASSETTE-POSTERIOR",
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_GIT_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


class RealizedCleanserStorageError(ValueError):
    pass


def _box(dx: float, dy: float, dz: float, x: float, y: float, z: float) -> cq.Workplane:
    return cq.Workplane("XY").box(dx, dy, dz, centered=(True, True, True)).translate((x, y, z))


def _z_cylinder(x: float, y: float, z0: float, d: float, length: float) -> cq.Workplane:
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(d / 2.0).extrude(length)


def _x_cylinder(y: float, z: float, x0: float, d: float, length: float) -> cq.Workplane:
    return cq.Workplane("YZ").workplane(offset=x0).center(y, z).circle(d / 2.0).extrude(length)


def _z_ring(x: float, y: float, z0: float, outer_d: float, inner_d: float, length: float) -> cq.Workplane:
    return _z_cylinder(x, y, z0, outer_d, length).cut(
        _z_cylinder(x, y, z0 - 0.1, inner_d, length + 0.2)
    )


def _x_ring(y: float, z: float, x0: float, outer_d: float, inner_d: float, length: float) -> cq.Workplane:
    return _x_cylinder(y, z, x0, outer_d, length).cut(
        _x_cylinder(y, z, x0 - 0.1, inner_d, length + 0.2)
    )


def _one_valid_solid(shape: cq.Workplane, label: str) -> None:
    if shape.solids().size() != 1 or not shape.val().isValid():
        raise RealizedCleanserStorageError(f"{label} must be one valid deterministic solid")


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    return float(a.val().intersect(b.val()).Volume())


@dataclass(frozen=True, slots=True)
class CleanserServiceStep:
    step_id: str
    moving_part: str
    translation_world_mm: tuple[float, float, float]
    precondition: str
    evidence_status: str = SERVICE_STATUS

    def __post_init__(self) -> None:
        if self.step_id not in SERVICE_SEQUENCE_IDS:
            raise RealizedCleanserStorageError(f"unknown cleanser service step {self.step_id!r}")
        if type(self.moving_part) is not str or not self.moving_part:
            raise RealizedCleanserStorageError("service moving part must be exact nonblank text")
        if type(self.translation_world_mm) is not tuple or len(self.translation_world_mm) != 3:
            raise RealizedCleanserStorageError("service translation must be an exact 3-vector tuple")
        if not all(type(v) in (int, float) and math.isfinite(float(v)) for v in self.translation_world_mm):
            raise RealizedCleanserStorageError("service translation must contain finite numeric scalars")
        if math.sqrt(sum(float(v) ** 2 for v in self.translation_world_mm)) <= 0.0:
            raise RealizedCleanserStorageError("service translation must be nonzero")
        if type(self.precondition) is not str or not self.precondition:
            raise RealizedCleanserStorageError("service precondition must be exact nonblank text")
        if self.evidence_status != SERVICE_STATUS:
            raise RealizedCleanserStorageError("service step cannot promote physical usability evidence")

    def manifest(self) -> dict[str, object]:
        return {
            "step_id": self.step_id,
            "moving_part": self.moving_part,
            "translation_world_mm": list(self.translation_world_mm),
            "precondition": self.precondition,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class RealizedCleanserStorage:
    source_authority_revision: str
    source_architecture_sha256: str
    authored_against_git_sha: str
    body_solid: cq.Workplane
    internal_cavity_solid: cq.Workplane
    cradle_solid: cq.Workplane
    retention_key_solid: cq.Workplane
    refill_bore_solid: cq.Workplane
    purge_bore_solid: cq.Workplane
    outlet_bore_solid: cq.Workplane
    refill_closure_reservation_solid: cq.Workplane
    purge_connector_reservation_solid: cq.Workplane
    outlet_connector_reservation_solid: cq.Workplane
    drain_path_reference_solid: cq.Workplane
    cassette_service_sweep_solid: cq.Workplane
    key_service_sweep_solid: cq.Workplane
    service_sequence: tuple[CleanserServiceStep, ...]
    fluid_identity: str = FLUID_IDENTITY
    reservoir_id: str = CLEANSER_STORAGE_ID
    reservoir_cavity_classification: str = RESERVOIR_CAVITY_CLASS
    mount_cavity_classification: str = MOUNT_CAVITY_CLASS
    geometry_status: str = GEOMETRY_STATUS
    compatibility_status: str = COMPATIBILITY_STATUS
    physical_validation_eligible: bool = False
    evidence_status: str = PHYSICAL_EVIDENCE_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    @property
    def geometric_cavity_volume_mL(self) -> float:
        return float(self.internal_cavity_solid.val().Volume()) / 1000.0

    @property
    def neutral_geometry_below_outlet_center_plane_mL(self) -> float:
        cavity_y_min = CENTER_Y_MM - CAVITY_Y_MM / 2.0
        return CAVITY_X_MM * CAVITY_Z_MM * (OUTLET_Y_MM - cavity_y_min) / 1000.0

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode()
        return sha256(raw).hexdigest()

    def validate_invariants(self) -> None:
        if type(self.source_architecture_sha256) is not str or _SHA256_RE.fullmatch(self.source_architecture_sha256) is None:
            raise RealizedCleanserStorageError("cleanser architecture source must be a canonical lowercase SHA-256")
        if type(self.authored_against_git_sha) is not str or _GIT_SHA_RE.fullmatch(self.authored_against_git_sha) is None:
            raise RealizedCleanserStorageError("authored-against Git provenance must be exact lowercase 40-hex")
        if type(self.source_authority_revision) is not str or not self.source_authority_revision:
            raise RealizedCleanserStorageError("realized cleanser geometry requires exact authority revision")
        if self.fluid_identity != "CLEANSER":
            raise RealizedCleanserStorageError("realized cleanser geometry must retain exact CLEANSER identity")
        if self.reservoir_id != CLEANSER_STORAGE_ID:
            raise RealizedCleanserStorageError("realized cleanser geometry changed the stable reservoir ID")
        if self.reservoir_cavity_classification != "WET_REMOVABLE" or self.mount_cavity_classification != "WET_DRAINABLE":
            raise RealizedCleanserStorageError("cleanser body/cradle hygiene classes changed")
        if self.geometry_status != GEOMETRY_STATUS or self.compatibility_status != COMPATIBILITY_STATUS:
            raise RealizedCleanserStorageError("realized cleanser status boundary changed")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise RealizedCleanserStorageError("realized cleanser geometry cannot become physical validation evidence")
        if self.evidence_status != PHYSICAL_EVIDENCE_STATUS:
            raise RealizedCleanserStorageError("realized cleanser evidence firewall changed")
        if tuple(step.step_id for step in self.service_sequence) != SERVICE_SEQUENCE_IDS:
            raise RealizedCleanserStorageError("cleanser service sequence order is not controlled")
        if not (RETENTION_KEY_STEM_DIAMETER_MM < RETENTION_KEY_BORE_DIAMETER_MM < RETENTION_KEY_HEAD_DIAMETER_MM):
            raise RealizedCleanserStorageError("retention key clearance hierarchy changed")
        if WALL_MM <= 0.0 or CRADLE_WALL_MIN_MM <= 0.0 or PACKAGE_CLEARANCE_RESERVATION_MM <= 0.0:
            raise RealizedCleanserStorageError("wall and clearance baselines must remain positive")
        for label, shape in (
            ("body", self.body_solid),
            ("cavity", self.internal_cavity_solid),
            ("cradle", self.cradle_solid),
            ("retention key", self.retention_key_solid),
            ("refill bore", self.refill_bore_solid),
            ("purge bore", self.purge_bore_solid),
            ("outlet bore", self.outlet_bore_solid),
            ("refill closure reservation", self.refill_closure_reservation_solid),
            ("purge connector reservation", self.purge_connector_reservation_solid),
            ("outlet connector reservation", self.outlet_connector_reservation_solid),
            ("drain path", self.drain_path_reference_solid),
            ("cassette service sweep", self.cassette_service_sweep_solid),
            ("key service sweep", self.key_service_sweep_solid),
        ):
            _one_valid_solid(shape, f"cleanser {label}")
        if not math.isclose(self.geometric_cavity_volume_mL, 3.072, abs_tol=1e-8):
            raise RealizedCleanserStorageError("cleanser cavity B-rep volume changed")
        if not math.isclose(self.neutral_geometry_below_outlet_center_plane_mL, 0.192, abs_tol=1e-12):
            raise RealizedCleanserStorageError("cleanser geometric low-band accounting changed")
        for label, a, b in (
            ("body/cradle", self.body_solid, self.cradle_solid),
            ("body/key", self.body_solid, self.retention_key_solid),
            ("cradle/key", self.cradle_solid, self.retention_key_solid),
        ):
            if _intersection_volume(a, b) > 1e-7:
                raise RealizedCleanserStorageError(f"assembled cleanser {label} material overlaps")

    def validate_current_sources(self, authority: Authority) -> CleanserStorageArchitecture:
        if type(authority) is not Authority:
            raise RealizedCleanserStorageError("authority must be an exact Authority contract")
        architecture = build_cleanser_storage_architecture(authority)
        architecture.validate_current_authority(authority)
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise RealizedCleanserStorageError("realized cleanser geometry is stale for current authority")
        if self.source_architecture_sha256 != architecture.architecture_sha256:
            raise RealizedCleanserStorageError("realized cleanser geometry is stale for current cleanser architecture")
        if tuple(port.port_id for port in architecture.ports) != PORT_IDS:
            raise RealizedCleanserStorageError("realized cleanser ports drifted from controlled architecture")
        if {port.fluid_identity for port in architecture.ports} != {"CLEANSER"}:
            raise RealizedCleanserStorageError("current cleanser architecture changed fluid identity")
        return architecture

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        rear_z = CENTER_Z_MM - BODY_Z_MM / 2.0
        lateral_x = CENTER_X_MM + BODY_X_MM / 2.0
        payload: dict[str, object] = {
            "schema": "MASCK_ONE_CELL4_REALIZED_CLEANSER_STORAGE_V1",
            "source_authority_revision": self.source_authority_revision,
            "source_architecture_sha256": self.source_architecture_sha256,
            "authored_against_git_sha": self.authored_against_git_sha,
            "authored_against_git_sha_role": "HISTORICAL_PROVENANCE_ONLY_NOT_RELEASE_FRESHNESS_PROOF",
            "world_frame_id": WORLD_FRAME_ID,
            "reservoir_id": self.reservoir_id,
            "fluid_identity": self.fluid_identity,
            "reservoir_cavity_classification": self.reservoir_cavity_classification,
            "mount_cavity_classification": self.mount_cavity_classification,
            "geometry": {
                "center_world_mm": [CENTER_X_MM, CENTER_Y_MM, CENTER_Z_MM],
                "internal_cavity_xyz_mm": [CAVITY_X_MM, CAVITY_Y_MM, CAVITY_Z_MM],
                "body_outer_xyz_mm": [BODY_X_MM, BODY_Y_MM, BODY_Z_MM],
                "body_wall_seed_mm": WALL_MM,
                "geometric_cavity_volume_mL": self.geometric_cavity_volume_mL,
                "neutral_geometry_below_outlet_center_plane_mL": self.neutral_geometry_below_outlet_center_plane_mL,
                "volume_evidence_role": "GEOMETRIC_ACCOUNTING_ONLY_NOT_DRAWABLE_VOLUME_OR_SERVICE_CADENCE",
            },
            "mounting": {
                "architecture": "POSTERIOR_SERVICE_SLIDE_IN_DRAINABLE_SLEEVE_WITH_RETRACTABLE_CROSS_KEY",
                "cradle_outer_xyz_mm": [CRADLE_OUTER_X_MM, CRADLE_OUTER_Y_MM, CRADLE_OUTER_Z_MM],
                "cradle_inner_xy_mm": [CRADLE_INNER_X_MM, CRADLE_INNER_Y_MM],
                "cradle_inner_z_mm": [CRADLE_INNER_Z_MIN_MM, CRADLE_INNER_Z_MAX_MM],
                "minimum_sidewall_seed_mm": CRADLE_WALL_MIN_MM,
                "retention_key_stem_diameter_mm": RETENTION_KEY_STEM_DIAMETER_MM,
                "retention_key_bore_diameter_mm": RETENTION_KEY_BORE_DIAMETER_MM,
                "retention_key_head_diameter_mm": RETENTION_KEY_HEAD_DIAMETER_MM,
                "retention_status": "POSITIVE_DIGITAL_CAPTURE_FORCE_WEAR_AND_DURABILITY_UNVALIDATED",
            },
            "ports": [
                {
                    "port_id": PORT_REFILL,
                    "fluid_identity": "CLEANSER",
                    "center_world_mm": [REFILL_X_MM, REFILL_Y_MM, rear_z],
                    "axis": "+Z_FROM_POSTERIOR_SERVICE_SIDE_INTO_CASSETTE",
                    "bore_diameter_mm": REFILL_BORE_DIAMETER_MM,
                    "boss_outer_diameter_mm": REFILL_BOSS_OUTER_DIAMETER_MM,
                    "external_closure_reservation_diameter_mm": REFILL_CLOSURE_RESERVATION_DIAMETER_MM,
                    "closure_status": "RESERVATION_ONLY_CLOSURE_AND_SEAL_HARDWARE_NOT_SELECTED",
                },
                {
                    "port_id": PORT_OUTLET,
                    "fluid_identity": "CLEANSER",
                    "center_world_mm": [lateral_x, OUTLET_Y_MM, OUTLET_Z_MM],
                    "axis": "-X_FROM_LATERAL_DEDICATED_METERING_HANDOFF_INTO_CASSETTE",
                    "bore_diameter_mm": OUTLET_BORE_DIAMETER_MM,
                    "boss_outer_diameter_mm": OUTLET_BOSS_OUTER_DIAMETER_MM,
                    "external_connector_reservation_diameter_mm": OUTLET_CONNECTOR_RESERVATION_DIAMETER_MM,
                    "isolation_status": "DEDICATED_CLEANSER_HANDOFF_ISOLATION_HARDWARE_AND_BACKFLOW_PERFORMANCE_UNVALIDATED",
                },
                {
                    "port_id": PORT_PURGE,
                    "fluid_identity": "CLEANSER",
                    "center_world_mm": [PURGE_X_MM, PURGE_Y_MM, rear_z],
                    "axis": "+Z_FROM_POSTERIOR_SERVICE_SIDE_INTO_CASSETTE",
                    "bore_diameter_mm": PURGE_BORE_DIAMETER_MM,
                    "boss_outer_diameter_mm": PURGE_BOSS_OUTER_DIAMETER_MM,
                    "external_connector_reservation_diameter_mm": PURGE_CONNECTOR_RESERVATION_DIAMETER_MM,
                    "purge_status": "REALIZED_SERVICE_PASSAGE_PURGE_VOLUME_PRESSURE_AND_FLOW_UNVALIDATED",
                },
            ],
            "wet_separation": {
                "physical_cradle_barrier_present": True,
                "drain_slot_xyz_mm": [DRAIN_SLOT_X_MM, DRAIN_SLOT_Y_MM, DRAIN_SLOT_Z_MM],
                "drain_slot_center_world_mm": [DRAIN_SLOT_CENTER_X_MM, DRAIN_SLOT_CENTER_Y_MM, DRAIN_SLOT_CENTER_Z_MM],
                "status": "GEOMETRIC_BARRIER_AND_LOW_POINT_OPENING_ONLY_NOT_LEAKPROOF_DRAINING_OR_DRYING_EVIDENCE",
            },
            "service_sequence": [step.manifest() for step in self.service_sequence],
            "cassette_withdrawal_travel_mm": CASSETTE_WITHDRAWAL_TRAVEL_MM,
            "retention_key_withdrawal_travel_mm": RETENTION_KEY_WITHDRAWAL_TRAVEL_MM,
            "package_clearance_reservation_mm": PACKAGE_CLEARANCE_RESERVATION_MM,
            "geometry_status": self.geometry_status,
            "compatibility_status": self.compatibility_status,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload


def build_realized_cleanser_storage(authority: Authority) -> RealizedCleanserStorage:
    if type(authority) is not Authority:
        raise RealizedCleanserStorageError("authority must be an exact Authority contract")
    architecture = build_cleanser_storage_architecture(authority)
    architecture.validate_current_authority(authority)

    cavity = _box(CAVITY_X_MM, CAVITY_Y_MM, CAVITY_Z_MM, CENTER_X_MM, CENTER_Y_MM, CENTER_Z_MM)
    body = _box(BODY_X_MM, BODY_Y_MM, BODY_Z_MM, CENTER_X_MM, CENTER_Y_MM, CENTER_Z_MM).cut(cavity)
    rear_z = CENTER_Z_MM - BODY_Z_MM / 2.0
    boss_z0 = rear_z - BOSS_PROJECTION_MM
    body = body.union(_z_ring(REFILL_X_MM, REFILL_Y_MM, boss_z0, REFILL_BOSS_OUTER_DIAMETER_MM, REFILL_BORE_DIAMETER_MM, 2.0))
    body = body.union(_z_ring(PURGE_X_MM, PURGE_Y_MM, boss_z0, PURGE_BOSS_OUTER_DIAMETER_MM, PURGE_BORE_DIAMETER_MM, 2.0))
    lateral_x = CENTER_X_MM + BODY_X_MM / 2.0
    outlet_boss_x0 = lateral_x - BOSS_BODY_OVERLAP_MM
    body = body.union(_x_ring(OUTLET_Y_MM, OUTLET_Z_MM, outlet_boss_x0, OUTLET_BOSS_OUTER_DIAMETER_MM, OUTLET_BORE_DIAMETER_MM, 2.0))
    body = body.union(_box(RETENTION_LUG_X_MM, RETENTION_LUG_Y_MM, RETENTION_LUG_Z_MM, CENTER_X_MM, RETENTION_LUG_CENTER_Y_MM, RETENTION_LUG_CENTER_Z_MM))

    refill_bore = _z_cylinder(REFILL_X_MM, REFILL_Y_MM, boss_z0 - 0.5, REFILL_BORE_DIAMETER_MM, 4.0)
    purge_bore = _z_cylinder(PURGE_X_MM, PURGE_Y_MM, boss_z0 - 0.5, PURGE_BORE_DIAMETER_MM, 4.0)
    outlet_bore = _x_cylinder(OUTLET_Y_MM, OUTLET_Z_MM, lateral_x - WALL_MM - 0.5, OUTLET_BORE_DIAMETER_MM, 4.0)
    key_bore = _x_cylinder(
        RETENTION_KEY_Y_MM,
        RETENTION_KEY_Z_MM,
        RETENTION_KEY_X_MIN_MM - 0.5,
        RETENTION_KEY_BORE_DIAMETER_MM,
        RETENTION_KEY_X_MAX_MM - RETENTION_KEY_X_MIN_MM + 1.0,
    )
    body = body.cut(refill_bore).cut(purge_bore).cut(outlet_bore).cut(key_bore)
    _one_valid_solid(body, "realized cleanser body")

    inner_z = (CRADLE_INNER_Z_MIN_MM + CRADLE_INNER_Z_MAX_MM) / 2.0
    inner_dz = CRADLE_INNER_Z_MAX_MM - CRADLE_INNER_Z_MIN_MM
    cradle = _box(CRADLE_OUTER_X_MM, CRADLE_OUTER_Y_MM, CRADLE_OUTER_Z_MM, CENTER_X_MM, CENTER_Y_MM, CENTER_Z_MM)
    cradle = cradle.cut(_box(CRADLE_INNER_X_MM, CRADLE_INNER_Y_MM, inner_dz, CENTER_X_MM, CENTER_Y_MM, inner_z))
    cradle = cradle.cut(_box(RETENTION_LUG_CHANNEL_X_MM, RETENTION_LUG_CHANNEL_Y_MM, RETENTION_LUG_CHANNEL_Z_MM, CENTER_X_MM, RETENTION_LUG_CENTER_Y_MM, RETENTION_LUG_CENTER_Z_MM))
    drain = _box(DRAIN_SLOT_X_MM, DRAIN_SLOT_Y_MM, DRAIN_SLOT_Z_MM, DRAIN_SLOT_CENTER_X_MM, DRAIN_SLOT_CENTER_Y_MM, DRAIN_SLOT_CENTER_Z_MM)
    cradle = cradle.cut(drain).cut(key_bore)
    passage_x0 = CENTER_X_MM + CRADLE_INNER_X_MM / 2.0 - 0.5
    cradle = cradle.cut(_x_cylinder(OUTLET_Y_MM, OUTLET_Z_MM, passage_x0, OUTLET_CRADLE_PASSAGE_DIAMETER_MM, CRADLE_WALL_MIN_MM + 2.0))
    _one_valid_solid(cradle, "realized cleanser cradle")

    key = _x_cylinder(
        RETENTION_KEY_Y_MM,
        RETENTION_KEY_Z_MM,
        RETENTION_KEY_X_MIN_MM,
        RETENTION_KEY_STEM_DIAMETER_MM,
        RETENTION_KEY_X_MAX_MM - RETENTION_KEY_X_MIN_MM,
    ).union(
        _x_cylinder(
            RETENTION_KEY_Y_MM,
            RETENTION_KEY_Z_MM,
            RETENTION_KEY_HEAD_X_MIN_MM,
            RETENTION_KEY_HEAD_DIAMETER_MM,
            RETENTION_KEY_HEAD_X_MAX_MM - RETENTION_KEY_HEAD_X_MIN_MM,
        )
    )
    _one_valid_solid(key, "realized cleanser retention key")

    refill_res = _z_cylinder(REFILL_X_MM, REFILL_Y_MM, boss_z0 - REFILL_CLOSURE_RESERVATION_DEPTH_MM, REFILL_CLOSURE_RESERVATION_DIAMETER_MM, REFILL_CLOSURE_RESERVATION_DEPTH_MM)
    purge_res = _z_cylinder(PURGE_X_MM, PURGE_Y_MM, boss_z0 - PURGE_CONNECTOR_RESERVATION_DEPTH_MM, PURGE_CONNECTOR_RESERVATION_DIAMETER_MM, PURGE_CONNECTOR_RESERVATION_DEPTH_MM)
    outlet_res = _x_cylinder(OUTLET_Y_MM, OUTLET_Z_MM, outlet_boss_x0 + 2.0, OUTLET_CONNECTOR_RESERVATION_DIAMETER_MM, OUTLET_CONNECTOR_RESERVATION_DEPTH_MM)

    body_bb = body.val().BoundingBox()
    cassette_sweep = _box(
        float(body_bb.xlen),
        float(body_bb.ylen),
        float(body_bb.zlen) + CASSETTE_WITHDRAWAL_TRAVEL_MM,
        (float(body_bb.xmin) + float(body_bb.xmax)) / 2.0,
        (float(body_bb.ymin) + float(body_bb.ymax)) / 2.0,
        (float(body_bb.zmin) + float(body_bb.zmax) - CASSETTE_WITHDRAWAL_TRAVEL_MM) / 2.0,
    )
    key_bb = key.val().BoundingBox()
    key_sweep = _box(
        float(key_bb.xlen) + RETENTION_KEY_WITHDRAWAL_TRAVEL_MM,
        float(key_bb.ylen),
        float(key_bb.zlen),
        (float(key_bb.xmin) + float(key_bb.xmax) + RETENTION_KEY_WITHDRAWAL_TRAVEL_MM) / 2.0,
        (float(key_bb.ymin) + float(key_bb.ymax)) / 2.0,
        (float(key_bb.zmin) + float(key_bb.zmax)) / 2.0,
    )

    sequence = (
        CleanserServiceStep(
            SERVICE_SEQUENCE_IDS[0],
            "cleanser_retention_key",
            (RETENTION_KEY_WITHDRAWAL_TRAVEL_MM, 0.0, 0.0),
            "MASK_REMOVED_UNPOWERED_CLEANSER_SERVICE",
        ),
        CleanserServiceStep(
            SERVICE_SEQUENCE_IDS[1],
            "cleanser_cassette",
            (0.0, 0.0, -CASSETTE_WITHDRAWAL_TRAVEL_MM),
            "RETENTION_KEY_RETRACTED_AND_MASK_REMOVED_UNPOWERED",
        ),
    )
    realized = RealizedCleanserStorage(
        source_authority_revision=str(authority.get("project", "authority_revision")),
        source_architecture_sha256=architecture.architecture_sha256,
        authored_against_git_sha=AUTHORED_AGAINST_MAIN_SHA,
        body_solid=body,
        internal_cavity_solid=cavity,
        cradle_solid=cradle,
        retention_key_solid=key,
        refill_bore_solid=refill_bore,
        purge_bore_solid=purge_bore,
        outlet_bore_solid=outlet_bore,
        refill_closure_reservation_solid=refill_res,
        purge_connector_reservation_solid=purge_res,
        outlet_connector_reservation_solid=outlet_res,
        drain_path_reference_solid=drain,
        cassette_service_sweep_solid=cassette_sweep,
        key_service_sweep_solid=key_sweep,
        service_sequence=sequence,
    )
    realized.validate_current_sources(authority)
    return realized
