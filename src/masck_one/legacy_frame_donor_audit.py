from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
from typing import Iterable

import cadquery as cq

from .model import MasckOneModel, build_model
from .spatial import Point3


SCHEMA = "MASCK_ONE_LEGACY_FRAME_DONOR_AUDIT_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
LEGACY_WORLD_FRAME_ID = "MASCK_ONE_CANONICAL_XYZ"
LEGACY_DONOR_PR = 63
LEGACY_DONOR_HEAD_SHA = "23b942bbb7f335eac74b42fa1b1613900e5a9347"
LEGACY_DONOR_STRUCTURE_BLOB_SHA = "28b069ea2fdfa445ec63c930c142c67f392c7b99"
EVIDENCE_STATUS = (
    "DIGITAL_LEGACY_DONOR_RECONSTRUCTION_AND_CURRENT_SOURCE_COMPATIBILITY_AUDIT_ONLY_"
    "NOT_ATTACHMENT_STRENGTH_STIFFNESS_FATIGUE_TOOLING_TOLERANCE_ASSEMBLY_SERVICE_"
    "FIT_HUMAN_FACTOR_OR_PHYSICAL_VALIDATION"
)
REFERENCE_ROLE = "REFERENCE_ONLY_LEGACY_DONOR_GEOMETRY_NEVER_PHYSICAL_ASSEMBLY_MATERIAL"

# Current released files directly consumed by this audit. Any movement requires an
# explicit rebind before legacy measurements may be trusted against current geometry.
SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/authority.py", "6866e3a428dab8b32b5a1d9e58da78b8f5aa1aa2"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/protected_volumes.py", "ff2b9b288559f9b268e5d08a1d6c78335f745cf1"),
    ("src/masck_one/spatial.py", "8c1106b523fef5111009cc56236a53e3bc5ee10e"),
)

# Exact Manual-A / PR #63 donor constants from mechanical_structure.py and
# frame_shell_attachment.py at LEGACY_DONOR_HEAD_SHA. They are evidence inputs only.
DONOR_FRAME_MEMBER_RADIAL_MM = 6.0
DONOR_FRAME_DEPTH_MM = 2.4
DONOR_FRAME_Z_REAR_MM = -4.0
DONOR_FUNCTIONAL_FRAME_XY_MM = (155.0, 202.0)

DONOR_BRIDGE_DEPTH_Z_MM = 4.4
DONOR_LATERAL_BRIDGE_X_MM = 76.0
DONOR_LATERAL_BRIDGE_SIZE_XYZ_MM = (4.0, 12.0, DONOR_BRIDGE_DEPTH_Z_MM)
DONOR_SUPERIOR_BRIDGE_Y_MM = 100.0
DONOR_SUPERIOR_BRIDGE_SIZE_XYZ_MM = (14.0, 4.0, DONOR_BRIDGE_DEPTH_Z_MM)

DONOR_ACTUATOR_DIAMETER_MM = 10.2
DONOR_ACTUATOR_LENGTH_MM = 18.7
DONOR_ACTUATOR_SHOE_XY_MM = 12.0
DONOR_ACTUATOR_SHOE_DEPTH_MM = 4.0
DONOR_ACTUATOR_SHOE_Z_MM = -2.5
DONOR_ACTUATOR_ZONE_CANDIDATES = (
    ("ACTUATOR_ZONE_SUPERIOR_LEFT", Point3(-60.0, 66.0, 2.0), +1.0),
    ("ACTUATOR_ZONE_SUPERIOR_RIGHT", Point3(60.0, 66.0, 2.0), -1.0),
    ("ACTUATOR_ZONE_INFERIOR_LEFT", Point3(-58.0, -60.0, 2.0), +1.0),
    ("ACTUATOR_ZONE_INFERIOR_RIGHT", Point3(58.0, -60.0, 2.0), -1.0),
)

DONOR_YOKE_X_MM = 77.0
DONOR_YOKE_WIDTH_MM = 5.0
DONOR_YOKE_HEIGHT_MM = 12.0
DONOR_PIVOT_BORE_RADIUS_MM = 1.8
DONOR_PIVOT_Z_MM = -19.0
DONOR_RELEASE_SOCKET_XYZ_MM = (12.0, 18.0, 13.0)
DONOR_RELEASE_SOCKET_CENTER_Z_MM = -17.5
DONOR_RELEASE_CHANNEL_XYZ_MM = (5.4, 9.4, 15.0)
DONOR_RELEASE_BORE_RADIUS_MM = 1.8
DONOR_RELEASE_DOG_Z_MM = -19.0

