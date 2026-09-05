from __future__ import annotations

"""Fail-closed Cell 5 DFM audit for actuator mount/reaction maturity.

This module creates no actuator, frame, carrier, fastener, flexure or stop geometry.
It binds the released actuator-frame/coupling topology and records the minimum digital
closure required before actuator mounts can be called manufacturable-in-principle.
Legacy Manual A geometry is retained only as exact-head donor review evidence.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
import re

from .actuation_sweep_contract import build_actuation_displacement_contract
from .actuator_coupling import build_actuator_coupling_architecture
from .actuator_frames import ActuatorFrameArchitecture, ZONE_IDS, build_actuator_frame_architecture
from .authority import Authority, load_authority
from .boundary_release import build_verified_interface_boundary_topology
from .interface_attachment import build_interface_attachment_architecture
from .model import MasckOneModel, build_model
from .structural_frame import StructuralFrameTopology, build_structural_frame_topology


SCHEMA = "MASCK_ONE_CELL5_ACTUATOR_MOUNT_DFM_AUDIT_V1"
SOURCE_MAIN_SHA = "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
EVIDENCE_STATUS = (
    "DIGITAL_ACTUATOR_MOUNT_DFM_MATURITY_AND_DONOR_REVIEW_ONLY_NOT_FORCE_STIFFNESS_"
    "FATIGUE_ACOUSTIC_DURABILITY_SUPPLIER_PROCESS_OR_PHYSICAL_VALIDATION"
)

SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/interface_topology.py", "38b7c932f71a8675d45d098ac65154f98ff8bbb5"),
    ("src/masck_one/boundary_release.py", "34a49eed2c521d55e48ac187c2dd33dc9e22a3e3"),
    ("src/masck_one/interface_attachment.py", "c161f99ddd3473f3b9dde30ec73397a72915191a"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
    ("src/masck_one/actuator_frames.py", "4c2013f994bdc9e084fe227eb5e166f973500ebb"),
    ("src/masck_one/actuation_sweep_contract.py", "7d3180a92646b262f665adbb38030f94a2955df4"),
    ("src/masck_one/actuator_coupling.py", "d56160304190c030e3bc389803eaa456aaab5af0"),
)

LEGACY_DONOR_PR = 63
LEGACY_DONOR_HEAD_SHA = "23b942bbb7f335eac74b42fa1b1613900e5a9347"
LEGACY_DONOR_STRUCTURE_BLOB_SHA = "28b069ea2fdfa445ec63c930c142c67f392c7b99"

REQ_PLACEMENT_DATUMS = "ACTUATOR_PLACEMENT_AND_MOUNT_DATUMS"
REQ_PACKAGE_RETENTION = "ACTUATOR_PACKAGE_AND_POSITIVE_RETENTION"
REQ_REACTION_JOIN = "ACTUATOR_REACTION_PATH_AND_FRAME_JOIN"
REQ_FINAL_STOPS = "ACTUATOR_FINAL_MECHANICAL_STOPS"
REQ_SERVICE_ACCESS = "ACTUATOR_NONTELEPORTING_SERVICE_AND_TOOL_ACCESS"
REQ_TOLERANCE_STACK = "ACTUATOR_MOUNT_TOLERANCE_STACK"
REQ_AXIS_KEYING = "ACTUATOR_AXIS_KEYING_AND_DOE_STRATEGY"
REQUIREMENT_IDS = (
    REQ_PLACEMENT_DATUMS,
    REQ_PACKAGE_RETENTION,
    REQ_REACTION_JOIN,
    REQ_FINAL_STOPS,
    REQ_SERVICE_ACCESS,
    REQ_TOLERANCE_STACK,
    REQ_AXIS_KEYING,
)

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")


class ActuatorMountDfmError(ValueError):
    pass


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ActuatorMountDfmError(f"{label} must be exact nonblank text")
    return value


def _exact_bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ActuatorMountDfmError(f"{label} must be an exact bool")
    return value


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_released_source_blobs() -> None:
    root = Path(__file__).resolve().parents[2]
    for relative_path, expected in SOURCE_GIT_BLOB_IDENTITIES:
        path = root / relative_path
        if not path.is_file():
            raise ActuatorMountDfmError(f"actuator-mount DFM source file is missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise ActuatorMountDfmError(
                f"actuator-mount DFM source moved at {relative_path}; expected {expected}, got {actual}"
            )


def _require_canonical_authority(authority: Authority) -> None:
    if type(authority) is not Authority:
        raise ActuatorMountDfmError("actuator-mount DFM audit requires exact Authority type")
    canonical = load_authority()
    if authority.data != canonical.data:
        raise ActuatorMountDfmError("supplied authority differs from the released machine authority")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise ActuatorMountDfmError("actuator-mount DFM authority revision moved")


@dataclass(frozen=True, slots=True)
class ActuatorMountDfmRequirement:
    requirement_id: str
    severity: str
    owner: str
    current_state: str
    closure_required: str
    evidence_status: str = "DIGITAL_DFM_REQUIREMENT_ONLY"

    def __post_init__(self) -> None:
        if self.requirement_id not in REQUIREMENT_IDS:
            raise ActuatorMountDfmError("uncontrolled actuator-mount DFM requirement")
        if self.severity not in {"P0", "P1"}:
            raise ActuatorMountDfmError("actuator-mount DFM severity must be P0 or P1")
        for label, value in (
            ("owner", self.owner),
            ("current_state", self.current_state),
            ("closure_required", self.closure_required),
            ("evidence_status", self.evidence_status),
        ):
            _text(value, label)
        if self.evidence_status != "DIGITAL_DFM_REQUIREMENT_ONLY":
            raise ActuatorMountDfmError("DFM requirement cannot imply physical validation")

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
class LegacyDonorObservation:
    donor_pr: int
    donor_head_sha: str
    donor_source_blob_sha: str
    baseline_actuator_vs_shoe_intersection_mm3: float
    baseline_actuator_vs_frame_intersection_mm3_max: float
    doe_max_actuator_vs_shoe_intersection_mm3: float
    doe_max_actuator_vs_frame_intersection_mm3: float
    collar_radial_wall_mm: float
    collar_actuator_radial_clearance_mm: float
    authority_status: str
    evidence_status: str

    def __post_init__(self) -> None:
        if type(self.donor_pr) is not int or self.donor_pr != LEGACY_DONOR_PR:
            raise ActuatorMountDfmError("unexpected legacy donor PR")
        if self.donor_head_sha != LEGACY_DONOR_HEAD_SHA or _SHA40.fullmatch(self.donor_head_sha) is None:
            raise ActuatorMountDfmError("legacy actuator donor head identity changed")
        if self.donor_source_blob_sha != LEGACY_DONOR_STRUCTURE_BLOB_SHA or _SHA40.fullmatch(self.donor_source_blob_sha) is None:
            raise ActuatorMountDfmError("legacy actuator donor source identity changed")
        for label, value in (
            ("baseline actuator/shoe intersection", self.baseline_actuator_vs_shoe_intersection_mm3),
            ("baseline actuator/frame intersection", self.baseline_actuator_vs_frame_intersection_mm3_max),
            ("DOE actuator/shoe intersection", self.doe_max_actuator_vs_shoe_intersection_mm3),
            ("DOE actuator/frame intersection", self.doe_max_actuator_vs_frame_intersection_mm3),
            ("collar radial wall", self.collar_radial_wall_mm),
            ("collar radial clearance", self.collar_actuator_radial_clearance_mm),
        ):
            if type(value) not in (int, float) or not math.isfinite(float(value)) or float(value) < 0.0:
                raise ActuatorMountDfmError(f"{label} must be finite and nonnegative")
        if self.baseline_actuator_vs_shoe_intersection_mm3 <= 0.0:
            raise ActuatorMountDfmError("legacy donor collision observation must remain explicit")
        if self.baseline_actuator_vs_frame_intersection_mm3_max <= 0.0:
            raise ActuatorMountDfmError("legacy donor frame collision observation must remain explicit")
        if self.doe_max_actuator_vs_shoe_intersection_mm3 < self.baseline_actuator_vs_shoe_intersection_mm3:
            raise ActuatorMountDfmError("legacy donor DOE shoe collision cannot understate baseline")
        if self.doe_max_actuator_vs_frame_intersection_mm3 < self.baseline_actuator_vs_frame_intersection_mm3_max:
            raise ActuatorMountDfmError("legacy donor DOE frame collision cannot understate baseline")
        if self.authority_status != "STALE_SOURCE_MATERIAL_ONLY_NOT_RELEASE_AUTHORITY":
            raise ActuatorMountDfmError("legacy donor must not be promoted to release authority")
        if self.evidence_status != "CELL5_EXACT_HEAD_DIGITAL_BREP_RECONSTRUCTION_ONLY":
            raise ActuatorMountDfmError("legacy donor observation evidence semantics changed")

    def manifest(self) -> dict[str, object]:
        return {
            "donor_pr": self.donor_pr,
            "donor_head_sha": self.donor_head_sha,
            "donor_source_blob_sha": self.donor_source_blob_sha,
            "authority_status": self.authority_status,
            "observed_candidate_dimensions_mm": {
                "collar_outer_diameter": 12.6,
                "collar_inner_diameter": 10.6,
                "actuator_diameter": 10.2,
                "collar_length": 4.0,
                "reaction_shoe_xyz": [12.0, 12.0, 4.0],
            },
            "derived_candidate_margins_mm": {
                "collar_radial_wall": self.collar_radial_wall_mm,
                "collar_actuator_radial_clearance": self.collar_actuator_radial_clearance_mm,
            },
            "independent_collision_observations_mm3": {
                "baseline_61deg_actuator_vs_shoe": self.baseline_actuator_vs_shoe_intersection_mm3,
                "baseline_61deg_actuator_vs_frame_max": self.baseline_actuator_vs_frame_intersection_mm3_max,
                "doe_50_to_72deg_actuator_vs_shoe_max": self.doe_max_actuator_vs_shoe_intersection_mm3,
                "doe_50_to_72deg_actuator_vs_frame_max": self.doe_max_actuator_vs_frame_intersection_mm3,
            },
            "attachment_semantics_observed": "POSITIVE_BREP_OVERLAP_USED_AS_COLLAR_TO_SHOE_AND_SHOE_TO_FRAME_ATTACHMENT",
            "fastener_split_clamp_keyed_orientation_and_final_stop_geometry_observed": False,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class ActuatorMountDfmAudit:
    schema: str
    source_main_sha: str
    authority_revision: str
    authority_blob_sha: str
    coordinate_frame_id: str
    structural_topology_sha256: str
    actuator_architecture_sha256: str
    displacement_contract_sha256: str
    coupling_architecture_sha256: str
    current_maturity: str
    mold_draft_nominal_deg: float
    rib_thickness_ratio_range: tuple[float, float]
    requirements: tuple[ActuatorMountDfmRequirement, ...]
    legacy_donor: LegacyDonorObservation
    digital_mvp_actuator_mount_dfm_ready: bool
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise ActuatorMountDfmError("unexpected actuator-mount DFM schema")
        if self.source_main_sha != SOURCE_MAIN_SHA or _SHA40.fullmatch(self.source_main_sha) is None:
            raise ActuatorMountDfmError("actuator-mount DFM audit is stale for released main")
        if self.authority_revision != AUTHORITY_REVISION:
            raise ActuatorMountDfmError("actuator-mount DFM authority revision is stale")
        if self.authority_blob_sha != AUTHORITY_BLOB_SHA or _SHA40.fullmatch(self.authority_blob_sha) is None:
            raise ActuatorMountDfmError("actuator-mount DFM authority blob is stale")
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise ActuatorMountDfmError("actuator-mount DFM audit must use authority world frame")
        for label, value in (
            ("structural topology", self.structural_topology_sha256),
            ("actuator architecture", self.actuator_architecture_sha256),
            ("displacement contract", self.displacement_contract_sha256),
            ("coupling architecture", self.coupling_architecture_sha256),
        ):
            if _SHA64.fullmatch(value) is None:
                raise ActuatorMountDfmError(f"{label} digest must be canonical SHA-256")
        if self.current_maturity != "TOPOLOGY_ONLY_NO_RELEASED_ACTUATOR_MOUNT_REACTION_OR_STOP_BREP":
            raise ActuatorMountDfmError("current actuator-mount maturity changed and requires audit replacement")
        if type(self.mold_draft_nominal_deg) not in (int, float) or not math.isfinite(float(self.mold_draft_nominal_deg)) or float(self.mold_draft_nominal_deg) <= 0.0:
            raise ActuatorMountDfmError("mold draft must be a positive finite authority value")
        if (
            type(self.rib_thickness_ratio_range) is not tuple
            or len(self.rib_thickness_ratio_range) != 2
            or any(type(v) not in (int, float) or not math.isfinite(float(v)) for v in self.rib_thickness_ratio_range)
            or not (0.0 < self.rib_thickness_ratio_range[0] < self.rib_thickness_ratio_range[1])
        ):
            raise ActuatorMountDfmError("rib ratio range must be a finite increasing tuple")
        if type(self.requirements) is not tuple or tuple(item.requirement_id for item in self.requirements) != REQUIREMENT_IDS:
            raise ActuatorMountDfmError("actuator-mount DFM requirements must use controlled deterministic order")
        if _exact_bool(self.digital_mvp_actuator_mount_dfm_ready, "digital_mvp_actuator_mount_dfm_ready"):
            raise ActuatorMountDfmError("unrealized actuator mounts cannot be digitally DFM-ready")
        if _exact_bool(self.physical_validation_eligible, "physical_validation_eligible"):
            raise ActuatorMountDfmError("digital actuator-mount DFM audit cannot be physical evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise ActuatorMountDfmError("actuator-mount DFM evidence firewall changed")

    @property
    def audit_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
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
            "source_architecture_sha256": {
                "structural_topology": self.structural_topology_sha256,
                "actuator_frames": self.actuator_architecture_sha256,
                "actuation_displacement": self.displacement_contract_sha256,
                "actuator_coupling": self.coupling_architecture_sha256,
            },
            "current_maturity": self.current_maturity,
            "manufacturing_rules": {
                "mold_draft_nominal_deg": self.mold_draft_nominal_deg,
                "rib_thickness_ratio_range": list(self.rib_thickness_ratio_range),
                "status": "AUTHORITY_RULES_ONLY_NOT_TOOLING_VALIDATION",
            },
            "requirements": [item.manifest() for item in self.requirements],
            "blocking_requirement_ids": [item.requirement_id for item in self.requirements],
            "legacy_donor_review": self.legacy_donor.manifest(),
            "digital_mvp_actuator_mount_dfm_ready": self.digital_mvp_actuator_mount_dfm_ready,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["audit_sha256"] = self.audit_sha256
        return payload


def _build_current_graph(authority: Authority) -> tuple[MasckOneModel, StructuralFrameTopology, ActuatorFrameArchitecture, object, object]:
    model = build_model(authority)
    boundaries = build_verified_interface_boundary_topology(
        authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(authority, boundaries)
    frame = build_structural_frame_topology(authority, attachment)
    actuator_architecture = build_actuator_frame_architecture(authority, frame)
    displacement = build_actuation_displacement_contract(authority, actuator_architecture)
    coupling = build_actuator_coupling_architecture(
        authority,
        actuator_architecture,
        displacement,
        frame,
        model.compliant_interface_topology,
    )
    return model, frame, actuator_architecture, displacement, coupling


def _require_current_unresolved_state(
    frame: StructuralFrameTopology,
    actuator_architecture: ActuatorFrameArchitecture,
    coupling: object,
) -> None:
    if actuator_architecture.sweep_ready:
        raise ActuatorMountDfmError("released actuator architecture gained sweep-ready geometry; replace this audit")
    if len(actuator_architecture.frames) != len(ZONE_IDS):
        raise ActuatorMountDfmError("released actuator zone count changed")
    for local in actuator_architecture.frames:
        if any(
            value is not None
            for value in (
                local.origin_xyz_mm,
                local.axis_azimuth_deg,
                local.structural_mount_datum_id,
                local.actuator_envelope_mm,
            )
        ):
            raise ActuatorMountDfmError("released actuator placement or mount geometry moved; replace this audit")
        if local.mount_status != "STRUCTURAL_RESERVATION_BOUND_FINAL_MOUNT_DATUM_UNRESOLVED":
            raise ActuatorMountDfmError("released actuator mount status moved")
    for zone in coupling.zones:
        if zone.flexure_geometry_status != "ABSTRACTION_ONLY_GEOMETRY_MATERIAL_STIFFNESS_AND_FATIGUE_UNRESOLVED":
            raise ActuatorMountDfmError("released coupling flexure maturity moved")
        if zone.mechanical_stop_status != "REQUIRED_INTERFACE_RESERVED_FINAL_STOP_GEOMETRY_AND_TRAVEL_MARGIN_UNRESOLVED":
            raise ActuatorMountDfmError("released actuator stop maturity moved")
        if zone.reaction_path_status != "TOPOLOGY_BINDS_COUPLING_TO_STRUCTURAL_ACTUATION_RESERVATION_LOADS_UNVALIDATED":
            raise ActuatorMountDfmError("released actuator reaction-path maturity moved")
    if frame.cross_section_dimensions_mm is not None or frame.material_selection is not None:
        raise ActuatorMountDfmError("released frame gained 3D structural maturity; replace this audit")


def build_actuator_mount_dfm_audit(authority: Authority | None = None) -> ActuatorMountDfmAudit:
    _require_released_source_blobs()
    authority = authority or load_authority()
    _require_canonical_authority(authority)
    model, frame, actuator_architecture, displacement, coupling = _build_current_graph(authority)
    _require_current_unresolved_state(frame, actuator_architecture, coupling)
    coupling.validate_current_sources(
        authority=authority,
        actuator_architecture=actuator_architecture,
        displacement_contract=displacement,
        structural_frame=frame,
        interface_topology=model.compliant_interface_topology,
    )

    manufacturing = authority.get("manufacturing")
    if type(manufacturing) is not dict:
        raise ActuatorMountDfmError("authority manufacturing mapping is required")
    rib_range = manufacturing.get("rib_thickness_ratio_range")
    if type(rib_range) is not list or len(rib_range) != 2:
        raise ActuatorMountDfmError("authority rib ratio range is malformed")

    requirements = (
        ActuatorMountDfmRequirement(
            REQ_PLACEMENT_DATUMS,
            "P0",
            "CELL_3_MECHANISMS_RETENTION",
            "all four released actuator local origins, azimuths, structural mount datums and selected package envelopes are unresolved",
            "realize four source-bound mount datums and controlled package/orientation geometry on the same realized structural frame before mount CAD can be frozen",
        ),
        ActuatorMountDfmRequirement(
            REQ_PACKAGE_RETENTION,
            "P0",
            "CELL_3_MECHANISMS_RETENTION",
            "released main contains no actuator carrier, split collar, clamp, latch, fastener, shoulder or other positive package-retention B-rep",
            "realize a manufacturable-in-principle actuator carrier/retainer with explicit installation direction, positive axial/radial retention and removal semantics; raw solid overlap is not retention",
        ),
        ActuatorMountDfmRequirement(
            REQ_REACTION_JOIN,
            "P0",
            "CELL_3_MECHANISMS_RETENTION",
            "coupling reaction path terminates at a structural reservation; no reaction shoe/carrier-to-frame join or local frame transition is released",
            "realize the coupling-to-carrier-to-frame reaction geometry and an explicit integral, bonded/welded or discrete-fastener join with process/tool access, without claiming structural capacity",
        ),
        ActuatorMountDfmRequirement(
            REQ_FINAL_STOPS,
            "P0",
            "CELL_3_MECHANISMS_RETENTION",
            "all four mechanical-stop interfaces and travel margins remain reservation-only",
            "realize positive mechanical stop faces for the controlled single-axis travel, bind stop locations to the selected moving element and prove overtravel is geometrically blocked without package penetration",
        ),
        ActuatorMountDfmRequirement(
            REQ_SERVICE_ACCESS,
            "P0",
            "CELL_3_MECHANISMS_RETENTION",
            "no current-main actuator install/remove trajectory, retainer tool path or collision-free service sequence exists",
            "prove a non-teleporting actuator/carrier installation and replacement sequence with retainer/tool/process access against current shell, frame and neighboring package geometry",
        ),
        ActuatorMountDfmRequirement(
            REQ_TOLERANCE_STACK,
            "P0",
            "CELL_3_MECHANISMS_RETENTION",
            "no released carrier-to-actuator fit, retainer engagement, carrier-to-frame or stop-clearance tolerance stack exists",
            "add source-bound worst-case dimensional stacks for actuator fit/clearance, retention engagement, frame join and stop travel; reject nonfinite, stale-source and negative-margin cases",
        ),
        ActuatorMountDfmRequirement(
            REQ_AXIS_KEYING,
            "P1",
            "CELL_3_MECHANISMS_RETENTION",
            "authority defines a 61 degree baseline and 50/55/61/67/72 degree DOE, but released mount geometry has no azimuth or keyed orientation strategy",
            "state whether the DOE represents selectable fixed build angles or an adjustable mount, then realize keyed orientation/datum geometry so assembly cannot silently rotate the actuator off its controlled single axis",
        ),
    )

    legacy = LegacyDonorObservation(
        LEGACY_DONOR_PR,
        LEGACY_DONOR_HEAD_SHA,
        LEGACY_DONOR_STRUCTURE_BLOB_SHA,
        21.993454,
        2.664932,
        43.628465,
        8.185202,
        1.0,
        0.2,
        "STALE_SOURCE_MATERIAL_ONLY_NOT_RELEASE_AUTHORITY",
        "CELL5_EXACT_HEAD_DIGITAL_BREP_RECONSTRUCTION_ONLY",
    )

    return ActuatorMountDfmAudit(
        SCHEMA,
        SOURCE_MAIN_SHA,
        AUTHORITY_REVISION,
        AUTHORITY_BLOB_SHA,
        WORLD_FRAME_ID,
        frame.topology_sha256,
        actuator_architecture.architecture_sha256,
        displacement.contract_sha256,
        coupling.architecture_sha256,
        "TOPOLOGY_ONLY_NO_RELEASED_ACTUATOR_MOUNT_REACTION_OR_STOP_BREP",
        float(manufacturing.get("mold_draft_nominal_deg")),
        (float(rib_range[0]), float(rib_range[1])),
        requirements,
        legacy,
        False,
        False,
        EVIDENCE_STATUS,
    )


def export_actuator_mount_dfm_audit(output_dir: str | Path, audit: ActuatorMountDfmAudit) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "actuator_mount_dfm_audit.json"
    path.write_text(
        json.dumps(audit.manifest(), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path
