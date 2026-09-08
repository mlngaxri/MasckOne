from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha1, sha256
import json
import math
from pathlib import Path

import cadquery as cq

from .model import MasckOneModel, build_model
from .spatial import Point3


SCHEMA = "MASCK_ONE_LEGACY_ACTUATOR_DONOR_AUDIT_V1"
SOURCE_MAIN_SHA = "5c41702f23ffe5a602b8af363e8588867d9af2e0"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
LEGACY_WORLD_FRAME_ID = "MASCK_ONE_CANONICAL_XYZ"
LEGACY_DONOR_PR = 63
LEGACY_DONOR_HEAD_SHA = "23b942bbb7f335eac74b42fa1b1613900e5a9347"
LEGACY_DONOR_STRUCTURE_BLOB_SHA = "28b069ea2fdfa445ec63c930c142c67f392c7b99"
REFERENCE_ROLE = "REFERENCE_ONLY_LEGACY_DONOR_GEOMETRY_NEVER_PHYSICAL_ASSEMBLY_MATERIAL"
EVIDENCE_STATUS = (
    "DIGITAL_LEGACY_ACTUATOR_DONOR_RECONSTRUCTION_INTERFERENCE_AND_SEMANTIC_AUDIT_ONLY_"
    "NOT_CURRENT_MOUNT_ATTACHMENT_FORCE_STIFFNESS_FATIGUE_ACOUSTIC_TOLERANCE_TOOLING_"
    "ASSEMBLY_SERVICE_SUPPLIER_OR_PHYSICAL_VALIDATION"
)

