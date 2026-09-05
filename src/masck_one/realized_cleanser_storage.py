"""Deterministic Cell 4 realization of the dedicated cleanser storage module.

This module converts the released cleanser-storage topology into bounded CAD geometry
without promoting storage, purge, compatibility, leakage, hygiene, service, or dosing
performance. All dimensions introduced here are explicit provisional engineering CAD
baselines, not supplier dimensions or authority values.
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

# Provisional cassette geometry. The released architecture deliberately does not carry
# a capacity. Capacity below is therefore geometric evidence owned by this realization,
# not a promoted architecture requirement or service-cadence claim.
CAVITY_X_MM = 16.0
CAVITY_Y_MM = 16.0
CAVITY_Z_MM = 12.0
WALL_MM = 1.0
BODY_X_MM = CAVITY_X_MM + 2.0 * WALL_MM
BODY_Y_MM = CAVITY_Y_MM + 2.0 * WALL_MM
BODY_Z_MM = CAVITY_Z_MM + 2.0 * WALL_MM
CENTER_X_MM = 29.0
CENTER_Y_MM = 76.0
CENTER_Z_MM = 8.0

# Drainable mounting sleeve, open to the posterior service side. The cassette receives
# 0.5 mm nominal digital running clearance on each X/Y side and a 0.25 mm anterior stop
# clearance. These values are CAD seeds only.
CRADLE_OUTER_X_MM = 22.0
CRADLE_OUTER_Y_MM = 22.0
CRADLE_OUTER_Z_MM = 16.0
CRADLE_INNER_X_MM = 19.0
CRADLE_INNER_Y_MM = 19.0
CRADLE_INNER_Z_MIN_MM = -0.50
CRADLE_INNER_Z_MAX_MM = 15.25
CRADLE_WALL_MIN_MM = (CRADLE_OUTER_X_MM - CRADLE_INNER_X_MM) / 2.0
DRAIN_SLOT_X_MM = 3.0
DRAIN_SLOT_Y_MM = 4.0
DRAIN_SLOT_Z_MM = 5.0
DRAIN_SLOT_CENTER_X_MM = 24.0
DRAIN_SLOT_CENTER_Y_MM = 65.5
DRAIN_SLOT_CENTER_Z_MM = 1.5

# Refill, purge, and outlet bores are actual through-wall geometry. Boss and external
# reservation values are provisional interface geometry, not selected fittings.
REFILL_X_MM = 26.0
REFILL_Y_MM = 80.0
REFILL_BORE_DIAMETER_MM = 4.0
REFILL_BOSS_OUTER_DIAMETER_MM = 7.0
REFILL_CLOSURE_RESERVATION_DIAMETER_MM = 9.0
REFILL_CLOSURE_RESERVATION_DEPTH_MM = 3.0

PURGE_X_MM = 32.0
PURGE_Y_MM = 72.0
PURGE_BORE_DIAMETER_MM = 2.0
PURGE_BOSS_OUTER_DIAMETER_MM = 4.0
PURGE_CONNECTOR_RESERVATION_DIAMETER_MM = 5.0
PURGE_CONNECTOR_RESERVATION_DEPTH_MM = 3.0

OUTLET_Y_MM = 69.0
OUTLET_Z_MM = 5.0
OUTLET_BORE_DIAMETER_MM = 2.0
OUTLET_BOSS_OUTER_DIAMETER_MM = 4.0
OUTLET_CONNECTOR_RESERVATION_DIAMETER_MM = 5.0
OUTLET_CONNECTOR_RESERVATION_DEPTH_MM = 3.0
OUTLET_CRADLE_PASSAGE_DIAMETER_MM = 5.0

BOSS_PROJECTION_MM = 1.0
BOSS_BODY_OVERLAP_MM = 1.0

# A removable cross-key passes through a molded cassette lug and both cradle sidewalls.
# It gives a real positive mounting feature while remaining an explicitly provisional
# part, with no release-force, wear, durability, or wet-hand-use claim.
RETENTION_LUG_X_MM = 4.0
RETENTION_LUG_Y_MM = 1.4
RETENTION_LUG_Z_MM = 3.0
RETENTION_LUG_CENTER_Y_MM = 66.7
RETENTION_LUG_CENTER_Z_MM = 1.8
RETENTION_KEY_Y_MM = RETENTION_LUG_CENTER_Y_MM
RETENTION_KEY_Z_MM = RETENTION_LUG_CENTER_Z_MM
RETENTION_KEY_STEM_DIAMETER_MM = 1.4
RETENTION_KEY_BORE_DIAMETER_MM = 1.8
RETENTION_KEY_HEAD_DIAMETER_MM = 3.5
RETENTION_KEY_X_MIN_MM = 17.0
RETENTION_KEY_X_MAX_MM = 41.0
RETENTION_KEY_HEAD_X_MIN_MM = 40.0
RETENTION_KEY_HEAD_X_MAX_MM = 42.0
RETENTION_LUG_CHANNEL_X_MM = 6.0
RETENTION_LUG_CHANNEL_Y_MM = 3.0
RETENTION_LUG_CHANNEL_Z_MM = 4.5

PACKAGE_CLEARANCE_RESERVATION_MM = 2.0
CASSETTE_WITHDRAWAL_TRAVEL_MM = 18.0
RETENTION_KEY_WITHDRAWAL_TRAVEL_MM = 26.0
SERVICE_SEQUENCE_IDS = (
    "CLEANSER-SERVICE-01-REMOVE-RETENTION-KEY",
    "CLEANSER-SERVICE-02-WITHDRAW-CASSETTE-POSTERIOR",
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_GIT_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


class RealizedCleanserStorageError(ValueError):
    pass


def _canonical_sha256(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise RealizedCleanserStorageError(f"{label} must be a canonical lowercase SHA-256")
    return value


def _git_sha(value: object, *, label: str) -> str:
    if type(value) is not str or _GIT_SHA_RE.fullmatch(value) is None:
        raise RealizedCleanserStorageError(f"{label} must be exact lowercase 40-hex")
    return value


def _box(width_x: float, height_y: float, depth_z: float, x: float, y: float, z: float) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(width_x, height_y, depth_z, centered=(True, True, True))
        .translate((x, y, z))
    )


def _z_cylinder(x: float, y: float, z_start: float, diameter: float, length: float) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .workplane(offset=z_start)
        .center(x, y)
        .circle(diameter / 2.0)
        .extrude(length)
    )


def _x_cylinder(y: float, z: float, x_start: float, diameter: float, length: float) -> cq.Workplane:
    return (
        cq.Workplane("YZ")
        .workplane(offset=x_start)
        .center(y, z)
        .circle(diameter / 2.0)
        .extrude(length)
    )


def _z_ring(x: float, y: float, z_start: float, outer_diameter: float, inner_diameter: float, length: float) -> cq.Workplane:
    return _z_cylinder(x, y, z_start, outer_diameter, length).cut(
        _z_cylinder(x, y, z_start - 0.1, inner_diameter, length + 0.2)
    )


def _x_ring(y: float, z: float, x_start: float, outer_diameter: float, inner_diameter: float, length: float) -> cq.Workplane:
    return _x_cylinder(y, z, x_start, outer_diameter, length).cut(
        _x_cylinder(y, z, x_start - 0.1, inner_diameter, length + 0.2)
    )


def _one_valid_solid(shape: cq.Workplane, *, label: str) -> None:
    if shape.solids().size() != 1 or not shape.val().isValid():
        raise RealizedCleanserStorageError(f"{label} must resolve as one valid deterministic solid")


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
        return self.internal_cavity_solid.val().Volume() / 1000.0

    @property
    def neutral_geometry_below_outlet_center_plane_mL(self) -> float:
        cavity_y_min = CENTER_Y_MM - CAVITY_Y_MM / 2.0
        band_height = OUTLET_Y_MM - cavity_y_min
        return CAVITY_X_MM * CAVITY_Z_MM * band_height / 1000.0

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()

    def validate_invariants(self) -> None:
        _canonical_sha256(self.source_architecture_sha256, label="cleanser architecture source")
        _git_sha(self.authored_against_git_sha, label="authored-against Git provenance")
        if type(self.source_authority_revision) is not str or not self.source_authority_revision:
            raise RealizedCleanserStorageError("realized cleanser geometry requires exact authority revision")
        if self.fluid_identity != "CLEANSER":
            raise RealizedCleanserStorageError("realized cleanser geometry must retain exact CLEANSER identity")
        if self.reservoir_id != CLEANSER_STORAGE_ID:
            raise RealizedCleanserStorageError("realized cleanser geometry changed the stable reservoir ID")
        if self.reservoir_cavity_classification != "WET_REMOVABLE":
            raise RealizedCleanserStorageError("cleanser cavity must remain WET_REMOVABLE")
        if self.mount_cavity_classification != "WET_DRAINABLE":
            raise RealizedCleanserStorageError("cleanser cradle must remain WET_DRAINABLE")
        if self.geometry_status != GEOMETRY_STATUS or self.compatibility_status != COMPATIBILITY_STATUS:
            raise RealizedCleanserStorageError("realized cleanser provenance/status boundary changed")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise RealizedCleanserStorageError("realized cleanser geometry cannot become physical validation evidence")
        if self.evidence_status != PHYSICAL_EVIDENCE_STATUS:
            raise RealizedCleanserStorageError("realized cleanser evidence firewall must remain exact")
        if tuple(step.step_id for step in self.service_sequence) != SERVICE_SEQUENCE_IDS:
            raise RealizedCleanserStorageError("cleanser service sequence order is not controlled")
        if not (RETENTION_KEY_STEM_DIAMETER_MM < RETENTION_KEY_BORE_DIAMETER_MM < RETENTION_KEY_HEAD_DIAMETER_MM):
            raise RealizedCleanserStorageError("retention key requires running clearance and a larger service head")
        if CRADLE_WALL_MIN_MM <= 0.0 or WALL_MM <= 0.0:
            raise RealizedCleanserStorageError("cleanser body and cradle require positive digital wall thickness")
        if PACKAGE_CLEARANCE_RESERVATION_MM <= 0.0:
            raise RealizedCleanserStorageError("package clearance reservation must be positive")

        for label, shape in (
            ("cleanser body", self.body_solid),
            ("cleanser cavity", self.internal_cavity_solid),
            ("cleanser cradle", self.cradle_solid),
            ("cleanser retention key", self.retention_key_solid),
            ("refill bore", self.refill_bore_solid),
            ("purge bore", self.purge_bore_solid),
            ("outlet bore", self.outlet_bore_solid),
            ("refill closure reservation", self.refill_closure_reservation_solid),
            ("purge connector reservation", self.purge_connector_reservation_solid),
            ("outlet connector reservation", self.outlet_connector_reservation_solid),
            ("drain path reference", self.drain_path_reference_solid),
            ("cassette service sweep", self.cassette_service_sweep_solid),
            ("key service sweep", self.key_service_sweep_solid),
        ):
            _one_valid_solid(shape, label=label)

        expected_volume_mL = CAVITY_X_MM * CAVITY_Y_MM * CAVITY_Z_MM / 1000.0
        if not math.isclose(self.geometric_cavity_volume_mL, expected_volume_mL, abs_tol=1e-8):
            raise RealizedCleanserStorageError("cleanser cavity B-rep volume does not match authored geometry")
        expected_dead_band_mL = CAVITY_X_MM * CAVITY_Z_MM * 1.0 / 1000.0
        if not math.isclose(self.neutral_geometry_below_outlet_center_plane_mL, expected_dead_band_mL, abs_tol=1e-12):
            raise RealizedCleanserStorageError("cleanser neutral geometric low-band accounting changed")

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
                "architecture": "POSTERIOR_SERVICE_SLIDE_IN_DRAINABLE_SLEEVE_WITH_REMOVABLE_CROSS_KEY",
                "cradle_outer_xyz_mm": [CRADLE_OUTER_X_MM, CRADLE_OUTER_Y_MM, CRADLE_OUTER_Z_MM],
                "cradle_inner_xy_mm": [CRADLE_INNER_X_MM, CRADLE_INNER_Y_MM],
                "cradle_inner_z_mm": [CRADLE_INNER_Z_MIN_MM, CRADLE_INNER_Z_MAX_MM],
                "minimum_sidewall_seed_mm": CRADLE_WALL_MIN_MM,
                "retention_key_stem_diameter_mm": RETENTION_KEY_STEM_DIAMETER_MM,
                "retention_key_bore_diameter_mm": RETENTION_KEY_BORE_DIAMETER_MM,
                "retention_key_head_diameter_mm": RETENTION_KEY_HEAD_DIAMETER_MM,
                "retention_status": "POSITIVE_DIGITAL_CAPTURE_PROVISIONAL_GEOMETRY_FORCE_WEAR_AND_DURABILITY_UNVALIDATED",
            },
            "ports": [
                {
                    "port_id": PORT_REFILL,
                    "fluid_identity": "CLEANSER",
                    "center_world_mm": [REFILL_X_MM, REFILL_Y_MM, CENTER_Z_MM - BODY_Z_MM / 2.0],
                    "axis": "+Z_FROM_POSTERIOR_SERVICE_SIDE_INTO_CASSETTE",
                    "bore_diameter_mm": REFILL_BORE_DIAMETER_MM,
                    "boss_outer_diameter_mm": REFILL_BOSS_OUTER_DIAMETER_MM,
                    "external_closure_reservation_diameter_mm": REFILL_CLOSURE_RESERVATION_DIAMETER_MM,
                    "closure_status": "RESERVATION_ONLY_CLOSURE_AND_SEAL_HARDWARE_NOT_SELECTED",
                },
                {
                    "port_id": PORT_OUTLET,
                    "fluid_identity": "CLEANSER",
                    "center_world_mm": [CENTER_X_MM - BODY_X_MM / 2.0, OUTLET_Y_MM, OUTLET_Z_MM],
                    "axis": "+X_FROM_MEDIAL_DEDICATED_METERING_HANDOFF_INTO_CASSETTE",
                    "bore_diameter_mm": OUTLET_BORE_DIAMETER_MM,
                    "boss_outer_diameter_mm": OUTLET_BOSS_OUTER_DIAMETER_MM,
                    "external_connector_reservation_diameter_mm": OUTLET_CONNECTOR_RESERVATION_DIAMETER_MM,
                    "isolation_status": "DEDICATED_CLEANSER_HANDOFF_ISOLATION_HARDWARE_AND_BACKFLOW_PERFORMANCE_UNVALIDATED",
                },
                {
                    "port_id": PORT_PURGE,
                    "fluid_identity": "CLEANSER",
                    "center_world_mm": [PURGE_X_MM, PURGE_Y_MM, CENTER_Z_MM - BODY_Z_MM / 2.0],
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
    outer = _box(BODY_X_MM, BODY_Y_MM, BODY_Z_MM, CENTER_X_MM, CENTER_Y_MM, CENTER_Z_MM)
    body = outer.cut(cavity)

    rear_face_z = CENTER_Z_MM - BODY_Z_MM / 2.0
    boss_start_z = rear_face_z - BOSS_PROJECTION_MM
    boss_length_z = BOSS_PROJECTION_MM + BOSS_BODY_OVERLAP_MM
    body = body.union(
        _z_ring(
            REFILL_X_MM,
            REFILL_Y_MM,
            boss_start_z,
            REFILL_BOSS_OUTER_DIAMETER_MM,
            REFILL_BORE_DIAMETER_MM,
            boss_length_z,
        )
    )
    body = body.union(
        _z_ring(
            PURGE_X_MM,
            PURGE_Y_MM,
            boss_start_z,
            PURGE_BOSS_OUTER_DIAMETER_MM,
            PURGE_BORE_DIAMETER_MM,
            boss_length_z,
        )
    )

    medial_face_x = CENTER_X_MM - BODY_X_MM / 2.0
    outlet_boss_start_x = medial_face_x - BOSS_PROJECTION_MM
    outlet_boss_length_x = BOSS_PROJECTION_MM + BOSS_BODY_OVERLAP_MM
    body = body.union(
        _x_ring(
            OUTLET_Y_MM,
            OUTLET_Z_MM,
            outlet_boss_start_x,
            OUTLET_BOSS_OUTER_DIAMETER_MM,
            OUTLET_BORE_DIAMETER_MM,
            outlet_boss_length_x,
        )
    )

    retention_lug = _box(
        RETENTION_LUG_X_MM,
        RETENTION_LUG_Y_MM,
        RETENTION_LUG_Z_MM,
        CENTER_X_MM,
        RETENTION_LUG_CENTER_Y_MM,
        RETENTION_LUG_CENTER_Z_MM,
    )
    body = body.union(retention_lug)

    refill_bore = _z_cylinder(
        REFILL_X_MM,
        REFILL_Y_MM,
        rear_face_z - BOSS_PROJECTION_MM - 0.5,
        REFILL_BORE_DIAMETER_MM,
        WALL_MM + BOSS_PROJECTION_MM + 2.0,
    )
    purge_bore = _z_cylinder(
        PURGE_X_MM,
        PURGE_Y_MM,
        rear_face_z - BOSS_PROJECTION_MM - 0.5,
        PURGE_BORE_DIAMETER_MM,
        WALL_MM + BOSS_PROJECTION_MM + 2.0,
    )
    outlet_bore = _x_cylinder(
        OUTLET_Y_MM,
        OUTLET_Z_MM,
        medial_face_x - BOSS_PROJECTION_MM - 0.5,
        OUTLET_BORE_DIAMETER_MM,
        WALL_MM + BOSS_PROJECTION_MM + 2.0,
    )
    key_bore = _x_cylinder(
        RETENTION_KEY_Y_MM,
        RETENTION_KEY_Z_MM,
        RETENTION_KEY_X_MIN_MM - 0.5,
        RETENTION_KEY_BORE_DIAMETER_MM,
        RETENTION_KEY_X_MAX_MM - RETENTION_KEY_X_MIN_MM + 1.0,
    )
    body = body.cut(refill_bore).cut(purge_bore).cut(outlet_bore).cut(key_bore)
    _one_valid_solid(body, label="realized cleanser body")

    cradle_outer = _box(
        CRADLE_OUTER_X_MM,
        CRADLE_OUTER_Y_MM,
        CRADLE_OUTER_Z_MM,
        CENTER_X_MM,
        CENTER_Y_MM,
        CENTER_Z_MM,
    )
    cradle_inner_z = (CRADLE_INNER_Z_MIN_MM + CRADLE_INNER_Z_MAX_MM) / 2.0
    cradle_inner_depth = CRADLE_INNER_Z_MAX_MM - CRADLE_INNER_Z_MIN_MM
    cradle_inner = _box(
        CRADLE_INNER_X_MM,
        CRADLE_INNER_Y_MM,
        cradle_inner_depth,
        CENTER_X_MM,
        CENTER_Y_MM,
        cradle_inner_z,
    )
    cradle = cradle_outer.cut(cradle_inner)

    lug_channel = _box(
        RETENTION_LUG_CHANNEL_X_MM,
        RETENTION_LUG_CHANNEL_Y_MM,
        RETENTION_LUG_CHANNEL_Z_MM,
        CENTER_X_MM,
        RETENTION_LUG_CENTER_Y_MM,
        RETENTION_LUG_CENTER_Z_MM,
    )
    drain_slot = _box(
        DRAIN_SLOT_X_MM,
        DRAIN_SLOT_Y_MM,
        DRAIN_SLOT_Z_MM,
        DRAIN_SLOT_CENTER_X_MM,
        DRAIN_SLOT_CENTER_Y_MM,
        DRAIN_SLOT_CENTER_Z_MM,
    )
    outlet_cradle_passage = _x_cylinder(
        OUTLET_Y_MM,
        OUTLET_Z_MM,
        CENTER_X_MM - CRADLE_OUTER_X_MM / 2.0 - 0.5,
        OUTLET_CRADLE_PASSAGE_DIAMETER_MM,
        CRADLE_WALL_MIN_MM + 2.0,
    )
    cradle = cradle.cut(lug_channel).cut(drain_slot).cut(key_bore).cut(outlet_cradle_passage)
    _one_valid_solid(cradle, label="realized cleanser cradle")

    key_stem = _x_cylinder(
        RETENTION_KEY_Y_MM,
        RETENTION_KEY_Z_MM,
        RETENTION_KEY_X_MIN_MM,
        RETENTION_KEY_STEM_DIAMETER_MM,
        RETENTION_KEY_X_MAX_MM - RETENTION_KEY_X_MIN_MM,
    )
    key_head = _x_cylinder(
        RETENTION_KEY_Y_MM,
        RETENTION_KEY_Z_MM,
        RETENTION_KEY_HEAD_X_MIN_MM,
        RETENTION_KEY_HEAD_DIAMETER_MM,
        RETENTION_KEY_HEAD_X_MAX_MM - RETENTION_KEY_HEAD_X_MIN_MM,
    )
    retention_key = key_stem.union(key_head)
    _one_valid_solid(retention_key, label="cleanser retention key")

    refill_closure_reservation = _z_cylinder(
        REFILL_X_MM,
        REFILL_Y_MM,
        boss_start_z - REFILL_CLOSURE_RESERVATION_DEPTH_MM,
        REFILL_CLOSURE_RESERVATION_DIAMETER_MM,
        REFILL_CLOSURE_RESERVATION_DEPTH_MM,
    )
    purge_connector_reservation = _z_cylinder(
        PURGE_X_MM,
        PURGE_Y_MM,
        boss_start_z - PURGE_CONNECTOR_RESERVATION_DEPTH_MM,
        PURGE_CONNECTOR_RESERVATION_DIAMETER_MM,
        PURGE_CONNECTOR_RESERVATION_DEPTH_MM,
    )
    outlet_connector_reservation = _x_cylinder(
        OUTLET_Y_MM,
        OUTLET_Z_MM,
        outlet_boss_start_x - OUTLET_CONNECTOR_RESERVATION_DEPTH_MM,
        OUTLET_CONNECTOR_RESERVATION_DIAMETER_MM,
        OUTLET_CONNECTOR_RESERVATION_DEPTH_MM,
    )

    body_bb = body.val().BoundingBox()
    cassette_service_sweep = _box(
        float(body_bb.xlen),
        float(body_bb.ylen),
        float(body_bb.zlen) + CASSETTE_WITHDRAWAL_TRAVEL_MM,
        (float(body_bb.xmin) + float(body_bb.xmax)) / 2.0,
        (float(body_bb.ymin) + float(body_bb.ymax)) / 2.0,
        (float(body_bb.zmin) + float(body_bb.zmax) - CASSETTE_WITHDRAWAL_TRAVEL_MM) / 2.0,
    )
    key_bb = retention_key.val().BoundingBox()
    key_service_sweep = _box(
        float(key_bb.xlen) + RETENTION_KEY_WITHDRAWAL_TRAVEL_MM,
        float(key_bb.ylen),
        float(key_bb.zlen),
        (float(key_bb.xmin) + float(key_bb.xmax) + RETENTION_KEY_WITHDRAWAL_TRAVEL_MM) / 2.0,
        (float(key_bb.ymin) + float(key_bb.ymax)) / 2.0,
        (float(key_bb.zmin) + float(key_bb.zmax)) / 2.0,
    )

    service_sequence = (
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
            "RETENTION_KEY_REMOVED_AND_MASK_REMOVED_UNPOWERED",
        ),
    )

    realized = RealizedCleanserStorage(
        source_authority_revision=str(authority.get("project", "authority_revision")),
        source_architecture_sha256=architecture.architecture_sha256,
        authored_against_git_sha=AUTHORED_AGAINST_MAIN_SHA,
        body_solid=body,
        internal_cavity_solid=cavity,
        cradle_solid=cradle,
        retention_key_solid=retention_key,
        refill_bore_solid=refill_bore,
        purge_bore_solid=purge_bore,
        outlet_bore_solid=outlet_bore,
        refill_closure_reservation_solid=refill_closure_reservation,
        purge_connector_reservation_solid=purge_connector_reservation,
        outlet_connector_reservation_solid=outlet_connector_reservation,
        drain_path_reference_solid=drain_slot,
        cassette_service_sweep_solid=cassette_service_sweep,
        key_service_sweep_solid=key_service_sweep,
        service_sequence=service_sequence,
    )
    realized.validate_current_sources(authority)
    return realized
