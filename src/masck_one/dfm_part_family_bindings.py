from __future__ import annotations

"""Current-main producer binding for the Cell 5 whole-product DFM part families.

This module does not make the stale unmerged Cell 5 PR #77 authoritative. It preserves
its 47 stable family IDs as donor taxonomy, binds each family to released-main producer
truth where such truth exists, retires stale topology/envelope semantics when released
geometry has advanced, and exposes current released subsystem identities that the
47-family donor does not yet represent.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
from pathlib import Path
import re

from .authority import Authority, load_authority

SCHEMA = "MASCK_ONE_CELL16_DFM_PART_FAMILY_PRODUCER_BINDINGS_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

BASELINE_CELL5_PR = 77
BASELINE_CELL5_HEAD_SHA = "bcade5e50854617894ffee1eee2f3a3bfc1de3bb"
BASELINE_CELL5_WHOLE_PRODUCT_DFM_BLOB_SHA = "9173205bafb2dad3052f093bc29022570880d60a"
BASELINE_FAMILY_COUNT = 47
BASELINE_STATUS = "UNMERGED_DONOR_TAXONOMY_ONLY_NOT_RELEASE_AUTHORITY"

M_UNRESOLVED = "UNRESOLVED_REQUIRED"
M_TOPOLOGY = "TOPOLOGY_ONLY"
M_CONTROLLED_ENVELOPE = "CONTROLLED_PACKAGE_REFERENCE_BREP"
M_DEVELOPMENT_REFERENCE = "DEVELOPMENT_REFERENCE_BREP"
M_REALIZED_CENTERLINE = "REALIZED_CENTERLINE_GEOMETRY"
M_REALIZED_BREP = "REALIZED_PHYSICAL_BREP"
MATURITIES = (
    M_UNRESOLVED,
    M_TOPOLOGY,
    M_CONTROLLED_ENVELOPE,
    M_DEVELOPMENT_REFERENCE,
    M_REALIZED_CENTERLINE,
    M_REALIZED_BREP,
)

ROLE_NONE = "NO_RELEASED_GEOMETRY"
ROLE_TOPOLOGY = "REFERENCE_TOPOLOGY_ONLY"
ROLE_PACKAGE_REFERENCE = "PACKAGE_REFERENCE_ONLY_NOT_PART_MATERIAL"
ROLE_DEVELOPMENT_REFERENCE = "DEVELOPMENT_REFERENCE_ONLY_NOT_PART_MATERIAL"
ROLE_CENTERLINE = "CENTERLINE_GEOMETRY_ONLY_NOT_SELECTED_ROUTE_MATERIAL"
ROLE_PHYSICAL_MATERIAL = "PHYSICAL_MATERIAL"
GEOMETRY_ROLES = (
    ROLE_NONE,
    ROLE_TOPOLOGY,
    ROLE_PACKAGE_REFERENCE,
    ROLE_DEVELOPMENT_REFERENCE,
    ROLE_CENTERLINE,
    ROLE_PHYSICAL_MATERIAL,
)

RETIRE_NONE = "NO_BASELINE_ENTRY_RETIREMENT"
RETIRE_TOPOLOGY = "RETIRE_STALE_TOPOLOGY_CLASSIFICATION"
RETIRE_ENVELOPE_SEMANTICS = "RETIRE_AMBIGUOUS_ENVELOPE_AS_PART_SEMANTICS"
RETIREMENT_KINDS = (RETIRE_NONE, RETIRE_TOPOLOGY, RETIRE_ENVELOPE_SEMANTICS)

EVIDENCE_STATUS = (
    "DIGITAL_RELEASED_SOURCE_AND_GEOMETRY_ROLE_BINDING_ONLY_NOT_TOOLING_PROCESS_SUPPLIER_"
    "MOLDABILITY_FIT_SEAL_HYGIENE_DURABILITY_OR_PHYSICAL_VALIDATION"
)

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_PART_ID = re.compile(r"^MASCK_ONE-DFM-[A-Z0-9-]+$")
_REPO_ROOT = Path(__file__).resolve().parents[2]

SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", AUTHORITY_BLOB_SHA),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/interface_topology.py", "38b7c932f71a8675d45d098ac65154f98ff8bbb5"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
    ("src/masck_one/water_reservoir.py", "6c14a37d07855550f0bd502e8308ed46682bc19c"),
    ("src/masck_one/cleanser_storage.py", "5e087ca8b05da8352ad4800b2ef8280ea8ddcf29"),
    ("src/masck_one/fresh_pump_packaging.py", "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4"),
    ("src/masck_one/distribution_manifold.py", "8f2a6c784b51734aba4d1f3809015707fc328405"),
    ("src/masck_one/distribution_geometry.py", "d2dd8b47bb6a2aa1edf57ac0632778228add7997"),
    ("src/masck_one/realized_waste_backbone.py", "6aa79d9a613e278f32da85b4654c0e35cc09b7ca"),
    ("src/masck_one/waste_pump_architecture.py", "ace02ee529070465b11832f475771125636312cb"),
    ("src/masck_one/waste_pump_packaging.py", "43587520a8c6cdc9ca8cfe362d2aac9589364fdc"),
    ("src/masck_one/waste_cartridge.py", "9dc0fe8a0ed92083c68406da3993e57e767e2483"),
    ("src/masck_one/waste_cartridge_dfm.py", "f9788cce30c14600c8a624509153596e46c1e478"),
)
SOURCE_BLOB_BY_PATH = dict(SOURCE_GIT_BLOB_IDENTITIES)

BASELINE_PART_IDS = tuple(
    sorted(
        f"MASCK_ONE-DFM-{suffix}"
        for suffix in (
            "SHELL-PRIMARY",
            "FACIAL-INTERFACE-CARRIER",
            "NASAL-LOBE-MEMBRANE",
            "REAR-SERVICE-COVER",
            "REACTION-FRAME",
            "RETENTION-HALO-LEFT",
            "RETENTION-HALO-RIGHT-TONGUE",
            "RETENTION-LEFT-PIVOT-PIN",
            "LATCH-SOCKET-GUIDE",
            "LATCH-SLIDER-GRIP",
            "LATCH-CAPTURE-PIN",
            "LATCH-GUIDE-CLOSURE",
            "ACTUATOR-CARRIER",
            "ACTUATOR-PACKAGE",
            "ACTUATOR-REACTION-SHOE",
            "WATER-RESERVOIR-BODY",
            "WATER-RESERVOIR-LID-SEAL",
            "WATER-PICKUP-CONNECTOR",
            "WATER-RESERVOIR-LID",
            "WATER-LID-RETENTION-KEY",
            "WATER-FILL-SEAL",
            "WATER-VENT-BARRIER",
            "WATER-FILL-CLOSURE",
            "CLEANSER-RESERVOIR-BODY",
            "CLEANSER-RESERVOIR-SEAL",
            "CLEANSER-RESERVOIR-CLOSURE",
            "FRESH-MANIFOLD-BODY",
            "FRESH-MANIFOLD-COVER-SEAL",
            "ROUTE-CARRIER-CLIP-SET",
            "FRESH-ROUTE-SET",
            "WASTE-BACKBONE-ROUTE-SET",
            "PASSIVE-BACKFLOW-BARRIER",
            "WASTE-CARTRIDGE-CARRIER",
            "WASTE-CARTRIDGE-BODY",
            "WASTE-CARTRIDGE-SEAL-KEY",
            "WASTE-CARTRIDGE-CLOSURE",
            "DRY-BAY-HOUSING",
            "BATTERY-CARRIER",
            "BATTERY-PACKAGE",
            "PCB-CARRIER",
            "PCB-ASSEMBLY",
            "HARNESS-SET",
            "WET-DRY-BULKHEAD",
            "HMI-CONTROL-MEMBRANE",
            "HMI-CONTROL-CAP-SET",
            "HMI-STATUS-WINDOW",
            "DRY-BAY-COVER-SEAL",
        )
    )
)

BASELINE_MATURITY_OVERRIDES = {
    "MASCK_ONE-DFM-SHELL-PRIMARY": "RELEASED_GEOMETRY",
    "MASCK_ONE-DFM-FACIAL-INTERFACE-CARRIER": "RELEASED_TOPOLOGY",
    "MASCK_ONE-DFM-NASAL-LOBE-MEMBRANE": "DEVELOPMENT_REFERENCE",
    "MASCK_ONE-DFM-REACTION-FRAME": "RELEASED_TOPOLOGY",
    "MASCK_ONE-DFM-ACTUATOR-PACKAGE": "RELEASED_ENVELOPE",
    "MASCK_ONE-DFM-CLEANSER-RESERVOIR-BODY": "RELEASED_TOPOLOGY",
    "MASCK_ONE-DFM-FRESH-MANIFOLD-BODY": "RELEASED_TOPOLOGY",
    "MASCK_ONE-DFM-FRESH-ROUTE-SET": "RELEASED_TOPOLOGY",
    "MASCK_ONE-DFM-WASTE-BACKBONE-ROUTE-SET": "RELEASED_TOPOLOGY",
    "MASCK_ONE-DFM-PASSIVE-BACKFLOW-BARRIER": "RELEASED_TOPOLOGY",
    "MASCK_ONE-DFM-WASTE-CARTRIDGE-BODY": "RELEASED_ENVELOPE",
    "MASCK_ONE-DFM-BATTERY-PACKAGE": "RELEASED_ENVELOPE",
}

# Only released-main producers appear here. Candidate PRs and legacy Manual A/B are
# intentionally absent even when their geometry is useful review evidence.
CURRENT_BINDING_OVERRIDES: dict[str, tuple[str, str | None, str, bool, str, str]] = {
    "MASCK_ONE-DFM-SHELL-PRIMARY": (
        M_REALIZED_BREP, "src/masck_one/model.py", ROLE_PHYSICAL_MATERIAL, True, RETIRE_NONE,
        "Current released rigid_shell B-rep is physical development material. Production tooling remains unvalidated.",
    ),
    "MASCK_ONE-DFM-FACIAL-INTERFACE-CARRIER": (
        M_TOPOLOGY, "src/masck_one/interface_topology.py", ROLE_TOPOLOGY, False, RETIRE_NONE,
        "Released compliant-interface topology has no final carrier B-rep.",
    ),
    "MASCK_ONE-DFM-NASAL-LOBE-MEMBRANE": (
        M_DEVELOPMENT_REFERENCE, "src/masck_one/model.py", ROLE_DEVELOPMENT_REFERENCE, False, RETIRE_NONE,
        "Released nasal-lobe solid is explicitly a local-thickness development reference, not production membrane material.",
    ),
    "MASCK_ONE-DFM-REACTION-FRAME": (
        M_TOPOLOGY, "src/masck_one/structural_frame.py", ROLE_TOPOLOGY, False, RETIRE_NONE,
        "Released structural frame remains topology/datum only with unresolved 3D member geometry.",
    ),
    "MASCK_ONE-DFM-ACTUATOR-PACKAGE": (
        M_CONTROLLED_ENVELOPE, "src/masck_one/model.py", ROLE_PACKAGE_REFERENCE, False, RETIRE_NONE,
        "Four released actuator solids are supplier-size package references, not selected actuator material.",
    ),
    "MASCK_ONE-DFM-WATER-RESERVOIR-BODY": (
        M_UNRESOLVED, "src/masck_one/water_reservoir.py", ROLE_NONE, False, RETIRE_NONE,
        "Released water architecture and model package envelope do not constitute a reservoir-body B-rep.",
    ),
    "MASCK_ONE-DFM-CLEANSER-RESERVOIR-BODY": (
        M_TOPOLOGY, "src/masck_one/cleanser_storage.py", ROLE_TOPOLOGY, False, RETIRE_NONE,
        "Released cleanser storage remains architecture/topology on current main; unmerged Cell 4 geometry is not consumed.",
    ),
    "MASCK_ONE-DFM-FRESH-MANIFOLD-BODY": (
        M_TOPOLOGY, "src/masck_one/distribution_manifold.py", ROLE_TOPOLOGY, False, RETIRE_NONE,
        "Released manifold is topology only; body, cover, joins and tool access remain unrealized.",
    ),
    "MASCK_ONE-DFM-FRESH-ROUTE-SET": (
        M_TOPOLOGY, "src/masck_one/distribution_geometry.py", ROLE_TOPOLOGY, False, RETIRE_NONE,
        "Released fresh routes do not yet have world-coordinate centerline plus selected tube/channel geometry.",
    ),
    "MASCK_ONE-DFM-WASTE-BACKBONE-ROUTE-SET": (
        M_REALIZED_CENTERLINE, "src/masck_one/realized_waste_backbone.py", ROLE_CENTERLINE, False, RETIRE_TOPOLOGY,
        "PR #68 released deterministic world-coordinate mixed-waste centerlines; the PR #77 topology-only label is obsolete.",
    ),
    "MASCK_ONE-DFM-PASSIVE-BACKFLOW-BARRIER": (
        M_TOPOLOGY, "src/masck_one/waste_pump_architecture.py", ROLE_TOPOLOGY, False, RETIRE_NONE,
        "Passive backflow stage is released in route order, but no selected passive device B-rep is released.",
    ),
    "MASCK_ONE-DFM-WASTE-CARTRIDGE-CARRIER": (
        M_UNRESOLVED, "src/masck_one/waste_cartridge.py", ROLE_NONE, False, RETIRE_NONE,
        "Released cartridge architecture reserves retention requirements but has no receiver/carrier material geometry.",
    ),
    "MASCK_ONE-DFM-WASTE-CARTRIDGE-BODY": (
        M_CONTROLLED_ENVELOPE, "src/masck_one/waste_cartridge_dfm.py", ROLE_PACKAGE_REFERENCE, False,
        RETIRE_ENVELOPE_SEMANTICS,
        "Merged PR #95 proves the 74 x 36 x 20 mm solid is package reference only and explicitly excludes it from physical assembly material.",
    ),
    "MASCK_ONE-DFM-BATTERY-PACKAGE": (
        M_CONTROLLED_ENVELOPE, "config/masck_one_authority.yaml", ROLE_PACKAGE_REFERENCE, False, RETIRE_NONE,
        "Authority battery is a packaging benchmark only, not production-qualified battery material.",
    ),
}

SUCCESSOR_REQUIRED_FAMILIES: tuple[tuple[str, str, str], ...] = (
    (
        "MASCK_ONE-DFM-WATER-PUMP-PACKAGE",
        "src/masck_one/fresh_pump_packaging.py",
        "Released PUMP-STATION-WATER identity exists but the 47-family donor has no distinct water-pump family.",
    ),
    (
        "MASCK_ONE-DFM-CLEANSER-PUMP-PACKAGE",
        "src/masck_one/fresh_pump_packaging.py",
        "Released PUMP-STATION-CLEANSER identity exists but the 47-family donor has no distinct cleanser-pump family.",
    ),
    (
        "MASCK_ONE-DFM-WASTE-PUMP-PACKAGE",
        "src/masck_one/waste_pump_architecture.py",
        "Released waste-pump station exists in the mixed-waste graph but the 47-family donor has no distinct waste-pump family.",
    ),
)


class DfmPartFamilyBindingError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_source_files_current() -> None:
    for relative_path, expected in SOURCE_GIT_BLOB_IDENTITIES:
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise DfmPartFamilyBindingError(f"DFM producer source is missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise DfmPartFamilyBindingError(
                f"DFM producer source moved at {relative_path}; expected {expected}, got {actual}"
            )


@dataclass(frozen=True, slots=True)
class ProducerBinding:
    part_id: str
    baseline_maturity: str
    current_maturity: str
    source_path: str | None
    source_blob_sha: str | None
    geometry_role: str
    physical_material_eligible: bool
    retirement_kind: str
    rationale: str
    evidence_status: str = "DIGITAL_PRODUCER_BINDING_ONLY"

    def __post_init__(self) -> None:
        if type(self.part_id) is not str or _PART_ID.fullmatch(self.part_id) is None:
            raise DfmPartFamilyBindingError("part ID must use the controlled MASCK_ONE-DFM namespace")
        if self.current_maturity not in MATURITIES or self.geometry_role not in GEOMETRY_ROLES:
            raise DfmPartFamilyBindingError("uncontrolled current maturity or geometry role")
        if self.retirement_kind not in RETIREMENT_KINDS:
            raise DfmPartFamilyBindingError("uncontrolled baseline retirement kind")
        if type(self.physical_material_eligible) is not bool:
            raise DfmPartFamilyBindingError("physical material eligibility must be exact bool")
        if type(self.rationale) is not str or not self.rationale.strip() or self.rationale != self.rationale.strip():
            raise DfmPartFamilyBindingError("producer-binding rationale must be exact nonblank text")
        if self.source_path is None:
            if self.source_blob_sha is not None:
                raise DfmPartFamilyBindingError("unresolved family cannot carry a source blob without a source path")
        else:
            expected = SOURCE_BLOB_BY_PATH.get(self.source_path)
            if expected is None or self.source_blob_sha != expected or _SHA40.fullmatch(self.source_blob_sha or "") is None:
                raise DfmPartFamilyBindingError("producer binding must use an exact released source path/blob pair")
        if self.physical_material_eligible:
            if self.current_maturity != M_REALIZED_BREP or self.geometry_role != ROLE_PHYSICAL_MATERIAL:
                raise DfmPartFamilyBindingError("only realized physical B-rep may be physical material eligible")
        elif self.geometry_role == ROLE_PHYSICAL_MATERIAL:
            raise DfmPartFamilyBindingError("physical material role requires exact material eligibility")
        if self.current_maturity in (M_UNRESOLVED, M_TOPOLOGY) and self.physical_material_eligible:
            raise DfmPartFamilyBindingError("topology or unresolved families cannot enter physical material")
        if self.geometry_role in (ROLE_PACKAGE_REFERENCE, ROLE_DEVELOPMENT_REFERENCE, ROLE_CENTERLINE, ROLE_TOPOLOGY):
            if self.physical_material_eligible:
                raise DfmPartFamilyBindingError("reference/topology/centerline geometry cannot enter physical material")
        if self.evidence_status != "DIGITAL_PRODUCER_BINDING_ONLY":
            raise DfmPartFamilyBindingError("producer binding cannot imply physical or production validation")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "part_id": self.part_id,
            "baseline_maturity": self.baseline_maturity,
            "current_maturity": self.current_maturity,
            "source_path": self.source_path,
            "source_blob_sha": self.source_blob_sha,
            "geometry_role": self.geometry_role,
            "physical_material_eligible": self.physical_material_eligible,
            "retirement_kind": self.retirement_kind,
            "rationale": self.rationale,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class SuccessorFamilyRequirement:
    part_id: str
    source_path: str
    source_blob_sha: str
    current_maturity: str
    rationale: str
    evidence_status: str = "CURRENT_RELEASED_SUBSYSTEM_IDENTITY_REQUIRES_SUCCESSOR_DFM_FAMILY"

    def __post_init__(self) -> None:
        if type(self.part_id) is not str or _PART_ID.fullmatch(self.part_id) is None:
            raise DfmPartFamilyBindingError("successor part ID must use the controlled MASCK_ONE-DFM namespace")
        expected = SOURCE_BLOB_BY_PATH.get(self.source_path)
        if expected is None or self.source_blob_sha != expected:
            raise DfmPartFamilyBindingError("successor family must bind exact released producer source")
        if self.current_maturity != M_TOPOLOGY:
            raise DfmPartFamilyBindingError("current pump successor families must remain topology only")
        if type(self.rationale) is not str or not self.rationale.strip():
            raise DfmPartFamilyBindingError("successor-family rationale must be nonblank")
        if self.evidence_status != "CURRENT_RELEASED_SUBSYSTEM_IDENTITY_REQUIRES_SUCCESSOR_DFM_FAMILY":
            raise DfmPartFamilyBindingError("successor family cannot imply realized geometry")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "part_id": self.part_id,
            "source_path": self.source_path,
            "source_blob_sha": self.source_blob_sha,
            "current_maturity": self.current_maturity,
            "rationale": self.rationale,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class DfmPartFamilyProducerAudit:
    schema: str
    source_main_sha: str
    authority_revision: str
    authority_blob_sha: str
    coordinate_frame_id: str
    baseline_cell5_pr: int
    baseline_cell5_head_sha: str
    baseline_cell5_whole_product_dfm_blob_sha: str
    baseline_status: str
    bindings: tuple[ProducerBinding, ...]
    successor_required_families: tuple[SuccessorFamilyRequirement, ...]
    physical_validation_eligible: bool
    production_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.schema != SCHEMA or self.source_main_sha != SOURCE_MAIN_SHA:
            raise DfmPartFamilyBindingError("DFM producer audit is stale for released main")
        if self.authority_revision != AUTHORITY_REVISION or self.authority_blob_sha != AUTHORITY_BLOB_SHA:
            raise DfmPartFamilyBindingError("DFM producer audit authority identity moved")
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise DfmPartFamilyBindingError("DFM producer audit must use canonical authority world frame")
        if self.baseline_cell5_pr != BASELINE_CELL5_PR:
            raise DfmPartFamilyBindingError("unexpected Cell 5 donor PR")
        for value in (self.baseline_cell5_head_sha, self.baseline_cell5_whole_product_dfm_blob_sha):
            if type(value) is not str or _SHA40.fullmatch(value) is None:
                raise DfmPartFamilyBindingError("Cell 5 donor provenance must be canonical 40-hex")
        if self.baseline_status != BASELINE_STATUS:
            raise DfmPartFamilyBindingError("unmerged Cell 5 donor cannot become release authority")
        if type(self.bindings) is not tuple or len(self.bindings) != BASELINE_FAMILY_COUNT:
            raise DfmPartFamilyBindingError("producer audit must map all 47 Cell 5 donor family IDs")
        ids = tuple(binding.part_id for binding in self.bindings)
        if ids != BASELINE_PART_IDS or len(set(ids)) != BASELINE_FAMILY_COUNT:
            raise DfmPartFamilyBindingError("producer audit family identity/order changed")
        for binding in self.bindings:
            binding.__post_init__()
        successor_ids = tuple(item.part_id for item in self.successor_required_families)
        if len(successor_ids) != 3 or len(set(successor_ids)) != 3 or any(item in BASELINE_PART_IDS for item in successor_ids):
            raise DfmPartFamilyBindingError("successor family requirements must be three unique additions to the donor taxonomy")
        for item in self.successor_required_families:
            item.__post_init__()
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise DfmPartFamilyBindingError("digital producer audit cannot be physical validation")
        if type(self.production_validation_eligible) is not bool or self.production_validation_eligible:
            raise DfmPartFamilyBindingError("digital producer audit cannot validate production tooling/capability")
        if self.evidence_status != EVIDENCE_STATUS:
            raise DfmPartFamilyBindingError("DFM producer evidence firewall changed")
        if self.physical_material_part_ids != ("MASCK_ONE-DFM-SHELL-PRIMARY",):
            raise DfmPartFamilyBindingError("current DFM producer truth must not classify package/reference geometry as part material")
        if self.retired_baseline_entry_ids != (
            "MASCK_ONE-DFM-WASTE-BACKBONE-ROUTE-SET",
            "MASCK_ONE-DFM-WASTE-CARTRIDGE-BODY",
        ):
            raise DfmPartFamilyBindingError("current baseline retirement set changed and requires explicit rebind")

    @property
    def physical_material_part_ids(self) -> tuple[str, ...]:
        return tuple(item.part_id for item in self.bindings if item.physical_material_eligible)

    @property
    def retired_baseline_entry_ids(self) -> tuple[str, ...]:
        return tuple(item.part_id for item in self.bindings if item.retirement_kind != RETIRE_NONE)

    @property
    def unresolved_part_ids(self) -> tuple[str, ...]:
        return tuple(item.part_id for item in self.bindings if item.current_maturity == M_UNRESOLVED)

    @property
    def successor_architecture_required(self) -> bool:
        return bool(self.successor_required_families)

    @property
    def digital_mvp_part_architecture_ready(self) -> bool:
        return not self.unresolved_part_ids and not self.successor_architecture_required

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": self.schema,
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "coordinate_frame_id": self.coordinate_frame_id,
            "baseline_cell5_pr": self.baseline_cell5_pr,
            "baseline_cell5_head_sha": self.baseline_cell5_head_sha,
            "baseline_cell5_whole_product_dfm_blob_sha": self.baseline_cell5_whole_product_dfm_blob_sha,
            "baseline_status": self.baseline_status,
            "baseline_family_count": BASELINE_FAMILY_COUNT,
            "bindings": [item.manifest() for item in self.bindings],
            "retired_baseline_entry_ids": list(self.retired_baseline_entry_ids),
            "physical_material_part_ids": list(self.physical_material_part_ids),
            "unresolved_part_ids": list(self.unresolved_part_ids),
            "successor_required_families": [item.manifest() for item in self.successor_required_families],
            "successor_architecture_required": self.successor_architecture_required,
            "digital_mvp_part_architecture_ready": self.digital_mvp_part_architecture_ready,
            "physical_validation_eligible": self.physical_validation_eligible,
            "production_validation_eligible": self.production_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["manifest_sha256"] = sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            ).hexdigest()
        return payload

    @property
    def manifest_sha256(self) -> str:
        return str(self.manifest()["manifest_sha256"])


def _build_binding(part_id: str) -> ProducerBinding:
    baseline_maturity = BASELINE_MATURITY_OVERRIDES.get(part_id, "UNRESOLVED_REQUIRED")
    current = CURRENT_BINDING_OVERRIDES.get(part_id)
    if current is None:
        return ProducerBinding(
            part_id,
            baseline_maturity,
            M_UNRESOLVED,
            None,
            None,
            ROLE_NONE,
            False,
            RETIRE_NONE,
            "No released-main physical producer geometry currently satisfies this manufacturing family.",
        )
    maturity, source_path, role, material, retirement, rationale = current
    source_blob = SOURCE_BLOB_BY_PATH[source_path] if source_path is not None else None
    return ProducerBinding(
        part_id,
        baseline_maturity,
        maturity,
        source_path,
        source_blob,
        role,
        material,
        retirement,
        rationale,
    )


def build_dfm_part_family_producer_audit(authority: Authority | None = None) -> DfmPartFamilyProducerAudit:
    _require_source_files_current()
    authority = authority or load_authority()
    if type(authority) is not Authority:
        raise DfmPartFamilyBindingError("DFM producer audit requires exact Authority type")
    canonical = load_authority()
    if authority.data != canonical.data:
        raise DfmPartFamilyBindingError("supplied authority differs from released machine authority")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise DfmPartFamilyBindingError("authority revision moved and requires DFM producer rebind")

    manufacturing = authority.get("manufacturing")
    seam = authority.get("geometry", "visible_seam")
    if type(manufacturing) is not dict or type(seam) is not dict:
        raise DfmPartFamilyBindingError("authority manufacturing/seam rules are malformed")
    if float(manufacturing.get("mold_draft_nominal_deg")) != 1.0:
        raise DfmPartFamilyBindingError("authority nominal mold draft moved")
    if tuple(float(v) for v in manufacturing.get("rib_thickness_ratio_range", ())) != (0.4, 0.6):
        raise DfmPartFamilyBindingError("authority rib ratio range moved")
    if float(seam.get("gap_mm")) != 0.4 or float(seam.get("tolerance_mm")) != 0.15:
        raise DfmPartFamilyBindingError("authority visible seam rule moved")
    if float(seam.get("flush_mismatch_max_mm")) != 0.15:
        raise DfmPartFamilyBindingError("authority flush mismatch rule moved")

    bindings = tuple(_build_binding(part_id) for part_id in BASELINE_PART_IDS)
    successor = tuple(
        SuccessorFamilyRequirement(
            part_id,
            source_path,
            SOURCE_BLOB_BY_PATH[source_path],
            M_TOPOLOGY,
            rationale,
        )
        for part_id, source_path, rationale in SUCCESSOR_REQUIRED_FAMILIES
    )
    return DfmPartFamilyProducerAudit(
        SCHEMA,
        SOURCE_MAIN_SHA,
        AUTHORITY_REVISION,
        AUTHORITY_BLOB_SHA,
        WORLD_FRAME_ID,
        BASELINE_CELL5_PR,
        BASELINE_CELL5_HEAD_SHA,
        BASELINE_CELL5_WHOLE_PRODUCT_DFM_BLOB_SHA,
        BASELINE_STATUS,
        bindings,
        successor,
        False,
        False,
        EVIDENCE_STATUS,
    )
