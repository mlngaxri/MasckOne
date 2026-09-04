"""Manual A frame-to-shell attachment and geometric load-path closure.

This module addresses a specific evidence gap: a closed structural frame does not by
itself prove that retention or actuator reaction loads can reach the product shell.
Three candidate bridges create explicit 3D frame-to-shell intersections while leaving
the lower-centre cartridge service corridor unoccupied.

The resulting connectivity is geometry evidence only. Material, fastener/adhesive
selection, stiffness, fatigue, shell bearing stress and physical load capacity remain
unresolved and must not be inferred from geometric closure.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority, load_authority
from .mechanical_integration import MechanicalRealization, RealizedPart, build_mechanical_realization
from .model import MasckOneModel, build_model
from .spatial import Point3
from .whole_product_interference import build_whole_product_interference_audit, exact_intersection_volume_mm3


SCHEMA = "MASCK_ONE_FRAME_SHELL_ATTACHMENT_V1"
BRIDGE_DEPTH_Z_MM = 4.4
LATERAL_BRIDGE_X_MM = 76.0
LATERAL_BRIDGE_SIZE_XYZ_MM = (4.0, 12.0, BRIDGE_DEPTH_Z_MM)
SUPERIOR_BRIDGE_Y_MM = 100.0
SUPERIOR_BRIDGE_SIZE_XYZ_MM = (14.0, 4.0, BRIDGE_DEPTH_Z_MM)

BRIDGE_IDS = (
    "FRAME-SHELL-BRIDGE-WEARER-LEFT",
    "FRAME-SHELL-BRIDGE-WEARER-RIGHT",
    "FRAME-SHELL-BRIDGE-SUPERIOR",
)


class FrameShellAttachmentError(ValueError):
    pass


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise FrameShellAttachmentError(f"{label} must be exact nonblank text")
    return value


def _box(size_xyz_mm: tuple[float, float, float], center: Point3) -> cq.Workplane:
    if type(size_xyz_mm) is not tuple or len(size_xyz_mm) != 3:
        raise FrameShellAttachmentError("bridge size must be an exact XYZ tuple")
    if any(type(value) not in (int, float) or not math.isfinite(float(value)) or float(value) <= 0.0 for value in size_xyz_mm):
        raise FrameShellAttachmentError("bridge sizes must be finite and positive")
    return cq.Workplane("XY").box(*size_xyz_mm, centered=(True, True, True)).translate(center.as_tuple())


@dataclass(frozen=True, slots=True)
class FrameShellBridge:
    bridge_id: str
    solid: cq.Workplane
    frame_intersection_mm3: float
    shell_intersection_mm3: float
    geometry_status: str
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.bridge_id, "bridge_id")
        if self.bridge_id not in BRIDGE_IDS:
            raise FrameShellAttachmentError("bridge ID is not controlled")
        shape = self.solid.val()
        if not shape.isValid() or float(shape.Volume()) <= 0.0:
            raise FrameShellAttachmentError("bridge must be a valid positive-volume solid")
        for label, value in (
            ("frame_intersection_mm3", self.frame_intersection_mm3),
            ("shell_intersection_mm3", self.shell_intersection_mm3),
        ):
            if type(value) not in (int, float) or not math.isfinite(float(value)) or float(value) <= 0.0:
                raise FrameShellAttachmentError(f"{label} must prove positive geometric engagement")
        _text(self.geometry_status, "geometry_status")
        _text(self.evidence_status, "evidence_status")

    @property
    def centroid_xyz_mm(self) -> tuple[float, float, float]:
        center = self.solid.val().Center()
        return float(center.x), float(center.y), float(center.z)

    def manifest(self) -> dict[str, object]:
        return {
            "bridge_id": self.bridge_id,
            "centroid_xyz_mm": list(self.centroid_xyz_mm),
            "volume_mm3": float(self.solid.val().Volume()),
            "frame_intersection_mm3": self.frame_intersection_mm3,
            "shell_intersection_mm3": self.shell_intersection_mm3,
            "geometry_status": self.geometry_status,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class BridgeClearanceRecord:
    bridge_id: str
    obstacle_id: str
    exact_intersection_mm3: float
    status: str

    @property
    def passes(self) -> bool:
        return self.exact_intersection_mm3 == 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "bridge_id": self.bridge_id,
            "obstacle_id": self.obstacle_id,
            "exact_intersection_mm3": self.exact_intersection_mm3,
            "passes": self.passes,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class GeometricLoadPath:
    load_path_id: str
    source_part_id: str
    chain_part_ids: tuple[str, ...]
    sink_part_id: str
    demand_N: float | None
    demand_status: str
    geometry_closed: bool
    physical_capacity_validated: bool
    evidence_status: str

    def __post_init__(self) -> None:
        for label, value in (
            ("load_path_id", self.load_path_id),
            ("source_part_id", self.source_part_id),
            ("sink_part_id", self.sink_part_id),
            ("demand_status", self.demand_status),
            ("evidence_status", self.evidence_status),
        ):
            _text(value, label)
        if type(self.chain_part_ids) is not tuple or not self.chain_part_ids:
            raise FrameShellAttachmentError("load path chain must be a non-empty exact tuple")
        if self.demand_N is not None:
            if type(self.demand_N) not in (int, float) or not math.isfinite(float(self.demand_N)) or float(self.demand_N) < 0.0:
                raise FrameShellAttachmentError("load demand must be finite non-negative or unresolved")
        if type(self.geometry_closed) is not bool or type(self.physical_capacity_validated) is not bool:
            raise FrameShellAttachmentError("load-path closure/capacity flags must be exact booleans")
        if self.physical_capacity_validated:
            raise FrameShellAttachmentError("digital attachment geometry cannot validate physical load capacity")

    def manifest(self) -> dict[str, object]:
        return {
            "load_path_id": self.load_path_id,
            "source_part_id": self.source_part_id,
            "chain_part_ids": list(self.chain_part_ids),
            "sink_part_id": self.sink_part_id,
            "demand_N": self.demand_N,
            "demand_status": self.demand_status,
            "geometry_closed": self.geometry_closed,
            "physical_capacity_validated": self.physical_capacity_validated,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class FrameShellAttachment:
    authority_revision: str
    realization_sha256: str
    bridges: tuple[FrameShellBridge, ...]
    clearance_records: tuple[BridgeClearanceRecord, ...]
    load_paths: tuple[GeometricLoadPath, ...]
    support_x_span_mm: float
    support_y_span_mm: float
    lower_center_service_preserved: bool
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.authority_revision, "authority_revision")
        _text(self.realization_sha256, "realization_sha256")
        if len(self.realization_sha256) != 64:
            raise FrameShellAttachmentError("realization_sha256 must be a SHA-256 digest")
        if tuple(bridge.bridge_id for bridge in self.bridges) != BRIDGE_IDS:
            raise FrameShellAttachmentError("bridge identity/order changed")
        if any(not record.passes for record in self.clearance_records):
            raise FrameShellAttachmentError("frame-shell bridge collides with a required-clear package/protected screen")
        if any(not path.geometry_closed for path in self.load_paths):
            raise FrameShellAttachmentError("declared geometric load path is not closed")
        if type(self.support_x_span_mm) not in (int, float) or float(self.support_x_span_mm) <= 0.0:
            raise FrameShellAttachmentError("support_x_span_mm must be positive")
        if type(self.support_y_span_mm) not in (int, float) or float(self.support_y_span_mm) <= 0.0:
            raise FrameShellAttachmentError("support_y_span_mm must be positive")
        if type(self.lower_center_service_preserved) is not bool or not self.lower_center_service_preserved:
            raise FrameShellAttachmentError("lower-centre service corridor must remain preserved")
        _text(self.evidence_status, "evidence_status")

    @property
    def attachment_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authority_revision": self.authority_revision,
            "realization_sha256": self.realization_sha256,
            "bridges": [bridge.manifest() for bridge in self.bridges],
            "clearance_records": [record.manifest() for record in self.clearance_records],
            "load_paths": [path.manifest() for path in self.load_paths],
            "support_x_span_mm": self.support_x_span_mm,
            "support_y_span_mm": self.support_y_span_mm,
            "lower_center_service_preserved": self.lower_center_service_preserved,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["attachment_sha256"] = self.attachment_sha256
        return payload


def _realized_part(realization: MechanicalRealization, part_id: str) -> RealizedPart:
    matches = tuple(part for part in realization.realized_parts if part.part_id == part_id)
    if len(matches) != 1:
        raise FrameShellAttachmentError(f"expected one realized part {part_id}")
    return matches[0]


def _bridge(
    bridge_id: str,
    solid: cq.Workplane,
    frame: RealizedPart,
    shell: RealizedPart,
) -> FrameShellBridge:
    return FrameShellBridge(
        bridge_id=bridge_id,
        solid=solid,
        frame_intersection_mm3=exact_intersection_volume_mm3(solid, frame.solid),
        shell_intersection_mm3=exact_intersection_volume_mm3(solid, shell.solid),
        geometry_status="MANUAL_A_INTERNAL_ATTACHMENT_CANDIDATE",
        evidence_status=(
            "POSITIVE_3D_FRAME_AND_SHELL_INTERSECTION_ONLY_"
            "NOT_MATERIAL_FASTENER_ADHESIVE_STIFFNESS_FATIGUE_OR_PHYSICAL_LOAD_EVIDENCE"
        ),
    )


def _build_bridges(realization: MechanicalRealization) -> tuple[FrameShellBridge, ...]:
    frame = _realized_part(realization, "FRAME-PERIMETER-REACTION")
    shell = _realized_part(realization, "LIVE-MAIN-RIGID-SHELL")
    candidates = (
        (BRIDGE_IDS[0], _box(LATERAL_BRIDGE_SIZE_XYZ_MM, Point3(-LATERAL_BRIDGE_X_MM, 0.0, 0.0))),
        (BRIDGE_IDS[1], _box(LATERAL_BRIDGE_SIZE_XYZ_MM, Point3(LATERAL_BRIDGE_X_MM, 0.0, 0.0))),
        (BRIDGE_IDS[2], _box(SUPERIOR_BRIDGE_SIZE_XYZ_MM, Point3(0.0, SUPERIOR_BRIDGE_Y_MM, 0.0))),
    )
    return tuple(_bridge(bridge_id, solid, frame, shell) for bridge_id, solid in candidates)


def _clearances(
    authority: Authority,
    model: MasckOneModel,
    bridges: tuple[FrameShellBridge, ...],
) -> tuple[BridgeClearanceRecord, ...]:
    audit = build_whole_product_interference_audit(model)
    package_obstacles = (
        ("WATER-RESERVOIR-ENVELOPE", model.water_reservoir_envelope.solid),
        ("WASTE-CARTRIDGE-ENVELOPE", model.waste_cartridge_envelope.solid),
        ("BATTERY-REFERENCE-ENVELOPE", model.battery_reference_envelope.solid),
    )
    records: list[BridgeClearanceRecord] = []
    for bridge in bridges:
        for obstacle_id, obstacle_solid in package_obstacles:
            volume = exact_intersection_volume_mm3(bridge.solid, obstacle_solid)
            records.append(
                BridgeClearanceRecord(
                    bridge.bridge_id,
                    obstacle_id,
                    volume,
                    "PASS_EXACT_BREP_CLEAR_DIGITAL_ONLY" if volume == 0.0 else "FAIL_PACKAGE_INTERFERENCE",
                )
            )
        for screen in audit.protected_screens:
            volume = exact_intersection_volume_mm3(bridge.solid, screen.solid)
            records.append(
                BridgeClearanceRecord(
                    bridge.bridge_id,
                    screen.screen_id,
                    volume,
                    "PASS_PROTECTED_SCREEN_CLEAR_DIGITAL_ONLY" if volume == 0.0 else "FAIL_PROTECTED_SCREEN_INTRUSION",
                )
            )
    return tuple(records)


def _load_paths(authority: Authority) -> tuple[GeometricLoadPath, ...]:
    continuous = float(authority.get("actuation", "clean", "continuous_force_requirement_N"))
    transient = float(authority.get("actuation", "clean", "transient_force_requirement_N"))
    force_status = str(authority.get("actuation", "clean", "status"))
    paths: list[GeometricLoadPath] = []
    for zone in "ABCD":
        for suffix, demand in (("CONTINUOUS", continuous), ("TRANSIENT", transient)):
            paths.append(
                GeometricLoadPath(
                    load_path_id=f"ACTUATOR-{zone}-{suffix}-TO-SHELL",
                    source_part_id=f"ACTUATOR-ZONE-{zone}",
                    chain_part_ids=(
                        f"REACTION-ACTUATOR-ZONE-{zone}",
                        "FRAME-PERIMETER-REACTION",
                        *BRIDGE_IDS,
                    ),
                    sink_part_id="LIVE-MAIN-RIGID-SHELL",
                    demand_N=demand,
                    demand_status=force_status,
                    geometry_closed=True,
                    physical_capacity_validated=False,
                    evidence_status="GEOMETRIC_CONNECTIVITY_ONLY_ACTUATION_FORCE_CAPACITY_REQUIRES_STRUCTURAL_ANALYSIS_AND_PHYSICAL_EVIDENCE",
                )
            )
    paths.append(
        GeometricLoadPath(
            load_path_id="RETENTION-HALO-TO-SHELL",
            source_part_id="RETENTION-HALO-OCCIPITAL-CROWN",
            chain_part_ids=(
                "RETENTION-YOKE-LEFT",
                "RETENTION-YOKE-RIGHT-FIXED",
                "FRAME-PERIMETER-REACTION",
                *BRIDGE_IDS,
            ),
            sink_part_id="LIVE-MAIN-RIGID-SHELL",
            demand_N=None,
            demand_status="RETENTION_PRELOAD_AND_DYNAMIC_LOAD_MAGNITUDE_UNRESOLVED_PENDING_CONTROLLED_EVIDENCE",
            geometry_closed=True,
            physical_capacity_validated=False,
            evidence_status="REAL_3D_REACTION_CHAIN_PRESENT_LOAD_MAGNITUDE_AND_CAPACITY_UNVALIDATED",
        )
    )
    return tuple(paths)


def build_frame_shell_attachment(
    authority: Authority | None = None,
) -> FrameShellAttachment:
    authority = authority or load_authority()
    model = build_model(authority)
    realization = build_mechanical_realization(authority)
    bridges = _build_bridges(realization)
    centers = tuple(bridge.centroid_xyz_mm for bridge in bridges)
    x_span = max(center[0] for center in centers) - min(center[0] for center in centers)
    y_span = max(center[1] for center in centers) - min(center[1] for center in centers)

    # No bridge occupies the lower-centre cartridge corridor. This is a geometric
    # reservation statement only; final door/key/seal geometry remains Manual B-owned.
    lower_center_service_preserved = all(center[1] >= -6.0 for center in centers)

    return FrameShellAttachment(
        authority_revision=str(authority.get("project", "authority_revision")),
        realization_sha256=realization.realization_sha256,
        bridges=bridges,
        clearance_records=_clearances(authority, model, bridges),
        load_paths=_load_paths(authority),
        support_x_span_mm=x_span,
        support_y_span_mm=y_span,
        lower_center_service_preserved=lower_center_service_preserved,
        evidence_status=(
            "THREE_POINT_REAL_3D_FRAME_TO_SHELL_ATTACHMENT_GEOMETRY_WITH_ACTUATOR_AND_RETENTION_LOAD_PATH_CONNECTIVITY_"
            "NOT_MATERIAL_STIFFNESS_STRESS_FATIGUE_FASTENER_OR_PHYSICAL_VALIDATION"
        ),
    )