GEOMETRY_DECIMALS = 8
INTERSECTION_ZERO_MM3 = 1e-8
_REPO_ROOT = Path(__file__).resolve().parents[2]


class LegacyFrameDonorAuditError(ValueError):
    """Raised when donor evidence or current-source compatibility is stale/invalid."""


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise LegacyFrameDonorAuditError(f"{label} must be exact nonblank text")
    return value


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LegacyFrameDonorAuditError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise LegacyFrameDonorAuditError(f"{label} must be finite")
    return result


def _positive(value: object, label: str) -> float:
    result = _finite(value, label)
    if result <= 0.0:
        raise LegacyFrameDonorAuditError(f"{label} must be positive")
    return result


def _quantized(value: object, label: str) -> float:
    result = round(_finite(value, label), GEOMETRY_DECIMALS)
    return 0.0 if abs(result) < 10 ** (-GEOMETRY_DECIMALS) else result


def _canonical_sha(value: object, length: int, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != length
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise LegacyFrameDonorAuditError(
            f"{label} must be lowercase canonical hexadecimal length {length}"
        )
    return value


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_current_sources() -> None:
    seen: set[str] = set()
    for relative_path, expected_sha in SOURCE_GIT_BLOB_IDENTITIES:
        _text(relative_path, "source path")
        _canonical_sha(expected_sha, 40, "source blob SHA")
        if relative_path in seen:
            raise LegacyFrameDonorAuditError(f"duplicate source binding: {relative_path}")
        seen.add(relative_path)
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise LegacyFrameDonorAuditError(f"current source file is missing: {relative_path}")
        actual_sha = _git_blob_sha(path)
        if actual_sha != expected_sha:
            raise LegacyFrameDonorAuditError(
                f"current source moved at {relative_path}; expected {expected_sha}, got {actual_sha}"
            )


def _box(size_xyz_mm: tuple[float, float, float], center_xyz_mm: tuple[float, float, float]) -> cq.Workplane:
    if type(size_xyz_mm) is not tuple or len(size_xyz_mm) != 3:
        raise LegacyFrameDonorAuditError("box size must be exact XYZ tuple")
    if type(center_xyz_mm) is not tuple or len(center_xyz_mm) != 3:
        raise LegacyFrameDonorAuditError("box center must be exact XYZ tuple")
    size = tuple(_positive(value, "box size") for value in size_xyz_mm)
    center = tuple(_finite(value, "box center") for value in center_xyz_mm)
    return cq.Workplane("XY").box(*size, centered=(True, True, True)).translate(center)


def _ring(
    outer_x_mm: float,
    outer_y_mm: float,
    radial_mm: float,
    depth_mm: float,
    z0_mm: float,
) -> cq.Workplane:
    outer_x = _positive(outer_x_mm, "ring outer X")
    outer_y = _positive(outer_y_mm, "ring outer Y")
    radial = _positive(radial_mm, "ring radial width")
    depth = _positive(depth_mm, "ring depth")
    inner_x = outer_x - 2.0 * radial
    inner_y = outer_y - 2.0 * radial
    if inner_x <= 0.0 or inner_y <= 0.0:
        raise LegacyFrameDonorAuditError("ring radial width consumes aperture")
    z0 = _finite(z0_mm, "ring Z")
    outer = (
        cq.Workplane("XY")
        .workplane(offset=z0)
        .ellipse(outer_x / 2.0, outer_y / 2.0)
        .extrude(depth)
    )
    cutter = (
        cq.Workplane("XY")
        .workplane(offset=z0 - 0.5)
        .ellipse(inner_x / 2.0, inner_y / 2.0)
        .extrude(depth + 1.0)
    )
    result = outer.cut(cutter)
    if not result.val().isValid() or len(result.val().Solids()) != 1:
        raise LegacyFrameDonorAuditError("legacy donor ring reconstruction is invalid")
    return result


def _cylinder_x(radius_mm: float, total_length_mm: float, center: tuple[float, float, float]) -> cq.Workplane:
    half = _positive(total_length_mm, "X cylinder length") / 2.0
    return (
        cq.Workplane("XY")
        .circle(_positive(radius_mm, "X cylinder radius"))
        .extrude(half, both=True)
        .rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 90.0)
        .translate(center)
    )


