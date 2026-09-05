from __future__ import annotations

"""Fail-closed Cell 5 DFM audit for the released waste-cartridge architecture.

The released Iteration 27 cartridge is an external package envelope plus topology and
requirements. This module intentionally creates no cartridge body, cavity, seal, latch,
media, key or service trajectory. It records the digital closure required before that
package can be called a manufacturable-in-principle disposable cartridge.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
import re

from .authority import Authority, load_authority
from .boundary_release import build_verified_interface_boundary_topology
from .cleanser_storage import build_cleanser_storage_architecture
from .distribution_geometry import build_distribution_geometry_architecture
from .distribution_manifold import build_distribution_manifold_architecture
from .fresh_pump_packaging import build_fresh_pump_packaging_architecture
from .interface_attachment import build_interface_attachment_architecture
from .model import MasckOneModel, build_model
from .structural_frame import build_structural_frame_topology
from .water_reservoir import build_water_reservoir_architecture
from .waste_acquisition import build_waste_acquisition_architecture
from .waste_cartridge import (
    CAPACITY_STATUS,
    KEYING_STATUS,
    SEALING_STATUS,
    SERVICE_STATUS,
    WasteCartridgeArchitecture,
    build_waste_cartridge_architecture,
)
from .waste_pump_packaging import build_waste_pump_packaging_architecture


SCHEMA = "MASCK_ONE_CELL5_WASTE_CARTRIDGE_DFM_AUDIT_V1"
SOURCE_MAIN_SHA = "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
MODEL_ENVELOPE_STATUS = "ENGINEERING_BASELINE_ENVELOPE"
CURRENT_HYGIENE_CLASSIFICATION = "UNRESOLVED"
EVIDENCE_STATUS = (
    "DIGITAL_WASTE_CARTRIDGE_DFM_MATURITY_ONLY_NOT_USABLE_CAPACITY_RETENTION_SEAL_"
    "LEAKAGE_HYGIENE_DURABILITY_WET_HAND_DISPOSAL_OR_PHYSICAL_VALIDATION"
)

SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/boundary_release.py", "34a49eed2c521d55e48ac187c2dd33dc9e22a3e3"),
    ("src/masck_one/interface_attachment.py", "c161f99ddd3473f3b9dde30ec73397a72915191a"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
    ("src/masck_one/water_reservoir.py", "6c14a37d07855550f0bd502e8308ed46682bc19c"),
    ("src/masck_one/cleanser_storage.py", "5e087ca8b05da8352ad4800b2ef8280ea8ddcf29"),
    ("src/masck_one/fresh_pump_packaging.py", "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4"),
    ("src/masck_one/distribution_manifold.py", "8f2a6c784b51734aba4d1f3809015707fc328405"),
    ("src/masck_one/distribution_geometry.py", "d2dd8b47bb6a2aa1edf57ac0632778228add7997"),
    ("src/masck_one/waste_acquisition.py", "7108fcfbe2baeaa9a343199a6817122ac2aea7ab"),
    ("src/masck_one/waste_pump_architecture.py", "ace02ee529070465b11832f475771125636312cb"),
    ("src/masck_one/waste_pump_packaging.py", "43587520a8c6cdc9ca8cfe362d2aac9589364fdc"),
    ("src/masck_one/waste_cartridge.py", "9dc0fe8a0ed92083c68406da3993e57e767e2483"),
)

EXPECTED_ABSENT_REALIZATION_PATHS = (
    "src/masck_one/realized_waste_cartridge.py",
    "src/masck_one/waste_cartridge_geometry.py",
    "src/masck_one/waste_cartridge_service.py",
)

REQ_BODY_CAVITY_WALLS = "CARTRIDGE_INTERNAL_CAVITY_AND_WALLS"
REQ_GEOMETRIC_CAPACITY = "CARTRIDGE_GEOMETRIC_CAPACITY_ACCOUNTING"
REQ_INLET_SEAL_CLOSURE = "CARTRIDGE_INLET_SEAL_AND_CLOSURE"
REQ_KEYING_RETENTION = "CARTRIDGE_POSITIVE_KEYING_AND_RETENTION"
REQ_SERVICE_PATH = "CARTRIDGE_NONTELEPORTING_SERVICE_PATH"
REQ_REMOVED_STATE = "CARTRIDGE_REMOVED_STATE_HANDLING"
REQ_DFM_TOLERANCE_PROCESS = "CARTRIDGE_DFM_TOLERANCE_AND_PROCESS"
REQUIREMENT_IDS = (
    REQ_BODY_CAVITY_WALLS,
    REQ_GEOMETRIC_CAPACITY,
    REQ_INLET_SEAL_CLOSURE,
    REQ_KEYING_RETENTION,
    REQ_SERVICE_PATH,
    REQ_REMOVED_STATE,
    REQ_DFM_TOLERANCE_PROCESS,
)

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]


class WasteCartridgeDfmError(ValueError):
    pass


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise WasteCartridgeDfmError(f"{label} must be exact nonblank text")
    return value


def _exact_bool(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise WasteCartridgeDfmError(f"{label} must be an exact bool")
    return value


def _finite(value: object, *, label: str, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise WasteCartridgeDfmError(f"{label} must be an exact finite numeric scalar")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise WasteCartridgeDfmError(f"{label} must be representable as a finite float") from exc
    if not math.isfinite(result):
        raise WasteCartridgeDfmError(f"{label} must be finite")
    if positive and result <= 0.0:
        raise WasteCartridgeDfmError(f"{label} must be positive")
    return result


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_source_files_current() -> None:
    for relative_path, expected in SOURCE_GIT_BLOB_IDENTITIES:
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise WasteCartridgeDfmError(f"waste-cartridge DFM source file is missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise WasteCartridgeDfmError(
                f"waste-cartridge DFM source moved at {relative_path}; expected {expected}, got {actual}"
            )
    for relative_path in EXPECTED_ABSENT_REALIZATION_PATHS:
        if (_REPO_ROOT / relative_path).exists():
            raise WasteCartridgeDfmError(
                f"new waste-cartridge realization source appeared at {relative_path}; rebind the Cell 5 DFM audit"
            )


def _require_canonical_authority(authority: Authority) -> None:
    if type(authority) is not Authority:
        raise WasteCartridgeDfmError("waste-cartridge DFM audit requires exact Authority type")
    canonical = load_authority()
    if authority.data != canonical.data:
        raise WasteCartridgeDfmError("supplied authority differs from released machine authority")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise WasteCartridgeDfmError("waste-cartridge DFM authority revision moved")


def _build_current_cartridge(model: MasckOneModel) -> WasteCartridgeArchitecture:
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    water = build_water_reservoir_architecture(model.authority)
    cleanser = build_cleanser_storage_architecture(model.authority)
    fresh_pumps = build_fresh_pump_packaging_architecture(
        model.authority,
        water,
        cleanser,
        frame,
    )
    manifold = build_distribution_manifold_architecture(
        model.authority,
        fresh_pumps,
        water,
        cleanser,
        frame,
    )
    distribution = build_distribution_geometry_architecture(
        model.authority,
        manifold,
        fresh_pumps,
        water,
        cleanser,
        frame,
        model.coverage_mesh,
        model.protected_volumes,
    )
    acquisition = build_waste_acquisition_architecture(model.authority, distribution)
    pump = build_waste_pump_packaging_architecture(
        model.authority,
        acquisition,
        distribution,
        frame,
    )
    return build_waste_cartridge_architecture(
        model.authority,
        pump,
        acquisition,
        distribution,
        frame,
    )


@dataclass(frozen=True, slots=True)
class WasteCartridgeDfmRequirement:
    requirement_id: str
    severity: str
    owner: str
    current_state: str
    closure_required: str
    evidence_status: str = "DIGITAL_DFM_REQUIREMENT_ONLY"

    def __post_init__(self) -> None:
        if self.requirement_id not in REQUIREMENT_IDS:
            raise WasteCartridgeDfmError("uncontrolled waste-cartridge DFM requirement")
        if self.severity != "P0":
            raise WasteCartridgeDfmError("waste-cartridge digital freeze blockers must remain P0")
        for label, value in (
            ("owner", self.owner),
            ("current_state", self.current_state),
            ("closure_required", self.closure_required),
            ("evidence_status", self.evidence_status),
        ):
            _text(value, label=label)
        if self.evidence_status != "DIGITAL_DFM_REQUIREMENT_ONLY":
            raise WasteCartridgeDfmError("DFM requirement cannot imply physical validation")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "requirement_id": self.requirement_id,
            "severity": self.severity,
            "owner": self.owner,
            "current_state": self.current_state,
            "closure_required": self.closure_required,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class WasteCartridgeDfmAudit:
    schema: str
    source_main_sha: str
    authority_revision: str
    authority_blob_sha: str
    coordinate_frame_id: str
    cartridge_architecture_sha256: str
    model_envelope_status: str
    external_envelope_mm: tuple[float, float, float]
    external_bounding_volume_mL: float
    retained_capacity_requirement_mL: float
    retained_requirement_to_external_bound_ratio: float
    service_cycles_baseline: int
    usable_internal_capacity_mL: None
    current_keying_status: str
    current_sealing_status: str
    current_service_status: str
    current_capacity_status: str
    current_hygiene_classification: str
    mold_draft_nominal_deg: float
    rib_thickness_ratio_range: tuple[float, float]
    requirements: tuple[WasteCartridgeDfmRequirement, ...]
    development_assembly_material_eligible: bool
    digital_mvp_cartridge_dfm_ready: bool
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise WasteCartridgeDfmError("unexpected waste-cartridge DFM schema")
        if self.source_main_sha != SOURCE_MAIN_SHA or _SHA40.fullmatch(self.source_main_sha) is None:
            raise WasteCartridgeDfmError("waste-cartridge DFM audit is stale for released main")
        if self.authority_revision != AUTHORITY_REVISION:
            raise WasteCartridgeDfmError("waste-cartridge DFM authority revision is stale")
        if self.authority_blob_sha != AUTHORITY_BLOB_SHA or _SHA40.fullmatch(self.authority_blob_sha) is None:
            raise WasteCartridgeDfmError("waste-cartridge DFM authority blob is stale")
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise WasteCartridgeDfmError("waste-cartridge DFM audit must use authority world frame")
        if type(self.cartridge_architecture_sha256) is not str or _SHA64.fullmatch(self.cartridge_architecture_sha256) is None:
            raise WasteCartridgeDfmError("cartridge architecture identity must be canonical SHA-256")
        if self.model_envelope_status != MODEL_ENVELOPE_STATUS:
            raise WasteCartridgeDfmError("released model cartridge maturity changed")
        if type(self.external_envelope_mm) is not tuple or len(self.external_envelope_mm) != 3:
            raise WasteCartridgeDfmError("cartridge external envelope must be an exact three-tuple")
        envelope = tuple(_finite(value, label="cartridge external envelope", positive=True) for value in self.external_envelope_mm)
        bound = _finite(self.external_bounding_volume_mL, label="external bounding volume", positive=True)
        retained = _finite(self.retained_capacity_requirement_mL, label="retained-capacity requirement", positive=True)
        ratio = _finite(
            self.retained_requirement_to_external_bound_ratio,
            label="retained requirement to external bound ratio",
            positive=True,
        )
        expected_bound = envelope[0] * envelope[1] * envelope[2] / 1000.0
        if not math.isclose(bound, expected_bound, rel_tol=0.0, abs_tol=1e-9):
            raise WasteCartridgeDfmError("external bounding-volume arithmetic changed")
        if not math.isclose(ratio, retained / bound, rel_tol=0.0, abs_tol=1e-12) or ratio >= 1.0:
            raise WasteCartridgeDfmError("cartridge retained-capacity package arithmetic changed")
        if type(self.service_cycles_baseline) is not int or self.service_cycles_baseline <= 0:
            raise WasteCartridgeDfmError("service-cycle baseline must be exact positive int")
        if self.usable_internal_capacity_mL is not None:
            raise WasteCartridgeDfmError("DFM audit cannot invent usable internal cartridge capacity")
        if self.current_keying_status != KEYING_STATUS:
            raise WasteCartridgeDfmError("released cartridge keying maturity changed")
        if self.current_sealing_status != SEALING_STATUS:
            raise WasteCartridgeDfmError("released cartridge sealing maturity changed")
        if self.current_service_status != SERVICE_STATUS:
            raise WasteCartridgeDfmError("released cartridge service maturity changed")
        if self.current_capacity_status != CAPACITY_STATUS:
            raise WasteCartridgeDfmError("released cartridge capacity maturity changed")
        if self.current_hygiene_classification != CURRENT_HYGIENE_CLASSIFICATION:
            raise WasteCartridgeDfmError("waste-cartridge hygiene class must remain unresolved until realized")
        draft = _finite(self.mold_draft_nominal_deg, label="nominal mold draft", positive=True)
        if type(self.rib_thickness_ratio_range) is not tuple or len(self.rib_thickness_ratio_range) != 2:
            raise WasteCartridgeDfmError("rib ratio range must be exact two-tuple")
        rib_min = _finite(self.rib_thickness_ratio_range[0], label="rib ratio minimum", positive=True)
        rib_max = _finite(self.rib_thickness_ratio_range[1], label="rib ratio maximum", positive=True)
        if rib_min > rib_max:
            raise WasteCartridgeDfmError("rib ratio range is reversed")
        if draft <= 0.0:
            raise WasteCartridgeDfmError("nominal mold draft must stay positive")
        if tuple(req.requirement_id for req in self.requirements) != REQUIREMENT_IDS:
            raise WasteCartridgeDfmError("waste-cartridge DFM requirement identity or order changed")
        if len({req.requirement_id for req in self.requirements}) != len(self.requirements):
            raise WasteCartridgeDfmError("waste-cartridge DFM requirements must be unique")
        for req in self.requirements:
            if type(req) is not WasteCartridgeDfmRequirement:
                raise WasteCartridgeDfmError("waste-cartridge DFM requirement type changed")
            req.__post_init__()
        if _exact_bool(self.development_assembly_material_eligible, label="assembly-material eligibility"):
            raise WasteCartridgeDfmError("an unresolved package envelope cannot be physical development-assembly material")
        if _exact_bool(self.digital_mvp_cartridge_dfm_ready, label="digital cartridge DFM readiness"):
            raise WasteCartridgeDfmError("released cartridge is not digitally DFM-ready")
        if _exact_bool(self.physical_validation_eligible, label="physical validation eligibility"):
            raise WasteCartridgeDfmError("digital cartridge DFM audit cannot become physical validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise WasteCartridgeDfmError("waste-cartridge DFM evidence boundary changed")

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return sha256(raw).hexdigest()

    def validate_current_sources(self, *, model: MasckOneModel | None = None) -> WasteCartridgeArchitecture:
        self.__post_init__()
        _require_source_files_current()
        model = model or build_model()
        _require_canonical_authority(model.authority)
        cartridge = _build_current_cartridge(model)
        if self.cartridge_architecture_sha256 != cartridge.architecture_sha256:
            raise WasteCartridgeDfmError("waste-cartridge DFM audit is stale for released cartridge architecture")
        component = model.waste_cartridge_envelope
        if component.name != "waste_cartridge_envelope" or component.status != MODEL_ENVELOPE_STATUS:
            raise WasteCartridgeDfmError("released cartridge package component identity changed")
        volume_mL = float(component.solid.val().Volume()) / 1000.0
        if not math.isclose(volume_mL, self.external_bounding_volume_mL, rel_tol=0.0, abs_tol=1e-6):
            raise WasteCartridgeDfmError("released cartridge package B-rep no longer matches authority envelope")
        return cartridge

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.__post_init__()
        payload: dict[str, object] = {
            "schema": self.schema,
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "coordinate_frame_id": self.coordinate_frame_id,
            "cartridge_architecture_sha256": self.cartridge_architecture_sha256,
            "current_released_geometry_role": "EXTERNAL_PACKAGE_ENVELOPE_ONLY_NOT_CARTRIDGE_MATERIAL",
            "model_envelope_status": self.model_envelope_status,
            "external_envelope_mm": list(self.external_envelope_mm),
            "external_bounding_volume_mL": self.external_bounding_volume_mL,
            "external_bounding_volume_semantics": "PACKAGE_UPPER_BOUND_ONLY_NOT_INTERNAL_OR_USABLE_CAPACITY",
            "retained_capacity_requirement_mL": self.retained_capacity_requirement_mL,
            "retained_requirement_to_external_bound_ratio": self.retained_requirement_to_external_bound_ratio,
            "service_cycles_baseline": self.service_cycles_baseline,
            "usable_internal_capacity_mL": self.usable_internal_capacity_mL,
            "current_keying_status": self.current_keying_status,
            "current_sealing_status": self.current_sealing_status,
            "current_service_status": self.current_service_status,
            "current_capacity_status": self.current_capacity_status,
            "current_hygiene_classification": self.current_hygiene_classification,
            "manufacturing_rules": {
                "mold_draft_nominal_deg": self.mold_draft_nominal_deg,
                "rib_thickness_ratio_range": list(self.rib_thickness_ratio_range),
                "rule_role": "RELEASED_DESIGN_RULES_NOT_PRODUCTION_PROCESS_CAPABILITY",
            },
            "requirements": [req.manifest() for req in self.requirements],
            "release_blocker_count": len(self.requirements),
            "development_assembly_material_eligible": self.development_assembly_material_eligible,
            "digital_mvp_cartridge_dfm_ready": self.digital_mvp_cartridge_dfm_ready,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload


def build_waste_cartridge_dfm_audit(*, model: MasckOneModel | None = None) -> WasteCartridgeDfmAudit:
    _require_source_files_current()
    model = model or build_model()
    _require_canonical_authority(model.authority)
    cartridge = _build_current_cartridge(model)
    if cartridge.capacity.usable_internal_capacity_mL is not None:
        raise WasteCartridgeDfmError("released cartridge unexpectedly claims usable internal capacity")
    unresolved = (
        cartridge.interfaces.key_geometry_mm,
        cartridge.interfaces.allowed_insertion_axis_xyz,
        cartridge.interfaces.seal_gland_geometry_mm,
        cartridge.interfaces.seal_compression_percent,
        cartridge.interfaces.insertion_trajectory_xyz_mm,
        cartridge.interfaces.removal_trajectory_xyz_mm,
        cartridge.interfaces.service_clearance_mm,
        cartridge.interfaces.retention_force_N,
    )
    if any(value is not None for value in unresolved):
        raise WasteCartridgeDfmError("released cartridge interface maturity advanced and requires a new DFM review")

    manufacturing = model.authority.get("manufacturing")
    if type(manufacturing) is not dict:
        raise WasteCartridgeDfmError("manufacturing authority must be an exact mapping")
    draft = _finite(manufacturing.get("mold_draft_nominal_deg"), label="authority mold draft", positive=True)
    rib_raw = manufacturing.get("rib_thickness_ratio_range")
    if type(rib_raw) is not list or len(rib_raw) != 2:
        raise WasteCartridgeDfmError("authority rib ratio range must be exact two-item list")
    rib_range = (
        _finite(rib_raw[0], label="authority rib ratio minimum", positive=True),
        _finite(rib_raw[1], label="authority rib ratio maximum", positive=True),
    )

    envelope = (
        float(cartridge.envelope.x_mm),
        float(cartridge.envelope.y_mm),
        float(cartridge.envelope.z_mm),
    )
    bound = float(cartridge.envelope.bounding_volume_mL)
    retained = float(cartridge.capacity.retained_capacity_min_mL)

    requirements = (
        WasteCartridgeDfmRequirement(
            REQ_BODY_CAVITY_WALLS,
            "P0",
            "CELL4_WASTE_CARTRIDGE_GEOMETRY",
            "Only the authority external package box exists; no cartridge body, internal cavity, wall, closure split, rib or boss B-rep is released.",
            "Realize deterministic cartridge material and cavity B-reps with intentional walls and part splits inside the controlled external envelope. Do not infer usable capacity or production moldability from the box.",
        ),
        WasteCartridgeDfmRequirement(
            REQ_GEOMETRIC_CAPACITY,
            "P0",
            "CELL4_WASTE_CARTRIDGE_GEOMETRY",
            "The 35 mL retained-capacity value is a validation-gated requirement while internal geometric capacity remains None.",
            "After body, walls, seals, retention and any media reservations exist, publish exact geometric cavity accounting that can be compared with the 35 mL requirement without promoting retained or usable liquid performance.",
        ),
        WasteCartridgeDfmRequirement(
            REQ_INLET_SEAL_CLOSURE,
            "P0",
            "CELL4_WASTE_CARTRIDGE_GEOMETRY",
            "The mixed-waste inlet and removable seal are interface IDs only; seal gland, land, closure and compression geometry are absent.",
            "Realize the inlet handoff, closure part boundary and seal gland or land geometry with a non-overlapping assembly state. Keep seal material, compression capability and leakage as unvalidated physical gates.",
        ),
        WasteCartridgeDfmRequirement(
            REQ_KEYING_RETENTION,
            "P0",
            "CELL4_WASTE_CARTRIDGE_GEOMETRY",
            "Keying and retention are topology-only; no key, latch, stop or misinsertion-blocking B-rep exists and retention force is unresolved.",
            "Realize positive keyed insertion and positive cartridge retention with an assembly sequence that does not rely on friction-only captivity. Prove digital misinsertion blocking without claiming physical force or wear performance.",
        ),
        WasteCartridgeDfmRequirement(
            REQ_SERVICE_PATH,
            "P0",
            "CELL4_WASTE_CARTRIDGE_GEOMETRY",
            "Insertion axis, insertion trajectory, removal trajectory and service clearance are all unresolved on released main.",
            "Publish non-teleporting insertion and removal motion B-reps or exact continuous sweeps against the current installed product geometry, including the access needed to operate the retention and wet interface.",
        ),
        WasteCartridgeDfmRequirement(
            REQ_REMOVED_STATE,
            "P0",
            "CELL4_WASTE_CARTRIDGE_GEOMETRY",
            "No removed-state closure or handling geometry is defined for the mixed-waste inlet, and the cartridge has no released hygiene classification.",
            "Define a deterministic removed-state handling and closure architecture for the wet mixed-waste interface and assign the resulting realized cavities only from the frozen hygiene vocabulary. Do not claim leak-tight disposal, hygiene or wet-hand usability from CAD.",
        ),
        WasteCartridgeDfmRequirement(
            REQ_DFM_TOLERANCE_PROCESS,
            "P0",
            "CELL4_WASTE_CARTRIDGE_GEOMETRY",
            "There is no cartridge parting, draft screen, tooling or secondary-operation access, or min-max fit stack because no production-intent part geometry exists.",
            "For the realized part split, apply the authority manufacturing rules or explicit controlled exceptions and publish critical min-max stacks for body-to-closure, key or latch, seal gland or land and device insertion fits plus required tooling or process access.",
        ),
    )

    audit = WasteCartridgeDfmAudit(
        schema=SCHEMA,
        source_main_sha=SOURCE_MAIN_SHA,
        authority_revision=AUTHORITY_REVISION,
        authority_blob_sha=AUTHORITY_BLOB_SHA,
        coordinate_frame_id=WORLD_FRAME_ID,
        cartridge_architecture_sha256=cartridge.architecture_sha256,
        model_envelope_status=model.waste_cartridge_envelope.status,
        external_envelope_mm=envelope,
        external_bounding_volume_mL=bound,
        retained_capacity_requirement_mL=retained,
        retained_requirement_to_external_bound_ratio=retained / bound,
        service_cycles_baseline=cartridge.capacity.service_cycles_baseline,
        usable_internal_capacity_mL=None,
        current_keying_status=cartridge.interfaces.keying_status,
        current_sealing_status=cartridge.interfaces.sealing_status,
        current_service_status=cartridge.interfaces.service_status,
        current_capacity_status=cartridge.capacity.capacity_status,
        current_hygiene_classification=CURRENT_HYGIENE_CLASSIFICATION,
        mold_draft_nominal_deg=draft,
        rib_thickness_ratio_range=rib_range,
        requirements=requirements,
        development_assembly_material_eligible=False,
        digital_mvp_cartridge_dfm_ready=False,
        physical_validation_eligible=False,
        evidence_status=EVIDENCE_STATUS,
    )
    audit.validate_current_sources(model=model)
    return audit