# Direct current-main source bindings used to decide what donor intent can still be
# retained. Any movement requires explicit reconstruction and review.
SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("schemas/masck_one_authority.schema.json", "58accbe48619058cb99ab51a0387cf01874c3717"),
    ("src/masck_one/authority.py", "6866e3a428dab8b32b5a1d9e58da78b8f5aa1aa2"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/actuator_frames.py", "4c2013f994bdc9e084fe227eb5e166f973500ebb"),
    ("src/masck_one/actuator_coupling.py", "d56160304190c030e3bc389803eaa456aaab5af0"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
    ("src/masck_one/spatial.py", "8c1106b523fef5111009cc56236a53e3bc5ee10e"),
)

# Exact Manual A / PR #63 donor values. They are immutable evidence inputs only.
DONOR_FRAME_MEMBER_RADIAL_MM = 6.0
DONOR_FRAME_DEPTH_MM = 2.4
DONOR_FRAME_Z_REAR_MM = -4.0
DONOR_FUNCTIONAL_FRAME_XY_MM = (155.0, 202.0)

DONOR_ACTUATOR_DIAMETER_MM = 10.2
DONOR_ACTUATOR_LENGTH_MM = 18.7
DONOR_COLLAR_OUTER_DIAMETER_MM = 12.6
DONOR_COLLAR_INNER_DIAMETER_MM = 10.6
DONOR_COLLAR_LENGTH_MM = 4.0
DONOR_SHOE_XY_MM = 12.0
DONOR_SHOE_DEPTH_MM = 4.0
DONOR_SHOE_Z_MM = -2.5
DONOR_ZONE_CANDIDATES = (
    ("ACTUATOR_ZONE_SUPERIOR_LEFT", Point3(-60.0, 66.0, 2.0), +1.0),
    ("ACTUATOR_ZONE_SUPERIOR_RIGHT", Point3(60.0, 66.0, 2.0), -1.0),
    ("ACTUATOR_ZONE_INFERIOR_LEFT", Point3(-58.0, -60.0, 2.0), +1.0),
    ("ACTUATOR_ZONE_INFERIOR_RIGHT", Point3(58.0, -60.0, 2.0), -1.0),
)
ZONE_IDS = tuple(item[0] for item in DONOR_ZONE_CANDIDATES)

GEOMETRY_DECIMALS = 8
INTERSECTION_ZERO_MM3 = 1e-8
PACKAGE_VOLUME_TOLERANCE_MM3 = 1e-5
_REPO_ROOT = Path(__file__).resolve().parents[2]


class LegacyActuatorDonorAuditError(ValueError):
    """Raised when donor reconstruction or current-source evidence is stale/invalid."""


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise LegacyActuatorDonorAuditError(f"{label} must be exact nonblank text")
    return value


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LegacyActuatorDonorAuditError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise LegacyActuatorDonorAuditError(f"{label} must be finite")
    return result


def _positive(value: object, label: str) -> float:
    result = _finite(value, label)
    if result <= 0.0:
        raise LegacyActuatorDonorAuditError(f"{label} must be positive")
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
        raise LegacyActuatorDonorAuditError(
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
            raise LegacyActuatorDonorAuditError(f"duplicate source binding: {relative_path}")
        seen.add(relative_path)
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise LegacyActuatorDonorAuditError(f"current source file is missing: {relative_path}")
        actual_sha = _git_blob_sha(path)
        if actual_sha != expected_sha:
            raise LegacyActuatorDonorAuditError(
                f"current source moved at {relative_path}; expected {expected_sha}, got {actual_sha}"
            )


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
        raise LegacyActuatorDonorAuditError("ring radial width consumes aperture")
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
    return outer.cut(cutter)


def _box(size_xyz_mm: tuple[float, float, float], center_xyz_mm: tuple[float, float, float]) -> cq.Workplane:
    if type(size_xyz_mm) is not tuple or len(size_xyz_mm) != 3:
        raise LegacyActuatorDonorAuditError("box size must be exact XYZ tuple")
    if type(center_xyz_mm) is not tuple or len(center_xyz_mm) != 3:
        raise LegacyActuatorDonorAuditError("box center must be exact XYZ tuple")
    size = tuple(_positive(value, "box size") for value in size_xyz_mm)
    center = tuple(_finite(value, "box center") for value in center_xyz_mm)
    return cq.Workplane("XY").box(*size, centered=(True, True, True)).translate(center)


def _axis_cylinder(
    origin: Point3,
    sign: float,
    angle_deg: float,
    diameter_mm: float,
    length_mm: float,
) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .circle(_positive(diameter_mm, "cylinder diameter") / 2.0)
        .extrude(_positive(length_mm, "cylinder length"))
        .rotate(
            (0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            _finite(sign, "axis sign") * _finite(angle_deg, "axis angle"),
        )
        .translate(origin.as_tuple())
    )


def _actuator(origin: Point3, sign: float, angle_deg: float) -> cq.Workplane:
    return _axis_cylinder(
        origin,
        sign,
        angle_deg,
        DONOR_ACTUATOR_DIAMETER_MM,
        DONOR_ACTUATOR_LENGTH_MM,
    )


def _collar(origin: Point3, sign: float, baseline_angle_deg: float) -> cq.Workplane:
    outer = _axis_cylinder(
        origin,
        sign,
        baseline_angle_deg,
        DONOR_COLLAR_OUTER_DIAMETER_MM,
        DONOR_COLLAR_LENGTH_MM,
    )
    inner = _axis_cylinder(
        origin,
        sign,
        baseline_angle_deg,
        DONOR_COLLAR_INNER_DIAMETER_MM,
        DONOR_COLLAR_LENGTH_MM + 1.0,
    )
    return outer.cut(inner)


def _shoe(origin: Point3) -> cq.Workplane:
    return _box(
        (DONOR_SHOE_XY_MM, DONOR_SHOE_XY_MM, DONOR_SHOE_DEPTH_MM),
        (origin.x, origin.y, DONOR_SHOE_Z_MM),
    )


def _intersection_volume(first: cq.Workplane, second: cq.Workplane) -> float:
    volume = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(volume) or volume < 0.0:
        raise LegacyActuatorDonorAuditError("intersection volume must be finite and nonnegative")
    return 0.0 if volume < INTERSECTION_ZERO_MM3 else _quantized(volume, "intersection volume")


def _shape_manifest(solid: cq.Workplane, label: str) -> dict[str, object]:
    shape = solid.val()
    if not shape.isValid() or float(shape.Volume()) <= 0.0:
        raise LegacyActuatorDonorAuditError(f"{label} must be a valid positive-volume B-rep")
    bounds = shape.BoundingBox()
    return {
        "volume_mm3": _quantized(shape.Volume(), f"{label} volume"),
        "bounds_mm": [
            _quantized(value, f"{label} bound")
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
class DonorReferencePart:
    part_id: str
    zone_id: str | None
    donor_semantics: str
    solid: cq.Workplane = field(repr=False, compare=False)
    geometry_role: str = REFERENCE_ROLE

    def __post_init__(self) -> None:
        _text(self.part_id, "part ID")
        if self.zone_id is not None and self.zone_id not in ZONE_IDS:
            raise LegacyActuatorDonorAuditError("donor part uses unknown actuator zone")
        _text(self.donor_semantics, "donor semantics")
        if self.geometry_role != REFERENCE_ROLE:
            raise LegacyActuatorDonorAuditError("legacy donor geometry cannot enter physical material")
        _shape_manifest(self.solid, self.part_id)

    def manifest(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "zone_id": self.zone_id,
            "geometry_role": self.geometry_role,
            "donor_semantics": self.donor_semantics,
            **_shape_manifest(self.solid, self.part_id),
        }


@dataclass(frozen=True, slots=True)
class InterferenceRecord:
    record_id: str
    zone_id: str
    angle_deg: float | None
    source_id: str
    target_id: str
    intersection_volume_mm3: float
    classification: str
    forbidden_pattern_id: str

    def __post_init__(self) -> None:
        _text(self.record_id, "interference record ID")
        if self.zone_id not in ZONE_IDS:
            raise LegacyActuatorDonorAuditError("interference record uses unknown actuator zone")
        if self.angle_deg is not None:
            object.__setattr__(self, "angle_deg", _finite(self.angle_deg, "record angle"))
        _text(self.source_id, "interference source")
        _text(self.target_id, "interference target")
        volume = _finite(self.intersection_volume_mm3, "intersection volume")
        if volume < 0.0:
            raise LegacyActuatorDonorAuditError("intersection volume cannot be negative")
        object.__setattr__(self, "intersection_volume_mm3", volume)
        _text(self.classification, "interference classification")
        _text(self.forbidden_pattern_id, "forbidden pattern ID")
        if volume > 0.0 and self.classification not in {
            "FORBIDDEN_OVERLAP_AS_ATTACHMENT",
            "LEGACY_MOVING_ACTUATOR_COLLISION",
        }:
            raise LegacyActuatorDonorAuditError(
                "positive donor intersection must be typed as forbidden attachment overlap or collision"
            )
        if volume == 0.0 and self.classification != "CLEAR_REFERENCE_ONLY_NO_ATTACHMENT_PROVEN":
            raise LegacyActuatorDonorAuditError("zero donor intersection must remain reference-only clear evidence")

    def manifest(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "zone_id": self.zone_id,
            "angle_deg": self.angle_deg,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "classification": self.classification,
            "forbidden_pattern_id": self.forbidden_pattern_id,
        }


@dataclass(frozen=True, slots=True)
class ForbiddenGeometryPattern:
    pattern_id: str
    disposition: str
    evidence_record_ids: tuple[str, ...]
    rule: str
    successor_requirement: str

    def __post_init__(self) -> None:
        _text(self.pattern_id, "forbidden pattern ID")
        if self.disposition != "REJECT":
            raise LegacyActuatorDonorAuditError("forbidden donor geometry must remain rejected")
        if not self.evidence_record_ids:
            raise LegacyActuatorDonorAuditError("forbidden pattern requires measured evidence")
        if len(set(self.evidence_record_ids)) != len(self.evidence_record_ids):
            raise LegacyActuatorDonorAuditError("forbidden pattern evidence cannot repeat")
        _text(self.rule, "forbidden pattern rule")
        _text(self.successor_requirement, "successor requirement")

    def manifest(self) -> dict[str, object]:
        return {
            "pattern_id": self.pattern_id,
            "disposition": self.disposition,
            "evidence_record_ids": list(self.evidence_record_ids),
            "rule": self.rule,
            "successor_requirement": self.successor_requirement,
        }


@dataclass(frozen=True, slots=True)
class SemanticDecision:
    semantic_id: str
    legacy_value: object
    disposition: str
    rationale: str

    def __post_init__(self) -> None:
        _text(self.semantic_id, "semantic ID")
        if self.disposition not in {
            "SALVAGE_COMPATIBLE_SINGLE_AXIS_SEMANTIC_ONLY",
            "SALVAGE_CURRENT_SOURCE_PACKAGING_INTENT_ONLY",
            "CURRENT_AUTHORITY_REFERENCE_NOT_DONOR_SALVAGE",
            "REJECT",
        }:
            raise LegacyActuatorDonorAuditError("uncontrolled donor semantic disposition")
        _text(self.rationale, "semantic rationale")

    def manifest(self) -> dict[str, object]:
        return {
            "semantic_id": self.semantic_id,
            "legacy_value": self.legacy_value,
            "disposition": self.disposition,
            "rationale": self.rationale,
        }


SEMANTIC_ORDER = (
    "FOUR_INDEPENDENT_ZONES",
    "SINGLE_LINEAR_AXIS_PER_ZONE",
    "ANGLE_DOE_ROTATES_SAME_AXIS_NOT_SECOND_DOF",
    "ACTUATOR_PACKAGE_REFERENCE_DIAMETER_LENGTH_MM",
    "COAXIAL_CARRIER_PACKAGING_INTENT",
    "DONOR_CLOSED_COLLAR_DIMENSIONS_MM",
    "DONOR_REACTION_SHOE_DIMENSIONS_MM",
    "DONOR_SIMPLE_FRAME_RING",
    "DONOR_WORLD_ZONE_ORIGINS",
)


@dataclass(frozen=True, slots=True)
class LegacyActuatorDonorAudit:
    reference_parts: tuple[DonorReferencePart, ...]
    static_overlap_records: tuple[InterferenceRecord, ...]
    angle_doe_records: tuple[InterferenceRecord, ...]
    forbidden_patterns: tuple[ForbiddenGeometryPattern, ...]
    semantic_decisions: tuple[SemanticDecision, ...]
    angle_doe_deg: tuple[float, ...]
    baseline_angle_deg: float
    current_model_package_reference_status: str
    current_mount_resolution_status: str
    physical_assembly_inclusion: bool
    physical_validation_eligible: bool
    evidence_status: str = EVIDENCE_STATUS
    coordinate_frame_id: str = WORLD_FRAME_ID
    legacy_coordinate_frame_id: str = LEGACY_WORLD_FRAME_ID

    def __post_init__(self) -> None:
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise LegacyActuatorDonorAuditError("audit must use canonical authority world")
        if self.legacy_coordinate_frame_id != LEGACY_WORLD_FRAME_ID:
            raise LegacyActuatorDonorAuditError("legacy frame identity drifted")
        if not self.reference_parts or not self.static_overlap_records or not self.angle_doe_records:
            raise LegacyActuatorDonorAuditError("actuator donor audit requires realized reference geometry and measurements")
        part_ids = tuple(part.part_id for part in self.reference_parts)
        if len(set(part_ids)) != len(part_ids):
            raise LegacyActuatorDonorAuditError("donor reference part IDs cannot repeat")
        all_records = self.static_overlap_records + self.angle_doe_records
        record_ids = tuple(record.record_id for record in all_records)
        if len(set(record_ids)) != len(record_ids):
            raise LegacyActuatorDonorAuditError("interference record IDs cannot repeat")
        known_record_ids = set(record_ids)
        for pattern in self.forbidden_patterns:
            if not set(pattern.evidence_record_ids).issubset(known_record_ids):
                raise LegacyActuatorDonorAuditError("forbidden pattern references unknown measurement evidence")
        if tuple(item.semantic_id for item in self.semantic_decisions) != SEMANTIC_ORDER:
            raise LegacyActuatorDonorAuditError("donor semantic decision order changed")
        if not self.angle_doe_deg or tuple(sorted(set(self.angle_doe_deg))) != self.angle_doe_deg:
            raise LegacyActuatorDonorAuditError("angle DOE must be unique and ascending")
        if self.baseline_angle_deg not in self.angle_doe_deg:
            raise LegacyActuatorDonorAuditError("baseline angle must be represented in DOE")
        if len(self.static_overlap_records) != len(ZONE_IDS) * 2:
            raise LegacyActuatorDonorAuditError("audit requires collar-shoe and shoe-frame overlap for every zone")
        if len(self.angle_doe_records) != len(ZONE_IDS) * len(self.angle_doe_deg) * 3:
            raise LegacyActuatorDonorAuditError("audit requires actuator-collar/shoe/frame measurements for every zone and DOE angle")
        if any(record.intersection_volume_mm3 <= 0.0 for record in self.static_overlap_records):
            raise LegacyActuatorDonorAuditError("legacy static attachment claims must reproduce positive material overlap")

        collar_rows = [record for record in self.angle_doe_records if record.target_id.endswith("_MOUNT_COLLAR")]
        for zone_id in ZONE_IDS:
            baseline_row = next(
                record for record in collar_rows
                if record.zone_id == zone_id and record.angle_deg == self.baseline_angle_deg
            )
            if baseline_row.intersection_volume_mm3 != 0.0:
                raise LegacyActuatorDonorAuditError("baseline actuator must retain donor collar radial clearance")
            off_baseline = [
                record for record in collar_rows
                if record.zone_id == zone_id and record.angle_deg != self.baseline_angle_deg
            ]
            if not any(record.intersection_volume_mm3 > 0.0 for record in off_baseline):
                raise LegacyActuatorDonorAuditError("fixed donor collar must reproduce off-baseline DOE interference")

        shoe_rows = [record for record in self.angle_doe_records if record.target_id.endswith("_REACTION_SHOE")]
        if not any(
            record.angle_deg == self.baseline_angle_deg and record.intersection_volume_mm3 > 0.0
            for record in shoe_rows
        ):
            raise LegacyActuatorDonorAuditError("legacy baseline actuator-shoe collision was not reproduced")
        frame_rows = [record for record in self.angle_doe_records if record.target_id == "LEGACY_PR63_FRAME_PERIMETER_REACTION_MEMBER"]
        if not any(record.intersection_volume_mm3 > 0.0 for record in frame_rows):
            raise LegacyActuatorDonorAuditError("legacy actuator-frame collision was not reproduced")

        _text(self.current_model_package_reference_status, "current package reference status")
        if self.current_model_package_reference_status != "MATCHES_CURRENT_MODEL_10P2_DIAMETER_X_18P7_LENGTH_REFERENCE_ONLY":
            raise LegacyActuatorDonorAuditError("current package reference compatibility was silently changed")
        _text(self.current_mount_resolution_status, "current mount resolution status")
        if self.current_mount_resolution_status != "UNRESOLVED_PER_CURRENT_ACTUATOR_FRAMES_AND_COUPLING_SOURCES":
            raise LegacyActuatorDonorAuditError("donor audit cannot promote unresolved current actuator mounts")
        if type(self.physical_assembly_inclusion) is not bool or self.physical_assembly_inclusion:
            raise LegacyActuatorDonorAuditError("legacy donor reference geometry cannot enter physical assembly")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise LegacyActuatorDonorAuditError("legacy donor audit cannot be physical validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise LegacyActuatorDonorAuditError("evidence firewall drifted")

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
                "NO_LEGACY_OR_MODEL_REFERENCE_PLACEMENT_IS_PROMOTED_TO_CURRENT_MOUNT_DATUM"
            ),
            "legacy_donor_pr": LEGACY_DONOR_PR,
            "legacy_donor_head_sha": LEGACY_DONOR_HEAD_SHA,
            "legacy_donor_structure_blob_sha": LEGACY_DONOR_STRUCTURE_BLOB_SHA,
            "reference_parts": [part.manifest() for part in self.reference_parts],
            "reference_geometry_sha256": self.reference_geometry_sha256,
            "static_overlap_records": [record.manifest() for record in self.static_overlap_records],
            "angle_doe_records": [record.manifest() for record in self.angle_doe_records],
            "forbidden_patterns": [pattern.manifest() for pattern in self.forbidden_patterns],
            "semantic_decisions": [item.manifest() for item in self.semantic_decisions],
            "angle_doe_deg": list(self.angle_doe_deg),
            "baseline_angle_deg": self.baseline_angle_deg,
            "current_model_package_reference_status": self.current_model_package_reference_status,
            "current_mount_resolution_status": self.current_mount_resolution_status,
            "physical_assembly_inclusion": self.physical_assembly_inclusion,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["audit_sha256"] = self.audit_sha256
        return payload


def _reference_parts(baseline_angle_deg: float) -> tuple[DonorReferencePart, ...]:
    parts: list[DonorReferencePart] = [
        DonorReferencePart(
            "LEGACY_PR63_FRAME_PERIMETER_REACTION_MEMBER",
            None,
            "SIMPLE_ELLIPTICAL_FRAME_DONOR_REFERENCE_ONLY",
            _ring(
                *DONOR_FUNCTIONAL_FRAME_XY_MM,
                DONOR_FRAME_MEMBER_RADIAL_MM,
                DONOR_FRAME_DEPTH_MM,
                DONOR_FRAME_Z_REAR_MM,
            ),
        )
    ]
    for zone_id, origin, sign in DONOR_ZONE_CANDIDATES:
        parts.append(
            DonorReferencePart(
                f"LEGACY_PR63_{zone_id}_MOUNT_COLLAR",
                zone_id,
                "FIXED_BASELINE_CLOSED_COLLAR_ACCEPTED_BY_RAW_SHOE_OVERLAP_IN_DONOR",
                _collar(origin, sign, baseline_angle_deg),
            )
        )
        parts.append(
            DonorReferencePart(
                f"LEGACY_PR63_{zone_id}_REACTION_SHOE",
                zone_id,
                "AXIS_ALIGNED_SHOE_ACCEPTED_BY_RAW_FRAME_OVERLAP_IN_DONOR",
                _shoe(origin),
            )
        )
    return tuple(parts)


def _part_map(parts: tuple[DonorReferencePart, ...]) -> dict[str, DonorReferencePart]:
    result = {part.part_id: part for part in parts}
    if len(result) != len(parts):
        raise LegacyActuatorDonorAuditError("duplicate donor part IDs")
    return result


def _semantic_decisions() -> tuple[SemanticDecision, ...]:
    return (
        SemanticDecision(
            "FOUR_INDEPENDENT_ZONES",
            4,
            "CURRENT_AUTHORITY_REFERENCE_NOT_DONOR_SALVAGE",
            "Four independently controllable zones are current machine authority; the donor does not grant this architecture.",
        ),
        SemanticDecision(
            "SINGLE_LINEAR_AXIS_PER_ZONE",
            "ONE_LINEAR_AXIS_PER_ZONE",
            "SALVAGE_COMPATIBLE_SINGLE_AXIS_SEMANTIC_ONLY",
            "One commanded linear motion axis per zone remains compatible with current actuation semantics; no donor mount placement, carrier, force, or stiffness evidence is inherited.",
        ),
        SemanticDecision(
            "ANGLE_DOE_ROTATES_SAME_AXIS_NOT_SECOND_DOF",
            [50.0, 55.0, 61.0, 67.0, 72.0],
            "SALVAGE_COMPATIBLE_SINGLE_AXIS_SEMANTIC_ONLY",
            "The authority angle DOE changes candidate axis orientation. It is not a second mechanism degree of freedom or permission for the installed actuator to articulate through the DOE.",
        ),
        SemanticDecision(
            "ACTUATOR_PACKAGE_REFERENCE_DIAMETER_LENGTH_MM",
            [DONOR_ACTUATOR_DIAMETER_MM, DONOR_ACTUATOR_LENGTH_MM],
            "SALVAGE_CURRENT_SOURCE_PACKAGING_INTENT_ONLY",
            "The donor 10.2 mm diameter by 18.7 mm cylinder matches the current model package-reference source and may be used only for reference packaging until actuator selection is controlled.",
        ),
        SemanticDecision(
            "COAXIAL_CARRIER_PACKAGING_INTENT",
            "CARRIER_CENTERED_ON_SINGLE_ACTUATOR_AXIS",
            "SALVAGE_CURRENT_SOURCE_PACKAGING_INTENT_ONLY",
            "A carrier may remain coaxial with the single actuator package axis, but the donor closed collar dimensions, fixed orientation, overlap attachment, and service semantics are rejected.",
        ),
        SemanticDecision(
            "DONOR_CLOSED_COLLAR_DIMENSIONS_MM",
            [DONOR_COLLAR_OUTER_DIAMETER_MM, DONOR_COLLAR_INNER_DIAMETER_MM, DONOR_COLLAR_LENGTH_MM],
            "REJECT",
            "The fixed closed collar collides with the actuator under off-baseline authority DOE review and lacks split positive retention, keyed orientation, and current tolerance closure.",
        ),
        SemanticDecision(
            "DONOR_REACTION_SHOE_DIMENSIONS_MM",
            [DONOR_SHOE_XY_MM, DONOR_SHOE_XY_MM, DONOR_SHOE_DEPTH_MM],
            "REJECT",
            "The donor shoe occupies actuator motion and obtains its frame/collar engagement from unexplained positive material overlap.",
        ),
        SemanticDecision(
            "DONOR_SIMPLE_FRAME_RING",
            [*DONOR_FUNCTIONAL_FRAME_XY_MM, DONOR_FRAME_MEMBER_RADIAL_MM, DONOR_FRAME_DEPTH_MM, DONOR_FRAME_Z_REAR_MM],
            "REJECT",
            "Cell 6 owns current structural geometry. The donor ring is not a current reaction counterpart and intersects donor actuator motion.",
        ),
        SemanticDecision(
            "DONOR_WORLD_ZONE_ORIGINS",
            [list(origin.as_tuple()) for _zone_id, origin, _sign in DONOR_ZONE_CANDIDATES],
            "REJECT",
            "Current actuator_frames.py leaves origins, azimuths, structural mount datums, and selected envelopes unresolved. Donor world placements cannot fill those fields.",
        ),
    )


def _verify_current_package_references(model: MasckOneModel) -> None:
    if len(model.actuator_envelopes) != len(ZONE_IDS):
        raise LegacyActuatorDonorAuditError("current model no longer exposes exactly four actuator package references")
    expected_names = tuple(f"actuator_envelope_{index}" for index in range(1, 5))
    if tuple(component.name for component in model.actuator_envelopes) != expected_names:
        raise LegacyActuatorDonorAuditError("current actuator package-reference identity/order changed")
    expected_volume = math.pi * (DONOR_ACTUATOR_DIAMETER_MM / 2.0) ** 2 * DONOR_ACTUATOR_LENGTH_MM
    for component in model.actuator_envelopes:
        if component.status != "ALPHA_PHYSICS_REFERENCE":
            raise LegacyActuatorDonorAuditError("current actuator geometry was promoted beyond package-reference status")
        shape = component.solid.val()
        if not shape.isValid():
            raise LegacyActuatorDonorAuditError("current actuator package reference is invalid B-rep")
        if abs(float(shape.Volume()) - expected_volume) > PACKAGE_VOLUME_TOLERANCE_MM3:
            raise LegacyActuatorDonorAuditError("current actuator package B-rep no longer matches the 10.2 x 18.7 mm reference cylinder")


def build_legacy_actuator_donor_audit(model: MasckOneModel | None = None) -> LegacyActuatorDonorAudit:
    _require_current_sources()
    model = model or build_model()
    if str(model.authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise LegacyActuatorDonorAuditError("authority revision moved")
    if int(model.authority.number("actuation", "count")) != len(ZONE_IDS):
        raise LegacyActuatorDonorAuditError("current authority no longer contains four actuator zones")
    _verify_current_package_references(model)

    angle_doe = tuple(float(value) for value in model.authority.get("actuation", "clean", "axis_angle_doe_deg"))
    baseline = float(model.authority.get("actuation", "clean", "axis_angle_baseline_deg"))
    if tuple(sorted(set(angle_doe))) != angle_doe or baseline not in angle_doe:
        raise LegacyActuatorDonorAuditError("current authority angle DOE is malformed")

    parts = _reference_parts(baseline)
    part_by_id = _part_map(parts)
    frame = part_by_id["LEGACY_PR63_FRAME_PERIMETER_REACTION_MEMBER"]

    static_records: list[InterferenceRecord] = []
    angle_records: list[InterferenceRecord] = []

    for zone_id, origin, sign in DONOR_ZONE_CANDIDATES:
        collar = part_by_id[f"LEGACY_PR63_{zone_id}_MOUNT_COLLAR"]
        shoe = part_by_id[f"LEGACY_PR63_{zone_id}_REACTION_SHOE"]

        collar_shoe_volume = _intersection_volume(collar.solid, shoe.solid)
        static_records.append(
            InterferenceRecord(
                f"STATIC_{zone_id}_COLLAR_TO_SHOE",
                zone_id,
                None,
                collar.part_id,
                shoe.part_id,
                collar_shoe_volume,
                "FORBIDDEN_OVERLAP_AS_ATTACHMENT" if collar_shoe_volume > 0.0 else "CLEAR_REFERENCE_ONLY_NO_ATTACHMENT_PROVEN",
                "FORBID_RAW_MATERIAL_OVERLAP_AS_ATTACHMENT",
            )
        )
        shoe_frame_volume = _intersection_volume(shoe.solid, frame.solid)
        static_records.append(
            InterferenceRecord(
                f"STATIC_{zone_id}_SHOE_TO_FRAME",
                zone_id,
                None,
                shoe.part_id,
                frame.part_id,
                shoe_frame_volume,
                "FORBIDDEN_OVERLAP_AS_ATTACHMENT" if shoe_frame_volume > 0.0 else "CLEAR_REFERENCE_ONLY_NO_ATTACHMENT_PROVEN",
                "FORBID_RAW_MATERIAL_OVERLAP_AS_ATTACHMENT",
            )
        )

        for angle in angle_doe:
            actuator = _actuator(origin, sign, angle)
            source_id = f"LEGACY_PR63_{zone_id}_ACTUATOR_AT_{angle:g}_DEG"
            targets = (
                (
                    collar.part_id,
                    collar.solid,
                    "FORBID_FIXED_BASELINE_COLLAR_AS_ANGLE_DOE_CLEARANCE_GEOMETRY",
                ),
                (
                    shoe.part_id,
                    shoe.solid,
                    "FORBID_REACTION_SHOE_IN_ACTUATOR_MOTION",
                ),
                (
                    frame.part_id,
                    frame.solid,
                    "FORBID_FRAME_IN_ACTUATOR_MOTION",
                ),
            )
            for target_id, target_solid, pattern_id in targets:
                volume = _intersection_volume(actuator, target_solid)
                angle_records.append(
                    InterferenceRecord(
                        f"DOE_{zone_id}_{angle:g}_DEG_TO_{target_id}",
                        zone_id,
                        angle,
                        source_id,
                        target_id,
                        volume,
                        "LEGACY_MOVING_ACTUATOR_COLLISION" if volume > 0.0 else "CLEAR_REFERENCE_ONLY_NO_ATTACHMENT_PROVEN",
                        pattern_id,
                    )
                )

    all_records = tuple(static_records + angle_records)

    def positive_ids(pattern_id: str) -> tuple[str, ...]:
        return tuple(
            record.record_id
            for record in all_records
            if record.forbidden_pattern_id == pattern_id and record.intersection_volume_mm3 > 0.0
        )

    patterns = (
        ForbiddenGeometryPattern(
            "FORBID_RAW_MATERIAL_OVERLAP_AS_ATTACHMENT",
            "REJECT",
            positive_ids("FORBID_RAW_MATERIAL_OVERLAP_AS_ATTACHMENT"),
            "Unexplained positive solid intersection cannot be used as a mechanical attachment or load path.",
            "Use an explicit positive attachment, integral continuity, clearance, or reference-only relation with real mating geometry.",
        ),
        ForbiddenGeometryPattern(
            "FORBID_FIXED_BASELINE_COLLAR_AS_ANGLE_DOE_CLEARANCE_GEOMETRY",
            "REJECT",
            positive_ids("FORBID_FIXED_BASELINE_COLLAR_AS_ANGLE_DOE_CLEARANCE_GEOMETRY"),
            "A fixed 61 degree closed collar cannot be treated as clear merely because the baseline package fits inside its bore.",
            "Future carrier geometry must be keyed to one selected installed axis orientation and separately cross-screened against every DOE orientation before angle selection; the installed mechanism is not expected to articulate through the DOE.",
        ),
        ForbiddenGeometryPattern(
            "FORBID_REACTION_SHOE_IN_ACTUATOR_MOTION",
            "REJECT",
            positive_ids("FORBID_REACTION_SHOE_IN_ACTUATOR_MOTION"),
            "Reaction material cannot occupy the actuator package or operational motion envelope.",
            "Realize a separated carrier-to-reaction interface with positive retention, explicit clearances, final stops, and a typed reaction path.",
        ),
        ForbiddenGeometryPattern(
            "FORBID_FRAME_IN_ACTUATOR_MOTION",
            "REJECT",
            positive_ids("FORBID_FRAME_IN_ACTUATOR_MOTION"),
            "Structural frame material cannot occupy the actuator package or operational motion envelope.",
            "Cell 6 must provide explicit reaction counterparts outside the source-bound actuator clearance/sweep volume before Cell 7 can close world mounts.",
        ),
    )

    audit = LegacyActuatorDonorAudit(
        reference_parts=parts,
        static_overlap_records=tuple(static_records),
        angle_doe_records=tuple(angle_records),
        forbidden_patterns=patterns,
        semantic_decisions=_semantic_decisions(),
        angle_doe_deg=angle_doe,
        baseline_angle_deg=baseline,
        current_model_package_reference_status="MATCHES_CURRENT_MODEL_10P2_DIAMETER_X_18P7_LENGTH_REFERENCE_ONLY",
        current_mount_resolution_status="UNRESOLVED_PER_CURRENT_ACTUATOR_FRAMES_AND_COUPLING_SOURCES",
        physical_assembly_inclusion=False,
        physical_validation_eligible=False,
    )
    audit.__post_init__()
    return audit


def export_legacy_actuator_donor_review(
    output_dir: str | Path,
    model: MasckOneModel | None = None,
) -> dict[str, object]:
    model = model or build_model()
    audit = build_legacy_actuator_donor_audit(model=model)
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    fixed_step_name = "legacy_pr63_actuator_mount_reference_only.step"
    doe_step_name = "legacy_pr63_actuator_angle_doe_reference_only.step"
    manifest_name = "legacy_pr63_actuator_donor_audit.json"

    fixed_compound = cq.Compound.makeCompound([part.solid.val() for part in audit.reference_parts])
    cq.exporters.export(cq.Workplane(obj=fixed_compound), str(output / fixed_step_name))

    doe_solids = []
    for _zone_id, origin, sign in DONOR_ZONE_CANDIDATES:
        for angle in audit.angle_doe_deg:
            doe_solids.append(_actuator(origin, sign, angle).val())
    doe_compound = cq.Compound.makeCompound(doe_solids)
    cq.exporters.export(cq.Workplane(obj=doe_compound), str(output / doe_step_name))

    manifest = audit.manifest()
    manifest["review_artifact_role"] = REFERENCE_ROLE
    manifest["review_step_files"] = [fixed_step_name, doe_step_name]
    manifest["manifest_file"] = manifest_name
    manifest["physical_assembly_inclusion"] = False
    with (output / manifest_name).open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, allow_nan=False)
        handle.write("\n")

    return manifest
