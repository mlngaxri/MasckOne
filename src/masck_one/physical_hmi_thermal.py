from __future__ import annotations

"""Cell 14 physical HMI and WARM thermal package decision state.

This module intentionally separates user-facing interface/package reservations from
physical material. The live machine authority does not freeze a physical-HMI control
count or function mapping, and it does not provide heater technology, temperature,
power, or physical skin-safety evidence. Legacy Manual B is dimensional donor lineage
only. COOL remains a bounded optional local envelope until a released dry-bay world
datum exists.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
import re

import cadquery as cq

from .authority import Authority, load_authority


SCHEMA = "MASCK_ONE_CELL14_PHYSICAL_HMI_THERMAL_DECISION_STATE_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
MODEL_BLOB_SHA = "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"
STRUCTURAL_FRAME_BLOB_SHA = "bda5ba87d232c0e6a22e200975a80414a10c9a83"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

LEGACY_MANUAL_B_PR = 64
LEGACY_MANUAL_B_HEAD_SHA = "49a32d0c61bd1057ee707ee2ef20b8ff4e6ede01"
LEGACY_MANUAL_B_ELECTRONICS_BLOB_SHA = "59e69a781e4ffcbb581a9f2835c9cb581b3939f2"
LEGACY_DONOR_STATUS = "LEGACY_MANUAL_B_DIMENSIONAL_DONOR_ONLY_NOT_RELEASE_AUTHORITY"

# Current concurrent exterior candidate is observation context only. It is never
# consumed by this module as released geometry and therefore does not alter release
# truth when that candidate moves.
OBSERVED_CELL2_PR = 70
OBSERVED_CELL2_HEAD_SHA = "76aa6999f6dd3ae72d725c5517f57edbbaa5cf1e"
OBSERVED_CELL2_GEOMETRY_CONSUMED = False

FRAME_HMI_RESERVATION_ID = "FRAME_RESERVATION_HMI_ELECTRONICS"
FRAME_THERMAL_RESERVATION_ID = "FRAME_RESERVATION_THERMAL_SYSTEM"
HMI_MAPPING_STATUS = "DECISION_BLOCKED_LIVE_AUTHORITY_HAS_NO_PHYSICAL_HMI_CONTROL_COUNT_OR_MAPPING"
HMI_CAPACITY_STATUS = "PROVISIONAL_NEUTRAL_INTERFACE_CAPACITY_REBOUND_TO_CURRENT_MAIN"
WARM_STATUS = "REQUIRED_CELL14_MVP_PACKAGE_RESERVATION_HARDWARE_AND_PHYSICAL_THERMAL_EVIDENCE_BLOCKED"
COOL_STATUS = "OPTIONAL_NONBLOCKING_BOUNDED_LOCAL_RESERVATION_WORLD_PLACEMENT_BLOCKED"
EVIDENCE_STATUS = (
    "DIGITAL_HMI_THERMAL_PACKAGE_AND_DECISION_STATE_ONLY_NOT_WET_USE_INGRESS_"
    "THERMAL_SKIN_SAFETY_RUNTIME_DURABILITY_OR_PHYSICAL_VALIDATION"
)

RELATION_SEAL_INTERFACE = "SEAL_INTERFACE_RESERVATION_NOT_PHYSICAL_MATERIAL"
RELATION_CLEARANCE = "USER_ACCESS_CLEARANCE_REFERENCE_ONLY"
RELATION_PACKAGE = "SEALED_NONUSER_PACKAGE_RESERVATION_NOT_PHYSICAL_MATERIAL"

PRIMARY_ID = "HMI-PRIMARY-CONTROL-CAPACITY"
SECONDARY_BAND_ID = "HMI-SECONDARY-OPTION-BAND"
STATUS_WINDOW_ID = "HMI-STATUS-WINDOW-CAPACITY"
WET_FINGER_ID = "HMI-WET-FINGER-ACCESS-CLEARANCE"
WARM_LEFT_ID = "WARM-LEFT-PACKAGE-RESERVATION"
WARM_RIGHT_ID = "WARM-RIGHT-PACKAGE-RESERVATION"
COOL_ID = "COOL-OPTIONAL-DRY-BAY-LOCAL-RESERVATION"

# Rebound dimensional seeds inherited from closed Manual B donor #64. They are not
# supplier dimensions or authority requirements.
PRIMARY_CENTER_MM = (69.0, 25.0, 9.0)
PRIMARY_SIZE_MM = (11.0, 11.0, 2.4)
SECONDARY_BAND_CENTER_MM = (69.0, -2.0, 9.0)
SECONDARY_BAND_SIZE_MM = (10.0, 40.0, 2.4)
STATUS_CENTER_MM = (69.0, 39.0, 9.0)
STATUS_SIZE_MM = (10.0, 3.0, 1.2)
WET_FINGER_CENTER_MM = (74.75, 9.0, 9.0)
WET_FINGER_SIZE_MM = (22.5, 68.0, 16.0)
WARM_PACKAGE_SIZE_MM = (22.0, 28.0, 2.4)
WARM_LEFT_CENTER_MM = (-52.0, -4.0, -4.0)
WARM_RIGHT_CENTER_MM = (52.0, -4.0, -4.0)
COOL_LOCAL_ENVELOPE_MM = (24.0, 12.0, 4.0)

WARM_STACK_ELEMENT_IDS = ("HEATER", "TEMPERATURE_SENSOR", "SPREADER", "INSULATION")
ALLOWED_HYGIENE_CLASS = "SEALED_NONUSER"

SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", AUTHORITY_BLOB_SHA),
    ("src/masck_one/model.py", MODEL_BLOB_SHA),
    ("src/masck_one/structural_frame.py", STRUCTURAL_FRAME_BLOB_SHA),
)

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]


class PhysicalHmiThermalError(ValueError):
    pass


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise PhysicalHmiThermalError(f"{label} must be exact nonblank text")
    return value


def _exact_bool(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise PhysicalHmiThermalError(f"{label} must be an exact bool")
    return value


def _finite(value: object, *, label: str, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise PhysicalHmiThermalError(f"{label} must be an exact finite numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise PhysicalHmiThermalError(f"{label} must be finite")
    if positive and result <= 0.0:
        raise PhysicalHmiThermalError(f"{label} must be positive")
    return result


def _point(value: object, *, label: str) -> tuple[float, float, float]:
    if type(value) is not tuple or len(value) != 3:
        raise PhysicalHmiThermalError(f"{label} must be an exact XYZ tuple")
    return tuple(_finite(item, label=f"{label}[{index}]") for index, item in enumerate(value))  # type: ignore[return-value]


def _size(value: object, *, label: str) -> tuple[float, float, float]:
    if type(value) is not tuple or len(value) != 3:
        raise PhysicalHmiThermalError(f"{label} must be an exact XYZ size tuple")
    return tuple(_finite(item, label=f"{label}[{index}]", positive=True) for index, item in enumerate(value))  # type: ignore[return-value]


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_source_files_current() -> None:
    for relative_path, expected in SOURCE_GIT_BLOB_IDENTITIES:
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise PhysicalHmiThermalError(f"Cell 14 source file is missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise PhysicalHmiThermalError(
                f"Cell 14 source moved at {relative_path}; expected {expected}, got {actual}"
            )


def _require_canonical_authority(authority: Authority) -> None:
    if type(authority) is not Authority:
        raise PhysicalHmiThermalError("Cell 14 requires the exact Authority type")
    canonical = load_authority()
    if authority.data != canonical.data:
        raise PhysicalHmiThermalError("supplied authority differs from released machine authority")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise PhysicalHmiThermalError("Cell 14 authority revision moved")
    if tuple(authority.get("manufacturing", "hygiene_classes")) != (
        "DRY_ALWAYS",
        "WET_DRAINABLE",
        "WET_REMOVABLE",
        "SEALED_NONUSER",
    ):
        raise PhysicalHmiThermalError("authority hygiene vocabulary moved")


def _box(center: tuple[float, float, float], size: tuple[float, float, float]) -> cq.Workplane:
    center = _point(center, label="box center")
    size = _size(size, label="box size")
    return cq.Workplane("XY").box(*size, centered=(True, True, True)).translate(center)


def _geometry_manifest(solid: cq.Workplane) -> dict[str, object]:
    shape = solid.val()
    if not shape.isValid() or len(shape.Solids()) != 1 or float(shape.Volume()) <= 0.0:
        raise PhysicalHmiThermalError("Cell 14 reservation must be one valid positive-volume solid")
    bb = shape.BoundingBox()
    values = (
        float(bb.xmin), float(bb.ymin), float(bb.zmin),
        float(bb.xmax), float(bb.ymax), float(bb.zmax), float(shape.Volume()),
    )
    if not all(math.isfinite(value) for value in values):
        raise PhysicalHmiThermalError("Cell 14 reservation geometry must remain finite")
    return {
        "min_mm": [values[0], values[1], values[2]],
        "max_mm": [values[3], values[4], values[5]],
        "spans_mm": [float(bb.xlen), float(bb.ylen), float(bb.zlen)],
        "volume_mm3": values[6],
    }


@dataclass(frozen=True, slots=True)
class WorldBoxReservation:
    reservation_id: str
    role: str
    center_xyz_mm: tuple[float, float, float]
    size_xyz_mm: tuple[float, float, float]
    relationship_semantics: str
    hygiene_class: str
    geometry_status: str
    development_assembly_material_eligible: bool = False
    evidence_status: str = EVIDENCE_STATUS

    def __post_init__(self) -> None:
        for label, value in (
            ("reservation_id", self.reservation_id),
            ("role", self.role),
            ("relationship_semantics", self.relationship_semantics),
            ("hygiene_class", self.hygiene_class),
            ("geometry_status", self.geometry_status),
            ("evidence_status", self.evidence_status),
        ):
            _text(value, label=label)
        _point(self.center_xyz_mm, label=f"{self.reservation_id} center")
        _size(self.size_xyz_mm, label=f"{self.reservation_id} size")
        if self.hygiene_class != ALLOWED_HYGIENE_CLASS:
            raise PhysicalHmiThermalError("Cell 14 internal HMI/thermal package reservations must remain SEALED_NONUSER")
        if _exact_bool(self.development_assembly_material_eligible, label="material eligibility"):
            raise PhysicalHmiThermalError("Cell 14 reservation/reference geometry cannot silently become physical material")
        if self.evidence_status != EVIDENCE_STATUS:
            raise PhysicalHmiThermalError("Cell 14 reservation evidence boundary changed")
        _geometry_manifest(self.solid)

    @property
    def solid(self) -> cq.Workplane:
        return _box(self.center_xyz_mm, self.size_xyz_mm)

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "reservation_id": self.reservation_id,
            "role": self.role,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xyz_mm": list(self.center_xyz_mm),
            "size_xyz_mm": list(self.size_xyz_mm),
            "relationship_semantics": self.relationship_semantics,
            "hygiene_class": self.hygiene_class,
            "geometry_status": self.geometry_status,
            "development_assembly_material_eligible": self.development_assembly_material_eligible,
            "evidence_status": self.evidence_status,
            "geometry": _geometry_manifest(self.solid),
        }


@dataclass(frozen=True, slots=True)
class PhysicalHmiCapacity:
    primary: WorldBoxReservation
    secondary_option_band: WorldBoxReservation
    status_window: WorldBoxReservation
    wet_finger_access_clearance: WorldBoxReservation
    final_control_count: None
    function_mapping: None
    donor_capacity_ceiling: int
    clean_first_product_intent: bool
    mapping_status: str
    switch_hardware_status: str
    seal_hardware_status: str
    wet_finger_usability_status: str

    def __post_init__(self) -> None:
        expected_ids = (PRIMARY_ID, SECONDARY_BAND_ID, STATUS_WINDOW_ID, WET_FINGER_ID)
        actual_ids = (
            self.primary.reservation_id,
            self.secondary_option_band.reservation_id,
            self.status_window.reservation_id,
            self.wet_finger_access_clearance.reservation_id,
        )
        if actual_ids != expected_ids:
            raise PhysicalHmiThermalError("neutral HMI capacity identity or order changed")
        if self.final_control_count is not None or self.function_mapping is not None:
            raise PhysicalHmiThermalError("live authority does not permit Cell 14 to freeze control count or mapping")
        if type(self.donor_capacity_ceiling) is not int or self.donor_capacity_ceiling != 4:
            raise PhysicalHmiThermalError("legacy donor capacity ceiling must remain four without becoming control-count authority")
        if not _exact_bool(self.clean_first_product_intent, label="CLEAN-first intent"):
            raise PhysicalHmiThermalError("CLEAN-first product intent must remain explicit")
        if self.mapping_status != HMI_MAPPING_STATUS:
            raise PhysicalHmiThermalError("HMI mapping decision must remain blocked")
        for label, value in (
            ("switch_hardware_status", self.switch_hardware_status),
            ("seal_hardware_status", self.seal_hardware_status),
            ("wet_finger_usability_status", self.wet_finger_usability_status),
        ):
            _text(value, label=label)

        access = self.wet_finger_access_clearance.solid.val().BoundingBox()
        for item in (self.primary, self.secondary_option_band, self.status_window):
            bb = item.solid.val().BoundingBox()
            if bb.xmin < access.xmin - 1e-9 or bb.xmax > access.xmax + 1e-9:
                raise PhysicalHmiThermalError("wet-finger clearance no longer contains HMI capacity in X")
            if bb.ymin < access.ymin - 1e-9 or bb.ymax > access.ymax + 1e-9:
                raise PhysicalHmiThermalError("wet-finger clearance no longer contains HMI capacity in Y")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "primary": self.primary.manifest(),
            "secondary_option_band": self.secondary_option_band.manifest(),
            "status_window": self.status_window.manifest(),
            "wet_finger_access_clearance": self.wet_finger_access_clearance.manifest(),
            "final_control_count": self.final_control_count,
            "function_mapping": self.function_mapping,
            "donor_capacity_ceiling": self.donor_capacity_ceiling,
            "donor_capacity_semantics": "GEOMETRIC_CAPACITY_ONLY_NOT_REQUIRED_CONTROL_COUNT",
            "clean_first_product_intent": self.clean_first_product_intent,
            "clean_first_intent_semantics": "PRODUCT_UX_INTENT_NOT_FROZEN_CONTROL_MAPPING",
            "mapping_status": self.mapping_status,
            "switch_hardware_status": self.switch_hardware_status,
            "seal_hardware_status": self.seal_hardware_status,
            "wet_finger_usability_status": self.wet_finger_usability_status,
        }


@dataclass(frozen=True, slots=True)
class WarmPackageReservation:
    side: str
    package: WorldBoxReservation
    stack_element_ids: tuple[str, ...]
    selected_hardware: None
    temperature_limit_C: None
    nominal_power_W: None
    thermal_performance_validated: bool
    physical_skin_safety_validated: bool
    status: str

    def __post_init__(self) -> None:
        expected_id = WARM_LEFT_ID if self.side == "WEARER_LEFT" else WARM_RIGHT_ID if self.side == "WEARER_RIGHT" else None
        if expected_id is None or self.package.reservation_id != expected_id:
            raise PhysicalHmiThermalError("WARM side/package identity changed")
        if self.stack_element_ids != WARM_STACK_ELEMENT_IDS:
            raise PhysicalHmiThermalError("WARM stack reservation identity or order changed")
        if self.selected_hardware is not None or self.temperature_limit_C is not None or self.nominal_power_W is not None:
            raise PhysicalHmiThermalError("Cell 14 cannot invent WARM hardware, temperature limit, or power")
        if _exact_bool(self.thermal_performance_validated, label="thermal performance validated"):
            raise PhysicalHmiThermalError("digital WARM package cannot claim validated thermal performance")
        if _exact_bool(self.physical_skin_safety_validated, label="physical skin safety validated"):
            raise PhysicalHmiThermalError("digital WARM package cannot claim physical skin safety")
        if self.status != WARM_STATUS:
            raise PhysicalHmiThermalError("WARM package status changed")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "side": self.side,
            "package": self.package.manifest(),
            "stack_element_ids": list(self.stack_element_ids),
            "selected_hardware": self.selected_hardware,
            "temperature_limit_C": self.temperature_limit_C,
            "nominal_power_W": self.nominal_power_W,
            "thermal_performance_validated": self.thermal_performance_validated,
            "physical_skin_safety_validated": self.physical_skin_safety_validated,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class CoolOptionalReservation:
    reservation_id: str
    local_envelope_mm: tuple[float, float, float]
    local_frame_id: str
    world_center_xyz_mm: None
    world_transform: None
    world_placement_status: str
    optional: bool
    mvp_blocking: bool
    condensation_closed: bool
    cooling_performance_validated: bool
    status: str

    def __post_init__(self) -> None:
        if self.reservation_id != COOL_ID:
            raise PhysicalHmiThermalError("COOL reservation identity changed")
        _size(self.local_envelope_mm, label="COOL local envelope")
        _text(self.local_frame_id, label="COOL local frame")
        if self.world_center_xyz_mm is not None or self.world_transform is not None:
            raise PhysicalHmiThermalError("COOL cannot gain authority-world placement before a released dry-bay datum exists")
        _text(self.world_placement_status, label="COOL world placement status")
        if not _exact_bool(self.optional, label="COOL optional"):
            raise PhysicalHmiThermalError("COOL must remain optional")
        if _exact_bool(self.mvp_blocking, label="COOL MVP blocking"):
            raise PhysicalHmiThermalError("COOL may not block the CLEAN-first MVP")
        if _exact_bool(self.condensation_closed, label="COOL condensation closed"):
            raise PhysicalHmiThermalError("COOL condensation closure has no evidence")
        if _exact_bool(self.cooling_performance_validated, label="COOL performance validated"):
            raise PhysicalHmiThermalError("COOL has no validated cooling performance")
        if self.status != COOL_STATUS:
            raise PhysicalHmiThermalError("COOL optional reservation status changed")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "reservation_id": self.reservation_id,
            "local_envelope_mm": list(self.local_envelope_mm),
            "local_frame_id": self.local_frame_id,
            "world_center_xyz_mm": self.world_center_xyz_mm,
            "world_transform": self.world_transform,
            "world_placement_status": self.world_placement_status,
            "optional": self.optional,
            "mvp_blocking": self.mvp_blocking,
            "condensation_closed": self.condensation_closed,
            "cooling_performance_validated": self.cooling_performance_validated,
            "status": self.status,
            "exportable_world_brep": False,
        }


@dataclass(frozen=True, slots=True)
class PhysicalHmiThermalDecisionState:
    schema: str
    source_main_sha: str
    authority_revision: str
    authority_blob_sha: str
    coordinate_frame_id: str
    legacy_donor_pr: int
    legacy_donor_head_sha: str
    legacy_donor_blob_sha: str
    legacy_donor_status: str
    observed_cell2_pr: int
    observed_cell2_head_sha: str
    observed_cell2_geometry_consumed: bool
    hmi_frame_reservation_id: str
    thermal_frame_reservation_id: str
    hmi: PhysicalHmiCapacity
    warm: tuple[WarmPackageReservation, WarmPackageReservation]
    cool: CoolOptionalReservation
    frozen_ids: tuple[str, ...]
    reserved_ids: tuple[str, ...]
    optional_ids: tuple[str, ...]
    decision_blocked_ids: tuple[str, ...]
    digital_mvp_hmi_thermal_ready: bool
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise PhysicalHmiThermalError("unexpected Cell 14 schema")
        if self.source_main_sha != SOURCE_MAIN_SHA or _SHA40.fullmatch(self.source_main_sha) is None:
            raise PhysicalHmiThermalError("Cell 14 decision state is stale for released main")
        if self.authority_revision != AUTHORITY_REVISION:
            raise PhysicalHmiThermalError("Cell 14 authority revision is stale")
        if self.authority_blob_sha != AUTHORITY_BLOB_SHA or _SHA40.fullmatch(self.authority_blob_sha) is None:
            raise PhysicalHmiThermalError("Cell 14 authority blob is stale")
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise PhysicalHmiThermalError("Cell 14 world frame changed")
        if self.legacy_donor_pr != LEGACY_MANUAL_B_PR:
            raise PhysicalHmiThermalError("legacy donor PR identity changed")
        if self.legacy_donor_head_sha != LEGACY_MANUAL_B_HEAD_SHA or _SHA40.fullmatch(self.legacy_donor_head_sha) is None:
            raise PhysicalHmiThermalError("legacy donor head identity changed")
        if self.legacy_donor_blob_sha != LEGACY_MANUAL_B_ELECTRONICS_BLOB_SHA or _SHA40.fullmatch(self.legacy_donor_blob_sha) is None:
            raise PhysicalHmiThermalError("legacy donor blob identity changed")
        if self.legacy_donor_status != LEGACY_DONOR_STATUS:
            raise PhysicalHmiThermalError("legacy donor cannot become release authority")
        if self.observed_cell2_pr != OBSERVED_CELL2_PR:
            raise PhysicalHmiThermalError("Cell 2 observation identity changed")
        if self.observed_cell2_head_sha != OBSERVED_CELL2_HEAD_SHA or _SHA40.fullmatch(self.observed_cell2_head_sha) is None:
            raise PhysicalHmiThermalError("Cell 2 observed head identity malformed")
        if _exact_bool(self.observed_cell2_geometry_consumed, label="Cell 2 geometry consumed"):
            raise PhysicalHmiThermalError("unmerged Cell 2 geometry may not become Cell 14 release authority")
        if self.hmi_frame_reservation_id != FRAME_HMI_RESERVATION_ID or self.thermal_frame_reservation_id != FRAME_THERMAL_RESERVATION_ID:
            raise PhysicalHmiThermalError("released structural-frame reservation identity changed")
        if tuple(item.side for item in self.warm) != ("WEARER_LEFT", "WEARER_RIGHT"):
            raise PhysicalHmiThermalError("bilateral WARM package order changed")
        if self.frozen_ids != (
            "AUTHORITY_WORLD_FRAME_AND_AXES",
            "AUTHORITY_HYGIENE_CLASS_VOCABULARY",
            "PHYSICAL_EVIDENCE_FIREWALL",
        ):
            raise PhysicalHmiThermalError("Cell 14 frozen decision set changed")
        if self.reserved_ids != (
            PRIMARY_ID,
            SECONDARY_BAND_ID,
            STATUS_WINDOW_ID,
            WET_FINGER_ID,
            WARM_LEFT_ID,
            WARM_RIGHT_ID,
        ):
            raise PhysicalHmiThermalError("Cell 14 reserved decision set changed")
        if self.optional_ids != (COOL_ID,):
            raise PhysicalHmiThermalError("Cell 14 optional decision set changed")
        if self.decision_blocked_ids != (
            "HMI_FINAL_CONTROL_COUNT_AND_FUNCTION_MAPPING",
            "HMI_SWITCH_AND_SEAL_HARDWARE",
            "HMI_STATUS_OPTICAL_HARDWARE",
            "HMI_WET_FINGER_FORCE_USABILITY_AND_INGRESS",
            "WARM_HEATER_SENSOR_SPREADER_INSULATION_SELECTION",
            "WARM_TEMPERATURE_POWER_CONTROL_AND_SKIN_SAFETY",
            "HMI_EXTERIOR_CUT_FAIRING_AND_DRY_SIDE_ATTACHMENT",
            "HMI_WARM_HARNESS_AND_WET_DRY_BULKHEAD_HANDOFF",
            "COOL_AUTHORITY_WORLD_PLACEMENT_UNTIL_DRY_BAY_RELEASE",
        ):
            raise PhysicalHmiThermalError("Cell 14 decision-blocked set changed")
        if _exact_bool(self.digital_mvp_hmi_thermal_ready, label="digital MVP HMI/thermal ready"):
            raise PhysicalHmiThermalError("current Cell 14 package cannot claim digital MVP closure while blocked interfaces remain")
        if _exact_bool(self.physical_validation_eligible, label="physical validation eligible"):
            raise PhysicalHmiThermalError("Cell 14 digital package cannot become physical validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise PhysicalHmiThermalError("Cell 14 evidence boundary changed")

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.__post_init__()
        payload: dict[str, object] = {
            "schema": self.schema,
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "coordinate_frame_id": self.coordinate_frame_id,
            "source_bindings": {
                "released_blobs": [
                    {"path": path, "git_blob_sha": blob}
                    for path, blob in SOURCE_GIT_BLOB_IDENTITIES
                ],
                "legacy_manual_b": {
                    "pr": self.legacy_donor_pr,
                    "head_sha": self.legacy_donor_head_sha,
                    "electronics_package_blob_sha": self.legacy_donor_blob_sha,
                    "status": self.legacy_donor_status,
                },
                "cell2_observation": {
                    "pr": self.observed_cell2_pr,
                    "head_sha": self.observed_cell2_head_sha,
                    "geometry_consumed": self.observed_cell2_geometry_consumed,
                    "status": "CANDIDATE_CONTEXT_ONLY_RECHECK_IF_USED_FOR_PROMOTION_REVIEW",
                },
            },
            "released_frame_reservations": {
                "hmi_electronics": self.hmi_frame_reservation_id,
                "thermal": self.thermal_frame_reservation_id,
                "maturity": "UNRESOLVED_RESERVATIONS_ON_RELEASED_MAIN",
            },
            "hmi": self.hmi.manifest(),
            "warm": [item.manifest() for item in self.warm],
            "cool": self.cool.manifest(),
            "decision_state": {
                "frozen_ids": list(self.frozen_ids),
                "reserved_ids": list(self.reserved_ids),
                "optional_ids": list(self.optional_ids),
                "decision_blocked_ids": list(self.decision_blocked_ids),
            },
            "digital_mvp_hmi_thermal_ready": self.digital_mvp_hmi_thermal_ready,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload

    @property
    def world_review_reservations(self) -> tuple[WorldBoxReservation, ...]:
        return (
            self.hmi.primary,
            self.hmi.secondary_option_band,
            self.hmi.status_window,
            self.hmi.wet_finger_access_clearance,
            self.warm[0].package,
            self.warm[1].package,
        )


def _hmi_capacity() -> PhysicalHmiCapacity:
    return PhysicalHmiCapacity(
        primary=WorldBoxReservation(
            PRIMARY_ID,
            "dominant tactile-control capacity; CLEAN-first is product intent but function mapping is not frozen",
            PRIMARY_CENTER_MM,
            PRIMARY_SIZE_MM,
            RELATION_SEAL_INTERFACE,
            ALLOWED_HYGIENE_CLASS,
            HMI_CAPACITY_STATUS,
        ),
        secondary_option_band=WorldBoxReservation(
            SECONDARY_BAND_ID,
            "continuous neutral capacity band that can host zero to three later secondary controls without freezing count",
            SECONDARY_BAND_CENTER_MM,
            SECONDARY_BAND_SIZE_MM,
            RELATION_SEAL_INTERFACE,
            ALLOWED_HYGIENE_CLASS,
            HMI_CAPACITY_STATUS,
        ),
        status_window=WorldBoxReservation(
            STATUS_WINDOW_ID,
            "flush optical/status-window capacity; LED, light-pipe, color and intensity remain unselected",
            STATUS_CENTER_MM,
            STATUS_SIZE_MM,
            RELATION_SEAL_INTERFACE,
            ALLOWED_HYGIENE_CLASS,
            HMI_CAPACITY_STATUS,
        ),
        wet_finger_access_clearance=WorldBoxReservation(
            WET_FINGER_ID,
            "external wet-finger approach and manipulation clearance reference around the physical HMI capacity",
            WET_FINGER_CENTER_MM,
            WET_FINGER_SIZE_MM,
            RELATION_CLEARANCE,
            ALLOWED_HYGIENE_CLASS,
            "DIGITAL_ACCESS_CLEARANCE_ONLY_NOT_USABILITY_OR_HAND_ANTHROPOMETRY_VALIDATION",
        ),
        final_control_count=None,
        function_mapping=None,
        donor_capacity_ceiling=4,
        clean_first_product_intent=True,
        mapping_status=HMI_MAPPING_STATUS,
        switch_hardware_status="BLOCKED_SWITCH_TECHNOLOGY_TRAVEL_FORCE_TACTILE_RESPONSE_AND_LIFETIME_UNSELECTED",
        seal_hardware_status="BLOCKED_SEAL_STACK_MATERIAL_COMPRESSION_AND_INGRESS_EVIDENCE_UNSELECTED",
        wet_finger_usability_status="BLOCKED_PENDING_PHYSICAL_WET_HAND_USABILITY_FORCE_AND_ACCIDENTAL_ACTIVATION_VALIDATION",
    )


def _warm(side: str, center: tuple[float, float, float], reservation_id: str) -> WarmPackageReservation:
    return WarmPackageReservation(
        side=side,
        package=WorldBoxReservation(
            reservation_id,
            "sealed WARM heater/sensor/spreader/insulation stack occupancy reservation",
            center,
            WARM_PACKAGE_SIZE_MM,
            RELATION_PACKAGE,
            ALLOWED_HYGIENE_CLASS,
            "PROVISIONAL_DONOR_DIMENSIONAL_PACKAGE_RESERVATION_REBOUND_TO_CURRENT_MAIN",
        ),
        stack_element_ids=WARM_STACK_ELEMENT_IDS,
        selected_hardware=None,
        temperature_limit_C=None,
        nominal_power_W=None,
        thermal_performance_validated=False,
        physical_skin_safety_validated=False,
        status=WARM_STATUS,
    )


def build_physical_hmi_thermal_decision_state(
    authority: Authority | None = None,
) -> PhysicalHmiThermalDecisionState:
    _require_source_files_current()
    authority = authority or load_authority()
    _require_canonical_authority(authority)

    state = PhysicalHmiThermalDecisionState(
        schema=SCHEMA,
        source_main_sha=SOURCE_MAIN_SHA,
        authority_revision=AUTHORITY_REVISION,
        authority_blob_sha=AUTHORITY_BLOB_SHA,
        coordinate_frame_id=WORLD_FRAME_ID,
        legacy_donor_pr=LEGACY_MANUAL_B_PR,
        legacy_donor_head_sha=LEGACY_MANUAL_B_HEAD_SHA,
        legacy_donor_blob_sha=LEGACY_MANUAL_B_ELECTRONICS_BLOB_SHA,
        legacy_donor_status=LEGACY_DONOR_STATUS,
        observed_cell2_pr=OBSERVED_CELL2_PR,
        observed_cell2_head_sha=OBSERVED_CELL2_HEAD_SHA,
        observed_cell2_geometry_consumed=OBSERVED_CELL2_GEOMETRY_CONSUMED,
        hmi_frame_reservation_id=FRAME_HMI_RESERVATION_ID,
        thermal_frame_reservation_id=FRAME_THERMAL_RESERVATION_ID,
        hmi=_hmi_capacity(),
        warm=(
            _warm("WEARER_LEFT", WARM_LEFT_CENTER_MM, WARM_LEFT_ID),
            _warm("WEARER_RIGHT", WARM_RIGHT_CENTER_MM, WARM_RIGHT_ID),
        ),
        cool=CoolOptionalReservation(
            reservation_id=COOL_ID,
            local_envelope_mm=COOL_LOCAL_ENVELOPE_MM,
            local_frame_id="FUTURE_RELEASED_DRY_BAY_LOCAL_FRAME",
            world_center_xyz_mm=None,
            world_transform=None,
            world_placement_status="BLOCKED_PENDING_RELEASED_DRY_BAY_WORLD_DATUM_AND_EXPLICIT_TRANSFORM",
            optional=True,
            mvp_blocking=False,
            condensation_closed=False,
            cooling_performance_validated=False,
            status=COOL_STATUS,
        ),
        frozen_ids=(
            "AUTHORITY_WORLD_FRAME_AND_AXES",
            "AUTHORITY_HYGIENE_CLASS_VOCABULARY",
            "PHYSICAL_EVIDENCE_FIREWALL",
        ),
        reserved_ids=(
            PRIMARY_ID,
            SECONDARY_BAND_ID,
            STATUS_WINDOW_ID,
            WET_FINGER_ID,
            WARM_LEFT_ID,
            WARM_RIGHT_ID,
        ),
        optional_ids=(COOL_ID,),
        decision_blocked_ids=(
            "HMI_FINAL_CONTROL_COUNT_AND_FUNCTION_MAPPING",
            "HMI_SWITCH_AND_SEAL_HARDWARE",
            "HMI_STATUS_OPTICAL_HARDWARE",
            "HMI_WET_FINGER_FORCE_USABILITY_AND_INGRESS",
            "WARM_HEATER_SENSOR_SPREADER_INSULATION_SELECTION",
            "WARM_TEMPERATURE_POWER_CONTROL_AND_SKIN_SAFETY",
            "HMI_EXTERIOR_CUT_FAIRING_AND_DRY_SIDE_ATTACHMENT",
            "HMI_WARM_HARNESS_AND_WET_DRY_BULKHEAD_HANDOFF",
            "COOL_AUTHORITY_WORLD_PLACEMENT_UNTIL_DRY_BAY_RELEASE",
        ),
        digital_mvp_hmi_thermal_ready=False,
        physical_validation_eligible=False,
        evidence_status=EVIDENCE_STATUS,
    )
    state.__post_init__()
    return state


def export_physical_hmi_thermal_review_artifacts(
    output_dir: str | Path,
    state: PhysicalHmiThermalDecisionState | None = None,
) -> tuple[str, ...]:
    state = state or build_physical_hmi_thermal_decision_state()
    if type(state) is not PhysicalHmiThermalDecisionState:
        raise TypeError("state must be exact PhysicalHmiThermalDecisionState")
    state.__post_init__()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    file_map = {
        "hmi_primary_control_capacity_reference.step": state.hmi.primary.solid,
        "hmi_secondary_option_band_reference.step": state.hmi.secondary_option_band.solid,
        "hmi_status_window_capacity_reference.step": state.hmi.status_window.solid,
        "hmi_wet_finger_access_clearance_reference.step": state.hmi.wet_finger_access_clearance.solid,
        "warm_left_package_reservation_reference.step": state.warm[0].package.solid,
        "warm_right_package_reservation_reference.step": state.warm[1].package.solid,
    }
    for filename, solid in file_map.items():
        cq.exporters.export(solid, str(output / filename))
    manifest_filename = "physical_hmi_thermal_decision_state.json"
    with (output / manifest_filename).open("w", encoding="utf-8") as handle:
        json.dump(state.manifest(), handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return (*file_map.keys(), manifest_filename)
