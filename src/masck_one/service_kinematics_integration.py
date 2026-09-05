"""Whole-product service kinematics integration V1.

This Cell 1 layer composes the *released service contracts* for quick release, routine
service entry, water refill, cleanser refill and waste-cartridge service with the live
repository's candidate/legacy motion sources. It deliberately does not import any
unmerged candidate B-rep. Current-main motion geometry that does not exist remains
blocked instead of being reconstructed from PR prose or legacy dimensions.

The model provides deterministic whole-product service states and conservative digital
interlocks. Those interlocks are engineering integration policy, not measured human-
factors, wet-hand, force, timing, sealing, durability or serviceability evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha1, sha256
import json
from pathlib import Path
import re

from .authority import Authority, load_authority
from .cleanser_storage import PORT_REFILL as CLEANSER_PORT_REFILL, build_cleanser_storage_architecture
from .mechanism_state import MechanismState, OperatingMode, TransitionAction, validate_transition
from .water_reservoir import PORT_FILL as WATER_PORT_FILL, build_water_reservoir_architecture
from .waste_cartridge import (
    INTERFACE_SERVICE as WASTE_CARTRIDGE_SERVICE_INTERFACE,
    SERVICE_STATUS as WASTE_CARTRIDGE_SERVICE_STATUS,
)


SCHEMA = "MASCK_ONE_WHOLE_PRODUCT_SERVICE_KINEMATICS_V1"
SOURCE_MAIN_SHA = "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
DIGITAL_ONLY = (
    "DIGITAL_SERVICE_STATE_AND_PROVENANCE_ONLY_NOT_PHYSICAL_SERVICE_WET_HAND_RELEASE_"
    "FORCE_TIME_FIT_COMFORT_SEAL_LEAKAGE_HYGIENE_DURABILITY_OR_SAFETY_VALIDATION"
)

RELEASED_SOURCE_BLOBS = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/mechanism_state.py", "d2589ebdd8b091606f5b190daad237bdfc946109"),
    ("src/masck_one/waste_cartridge.py", "9dc0fe8a0ed92083c68406da3993e57e767e2483"),
    ("src/masck_one/water_reservoir.py", "6c14a37d07855550f0bd502e8308ed46682bc19c"),
    ("src/masck_one/cleanser_storage.py", "5e087ca8b05da8352ad4800b2ef8280ea8ddcf29"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
)

# These paths are intentionally absent from released main at this source. If a later
# producer release adds one, this V1 must be rebound rather than silently treating that
# new geometry as previously integrated service truth.
EXPECTED_ABSENT_CURRENT_MAIN_PATHS = (
    "src/masck_one/right_quick_release_sweep.py",
    "src/masck_one/occipital_stabilizer.py",
    "src/masck_one/retention_fit_adjustment.py",
    "src/masck_one/hair_pinch_keepouts.py",
    "src/masck_one/realized_water_reservoir.py",
    "src/masck_one/water_reservoir_closure.py",
    "src/masck_one/cleanser_service_envelope.py",
    "src/masck_one/electronics_package.py",
    "src/masck_one/mechanical_assembly_kinematics.py",
)

_SHA1_RE = re.compile(r"[0-9a-f]{40}\Z")
_TEXT_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_REPO_ROOT = Path(__file__).resolve().parents[2]


class ServiceKinematicsError(ValueError):
    """Raised when service-state integration would over-promote current evidence."""


class ServiceDomain(str, Enum):
    EMERGENCY_RELEASE = "EMERGENCY_RELEASE"
    RETENTION_ADJUSTMENT = "RETENTION_ADJUSTMENT"
    WATER_REFILL = "WATER_REFILL"
    CLEANSER_REFILL = "CLEANSER_REFILL"
    WASTE_CARTRIDGE = "WASTE_CARTRIDGE"
    BATTERY_DOOR = "BATTERY_DOOR"
    SERVICE_COVER = "SERVICE_COVER"


class CandidateClass(str, Enum):
    NONAUTHORITATIVE_CANDIDATE = "NONAUTHORITATIVE_CANDIDATE"
    STACKED_NONAUTHORITATIVE_CANDIDATE = "STACKED_NONAUTHORITATIVE_CANDIDATE"
    LEGACY_DONOR_ONLY = "LEGACY_DONOR_ONLY"


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ServiceKinematicsError(f"{label} must be exact nonblank text")
    return value


def _sha1(value: object, *, label: str) -> str:
    text = _text(value, label=label)
    if _SHA1_RE.fullmatch(text) is None:
        raise ServiceKinematicsError(f"{label} must be lowercase 40-hex")
    return text


def _sha256_text(value: object, *, label: str) -> str:
    text = _text(value, label=label)
    if _TEXT_SHA256_RE.fullmatch(text) is None:
        raise ServiceKinematicsError(f"{label} must be lowercase SHA-256")
    return text


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return sha1(header + data).hexdigest()


def _digest(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceBinding:
    source_main_sha: str = SOURCE_MAIN_SHA
    authority_revision: str = AUTHORITY_REVISION
    world_frame_id: str = WORLD_FRAME_ID
    released_source_blobs: tuple[tuple[str, str], ...] = RELEASED_SOURCE_BLOBS

    def validate(self, *, repo_root: Path = _REPO_ROOT) -> None:
        _sha1(self.source_main_sha, label="source main SHA")
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise ServiceKinematicsError("service kinematics is stale for released main")
        if self.authority_revision != AUTHORITY_REVISION:
            raise ServiceKinematicsError("service kinematics authority revision changed")
        if self.world_frame_id != WORLD_FRAME_ID:
            raise ServiceKinematicsError("service kinematics must use the authority world frame")
        if self.released_source_blobs != RELEASED_SOURCE_BLOBS:
            raise ServiceKinematicsError("released service source set changed")
        for relative, expected in self.released_source_blobs:
            _sha1(expected, label=f"source blob {relative}")
            path = repo_root / relative
            if not path.is_file():
                raise ServiceKinematicsError(f"released source missing: {relative}")
            actual = _git_blob_sha(path)
            if actual != expected:
                raise ServiceKinematicsError(
                    f"released source changed without service-kinematics rebind: {relative}"
                )

    def manifest(self) -> dict[str, object]:
        return {
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "world_frame_id": self.world_frame_id,
            "released_source_blobs": [list(item) for item in self.released_source_blobs],
        }


@dataclass(frozen=True, slots=True)
class CandidateSource:
    source_id: str
    domains: tuple[ServiceDomain, ...]
    pr_number: int
    head_sha: str
    source_path: str
    source_blob_sha: str
    source_class: CandidateClass
    geometry_consumed: bool
    note: str

    def __post_init__(self) -> None:
        _text(self.source_id, label="candidate source ID")
        if type(self.domains) is not tuple or not self.domains or any(type(item) is not ServiceDomain for item in self.domains):
            raise ServiceKinematicsError("candidate domains must be a nonempty exact ServiceDomain tuple")
        if type(self.pr_number) is not int or self.pr_number <= 0:
            raise ServiceKinematicsError("candidate PR number must be a positive integer")
        _sha1(self.head_sha, label="candidate head SHA")
        _text(self.source_path, label="candidate source path")
        _sha1(self.source_blob_sha, label="candidate source blob")
        if type(self.source_class) is not CandidateClass:
            raise ServiceKinematicsError("candidate source class must use controlled vocabulary")
        if type(self.geometry_consumed) is not bool or self.geometry_consumed:
            raise ServiceKinematicsError("unmerged/legacy candidate geometry cannot be consumed")
        _text(self.note, label="candidate note")

    def manifest(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "domains": [item.value for item in self.domains],
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "source_path": self.source_path,
            "source_blob_sha": self.source_blob_sha,
            "source_class": self.source_class.value,
            "geometry_consumed": False,
            "note": self.note,
        }


CANDIDATE_SOURCES = (
    CandidateSource(
        "CELL3_RIGHT_RELEASE_PR71",
        (ServiceDomain.EMERGENCY_RELEASE,),
        71,
        "0b5a619c6cea344038b0e8b8cc10a50e3d193390",
        "src/masck_one/right_quick_release_sweep.py",
        "d9be83d27deef9afd7e98dcbb874ebed1d1ab360",
        CandidateClass.NONAUTHORITATIVE_CANDIDATE,
        False,
        "Exact 0..7.3 mm slider sweep exists only on the unmerged Cell 3 candidate; full-head removal remains unresolved.",
    ),
    CandidateSource(
        "CELL3_OCCIPITAL_PR83",
        (ServiceDomain.RETENTION_ADJUSTMENT,),
        83,
        "8047fda9b835b00add1277868228ad6109779092",
        "src/masck_one/occipital_stabilizer.py",
        "1139b675c4758d8580cf5a18fa7a0b87b2d6ef99",
        CandidateClass.STACKED_NONAUTHORITATIVE_CANDIDATE,
        False,
        "Lateral occipital geometry is candidate-only and lacks the released frame-side positive-capture counterpart.",
    ),
    CandidateSource(
        "CELL3_RETENTION_FIT_PR87",
        (ServiceDomain.RETENTION_ADJUSTMENT,),
        87,
        "bf7a199838986f00a84ad48be8c7b3a11401743c",
        "src/masck_one/retention_fit_adjustment.py",
        "4d4583d3df7c86151fd7761fbc05e6f93328d338",
        CandidateClass.STACKED_NONAUTHORITATIVE_CANDIDATE,
        False,
        "Mask-removed unpowered indexed adjustment motion is not released-main geometry.",
    ),
    CandidateSource(
        "CELL3_HAIR_PINCH_PR89",
        (ServiceDomain.EMERGENCY_RELEASE, ServiceDomain.RETENTION_ADJUSTMENT, ServiceDomain.SERVICE_COVER),
        89,
        "c900c42ac5f45ad0516b58e408454eb3295d172d",
        "src/masck_one/hair_pinch_keepouts.py",
        "04ba87a6f8c6dbd103dae0f19869446b064e2057",
        CandidateClass.STACKED_NONAUTHORITATIVE_CANDIDATE,
        False,
        "Hazard/access volumes are candidate reference geometry with physical_guard_realized=false.",
    ),
    CandidateSource(
        "CELL4_WATER_REALIZATION_PR75",
        (ServiceDomain.WATER_REFILL,),
        75,
        "08b5769753858cb457f0117bf25498875072d812",
        "src/masck_one/realized_water_reservoir.py",
        "96c311beb58ff5ddb1af4fbd28a46ffe9adeda37",
        CandidateClass.STACKED_NONAUTHORITATIVE_CANDIDATE,
        False,
        "A 14 mm posterior module-withdrawal reservation exists only on the stale/unmerged water realization.",
    ),
    CandidateSource(
        "CELL4_WATER_CLOSURE_PR78",
        (ServiceDomain.WATER_REFILL,),
        78,
        "d309573ece2ccc2bd3302f0ccda779f2f4324eb5",
        "src/masck_one/water_reservoir_closure.py",
        "4f64d9f28f09c57545d8f3c4f5df821b558ff6cd",
        CandidateClass.STACKED_NONAUTHORITATIVE_CANDIDATE,
        False,
        "Lid/key service sequence is candidate-only and explicitly not wet-hand or physical service validation.",
    ),
    CandidateSource(
        "CELL4_CLEANSER_SERVICE_PR80",
        (ServiceDomain.CLEANSER_REFILL,),
        80,
        "6e3e05812406620072b37f54827b8345ed55ccea",
        "src/masck_one/cleanser_service_envelope.py",
        "1944487af9baa1c9fe27004eceed52eeb8a08167",
        CandidateClass.NONAUTHORITATIVE_CANDIDATE,
        False,
        "Complete attached cleanser-module withdrawal envelope is unmerged candidate geometry.",
    ),
    CandidateSource(
        "LEGACY_MANUAL_A_PR63",
        (ServiceDomain.WASTE_CARTRIDGE, ServiceDomain.BATTERY_DOOR, ServiceDomain.SERVICE_COVER),
        63,
        "23b942bbb7f335eac74b42fa1b1613900e5a9347",
        "src/masck_one/mechanical_assembly_kinematics.py",
        "c7d25510469db4530d0e8763601fb0ac11f34422",
        CandidateClass.LEGACY_DONOR_ONLY,
        False,
        "Legacy Manual A service/assembly kinematics are source material only and are not current authority.",
    ),
    CandidateSource(
        "LEGACY_MANUAL_B_PR64",
        (ServiceDomain.BATTERY_DOOR, ServiceDomain.SERVICE_COVER),
        64,
        "49a32d0c61bd1057ee707ee2ef20b8ff4e6ede01",
        "src/masck_one/electronics_package.py",
        "59e69a781e4ffcbb581a9f2835c9cb581b3939f2",
        CandidateClass.LEGACY_DONOR_ONLY,
        False,
        "Legacy dry-bay/door packaging is mechanically stale and cannot define current battery or cover motion.",
    ),
)


@dataclass(frozen=True, slots=True)
class ServiceMotionRecord:
    motion_id: str
    domain: ServiceDomain
    source_interface_id: str
    motion_kind: str
    released_contract_path: str | None
    released_contract_available: bool
    current_main_motion_geometry_available: bool
    current_main_maturity: str
    routine_service: bool
    required_conditions: tuple[str, ...]
    candidate_source_ids: tuple[str, ...]
    blocker: str
    evidence_status: str = DIGITAL_ONLY

    def __post_init__(self) -> None:
        _text(self.motion_id, label="motion ID")
        if type(self.domain) is not ServiceDomain:
            raise ServiceKinematicsError("motion domain must use ServiceDomain")
        _text(self.source_interface_id, label="motion interface ID")
        _text(self.motion_kind, label="motion kind")
        if self.released_contract_path is not None:
            _text(self.released_contract_path, label="released contract path")
        for name in ("released_contract_available", "current_main_motion_geometry_available", "routine_service"):
            if type(getattr(self, name)) is not bool:
                raise ServiceKinematicsError(f"{name} must be exact bool")
        # V1 is bound to a main where no objective-domain motion B-rep is released.
        if self.current_main_motion_geometry_available:
            raise ServiceKinematicsError("V1 cannot silently promote a current-main service motion B-rep")
        _text(self.current_main_maturity, label="current-main maturity")
        if type(self.required_conditions) is not tuple or not self.required_conditions:
            raise ServiceKinematicsError("service motion requires an immutable condition set")
        for item in self.required_conditions:
            _text(item, label="service condition")
        if type(self.candidate_source_ids) is not tuple:
            raise ServiceKinematicsError("candidate source IDs must be an exact tuple")
        _text(self.blocker, label="motion blocker")
        if self.evidence_status != DIGITAL_ONLY:
            raise ServiceKinematicsError("service motion evidence firewall changed")

    def manifest(self) -> dict[str, object]:
        return {
            "motion_id": self.motion_id,
            "domain": self.domain.value,
            "source_interface_id": self.source_interface_id,
            "motion_kind": self.motion_kind,
            "released_contract_path": self.released_contract_path,
            "released_contract_available": self.released_contract_available,
            "current_main_motion_geometry_available": False,
            "current_main_maturity": self.current_main_maturity,
            "routine_service": self.routine_service,
            "required_conditions": list(self.required_conditions),
            "candidate_source_ids": list(self.candidate_source_ids),
            "blocker": self.blocker,
            "evidence_status": self.evidence_status,
        }


ROUTINE_CONDITIONS = (
    "DEVICE_REMOVED_FROM_WEARER_CELL1_V1_CONSERVATIVE_POLICY",
    "UNPOWERED",
    "NO_ACTIVE_CYCLE",
    "RETENTION_DISENGAGED",
    "ONE_ACTIVE_SERVICE_DOMAIN_AT_A_TIME",
)

MOTIONS = (
    ServiceMotionRecord(
        "SERVICE-MOTION-EMERGENCY-RELEASE",
        ServiceDomain.EMERGENCY_RELEASE,
        "SAFETY-QUICK-RELEASE",
        "MECHANICAL_RELEASE",
        "src/masck_one/mechanism_state.py",
        True,
        False,
        "RELEASED_STATE_SEMANTICS_ONLY_EXACT_MOTION_BREP_NOT_ON_MAIN",
        False,
        (
            "NO_ACTIVE_CYCLE_FOR_DIGITAL_STATE_TRANSITION",
            "MECHANICAL_PATH_MUST_WORK_UNPOWERED",
            "ONE_HAND_WET_REQUIREMENT_REMAINS_PHYSICAL_VALIDATION_GATED",
        ),
        ("CELL3_RIGHT_RELEASE_PR71", "CELL3_HAIR_PINCH_PR89"),
        "Exact current-main release motion and whole-head post-release removal geometry are not released.",
    ),
    ServiceMotionRecord(
        "SERVICE-MOTION-RETENTION-ADJUSTMENT",
        ServiceDomain.RETENTION_ADJUSTMENT,
        "RETENTION-SERVICE-ADJUSTMENT",
        "INDEXED_RETENTION_ADJUSTMENT",
        None,
        False,
        False,
        "NO_RELEASED_RETENTION_ADJUSTMENT_MOTION_PRODUCER",
        True,
        ROUTINE_CONDITIONS,
        ("CELL3_OCCIPITAL_PR83", "CELL3_RETENTION_FIT_PR87", "CELL3_HAIR_PINCH_PR89"),
        "Current main has structural retention reservations but no released adjustment B-rep or frame-side positive capture.",
    ),
    ServiceMotionRecord(
        "SERVICE-MOTION-WATER-REFILL",
        ServiceDomain.WATER_REFILL,
        WATER_PORT_FILL,
        "REMOVE_MODULE_THEN_REFILL_CLOSURE_SERVICE",
        "src/masck_one/water_reservoir.py",
        True,
        False,
        "RELEASED_WATER_SERVICE_ARCHITECTURE_PORT_GEOMETRY_AND_MOTION_UNRESOLVED",
        True,
        ROUTINE_CONDITIONS,
        ("CELL4_WATER_REALIZATION_PR75", "CELL4_WATER_CLOSURE_PR78"),
        "Released main defines removable/refillable intent but not module withdrawal, closure, seal or refill service motion geometry.",
    ),
    ServiceMotionRecord(
        "SERVICE-MOTION-CLEANSER-REFILL",
        ServiceDomain.CLEANSER_REFILL,
        CLEANSER_PORT_REFILL,
        "REMOVE_MODULE_THEN_REFILL_PURGE_CLOSURE_SERVICE",
        "src/masck_one/cleanser_storage.py",
        True,
        False,
        "RELEASED_CLEANSER_SERVICE_ARCHITECTURE_PORT_GEOMETRY_AND_MOTION_UNRESOLVED",
        True,
        ROUTINE_CONDITIONS,
        ("CELL4_CLEANSER_SERVICE_PR80",),
        "Released main defines refill/purge service intent but not current-main closure or module-removal B-rep.",
    ),
    ServiceMotionRecord(
        "SERVICE-MOTION-WASTE-CARTRIDGE",
        ServiceDomain.WASTE_CARTRIDGE,
        WASTE_CARTRIDGE_SERVICE_INTERFACE,
        "CARTRIDGE_INSERTION_REMOVAL",
        "src/masck_one/waste_cartridge.py",
        True,
        False,
        "RELEASED_SERVICE_INTERFACE_TRAJECTORY_AND_CLEARANCE_EXPLICITLY_UNRESOLVED",
        True,
        ROUTINE_CONDITIONS,
        ("LEGACY_MANUAL_A_PR63",),
        "Current waste-cartridge source requires insertion/removal trajectory and service clearance to remain None.",
    ),
    ServiceMotionRecord(
        "SERVICE-MOTION-BATTERY-DOOR",
        ServiceDomain.BATTERY_DOOR,
        "BATTERY-DRY-BAY-SERVICE-DOOR",
        "DOOR_OPEN_AND_BATTERY_EXTRACTION",
        None,
        False,
        False,
        "BATTERY_PACKAGING_BENCHMARK_ONLY_NO_RELEASED_DOOR_OR_EXTRACTION_MOTION",
        True,
        ROUTINE_CONDITIONS,
        ("LEGACY_MANUAL_A_PR63", "LEGACY_MANUAL_B_PR64"),
        "Current main contains only a battery packaging benchmark; dry-bay door, battery retention and extraction motion have no released producer.",
    ),
    ServiceMotionRecord(
        "SERVICE-MOTION-REAR-COVER",
        ServiceDomain.SERVICE_COVER,
        "REAR-SERVICE-COVER",
        "COVER_OPEN_REMOVE_REINSTALL",
        None,
        False,
        False,
        "NO_RELEASED_REAR_SERVICE_COVER_GEOMETRY_OR_MOTION",
        True,
        ROUTINE_CONDITIONS,
        ("CELL3_HAIR_PINCH_PR89", "LEGACY_MANUAL_A_PR63", "LEGACY_MANUAL_B_PR64"),
        "No current-main cover B-rep, hinge/fastener architecture, opening sweep or tool/access path exists.",
    ),
)


@dataclass(frozen=True, slots=True)
class WholeProductServiceState:
    mechanism: MechanismState
    device_removed: bool
    powered: bool
    active_domain: ServiceDomain | None = None

    def __post_init__(self) -> None:
        if type(self.mechanism) is not MechanismState:
            raise ServiceKinematicsError("service state mechanism must use exact MechanismState")
        if type(self.device_removed) is not bool or type(self.powered) is not bool:
            raise ServiceKinematicsError("device_removed and powered must be exact booleans")
        if self.active_domain is not None and type(self.active_domain) is not ServiceDomain:
            raise ServiceKinematicsError("active service domain must use ServiceDomain")
        if self.mechanism.cycle_active and not self.powered:
            raise ServiceKinematicsError("active cycle cannot coexist with unpowered service context")
        if self.mechanism.cycle_active and self.device_removed:
            raise ServiceKinematicsError("active cycle cannot coexist with removed-device service context")
        if self.mechanism.mode is OperatingMode.SERVICE:
            if not self.device_removed or self.powered:
                raise ServiceKinematicsError("Cell 1 V1 routine SERVICE mode requires removed, unpowered device")
            if self.mechanism.retention_engaged or self.mechanism.quick_release_open:
                raise ServiceKinematicsError("routine SERVICE mode requires neutral disengaged retention state")
        if self.mechanism.service_access_open and self.mechanism.mode is not OperatingMode.SERVICE:
            raise ServiceKinematicsError("service access must remain inside SERVICE mode")
        if self.active_domain is not None:
            if self.active_domain is ServiceDomain.EMERGENCY_RELEASE:
                raise ServiceKinematicsError("emergency release is not a routine active service domain")
            if not self.mechanism.service_access_open:
                raise ServiceKinematicsError("selected routine service domain requires open service session")

    @property
    def state_sha256(self) -> str:
        return _digest(self.manifest(include_sha=False))

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "device_removed": self.device_removed,
            "powered": self.powered,
            "active_domain": self.active_domain.value if self.active_domain is not None else None,
            "mechanism": {
                "mode": self.mechanism.mode.value,
                "cycle_active": self.mechanism.cycle_active,
                "retention_engaged": self.mechanism.retention_engaged,
                "quick_release_open": self.mechanism.quick_release_open,
                "service_access_open": self.mechanism.service_access_open,
                "fault_latched": self.mechanism.fault_latched,
                "mechanism_provenance_sha256": self.mechanism.mechanism_provenance_sha256,
                "mechanism_state_sha256": self.mechanism.provenance_sha256,
            },
            "evidence_status": "SIMULATED_WHOLE_PRODUCT_SERVICE_STATE_ONLY",
        }
        if include_sha:
            payload["state_sha256"] = self.state_sha256
        return payload


@dataclass(frozen=True, slots=True)
class WholeProductServiceKinematics:
    binding: SourceBinding
    candidates: tuple[CandidateSource, ...]
    motions: tuple[ServiceMotionRecord, ...]
    physical_validation_eligible: bool = False
    evidence_status: str = DIGITAL_ONLY

    def validate_current_sources(self, *, repo_root: Path = _REPO_ROOT) -> None:
        self.binding.validate(repo_root=repo_root)
        if self.candidates != CANDIDATE_SOURCES:
            raise ServiceKinematicsError("candidate service-source snapshot changed")
        if self.motions != MOTIONS:
            raise ServiceKinematicsError("service motion registry changed")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise ServiceKinematicsError("service kinematics cannot become physical validation evidence")
        if self.evidence_status != DIGITAL_ONLY:
            raise ServiceKinematicsError("service kinematics evidence firewall changed")

        candidate_ids = tuple(item.source_id for item in self.candidates)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ServiceKinematicsError("candidate service source IDs cannot repeat")
        motion_ids = tuple(item.motion_id for item in self.motions)
        if len(motion_ids) != len(set(motion_ids)):
            raise ServiceKinematicsError("service motion IDs cannot repeat")
        domains = tuple(item.domain for item in self.motions)
        if domains != tuple(ServiceDomain):
            raise ServiceKinematicsError("service registry must cover every controlled domain exactly once")
        known_candidates = set(candidate_ids)
        for motion in self.motions:
            for source_id in motion.candidate_source_ids:
                if source_id not in known_candidates:
                    raise ServiceKinematicsError(f"unknown candidate source binding {source_id}")

        authority = load_authority()
        if type(authority) is not Authority:
            raise ServiceKinematicsError("authority loader returned unexpected type")
        if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
            raise ServiceKinematicsError("live authority revision moved")
        coordinate_status = str(authority.get("coordinate_system", "status"))
        if coordinate_status != "FROZEN_DATUM":
            raise ServiceKinematicsError("canonical coordinate datum is no longer frozen")

        quick = authority.get("safety", "quick_release")
        if type(quick) is not dict or quick.get("one_hand_wet_unpowered") is not True:
            raise ServiceKinematicsError("one-hand wet unpowered quick-release requirement changed")
        if str(quick.get("time_status")) != "FROZEN_SAFETY_REQUIREMENT":
            raise ServiceKinematicsError("quick-release timing requirement status changed")

        water = build_water_reservoir_architecture(authority)
        water_fill = next(port for port in water.ports if port.port_id == WATER_PORT_FILL)
        if "UNRESOLVED" not in water_fill.geometry_status:
            raise ServiceKinematicsError("water fill geometry matured and service integration requires rebind")

        cleanser = build_cleanser_storage_architecture(authority)
        cleanser_fill = next(port for port in cleanser.ports if port.port_id == CLEANSER_PORT_REFILL)
        if "UNRESOLVED" not in cleanser_fill.geometry_status:
            raise ServiceKinematicsError("cleanser refill geometry matured and service integration requires rebind")

        if "UNRESOLVED" not in WASTE_CARTRIDGE_SERVICE_STATUS:
            raise ServiceKinematicsError("waste-cartridge service trajectory matured and requires rebind")
        battery_status = str(authority.get("battery_reference", "status"))
        if battery_status != "PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE":
            raise ServiceKinematicsError("battery reference maturity changed")

        for relative in EXPECTED_ABSENT_CURRENT_MAIN_PATHS:
            if (repo_root / relative).exists():
                raise ServiceKinematicsError(
                    f"service producer now exists on this worktree and V1 must be rebound: {relative}"
                )

    @property
    def kinematics_sha256(self) -> str:
        return _digest(self._manifest_payload())

    @property
    def blocked_motion_count(self) -> int:
        return sum(not item.current_main_motion_geometry_available for item in self.motions)

    def _manifest_payload(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "binding": self.binding.manifest(),
            "routine_service_policy": {
                "conditions": list(ROUTINE_CONDITIONS),
                "semantics": "CELL1_V1_CONSERVATIVE_DIGITAL_INTEGRATION_POLICY_NOT_PHYSICAL_HUMAN_FACTORS_VALIDATION",
                "simultaneous_active_domains_max": 1,
            },
            "authority_quick_release_boundary": {
                "time_max_s": 2.0,
                "time_status": "FROZEN_SAFETY_REQUIREMENT",
                "force_target_N": [5.0, 12.0],
                "force_status": "VALIDATION_GATED",
                "one_hand_wet_unpowered": True,
                "one_hand_wet_unpowered_status": "FROZEN_SAFETY_REQUIREMENT",
            },
            "motions": [item.manifest() for item in self.motions],
            "candidate_sources": [item.manifest() for item in self.candidates],
            "current_main_motion_geometry_available_count": sum(
                item.current_main_motion_geometry_available for item in self.motions
            ),
            "blocked_motion_count": self.blocked_motion_count,
            "physical_validation_eligible": False,
            "evidence_status": self.evidence_status,
        }

    def manifest(self) -> dict[str, object]:
        self.validate_current_sources()
        payload = self._manifest_payload()
        payload["kinematics_sha256"] = self.kinematics_sha256
        return payload

    def motion_for(self, domain: ServiceDomain) -> ServiceMotionRecord:
        if type(domain) is not ServiceDomain:
            raise ServiceKinematicsError("service domain must use controlled enum")
        return next(item for item in self.motions if item.domain is domain)

    def removed_idle_state(self) -> WholeProductServiceState:
        mechanism = MechanismState(
            mode=OperatingMode.IDLE,
            cycle_active=False,
            retention_engaged=False,
            quick_release_open=False,
            service_access_open=False,
            fault_latched=False,
            mechanism_provenance_sha256=self.kinematics_sha256,
        )
        return WholeProductServiceState(mechanism, device_removed=True, powered=False)

    def open_service_session(self, before: WholeProductServiceState) -> WholeProductServiceState:
        expected = self.removed_idle_state()
        if before.manifest(include_sha=False) != expected.manifest(include_sha=False):
            raise ServiceKinematicsError("routine service may start only from exact removed, unpowered idle state")
        intermediate = MechanismState(
            OperatingMode.SERVICE, False, False, False, False, False, self.kinematics_sha256
        )
        validate_transition(
            before.mechanism,
            intermediate,
            TransitionAction.ENTER_SERVICE,
            current_mechanism_provenance_sha256=self.kinematics_sha256,
        )
        opened = MechanismState(
            OperatingMode.SERVICE, False, False, False, True, False, self.kinematics_sha256
        )
        validate_transition(
            intermediate,
            opened,
            TransitionAction.OPEN_SERVICE,
            current_mechanism_provenance_sha256=self.kinematics_sha256,
        )
        return WholeProductServiceState(opened, device_removed=True, powered=False)

    def select_domain(
        self,
        state: WholeProductServiceState,
        domain: ServiceDomain,
    ) -> WholeProductServiceState:
        if type(state) is not WholeProductServiceState:
            raise ServiceKinematicsError("service selection requires WholeProductServiceState")
        if type(domain) is not ServiceDomain or domain is ServiceDomain.EMERGENCY_RELEASE:
            raise ServiceKinematicsError("emergency release is not selected through routine service")
        if state.active_domain is not None:
            raise ServiceKinematicsError("only one routine service domain may be active")
        if state.mechanism.mode is not OperatingMode.SERVICE or not state.mechanism.service_access_open:
            raise ServiceKinematicsError("routine domain selection requires open service session")
        return WholeProductServiceState(
            state.mechanism,
            device_removed=state.device_removed,
            powered=state.powered,
            active_domain=domain,
        )

    def execute_selected_motion(self, state: WholeProductServiceState) -> None:
        if type(state) is not WholeProductServiceState or state.active_domain is None:
            raise ServiceKinematicsError("motion execution requires one selected service domain")
        motion = self.motion_for(state.active_domain)
        if not motion.current_main_motion_geometry_available:
            raise ServiceKinematicsError(
                f"{motion.domain.value} motion is blocked: no released current-main motion geometry"
            )
        raise ServiceKinematicsError("unreachable V1 motion execution state")

    def clear_domain(self, state: WholeProductServiceState) -> WholeProductServiceState:
        if type(state) is not WholeProductServiceState or state.active_domain is None:
            raise ServiceKinematicsError("clear_domain requires a selected routine service domain")
        return WholeProductServiceState(
            state.mechanism,
            device_removed=state.device_removed,
            powered=state.powered,
            active_domain=None,
        )

    def close_service_session(self, before: WholeProductServiceState) -> WholeProductServiceState:
        if type(before) is not WholeProductServiceState:
            raise ServiceKinematicsError("service close requires WholeProductServiceState")
        if before.active_domain is not None:
            raise ServiceKinematicsError("active service domain must be cleared before closing session")
        if before.mechanism.mode is not OperatingMode.SERVICE or not before.mechanism.service_access_open:
            raise ServiceKinematicsError("service close requires open service session")
        closed_access = MechanismState(
            OperatingMode.SERVICE, False, False, False, False, False, self.kinematics_sha256
        )
        validate_transition(
            before.mechanism,
            closed_access,
            TransitionAction.CLOSE_SERVICE,
            current_mechanism_provenance_sha256=self.kinematics_sha256,
        )
        idle = MechanismState(
            OperatingMode.IDLE, False, False, False, False, False, self.kinematics_sha256
        )
        validate_transition(
            closed_access,
            idle,
            TransitionAction.EXIT_SERVICE,
            current_mechanism_provenance_sha256=self.kinematics_sha256,
        )
        return WholeProductServiceState(idle, device_removed=True, powered=False)

    def worn_retained_unpowered_idle_state(self) -> WholeProductServiceState:
        mechanism = MechanismState(
            OperatingMode.IDLE, False, True, False, False, False, self.kinematics_sha256
        )
        return WholeProductServiceState(mechanism, device_removed=False, powered=False)

    def emergency_release_reference_state(
        self,
        before: WholeProductServiceState,
    ) -> WholeProductServiceState:
        expected = self.worn_retained_unpowered_idle_state()
        if before.manifest(include_sha=False) != expected.manifest(include_sha=False):
            raise ServiceKinematicsError(
                "emergency-release reference transition is modeled only from worn, retained, unpowered idle state"
            )
        released = MechanismState(
            OperatingMode.IDLE, False, False, True, False, False, self.kinematics_sha256
        )
        validate_transition(
            before.mechanism,
            released,
            TransitionAction.RELEASE_RETENTION,
            current_mechanism_provenance_sha256=self.kinematics_sha256,
        )
        return WholeProductServiceState(released, device_removed=False, powered=False)


def build_whole_product_service_kinematics() -> WholeProductServiceKinematics:
    integration = WholeProductServiceKinematics(SourceBinding(), CANDIDATE_SOURCES, MOTIONS)
    integration.validate_current_sources()
    return integration


def export_service_kinematics_manifest(
    output_dir: str | Path,
    integration: WholeProductServiceKinematics | None = None,
) -> Path:
    integration = integration or build_whole_product_service_kinematics()
    integration.validate_current_sources()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    path = output / "whole_product_service_kinematics_v1.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(integration.manifest(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path
