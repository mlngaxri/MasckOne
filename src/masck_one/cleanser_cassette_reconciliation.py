"""Cell 10 reconciliation of the removable CLEANSER cassette onto current main.

The exact Cell 4 PR #80 storage producer is vendored byte-for-byte on this branch.
This module consumes its body/cavity/cradle/port geometry, supersedes only the reviewed
friction-only retention key with positive rotate-to-release geometry, closes bounded
digital fit tolerances, and retains the strongest later complete-module service sweep as
reference-only migration protection.

Nothing here establishes cleanser chemistry compatibility, sealing, dose accuracy,
usable capacity, leakage, hygiene performance, service force, durability, or flow.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

import cadquery as cq

from .authority import Authority
from .cleanser_storage import CLEANSER_STORAGE_ID, PORT_IDS
from .realized_cleanser_storage import (
    BODY_X_MM,
    BODY_Y_MM,
    CASSETTE_WITHDRAWAL_TRAVEL_MM,
    CENTER_X_MM,
    CENTER_Y_MM,
    CENTER_Z_MM,
    CRADLE_INNER_X_MM,
    CRADLE_INNER_Y_MM,
    PACKAGE_CLEARANCE_RESERVATION_MM,
    RETENTION_KEY_BORE_DIAMETER_MM,
    RETENTION_KEY_HEAD_DIAMETER_MM,
    RETENTION_KEY_HEAD_X_MAX_MM,
    RETENTION_KEY_HEAD_X_MIN_MM,
    RETENTION_KEY_STEM_DIAMETER_MM,
    RETENTION_KEY_X_MAX_MM,
    RETENTION_KEY_X_MIN_MM,
    RETENTION_KEY_Y_MM,
    RETENTION_KEY_Z_MM,
    RealizedCleanserStorage,
    build_realized_cleanser_storage,
)

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SCHEMA = "MASCK_ONE_CELL10_RECONCILED_CLEANSER_CASSETTE_V1"
FLUID_IDENTITY = "CLEANSER"

SOURCE_PR_NUMBER = 80
SOURCE_HEAD_SHA = "6e3e05812406620072b37f54827b8345ed55ccea"
SOURCE_STORAGE_BLOB_SHA = "7c7eca7a12b14526946f759740161c33c13e5cb4"
SOURCE_SERVICE_ENVELOPE_BLOB_SHA = "1944487af9baa1c9fe27004eceed52eeb8a08167"
SOURCE_SERVICE_INTERFACE_BLOB_SHA = "7977c6d12e3b2883a246ca00d1570ad683229243"
RECONCILED_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"

GEOMETRY_STATUS = "CELL10_SOURCE_BOUND_RECONCILED_DIGITAL_CAD_NOT_SUPPLIER_SELECTED"
TOLERANCE_STATUS = "CELL10_PROVISIONAL_DIGITAL_TOLERANCE_BASELINE_NOT_PROCESS_CAPABILITY"
PROCESS_STATUS = "PROCESS_ACCESS_INTENT_ONLY_NOT_PRODUCTION_MOLDABILITY_EVIDENCE"
COMPATIBILITY_STATUS = (
    "BLOCKED_PENDING_SELECTED_CLEANSER_CHEMISTRY_WETTED_MATERIALS_AND_CONTROLLED_EVIDENCE"
)
EVIDENCE_STATUS = "DIGITAL_GEOMETRY_ONLY_NOT_PHYSICAL_PERFORMANCE_EVIDENCE"
SERVICE_STATUS = "MASK_REMOVED_UNPOWERED_DIGITAL_SERVICE_SEQUENCE_NOT_WET_USE_VALIDATION"

# Positive-retention repair. The tab is outside the -X cradle wall in the installed
# state. Locked orientation is tall in Z. A keyed Y-oriented slot admits it only after
# a controlled 90 degree rotation about +X.
RETENTION_TAB_CENTER_X_MM = 14.95
RETENTION_TAB_X_MM = 0.80
RETENTION_TAB_LOCKED_Y_MM = 1.00
RETENTION_TAB_LOCKED_Z_MM = 3.20
RETENTION_TAB_UNLOCKED_Y_MM = RETENTION_TAB_LOCKED_Z_MM
RETENTION_TAB_UNLOCKED_Z_MM = RETENTION_TAB_LOCKED_Y_MM

RETENTION_SLOT_CENTER_X_MM = 16.25
RETENTION_SLOT_X_MM = 2.00
RETENTION_SLOT_Y_MM = 3.60
RETENTION_SLOT_Z_MM = 1.40

KEY_UNLOCK_ROTATION_DEG = -90.0
RETENTION_KEY_WITHDRAWAL_TRAVEL_MM = 14.0

# Digital tolerance closure only. These do not assert molding or machining capability.
BODY_XY_TOL_MM = 0.10
CRADLE_INNER_XY_TOL_MM = 0.10
KEY_STEM_TOL_MM = 0.05
KEY_BORE_TOL_MM = 0.05
TAB_SPAN_TOL_MM = 0.05
SLOT_SPAN_TOL_MM = 0.05

# Exact complete successor-module envelope from the inspected PR #80 producer chain:
# body + refill/purge closure + closure key, swept -18 mm in Z.
UPSTREAM_MODULE_X_BOUNDS_MM = (17.5, 36.5)
UPSTREAM_MODULE_Y_BOUNDS_MM = (62.0, 81.3)
UPSTREAM_MODULE_Z_BOUNDS_MM = (-22.1, 15.0)

PHYSICAL_SOLID_IDS = (
    "MASCK_ONE-CLEANSER-CASSETTE-BODY",
    "MASCK_ONE-CLEANSER-CASSETTE-CRADLE",
    "MASCK_ONE-CLEANSER-CASSETTE-RETENTION-KEY",
)
REFERENCE_SOLID_IDS = (
    "MASCK_ONE-CLEANSER-CASSETTE-CAVITY-REFERENCE",
    "MASCK_ONE-CLEANSER-CASSETTE-REFILL-BORE-REFERENCE",
    "MASCK_ONE-CLEANSER-CASSETTE-PURGE-BORE-REFERENCE",
    "MASCK_ONE-CLEANSER-CASSETTE-OUTLET-BORE-REFERENCE",
    "MASCK_ONE-CLEANSER-CASSETTE-DRAIN-REFERENCE",
    "MASCK_ONE-CLEANSER-CASSETTE-KEY-UNLOCK-SWEEP-REFERENCE",
    "MASCK_ONE-CLEANSER-CASSETTE-KEY-WITHDRAW-SWEEP-REFERENCE",
    "MASCK_ONE-CLEANSER-CASSETTE-WITHDRAW-SWEEP-REFERENCE",
    "MASCK_ONE-CLEANSER-UPSTREAM-COMPLETE-MODULE-SWEEP-REFERENCE",
)

SERVICE_SEQUENCE_IDS = (
    "CLEANSER-SERVICE-01-ROTATE-RETENTION-KEY-TO-SLOT",
    "CLEANSER-SERVICE-02-WITHDRAW-RETENTION-KEY",
    "CLEANSER-SERVICE-03-WITHDRAW-CASSETTE-POSTERIOR",
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_GIT_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


class CleanserCassetteReconciliationError(ValueError):
    pass


def _box(dx: float, dy: float, dz: float, x: float, y: float, z: float) -> cq.Workplane:
    return cq.Workplane("XY").box(dx, dy, dz, centered=(True, True, True)).translate((x, y, z))


def _x_cylinder(y: float, z: float, x0: float, diameter: float, length: float) -> cq.Workplane:
    return cq.Workplane("YZ").workplane(offset=x0).center(y, z).circle(diameter / 2.0).extrude(length)


def _one_valid_solid(shape: cq.Workplane, label: str) -> None:
    if shape.solids().size() != 1 or not shape.val().isValid() or shape.val().Volume() <= 0.0:
        raise CleanserCassetteReconciliationError(
            f"{label} must be one positive valid deterministic solid"
        )


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    return float(a.val().intersect(b.val()).Volume())


def _bounds(shape: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = shape.val().BoundingBox()
    return (
        float(bb.xmin),
        float(bb.xmax),
        float(bb.ymin),
        float(bb.ymax),
        float(bb.zmin),
        float(bb.zmax),
    )


@dataclass(frozen=True, slots=True)
class CleanserServiceStep:
    step_id: str
    moving_part: str
    motion_kind: str
    translation_world_mm: tuple[float, float, float]
    rotation_axis_world: tuple[float, float, float] | None
    rotation_deg: float | None
    precondition: str

    def __post_init__(self) -> None:
        if self.step_id not in SERVICE_SEQUENCE_IDS:
            raise CleanserCassetteReconciliationError(
                f"unknown cleanser service step {self.step_id!r}"
            )
        if type(self.moving_part) is not str or not self.moving_part:
            raise CleanserCassetteReconciliationError(
                "service moving part must be exact nonblank text"
            )
        if self.motion_kind not in {"ROTATION", "TRANSLATION"}:
            raise CleanserCassetteReconciliationError("service motion kind must be controlled")
        if type(self.translation_world_mm) is not tuple or len(self.translation_world_mm) != 3:
            raise CleanserCassetteReconciliationError(
                "service translation must be an exact three-vector"
            )
        if not all(
            type(value) in (int, float) and math.isfinite(float(value))
            for value in self.translation_world_mm
        ):
            raise CleanserCassetteReconciliationError(
                "service translation must contain finite numeric scalars"
            )
        if self.motion_kind == "ROTATION":
            if self.rotation_axis_world != (1.0, 0.0, 0.0):
                raise CleanserCassetteReconciliationError(
                    "retention key unlock rotation must remain about +X"
                )
            if type(self.rotation_deg) not in (int, float) or not math.isfinite(
                float(self.rotation_deg)
            ):
                raise CleanserCassetteReconciliationError("rotation angle must be finite")
            if float(self.rotation_deg) != KEY_UNLOCK_ROTATION_DEG:
                raise CleanserCassetteReconciliationError(
                    "retention key unlock angle changed"
                )
        else:
            if self.rotation_axis_world is not None or self.rotation_deg is not None:
                raise CleanserCassetteReconciliationError(
                    "translation step cannot carry rotation fields"
                )
            if math.sqrt(
                sum(float(value) ** 2 for value in self.translation_world_mm)
            ) <= 0.0:
                raise CleanserCassetteReconciliationError(
                    "translation service motion must be nonzero"
                )
        if type(self.precondition) is not str or not self.precondition:
            raise CleanserCassetteReconciliationError(
                "service precondition must be exact nonblank text"
            )

    def manifest(self) -> dict[str, object]:
        return {
            "step_id": self.step_id,
            "moving_part": self.moving_part,
            "motion_kind": self.motion_kind,
            "translation_world_mm": list(self.translation_world_mm),
            "rotation_axis_world": (
                None if self.rotation_axis_world is None else list(self.rotation_axis_world)
            ),
            "rotation_deg": self.rotation_deg,
            "precondition": self.precondition,
            "evidence_status": SERVICE_STATUS,
        }


@dataclass(frozen=True, slots=True)
class ReconciledCleanserCassette:
    source_authority_revision: str
    source_storage_manifest_sha256: str
    source_storage: RealizedCleanserStorage
    body_solid: cq.Workplane
    cavity_reference_solid: cq.Workplane
    cradle_solid: cq.Workplane
    retention_key_locked_solid: cq.Workplane
    retention_key_unlocked_solid: cq.Workplane
    key_unlock_rotation_sweep_reference_solid: cq.Workplane
    key_withdrawal_sweep_reference_solid: cq.Workplane
    cassette_withdrawal_sweep_reference_solid: cq.Workplane
    upstream_complete_module_service_envelope_reference_solid: cq.Workplane
    service_sequence: tuple[CleanserServiceStep, ...]
    fluid_identity: str = FLUID_IDENTITY
    reservoir_id: str = CLEANSER_STORAGE_ID
    geometry_status: str = GEOMETRY_STATUS
    compatibility_status: str = COMPATIBILITY_STATUS
    physical_validation_eligible: bool = False
    evidence_status: str = EVIDENCE_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    @property
    def geometric_cavity_volume_mL(self) -> float:
        return float(self.cavity_reference_solid.val().Volume()) / 1000.0

    @property
    def cassette_min_side_clearance_mm(self) -> float:
        return (
            (CRADLE_INNER_X_MM - CRADLE_INNER_XY_TOL_MM)
            - (BODY_X_MM + BODY_XY_TOL_MM)
        ) / 2.0

    @property
    def key_min_diametral_clearance_mm(self) -> float:
        return (RETENTION_KEY_BORE_DIAMETER_MM - KEY_BORE_TOL_MM) - (
            RETENTION_KEY_STEM_DIAMETER_MM + KEY_STEM_TOL_MM
        )

    @property
    def unlocked_slot_min_clearance_yz_mm(self) -> tuple[float, float]:
        y = (RETENTION_SLOT_Y_MM - SLOT_SPAN_TOL_MM) - (
            RETENTION_TAB_UNLOCKED_Y_MM + TAB_SPAN_TOL_MM
        )
        z = (RETENTION_SLOT_Z_MM - SLOT_SPAN_TOL_MM) - (
            RETENTION_TAB_UNLOCKED_Z_MM + TAB_SPAN_TOL_MM
        )
        return y, z

    @property
    def locked_tab_min_block_overhang_each_side_mm(self) -> float:
        return (
            (RETENTION_TAB_LOCKED_Z_MM - TAB_SPAN_TOL_MM)
            - (RETENTION_SLOT_Z_MM + SLOT_SPAN_TOL_MM)
        ) / 2.0

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def validate_invariants(self) -> None:
        for label, value in (
            ("source head", SOURCE_HEAD_SHA),
            ("source storage blob", SOURCE_STORAGE_BLOB_SHA),
            ("source service envelope blob", SOURCE_SERVICE_ENVELOPE_BLOB_SHA),
            ("source service interface blob", SOURCE_SERVICE_INTERFACE_BLOB_SHA),
            ("reconciled main", RECONCILED_MAIN_SHA),
        ):
            if type(value) is not str or _GIT_SHA_RE.fullmatch(value) is None:
                raise CleanserCassetteReconciliationError(
                    f"{label} must be exact lowercase 40-hex"
                )
        if (
            type(self.source_storage_manifest_sha256) is not str
            or _SHA256_RE.fullmatch(self.source_storage_manifest_sha256) is None
        ):
            raise CleanserCassetteReconciliationError(
                "source storage manifest must be canonical lowercase SHA-256"
            )
        if self.source_storage_manifest_sha256 != self.source_storage.manifest_sha256:
            raise CleanserCassetteReconciliationError(
                "reconciled cassette source storage manifest drifted"
            )
        if self.fluid_identity != "CLEANSER" or self.reservoir_id != CLEANSER_STORAGE_ID:
            raise CleanserCassetteReconciliationError(
                "cassette must retain exact CLEANSER identity and stable reservoir ID"
            )
        if self.geometry_status != GEOMETRY_STATUS:
            raise CleanserCassetteReconciliationError("reconciled geometry status changed")
        if self.compatibility_status != COMPATIBILITY_STATUS:
            raise CleanserCassetteReconciliationError(
                "cleanser compatibility evidence boundary changed"
            )
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise CleanserCassetteReconciliationError(
                "digital cleanser cassette cannot become physical validation evidence"
            )
        if self.evidence_status != EVIDENCE_STATUS:
            raise CleanserCassetteReconciliationError(
                "cleanser cassette evidence firewall changed"
            )
        if set(PHYSICAL_SOLID_IDS) & set(REFERENCE_SOLID_IDS):
            raise CleanserCassetteReconciliationError(
                "physical and reference solid identities must remain disjoint"
            )
        if len(set(PHYSICAL_SOLID_IDS)) != len(PHYSICAL_SOLID_IDS) or len(
            set(REFERENCE_SOLID_IDS)
        ) != len(REFERENCE_SOLID_IDS):
            raise CleanserCassetteReconciliationError("solid identities must remain unique")
        if tuple(step.step_id for step in self.service_sequence) != SERVICE_SEQUENCE_IDS:
            raise CleanserCassetteReconciliationError(
                "cleanser service sequence order changed"
            )
        if self.cassette_min_side_clearance_mm <= 0.0:
            raise CleanserCassetteReconciliationError(
                "cassette worst-case sliding clearance is not positive"
            )
        if self.key_min_diametral_clearance_mm <= 0.0:
            raise CleanserCassetteReconciliationError(
                "retention key worst-case running clearance is not positive"
            )
        if min(self.unlocked_slot_min_clearance_yz_mm) <= 0.0:
            raise CleanserCassetteReconciliationError(
                "unlocked bayonet tab does not clear keyed slot at tolerance limits"
            )
        if self.locked_tab_min_block_overhang_each_side_mm <= 0.0:
            raise CleanserCassetteReconciliationError(
                "locked bayonet tab loses positive blocking at tolerance limits"
            )

        for label, shape in (
            ("body", self.body_solid),
            ("cavity reference", self.cavity_reference_solid),
            ("cradle", self.cradle_solid),
            ("locked retention key", self.retention_key_locked_solid),
            ("unlocked retention key", self.retention_key_unlocked_solid),
            ("unlock rotation sweep", self.key_unlock_rotation_sweep_reference_solid),
            ("key withdrawal sweep", self.key_withdrawal_sweep_reference_solid),
            ("cassette withdrawal sweep", self.cassette_withdrawal_sweep_reference_solid),
            (
                "upstream complete module service envelope",
                self.upstream_complete_module_service_envelope_reference_solid,
            ),
        ):
            _one_valid_solid(shape, f"cleanser {label}")

        if not math.isclose(self.geometric_cavity_volume_mL, 3.072, abs_tol=1e-8):
            raise CleanserCassetteReconciliationError(
                "source-consumed cleanser cavity volume changed"
            )
        for label, a, b in (
            ("body/cradle", self.body_solid, self.cradle_solid),
            ("body/key", self.body_solid, self.retention_key_locked_solid),
            ("cradle/key", self.cradle_solid, self.retention_key_locked_solid),
        ):
            if _intersection_volume(a, b) > 1e-7:
                raise CleanserCassetteReconciliationError(
                    f"assembled cleanser {label} material overlaps"
                )

        # A small attempted +X withdrawal must hit the cradle while locked, and must
        # enter the keyed slot without collision after the controlled unlock rotation.
        locked_probe = self.retention_key_locked_solid.translate((0.5, 0.0, 0.0))
        unlocked_probe = self.retention_key_unlocked_solid.translate((0.5, 0.0, 0.0))
        if _intersection_volume(locked_probe, self.cradle_solid) <= 1e-5:
            raise CleanserCassetteReconciliationError(
                "locked retention key lacks positive cradle blocking"
            )
        if _intersection_volume(unlocked_probe, self.cradle_solid) > 1e-7:
            raise CleanserCassetteReconciliationError(
                "unlocked retention key cannot enter keyed withdrawal slot"
            )

    def validate_current_sources(self, authority: Authority) -> RealizedCleanserStorage:
        if type(authority) is not Authority:
            raise CleanserCassetteReconciliationError(
                "authority must be an exact Authority contract"
            )
        source = build_realized_cleanser_storage(authority)
        source.validate_current_sources(authority)
        if self.source_authority_revision != str(
            authority.get("project", "authority_revision")
        ):
            raise CleanserCassetteReconciliationError(
                "reconciled cleanser cassette is stale for current authority"
            )
        if source.manifest_sha256 != self.source_storage_manifest_sha256:
            raise CleanserCassetteReconciliationError(
                "reconciled cleanser cassette is stale for source storage manifest"
            )
        if tuple(port.port_id for port in source.validate_current_sources(authority).ports) != PORT_IDS:
            raise CleanserCassetteReconciliationError(
                "cleanser source port identity drifted"
            )
        return source

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        source = self.source_storage
        source_manifest = source.manifest()
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "world_frame_id": WORLD_FRAME_ID,
            "source": {
                "candidate_pr": SOURCE_PR_NUMBER,
                "candidate_head_sha": SOURCE_HEAD_SHA,
                "candidate_storage_blob_sha": SOURCE_STORAGE_BLOB_SHA,
                "candidate_storage_manifest_sha256": self.source_storage_manifest_sha256,
                "candidate_service_interface_blob_sha": SOURCE_SERVICE_INTERFACE_BLOB_SHA,
                "candidate_service_envelope_blob_sha": SOURCE_SERVICE_ENVELOPE_BLOB_SHA,
                "reconciled_main_sha": RECONCILED_MAIN_SHA,
                "donor_retention_disposition": (
                    "SUPERSEDED_CELL5_REVIEW_REJECTED_FRICTION_ONLY_WITHDRAWAL_RESISTANCE"
                ),
            },
            "source_authority_revision": self.source_authority_revision,
            "reservoir_id": self.reservoir_id,
            "fluid_identity": self.fluid_identity,
            "geometry_roles": {
                "physical_material": list(PHYSICAL_SOLID_IDS),
                "reference_only": list(REFERENCE_SOLID_IDS),
                "mixing_rule": (
                    "REFERENCE_KEEP_OUT_SERVICE_CAVITY_AND_SWEEP_SOLIDS_MUST_NOT_ENTER_PHYSICAL_MATERIAL"
                ),
            },
            "source_consumed_geometry": {
                "center_world_mm": source_manifest["geometry"]["center_world_mm"],
                "internal_cavity_xyz_mm": source_manifest["geometry"][
                    "internal_cavity_xyz_mm"
                ],
                "body_outer_xyz_mm": source_manifest["geometry"]["body_outer_xyz_mm"],
                "geometric_cavity_volume_mL": self.geometric_cavity_volume_mL,
                "gross_volume_role": (
                    "GEOMETRIC_ACCOUNTING_ONLY_NOT_USABLE_CAPACITY_DOSE_OR_REFILL_CADENCE"
                ),
                "ports": source_manifest["ports"],
                "drain_slot": source_manifest["wet_separation"],
            },
            "retention": {
                "architecture": (
                    "ROTATE_TO_RELEASE_BAYONET_CROSS_KEY_WITH_EXTERNAL_LOCKING_TAB"
                ),
                "positive_load_path": (
                    "LOCKED_TAB_TO_CRADLE_WALL_GEOMETRIC_BLOCK_NOT_FRICTION"
                ),
                "unlock_rotation_axis_world": [1.0, 0.0, 0.0],
                "unlock_rotation_deg": KEY_UNLOCK_ROTATION_DEG,
                "retention_force_status": "UNKNOWN_PHYSICAL_GATE",
                "wear_durability_status": "UNKNOWN_PHYSICAL_GATE",
            },
            "tolerance_stack": {
                "status": TOLERANCE_STATUS,
                "body_xy_plus_minus_mm": BODY_XY_TOL_MM,
                "cradle_inner_xy_plus_minus_mm": CRADLE_INNER_XY_TOL_MM,
                "cassette_min_side_clearance_mm": self.cassette_min_side_clearance_mm,
                "key_stem_plus_minus_mm": KEY_STEM_TOL_MM,
                "key_bore_plus_minus_mm": KEY_BORE_TOL_MM,
                "key_min_diametral_clearance_mm": self.key_min_diametral_clearance_mm,
                "tab_span_plus_minus_mm": TAB_SPAN_TOL_MM,
                "slot_span_plus_minus_mm": SLOT_SPAN_TOL_MM,
                "unlocked_slot_min_clearance_yz_mm": list(
                    self.unlocked_slot_min_clearance_yz_mm
                ),
                "locked_tab_min_block_overhang_each_side_mm": (
                    self.locked_tab_min_block_overhang_each_side_mm
                ),
            },
            "dfm_process_access": {
                "status": PROCESS_STATUS,
                "retention_cross_bore": (
                    "SECONDARY_DRILL_OR_CONTROLLED_SIDE_ACTION_REQUIRED"
                ),
                "retention_keyed_slot": (
                    "SECONDARY_SLOT_MILL_OR_CONTROLLED_SIDE_ACTION_REQUIRED"
                ),
                "source_multi_axis_fluid_bores": (
                    "SECONDARY_DRILL_OR_CONTROLLED_MULTI_AXIS_TOOL_ACCESS_REQUIRED"
                ),
                "production_process_selected": None,
            },
            "hygiene": {
                "reservoir_cavity_classification": source.reservoir_cavity_classification,
                "mount_cavity_classification": source.mount_cavity_classification,
                "performance_status": (
                    "CLASSIFICATION_ONLY_DRAINING_DRYING_AND_CLEANABILITY_UNVALIDATED"
                ),
            },
            "service": {
                "sequence": [step.manifest() for step in self.service_sequence],
                "cassette_withdrawal_travel_mm": CASSETTE_WITHDRAWAL_TRAVEL_MM,
                "retention_key_withdrawal_travel_mm": RETENTION_KEY_WITHDRAWAL_TRAVEL_MM,
                "upstream_successor_complete_module_sweep_bounds_world_mm": {
                    "x": list(UPSTREAM_MODULE_X_BOUNDS_MM),
                    "y": list(UPSTREAM_MODULE_Y_BOUNDS_MM),
                    "z": list(UPSTREAM_MODULE_Z_BOUNDS_MM),
                },
                "upstream_complete_module_sweep_role": (
                    "REFERENCE_ONLY_FUTURE_FILL_VENT_PICKUP_SERVICE_MIGRATION_GUARD"
                ),
                "physical_service_status": "UNKNOWN_NOT_WET_HAND_VALIDATED",
            },
            "package_clearance_reservation_mm": PACKAGE_CLEARANCE_RESERVATION_MM,
            "cradle_to_frame_attachment": (
                "UNRESOLVED_CROSS_LANE_POSITIVE_ATTACHMENT_REQUIRED"
            ),
            "development_assembly_material_inclusion": (
                "BLOCKED_UNTIL_CRADLE_TO_FRAME_POSITIVE_ATTACHMENT_IS_RELEASED"
            ),
            "geometry_status": self.geometry_status,
            "compatibility_status": self.compatibility_status,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload


def _retention_key(*, locked: bool) -> cq.Workplane:
    stem = _x_cylinder(
        RETENTION_KEY_Y_MM,
        RETENTION_KEY_Z_MM,
        RETENTION_KEY_X_MIN_MM,
        RETENTION_KEY_STEM_DIAMETER_MM,
        RETENTION_KEY_X_MAX_MM - RETENTION_KEY_X_MIN_MM,
    )
    head = _x_cylinder(
        RETENTION_KEY_Y_MM,
        RETENTION_KEY_Z_MM,
        RETENTION_KEY_HEAD_X_MIN_MM,
        RETENTION_KEY_HEAD_DIAMETER_MM,
        RETENTION_KEY_HEAD_X_MAX_MM - RETENTION_KEY_HEAD_X_MIN_MM,
    )
    tab_y = RETENTION_TAB_LOCKED_Y_MM if locked else RETENTION_TAB_UNLOCKED_Y_MM
    tab_z = RETENTION_TAB_LOCKED_Z_MM if locked else RETENTION_TAB_UNLOCKED_Z_MM
    tab = _box(
        RETENTION_TAB_X_MM,
        tab_y,
        tab_z,
        RETENTION_TAB_CENTER_X_MM,
        RETENTION_KEY_Y_MM,
        RETENTION_KEY_Z_MM,
    )
    return stem.union(head).union(tab)


def build_reconciled_cleanser_cassette(authority: Authority) -> ReconciledCleanserCassette:
    if type(authority) is not Authority:
        raise CleanserCassetteReconciliationError(
            "authority must be an exact Authority contract"
        )

    source = build_realized_cleanser_storage(authority)
    source.validate_current_sources(authority)

    keyed_slot = _box(
        RETENTION_SLOT_X_MM,
        RETENTION_SLOT_Y_MM,
        RETENTION_SLOT_Z_MM,
        RETENTION_SLOT_CENTER_X_MM,
        RETENTION_KEY_Y_MM,
        RETENTION_KEY_Z_MM,
    )
    cradle = source.cradle_solid.cut(keyed_slot)
    _one_valid_solid(cradle, "reconciled cleanser cradle")

    locked_key = _retention_key(locked=True)
    unlocked_key = _retention_key(locked=False)
    _one_valid_solid(locked_key, "locked cleanser retention key")
    _one_valid_solid(unlocked_key, "unlocked cleanser retention key")

    tab_radius = math.sqrt(
        (RETENTION_TAB_LOCKED_Y_MM / 2.0) ** 2
        + (RETENTION_TAB_LOCKED_Z_MM / 2.0) ** 2
    )
    rotation_sweep = _x_cylinder(
        RETENTION_KEY_Y_MM,
        RETENTION_KEY_Z_MM,
        RETENTION_TAB_CENTER_X_MM - RETENTION_TAB_X_MM / 2.0,
        2.0 * tab_radius,
        RETENTION_TAB_X_MM,
    )

    key_bb = unlocked_key.val().BoundingBox()
    key_sweep = _box(
        float(key_bb.xlen) + RETENTION_KEY_WITHDRAWAL_TRAVEL_MM,
        float(key_bb.ylen),
        float(key_bb.zlen),
        (
            float(key_bb.xmin)
            + float(key_bb.xmax)
            + RETENTION_KEY_WITHDRAWAL_TRAVEL_MM
        )
        / 2.0,
        (float(key_bb.ymin) + float(key_bb.ymax)) / 2.0,
        (float(key_bb.zmin) + float(key_bb.zmax)) / 2.0,
    )

    ux0, ux1 = UPSTREAM_MODULE_X_BOUNDS_MM
    uy0, uy1 = UPSTREAM_MODULE_Y_BOUNDS_MM
    uz0, uz1 = UPSTREAM_MODULE_Z_BOUNDS_MM
    upstream_envelope = _box(
        ux1 - ux0,
        uy1 - uy0,
        uz1 - uz0,
        (ux0 + ux1) / 2.0,
        (uy0 + uy1) / 2.0,
        (uz0 + uz1) / 2.0,
    )

    sequence = (
        CleanserServiceStep(
            SERVICE_SEQUENCE_IDS[0],
            "cleanser_retention_key",
            "ROTATION",
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            KEY_UNLOCK_ROTATION_DEG,
            "MASK_REMOVED_UNPOWERED_KEY_HEAD_ACCESSIBLE",
        ),
        CleanserServiceStep(
            SERVICE_SEQUENCE_IDS[1],
            "cleanser_retention_key",
            "TRANSLATION",
            (RETENTION_KEY_WITHDRAWAL_TRAVEL_MM, 0.0, 0.0),
            None,
            None,
            "RETENTION_KEY_ROTATED_TO_KEYED_SLOT_MASK_REMOVED_UNPOWERED",
        ),
        CleanserServiceStep(
            SERVICE_SEQUENCE_IDS[2],
            "cleanser_cassette",
            "TRANSLATION",
            (0.0, 0.0, -CASSETTE_WITHDRAWAL_TRAVEL_MM),
            None,
            None,
            "RETENTION_KEY_WITHDRAWN_MASK_REMOVED_UNPOWERED",
        ),
    )

    reconciled = ReconciledCleanserCassette(
        source_authority_revision=str(authority.get("project", "authority_revision")),
        source_storage_manifest_sha256=source.manifest_sha256,
        source_storage=source,
        body_solid=source.body_solid,
        cavity_reference_solid=source.internal_cavity_solid,
        cradle_solid=cradle,
        retention_key_locked_solid=locked_key,
        retention_key_unlocked_solid=unlocked_key,
        key_unlock_rotation_sweep_reference_solid=rotation_sweep,
        key_withdrawal_sweep_reference_solid=key_sweep,
        cassette_withdrawal_sweep_reference_solid=source.cassette_service_sweep_solid,
        upstream_complete_module_service_envelope_reference_solid=upstream_envelope,
        service_sequence=sequence,
    )
    reconciled.validate_current_sources(authority)
    return reconciled