def _cylinder_y(radius_mm: float, total_length_mm: float, center: tuple[float, float, float]) -> cq.Workplane:
    half = _positive(total_length_mm, "Y cylinder length") / 2.0
    return (
        cq.Workplane("XY")
        .circle(_positive(radius_mm, "Y cylinder radius"))
        .extrude(half, both=True)
        .rotate((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 90.0)
        .translate(center)
    )


def _actuator(origin: Point3, sign: float, angle_deg: float) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .circle(DONOR_ACTUATOR_DIAMETER_MM / 2.0)
        .extrude(DONOR_ACTUATOR_LENGTH_MM)
        .rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), _finite(sign, "axis sign") * _finite(angle_deg, "axis angle"))
        .translate(origin.as_tuple())
    )


def _intersection_volume(first: cq.Workplane, second: cq.Workplane) -> float:
    volume = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(volume) or volume < 0.0:
        raise LegacyFrameDonorAuditError("intersection volume must be finite and nonnegative")
    return 0.0 if volume < INTERSECTION_ZERO_MM3 else _quantized(volume, "intersection volume")


def _protected_solid(model: MasckOneModel, index: int) -> tuple[str, cq.Workplane]:
    protected = model.protected_volumes.all[index]
    zone = protected.zone
    wp = cq.Workplane("XY").workplane(offset=-80.0).center(zone.center.x, zone.center.y)
    if zone.shape == "CIRCLE":
        solid = wp.circle(zone.envelope_width_mm / 2.0).extrude(160.0)
    else:
        solid = wp.ellipse(zone.envelope_width_mm / 2.0, zone.envelope_height_mm / 2.0).extrude(160.0)
    if zone.angle_deg:
        solid = solid.rotate(
            (zone.center.x, zone.center.y, 0.0),
            (zone.center.x, zone.center.y, 1.0),
            zone.angle_deg,
        )
    return zone.zone_id, solid


@dataclass(frozen=True, slots=True)
class DonorReferencePart:
    part_id: str
    donor_semantics: str
    solid: cq.Workplane = field(repr=False, compare=False)
    geometry_role: str = REFERENCE_ROLE

    def __post_init__(self) -> None:
        _text(self.part_id, "part ID")
        _text(self.donor_semantics, "donor semantics")
        if self.geometry_role != REFERENCE_ROLE:
            raise LegacyFrameDonorAuditError("legacy donor geometry cannot enter physical material")
        if type(self.solid) is not cq.Workplane:
            raise LegacyFrameDonorAuditError("donor reference part requires exact CadQuery Workplane")
        shape = self.solid.val()
        if not shape.isValid() or float(shape.Volume()) <= 0.0:
            raise LegacyFrameDonorAuditError(f"{self.part_id} is not a valid positive-volume B-rep")

    def manifest(self) -> dict[str, object]:
        shape = self.solid.val()
        bounds = shape.BoundingBox()
        return {
            "part_id": self.part_id,
            "geometry_role": self.geometry_role,
            "donor_semantics": self.donor_semantics,
            "volume_mm3": _quantized(shape.Volume(), f"{self.part_id} volume"),
            "bbox_mm": [
                _quantized(value, f"{self.part_id} bound")
                for value in (
                    bounds.xmin,
                    bounds.ymin,
                    bounds.zmin,
                    bounds.xmax,
                    bounds.ymax,
                    bounds.zmax,
                )
            ],
        }


@dataclass(frozen=True, slots=True)
class DonorOverlapRecord:
    source_id: str
    target_id: str
    intersection_volume_mm3: float
    interpretation: str

    def __post_init__(self) -> None:
        _text(self.source_id, "overlap source")
        _text(self.target_id, "overlap target")
        volume = _finite(self.intersection_volume_mm3, "overlap volume")
        if volume < 0.0:
            raise LegacyFrameDonorAuditError("overlap volume cannot be negative")
        object.__setattr__(self, "intersection_volume_mm3", volume)
        _text(self.interpretation, "overlap interpretation")
        if volume > 0.0 and "NOT_ATTACHMENT" not in self.interpretation and "COLLISION" not in self.interpretation:
            raise LegacyFrameDonorAuditError(
                "positive donor overlap must be typed as non-attachment or collision"
            )

    def manifest(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "interpretation": self.interpretation,
        }


