"""Cell 17 source-bound datum, CTQ, and tolerance-closure inventory.

This module inventories released dimensional references and current tolerance
closure without promoting provisional references into manufacturing datums or
claiming process capability, metrology capability, fit, or physical validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
import re

from .actuator_frames import ZONE_IDS
from .authority import Authority, load_authority
from .spatial import CanonicalDatums
from .structural_frame import (
    DATUM_CENTER,
    DATUM_INFERIOR,
    DATUM_LEFT,
    DATUM_RIGHT,
    DATUM_SUPERIOR,
)

SCHEMA = "MASCK_ONE_CELL17_DATUM_CTQ_INVENTORY_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
LEGACY_SPATIAL_FRAME_ID = "MASCK_ONE_GLOBAL"
FRAME_CONTRACT_RELEASE_STATUS = "NOT_RELEASED_ON_SOURCE_MAIN"
EVIDENCE_STATUS = (
    "DIGITAL_DATUM_CTQ_AND_TOLERANCE_ARCHITECTURE_ONLY_NOT_PROCESS_CAPABILITY_"
    "METROLOGY_CAPABILITY_FIT_ASSEMBLY_PERFORMANCE_OR_PHYSICAL_VALIDATION"
)

SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("schemas/masck_one_authority.schema.json", "58accbe48619058cb99ab51a0387cf01874c3717"),
    ("src/masck_one/authority.py", "6866e3a428dab8b32b5a1d9e58da78b8f5aa1aa2"),
    ("src/masck_one/spatial.py", "8c1106b523fef5111009cc56236a53e3bc5ee10e"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
    ("src/masck_one/actuator_frames.py", "4c2013f994bdc9e084fe227eb5e166f973500ebb"),
    ("src/masck_one/mechanism_tolerance.py", "0a5fb13bdfe21f181f8910ef8abece88264950e2"),
    ("src/masck_one/mechanism_clearance_binding.py", "446177aa32420f89098f0fff86507177d220ad10"),
    ("src/masck_one/realized_waste_backbone.py", "6aa79d9a613e278f32da85b4654c0e35cc09b7ca"),
    ("src/masck_one/waste_cartridge_dfm.py", "f9788cce30c14600c8a624509153596e46c1e478"),
)
EXPECTED_ABSENT_RELEASE_PATHS = (
    "src/masck_one/frame_contract.py",
    "src/masck_one/frame_audit.py",
    "src/masck_one/structural_frame_dfm.py",
    "src/masck_one/actuator_mount_dfm.py",
    "src/masck_one/fluid_routing_dfm.py",
)

DATUM_KIND_VALUES = ("FRAME", "PLANE", "POINT", "REQUIRED_LOCAL_MOUNT_DATUM")
DATUM_RESOLUTION_VALUES = (
    "CANONICAL",
    "AUTHORITY_DERIVED",
    "DUPLICATE_IDENTITY_ALIAS_UNRELEASED_BINDING",
    "IMPLICIT_UNRESOLVED",
)
MANUFACTURING_DATUM_STATUS_VALUES = (
    "REFERENCE_ONLY_NOT_MANUFACTURING_DATUM",
    "NOT_QUALIFIED_3D_DATUM",
    "UNRESOLVED",
)
CTQ_STATUS_VALUES = ("DEFINED_DIGITAL_REQUIREMENT", "BLOCKED_UNRESOLVED_GEOMETRY_OR_DATUM")
TOLERANCE_KIND_VALUES = ("BILATERAL", "ABSOLUTE_MAX", "MINIMUM", "UNRESOLVED")
CANDIDATE_EVIDENCE = "UNRELEASED_CANDIDATE_SNAPSHOT_NOT_RELEASE_AUTHORITY"

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_ID = re.compile(r"^[A-Z][A-Z0-9_]{2,95}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]


class DatumCtqInventoryError(ValueError):
    pass


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise DatumCtqInventoryError(f"{label} must be exact nonblank text")
    return value


def _identity(value: object, *, label: str) -> str:
    text = _text(value, label=label)
    if _ID.fullmatch(text) is None:
        raise DatumCtqInventoryError(f"{label} must be canonical uppercase identity text")
    return text


def _exact_bool(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise DatumCtqInventoryError(f"{label} must be an exact bool")
    return value


def _finite(value: object, *, label: str) -> float:
    if type(value) not in (int, float):
        raise DatumCtqInventoryError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise DatumCtqInventoryError(f"{label} must be finite")
    return 0.0 if result == 0.0 else result


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_source_files_current() -> None:
    for relative_path, expected in SOURCE_GIT_BLOB_IDENTITIES:
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise DatumCtqInventoryError(f"datum/CTQ source file is missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise DatumCtqInventoryError(
                f"datum/CTQ source moved at {relative_path}; expected {expected}, got {actual}"
            )
    for relative_path in EXPECTED_ABSENT_RELEASE_PATHS:
        if (_REPO_ROOT / relative_path).exists():
            raise DatumCtqInventoryError(
                f"previously absent datum/DFM source appeared at {relative_path}; reconstruct live release state"
            )


def _require_canonical_authority(authority: Authority) -> None:
    if type(authority) is not Authority:
        raise DatumCtqInventoryError("datum/CTQ inventory requires exact Authority type")
    canonical = load_authority()
    if authority.data != canonical.data:
        raise DatumCtqInventoryError("supplied authority differs from released machine authority")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise DatumCtqInventoryError("authority revision moved")


@dataclass(frozen=True, slots=True)
class DatumObservation:
    observation_id: str
    producer: str
    source_path: str
    datum_label: str
    datum_kind: str
    coordinate_frame_id: str
    coordinates_xyz_mm: tuple[float | None, float | None, float | None] | None
    resolution: str
    manufacturing_datum_status: str
    evidence_status: str = "DIGITAL_REFERENCE_ONLY"

    def __post_init__(self) -> None:
        _identity(self.observation_id, label="datum observation ID")
        _text(self.producer, label="datum producer")
        _text(self.source_path, label="datum source path")
        _text(self.datum_label, label="datum label")
        if self.datum_kind not in DATUM_KIND_VALUES:
            raise DatumCtqInventoryError("unsupported datum kind")
        _text(self.coordinate_frame_id, label="coordinate frame ID")
        if self.resolution not in DATUM_RESOLUTION_VALUES:
            raise DatumCtqInventoryError("unsupported datum resolution")
        if self.manufacturing_datum_status not in MANUFACTURING_DATUM_STATUS_VALUES:
            raise DatumCtqInventoryError("unsupported manufacturing datum status")
        if self.evidence_status != "DIGITAL_REFERENCE_ONLY":
            raise DatumCtqInventoryError("datum observation cannot imply physical evidence")
        if self.coordinates_xyz_mm is not None:
            if type(self.coordinates_xyz_mm) is not tuple or len(self.coordinates_xyz_mm) != 3:
                raise DatumCtqInventoryError("datum coordinates must be exact XYZ tuple or None")
            for value in self.coordinates_xyz_mm:
                if value is not None:
                    _finite(value, label="datum coordinate")
        if self.resolution == "IMPLICIT_UNRESOLVED":
            if self.coordinates_xyz_mm is not None or self.manufacturing_datum_status != "UNRESOLVED":
                raise DatumCtqInventoryError("implicit unresolved datum cannot carry coordinates or qualification")
        if self.manufacturing_datum_status == "NOT_QUALIFIED_3D_DATUM":
            if self.coordinates_xyz_mm is None or self.coordinates_xyz_mm[2] is not None:
                raise DatumCtqInventoryError("unqualified 3D datum must preserve unresolved Z")
        if self.resolution == "CANONICAL" and self.coordinate_frame_id != WORLD_FRAME_ID:
            raise DatumCtqInventoryError("canonical datum must use authority-world frame")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "observation_id": self.observation_id,
            "producer": self.producer,
            "source_path": self.source_path,
            "datum_label": self.datum_label,
            "datum_kind": self.datum_kind,
            "coordinate_frame_id": self.coordinate_frame_id,
            "coordinates_xyz_mm": None if self.coordinates_xyz_mm is None else list(self.coordinates_xyz_mm),
            "resolution": self.resolution,
            "manufacturing_datum_status": self.manufacturing_datum_status,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class DuplicateDatumGroup:
    group_id: str
    observation_ids: tuple[str, ...]
    relationship: str
    released_binding_status: str
    manufacturing_interchangeability_allowed: bool = False

    def __post_init__(self) -> None:
        _identity(self.group_id, label="duplicate datum group ID")
        if type(self.observation_ids) is not tuple or len(self.observation_ids) < 2:
            raise DatumCtqInventoryError("duplicate datum group requires at least two observations")
        if len(set(self.observation_ids)) != len(self.observation_ids):
            raise DatumCtqInventoryError("duplicate datum group observations must be unique")
        for item in self.observation_ids:
            _identity(item, label="duplicate datum observation ID")
        _text(self.relationship, label="duplicate datum relationship")
        _text(self.released_binding_status, label="duplicate datum binding status")
        if _exact_bool(
            self.manufacturing_interchangeability_allowed,
            label="manufacturing datum interchangeability",
        ):
            raise DatumCtqInventoryError(
                "duplicate digital references cannot become interchangeable manufacturing datums without qualification"
            )

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "group_id": self.group_id,
            "observation_ids": list(self.observation_ids),
            "relationship": self.relationship,
            "released_binding_status": self.released_binding_status,
            "manufacturing_interchangeability_allowed": self.manufacturing_interchangeability_allowed,
        }


@dataclass(frozen=True, slots=True)
class CtqRecord:
    ctq_id: str
    source: str
    owner: str
    characteristic: str
    unit: str
    tolerance_kind: str
    nominal: float | None
    lower_limit: float | None
    upper_limit: float | None
    status: str
    inspection_reference: str
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        _identity(self.ctq_id, label="CTQ ID")
        for label, value in (
            ("CTQ source", self.source),
            ("CTQ owner", self.owner),
            ("CTQ characteristic", self.characteristic),
            ("CTQ unit", self.unit),
            ("CTQ inspection reference", self.inspection_reference),
        ):
            _text(value, label=label)
        if self.tolerance_kind not in TOLERANCE_KIND_VALUES:
            raise DatumCtqInventoryError("unsupported tolerance kind")
        if self.status not in CTQ_STATUS_VALUES:
            raise DatumCtqInventoryError("unsupported CTQ status")
        numeric = (self.nominal, self.lower_limit, self.upper_limit)
        for value in numeric:
            if value is not None:
                _finite(value, label="CTQ numeric")
        if self.status == "BLOCKED_UNRESOLVED_GEOMETRY_OR_DATUM":
            if self.tolerance_kind != "UNRESOLVED" or any(value is not None for value in numeric):
                raise DatumCtqInventoryError("blocked CTQ cannot invent numeric limits")
        else:
            if self.tolerance_kind == "UNRESOLVED":
                raise DatumCtqInventoryError("defined CTQ cannot use unresolved tolerance kind")
        if self.lower_limit is not None and self.upper_limit is not None:
            if self.lower_limit > self.upper_limit:
                raise DatumCtqInventoryError("CTQ limits are reversed")
        if _exact_bool(self.physical_validation_eligible, label="CTQ physical validation eligibility"):
            raise DatumCtqInventoryError("digital CTQ cannot become physical validation evidence")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "ctq_id": self.ctq_id,
            "source": self.source,
            "owner": self.owner,
            "characteristic": self.characteristic,
            "unit": self.unit,
            "tolerance_kind": self.tolerance_kind,
            "nominal": self.nominal,
            "lower_limit": self.lower_limit,
            "upper_limit": self.upper_limit,
            "status": self.status,
            "inspection_reference": self.inspection_reference,
            "physical_validation_eligible": self.physical_validation_eligible,
        }


@dataclass(frozen=True, slots=True)
class CandidateCell5BlockerSnapshot:
    pr_number: int
    exact_head_sha: str
    blocker_id: str
    upstream_owner: str
    required_closure: str
    evidence_status: str = CANDIDATE_EVIDENCE

    def __post_init__(self) -> None:
        if type(self.pr_number) is not int or self.pr_number <= 0:
            raise DatumCtqInventoryError("candidate PR number must be exact positive int")
        if type(self.exact_head_sha) is not str or _SHA40.fullmatch(self.exact_head_sha) is None:
            raise DatumCtqInventoryError("candidate PR head must be exact lowercase 40-hex")
        _identity(self.blocker_id, label="candidate blocker ID")
        _text(self.upstream_owner, label="candidate blocker owner")
        _text(self.required_closure, label="candidate blocker closure")
        if self.evidence_status != CANDIDATE_EVIDENCE:
            raise DatumCtqInventoryError("unreleased candidate cannot be promoted to release authority")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "pr_number": self.pr_number,
            "exact_head_sha": self.exact_head_sha,
            "blocker_id": self.blocker_id,
            "upstream_owner": self.upstream_owner,
            "required_closure": self.required_closure,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class DatumCtqInventory:
    schema: str
    source_main_sha: str
    authority_revision: str
    authority_blob_sha: str
    canonical_world_frame_id: str
    cross_system_frame_contract_status: str
    datums: tuple[DatumObservation, ...]
    duplicate_datum_groups: tuple[DuplicateDatumGroup, ...]
    ctqs: tuple[CtqRecord, ...]
    candidate_frame_contract_pr_number: int
    candidate_frame_contract_head_sha: str
    candidate_cell5_blockers: tuple[CandidateCell5BlockerSnapshot, ...]
    digital_mvp_dimensional_ready: bool
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise DatumCtqInventoryError("unexpected datum/CTQ schema")
        if self.source_main_sha != SOURCE_MAIN_SHA or _SHA40.fullmatch(self.source_main_sha) is None:
            raise DatumCtqInventoryError("datum/CTQ inventory is stale for released main")
        if self.authority_revision != AUTHORITY_REVISION:
            raise DatumCtqInventoryError("datum/CTQ authority revision is stale")
        if self.authority_blob_sha != AUTHORITY_BLOB_SHA:
            raise DatumCtqInventoryError("datum/CTQ authority blob is stale")
        if self.canonical_world_frame_id != WORLD_FRAME_ID:
            raise DatumCtqInventoryError("datum/CTQ inventory must use authority-world frame")
        if self.cross_system_frame_contract_status != FRAME_CONTRACT_RELEASE_STATUS:
            raise DatumCtqInventoryError("cross-system frame-contract release status changed")
        if type(self.candidate_frame_contract_pr_number) is not int or self.candidate_frame_contract_pr_number != 79:
            raise DatumCtqInventoryError("cross-system frame-contract candidate PR identity changed")
        if type(self.candidate_frame_contract_head_sha) is not str or _SHA40.fullmatch(self.candidate_frame_contract_head_sha) is None:
            raise DatumCtqInventoryError("cross-system frame-contract candidate head must be exact lowercase 40-hex")
        for collection, label in (
            (self.datums, "datum"),
            (self.duplicate_datum_groups, "duplicate datum group"),
            (self.ctqs, "CTQ"),
            (self.candidate_cell5_blockers, "candidate blocker"),
        ):
            if type(collection) is not tuple or not collection:
                raise DatumCtqInventoryError(f"{label} collection must be exact nonempty tuple")
        if len({item.observation_id for item in self.datums}) != len(self.datums):
            raise DatumCtqInventoryError("datum observation identities must be unique")
        datum_ids = {item.observation_id for item in self.datums}
        for group in self.duplicate_datum_groups:
            group.__post_init__()
            if not set(group.observation_ids).issubset(datum_ids):
                raise DatumCtqInventoryError("duplicate datum group references unknown observation")
        if len({item.ctq_id for item in self.ctqs}) != len(self.ctqs):
            raise DatumCtqInventoryError("CTQ identities must be unique")
        if len({(item.pr_number, item.blocker_id) for item in self.candidate_cell5_blockers}) != len(
            self.candidate_cell5_blockers
        ):
            raise DatumCtqInventoryError("candidate blocker snapshots must be unique")
        for item in self.datums:
            item.__post_init__()
        for item in self.ctqs:
            item.__post_init__()
        for item in self.candidate_cell5_blockers:
            item.__post_init__()
        if not any(item.resolution == "IMPLICIT_UNRESOLVED" for item in self.datums):
            raise DatumCtqInventoryError("inventory unexpectedly claims every datum is explicit")
        if not any(item.status == "BLOCKED_UNRESOLVED_GEOMETRY_OR_DATUM" for item in self.ctqs):
            raise DatumCtqInventoryError("inventory unexpectedly claims all CTQs are closed")
        if _exact_bool(self.digital_mvp_dimensional_ready, label="digital dimensional readiness"):
            raise DatumCtqInventoryError("current release cannot be dimensionally ready while datum/CTQ blockers remain")
        if _exact_bool(self.physical_validation_eligible, label="inventory physical validation eligibility"):
            raise DatumCtqInventoryError("digital inventory cannot become physical validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise DatumCtqInventoryError("datum/CTQ evidence boundary changed")

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def validate_current_sources(self) -> None:
        self.__post_init__()
        _require_source_files_current()
        _require_canonical_authority(load_authority())

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.__post_init__()
        payload: dict[str, object] = {
            "schema": self.schema,
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "canonical_world_frame_id": self.canonical_world_frame_id,
            "cross_system_frame_contract_status": self.cross_system_frame_contract_status,
            "candidate_frame_contract": {
                "pr_number": self.candidate_frame_contract_pr_number,
                "exact_head_sha": self.candidate_frame_contract_head_sha,
                "evidence_status": CANDIDATE_EVIDENCE,
            },
            "source_git_blob_identities": [
                {"path": path, "blob_sha": blob_sha}
                for path, blob_sha in SOURCE_GIT_BLOB_IDENTITIES
            ],
            "expected_absent_release_paths": list(EXPECTED_ABSENT_RELEASE_PATHS),
            "datums": [item.manifest() for item in self.datums],
            "duplicate_datum_groups": [item.manifest() for item in self.duplicate_datum_groups],
            "ctqs": [item.manifest() for item in self.ctqs],
            "candidate_cell5_blockers": [item.manifest() for item in self.candidate_cell5_blockers],
            "candidate_evidence_rule": "EXACT_HEAD_SNAPSHOT_ONLY_RECONSTRUCT_LIVE_PR_BEFORE_CONSUMPTION",
            "unresolved_datum_count": sum(item.resolution == "IMPLICIT_UNRESOLVED" for item in self.datums),
            "blocked_ctq_count": sum(item.status == "BLOCKED_UNRESOLVED_GEOMETRY_OR_DATUM" for item in self.ctqs),
            "digital_mvp_dimensional_ready": self.digital_mvp_dimensional_ready,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            payload["manifest_sha256"] = sha256(raw).hexdigest()
        return payload


def _datum_inventory(authority: Authority) -> tuple[DatumObservation, ...]:
    canonical = CanonicalDatums.from_authority(authority)
    origin = canonical.global_frame.origin.as_tuple()
    width, height = authority.pair("geometry", "functional_frame_xy_mm")
    structural = (
        (DATUM_CENTER, (0.0, 0.0, None)),
        (DATUM_SUPERIOR, (0.0, height / 2.0, None)),
        (DATUM_INFERIOR, (0.0, -height / 2.0, None)),
        (DATUM_LEFT, (-width / 2.0, 0.0, None)),
        (DATUM_RIGHT, (width / 2.0, 0.0, None)),
    )
    result: list[DatumObservation] = [
        DatumObservation(
            "DATUM_AUTHORITY_WORLD",
            "machine authority",
            "config/masck_one_authority.yaml:coordinate_system",
            WORLD_FRAME_ID,
            "FRAME",
            WORLD_FRAME_ID,
            origin,
            "CANONICAL",
            "REFERENCE_ONLY_NOT_MANUFACTURING_DATUM",
        ),
        DatumObservation(
            "DATUM_SPATIAL_GLOBAL_ALIAS",
            "CanonicalDatums",
            "src/masck_one/spatial.py:CanonicalDatums.from_authority",
            canonical.global_frame.name,
            "FRAME",
            LEGACY_SPATIAL_FRAME_ID,
            origin,
            "DUPLICATE_IDENTITY_ALIAS_UNRELEASED_BINDING",
            "REFERENCE_ONLY_NOT_MANUFACTURING_DATUM",
        ),
        DatumObservation(
            "DATUM_SAGITTAL_PLANE",
            "CanonicalDatums",
            "src/masck_one/spatial.py:CanonicalDatums.from_authority",
            canonical.sagittal_plane.name,
            "PLANE",
            WORLD_FRAME_ID,
            origin,
            "AUTHORITY_DERIVED",
            "REFERENCE_ONLY_NOT_MANUFACTURING_DATUM",
        ),
        DatumObservation(
            "DATUM_TRANSVERSE_PLANE",
            "CanonicalDatums",
            "src/masck_one/spatial.py:CanonicalDatums.from_authority",
            canonical.transverse_plane.name,
            "PLANE",
            WORLD_FRAME_ID,
            origin,
            "AUTHORITY_DERIVED",
            "REFERENCE_ONLY_NOT_MANUFACTURING_DATUM",
        ),
        DatumObservation(
            "DATUM_CORONAL_PLANE",
            "CanonicalDatums",
            "src/masck_one/spatial.py:CanonicalDatums.from_authority",
            canonical.coronal_plane.name,
            "PLANE",
            WORLD_FRAME_ID,
            origin,
            "AUTHORITY_DERIVED",
            "REFERENCE_ONLY_NOT_MANUFACTURING_DATUM",
        ),
    ]
    for datum_id, coords in structural:
        suffix = datum_id.removeprefix("MASCK_ONE-FRAME-DATUM-").replace("-", "_")
        result.append(
            DatumObservation(
                f"DATUM_FRAME_{suffix}",
                "StructuralFrameTopology",
                "src/masck_one/structural_frame.py:_datums",
                datum_id,
                "POINT",
                WORLD_FRAME_ID,
                coords,
                "AUTHORITY_DERIVED",
                "NOT_QUALIFIED_3D_DATUM",
            )
        )
    for zone_id in ZONE_IDS:
        result.append(
            DatumObservation(
                f"DATUM_{zone_id}_MOUNT",
                "ActuatorFrameArchitecture",
                "src/masck_one/actuator_frames.py:build_actuator_frame_architecture",
                "UNRESOLVED",
                "REQUIRED_LOCAL_MOUNT_DATUM",
                WORLD_FRAME_ID,
                None,
                "IMPLICIT_UNRESOLVED",
                "UNRESOLVED",
            )
        )
    result.append(
        DatumObservation(
            "DATUM_MECHANISM_CLEARANCE_FRAME",
            "CollisionClearanceBinding",
            "src/masck_one/mechanism_clearance_binding.py:CollisionClearanceBinding",
            "CALLER_SUPPLIED_GENERIC_ID",
            "FRAME",
            "UNRESOLVED",
            None,
            "IMPLICIT_UNRESOLVED",
            "UNRESOLVED",
        )
    )
    return tuple(result)


def _ctq_inventory(authority: Authority) -> tuple[CtqRecord, ...]:
    seam_nominal = float(authority.get("geometry", "visible_seam", "gap_mm"))
    seam_tol = float(authority.get("geometry", "visible_seam", "tolerance_mm"))
    flush_max = float(authority.get("geometry", "visible_seam", "flush_mismatch_max_mm"))
    shell_nominal = float(authority.get("geometry", "shell_nominal_wall_mm"))
    shell_min = float(authority.get("geometry", "shell_absolute_development_min_mm"))
    return (
        CtqRecord(
            "CTQ_VISIBLE_SEAM_GAP",
            "machine authority geometry.visible_seam",
            "WHOLE_PRODUCT_PART_SPLIT_OWNER",
            "visible seam gap",
            "mm",
            "BILATERAL",
            seam_nominal,
            seam_nominal - seam_tol,
            seam_nominal + seam_tol,
            "DEFINED_DIGITAL_REQUIREMENT",
            "FINAL_MATING_SEAM_DATUM_AND_INSPECTION_FIXTURE_UNRESOLVED",
        ),
        CtqRecord(
            "CTQ_VISIBLE_SEAM_FLUSH_MISMATCH",
            "machine authority geometry.visible_seam",
            "WHOLE_PRODUCT_PART_SPLIT_OWNER",
            "absolute visible seam flush mismatch",
            "mm",
            "ABSOLUTE_MAX",
            0.0,
            0.0,
            flush_max,
            "DEFINED_DIGITAL_REQUIREMENT",
            "FINAL_MATING_SEAM_DATUM_AND_INSPECTION_FIXTURE_UNRESOLVED",
        ),
        CtqRecord(
            "CTQ_SHELL_WALL_MINIMUM",
            "machine authority geometry shell wall",
            "SHELL_GEOMETRY_OWNER",
            "shell wall thickness",
            "mm",
            "MINIMUM",
            shell_nominal,
            shell_min,
            None,
            "DEFINED_DIGITAL_REQUIREMENT",
            "A_SURFACE_TO_INNER_WALL_NORMAL_THICKNESS_INSPECTION_REFERENCE_PENDING_FINAL_PART_SPLIT",
        ),
        CtqRecord(
            "CTQ_STRUCTURAL_FRAME_3D_DATUM_QUALIFICATION",
            "released structural_frame.py plus Cell 5 PR #82 candidate blocker",
            "STRUCTURAL_FRAME_GEOMETRY_OWNER",
            "3D structural frame primary/secondary/tertiary manufacturing datum scheme",
            "mm",
            "UNRESOLVED",
            None,
            None,
            None,
            "BLOCKED_UNRESOLVED_GEOMETRY_OR_DATUM",
            "BLOCKED_UNTIL_REALIZED_3D_FRAME_MEMBERS_AND_FRAME_SHELL_JOIN_EXIST",
        ),
        CtqRecord(
            "CTQ_ACTUATOR_MOUNT_DATUM_FIT_STACK",
            "released actuator_frames.py plus Cell 5 PR #91 candidate blocker",
            "ACTUATOR_MOUNT_GEOMETRY_OWNER",
            "four-zone actuator mount datum, retention, frame-join and stop fit stack",
            "mm",
            "UNRESOLVED",
            None,
            None,
            None,
            "BLOCKED_UNRESOLVED_GEOMETRY_OR_DATUM",
            "BLOCKED_UNTIL_MOUNT_ORIGINS_AZIMUTHS_DATUMS_ENVELOPES_REACTION_AND_STOP_GEOMETRY_EXIST",
        ),
        CtqRecord(
            "CTQ_MECHANISM_CLEARANCE_FRAME_BINDING",
            "released mechanism_tolerance.py and mechanism_clearance_binding.py",
            "DIMENSIONAL_ENGINEERING",
            "clearance-stack coordinate frame must bind to authority world or explicit local-to-world transform",
            "mm",
            "UNRESOLVED",
            None,
            None,
            None,
            "BLOCKED_UNRESOLVED_GEOMETRY_OR_DATUM",
            "CURRENT_BINDING_PROVES_SAME_STRING_ONLY_AND_TESTS_ACCEPT_GENERIC_ROOT_WORLD",
        ),
        CtqRecord(
            "CTQ_WASTE_CARTRIDGE_CRITICAL_FIT_STACKS",
            "released waste_cartridge_dfm.py requirement CARTRIDGE_DFM_TOLERANCE_AND_PROCESS",
            "CELL4_WASTE_CARTRIDGE_GEOMETRY",
            "body-to-closure, key/latch, seal gland/land and device insertion min-max stacks",
            "mm",
            "UNRESOLVED",
            None,
            None,
            None,
            "BLOCKED_UNRESOLVED_GEOMETRY_OR_DATUM",
            "BLOCKED_UNTIL_REALIZED_CARTRIDGE_PART_SPLIT_SEAL_RETENTION_AND_SERVICE_GEOMETRY_EXIST",
        ),
        CtqRecord(
            "CTQ_FLUID_ROUTING_CRITICAL_FIT_STACKS",
            "Cell 5 PR #99 candidate blocker only",
            "FLUID_ROUTING_GEOMETRY_OWNER",
            "connector, clip, manifold and route-separation tolerance stacks",
            "mm",
            "UNRESOLVED",
            None,
            None,
            None,
            "BLOCKED_UNRESOLVED_GEOMETRY_OR_DATUM",
            "CANDIDATE_ONLY_BLOCKED_UNTIL_RELEASED_ROUTE_CONNECTOR_MANIFOLD_AND_RETENTION_GEOMETRY_EXISTS",
        ),
    )


def _candidate_cell5_blockers() -> tuple[CandidateCell5BlockerSnapshot, ...]:
    return (
        CandidateCell5BlockerSnapshot(
            82,
            "a52dbf7fab09b0e82715d6c800b07e35c6216965",
            "CELL5_STRUCTURAL_FRAME_DFM_DATUM_AND_JOIN_CLOSURE",
            "STRUCTURAL_FRAME_GEOMETRY_OWNER",
            "Realize 3D frame members/cross-section and explicit frame-shell joins before selecting manufacturing datums or fit stacks.",
        ),
        CandidateCell5BlockerSnapshot(
            91,
            "c57b577d4e4d3333ecfb736be7fc4462dd7fa823",
            "CELL5_ACTUATOR_MOUNT_TOLERANCE_STACK_CLOSURE",
            "ACTUATOR_MOUNT_GEOMETRY_OWNER",
            "Resolve source-bound mount datums and publish actuator fit, retention, frame-join and positive-stop tolerance stacks.",
        ),
        CandidateCell5BlockerSnapshot(
            99,
            "072d59bd7a278385818cf19af38dbca58b8b1bd7",
            "CELL5_FLUID_ROUTING_TOLERANCE_STACK_CLOSURE",
            "FLUID_ROUTING_GEOMETRY_OWNER",
            "Publish connector, clip, manifold and route-separation tolerance stacks after production-intent route geometry exists.",
        ),
    )


def build_datum_ctq_inventory(*, authority: Authority | None = None) -> DatumCtqInventory:
    _require_source_files_current()
    authority = authority or load_authority()
    _require_canonical_authority(authority)
    if str(authority.get("project", "units", "length")) != "mm":
        raise DatumCtqInventoryError("dimensional inventory requires authority length unit mm")
    if tuple(authority.get("coordinate_system", "origin")) != (0.0, 0.0, 0.0):
        raise DatumCtqInventoryError("authority-world origin moved")
    axis_semantics = (
        authority.get("coordinate_system", "x_positive"),
        authority.get("coordinate_system", "y_positive"),
        authority.get("coordinate_system", "z_positive"),
    )
    if axis_semantics != ("wearer_right", "superior", "anterior"):
        raise DatumCtqInventoryError("authority-world axis semantics moved")

    datums = _datum_inventory(authority)
    duplicate = DuplicateDatumGroup(
        "DUPLICATE_WORLD_FRAME_IDENTITY_ALIAS",
        ("DATUM_AUTHORITY_WORLD", "DATUM_SPATIAL_GLOBAL_ALIAS"),
        "IDENTICAL_ORIGIN_AND_BASIS_BUT_DISTINCT_FRAME_LABELS",
        "OPEN_CELL1_PR79_PROPOSES_EXPLICIT_IDENTITY_ALIAS_NOT_RELEASED_ON_SOURCE_MAIN",
    )
    inventory = DatumCtqInventory(
        schema=SCHEMA,
        source_main_sha=SOURCE_MAIN_SHA,
        authority_revision=AUTHORITY_REVISION,
        authority_blob_sha=AUTHORITY_BLOB_SHA,
        canonical_world_frame_id=WORLD_FRAME_ID,
        cross_system_frame_contract_status=FRAME_CONTRACT_RELEASE_STATUS,
        candidate_frame_contract_pr_number=79,
        candidate_frame_contract_head_sha="7f60cae4962ffc49ed8e77faf77534f4fd82b1f5",
        datums=datums,
        duplicate_datum_groups=(duplicate,),
        ctqs=_ctq_inventory(authority),
        candidate_cell5_blockers=_candidate_cell5_blockers(),
        digital_mvp_dimensional_ready=False,
        physical_validation_eligible=False,
        evidence_status=EVIDENCE_STATUS,
    )
    inventory.validate_current_sources()
    return inventory


def write_datum_ctq_inventory(
    output_dir: str | Path,
    *,
    inventory: DatumCtqInventory | None = None,
) -> dict[str, object]:
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    inventory = inventory or build_datum_ctq_inventory()
    inventory.validate_current_sources()
    payload = inventory.manifest()
    with (output / "datum_ctq_inventory.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return payload


def main() -> int:
    print(json.dumps(build_datum_ctq_inventory().manifest(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
