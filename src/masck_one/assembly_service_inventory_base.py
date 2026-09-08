from __future__ import annotations

"""Cell 15 current part, assembly-stage, and service-motion inventory.

This module reconciles three intentionally different evidence layers without promoting
unmerged work into release authority:

* released ``main`` geometry/export semantics,
* the Cell 1 component-registry and Cell 5 DFM part-architecture donor contracts, and
* exact-head specialist candidates that may contain useful service-motion evidence.

The inventory is digital provenance and dependency control only. It does not establish
physical serviceability, fit, force, sealing, hygiene, electrical safety, durability,
supplier qualification, or production capability.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
from pathlib import Path
import re


SCHEMA = "MASCK_ONE_CELL15_ASSEMBLY_SERVICE_INVENTORY_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

CELL1_COMPONENT_REGISTRY_PR = 74
CELL1_COMPONENT_REGISTRY_HEAD = "77bbe94e78f3f3b87fed7a1b5b44d7b5ac3e1adc"
CELL1_COMPONENT_REGISTRY_BLOB = "dd7306d9bd876b821e3887133e3e0c096b48ebcf"
CELL1_COMPONENT_REGISTRY_SOURCE_MAIN = "5fce2a43a34d8be49256677a35af60c906dc1653"

CELL5_DFM_PR = 77
CELL5_DFM_HEAD = "bcade5e50854617894ffee1eee2f3a3bfc1de3bb"
CELL5_DFM_BLOB = "9173205bafb2dad3052f093bc29022570880d60a"
CELL5_DFM_SOURCE_MAIN = "628ec5f5766937433b1bdf8f30edc372924cf41e"

CELL1_ASSEMBLY_BOUNDARY_PR = 101
CELL1_ASSEMBLY_BOUNDARY_HEAD = "468cc246ecc56e3e90673c55af68445f0b09ba9d"
CELL1_ASSEMBLY_BOUNDARY_BLOB = "55487cd7251621cc5062fa9914f1c4f28ddcf4f0"

SOURCE_GIT_BLOB_BY_PATH = {
    "config/masck_one_authority.yaml": AUTHORITY_BLOB_SHA,
    "src/masck_one/model.py": "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894",
    "src/masck_one/export.py": "9b650953a66b025c7b0393e8843bee81d287dd21",
    "src/masck_one/structural_frame.py": "bda5ba87d232c0e6a22e200975a80414a10c9a83",
    "src/masck_one/fresh_pump_packaging.py": "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4",
    "src/masck_one/waste_pump_architecture.py": "ace02ee529070465b11832f475771125636312cb",
    "src/masck_one/realized_waste_backbone.py": "6aa79d9a613e278f32da85b4654c0e35cc09b7ca",
    "src/masck_one/waste_cartridge.py": "9dc0fe8a0ed92083c68406da3993e57e767e2483",
    "src/masck_one/waste_cartridge_dfm.py": "f9788cce30c14600c8a624509153596e46c1e478",
}

ROLE_PHYSICAL_MATERIAL = "PHYSICAL_MATERIAL"
ROLE_DEVELOPMENT_REFERENCE = "DEVELOPMENT_REFERENCE"
ROLE_PACKAGE_REFERENCE = "PACKAGE_REFERENCE"
ROLE_PROTECTED_KEEPOUT = "PROTECTED_KEEPOUT"
INSTANCE_ROLES = (
    ROLE_PHYSICAL_MATERIAL,
    ROLE_DEVELOPMENT_REFERENCE,
    ROLE_PACKAGE_REFERENCE,
    ROLE_PROTECTED_KEEPOUT,
)

SERVICE_NONUSER_FIXED = "NONUSER_FIXED"
SERVICE_USER_REMOVABLE = "USER_REMOVABLE"
SERVICE_CONSUMABLE_REPLACEABLE = "CONSUMABLE_REPLACEABLE"
SERVICE_TECHNICIAN_REMOVABLE = "TECHNICIAN_REMOVABLE"
SERVICE_CLASSES = (
    SERVICE_NONUSER_FIXED,
    SERVICE_USER_REMOVABLE,
    SERVICE_CONSUMABLE_REPLACEABLE,
    SERVICE_TECHNICIAN_REMOVABLE,
)

PATH_NOT_APPLICABLE = "NOT_APPLICABLE"
PATH_REQUIRED = "DIGITAL_PATH_REQUIRED"
PATH_STATUSES = (PATH_NOT_APPLICABLE, PATH_REQUIRED)

M_RELEASED_GEOMETRY = "RELEASED_GEOMETRY"
M_RELEASED_ENVELOPE = "RELEASED_ENVELOPE"
M_RELEASED_TOPOLOGY = "RELEASED_TOPOLOGY"
M_DEVELOPMENT_REFERENCE = "DEVELOPMENT_REFERENCE"
M_UNRESOLVED_REQUIRED = "UNRESOLVED_REQUIRED"
DFM_MATURITIES = (
    M_RELEASED_GEOMETRY,
    M_RELEASED_ENVELOPE,
    M_RELEASED_TOPOLOGY,
    M_DEVELOPMENT_REFERENCE,
    M_UNRESOLVED_REQUIRED,
)

MOTION_MISSING_RELEASED_PRODUCER = "MISSING_RELEASED_MOTION_PRODUCER"
MOTION_CANDIDATE_EXACT = "CANDIDATE_EXACT_CONTINUOUS_SWEEP"
MOTION_CANDIDATE_CONSERVATIVE = "CANDIDATE_CONSERVATIVE_ENVELOPE"
MOTION_CANDIDATE_REFERENCE = "CANDIDATE_REFERENCE_MOTION_ONLY"
MOTION_CANDIDATE_STATIONARY = "CANDIDATE_STATIONARY_SERVICE_RESERVATION_ONLY"
MOTION_NO_CANDIDATE = "NO_CURRENT_MOTION_CANDIDATE"
CANDIDATE_MOTION_STATES = (
    MOTION_CANDIDATE_EXACT,
    MOTION_CANDIDATE_CONSERVATIVE,
    MOTION_CANDIDATE_REFERENCE,
    MOTION_CANDIDATE_STATIONARY,
    MOTION_NO_CANDIDATE,
)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_STATUS = (
    "DIGITAL_INVENTORY_ASSEMBLY_STAGE_AND_SERVICE_MOTION_PROVENANCE_ONLY_NOT_"
    "PHYSICAL_SERVICE_FIT_FORCE_SEAL_HYGIENE_SAFETY_DURABILITY_OR_PRODUCTION_EVIDENCE"
)


class AssemblyServiceInventoryError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def validate_released_source_bindings() -> None:
    """Fail closed when any source used for current-main conclusions has moved."""
    for relative_path, expected_sha in sorted(SOURCE_GIT_BLOB_BY_PATH.items()):
        if _SHA_RE.fullmatch(expected_sha) is None:
            raise AssemblyServiceInventoryError(f"malformed source blob for {relative_path}")
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise AssemblyServiceInventoryError(f"missing released source file {relative_path}")
        actual_sha = _git_blob_sha(path)
        if actual_sha != expected_sha:
            raise AssemblyServiceInventoryError(
                f"released source moved at {relative_path}; expected {expected_sha}, got {actual_sha}"
            )


@dataclass(frozen=True, slots=True)
class ReleasedModelInstance:
    instance_id: str
    source_name: str
    source_status: str
    semantic_role: str
    development_assembly_included: bool

    def __post_init__(self) -> None:
        for label, value in (
            ("instance_id", self.instance_id),
            ("source_name", self.source_name),
            ("source_status", self.source_status),
        ):
            if type(value) is not str or not value or value != value.strip():
                raise AssemblyServiceInventoryError(f"{label} must be exact nonblank text")
        if self.semantic_role not in INSTANCE_ROLES:
            raise AssemblyServiceInventoryError("uncontrolled released-model instance role")
        if type(self.development_assembly_included) is not bool:
            raise AssemblyServiceInventoryError("development assembly membership must be bool")

    def manifest(self) -> dict[str, object]:
        return {
            "instance_id": self.instance_id,
            "source_name": self.source_name,
            "source_status": self.source_status,
            "semantic_role": self.semantic_role,
            "development_assembly_included": self.development_assembly_included,
        }


@dataclass(frozen=True, slots=True)
class DfmDonorPart:
    part_id: str
    assembly_stage: int
    service_class: str
    service_path_status: str
    donor_maturity: str

    def __post_init__(self) -> None:
        if type(self.part_id) is not str or not self.part_id.startswith("MASCK_ONE-DFM-"):
            raise AssemblyServiceInventoryError("DFM donor part ID is malformed")
        if type(self.assembly_stage) is not int or isinstance(self.assembly_stage, bool) or self.assembly_stage < 0:
            raise AssemblyServiceInventoryError("assembly stage must be an exact nonnegative integer")
        if self.service_class not in SERVICE_CLASSES:
            raise AssemblyServiceInventoryError("uncontrolled service class")
        if self.service_path_status not in PATH_STATUSES:
            raise AssemblyServiceInventoryError("uncontrolled service path status")
        if self.donor_maturity not in DFM_MATURITIES:
            raise AssemblyServiceInventoryError("uncontrolled donor maturity")
        if self.service_class in (
            SERVICE_USER_REMOVABLE,
            SERVICE_CONSUMABLE_REPLACEABLE,
            SERVICE_TECHNICIAN_REMOVABLE,
        ) and self.service_path_status != PATH_REQUIRED:
            raise AssemblyServiceInventoryError("removable donor parts require an explicit service path")

    def manifest(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "assembly_stage": self.assembly_stage,
            "service_class": self.service_class,
            "service_path_status": self.service_path_status,
            "donor_maturity": self.donor_maturity,
        }


@dataclass(frozen=True, slots=True)
class CandidateBinding:
    pr_number: int
    head_sha: str
    evidence_kind: str
    source_path: str | None = None
    source_blob_sha: str | None = None

    def __post_init__(self) -> None:
        if type(self.pr_number) is not int or isinstance(self.pr_number, bool) or self.pr_number <= 0:
            raise AssemblyServiceInventoryError("candidate PR number must be an exact positive integer")
        if type(self.head_sha) is not str or _SHA_RE.fullmatch(self.head_sha) is None:
            raise AssemblyServiceInventoryError("candidate head must be canonical lowercase 40-hex")
        if type(self.evidence_kind) is not str or not self.evidence_kind:
            raise AssemblyServiceInventoryError("candidate evidence kind must be explicit")
        if (self.source_path is None) != (self.source_blob_sha is None):
            raise AssemblyServiceInventoryError("candidate source path/blob must be supplied together")
        if self.source_blob_sha is not None and _SHA_RE.fullmatch(self.source_blob_sha) is None:
            raise AssemblyServiceInventoryError("candidate source blob must be canonical lowercase 40-hex")

    def manifest(self) -> dict[str, object]:
        return {
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "authority_status": "UNMERGED_CANDIDATE_NOT_RELEASE_AUTHORITY",
            "evidence_kind": self.evidence_kind,
            "source_path": self.source_path,
            "source_blob_sha": self.source_blob_sha,
        }


@dataclass(frozen=True, slots=True)
class ServiceDomain:
    domain_id: str
    owner: str
    affected_part_ids: tuple[str, ...]
    released_motion_status: str
    candidate_motion_status: str
    blocker: str
    candidate: CandidateBinding | None = None

    def __post_init__(self) -> None:
        if type(self.domain_id) is not str or not self.domain_id.startswith("MASCK_ONE-SERVICE-"):
            raise AssemblyServiceInventoryError("service domain ID is malformed")
        if self.owner not in ("CELL_3", "CELL_4", "CELL_15_INTEGRATION"):
            raise AssemblyServiceInventoryError("uncontrolled service-domain owner")
        if type(self.affected_part_ids) is not tuple or not self.affected_part_ids:
            raise AssemblyServiceInventoryError("service domain requires affected part IDs")
        if len(self.affected_part_ids) != len(set(self.affected_part_ids)):
            raise AssemblyServiceInventoryError("service-domain part IDs cannot repeat")
        if self.released_motion_status != MOTION_MISSING_RELEASED_PRODUCER:
            raise AssemblyServiceInventoryError(
                "current released main has no accepted complete service-motion producer in these domains"
            )
        if self.candidate_motion_status not in CANDIDATE_MOTION_STATES:
            raise AssemblyServiceInventoryError("uncontrolled candidate motion state")
        if type(self.blocker) is not str or not self.blocker:
            raise AssemblyServiceInventoryError("service-domain blocker must be explicit")
        if self.candidate_motion_status == MOTION_NO_CANDIDATE and self.candidate is not None:
            raise AssemblyServiceInventoryError("no-candidate domain cannot carry candidate provenance")
        if self.candidate_motion_status != MOTION_NO_CANDIDATE and self.candidate is None:
            raise AssemblyServiceInventoryError("candidate motion state requires exact candidate provenance")

    def manifest(self) -> dict[str, object]:
        return {
            "domain_id": self.domain_id,
            "owner": self.owner,
            "affected_part_ids": list(self.affected_part_ids),
            "released_motion_status": self.released_motion_status,
            "candidate_motion_status": self.candidate_motion_status,
            "blocker": self.blocker,
            "candidate": None if self.candidate is None else self.candidate.manifest(),
        }


def _released_model_instances() -> tuple[ReleasedModelInstance, ...]:
    items = [
        ReleasedModelInstance(
            "MASCK_ONE-ASM-RIGID-SHELL",
            "rigid_shell",
            "CAD_BASELINE",
            ROLE_PHYSICAL_MATERIAL,
            True,
        ),
        ReleasedModelInstance(
            "MASCK_ONE-ASM-NASAL-LOBE-REFERENCE",
            "nasal_lobe_membrane_reference",
            "DEVELOPMENT_LOCAL_THICKNESS_REFERENCE",
            ROLE_DEVELOPMENT_REFERENCE,
            True,
        ),
    ]
    for index in range(1, 5):
        items.append(
            ReleasedModelInstance(
                f"MASCK_ONE-ASM-ACTUATOR-REFERENCE-{index:02d}",
                f"actuator_envelope_{index}",
                "ALPHA_PHYSICS_REFERENCE",
                ROLE_PACKAGE_REFERENCE,
                True,
            )
        )
    items.extend(
        [
            ReleasedModelInstance(
                "MASCK_ONE-ASM-WATER-REFERENCE",
                "water_reservoir_envelope",
                "ENGINEERING_BASELINE_ENVELOPE",
                ROLE_PACKAGE_REFERENCE,
                True,
            ),
            ReleasedModelInstance(
                "MASCK_ONE-ASM-WASTE-CARTRIDGE-REFERENCE",
                "waste_cartridge_envelope",
                "ENGINEERING_BASELINE_ENVELOPE",
                ROLE_PACKAGE_REFERENCE,
                False,
            ),
            ReleasedModelInstance(
                "MASCK_ONE-ASM-BATTERY-REFERENCE",
                "battery_reference_envelope",
                "PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE",
                ROLE_PACKAGE_REFERENCE,
                True,
            ),
        ]
    )
    for suffix, source_name in (
        ("EYE-LEFT", "visual_eye_left"),
        ("EYE-RIGHT", "visual_eye_right"),
        ("MOUTH", "visual_mouth"),
        ("NOSTRIL-LEFT", "visual_nostril_left"),
        ("NOSTRIL-RIGHT", "visual_nostril_right"),
    ):
        items.append(
            ReleasedModelInstance(
                f"MASCK_ONE-ASM-KEEPOUT-{suffix}",
                source_name,
                "REFERENCE_ONLY",
                ROLE_PROTECTED_KEEPOUT,
                False,
            )
        )
    return tuple(sorted(items, key=lambda item: item.instance_id))


def _dfm_donor_parts() -> tuple[DfmDonorPart, ...]:
    raw = (
        ("SHELL-PRIMARY", 10, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, M_RELEASED_GEOMETRY),
        ("FACIAL-INTERFACE-CARRIER", 70, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, M_RELEASED_TOPOLOGY),
        ("NASAL-LOBE-MEMBRANE", 72, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, M_DEVELOPMENT_REFERENCE),
        ("REAR-SERVICE-COVER", 95, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("REACTION-FRAME", 20, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, M_RELEASED_TOPOLOGY),
        ("RETENTION-HALO-LEFT", 80, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, M_UNRESOLVED_REQUIRED),
        ("RETENTION-HALO-RIGHT-TONGUE", 80, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, M_UNRESOLVED_REQUIRED),
        ("RETENTION-LEFT-PIVOT-PIN", 82, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, M_UNRESOLVED_REQUIRED),
        ("LATCH-SOCKET-GUIDE", 82, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, M_UNRESOLVED_REQUIRED),
        ("LATCH-SLIDER-GRIP", 84, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, M_UNRESOLVED_REQUIRED),
        ("LATCH-CAPTURE-PIN", 84, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, M_UNRESOLVED_REQUIRED),
        ("LATCH-GUIDE-CLOSURE", 86, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("ACTUATOR-CARRIER", 40, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("ACTUATOR-PACKAGE", 42, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_RELEASED_ENVELOPE),
        ("ACTUATOR-REACTION-SHOE", 44, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("WATER-RESERVOIR-BODY", 50, SERVICE_USER_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("WATER-RESERVOIR-LID-SEAL", 52, SERVICE_USER_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("WATER-PICKUP-CONNECTOR", 53, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("WATER-RESERVOIR-LID", 54, SERVICE_USER_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("WATER-LID-RETENTION-KEY", 55, SERVICE_USER_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("WATER-FILL-SEAL", 56, SERVICE_USER_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("WATER-VENT-BARRIER", 56, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("WATER-FILL-CLOSURE", 57, SERVICE_USER_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("CLEANSER-RESERVOIR-BODY", 50, SERVICE_USER_REMOVABLE, PATH_REQUIRED, M_RELEASED_TOPOLOGY),
        ("CLEANSER-RESERVOIR-SEAL", 52, SERVICE_USER_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("CLEANSER-RESERVOIR-CLOSURE", 54, SERVICE_USER_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("FRESH-MANIFOLD-BODY", 58, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_RELEASED_TOPOLOGY),
        ("FRESH-MANIFOLD-COVER-SEAL", 59, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("ROUTE-CARRIER-CLIP-SET", 59, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("FRESH-ROUTE-SET", 61, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_RELEASED_TOPOLOGY),
        ("WASTE-BACKBONE-ROUTE-SET", 62, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_RELEASED_TOPOLOGY),
        ("PASSIVE-BACKFLOW-BARRIER", 64, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_RELEASED_TOPOLOGY),
        ("WASTE-CARTRIDGE-CARRIER", 66, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, M_UNRESOLVED_REQUIRED),
        ("WASTE-CARTRIDGE-BODY", 68, SERVICE_CONSUMABLE_REPLACEABLE, PATH_REQUIRED, M_RELEASED_ENVELOPE),
        ("WASTE-CARTRIDGE-SEAL-KEY", 69, SERVICE_CONSUMABLE_REPLACEABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("WASTE-CARTRIDGE-CLOSURE", 70, SERVICE_CONSUMABLE_REPLACEABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("DRY-BAY-HOUSING", 30, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, M_UNRESOLVED_REQUIRED),
        ("BATTERY-CARRIER", 32, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("BATTERY-PACKAGE", 34, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_RELEASED_ENVELOPE),
        ("PCB-CARRIER", 36, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("PCB-ASSEMBLY", 38, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("HARNESS-SET", 46, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("WET-DRY-BULKHEAD", 48, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("HMI-CONTROL-MEMBRANE", 74, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, M_UNRESOLVED_REQUIRED),
        ("HMI-CONTROL-CAP-SET", 76, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("HMI-STATUS-WINDOW", 76, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
        ("DRY-BAY-COVER-SEAL", 92, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, M_UNRESOLVED_REQUIRED),
    )
    return tuple(
        sorted(
            (
                DfmDonorPart(
                    f"MASCK_ONE-DFM-{suffix}",
                    stage,
                    service_class,
                    path_status,
                    maturity,
                )
                for suffix, stage, service_class, path_status, maturity in raw
            ),
            key=lambda item: item.part_id,
        )
    )


def _service_domains() -> tuple[ServiceDomain, ...]:
    qr = CandidateBinding(
        71,
        "0b5a619c6cea344038b0e8b8cc10a50e3d193390",
        "EXACT_COMPLETE_0_TO_7P3_MM_RIGID_SLIDER_WITHDRAWAL_SWEEP",
        "src/masck_one/right_quick_release_sweep.py",
        "d9be83d27deef9afd7e98dcbb874ebed1d1ab360",
    )
    cleanser = CandidateBinding(
        80,
        "6e3e05812406620072b37f54827b8345ed55ccea",
        "CONSERVATIVE_COMPLETE_ATTACHED_MODULE_REMOVAL_ENVELOPE",
        "src/masck_one/cleanser_service_envelope.py",
        "1944487af9baa1c9fe27004eceed52eeb8a08167",
    )
    rear = CandidateBinding(
        70,
        "58b95bc369d3879607ac060a5725426019d65abc",
        "REAR_SERVICE_SKIN_WITH_REFERENCE_REMOVAL_TRANSLATION",
    )
    retention = CandidateBinding(
        92,
        "e332426526ec4ceb885ad9d35250a89d78b6066c",
        "RETENTION_LOAD_PATH_GEOMETRY_WITH_CARRIER_SEPARATION_STILL_OPEN",
    )
    water_pump = CandidateBinding(
        85,
        "668727ad2676a7d41f095878ff5d9110c8f7a44a",
        "STATIONARY_PUMP_SERVICE_CLEARANCE_RESERVATION_REPLACEMENT_TRAJECTORY_UNRESOLVED",
    )
    cleanser_pump = CandidateBinding(
        94,
        "1eb826fe859c6d5ee6dc0097aa58a67944bb530b",
        "STATIONARY_PUMP_SERVICE_CLEARANCE_RESERVATION_REPLACEMENT_TRAJECTORY_UNRESOLVED",
    )
    waste_pump = CandidateBinding(
        96,
        "2626a4f5c3b971b7caf5b384a44c262489ccf128",
        "STATIONARY_PUMP_SERVICE_CLEARANCE_RESERVATION_REPLACEMENT_TRAJECTORY_UNRESOLVED",
    )
    backflow = CandidateBinding(
        100,
        "f788284d4a4e9f30d0e35b1ceea6c716e74a5e16",
        "STATIONARY_BARRIER_SERVICE_CLEARANCE_RESERVATION_REPLACEMENT_TRAJECTORY_UNRESOLVED",
    )
    domains = (
        ServiceDomain(
            "MASCK_ONE-SERVICE-RIGHT-EMERGENCY-RELEASE",
            "CELL_3",
            (
                "MASCK_ONE-DFM-LATCH-SOCKET-GUIDE",
                "MASCK_ONE-DFM-LATCH-SLIDER-GRIP",
                "MASCK_ONE-DFM-LATCH-CAPTURE-PIN",
            ),
            MOTION_MISSING_RELEASED_PRODUCER,
            MOTION_CANDIDATE_EXACT,
            "PR71 is candidate-only and stale to current main; full-head removal is outside its exact slider sweep.",
            qr,
        ),
        ServiceDomain(
            "MASCK_ONE-SERVICE-WHOLE-HEAD-REMOVAL",
            "CELL_3",
            ("MASCK_ONE-DFM-RETENTION-HALO-LEFT", "MASCK_ONE-DFM-RETENTION-HALO-RIGHT-TONGUE"),
            MOTION_MISSING_RELEASED_PRODUCER,
            MOTION_CANDIDATE_REFERENCE,
            "Retention candidate keeps carrier separation and complete whole-head removal explicitly open.",
            retention,
        ),
        ServiceDomain(
            "MASCK_ONE-SERVICE-RETENTION-CARRIER-SEPARATION",
            "CELL_3",
            ("MASCK_ONE-DFM-RETENTION-LEFT-PIVOT-PIN", "MASCK_ONE-DFM-LATCH-GUIDE-CLOSURE"),
            MOTION_MISSING_RELEASED_PRODUCER,
            MOTION_CANDIDATE_REFERENCE,
            "Nonteleporting carrier separation and reassembly after pin withdrawal remains unresolved.",
            retention,
        ),
        ServiceDomain(
            "MASCK_ONE-SERVICE-ACTUATOR-REPLACEMENT",
            "CELL_3",
            (
                "MASCK_ONE-DFM-ACTUATOR-CARRIER",
                "MASCK_ONE-DFM-ACTUATOR-PACKAGE",
                "MASCK_ONE-DFM-ACTUATOR-REACTION-SHOE",
            ),
            MOTION_MISSING_RELEASED_PRODUCER,
            MOTION_NO_CANDIDATE,
            "Carrier, reaction-shoe, access and nonteleporting extraction geometry are not released.",
        ),
        ServiceDomain(
            "MASCK_ONE-SERVICE-WATER-RESERVOIR-REFILL-AND-REMOVAL",
            "CELL_4",
            (
                "MASCK_ONE-DFM-WATER-RESERVOIR-BODY",
                "MASCK_ONE-DFM-WATER-RESERVOIR-LID",
                "MASCK_ONE-DFM-WATER-LID-RETENTION-KEY",
                "MASCK_ONE-DFM-WATER-FILL-CLOSURE",
            ),
            MOTION_MISSING_RELEASED_PRODUCER,
            MOTION_NO_CANDIDATE,
            "Released main has only the water package envelope and topology; no accepted refill/removal sweep exists.",
        ),
        ServiceDomain(
            "MASCK_ONE-SERVICE-CLEANSER-REFILL-AND-MODULE-REMOVAL",
            "CELL_4",
            (
                "MASCK_ONE-DFM-CLEANSER-RESERVOIR-BODY",
                "MASCK_ONE-DFM-CLEANSER-RESERVOIR-CLOSURE",
            ),
            MOTION_MISSING_RELEASED_PRODUCER,
            MOTION_CANDIDATE_CONSERVATIVE,
            "PR80 carries a conservative complete-module envelope, but it is unmerged and not exact moving B-rep occupancy.",
            cleanser,
        ),
        ServiceDomain(
            "MASCK_ONE-SERVICE-WASTE-CARTRIDGE-REPLACEMENT",
            "CELL_4",
            (
                "MASCK_ONE-DFM-WASTE-CARTRIDGE-BODY",
                "MASCK_ONE-DFM-WASTE-CARTRIDGE-SEAL-KEY",
                "MASCK_ONE-DFM-WASTE-CARTRIDGE-CLOSURE",
            ),
            MOTION_MISSING_RELEASED_PRODUCER,
            MOTION_NO_CANDIDATE,
            "PR95 intentionally keeps the package proxy nonmaterial; receiver, key, seal and nonteleporting insertion/removal geometry remain open.",
        ),
        ServiceDomain(
            "MASCK_ONE-SERVICE-WATER-PUMP-REPLACEMENT",
            "CELL_4",
            ("MASCK_ONE-COMP-WATER-PUMP",),
            MOTION_MISSING_RELEASED_PRODUCER,
            MOTION_CANDIDATE_STATIONARY,
            "PR85 realizes a stationary reservation only and explicitly leaves complete replacement trajectory unresolved.",
            water_pump,
        ),
        ServiceDomain(
            "MASCK_ONE-SERVICE-CLEANSER-PUMP-REPLACEMENT",
            "CELL_4",
            ("MASCK_ONE-COMP-CLEANSER-PUMP",),
            MOTION_MISSING_RELEASED_PRODUCER,
            MOTION_CANDIDATE_STATIONARY,
            "PR94 realizes a stationary reservation only and explicitly leaves complete replacement trajectory unresolved.",
            cleanser_pump,
        ),
        ServiceDomain(
            "MASCK_ONE-SERVICE-WASTE-PUMP-REPLACEMENT",
            "CELL_4",
            ("MASCK_ONE-COMP-WASTE-PUMP",),
            MOTION_MISSING_RELEASED_PRODUCER,
            MOTION_CANDIDATE_STATIONARY,
            "PR96 realizes a stationary reservation only and explicitly leaves replacement trajectory unresolved.",
            waste_pump,
        ),
        ServiceDomain(
            "MASCK_ONE-SERVICE-PASSIVE-BACKFLOW-REPLACEMENT",
            "CELL_4",
            ("MASCK_ONE-DFM-PASSIVE-BACKFLOW-BARRIER",),
            MOTION_MISSING_RELEASED_PRODUCER,
            MOTION_CANDIDATE_STATIONARY,
            "PR100 realizes a stationary reservation only and explicitly leaves replacement trajectory unresolved.",
            backflow,
        ),
        ServiceDomain(
            "MASCK_ONE-SERVICE-REAR-COVER-ACCESS",
            "CELL_4",
            ("MASCK_ONE-DFM-REAR-SERVICE-COVER", "MASCK_ONE-DFM-DRY-BAY-COVER-SEAL"),
            MOTION_MISSING_RELEASED_PRODUCER,
            MOTION_CANDIDATE_REFERENCE,
            "PR70 has a review-only cover translation, while attachment, seal and nested dry-side access remain unresolved.",
            rear,
        ),
        ServiceDomain(
            "MASCK_ONE-SERVICE-BATTERY-EXTRACTION",
            "CELL_4",
            ("MASCK_ONE-DFM-BATTERY-CARRIER", "MASCK_ONE-DFM-BATTERY-PACKAGE"),
            MOTION_MISSING_RELEASED_PRODUCER,
            MOTION_NO_CANDIDATE,
            "Battery carrier, connector disengagement, swelling allowance and nonteleporting extraction remain unresolved.",
        ),
        ServiceDomain(
            "MASCK_ONE-SERVICE-PCB-HARNESS-BULKHEAD",
            "CELL_4",
            (
                "MASCK_ONE-DFM-PCB-CARRIER",
                "MASCK_ONE-DFM-PCB-ASSEMBLY",
                "MASCK_ONE-DFM-HARNESS-SET",
                "MASCK_ONE-DFM-WET-DRY-BULKHEAD",
            ),
            MOTION_MISSING_RELEASED_PRODUCER,
            MOTION_NO_CANDIDATE,
            "No released dry-bay, connector-disengagement, harness-release or tool-access motion exists.",
        ),
    )
    return tuple(sorted(domains, key=lambda item: item.domain_id))


@dataclass(frozen=True, slots=True)
class AssemblyServiceInventory:
    released_instances: tuple[ReleasedModelInstance, ...]
    dfm_donor_parts: tuple[DfmDonorPart, ...]
    service_domains: tuple[ServiceDomain, ...]
    physical_validation_eligible: bool = False
    evidence_status: str = EVIDENCE_STATUS

    def __post_init__(self) -> None:
        if type(self.released_instances) is not tuple or len(self.released_instances) != 14:
            raise AssemblyServiceInventoryError("released model inventory must contain exactly 14 source instances")
        if type(self.dfm_donor_parts) is not tuple or len(self.dfm_donor_parts) != 47:
            raise AssemblyServiceInventoryError("Cell 5 DFM donor inventory must contain exactly 47 part families")
        if type(self.service_domains) is not tuple or not self.service_domains:
            raise AssemblyServiceInventoryError("service inventory requires controlled service domains")
        for collection, label, key in (
            (self.released_instances, "released instance", lambda item: item.instance_id),
            (self.dfm_donor_parts, "DFM donor part", lambda item: item.part_id),
            (self.service_domains, "service domain", lambda item: item.domain_id),
        ):
            values = tuple(key(item) for item in collection)
            if len(values) != len(set(values)) or values != tuple(sorted(values)):
                raise AssemblyServiceInventoryError(f"{label} IDs must be unique and deterministically sorted")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise AssemblyServiceInventoryError("digital inventory cannot become physical validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise AssemblyServiceInventoryError("inventory evidence firewall changed")

        donor_ids = {item.part_id for item in self.dfm_donor_parts}
        expected_missing_pump_part_families = {
            "MASCK_ONE-COMP-WATER-PUMP",
            "MASCK_ONE-COMP-CLEANSER-PUMP",
            "MASCK_ONE-COMP-WASTE-PUMP",
        }
        if any(component_id.replace("-COMP-", "-DFM-") in donor_ids for component_id in expected_missing_pump_part_families):
            raise AssemblyServiceInventoryError("pump reconciliation assumption changed; rebind Cell 5 DFM donor")
        if any(domain.released_motion_status != MOTION_MISSING_RELEASED_PRODUCER for domain in self.service_domains):
            raise AssemblyServiceInventoryError("released service-motion status changed without Cell 15 rebind")

    @property
    def current_reference_instances_in_development_assembly(self) -> tuple[str, ...]:
        return tuple(
            item.instance_id
            for item in self.released_instances
            if item.development_assembly_included and item.semantic_role != ROLE_PHYSICAL_MATERIAL
        )

    @property
    def missing_released_motion_domain_ids(self) -> tuple[str, ...]:
        return tuple(
            item.domain_id
            for item in self.service_domains
            if item.released_motion_status == MOTION_MISSING_RELEASED_PRODUCER
        )

    @property
    def inventory_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        donor_ids = {item.part_id for item in self.dfm_donor_parts}
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": SOURCE_MAIN_SHA,
            "authority_revision": AUTHORITY_REVISION,
            "authority_blob_sha": AUTHORITY_BLOB_SHA,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "released_source_git_blobs": dict(sorted(SOURCE_GIT_BLOB_BY_PATH.items())),
            "released_model_instances": [item.manifest() for item in self.released_instances],
            "current_reference_instances_in_development_assembly": list(
                self.current_reference_instances_in_development_assembly
            ),
            "source_contracts": {
                "cell1_component_registry": {
                    "pr_number": CELL1_COMPONENT_REGISTRY_PR,
                    "head_sha": CELL1_COMPONENT_REGISTRY_HEAD,
                    "source_blob_sha": CELL1_COMPONENT_REGISTRY_BLOB,
                    "authored_against_main_sha": CELL1_COMPONENT_REGISTRY_SOURCE_MAIN,
                    "authority_status": "STALE_UNMERGED_DONOR_NOT_RELEASE_AUTHORITY",
                },
                "cell5_dfm_part_architecture": {
                    "pr_number": CELL5_DFM_PR,
                    "head_sha": CELL5_DFM_HEAD,
                    "source_blob_sha": CELL5_DFM_BLOB,
                    "authored_against_main_sha": CELL5_DFM_SOURCE_MAIN,
                    "authority_status": "STALE_UNMERGED_DONOR_NOT_RELEASE_AUTHORITY",
                },
                "cell1_current_main_assembly_boundary": {
                    "pr_number": CELL1_ASSEMBLY_BOUNDARY_PR,
                    "head_sha": CELL1_ASSEMBLY_BOUNDARY_HEAD,
                    "source_blob_sha": CELL1_ASSEMBLY_BOUNDARY_BLOB,
                    "authored_against_main_sha": SOURCE_MAIN_SHA,
                    "authority_status": "CURRENT_MAIN_BOUND_CANDIDATE_NOT_RELEASE_AUTHORITY",
                },
            },
            "dfm_donor_parts": [item.manifest() for item in self.dfm_donor_parts],
            "reconciliation_findings": {
                "cell5_dfm_missing_component_registry_pump_part_families": [
                    "MASCK_ONE-COMP-CLEANSER-PUMP",
                    "MASCK_ONE-COMP-WASTE-PUMP",
                    "MASCK_ONE-COMP-WATER-PUMP",
                ],
                "waste_cartridge_package_proxy_current_main_role": (
                    "STANDALONE_PACKAGE_REFERENCE_EXCLUDED_FROM_DEVELOPMENT_ASSEMBLY_MATERIAL_POST_PR95"
                ),
                "current_main_reference_partition_gap": {
                    "reference_instances_still_in_development_assembly": list(
                        self.current_reference_instances_in_development_assembly
                    ),
                    "candidate_fix_pr": CELL1_ASSEMBLY_BOUNDARY_PR,
                    "candidate_fix_head_sha": CELL1_ASSEMBLY_BOUNDARY_HEAD,
                },
                "dfm_donor_has_passive_backflow_part_family": (
                    "MASCK_ONE-DFM-PASSIVE-BACKFLOW-BARRIER" in donor_ids
                ),
            },
            "service_domains": [item.manifest() for item in self.service_domains],
            "missing_released_motion_domain_ids": list(self.missing_released_motion_domain_ids),
            "digital_mvp_service_ready": False,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["inventory_sha256"] = self.inventory_sha256
        return payload


def build_current_assembly_service_inventory(*, validate_sources: bool = True) -> AssemblyServiceInventory:
    if validate_sources:
        validate_released_source_bindings()
    inventory = AssemblyServiceInventory(
        _released_model_instances(),
        _dfm_donor_parts(),
        _service_domains(),
    )
    return inventory