@dataclass(frozen=True, slots=True)
class DonorSalvageDecision:
    datum_id: str
    legacy_value: object
    disposition: str
    rationale: str

    def __post_init__(self) -> None:
        _text(self.datum_id, "salvage datum ID")
        if self.disposition not in {
            "PROVISIONAL_SEED_ONLY",
            "CURRENT_AUTHORITY_REFERENCE_NOT_DONOR_SALVAGE",
            "REJECT",
        }:
            raise LegacyFrameDonorAuditError("uncontrolled salvage disposition")
        _text(self.rationale, "salvage rationale")

    def manifest(self) -> dict[str, object]:
        return {
            "datum_id": self.datum_id,
            "legacy_value": self.legacy_value,
            "disposition": self.disposition,
            "rationale": self.rationale,
        }


SALVAGE_DATUM_ORDER = (
    "FRAME_FUNCTIONAL_XY_MM",
    "FRAME_AXIAL_DEPTH_MM",
    "FRAME_RADIAL_WIDTH_MM",
    "FRAME_Z_REAR_MM",
    "FRAME_SIMPLE_ELLIPTICAL_RING_TOPOLOGY",
    "FRAME_SHELL_BRIDGE_GEOMETRY",
    "ACTUATOR_REACTION_SHOE_GEOMETRY",
    "RETENTION_FRAME_ROOT_GEOMETRY",
    "SAMPLED_WAYPOINT_ASSEMBLY_CLAIM",
)


