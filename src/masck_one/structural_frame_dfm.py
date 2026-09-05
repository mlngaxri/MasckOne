from __future__ import annotations

"""Fail-closed DFM audit for the released structural-frame maturity.

This module does not create frame geometry. It distinguishes the released Iteration-15
reaction topology from a manufacturable-in-principle frame and records the minimum
closure required before a whole-product CAD freeze can call the frame digitally ready.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
import re

from .authority import Authority, load_authority
from .boundary_release import build_verified_interface_boundary_topology
from .interface_attachment import build_interface_attachment_architecture
from .model import build_model
from .structural_frame import (
    RESERVATION_ACTUATION,
    RESERVATION_RETENTION,
    StructuralFrameTopology,
    build_structural_frame_topology,
)


SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_DFM_AUDIT_V1"
SOURCE_MAIN_SHA = "628ec5f5766937433b1bdf8f30edc372924cf41e"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
EVIDENCE_STATUS = (
    "DIGITAL_DFM_MATURITY_AND_CLOSURE_CONTRACT_ONLY_NOT_STRENGTH_STIFFNESS_FATIGUE_"
    "MOLDABILITY_TOOLING_SUPPLIER_FIT_COMFORT_OR_PHYSICAL_VALIDATION"
)

# Git blob identities from released main. These bind the topology-construction source
# graph without pretending a self-reported SOURCE_MAIN_SHA proves the checkout content.
# Any movement requires deliberate reconstruction/review of this audit.
SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/anatomy.py", "872d1e5be1b9ce9baa5b63cb53462eb7b36f40ab"),
    ("src/masck_one/authority.py", "6866e3a428dab8b32b5a1d9e58da78b8f5aa1aa2"),
    ("src/masck_one/boundary_preflight.py", "0253b61d2bb1dbf4c5377124114a1cc6bd90dfa9"),
    ("src/masck_one/boundary_release.py", "34a49eed2c521d55e48ac187c2dd33dc9e22a3e3"),
    ("src/masck_one/coverage.py", "4a8cec4d94db97e63f634a94dd8c90094f3afcb0"),
    ("src/masck_one/facial_surface.py", "764f6f65b83ac7709d959bb0f37f861c90ea2794"),
    ("src/masck_one/interface_attachment.py", "c161f99ddd3473f3b9dde30ec73397a72915191a"),
    ("src/masck_one/interface_boundaries.py", "496c9b50867ca0bb319175d1d2e47caf4bc4fb64"),
    ("src/masck_one/interface_topology.py", "38b7c932f71a8675d45d098ac65154f98ff8bbb5"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
)

REQ_FRAME_MEMBER = "FRAME_MEMBER_3D_REALIZATION"
REQ_FRAME_SHELL_JOIN = "FRAME_SHELL_JOIN_ARCHITECTURE"
REQ_TOOL_ACCESS = "FRAME_ATTACHMENT_TOOL_ACCESS"
REQ_ACTUATOR_ATTACHMENT = "ACTUATOR_REACTION_ATTACHMENT"
REQ_RETENTION_ATTACHMENT = "RETENTION_FRAME_ATTACHMENT"
REQ_ASSEMBLY_SEQUENCE = "FRAME_NONTELEPORTING_ASSEMBLY_SEQUENCE"
REQUIREMENT_IDS = (
    REQ_FRAME_MEMBER,
    REQ_FRAME_SHELL_JOIN,
    REQ_TOOL_ACCESS,
    REQ_ACTUATOR_ATTACHMENT,
    REQ_RETENTION_ATTACHMENT,
    REQ_ASSEMBLY_SEQUENCE,
)

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")


class StructuralFrameDfmError(ValueError):
    pass


def _exact_text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise StructuralFrameDfmError(f"{label} must be exact nonblank text")
    return value


def _exact_bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise StructuralFrameDfmError(f"{label} must be an exact bool")
    return value


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_released_source_blobs() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    for relative_path, expected_blob_sha in SOURCE_GIT_BLOB_IDENTITIES:
        path = repository_root / relative_path
        if not path.is_file():
            raise StructuralFrameDfmError(f"structural DFM source file is missing: {relative_path}")
        actual_blob_sha = _git_blob_sha(path)
        if actual_blob_sha != expected_blob_sha:
            raise StructuralFrameDfmError(
                f"structural DFM source moved at {relative_path}; expected {expected_blob_sha}, got {actual_blob_sha}"
            )


@dataclass(frozen=True, slots=True)
class FrameDfmRequirement:
    requirement_id: str
    severity: str
    owner: str
    current_state: str
    closure_required: str
    evidence_status: str = "DIGITAL_DFM_REQUIREMENT_ONLY"

    def __post_init__(self) -> None:
        if self.requirement_id not in REQUIREMENT_IDS:
            raise StructuralFrameDfmError("uncontrolled structural-frame DFM requirement")
        if self.severity not in {"P0", "P1"}:
            raise StructuralFrameDfmError("structural-frame DFM severity must be P0 or P1")
        for label, value in (
            ("owner", self.owner),
            ("current_state", self.current_state),
            ("closure_required", self.closure_required),
            ("evidence_status", self.evidence_status),
        ):
            _exact_text(value, label)
        if self.evidence_status != "DIGITAL_DFM_REQUIREMENT_ONLY":
            raise StructuralFrameDfmError("DFM requirement cannot imply physical validation")

    def manifest(self) -> dict[str, object]:
        return {
            "requirement_id": self.requirement_id,
            "severity": self.severity,
            "owner": self.owner,
            "current_state": self.current_state,
            "closure_required": self.closure_required,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameDfmAudit:
    schema: str
    source_main_sha: str
    authority_revision: str
    authority_blob_sha: str
    coordinate_frame_id: str
    structural_topology_sha256: str
    current_maturity: str
    mold_draft_nominal_deg: float
    rib_thickness_ratio_range: tuple[float, float]
    requirements: tuple[FrameDfmRequirement, ...]
    digital_mvp_frame_dfm_ready: bool
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise StructuralFrameDfmError("unexpected structural-frame DFM schema")
        if self.source_main_sha != SOURCE_MAIN_SHA or _SHA40.fullmatch(self.source_main_sha) is None:
            raise StructuralFrameDfmError("structural-frame DFM audit is stale for released main")
        if self.authority_revision != AUTHORITY_REVISION:
            raise StructuralFrameDfmError("structural-frame DFM authority revision is stale")
        if self.authority_blob_sha != AUTHORITY_BLOB_SHA or _SHA40.fullmatch(self.authority_blob_sha) is None:
            raise StructuralFrameDfmError("structural-frame DFM authority blob is stale")
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise StructuralFrameDfmError("structural-frame DFM audit must use authority world frame")
        if _SHA64.fullmatch(self.structural_topology_sha256) is None:
            raise StructuralFrameDfmError("structural topology digest must be canonical SHA-256")
        if self.current_maturity != "TOPOLOGY_ONLY_3D_FRAME_AND_JOINS_UNRESOLVED":
            raise StructuralFrameDfmError("current frame maturity must remain explicit and fail closed")
        if (
            type(self.mold_draft_nominal_deg) not in (int, float)
            or not math.isfinite(float(self.mold_draft_nominal_deg))
            or self.mold_draft_nominal_deg <= 0.0
        ):
            raise StructuralFrameDfmError("mold draft must be a positive finite numeric authority value")
        if (
            type(self.rib_thickness_ratio_range) is not tuple
            or len(self.rib_thickness_ratio_range) != 2
            or any(
                type(value) not in (int, float) or not math.isfinite(float(value))
                for value in self.rib_thickness_ratio_range
            )
            or not (0.0 < self.rib_thickness_ratio_range[0] < self.rib_thickness_ratio_range[1])
        ):
            raise StructuralFrameDfmError("rib ratio range must be a valid finite increasing tuple")
        if type(self.requirements) is not tuple or tuple(item.requirement_id for item in self.requirements) != REQUIREMENT_IDS:
            raise StructuralFrameDfmError("structural-frame DFM requirements must use controlled deterministic order")
        ready = _exact_bool(self.digital_mvp_frame_dfm_ready, "digital_mvp_frame_dfm_ready")
        physical = _exact_bool(self.physical_validation_eligible, "physical_validation_eligible")
        if ready:
            raise StructuralFrameDfmError("topology-only frame cannot be digitally DFM-ready")
        if physical:
            raise StructuralFrameDfmError("digital structural-frame DFM audit cannot be physical evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise StructuralFrameDfmError("structural-frame DFM evidence firewall changed")

    @property
    def audit_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode()
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": self.schema,
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "source_git_blob_identities": [
                {"path": path, "git_blob_sha": blob_sha}
                for path, blob_sha in SOURCE_GIT_BLOB_IDENTITIES
            ],
            "coordinate_frame_id": self.coordinate_frame_id,
            "structural_topology_sha256": self.structural_topology_sha256,
            "current_maturity": self.current_maturity,
            "manufacturing_rules": {
                "mold_draft_nominal_deg": self.mold_draft_nominal_deg,
                "rib_thickness_ratio_range": list(self.rib_thickness_ratio_range),
                "status": "AUTHORITY_RULES_ONLY_NOT_TOOLING_VALIDATION",
            },
            "requirements": [item.manifest() for item in self.requirements],
            "blocking_requirement_ids": [item.requirement_id for item in self.requirements],
            "digital_mvp_frame_dfm_ready": self.digital_mvp_frame_dfm_ready,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["audit_sha256"] = self.audit_sha256
        return payload


def _build_current_frame(authority: Authority) -> StructuralFrameTopology:
    model = build_model(authority)
    boundaries = build_verified_interface_boundary_topology(
        authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(authority, boundaries)
    return build_structural_frame_topology(authority, attachment)


def _require_topology_only(frame: StructuralFrameTopology) -> None:
    if frame.cross_section_dimensions_mm is not None or frame.material_selection is not None:
        raise StructuralFrameDfmError(
            "released frame maturity changed; reconstruct and replace this topology-only DFM audit"
        )
    if any(datum.manifest()["z_mm"] is not None for datum in frame.datums):
        raise StructuralFrameDfmError(
            "released frame gained 3D placement; reconstruct and replace this topology-only DFM audit"
        )
    if "3D_MEMBER_GEOMETRY_AND_CROSS_SECTION_UNRESOLVED" not in frame.perimeter_reaction_path.geometry_realization_status:
        raise StructuralFrameDfmError(
            "released frame realization status changed; structural DFM audit requires typed invalidation"
        )
    reservation_by_id = {item.reservation_id: item for item in frame.reservations}
    if reservation_by_id[RESERVATION_RETENTION].envelope_status != "UNRESOLVED":
        raise StructuralFrameDfmError("retention-frame envelope moved; DFM audit requires reconstruction")
    if reservation_by_id[RESERVATION_RETENTION].placement_status != "RETENTION_GEOMETRY_DEFERRED_TO_ITERATION29":
        raise StructuralFrameDfmError("retention-frame placement moved; DFM audit requires reconstruction")
    if reservation_by_id[RESERVATION_ACTUATION].interface_count != 4:
        raise StructuralFrameDfmError("actuation-frame reservation moved; DFM audit requires reconstruction")


def build_structural_frame_dfm_audit(authority: Authority | None = None) -> StructuralFrameDfmAudit:
    _require_released_source_blobs()
    authority = authority or load_authority()
    if type(authority) is not Authority:
        raise StructuralFrameDfmError("structural-frame DFM audit requires exact Authority type")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise StructuralFrameDfmError("authority revision moved and requires DFM rebind")
    frame = _build_current_frame(authority)
    _require_topology_only(frame)

    manufacturing = authority.get("manufacturing")
    if type(manufacturing) is not dict:
        raise StructuralFrameDfmError("authority manufacturing mapping is required")
    rib_range = manufacturing.get("rib_thickness_ratio_range")
    if type(rib_range) is not list or len(rib_range) != 2:
        raise StructuralFrameDfmError("authority rib ratio range is malformed")

    requirements = (
        FrameDfmRequirement(
            REQ_FRAME_MEMBER,
            "P0",
            "CELL_3_MECHANISMS_RETENTION",
            "released main contains reaction topology and XY datums only; no 3D member, wall/cross-section or local structural transitions",
            "realize the current-main frame as valid B-rep members with explicit cross-section/wall intent, local transitions and controlled source binding before DFM freeze",
        ),
        FrameDfmRequirement(
            REQ_FRAME_SHELL_JOIN,
            "P0",
            "CELL_3_MECHANISMS_RETENTION",
            "no released frame-to-shell bridge or join geometry exists; legacy overlap solids are source material only",
            "realize each frame-to-shell bridge and select explicit integral, bonded/welded or discrete-fastener join semantics; raw positive B-rep overlap alone is not an assembly method",
        ),
        FrameDfmRequirement(
            REQ_TOOL_ACCESS,
            "P1",
            "CELL_3_MECHANISMS_RETENTION",
            "bosses, inserts, fasteners and tool axes are unresolved because no join architecture is released",
            "for discrete fastening, model boss/insert or through-fastener support plus installation/removal tool access; for integral or bonded joins, encode the applicable process/assembly access instead of inventing hardware",
        ),
        FrameDfmRequirement(
            REQ_ACTUATOR_ATTACHMENT,
            "P0",
            "CELL_3_MECHANISMS_RETENTION",
            "four actuation interfaces are reservation-only; current-main carriers, reaction shoes, attachment features and final mechanical hard stops are not realized",
            "realize the four differentiated actuator reaction interfaces and their frame attachment/retention so loads have a non-teleporting geometric path without claiming structural capacity",
        ),
        FrameDfmRequirement(
            REQ_RETENTION_ATTACHMENT,
            "P0",
            "CELL_3_MECHANISMS_RETENTION",
            "retention interface is reservation-only; current active right-latch geometry is not yet attached to a released 3D frame and the left interface is unported",
            "realize left and right frame-side retention attachments on the same current-main frame, including positive pin/closure retention and accessible assembly order",
        ),
        FrameDfmRequirement(
            REQ_ASSEMBLY_SEQUENCE,
            "P0",
            "CELL_3_MECHANISMS_RETENTION",
            "no current-main frame insertion and final frame-to-shell closure trajectory exists",
            "prove a collision-free frame insertion sequence and final join closure without requiring parts to pass through shell/frame material; sampled waypoints alone are insufficient for a claimed continuous sweep",
        ),
    )

    return StructuralFrameDfmAudit(
        SCHEMA,
        SOURCE_MAIN_SHA,
        AUTHORITY_REVISION,
        AUTHORITY_BLOB_SHA,
        WORLD_FRAME_ID,
        frame.topology_sha256,
        "TOPOLOGY_ONLY_3D_FRAME_AND_JOINS_UNRESOLVED",
        float(manufacturing.get("mold_draft_nominal_deg")),
        (float(rib_range[0]), float(rib_range[1])),
        requirements,
        False,
        False,
        EVIDENCE_STATUS,
    )
