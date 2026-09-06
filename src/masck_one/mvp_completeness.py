from __future__ import annotations

"""Fail-closed Cell 20 MVP completeness and physical-gate manifest.

This module is release-control evidence only. It distinguishes released geometry,
released topology/reference data, active unmerged candidate observations, digital
blockers, and physical-evidence gates. Candidate observations never become release
truth and physical gates never become closed without controlled evidence.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import argparse
import json
from pathlib import Path
import re

from .authority import Authority, load_authority


SCHEMA = "MASCK_ONE_CELL20_MVP_COMPLETENESS_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
SOURCE_PACKAGE_TREE_SHA = "4c179c6d6007968e86acde34d64b6856f9745982"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
AUTHORITY_SCHEMA_BLOB_SHA = "58accbe48619058cb99ab51a0387cf01874c3717"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
CANDIDATE_SNAPSHOT_OBSERVED_AT_UTC = "2026-09-06T00:55:25Z"
EVIDENCE_STATUS = (
    "DIGITAL_MVP_COMPLETENESS_AND_BLOCKER_CLASSIFICATION_ONLY_NOT_FIT_COMFORT_LOAD_"
    "HYDRAULIC_ELECTRICAL_THERMAL_HYGIENE_RELIABILITY_OR_PHYSICAL_VALIDATION"
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_DIR = Path(__file__).resolve().parent
_SELF_NAME = Path(__file__).name
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_ALLOWED_EVIDENCE = frozenset(
    {
        "AUTHORITY_CONTRACT",
        "REALIZED_BREP",
        "REALIZED_CENTERLINE",
        "DIGITAL_TOPOLOGY",
        "REFERENCE_ENVELOPE",
        "DFM_GATE_ONLY",
        "ABSENT",
    }
)
_ALLOWED_DIGITAL_STATES = frozenset({"CLOSED", "PARTIAL", "BLOCKED"})
_GEOMETRY_CLOSING_EVIDENCE = frozenset({"REALIZED_BREP", "REALIZED_CENTERLINE"})


class MvpCompletenessError(ValueError):
    pass


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise MvpCompletenessError(f"{label} must be exact nonblank text")
    return value


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _released_package_tree_sha() -> str:
    """Reconstruct the Git tree for the released package, excluding this Cell 20 file."""
    entries: list[tuple[bytes, bytes]] = []
    for path in _PACKAGE_DIR.iterdir():
        if not path.is_file() or path.name == _SELF_NAME:
            continue
        name = path.name.encode("utf-8")
        blob = bytes.fromhex(_git_blob_sha(path))
        entries.append((name, b"100644 " + name + b"\0" + blob))
    entries.sort(key=lambda item: item[0])
    payload = b"".join(entry for _, entry in entries)
    return sha1(f"tree {len(payload)}\0".encode("ascii") + payload).hexdigest()


def _require_released_sources_current(authority: Authority) -> None:
    if type(authority) is not Authority:
        raise MvpCompletenessError("MVP completeness requires the exact Authority type")
    canonical = load_authority()
    if authority.data != canonical.data:
        raise MvpCompletenessError("supplied authority differs from released machine authority")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise MvpCompletenessError("authority revision moved and requires Cell 20 reclassification")

    authority_path = _REPO_ROOT / "config/masck_one_authority.yaml"
    schema_path = _REPO_ROOT / "schemas/masck_one_authority.schema.json"
    if _git_blob_sha(authority_path) != AUTHORITY_BLOB_SHA:
        raise MvpCompletenessError("machine authority blob moved and requires Cell 20 reclassification")
    if _git_blob_sha(schema_path) != AUTHORITY_SCHEMA_BLOB_SHA:
        raise MvpCompletenessError("authority schema blob moved and requires Cell 20 reclassification")

    actual_tree = _released_package_tree_sha()
    if actual_tree != SOURCE_PACKAGE_TREE_SHA:
        raise MvpCompletenessError(
            "released src/masck_one producer tree moved; "
            f"expected {SOURCE_PACKAGE_TREE_SHA}, got {actual_tree}; rebind the completeness matrix"
        )


@dataclass(frozen=True, slots=True)
class CandidateObservation:
    pr_number: int
    observed_head_sha: str
    role: str
    release_authoritative: bool = False
    review_evidence_eligible: bool = False
    requires_live_head_revalidation: bool = True

    def __post_init__(self) -> None:
        if type(self.pr_number) is not int or self.pr_number <= 0:
            raise MvpCompletenessError("candidate PR number must be an exact positive integer")
        if type(self.observed_head_sha) is not str or _SHA40.fullmatch(self.observed_head_sha) is None:
            raise MvpCompletenessError("candidate head must be exact lowercase Git SHA")
        _text(self.role, label="candidate role")
        if type(self.release_authoritative) is not bool or self.release_authoritative:
            raise MvpCompletenessError("unmerged candidate observation cannot be release authority")
        if type(self.review_evidence_eligible) is not bool or self.review_evidence_eligible:
            raise MvpCompletenessError("moving candidate snapshot cannot be promotion review evidence")
        if type(self.requires_live_head_revalidation) is not bool or not self.requires_live_head_revalidation:
            raise MvpCompletenessError("candidate head movement must require live revalidation")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "pr_number": self.pr_number,
            "observed_head_sha": self.observed_head_sha,
            "role": self.role,
            "release_authoritative": self.release_authoritative,
            "review_evidence_eligible": self.review_evidence_eligible,
            "requires_live_head_revalidation": self.requires_live_head_revalidation,
        }


@dataclass(frozen=True, slots=True)
class RequirementStatus:
    requirement_id: str
    category: str
    requirement: str
    geometry_required_for_closure: bool
    released_main_evidence: str
    digital_state: str
    owner_cells: tuple[int, ...]
    candidate_prs: tuple[int, ...]
    physical_gate_ids: tuple[str, ...]
    closure_required: str

    def __post_init__(self) -> None:
        for label, value in (
            ("requirement ID", self.requirement_id),
            ("category", self.category),
            ("requirement", self.requirement),
            ("closure requirement", self.closure_required),
        ):
            _text(value, label=label)
        if type(self.geometry_required_for_closure) is not bool:
            raise MvpCompletenessError("geometry-required flag must be an exact bool")
        if self.released_main_evidence not in _ALLOWED_EVIDENCE:
            raise MvpCompletenessError("requirement uses uncontrolled released-main evidence vocabulary")
        if self.digital_state not in _ALLOWED_DIGITAL_STATES:
            raise MvpCompletenessError("requirement uses uncontrolled digital-state vocabulary")
        if self.geometry_required_for_closure and self.digital_state == "CLOSED":
            if self.released_main_evidence not in _GEOMETRY_CLOSING_EVIDENCE:
                raise MvpCompletenessError("framework/reference evidence cannot close a geometry-required requirement")
        if type(self.owner_cells) is not tuple or not self.owner_cells:
            raise MvpCompletenessError("requirement must identify at least one owning cell")
        if any(type(item) is not int or not 1 <= item <= 20 for item in self.owner_cells):
            raise MvpCompletenessError("owner cells must be exact integers in 1..20")
        if tuple(sorted(set(self.owner_cells))) != self.owner_cells:
            raise MvpCompletenessError("owner cells must be unique and sorted")
        if type(self.candidate_prs) is not tuple:
            raise MvpCompletenessError("candidate PR list must be immutable")
        if any(type(item) is not int or item <= 0 for item in self.candidate_prs):
            raise MvpCompletenessError("candidate PR numbers must be exact positive integers")
        if tuple(sorted(set(self.candidate_prs))) != self.candidate_prs:
            raise MvpCompletenessError("candidate PR numbers must be unique and sorted")
        if type(self.physical_gate_ids) is not tuple:
            raise MvpCompletenessError("physical gate IDs must be immutable")
        if any(type(item) is not str or not item for item in self.physical_gate_ids):
            raise MvpCompletenessError("physical gate IDs must be exact nonblank text")
        if tuple(sorted(set(self.physical_gate_ids))) != self.physical_gate_ids:
            raise MvpCompletenessError("physical gate IDs must be unique and sorted")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "requirement_id": self.requirement_id,
            "category": self.category,
            "requirement": self.requirement,
            "geometry_required_for_closure": self.geometry_required_for_closure,
            "released_main_evidence": self.released_main_evidence,
            "digital_state": self.digital_state,
            "owner_cells": list(self.owner_cells),
            "candidate_prs": list(self.candidate_prs),
            "physical_gate_ids": list(self.physical_gate_ids),
            "closure_required": self.closure_required,
        }


@dataclass(frozen=True, slots=True)
class PhysicalGate:
    gate_id: str
    controlled_requirement: str
    authority_status: str
    evidence_required: str
    owner_cells: tuple[int, ...]
    closed: bool = False

    def __post_init__(self) -> None:
        for label, value in (
            ("physical gate ID", self.gate_id),
            ("controlled requirement", self.controlled_requirement),
            ("authority status", self.authority_status),
            ("physical evidence requirement", self.evidence_required),
        ):
            _text(value, label=label)
        if type(self.owner_cells) is not tuple or not self.owner_cells:
            raise MvpCompletenessError("physical gate must identify at least one owning cell")
        if any(type(item) is not int or not 1 <= item <= 20 for item in self.owner_cells):
            raise MvpCompletenessError("physical gate owner cells must be exact integers in 1..20")
        if tuple(sorted(set(self.owner_cells))) != self.owner_cells:
            raise MvpCompletenessError("physical gate owner cells must be unique and sorted")
        if type(self.closed) is not bool or self.closed:
            raise MvpCompletenessError("Cell 20 digital manifest cannot close a physical validation gate")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "gate_id": self.gate_id,
            "controlled_requirement": self.controlled_requirement,
            "authority_status": self.authority_status,
            "evidence_required": self.evidence_required,
            "owner_cells": list(self.owner_cells),
            "closed": self.closed,
        }


CANDIDATE_OBSERVATIONS: tuple[CandidateObservation, ...] = (
    CandidateObservation(70, "559f89953e6ac7667e79426daabcd54b88f43acb", "five-station exterior, authority eye roll and compact rear-service skin"),
    CandidateObservation(71, "0b5a619c6cea344038b0e8b8cc10a50e3d193390", "positive captive emergency quick-release source candidate"),
    CandidateObservation(77, "bcade5e50854617894ffee1eee2f3a3bfc1de3bb", "whole-product DFM maturity gate candidate"),
    CandidateObservation(80, "6e3e05812406620072b37f54827b8345ed55ccea", "cleanser storage and service candidate"),
    CandidateObservation(82, "a52dbf7fab09b0e82715d6c800b07e35c6216965", "structural-frame DFM gate candidate"),
    CandidateObservation(85, "668727ad2676a7d41f095878ff5d9110c8f7a44a", "fresh-water pump package screening candidate"),
    CandidateObservation(90, "32ffd2d297f1d4cca0da6a73cc2ce3fccb8d5388", "whole-product collision matrix requiring material-boundary rebind"),
    CandidateObservation(91, "c57b577d4e4d3333ecfb736be7fc4462dd7fa823", "actuator-mount DFM gate candidate"),
    CandidateObservation(92, "e332426526ec4ceb885ad9d35250a89d78b6066c", "integrated retention, fit, hair/pinch and positive load-path candidate"),
    CandidateObservation(93, "144934a9ad24fa497a8b101ad32e3a3231f136e0", "service-kinematics integration gate candidate"),
    CandidateObservation(94, "1eb826fe859c6d5ee6dc0097aa58a67944bb530b", "cleanser pump package screening candidate"),
    CandidateObservation(96, "2626a4f5c3b971b7caf5b384a44c262489ccf128", "mixed-waste pump package candidate"),
    CandidateObservation(98, "39dbd4c03d6f2b3965f99f75745519303b71f96a", "protected-face aggregate requiring material-boundary rebind"),
    CandidateObservation(99, "072d59bd7a278385818cf19af38dbca58b8b1bd7", "fluid-routing DFM gate candidate"),
    CandidateObservation(100, "f788284d4a4e9f30d0e35b1ceea6c716e74a5e16", "passive-backflow package candidate"),
    CandidateObservation(101, "468cc246ecc56e3e90673c55af68445f0b09ba9d", "current-main physical-material versus reference assembly-boundary candidate"),
)


PHYSICAL_GATES: tuple[PhysicalGate, ...] = (
    PhysicalGate("PVAL-ACTUATION-FORCE-RESPONSE", "actuation force/response at controlled CLEAN operating point", "VALIDATION_GATED", "instrumented actuator/load response on controlled physical hardware", (7,)),
    PhysicalGate("PVAL-AIRWAY-PRESSURE", "airway pressure-drop limits at controlled flow points", "VALIDATION_GATED", "controlled flow-bench pressure-drop evidence on final airway geometry", (4, 9)),
    PhysicalGate("PVAL-CARTRIDGE-RETENTION", "retained cartridge capacity and six-cycle service cadence", "VALIDATION_GATED", "physical capacity, retention, leakage and service-cycle evidence", (11, 16)),
    PhysicalGate("PVAL-COVERAGE", "skin-contact coverage including aggregate and T-zone targets", "VALIDATION_GATED", "representative physical fit/contact evidence", (4, 5)),
    PhysicalGate("PVAL-EXTERNAL-LEAKAGE", "external liquid leakage <= controlled per-cycle limit", "VALIDATION_GATED", "controlled wet bench leakage testing on assembled product", (4, 9, 10, 11)),
    PhysicalGate("PVAL-QUICK-RELEASE", "wet one-hand unpowered emergency release <=2.0 s and 5-12 N", "VALIDATION_GATED", "human-use and instrumented release force/time evidence", (8, 15)),
    PhysicalGate("PVAL-STRUCTURAL-MODE", "structural deflection and preferred first-mode requirement", "VALIDATION_GATED", "final material/geometry analysis correlated to physical structural evidence", (6, 17)),
    PhysicalGate("PVAL-WASTE-RECOVERY", "mixed-waste recovery >=0.90", "VALIDATION_GATED", "controlled wet recovery measurements on final fluid system", (4, 11)),
    PhysicalGate("PVAL-WASTE-RESIDUAL", "residual free liquid <=400 uL per cycle", "VALIDATION_GATED", "controlled residual-liquid measurements on final fluid system", (4, 11)),
)


REQUIREMENTS: tuple[RequirementStatus, ...] = (
    RequirementStatus("ARCH-001", "frozen_architecture", "canonical +X wearer-right, +Y superior, +Z anterior world in millimetres", False, "AUTHORITY_CONTRACT", "CLOSED", (1, 20), (), (), "preserve canonical frame and explicit transforms in every final export"),
    RequirementStatus("ARCH-002", "frozen_architecture", "outer XY 172 x 210 mm and functional-frame XY 155 x 202 mm", False, "AUTHORITY_CONTRACT", "CLOSED", (2, 6), (), (), "preserve authority envelopes through final geometry"),
    RequirementStatus("ARCH-003", "frozen_architecture", "rigid shell nominal 1.8 mm with development minimum 1.5 mm", True, "REALIZED_BREP", "CLOSED", (2, 5), (70,), (), "revalidate the minimum after any exterior source move"),
    RequirementStatus("ARCH-004", "frozen_architecture", "46 x 30 mm eye apertures, controlled cant, 3.0 mm inner-edge roll and protected eye keepouts", True, "REALIZED_BREP", "PARTIAL", (1, 2), (70, 98), (), "release the authority eye roll and rebind whole-product protected-material checks"),
    RequirementStatus("ARCH-005", "frozen_architecture", "58 x 32 mm mouth aperture and hard protected mouth envelope", True, "REALIZED_BREP", "PARTIAL", (1, 2), (70, 98), (), "recheck every accepted physical material body against the protected envelope"),
    RequirementStatus("ARCH-006", "frozen_architecture", "nostril centres +/-10.5 mm at Y -7.5 mm, local opening >=8.0 mm and controlled airway envelope", True, "DIGITAL_TOPOLOGY", "PARTIAL", (4, 9), (98,), ("PVAL-AIRWAY-PRESSURE",), "realize final airway geometry and verify full accepted-material separation"),
    RequirementStatus("ARCH-007", "frozen_architecture", "four independently controllable actuation zones", False, "DIGITAL_TOPOLOGY", "CLOSED", (7,), (), ("PVAL-ACTUATION-FORCE-RESPONSE",), "preserve four-zone identity through final mounts and controls"),
    RequirementStatus("ARCH-008", "frozen_architecture", "CLEAN development baseline about 40 Hz, 0.52 mm peak-to-peak and 61 deg axis", False, "AUTHORITY_CONTRACT", "CLOSED", (7,), (), ("PVAL-ACTUATION-FORCE-RESPONSE",), "do not promote development parameters to physical performance"),
    RequirementStatus("ARCH-009", "frozen_architecture", "fresh-water gross 6.5 mL and usable minimum 5.5 mL", True, "REFERENCE_ENVELOPE", "BLOCKED", (9,), (85,), (), "realize storage body, fill, vent, pickup, seal and service geometry"),
    RequirementStatus("ARCH-010", "frozen_architecture", "cycle water 3.2 mL, cleanser 0.60 mL and post-flush 0.80 mL", False, "AUTHORITY_CONTRACT", "CLOSED", (4, 9, 10), (), ("PVAL-EXTERNAL-LEAKAGE",), "preserve controlled fluid accounting and validate delivery/leakage physically"),
    RequirementStatus("ARCH-011", "frozen_architecture", "mixed waste order acquisition -> pump -> passive backflow protection -> cartridge", True, "REALIZED_CENTERLINE", "CLOSED", (4, 11), (96, 100), ("PVAL-WASTE-RECOVERY", "PVAL-WASTE-RESIDUAL"), "retain stage identity while selected pump/barrier hardware is packaged"),
    RequirementStatus("ARCH-012", "frozen_architecture", "waste cartridge external 74 x 36 x 20 mm, retained capacity >=35 mL and six-cycle development cadence", True, "REFERENCE_ENVELOPE", "BLOCKED", (5, 11, 16), (), ("PVAL-CARTRIDGE-RETENTION",), "realize body, cavity, keying, seal, retention and nonteleporting service geometry"),
    RequirementStatus("ARCH-013", "frozen_architecture", "wet one-hand unpowered emergency removal <=2.0 s and 5-12 N", True, "ABSENT", "BLOCKED", (8,), (71, 92), ("PVAL-QUICK-RELEASE",), "release complete crown/front reaction path and whole-head removal geometry"),
    RequirementStatus("ARCH-014", "frozen_architecture", "battery reference remains packaging evidence only until selected and promoted", False, "REFERENCE_ENVELOPE", "CLOSED", (12,), (70,), (), "do not treat benchmark battery envelope as selected dry-side hardware"),
    RequirementStatus("ARCH-015", "frozen_architecture", "dry mass <=215 g, loaded mass <255 g, CG Z <=30 mm and pitch torque <=0.070 N m", False, "AUTHORITY_CONTRACT", "CLOSED", (18,), (), (), "keep unknown part masses unknown until selected material/component evidence exists"),
    RequirementStatus("ARCH-016", "frozen_architecture", "nominal 1 deg draft and rib thickness ratio 0.40-0.60 wall", False, "AUTHORITY_CONTRACT", "CLOSED", (5, 16), (70, 77, 82, 91, 99), (), "apply to realized part splits and tooling directions before digital freeze"),
    RequirementStatus("ARCH-017", "frozen_architecture", "mature cavities must resolve to one allowed hygiene class", False, "DIGITAL_TOPOLOGY", "PARTIAL", (4, 16), (), (), "classify every final realized cavity after geometry/service closure"),

    RequirementStatus("MVP-001", "digital_mvp_deliverable", "mature calm consumer-care exterior with authority eye treatment and disciplined rear package", True, "REALIZED_BREP", "BLOCKED", (2,), (70,), (), "close tooling/part split/draft and real dry-side nesting behind the compact service interface"),
    RequirementStatus("MVP-002", "digital_mvp_deliverable", "explicit physical-material versus reference/keepout assembly boundary", True, "REALIZED_BREP", "BLOCKED", (1, 20), (101,), (), "consume a released assembly-boundary composer before whole-product collision/export promotion"),
    RequirementStatus("MVP-003", "digital_mvp_deliverable", "real structural frame, shell-frame joins and complete positive load paths", True, "DIGITAL_TOPOLOGY", "BLOCKED", (3, 6), (82, 92), ("PVAL-STRUCTURAL-MODE",), "realize frame members, sections, joins, mating counterparts and material"),
    RequirementStatus("MVP-004", "digital_mvp_deliverable", "four-zone actuator mounting, coupling, stops and structural reactions", True, "DIGITAL_TOPOLOGY", "BLOCKED", (3, 7), (91,), ("PVAL-ACTUATION-FORCE-RESPONSE",), "realize mount B-reps, positive attachments, hard stops and service access"),
    RequirementStatus("MVP-005", "digital_mvp_deliverable", "retention, crown support, positive quick release and nonteleporting whole-head removal", True, "ABSENT", "BLOCKED", (3, 8), (71, 92), ("PVAL-QUICK-RELEASE",), "close crown/front counterparts, carrier separation/reassembly and complete removal path"),
    RequirementStatus("MVP-006", "digital_mvp_deliverable", "complete fresh-water storage, pump, manifold, routing and outlets", True, "DIGITAL_TOPOLOGY", "BLOCKED", (4, 9), (85, 99), ("PVAL-EXTERNAL-LEAKAGE",), "realize selected package interfaces, service geometry and route supports without protected conflicts"),
    RequirementStatus("MVP-007", "digital_mvp_deliverable", "complete cleanser storage, pump, routing, distribution and service", True, "DIGITAL_TOPOLOGY", "BLOCKED", (4, 10), (80, 94, 99), ("PVAL-EXTERNAL-LEAKAGE",), "release storage/service geometry and selected pump/package interfaces"),
    RequirementStatus("MVP-008", "digital_mvp_deliverable", "complete mixed-waste acquisition, pump, passive backflow protection, routing and cartridge handoff", True, "REALIZED_CENTERLINE", "PARTIAL", (4, 11), (96, 100), ("PVAL-WASTE-RECOVERY", "PVAL-WASTE-RESIDUAL"), "retain released centerline backbone while closing selected hardware packages and service"),
    RequirementStatus("MVP-009", "digital_mvp_deliverable", "real waste-cartridge body, internal capacity, keying, seal, retention and service trajectory", True, "DFM_GATE_ONLY", "BLOCKED", (5, 11, 16), (), ("PVAL-CARTRIDGE-RETENTION",), "replace package envelope and DFM gate with manufacturable B-rep and verified insertion/removal geometry"),
    RequirementStatus("MVP-010", "digital_mvp_deliverable", "current dry-side battery, PCB, charging, supports, sealing and extraction package", True, "REFERENCE_ENVELOPE", "BLOCKED", (12,), (70,), (), "nest real dry-side components and attachments behind the accepted exterior interface"),
    RequirementStatus("MVP-011", "digital_mvp_deliverable", "complete harness, connectors and wet/dry bulkhead geometry", True, "ABSENT", "BLOCKED", (13,), (), (), "realize endpoint-to-endpoint harness, connector retention, bulkhead sealing and service"),
    RequirementStatus("MVP-012", "digital_mvp_deliverable", "physical HMI and WARM thermal/user-facing hardware packaging", True, "ABSENT", "BLOCKED", (14,), (), (), "realize user hardware, thermal interfaces, guards, service and dry/wet relationships"),
    RequirementStatus("MVP-013", "digital_mvp_deliverable", "whole-product wet/dry/hygiene classification with every mature cavity resolved", False, "DIGITAL_TOPOLOGY", "BLOCKED", (4, 16), (), (), "complete classifications after missing physical cavities and service states exist"),
    RequirementStatus("MVP-014", "digital_mvp_deliverable", "nonteleporting assembly and service kinematics for every removable/replaceable subsystem", True, "DIGITAL_TOPOLOGY", "BLOCKED", (15,), (71, 80, 93), (), "replace reservations and sampled proxies with continuous collision-checked motions where required"),
    RequirementStatus("MVP-015", "digital_mvp_deliverable", "DFM part splits, joinery, tooling directions, draft, ribs and surface closure", True, "DFM_GATE_ONLY", "BLOCKED", (5, 16), (70, 77, 82, 91, 99), (), "apply DFM gates to realized part families and close all P0 manufacturability blockers"),
    RequirementStatus("MVP-016", "digital_mvp_deliverable", "whole-product CTQ, tolerance and manufacturing datum architecture", False, "DIGITAL_TOPOLOGY", "PARTIAL", (17,), (), (), "extend mechanism-local tolerance contracts to all final interfaces, seals, seams and service datums"),
    RequirementStatus("MVP-017", "digital_mvp_deliverable", "honest mass, CG and pitch ledger with no invented unknown masses", False, "ABSENT", "BLOCKED", (18,), (), (), "bind every final part/component mass source and recompute loaded/dry properties"),
    RequirementStatus("MVP-018", "digital_mvp_deliverable", "honest power and fluid ledgers bound to selected packages and realized routes", False, "DIGITAL_TOPOLOGY", "BLOCKED", (18,), (), (), "retain released fluid accounting and add selected electrical loads, duty cycles and unresolved unknowns"),
    RequirementStatus("MVP-019", "digital_mvp_deliverable", "zero unexplained accepted-material collisions and zero protected-region conflicts", True, "DIGITAL_TOPOLOGY", "BLOCKED", (1, 19), (90, 98, 101), (), "rebind collision/protected checks to the released physical-material boundary and every accepted subsystem body"),
    RequirementStatus("MVP-020", "digital_mvp_deliverable", "deterministic STEP/export hierarchy and Fusion handoff for the complete physical product", True, "REALIZED_BREP", "PARTIAL", (1, 20), (70, 101), (), "export final physical hierarchy, references separately, stable IDs/transforms, manifests and Fusion-ready handoff"),
    RequirementStatus("MVP-021", "digital_mvp_deliverable", "precise physical-validation blocker register without converting digital evidence into validation", False, "ABSENT", "BLOCKED", (20,), (), (), "release this Cell 20 manifest and keep every physical gate open until controlled evidence exists"),
)


@dataclass(frozen=True, slots=True)
class MvpCompletenessMatrix:
    source_main_sha: str
    authority_revision: str
    authority_blob_sha: str
    authority_schema_blob_sha: str
    world_frame_id: str
    candidate_snapshot_observed_at_utc: str
    requirements: tuple[RequirementStatus, ...]
    candidate_observations: tuple[CandidateObservation, ...]
    physical_gates: tuple[PhysicalGate, ...]
    evidence_status: str = EVIDENCE_STATUS
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_main_sha != SOURCE_MAIN_SHA or _SHA40.fullmatch(self.source_main_sha) is None:
            raise MvpCompletenessError("MVP completeness matrix is stale for released main")
        if self.authority_revision != AUTHORITY_REVISION:
            raise MvpCompletenessError("MVP completeness authority revision is stale")
        if self.authority_blob_sha != AUTHORITY_BLOB_SHA or _SHA40.fullmatch(self.authority_blob_sha) is None:
            raise MvpCompletenessError("MVP completeness authority blob is stale")
        if self.authority_schema_blob_sha != AUTHORITY_SCHEMA_BLOB_SHA or _SHA40.fullmatch(self.authority_schema_blob_sha) is None:
            raise MvpCompletenessError("MVP completeness authority schema blob is stale")
        if self.world_frame_id != WORLD_FRAME_ID:
            raise MvpCompletenessError("MVP completeness must use the canonical authority world frame")
        _text(self.candidate_snapshot_observed_at_utc, label="candidate snapshot timestamp")
        if type(self.requirements) is not tuple or not self.requirements:
            raise MvpCompletenessError("MVP completeness requires immutable requirement rows")
        ids = tuple(item.requirement_id for item in self.requirements)
        if ids != tuple(dict.fromkeys(ids)):
            raise MvpCompletenessError("MVP requirement IDs must be unique and deterministic")
        for item in self.requirements:
            item.__post_init__()
        if type(self.candidate_observations) is not tuple:
            raise MvpCompletenessError("candidate observations must be immutable")
        candidate_ids = tuple(item.pr_number for item in self.candidate_observations)
        if candidate_ids != tuple(sorted(candidate_ids)) or len(candidate_ids) != len(set(candidate_ids)):
            raise MvpCompletenessError("candidate observations must be unique and sorted by PR number")
        candidate_set = set(candidate_ids)
        for item in self.candidate_observations:
            item.__post_init__()
        for row in self.requirements:
            missing = set(row.candidate_prs) - candidate_set
            if missing:
                raise MvpCompletenessError(f"requirement references unknown candidate PRs: {sorted(missing)}")
        if type(self.physical_gates) is not tuple:
            raise MvpCompletenessError("physical gates must be immutable")
        gate_ids = tuple(item.gate_id for item in self.physical_gates)
        if gate_ids != tuple(sorted(gate_ids)) or len(gate_ids) != len(set(gate_ids)):
            raise MvpCompletenessError("physical gates must be unique and sorted by gate ID")
        gate_set = set(gate_ids)
        for item in self.physical_gates:
            item.__post_init__()
        for row in self.requirements:
            missing = set(row.physical_gate_ids) - gate_set
            if missing:
                raise MvpCompletenessError(f"requirement references unknown physical gates: {sorted(missing)}")
        if self.evidence_status != EVIDENCE_STATUS:
            raise MvpCompletenessError("MVP completeness evidence boundary is controlled")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise MvpCompletenessError("digital completeness evidence cannot become physical validation")

    @property
    def digital_state_counts(self) -> dict[str, int]:
        self.__post_init__()
        return {
            state: sum(item.digital_state == state for item in self.requirements)
            for state in ("CLOSED", "PARTIAL", "BLOCKED")
        }

    @property
    def digital_mvp_freeze_ready(self) -> bool:
        self.__post_init__()
        return all(item.digital_state == "CLOSED" for item in self.requirements)

    @property
    def physical_validation_complete(self) -> bool:
        self.__post_init__()
        return all(item.closed for item in self.physical_gates)

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        payload = {
            "schema": SCHEMA,
            "source_main_sha": self.source_main_sha,
            "source_package_tree_sha": SOURCE_PACKAGE_TREE_SHA,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "authority_schema_blob_sha": self.authority_schema_blob_sha,
            "world_frame_id": self.world_frame_id,
            "candidate_snapshot_observed_at_utc": self.candidate_snapshot_observed_at_utc,
            "candidate_snapshot_release_authoritative": False,
            "candidate_snapshot_review_evidence_eligible": False,
            "requirements": [item.manifest() for item in self.requirements],
            "candidate_observations": [item.manifest() for item in self.candidate_observations],
            "physical_validation_blockers": [item.manifest() for item in self.physical_gates],
            "digital_state_counts": self.digital_state_counts,
            "digital_mvp_freeze_ready": self.digital_mvp_freeze_ready,
            "physical_validation_complete": self.physical_validation_complete,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        return payload

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(self.manifest(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return sha256(raw).hexdigest()


def build_mvp_completeness_matrix(authority: Authority | None = None) -> MvpCompletenessMatrix:
    current_authority = load_authority() if authority is None else authority
    _require_released_sources_current(current_authority)
    matrix = MvpCompletenessMatrix(
        source_main_sha=SOURCE_MAIN_SHA,
        authority_revision=AUTHORITY_REVISION,
        authority_blob_sha=AUTHORITY_BLOB_SHA,
        authority_schema_blob_sha=AUTHORITY_SCHEMA_BLOB_SHA,
        world_frame_id=WORLD_FRAME_ID,
        candidate_snapshot_observed_at_utc=CANDIDATE_SNAPSHOT_OBSERVED_AT_UTC,
        requirements=REQUIREMENTS,
        candidate_observations=CANDIDATE_OBSERVATIONS,
        physical_gates=PHYSICAL_GATES,
    )
    matrix.__post_init__()
    return matrix


def write_mvp_completeness_manifest(path: str | Path) -> Path:
    output = Path(path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    matrix = build_mvp_completeness_matrix()
    payload = matrix.manifest()
    payload["manifest_sha256"] = matrix.manifest_sha256
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit the fail-closed Cell 20 MVP completeness manifest")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    output = write_mvp_completeness_manifest(args.output)
    matrix = build_mvp_completeness_matrix()
    print(
        json.dumps(
            {
                "output": str(output),
                "manifest_sha256": matrix.manifest_sha256,
                "digital_state_counts": matrix.digital_state_counts,
                "digital_mvp_freeze_ready": matrix.digital_mvp_freeze_ready,
                "physical_validation_complete": matrix.physical_validation_complete,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