@dataclass(frozen=True, slots=True)
class LegacyFrameDonorAudit:
    reference_parts: tuple[DonorReferencePart, ...]
    overlap_records: tuple[DonorOverlapRecord, ...]
    actuator_collision_records: tuple[DonorOverlapRecord, ...]
    protected_conflict_records: tuple[DonorOverlapRecord, ...]
    salvage_decisions: tuple[DonorSalvageDecision, ...]
    donor_angle_doe_deg: tuple[float, ...]
    donor_baseline_angle_deg: float
    tool_access_status: str
    continuous_assembly_status: str
    positive_join_status: str
    physical_validation_eligible: bool
    evidence_status: str = EVIDENCE_STATUS
    coordinate_frame_id: str = WORLD_FRAME_ID
    legacy_coordinate_frame_id: str = LEGACY_WORLD_FRAME_ID

    def __post_init__(self) -> None:
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise LegacyFrameDonorAuditError("donor audit must be rebound into canonical authority world")
        if self.legacy_coordinate_frame_id != LEGACY_WORLD_FRAME_ID:
            raise LegacyFrameDonorAuditError("legacy donor coordinate-frame identity changed")
        if not self.reference_parts or not self.overlap_records or not self.actuator_collision_records:
            raise LegacyFrameDonorAuditError("donor audit requires realized reference geometry and overlaps")
        if tuple(item.datum_id for item in self.salvage_decisions) != SALVAGE_DATUM_ORDER:
            raise LegacyFrameDonorAuditError("salvage decisions changed identity/order")
        axial = next(item for item in self.salvage_decisions if item.datum_id == "FRAME_AXIAL_DEPTH_MM")
        if axial.disposition != "PROVISIONAL_SEED_ONLY" or float(axial.legacy_value) != DONOR_FRAME_DEPTH_MM:
            raise LegacyFrameDonorAuditError("2.4 mm donor depth must remain provisional-only")
        for item in self.salvage_decisions:
            if item.datum_id != "FRAME_AXIAL_DEPTH_MM" and item.disposition == "PROVISIONAL_SEED_ONLY":
                raise LegacyFrameDonorAuditError("no other legacy frame datum is approved as a provisional seed")
        for label, value in (
            ("tool access status", self.tool_access_status),
            ("continuous assembly status", self.continuous_assembly_status),
            ("positive join status", self.positive_join_status),
            ("evidence status", self.evidence_status),
        ):
            _text(value, label)
        if self.tool_access_status != "UNPROVEN_NO_FASTENER_BOSS_INSERT_TOOL_OR_PROCESS_ACCESS_GEOMETRY":
            raise LegacyFrameDonorAuditError("legacy donor tool access was silently promoted")
        if self.continuous_assembly_status != "UNPROVEN_SAMPLED_WAYPOINTS_ARE_NOT_CONTINUOUS_SWEEPS":
            raise LegacyFrameDonorAuditError("legacy sampled waypoints cannot prove continuous assembly")
        if self.positive_join_status != "UNRESOLVED_LEGACY_POSITIVE_INTERSECTION_IS_NOT_TYPED_ATTACHMENT":
            raise LegacyFrameDonorAuditError("legacy overlap cannot be promoted to positive join evidence")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise LegacyFrameDonorAuditError("legacy donor audit cannot be physical validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise LegacyFrameDonorAuditError("donor evidence firewall drifted")
        if not self.donor_angle_doe_deg or tuple(sorted(set(self.donor_angle_doe_deg))) != self.donor_angle_doe_deg:
            raise LegacyFrameDonorAuditError("donor audit DOE must be unique and ascending")
        if self.donor_baseline_angle_deg not in self.donor_angle_doe_deg:
            raise LegacyFrameDonorAuditError("donor baseline angle must be in current authority DOE")

    @property
    def reference_geometry_sha256(self) -> str:
        raw = json.dumps(
            [part.manifest() for part in self.reference_parts],
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    @property
    def audit_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authored_against_main_sha": SOURCE_MAIN_SHA,
            "authority_revision": AUTHORITY_REVISION,
            "source_git_blob_identities": [
                {"path": path, "git_blob_sha": digest}
                for path, digest in SOURCE_GIT_BLOB_IDENTITIES
            ],
            "coordinate_frame_id": self.coordinate_frame_id,
            "legacy_coordinate_frame_id": self.legacy_coordinate_frame_id,
            "coordinate_rebind_status": (
                "AUDIT_ONLY_NUMERIC_DONOR_GEOMETRY_RECONSTRUCTED_IN_CURRENT_AUTHORITY_WORLD_"
                "LEGACY_FRAME_ID_IS_NOT_CURRENT_AUTHORITY"
            ),
            "legacy_donor_pr": LEGACY_DONOR_PR,
            "legacy_donor_head_sha": LEGACY_DONOR_HEAD_SHA,
            "legacy_donor_structure_blob_sha": LEGACY_DONOR_STRUCTURE_BLOB_SHA,
            "reference_parts": [part.manifest() for part in self.reference_parts],
            "reference_geometry_sha256": self.reference_geometry_sha256,
            "overlap_records": [item.manifest() for item in self.overlap_records],
            "actuator_collision_records": [
                item.manifest() for item in self.actuator_collision_records
            ],
            "protected_conflict_records": [
                item.manifest() for item in self.protected_conflict_records
            ],
            "donor_angle_doe_deg": list(self.donor_angle_doe_deg),
            "donor_baseline_angle_deg": self.donor_baseline_angle_deg,
            "salvage_decisions": [item.manifest() for item in self.salvage_decisions],
            "tool_access_status": self.tool_access_status,
            "continuous_assembly_status": self.continuous_assembly_status,
            "positive_join_status": self.positive_join_status,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["audit_sha256"] = self.audit_sha256
        return payload


def _legacy_reference_parts() -> tuple[DonorReferencePart, ...]:
    frame = DonorReferencePart(
        "LEGACY_PR63_FRAME_PERIMETER_REACTION_MEMBER",
        "SIMPLE_ELLIPTICAL_RING_DONOR_NOT_CURRENT_FRAME_TOPOLOGY",
        _ring(
            *DONOR_FUNCTIONAL_FRAME_XY_MM,
            DONOR_FRAME_MEMBER_RADIAL_MM,
            DONOR_FRAME_DEPTH_MM,
            DONOR_FRAME_Z_REAR_MM,
        ),
    )
    bridges = (
        DonorReferencePart(
            "LEGACY_PR63_FRAME_SHELL_BRIDGE_WEARER_LEFT",
            "SEPARATE_BOX_ACCEPTED_BY_POSITIVE_INTERSECTION_IN_DONOR",
            _box(DONOR_LATERAL_BRIDGE_SIZE_XYZ_MM, (-DONOR_LATERAL_BRIDGE_X_MM, 0.0, 0.0)),
        ),
        DonorReferencePart(
            "LEGACY_PR63_FRAME_SHELL_BRIDGE_WEARER_RIGHT",
            "SEPARATE_BOX_ACCEPTED_BY_POSITIVE_INTERSECTION_IN_DONOR",
            _box(DONOR_LATERAL_BRIDGE_SIZE_XYZ_MM, (DONOR_LATERAL_BRIDGE_X_MM, 0.0, 0.0)),
        ),
        DonorReferencePart(
            "LEGACY_PR63_FRAME_SHELL_BRIDGE_SUPERIOR",
            "SEPARATE_BOX_ACCEPTED_BY_POSITIVE_INTERSECTION_IN_DONOR",
            _box(DONOR_SUPERIOR_BRIDGE_SIZE_XYZ_MM, (0.0, DONOR_SUPERIOR_BRIDGE_Y_MM, 0.0)),
        ),
    )
    shoes = tuple(
        DonorReferencePart(
            f"LEGACY_PR63_{zone_id}_REACTION_SHOE",
            "REACTION_SHOE_ACCEPTED_BY_POSITIVE_FRAME_OVERLAP_IN_DONOR",
            _box(
                (DONOR_ACTUATOR_SHOE_XY_MM, DONOR_ACTUATOR_SHOE_XY_MM, DONOR_ACTUATOR_SHOE_DEPTH_MM),
                (origin.x, origin.y, DONOR_ACTUATOR_SHOE_Z_MM),
            ),
        )
        for zone_id, origin, _sign in DONOR_ACTUATOR_ZONE_CANDIDATES
    )

    pivot_bore = _cylinder_y(
        DONOR_PIVOT_BORE_RADIUS_MM,
        24.0,
        (-DONOR_YOKE_X_MM, 0.0, DONOR_PIVOT_Z_MM),
    )
    left_front = _box((12.0, DONOR_YOKE_HEIGHT_MM, 12.0), (-DONOR_YOKE_X_MM, 0.0, -8.0))
    clevis_outer = _box((12.0, 18.0, 13.0), (-DONOR_YOKE_X_MM, 0.0, -17.5))
    clevis_slot = _box((10.0, 5.4, 15.0), (-DONOR_YOKE_X_MM, 0.0, -17.5))
    left_clevis = DonorReferencePart(
        "LEGACY_PR63_RETENTION_LEFT_FRAME_CLEVIS",
        "FRAME_SIDE_ROOT_ACCEPTED_BY_POSITIVE_FRAME_OVERLAP_IN_DONOR",
        left_front.union(clevis_outer.cut(clevis_slot).cut(pivot_bore)),
    )

    right_front = _box(
        (DONOR_YOKE_WIDTH_MM, DONOR_YOKE_HEIGHT_MM, 12.0),
        (DONOR_YOKE_X_MM, 0.0, -8.0),
    )
    socket_outer = _box(
        DONOR_RELEASE_SOCKET_XYZ_MM,
        (DONOR_YOKE_X_MM, 0.0, DONOR_RELEASE_SOCKET_CENTER_Z_MM),
    )
    channel = _box(
        DONOR_RELEASE_CHANNEL_XYZ_MM,
        (DONOR_YOKE_X_MM, 0.0, DONOR_RELEASE_SOCKET_CENTER_Z_MM),
    )
    release_bore = _cylinder_x(
        DONOR_RELEASE_BORE_RADIUS_MM,
        30.0,
        (DONOR_YOKE_X_MM, 0.0, DONOR_RELEASE_DOG_Z_MM),
    )
    right_socket = DonorReferencePart(
        "LEGACY_PR63_RETENTION_RIGHT_FRAME_SOCKET",
        "FRAME_SIDE_ROOT_ACCEPTED_BY_POSITIVE_FRAME_OVERLAP_IN_DONOR",
        right_front.union(socket_outer.cut(channel).cut(release_bore)),
    )
    return (frame, *bridges, *shoes, left_clevis, right_socket)


def _part_map(parts: Iterable[DonorReferencePart]) -> dict[str, DonorReferencePart]:
    result = {part.part_id: part for part in parts}
    if len(result) != len(tuple(parts)):
        raise LegacyFrameDonorAuditError("duplicate donor part IDs")
    return result


def _salvage_decisions() -> tuple[DonorSalvageDecision, ...]:
    return (
        DonorSalvageDecision(
            "FRAME_FUNCTIONAL_XY_MM",
            list(DONOR_FUNCTIONAL_FRAME_XY_MM),
            "CURRENT_AUTHORITY_REFERENCE_NOT_DONOR_SALVAGE",
            "The 155 x 202 mm value is already a current authority functional-frame reference and does not validate the donor ring cross-section or topology.",
        ),
        DonorSalvageDecision(
            "FRAME_AXIAL_DEPTH_MM",
            DONOR_FRAME_DEPTH_MM,
            "PROVISIONAL_SEED_ONLY",
            "2.4 mm is compatible as a bounded CAD seed only; it is not authority, material, strength, stiffness, fatigue, tolerance, or process evidence.",
        ),
        DonorSalvageDecision(
            "FRAME_RADIAL_WIDTH_MM",
            DONOR_FRAME_MEMBER_RADIAL_MM,
            "REJECT",
            "The 6.0 mm simple-ring radial width is not source-bound to the released interface-attachment perimeter and has no current structural-performance basis.",
        ),
        DonorSalvageDecision(
            "FRAME_Z_REAR_MM",
            DONOR_FRAME_Z_REAR_MM,
            "REJECT",
            "Legacy Z placement predates current package and service geometry and cannot be inherited without current collision and join closure.",
        ),
        DonorSalvageDecision(
            "FRAME_SIMPLE_ELLIPTICAL_RING_TOPOLOGY",
            "OUTER_FUNCTIONAL_FRAME_ELLIPSE_MINUS_6_MM_INSET",
            "REJECT",
            "Current released attachment topology is not represented by the donor's uniform inset ellipse.",
        ),
        DonorSalvageDecision(
            "FRAME_SHELL_BRIDGE_GEOMETRY",
            "THREE_SEPARATE_OVERLAPPING_BOXES",
            "REJECT",
            "Positive material overlap is not a typed shell-frame attachment, and no fastener, boss, insert, bonded interface, process access, or tolerance architecture exists.",
        ),
        DonorSalvageDecision(
            "ACTUATOR_REACTION_SHOE_GEOMETRY",
            "FOUR_12_X_12_X_4_MM_OVERLAPPING_SHOES",
            "REJECT",
            "Donor shoes overlap frame material and collide with their own actuator bodies across the authority angle DOE; current mount datums/coupling remain separately owned.",
        ),
        DonorSalvageDecision(
            "RETENTION_FRAME_ROOT_GEOMETRY",
            "LEFT_CLEVIS_AND_RIGHT_SOCKET_OVERLAP_FRAME",
            "REJECT",
            "Frame-side retention roots rely on raw overlap and are stale to current Cell 3 retention interfaces; mating counterparts require explicit positive join semantics.",
        ),
        DonorSalvageDecision(
            "SAMPLED_WAYPOINT_ASSEMBLY_CLAIM",
            "DISCRETE_TRANSLATED_BREP_SAMPLES",
            "REJECT",
            "Discrete waypoint clearance cannot establish continuous nonteleporting assembly or service motion.",
        ),
    )


def build_legacy_frame_donor_audit() -> LegacyFrameDonorAudit:
    _require_current_sources()
    model = build_model()
    if str(model.authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise LegacyFrameDonorAuditError("current authority revision moved and donor audit requires rebind")
    current_frame_xy = tuple(float(value) for value in model.authority.pair("geometry", "functional_frame_xy_mm"))
    if current_frame_xy != DONOR_FUNCTIONAL_FRAME_XY_MM:
        raise LegacyFrameDonorAuditError(
            "current functional-frame reference moved; donor compatibility must be re-audited"
        )

    _canonical_sha(LEGACY_DONOR_HEAD_SHA, 40, "legacy donor head SHA")
    _canonical_sha(LEGACY_DONOR_STRUCTURE_BLOB_SHA, 40, "legacy donor source blob SHA")

    parts = _legacy_reference_parts()
    part_by_id = {part.part_id: part for part in parts}
    if len(part_by_id) != len(parts):
        raise LegacyFrameDonorAuditError("duplicate donor reference part identity")
    frame = part_by_id["LEGACY_PR63_FRAME_PERIMETER_REACTION_MEMBER"]

    overlap_records: list[DonorOverlapRecord] = []
    for part in parts[1:]:
        volume = _intersection_volume(part.solid, frame.solid)
        overlap_records.append(
            DonorOverlapRecord(
                part.part_id,
                frame.part_id,
                volume,
                "LEGACY_POSITIVE_MATERIAL_OVERLAP_NOT_ATTACHMENT" if volume > 0.0 else "CLEAR_NO_ATTACHMENT_PROVEN",
            )
        )

    shell_targets = (frame, *parts[1:4])
    for part in shell_targets:
        volume = _intersection_volume(part.solid, model.shell.solid)
        overlap_records.append(
            DonorOverlapRecord(
                part.part_id,
                "CURRENT_MAIN_RIGID_SHELL",
                volume,
                "CURRENT_SHELL_MATERIAL_OVERLAP_NOT_ATTACHMENT" if volume > 0.0 else "CLEAR_NO_ATTACHMENT_PROVEN",
            )
        )

    angle_doe = tuple(
        float(value) for value in model.authority.get("actuation", "clean", "axis_angle_doe_deg")
    )
    baseline = float(model.authority.get("actuation", "clean", "axis_angle_baseline_deg"))
    actuator_collisions: list[DonorOverlapRecord] = []
    for zone_id, origin, sign in DONOR_ACTUATOR_ZONE_CANDIDATES:
        shoe = part_by_id[f"LEGACY_PR63_{zone_id}_REACTION_SHOE"]
        for angle in angle_doe:
            actuator = _actuator(origin, sign, angle)
            for target_id, target_solid in (
                (shoe.part_id, shoe.solid),
                (frame.part_id, frame.solid),
            ):
                volume = _intersection_volume(actuator, target_solid)
                actuator_collisions.append(
                    DonorOverlapRecord(
                        f"LEGACY_PR63_{zone_id}_ACTUATOR_AT_{angle:g}_DEG",
                        target_id,
                        volume,
                        "LEGACY_ACTUATOR_MATERIAL_COLLISION" if volume > 0.0 else "CLEAR",
                    )
                )

    protected_records: list[DonorOverlapRecord] = []
    protected_solids = tuple(
        _protected_solid(model, index) for index in range(len(model.protected_volumes.all))
    )
    for part in parts:
        for protected_id, protected_solid in protected_solids:
            volume = _intersection_volume(part.solid, protected_solid)
            protected_records.append(
                DonorOverlapRecord(
                    part.part_id,
                    protected_id,
                    volume,
                    "LEGACY_REFERENCE_PROTECTED_VOLUME_COLLISION" if volume > 0.0 else "CLEAR",
                )
            )

    result = LegacyFrameDonorAudit(
        reference_parts=parts,
        overlap_records=tuple(overlap_records),
        actuator_collision_records=tuple(actuator_collisions),
        protected_conflict_records=tuple(protected_records),
        salvage_decisions=_salvage_decisions(),
        donor_angle_doe_deg=angle_doe,
        donor_baseline_angle_deg=baseline,
        tool_access_status="UNPROVEN_NO_FASTENER_BOSS_INSERT_TOOL_OR_PROCESS_ACCESS_GEOMETRY",
        continuous_assembly_status="UNPROVEN_SAMPLED_WAYPOINTS_ARE_NOT_CONTINUOUS_SWEEPS",
        positive_join_status="UNRESOLVED_LEGACY_POSITIVE_INTERSECTION_IS_NOT_TYPED_ATTACHMENT",
        physical_validation_eligible=False,
    )
    result.__post_init__()
    return result


def export_legacy_frame_donor_review(output_dir: str | Path) -> dict[str, object]:
    audit = build_legacy_frame_donor_audit()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    step_name = "legacy_pr63_frame_donor_reference_only.step"
    manifest_name = "legacy_pr63_frame_donor_audit.json"
    compound = cq.Compound.makeCompound([part.solid.val() for part in audit.reference_parts])
    cq.exporters.export(cq.Workplane(obj=compound), str(output / step_name))
    manifest = audit.manifest()
    manifest["review_artifact_role"] = REFERENCE_ROLE
    manifest["review_step_file"] = step_name
    manifest["physical_assembly_inclusion"] = False
    with (output / manifest_name).open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return {
        "step_file": step_name,
        "manifest_file": manifest_name,
        "audit_sha256": audit.audit_sha256,
        "reference_geometry_sha256": audit.reference_geometry_sha256,
        "physical_assembly_inclusion": False,
    }
