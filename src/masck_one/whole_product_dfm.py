from __future__ import annotations

"""Cross-cutting manufacturing part architecture for the released Masck One baseline.

This module owns no subsystem B-rep. It records manufacturing part boundaries,
assembly dependencies, service ownership, hygiene intent and prototype/production
process intent. Active specialist PRs may be supplied as observations for a review
session, but they are never release truth and are not hard-coded into the contract.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from .authority import Authority, load_authority

DFM_SCHEMA = "MASCK_ONE_WHOLE_PRODUCT_DFM_PART_ARCHITECTURE_V1"
SOURCE_MAIN_SHA = "5fce2a43a34d8be49256677a35af60c906dc1653"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

OWNER_CELL_1 = "CELL_1_INTEGRATION"
OWNER_CELL_2 = "CELL_2_EXTERIOR_INTERFACE"
OWNER_CELL_3 = "CELL_3_MECHANISMS_RETENTION"
OWNER_CELL_4 = "CELL_4_FLUID_POWER_HMI_THERMAL"
OWNERS = (OWNER_CELL_1, OWNER_CELL_2, OWNER_CELL_3, OWNER_CELL_4)

SYSTEM_SHELL_INTERFACE = "SHELL_INTERFACE"
SYSTEM_STRUCTURE_RETENTION = "STRUCTURE_RETENTION"
SYSTEM_ACTUATION = "ACTUATION"
SYSTEM_FRESH_FLUID = "FRESH_FLUID"
SYSTEM_WASTE = "WASTE"
SYSTEM_ELECTRICAL_HMI = "ELECTRICAL_HMI"
SYSTEMS = (SYSTEM_SHELL_INTERFACE, SYSTEM_STRUCTURE_RETENTION, SYSTEM_ACTUATION, SYSTEM_FRESH_FLUID, SYSTEM_WASTE, SYSTEM_ELECTRICAL_HMI)

MATURITY_RELEASED_GEOMETRY = "RELEASED_GEOMETRY"
MATURITY_RELEASED_ENVELOPE = "RELEASED_ENVELOPE"
MATURITY_RELEASED_TOPOLOGY = "RELEASED_TOPOLOGY"
MATURITY_DEVELOPMENT_REFERENCE = "DEVELOPMENT_REFERENCE"
MATURITY_UNRESOLVED_REQUIRED = "UNRESOLVED_REQUIRED"
MATURITIES = (MATURITY_RELEASED_GEOMETRY, MATURITY_RELEASED_ENVELOPE, MATURITY_RELEASED_TOPOLOGY, MATURITY_DEVELOPMENT_REFERENCE, MATURITY_UNRESOLVED_REQUIRED)

SERVICE_NONUSER_FIXED = "NONUSER_FIXED"
SERVICE_USER_REMOVABLE = "USER_REMOVABLE"
SERVICE_CONSUMABLE_REPLACEABLE = "CONSUMABLE_REPLACEABLE"
SERVICE_TECHNICIAN_REMOVABLE = "TECHNICIAN_REMOVABLE"
SERVICE_CLASSES = (SERVICE_NONUSER_FIXED, SERVICE_USER_REMOVABLE, SERVICE_CONSUMABLE_REPLACEABLE, SERVICE_TECHNICIAN_REMOVABLE)
PATH_NOT_APPLICABLE = "NOT_APPLICABLE"
PATH_REQUIRED = "DIGITAL_PATH_REQUIRED"
PATH_CLOSED = "DIGITAL_PATH_CLOSED"
PATH_STATUSES = (PATH_NOT_APPLICABLE, PATH_REQUIRED, PATH_CLOSED)

ROLE_PRIMARY_STRUCTURE = "PRIMARY_STRUCTURE"
ROLE_HOUSING = "HOUSING"
ROLE_COVER = "COVER"
ROLE_SOFT_INTERFACE = "SOFT_INTERFACE"
ROLE_RETENTION = "RETENTION"
ROLE_LATCH = "LATCH"
ROLE_CARRIER = "CARRIER"
ROLE_PURCHASED_PACKAGE = "PURCHASED_PACKAGE"
ROLE_RESERVOIR = "RESERVOIR"
ROLE_MANIFOLD = "MANIFOLD"
ROLE_ROUTE = "ROUTE"
ROLE_SEAL = "SEAL"
ROLE_CONNECTOR = "CONNECTOR"
ROLE_CARTRIDGE = "CARTRIDGE"
ROLE_HMI = "HMI"
ROLE_ELECTRICAL = "ELECTRICAL"
ROLES = (ROLE_PRIMARY_STRUCTURE, ROLE_HOUSING, ROLE_COVER, ROLE_SOFT_INTERFACE, ROLE_RETENTION, ROLE_LATCH, ROLE_CARRIER, ROLE_PURCHASED_PACKAGE, ROLE_RESERVOIR, ROLE_MANIFOLD, ROLE_ROUTE, ROLE_SEAL, ROLE_CONNECTOR, ROLE_CARTRIDGE, ROLE_HMI, ROLE_ELECTRICAL)

PROCESS_RIGID_POLYMER_TBD = "RIGID_POLYMER_PROCESS_TBD"
PROCESS_SOFT_POLYMER_TBD = "SOFT_POLYMER_PROCESS_TBD"
PROCESS_STRUCTURAL_CARRIER_TBD = "STRUCTURAL_CARRIER_PROCESS_TBD"
PROCESS_PURCHASED_REFERENCE = "PURCHASED_COMPONENT_REFERENCE_ONLY"
PROCESS_FLEXIBLE_ROUTE_TBD = "FLEXIBLE_ROUTE_OR_CHANNEL_PROCESS_TBD"
PROCESS_SEAL_TBD = "SEAL_PROCESS_AND_MATERIAL_TBD"
PROCESS_ELECTRONIC_ASSEMBLY_TBD = "ELECTRONIC_ASSEMBLY_PROCESS_TBD"
PROCESS_INTENTS = (PROCESS_RIGID_POLYMER_TBD, PROCESS_SOFT_POLYMER_TBD, PROCESS_STRUCTURAL_CARRIER_TBD, PROCESS_PURCHASED_REFERENCE, PROCESS_FLEXIBLE_ROUTE_TBD, PROCESS_SEAL_TBD, PROCESS_ELECTRONIC_ASSEMBLY_TBD)
PROTOTYPE_PRINT_MACHINE = "ADDITIVE_OR_MACHINED_PROTOTYPE_CANDIDATE"
PROTOTYPE_SOFT_TOOL = "SOFT_TOOL_OR_CAST_PROTOTYPE_CANDIDATE"
PROTOTYPE_PURCHASED = "PURCHASED_DEVELOPMENT_REFERENCE"
PROTOTYPE_FLEXIBLE_ROUTE = "CUT_FORMED_FLEXIBLE_ROUTE_PROTOTYPE_CANDIDATE"
PROTOTYPE_ELECTRONICS = "DEVELOPMENT_ELECTRONIC_ASSEMBLY_CANDIDATE"
PROTOTYPE_METHODS = (PROTOTYPE_PRINT_MACHINE, PROTOTYPE_SOFT_TOOL, PROTOTYPE_PURCHASED, PROTOTYPE_FLEXIBLE_ROUTE, PROTOTYPE_ELECTRONICS)

H_DRY = "DRY_ALWAYS"
H_WET_DRAINABLE = "WET_DRAINABLE"
H_WET_REMOVABLE = "WET_REMOVABLE"
H_SEALED = "SEALED_NONUSER"
HYGIENE_CLASSES = (H_DRY, H_WET_DRAINABLE, H_WET_REMOVABLE, H_SEALED)
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_PART_RE = re.compile(r"^MASCK_ONE-DFM-[A-Z0-9-]+$")


class DfmArchitectureError(ValueError):
    pass


def _real(value: object, *, label: str, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise DfmArchitectureError(f"{label} must be an exact numeric scalar")
    out = float(value)
    if not math.isfinite(out):
        raise DfmArchitectureError(f"{label} must be finite")
    if positive and out <= 0.0:
        raise DfmArchitectureError(f"{label} must be positive")
    return out


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise DfmArchitectureError(f"{label} must be exact nonblank text")
    return value


@dataclass(frozen=True, slots=True)
class ManufacturingRules:
    mold_draft_nominal_deg: float
    rib_thickness_ratio_min: float
    rib_thickness_ratio_max: float
    visible_seam_gap_mm: float
    visible_seam_tolerance_mm: float
    flush_mismatch_max_mm: float
    hygiene_classes: tuple[str, ...]
    evidence_status: str = "AUTHORITY_GEOMETRY_RULES_ONLY_NOT_TOOLING_OR_PROCESS_VALIDATION"

    def __post_init__(self) -> None:
        draft = _real(self.mold_draft_nominal_deg, label="mold draft", positive=True)
        rib_min = _real(self.rib_thickness_ratio_min, label="rib ratio minimum", positive=True)
        rib_max = _real(self.rib_thickness_ratio_max, label="rib ratio maximum", positive=True)
        gap = _real(self.visible_seam_gap_mm, label="visible seam gap", positive=True)
        tol = _real(self.visible_seam_tolerance_mm, label="visible seam tolerance", positive=True)
        flush = _real(self.flush_mismatch_max_mm, label="flush mismatch", positive=True)
        if rib_min >= rib_max:
            raise DfmArchitectureError("rib ratio range must be strictly increasing")
        if self.hygiene_classes != HYGIENE_CLASSES:
            raise DfmArchitectureError("DFM hygiene vocabulary must match frozen authority order")
        if self.evidence_status != "AUTHORITY_GEOMETRY_RULES_ONLY_NOT_TOOLING_OR_PROCESS_VALIDATION":
            raise DfmArchitectureError("manufacturing rules cannot imply tooling validation")
        object.__setattr__(self, "mold_draft_nominal_deg", draft)
        object.__setattr__(self, "rib_thickness_ratio_min", rib_min)
        object.__setattr__(self, "rib_thickness_ratio_max", rib_max)
        object.__setattr__(self, "visible_seam_gap_mm", gap)
        object.__setattr__(self, "visible_seam_tolerance_mm", tol)
        object.__setattr__(self, "flush_mismatch_max_mm", flush)

    def manifest(self) -> dict[str, object]:
        return {"mold_draft_nominal_deg": self.mold_draft_nominal_deg, "rib_thickness_ratio_range": [self.rib_thickness_ratio_min, self.rib_thickness_ratio_max], "visible_seam_gap_mm": self.visible_seam_gap_mm, "visible_seam_tolerance_mm": self.visible_seam_tolerance_mm, "flush_mismatch_max_mm": self.flush_mismatch_max_mm, "hygiene_classes": list(self.hygiene_classes), "evidence_status": self.evidence_status}


@dataclass(frozen=True, slots=True)
class PartFamily:
    part_id: str
    display_name: str
    system: str
    owner: str
    quantity: int
    role: str
    maturity: str
    source_ref: str
    hygiene_class: str
    hygiene_provenance: str
    service_class: str
    service_path_status: str
    prototype_method: str
    production_process_intent: str
    assembly_stage: int
    prerequisites: tuple[str, ...]
    closure_semantics: str
    evidence_status: str = "DIGITAL_PART_BOUNDARY_ONLY_NOT_PRODUCTION_OR_PHYSICAL_VALIDATION"

    def __post_init__(self) -> None:
        if type(self.part_id) is not str or _PART_RE.fullmatch(self.part_id) is None:
            raise DfmArchitectureError("part ID must use the controlled MASCK_ONE-DFM namespace")
        for label, value in (("part display name", self.display_name), ("part source reference", self.source_ref), ("hygiene provenance", self.hygiene_provenance), ("closure semantics", self.closure_semantics)):
            _text(value, label=label)
        if self.system not in SYSTEMS or self.owner not in OWNERS:
            raise DfmArchitectureError("uncontrolled system or owner")
        if type(self.quantity) is not int or isinstance(self.quantity, bool) or self.quantity <= 0:
            raise DfmArchitectureError("part-family quantity must be an exact positive integer")
        if self.role not in ROLES or self.maturity not in MATURITIES:
            raise DfmArchitectureError("uncontrolled part role or maturity")
        if self.hygiene_class not in HYGIENE_CLASSES or self.service_class not in SERVICE_CLASSES:
            raise DfmArchitectureError("uncontrolled hygiene or service class")
        if self.service_path_status not in PATH_STATUSES:
            raise DfmArchitectureError("uncontrolled service-path state")
        if self.prototype_method not in PROTOTYPE_METHODS or self.production_process_intent not in PROCESS_INTENTS:
            raise DfmArchitectureError("uncontrolled manufacturing intent")
        if type(self.assembly_stage) is not int or isinstance(self.assembly_stage, bool) or self.assembly_stage < 0:
            raise DfmArchitectureError("assembly stage must be an exact non-negative integer")
        if type(self.prerequisites) is not tuple or any(type(item) is not str for item in self.prerequisites):
            raise DfmArchitectureError("assembly prerequisites must be an exact tuple of part IDs")
        if self.part_id in self.prerequisites:
            raise DfmArchitectureError("a part cannot depend on itself")
        if self.role == ROLE_SEAL and self.hygiene_class == H_DRY:
            raise DfmArchitectureError("a seal part cannot be classified DRY_ALWAYS")
        if self.service_class in (SERVICE_USER_REMOVABLE, SERVICE_CONSUMABLE_REPLACEABLE):
            if self.hygiene_class == H_SEALED:
                raise DfmArchitectureError("user-service parts cannot be SEALED_NONUSER")
            if self.service_path_status == PATH_NOT_APPLICABLE:
                raise DfmArchitectureError("user-service parts require explicit digital service-path state")
        if self.service_class == SERVICE_NONUSER_FIXED and self.service_path_status == PATH_CLOSED:
            raise DfmArchitectureError("nonuser fixed parts cannot claim a service trajectory")
        if self.evidence_status != "DIGITAL_PART_BOUNDARY_ONLY_NOT_PRODUCTION_OR_PHYSICAL_VALIDATION":
            raise DfmArchitectureError("part record cannot promote production or physical validation")

    def manifest(self) -> dict[str, object]:
        return {"part_id": self.part_id, "display_name": self.display_name, "system": self.system, "owner": self.owner, "quantity": self.quantity, "role": self.role, "maturity": self.maturity, "source_ref": self.source_ref, "hygiene_class": self.hygiene_class, "hygiene_provenance": self.hygiene_provenance, "service_class": self.service_class, "service_path_status": self.service_path_status, "prototype_method": self.prototype_method, "production_process_intent": self.production_process_intent, "assembly_stage": self.assembly_stage, "prerequisites": list(self.prerequisites), "closure_semantics": self.closure_semantics, "evidence_status": self.evidence_status}


@dataclass(frozen=True, slots=True)
class CandidateBinding:
    pr_number: int
    head_sha: str
    owner: str
    affected_part_ids: tuple[str, ...]
    authority_status: str = "OBSERVED_UNMERGED_CANDIDATE_NOT_RELEASE_AUTHORITY"

    def __post_init__(self) -> None:
        if type(self.pr_number) is not int or isinstance(self.pr_number, bool) or self.pr_number <= 0:
            raise DfmArchitectureError("candidate PR number must be an exact positive integer")
        if type(self.head_sha) is not str or _SHA_RE.fullmatch(self.head_sha) is None:
            raise DfmArchitectureError("candidate head must be canonical lowercase 40-hex")
        if self.owner not in OWNERS:
            raise DfmArchitectureError("candidate owner is uncontrolled")
        if type(self.affected_part_ids) is not tuple or not self.affected_part_ids or len(self.affected_part_ids) != len(set(self.affected_part_ids)):
            raise DfmArchitectureError("candidate affected part IDs must be a nonempty unique tuple")
        if self.authority_status != "OBSERVED_UNMERGED_CANDIDATE_NOT_RELEASE_AUTHORITY":
            raise DfmArchitectureError("unmerged candidate cannot become release authority")

    def manifest(self) -> dict[str, object]:
        return {"pr_number": self.pr_number, "head_sha": self.head_sha, "owner": self.owner, "affected_part_ids": list(self.affected_part_ids), "authority_status": self.authority_status}


@dataclass(frozen=True, slots=True)
class WholeProductDfmArchitecture:
    schema: str
    source_main_sha: str
    authority_revision: str
    authority_blob_sha: str
    coordinate_frame_id: str
    rules: ManufacturingRules
    parts: tuple[PartFamily, ...]
    observed_candidates: tuple[CandidateBinding, ...]
    physical_validation_eligible: bool
    production_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.schema != DFM_SCHEMA:
            raise DfmArchitectureError("unexpected DFM architecture schema")
        if self.source_main_sha != SOURCE_MAIN_SHA or _SHA_RE.fullmatch(self.source_main_sha) is None:
            raise DfmArchitectureError("DFM architecture is stale for reconstructed main")
        if self.authority_revision != AUTHORITY_REVISION or self.authority_blob_sha != AUTHORITY_BLOB_SHA:
            raise DfmArchitectureError("DFM architecture authority identity is stale")
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise DfmArchitectureError("DFM architecture must use the canonical authority frame")
        if type(self.rules) is not ManufacturingRules or type(self.parts) is not tuple or not self.parts or type(self.observed_candidates) is not tuple:
            raise DfmArchitectureError("DFM architecture requires immutable controlled inputs")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise DfmArchitectureError("digital DFM architecture cannot be physical evidence")
        if type(self.production_validation_eligible) is not bool or self.production_validation_eligible:
            raise DfmArchitectureError("digital DFM architecture cannot validate production tooling or capability")
        if self.evidence_status != "DIGITAL_PART_SPLIT_ASSEMBLY_SERVICE_AND_PROCESS_INTENT_ONLY_NOT_TOOLING_SUPPLIER_MOLDABILITY_SEALING_DURABILITY_HYGIENE_OR_PHYSICAL_EVIDENCE":
            raise DfmArchitectureError("DFM evidence firewall must remain explicit")
        self._validate_graph_and_coverage()

    def _validate_graph_and_coverage(self) -> None:
        by_id = {part.part_id: part for part in self.parts}
        if len(by_id) != len(self.parts):
            raise DfmArchitectureError("DFM part IDs must be globally unique")
        if tuple(part.part_id for part in self.parts) != tuple(sorted(by_id)):
            raise DfmArchitectureError("DFM parts must be deterministic by part ID")
        if set(part.system for part in self.parts) != set(SYSTEMS):
            raise DfmArchitectureError("DFM architecture must cover every whole-product system")
        for part in self.parts:
            for dependency in part.prerequisites:
                if dependency not in by_id:
                    raise DfmArchitectureError(f"unknown assembly prerequisite {dependency!r}")
                if by_id[dependency].assembly_stage >= part.assembly_stage:
                    raise DfmArchitectureError("assembly prerequisites must occur at an earlier stage")
        required_roles = {ROLE_HOUSING, ROLE_COVER, ROLE_SOFT_INTERFACE, ROLE_PRIMARY_STRUCTURE, ROLE_RETENTION, ROLE_LATCH, ROLE_CARRIER, ROLE_PURCHASED_PACKAGE, ROLE_RESERVOIR, ROLE_MANIFOLD, ROLE_ROUTE, ROLE_SEAL, ROLE_CONNECTOR, ROLE_CARTRIDGE, ROLE_HMI, ROLE_ELECTRICAL}
        if not required_roles.issubset({part.role for part in self.parts}):
            raise DfmArchitectureError("DFM architecture is missing required manufacturing roles")
        candidate_prs: set[int] = set()
        for candidate in self.observed_candidates:
            candidate.__post_init__()
            if candidate.pr_number in candidate_prs:
                raise DfmArchitectureError("candidate PR bindings cannot repeat")
            candidate_prs.add(candidate.pr_number)
            if any(part_id not in by_id for part_id in candidate.affected_part_ids):
                raise DfmArchitectureError("candidate binding references an unknown DFM part")

    @property
    def unresolved_required_part_ids(self) -> tuple[str, ...]:
        return tuple(part.part_id for part in self.parts if part.maturity == MATURITY_UNRESOLVED_REQUIRED)

    @property
    def user_service_blocker_ids(self) -> tuple[str, ...]:
        return tuple(part.part_id for part in self.parts if part.service_class in (SERVICE_USER_REMOVABLE, SERVICE_CONSUMABLE_REPLACEABLE) and part.service_path_status != PATH_CLOSED)

    @property
    def digital_mvp_part_architecture_ready(self) -> bool:
        return not self.unresolved_required_part_ids and not self.user_service_blocker_ids

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": self.schema,
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "coordinate_frame_id": self.coordinate_frame_id,
            "manufacturing_rules": self.rules.manifest(),
            "parts": [part.manifest() for part in self.parts],
            "observed_candidates": [candidate.manifest() for candidate in self.observed_candidates],
            "system_summary": {system: {"part_family_count": sum(part.system == system for part in self.parts), "physical_part_quantity": sum(part.quantity for part in self.parts if part.system == system), "unresolved_part_family_count": sum(part.system == system and part.maturity == MATURITY_UNRESOLVED_REQUIRED for part in self.parts)} for system in SYSTEMS},
            "unresolved_required_part_ids": list(self.unresolved_required_part_ids),
            "user_service_blocker_ids": list(self.user_service_blocker_ids),
            "digital_mvp_part_architecture_ready": self.digital_mvp_part_architecture_ready,
            "physical_validation_eligible": self.physical_validation_eligible,
            "production_validation_eligible": self.production_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["dfm_architecture_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def _p(suffix: str, name: str, system: str, owner: str, quantity: int, role: str, maturity: str, source: str, hygiene: str, service: str, path: str, prototype: str, production: str, stage: int, prerequisites: tuple[str, ...] = (), closure: str = "NO_SEPARATE_CLOSURE_REQUIRED", hygiene_provenance: str = "CELL5_PROVISIONAL_CLASS_WITHIN_FROZEN_AUTHORITY_VOCABULARY") -> PartFamily:
    return PartFamily(f"MASCK_ONE-DFM-{suffix}", name, system, owner, quantity, role, maturity, source, hygiene, hygiene_provenance, service, path, prototype, production, stage, prerequisites, closure)


def _build_parts() -> tuple[PartFamily, ...]:
    p = (
        _p("SHELL-PRIMARY", "Primary exterior shell", SYSTEM_SHELL_INTERFACE, OWNER_CELL_2, 1, ROLE_HOUSING, MATURITY_RELEASED_GEOMETRY, "src/masck_one/model.py:rigid_shell", H_WET_DRAINABLE, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 10),
        _p("FACIAL-INTERFACE-CARRIER", "Compliant facial interface carrier", SYSTEM_SHELL_INTERFACE, OWNER_CELL_2, 1, ROLE_SOFT_INTERFACE, MATURITY_RELEASED_TOPOLOGY, "src/masck_one/interface_topology.py", H_WET_DRAINABLE, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, PROTOTYPE_SOFT_TOOL, PROCESS_SOFT_POLYMER_TBD, 70, ("MASCK_ONE-DFM-SHELL-PRIMARY",)),
        _p("NASAL-LOBE-MEMBRANE", "Nasal lobe membrane insert", SYSTEM_SHELL_INTERFACE, OWNER_CELL_2, 1, ROLE_SOFT_INTERFACE, MATURITY_DEVELOPMENT_REFERENCE, "src/masck_one/model.py:nasal_lobe_membrane_reference", H_WET_DRAINABLE, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, PROTOTYPE_SOFT_TOOL, PROCESS_SOFT_POLYMER_TBD, 72, ("MASCK_ONE-DFM-FACIAL-INTERFACE-CARRIER",)),
        _p("REAR-SERVICE-COVER", "Rear service cover", SYSTEM_SHELL_INTERFACE, OWNER_CELL_4, 1, ROLE_COVER, MATURITY_UNRESOLVED_REQUIRED, "src/masck_one/structural_frame.py:HMI_ELECTRONICS_RESERVATION", H_WET_DRAINABLE, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 95, ("MASCK_ONE-DFM-DRY-BAY-HOUSING", "MASCK_ONE-DFM-DRY-BAY-COVER-SEAL"), "POSITIVE_RETAINED_COVER_WITH_TOOL_OR_CONTROLLED_RELEASE_ACCESS"),
        _p("REACTION-FRAME", "Internal reaction frame", SYSTEM_STRUCTURE_RETENTION, OWNER_CELL_3, 1, ROLE_PRIMARY_STRUCTURE, MATURITY_RELEASED_TOPOLOGY, "src/masck_one/structural_frame.py", H_SEALED, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, PROTOTYPE_PRINT_MACHINE, PROCESS_STRUCTURAL_CARRIER_TBD, 20, ("MASCK_ONE-DFM-SHELL-PRIMARY",)),
        _p("RETENTION-HALO-LEFT", "Left retention halo member", SYSTEM_STRUCTURE_RETENTION, OWNER_CELL_3, 1, ROLE_RETENTION, MATURITY_UNRESOLVED_REQUIRED, "src/masck_one/structural_frame.py:RETENTION_RESERVATION", H_DRY, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, PROTOTYPE_PRINT_MACHINE, PROCESS_STRUCTURAL_CARRIER_TBD, 80, ("MASCK_ONE-DFM-REACTION-FRAME",)),
        _p("RETENTION-HALO-RIGHT-TONGUE", "Right retention halo and latch tongue", SYSTEM_STRUCTURE_RETENTION, OWNER_CELL_3, 1, ROLE_RETENTION, MATURITY_UNRESOLVED_REQUIRED, "src/masck_one/structural_frame.py:RETENTION_RESERVATION", H_DRY, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, PROTOTYPE_PRINT_MACHINE, PROCESS_STRUCTURAL_CARRIER_TBD, 80, ("MASCK_ONE-DFM-REACTION-FRAME",)),
        _p("RETENTION-LEFT-PIVOT-PIN", "Left retention pivot pin", SYSTEM_STRUCTURE_RETENTION, OWNER_CELL_3, 1, ROLE_RETENTION, MATURITY_UNRESOLVED_REQUIRED, "legacy-port-required-from-PR63", H_DRY, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, PROTOTYPE_PRINT_MACHINE, PROCESS_STRUCTURAL_CARRIER_TBD, 82, ("MASCK_ONE-DFM-RETENTION-HALO-LEFT",)),
        _p("LATCH-SOCKET-GUIDE", "Right quick-release socket and guide body", SYSTEM_STRUCTURE_RETENTION, OWNER_CELL_3, 1, ROLE_LATCH, MATURITY_UNRESOLVED_REQUIRED, "active-candidate-PR71-not-released", H_DRY, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, PROTOTYPE_PRINT_MACHINE, PROCESS_STRUCTURAL_CARRIER_TBD, 82, ("MASCK_ONE-DFM-RETENTION-HALO-RIGHT-TONGUE",)),
        _p("LATCH-SLIDER-GRIP", "Right quick-release slider and pull grip", SYSTEM_STRUCTURE_RETENTION, OWNER_CELL_3, 1, ROLE_LATCH, MATURITY_UNRESOLVED_REQUIRED, "active-candidate-PR71-not-released", H_DRY, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, PROTOTYPE_PRINT_MACHINE, PROCESS_STRUCTURAL_CARRIER_TBD, 84, ("MASCK_ONE-DFM-LATCH-SOCKET-GUIDE",)),
        _p("LATCH-CAPTURE-PIN", "Right quick-release transverse capture pin", SYSTEM_STRUCTURE_RETENTION, OWNER_CELL_3, 1, ROLE_LATCH, MATURITY_UNRESOLVED_REQUIRED, "active-candidate-PR71-not-released", H_DRY, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, PROTOTYPE_PRINT_MACHINE, PROCESS_STRUCTURAL_CARRIER_TBD, 84, ("MASCK_ONE-DFM-LATCH-SOCKET-GUIDE",)),
        _p("LATCH-GUIDE-CLOSURE", "Quick-release guide closure and flexure retainer", SYSTEM_STRUCTURE_RETENTION, OWNER_CELL_3, 1, ROLE_COVER, MATURITY_UNRESOLVED_REQUIRED, "dfm-required-split-for-nonteleporting-latch-assembly", H_DRY, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_STRUCTURAL_CARRIER_TBD, 86, ("MASCK_ONE-DFM-LATCH-SLIDER-GRIP", "MASCK_ONE-DFM-LATCH-CAPTURE-PIN"), "POSITIVE_RETAINED_GUIDE_CLOSURE_REQUIRED_AFTER_SLIDER_INSERTION"),
        _p("ACTUATOR-CARRIER", "Removable actuator carrier or collar", SYSTEM_ACTUATION, OWNER_CELL_3, 4, ROLE_CARRIER, MATURITY_UNRESOLVED_REQUIRED, "legacy-port-required-from-PR63", H_SEALED, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_STRUCTURAL_CARRIER_TBD, 40, ("MASCK_ONE-DFM-REACTION-FRAME",)),
        _p("ACTUATOR-PACKAGE", "Actuator package", SYSTEM_ACTUATION, OWNER_CELL_3, 4, ROLE_PURCHASED_PACKAGE, MATURITY_RELEASED_ENVELOPE, "src/masck_one/model.py:actuator_envelope_1..4", H_SEALED, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PURCHASED, PROCESS_PURCHASED_REFERENCE, 42, ("MASCK_ONE-DFM-ACTUATOR-CARRIER",)),
        _p("ACTUATOR-REACTION-SHOE", "Actuator reaction shoe and hard-stop interface", SYSTEM_ACTUATION, OWNER_CELL_3, 4, ROLE_CARRIER, MATURITY_UNRESOLVED_REQUIRED, "legacy-port-required-from-PR63", H_SEALED, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_STRUCTURAL_CARRIER_TBD, 44, ("MASCK_ONE-DFM-ACTUATOR-PACKAGE",)),
        _p("WATER-RESERVOIR-BODY", "Fresh-water reservoir body", SYSTEM_FRESH_FLUID, OWNER_CELL_4, 1, ROLE_RESERVOIR, MATURITY_UNRESOLVED_REQUIRED, "current-main-envelope-plus-active-candidate-reservoir", H_WET_REMOVABLE, SERVICE_USER_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 50, ("MASCK_ONE-DFM-REACTION-FRAME",), hygiene_provenance="CURRENT_WATER_ARCHITECTURE_EXPLICIT_WET_REMOVABLE"),
        _p("WATER-RESERVOIR-LID-SEAL", "Fresh-water reservoir lid seal", SYSTEM_FRESH_FLUID, OWNER_CELL_4, 1, ROLE_SEAL, MATURITY_UNRESOLVED_REQUIRED, "water-reservoir-seal-geometry-unresolved", H_WET_REMOVABLE, SERVICE_USER_REMOVABLE, PATH_REQUIRED, PROTOTYPE_SOFT_TOOL, PROCESS_SEAL_TBD, 52, ("MASCK_ONE-DFM-WATER-RESERVOIR-BODY",), "CONTROLLED_SEAL_LAND_AND_COMPRESSION_GEOMETRY_REQUIRED", "CURRENT_WATER_ARCHITECTURE_REQUIRES_SEAL_WET_REMOVABLE_CLASS_PROVISIONAL"),
        _p("WATER-PICKUP-CONNECTOR", "Fresh-water pickup connector or fitting", SYSTEM_FRESH_FLUID, OWNER_CELL_4, 1, ROLE_CONNECTOR, MATURITY_UNRESOLVED_REQUIRED, "water-pickup-connector-reservation-only", H_WET_REMOVABLE, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PURCHASED, PROCESS_PURCHASED_REFERENCE, 53, ("MASCK_ONE-DFM-WATER-RESERVOIR-BODY",), "POSITIVE_RETAINED_PICKUP_CONNECTION_AND_SEAL_INTERFACE_REQUIRED"),
        _p("WATER-RESERVOIR-LID", "Fresh-water reservoir lid", SYSTEM_FRESH_FLUID, OWNER_CELL_4, 1, ROLE_COVER, MATURITY_UNRESOLVED_REQUIRED, "current-main-envelope-plus-active-candidate-reservoir", H_WET_REMOVABLE, SERVICE_USER_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 54, ("MASCK_ONE-DFM-WATER-RESERVOIR-BODY", "MASCK_ONE-DFM-WATER-RESERVOIR-LID-SEAL"), "POSITIVE_USER_RETAINED_LID_REQUIRED"),
        _p("WATER-FILL-SEAL", "Fresh-water fill closure seal", SYSTEM_FRESH_FLUID, OWNER_CELL_4, 1, ROLE_SEAL, MATURITY_UNRESOLVED_REQUIRED, "water-fill-closure-reservation-no-seal-selected", H_WET_REMOVABLE, SERVICE_USER_REMOVABLE, PATH_REQUIRED, PROTOTYPE_SOFT_TOOL, PROCESS_SEAL_TBD, 55, ("MASCK_ONE-DFM-WATER-RESERVOIR-LID",), "CONTROLLED_FILL_SEAL_LAND_AND_COMPRESSION_REQUIRED"),
        _p("WATER-VENT-BARRIER", "Fresh-water vent liquid-barrier element", SYSTEM_FRESH_FLUID, OWNER_CELL_4, 1, ROLE_SEAL, MATURITY_UNRESOLVED_REQUIRED, "water-vent-barrier-reservation-no-hardware-selected", H_WET_REMOVABLE, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PURCHASED, PROCESS_PURCHASED_REFERENCE, 55, ("MASCK_ONE-DFM-WATER-RESERVOIR-LID",), "VENT_BARRIER_RETENTION_AND_SEAL_INTERFACE_REQUIRED"),
        _p("WATER-FILL-CLOSURE", "Fresh-water user fill closure", SYSTEM_FRESH_FLUID, OWNER_CELL_4, 1, ROLE_COVER, MATURITY_UNRESOLVED_REQUIRED, "water-fill-closure-reservation-no-hardware-selected", H_WET_REMOVABLE, SERVICE_USER_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 56, ("MASCK_ONE-DFM-WATER-FILL-SEAL",), "POSITIVE_USER_RETAINED_FILL_CLOSURE_REQUIRED"),
        _p("CLEANSER-RESERVOIR-BODY", "Cleanser reservoir body", SYSTEM_FRESH_FLUID, OWNER_CELL_4, 1, ROLE_RESERVOIR, MATURITY_RELEASED_TOPOLOGY, "src/masck_one/cleanser_storage.py", H_WET_REMOVABLE, SERVICE_USER_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 50, ("MASCK_ONE-DFM-REACTION-FRAME",)),
        _p("CLEANSER-RESERVOIR-SEAL", "Cleanser reservoir closure seal", SYSTEM_FRESH_FLUID, OWNER_CELL_4, 1, ROLE_SEAL, MATURITY_UNRESOLVED_REQUIRED, "src/masck_one/cleanser_storage.py:seal-unresolved", H_WET_REMOVABLE, SERVICE_USER_REMOVABLE, PATH_REQUIRED, PROTOTYPE_SOFT_TOOL, PROCESS_SEAL_TBD, 52, ("MASCK_ONE-DFM-CLEANSER-RESERVOIR-BODY",), "CONTROLLED_SEAL_LAND_AND_COMPRESSION_GEOMETRY_REQUIRED"),
        _p("CLEANSER-RESERVOIR-CLOSURE", "Cleanser reservoir closure", SYSTEM_FRESH_FLUID, OWNER_CELL_4, 1, ROLE_COVER, MATURITY_UNRESOLVED_REQUIRED, "src/masck_one/cleanser_storage.py:closure-unresolved", H_WET_REMOVABLE, SERVICE_USER_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 54, ("MASCK_ONE-DFM-CLEANSER-RESERVOIR-BODY", "MASCK_ONE-DFM-CLEANSER-RESERVOIR-SEAL"), "POSITIVE_USER_RETAINED_CLOSURE_REQUIRED"),
        _p("FRESH-MANIFOLD-BODY", "Fresh-water and cleanser distribution manifold body", SYSTEM_FRESH_FLUID, OWNER_CELL_4, 1, ROLE_MANIFOLD, MATURITY_RELEASED_TOPOLOGY, "src/masck_one/distribution_manifold.py", H_WET_DRAINABLE, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 57, ("MASCK_ONE-DFM-REACTION-FRAME",)),
        _p("FRESH-MANIFOLD-COVER-SEAL", "Fresh manifold closure and seal set", SYSTEM_FRESH_FLUID, OWNER_CELL_4, 1, ROLE_SEAL, MATURITY_UNRESOLVED_REQUIRED, "distribution-manifold-closure-geometry-unresolved", H_WET_DRAINABLE, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_SOFT_TOOL, PROCESS_SEAL_TBD, 59, ("MASCK_ONE-DFM-FRESH-MANIFOLD-BODY",), "MANIFOLD_CLOSURE_MUST_RETAIN_SEAL_AND_ALLOW_ASSEMBLY_WITHOUT_TELEPORTATION"),
        _p("ROUTE-CARRIER-CLIP-SET", "Fluid-route carrier and clip set", SYSTEM_FRESH_FLUID, OWNER_CELL_4, 1, ROLE_CARRIER, MATURITY_UNRESOLVED_REQUIRED, "route-retention-geometry-unresolved", H_WET_DRAINABLE, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 59, ("MASCK_ONE-DFM-REACTION-FRAME",)),
        _p("FRESH-ROUTE-SET", "Fresh-water and cleanser route set", SYSTEM_FRESH_FLUID, OWNER_CELL_4, 2, ROLE_ROUTE, MATURITY_RELEASED_TOPOLOGY, "src/masck_one/distribution_geometry.py", H_WET_DRAINABLE, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_FLEXIBLE_ROUTE, PROCESS_FLEXIBLE_ROUTE_TBD, 61, ("MASCK_ONE-DFM-FRESH-MANIFOLD-BODY", "MASCK_ONE-DFM-ROUTE-CARRIER-CLIP-SET")),
        _p("WASTE-BACKBONE-ROUTE-SET", "Mixed-waste backbone route set", SYSTEM_WASTE, OWNER_CELL_4, 1, ROLE_ROUTE, MATURITY_RELEASED_TOPOLOGY, "src/masck_one/waste_pump_architecture.py", H_WET_DRAINABLE, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_FLEXIBLE_ROUTE, PROCESS_FLEXIBLE_ROUTE_TBD, 62, ("MASCK_ONE-DFM-ROUTE-CARRIER-CLIP-SET",)),
        _p("PASSIVE-BACKFLOW-BARRIER", "Passive waste backflow barrier package", SYSTEM_WASTE, OWNER_CELL_4, 1, ROLE_PURCHASED_PACKAGE, MATURITY_RELEASED_TOPOLOGY, "src/masck_one/waste_pump_architecture.py:passive-barrier", H_WET_DRAINABLE, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PURCHASED, PROCESS_PURCHASED_REFERENCE, 64, ("MASCK_ONE-DFM-WASTE-BACKBONE-ROUTE-SET",)),
        _p("WASTE-CARTRIDGE-CARRIER", "Waste cartridge receiver and carrier", SYSTEM_WASTE, OWNER_CELL_4, 1, ROLE_CARRIER, MATURITY_UNRESOLVED_REQUIRED, "src/masck_one/waste_cartridge.py:retention-region-only", H_WET_DRAINABLE, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 66, ("MASCK_ONE-DFM-REACTION-FRAME",)),
        _p("WASTE-CARTRIDGE-BODY", "Removable waste cartridge body", SYSTEM_WASTE, OWNER_CELL_4, 1, ROLE_CARTRIDGE, MATURITY_RELEASED_ENVELOPE, "src/masck_one/model.py:waste_cartridge_envelope", H_WET_REMOVABLE, SERVICE_CONSUMABLE_REPLACEABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 68, ("MASCK_ONE-DFM-WASTE-CARTRIDGE-CARRIER",)),
        _p("WASTE-CARTRIDGE-SEAL-KEY", "Waste cartridge seal and key set", SYSTEM_WASTE, OWNER_CELL_4, 1, ROLE_SEAL, MATURITY_UNRESOLVED_REQUIRED, "src/masck_one/waste_cartridge.py:key-seal-trajectory-unresolved", H_WET_REMOVABLE, SERVICE_CONSUMABLE_REPLACEABLE, PATH_REQUIRED, PROTOTYPE_SOFT_TOOL, PROCESS_SEAL_TBD, 69, ("MASCK_ONE-DFM-WASTE-CARTRIDGE-BODY",), "KEY_GEOMETRY_SEAL_LAND_AND_COMPRESSION_REQUIRED_BEFORE_SERVICE_CLOSURE"),
        _p("WASTE-CARTRIDGE-CLOSURE", "Waste cartridge closure or service lid", SYSTEM_WASTE, OWNER_CELL_4, 1, ROLE_COVER, MATURITY_UNRESOLVED_REQUIRED, "src/masck_one/waste_cartridge.py:service-geometry-unresolved", H_WET_REMOVABLE, SERVICE_CONSUMABLE_REPLACEABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 70, ("MASCK_ONE-DFM-WASTE-CARTRIDGE-BODY", "MASCK_ONE-DFM-WASTE-CARTRIDGE-SEAL-KEY"), "POSITIVE_RETENTION_AND_NON_MISINSERTION_CLOSURE_REQUIRED"),
        _p("DRY-BAY-HOUSING", "Electronics dry-bay housing", SYSTEM_ELECTRICAL_HMI, OWNER_CELL_4, 1, ROLE_HOUSING, MATURITY_UNRESOLVED_REQUIRED, "src/masck_one/structural_frame.py:HMI_ELECTRONICS_RESERVATION", H_SEALED, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 30, ("MASCK_ONE-DFM-REACTION-FRAME",)),
        _p("BATTERY-CARRIER", "Non-compressive battery carrier", SYSTEM_ELECTRICAL_HMI, OWNER_CELL_4, 1, ROLE_CARRIER, MATURITY_UNRESOLVED_REQUIRED, "portable-donor-PR64-must-be-rebound", H_SEALED, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 32, ("MASCK_ONE-DFM-REACTION-FRAME",)),
        _p("BATTERY-PACKAGE", "Battery package benchmark", SYSTEM_ELECTRICAL_HMI, OWNER_CELL_4, 1, ROLE_PURCHASED_PACKAGE, MATURITY_RELEASED_ENVELOPE, "config/masck_one_authority.yaml:battery_reference", H_SEALED, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PURCHASED, PROCESS_PURCHASED_REFERENCE, 34, ("MASCK_ONE-DFM-BATTERY-CARRIER",)),
        _p("PCB-CARRIER", "Control and power PCB carrier", SYSTEM_ELECTRICAL_HMI, OWNER_CELL_4, 1, ROLE_CARRIER, MATURITY_UNRESOLVED_REQUIRED, "portable-donor-PR64-must-be-rebound", H_SEALED, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 36, ("MASCK_ONE-DFM-DRY-BAY-HOUSING",)),
        _p("PCB-ASSEMBLY", "Control and power PCB assembly", SYSTEM_ELECTRICAL_HMI, OWNER_CELL_4, 1, ROLE_ELECTRICAL, MATURITY_UNRESOLVED_REQUIRED, "src/masck_one/structural_frame.py:HMI_ELECTRONICS_RESERVATION", H_SEALED, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_ELECTRONICS, PROCESS_ELECTRONIC_ASSEMBLY_TBD, 38, ("MASCK_ONE-DFM-PCB-CARRIER",)),
        _p("HARNESS-SET", "Electrical harness and strain-relief set", SYSTEM_ELECTRICAL_HMI, OWNER_CELL_4, 1, ROLE_ELECTRICAL, MATURITY_UNRESOLVED_REQUIRED, "portable-donor-PR64-must-be-rebound", H_SEALED, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_ELECTRONICS, PROCESS_ELECTRONIC_ASSEMBLY_TBD, 46, ("MASCK_ONE-DFM-PCB-ASSEMBLY", "MASCK_ONE-DFM-ACTUATOR-PACKAGE")),
        _p("WET-DRY-BULKHEAD", "Wet-to-dry bulkhead and connector support", SYSTEM_ELECTRICAL_HMI, OWNER_CELL_4, 1, ROLE_SEAL, MATURITY_UNRESOLVED_REQUIRED, "src/masck_one/structural_frame.py:HMI_ELECTRONICS_RESERVATION", H_SEALED, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_SEAL_TBD, 48, ("MASCK_ONE-DFM-DRY-BAY-HOUSING",), "CONTROLLED_BULKHEAD_SEAL_AND_CONNECTOR_RETENTION_REQUIRED"),
        _p("HMI-CONTROL-MEMBRANE", "Physical HMI control membrane", SYSTEM_ELECTRICAL_HMI, OWNER_CELL_4, 1, ROLE_HMI, MATURITY_UNRESOLVED_REQUIRED, "src/masck_one/structural_frame.py:HMI_ELECTRONICS_RESERVATION", H_WET_DRAINABLE, SERVICE_NONUSER_FIXED, PATH_NOT_APPLICABLE, PROTOTYPE_SOFT_TOOL, PROCESS_SOFT_POLYMER_TBD, 74, ("MASCK_ONE-DFM-SHELL-PRIMARY", "MASCK_ONE-DFM-WET-DRY-BULKHEAD"), "HMI_SEAL_LAND_AND_CONTROL_TRAVEL_MUST_NOT_REQUIRE_BURIED_ACCESS"),
        _p("HMI-CONTROL-CAP-SET", "CLEAN/POWER/WARM/COOL control cap set", SYSTEM_ELECTRICAL_HMI, OWNER_CELL_4, 4, ROLE_HMI, MATURITY_UNRESOLVED_REQUIRED, "current-main-functions-reserved-control-geometry-unresolved", H_WET_DRAINABLE, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 76, ("MASCK_ONE-DFM-HMI-CONTROL-MEMBRANE",)),
        _p("HMI-STATUS-WINDOW", "Status-window lens or light guide", SYSTEM_ELECTRICAL_HMI, OWNER_CELL_4, 1, ROLE_HMI, MATURITY_UNRESOLVED_REQUIRED, "portable-donor-PR64-must-be-rebound", H_WET_DRAINABLE, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_PRINT_MACHINE, PROCESS_RIGID_POLYMER_TBD, 76, ("MASCK_ONE-DFM-SHELL-PRIMARY", "MASCK_ONE-DFM-WET-DRY-BULKHEAD")),
        _p("DRY-BAY-COVER-SEAL", "Dry-bay service-cover seal", SYSTEM_ELECTRICAL_HMI, OWNER_CELL_4, 1, ROLE_SEAL, MATURITY_UNRESOLVED_REQUIRED, "dry-bay-seal-geometry-unresolved", H_SEALED, SERVICE_TECHNICIAN_REMOVABLE, PATH_REQUIRED, PROTOTYPE_SOFT_TOOL, PROCESS_SEAL_TBD, 92, ("MASCK_ONE-DFM-DRY-BAY-HOUSING",), "CONTROLLED_SEAL_LAND_COMPRESSION_AND_COVER_RETENTION_REQUIRED"),
    )
    return tuple(sorted(p, key=lambda item: item.part_id))


def build_whole_product_dfm_architecture(authority: Authority | None = None, *, observed_candidates: tuple[CandidateBinding, ...] = ()) -> WholeProductDfmArchitecture:
    authority = authority or load_authority()
    if type(authority) is not Authority:
        raise DfmArchitectureError("DFM architecture requires the exact Authority type")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise DfmArchitectureError("authority revision moved and requires DFM rebind")
    manufacturing = authority.get("manufacturing")
    geometry = authority.get("geometry")
    if type(manufacturing) is not dict or type(geometry) is not dict:
        raise DfmArchitectureError("authority manufacturing and geometry mappings are required")
    rib_range = manufacturing.get("rib_thickness_ratio_range")
    hygiene = manufacturing.get("hygiene_classes")
    seam = geometry.get("visible_seam")
    if type(rib_range) is not list or len(rib_range) != 2 or type(hygiene) is not list or type(seam) is not dict:
        raise DfmArchitectureError("authority manufacturing geometry is malformed")
    rules = ManufacturingRules(manufacturing.get("mold_draft_nominal_deg"), rib_range[0], rib_range[1], seam.get("gap_mm"), seam.get("tolerance_mm"), seam.get("flush_mismatch_max_mm"), tuple(hygiene))
    return WholeProductDfmArchitecture(DFM_SCHEMA, SOURCE_MAIN_SHA, AUTHORITY_REVISION, AUTHORITY_BLOB_SHA, WORLD_FRAME_ID, rules, _build_parts(), observed_candidates, False, False, "DIGITAL_PART_SPLIT_ASSEMBLY_SERVICE_AND_PROCESS_INTENT_ONLY_NOT_TOOLING_SUPPLIER_MOLDABILITY_SEALING_DURABILITY_HYGIENE_OR_PHYSICAL_EVIDENCE")
