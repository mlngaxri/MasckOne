from __future__ import annotations

"""Cell 13 released electrical endpoint inventory and Manual-B donor delta.

This module intentionally does not realize harness centerlines, connector hardware,
strain relief, service loops, or wet/dry bulkhead material. Released main does not yet
expose trustworthy electrical mating datums for those features. The inventory instead
binds stable endpoint identity, current maturity, exact source provenance, and the
closed Manual-B 13-route donor delta so stale route coordinates cannot become product
truth by implication.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
import re

from .actuator_frames import ZONE_IDS as ACTUATOR_ZONE_IDS
from .authority import Authority, load_authority
from .fresh_pump_packaging import STATION_CLEANSER, STATION_WATER
from .model import MasckOneModel, build_model
from .structural_frame import RESERVATION_HMI_ELECTRONICS, RESERVATION_THERMAL
from .waste_pump_architecture import STATION_WASTE

SCHEMA = "MASCK_ONE_CELL13_HARNESS_ENDPOINT_INVENTORY_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

LEGACY_DONOR_PR = 64
LEGACY_DONOR_HEAD_SHA = "49a32d0c61bd1057ee707ee2ef20b8ff4e6ede01"
LEGACY_DONOR_FILE = "src/masck_one/electronics_package.py"
LEGACY_DONOR_FILE_BLOB_SHA = "59e69a781e4ffcbb581a9f2835c9cb581b3939f2"
LEGACY_DONOR_CLEARANCE_RADIUS_MM = 1.4
LEGACY_DONOR_STATUS = "CLOSED_UNMERGED_DONOR_ONLY_NOT_CURRENT_PRODUCT_GEOMETRY"
LEGACY_ROUTE_DISPOSITION = "DONOR_ONLY_REBIND_REQUIRED_NO_CURRENT_ELECTRICAL_DATUM"

SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", AUTHORITY_BLOB_SHA),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/actuator_frames.py", "4c2013f994bdc9e084fe227eb5e166f973500ebb"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
    ("src/masck_one/fresh_pump_packaging.py", "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4"),
    ("src/masck_one/waste_pump_architecture.py", "ace02ee529070465b11832f475771125636312cb"),
)
SOURCE_BLOB_BY_MODULE = dict(SOURCE_GIT_BLOB_IDENTITIES)
EXPECTED_ABSENT_RELEASE_PATHS = (LEGACY_DONOR_FILE,)

CONTROLLED_ENVELOPE = "CONTROLLED_ENVELOPE"
TOPOLOGY_ONLY = "TOPOLOGY_ONLY"
UNRESOLVED = "UNRESOLVED"
OPTIONAL_UNRESOLVED = "OPTIONAL_UNRESOLVED"
MATURITY_VOCABULARY = (
    CONTROLLED_ENVELOPE,
    TOPOLOGY_ONLY,
    UNRESOLVED,
    OPTIONAL_UNRESOLVED,
)

BOUNDARY_DRY_INTENT_UNRELEASED = "DRY_SIDE_INTENT_BUT_DRY_BAY_GEOMETRY_UNRELEASED"
BOUNDARY_WET_DRY_CROSSING_UNRELEASED = "WET_DRY_CROSSING_REQUIRED_BULKHEAD_GEOMETRY_UNRELEASED"
BOUNDARY_PACKAGE_CLASS_UNRESOLVED = "PACKAGE_SIDE_CLASSIFICATION_PENDING_OWNER_GEOMETRY"
BOUNDARY_STATUS_VOCABULARY = (
    BOUNDARY_DRY_INTENT_UNRELEASED,
    BOUNDARY_WET_DRY_CROSSING_UNRELEASED,
    BOUNDARY_PACKAGE_CLASS_UNRESOLVED,
)

OWNER_CELL_7 = "CELL_7_ACTUATION"
OWNER_CELL_9 = "CELL_9_FRESH_WATER"
OWNER_CELL_10 = "CELL_10_CLEANSER"
OWNER_CELL_11 = "CELL_11_WASTE"
OWNER_CELL_12 = "CELL_12_DRY_SIDE"
OWNER_CELL_14 = "CELL_14_HMI_WARM"
OWNER_VOCABULARY = (
    OWNER_CELL_7,
    OWNER_CELL_9,
    OWNER_CELL_10,
    OWNER_CELL_11,
    OWNER_CELL_12,
    OWNER_CELL_14,
)

EP_BATTERY = "MASCK_ONE-ELEC-EP-BATTERY"
EP_PCB = "MASCK_ONE-ELEC-EP-PCB"
EP_ACTUATOR_01 = "MASCK_ONE-ELEC-EP-ACTUATOR-01"
EP_ACTUATOR_02 = "MASCK_ONE-ELEC-EP-ACTUATOR-02"
EP_ACTUATOR_03 = "MASCK_ONE-ELEC-EP-ACTUATOR-03"
EP_ACTUATOR_04 = "MASCK_ONE-ELEC-EP-ACTUATOR-04"
EP_PUMP_WATER = "MASCK_ONE-ELEC-EP-PUMP-WATER"
EP_PUMP_CLEANSER = "MASCK_ONE-ELEC-EP-PUMP-CLEANSER"
EP_PUMP_WASTE = "MASCK_ONE-ELEC-EP-PUMP-WASTE"
EP_HMI = "MASCK_ONE-ELEC-EP-HMI"
EP_WARM_LEFT = "MASCK_ONE-ELEC-EP-WARM-LEFT"
EP_WARM_RIGHT = "MASCK_ONE-ELEC-EP-WARM-RIGHT"
EP_COOL_OPTIONAL = "MASCK_ONE-ELEC-EP-COOL-OPTIONAL"
EP_CHARGING = "MASCK_ONE-ELEC-EP-CHARGING"
ENDPOINT_IDS = (
    EP_BATTERY,
    EP_PCB,
    EP_ACTUATOR_01,
    EP_ACTUATOR_02,
    EP_ACTUATOR_03,
    EP_ACTUATOR_04,
    EP_PUMP_WATER,
    EP_PUMP_CLEANSER,
    EP_PUMP_WASTE,
    EP_HMI,
    EP_WARM_LEFT,
    EP_WARM_RIGHT,
    EP_COOL_OPTIONAL,
    EP_CHARGING,
)
ACTUATOR_ENDPOINT_IDS = (
    EP_ACTUATOR_01,
    EP_ACTUATOR_02,
    EP_ACTUATOR_03,
    EP_ACTUATOR_04,
)

ROUTE_BATTERY_PCB = "HARNESS-BATTERY-PCB"
ROUTE_ACTUATOR_A = "HARNESS-PCB-ACTUATOR-A"
ROUTE_ACTUATOR_B = "HARNESS-PCB-ACTUATOR-B"
ROUTE_ACTUATOR_C = "HARNESS-PCB-ACTUATOR-C"
ROUTE_ACTUATOR_D = "HARNESS-PCB-ACTUATOR-D"
ROUTE_WATER_PUMP = "HARNESS-PCB-FRESH-WATER-PUMP"
ROUTE_CLEANSER_PUMP = "HARNESS-PCB-CLEANSER-PUMP"
ROUTE_WASTE_PUMP = "HARNESS-PCB-WASTE-PUMP"
ROUTE_HMI = "HARNESS-PCB-HMI"
ROUTE_WARM_LEFT = "HARNESS-PCB-WARM-LEFT"
ROUTE_WARM_RIGHT = "HARNESS-PCB-WARM-RIGHT"
ROUTE_COOL = "HARNESS-PCB-COOL-RESERVATION"
ROUTE_CHARGING = "HARNESS-PCB-CHARGING"
LEGACY_ROUTE_IDS = (
    ROUTE_BATTERY_PCB,
    ROUTE_ACTUATOR_A,
    ROUTE_ACTUATOR_B,
    ROUTE_ACTUATOR_C,
    ROUTE_ACTUATOR_D,
    ROUTE_WATER_PUMP,
    ROUTE_CLEANSER_PUMP,
    ROUTE_WASTE_PUMP,
    ROUTE_HMI,
    ROUTE_WARM_LEFT,
    ROUTE_WARM_RIGHT,
    ROUTE_COOL,
    ROUTE_CHARGING,
)

_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]

EVIDENCE_STATUS = (
    "DIGITAL_ENDPOINT_IDENTITY_AND_DONOR_DELTA_ONLY_NOT_HARNESS_CONNECTOR_BULKHEAD_"
    "INGRESS_ELECTRICAL_THERMAL_SERVICE_OR_PHYSICAL_VALIDATION_EVIDENCE"
)


class HarnessEndpointInventoryError(ValueError):
    pass


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise HarnessEndpointInventoryError(f"{label} must be exact nonblank text")
    return value


def _exact_bool(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise HarnessEndpointInventoryError(f"{label} must be an exact bool")
    return value


def _point_or_none(value: object, *, label: str) -> tuple[float, float, float] | None:
    if value is None:
        return None
    if type(value) is not tuple or len(value) != 3:
        raise HarnessEndpointInventoryError(f"{label} must be an exact XYZ tuple or None")
    result: list[float] = []
    for item in value:
        if type(item) not in (int, float):
            raise HarnessEndpointInventoryError(f"{label} values must be exact numeric scalars")
        numeric = float(item)
        if not math.isfinite(numeric):
            raise HarnessEndpointInventoryError(f"{label} values must be finite")
        result.append(0.0 if numeric == 0.0 else numeric)
    return tuple(result)  # type: ignore[return-value]


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_source_files_current() -> None:
    for relative_path, expected in SOURCE_GIT_BLOB_IDENTITIES:
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise HarnessEndpointInventoryError(f"Cell 13 source file is missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise HarnessEndpointInventoryError(
                f"Cell 13 source moved at {relative_path}; expected {expected}, got {actual}"
            )
    for relative_path in EXPECTED_ABSENT_RELEASE_PATHS:
        if (_REPO_ROOT / relative_path).exists():
            raise HarnessEndpointInventoryError(
                f"legacy or replacement endpoint producer appeared at {relative_path}; rebind Cell 13 before release"
            )


def _require_canonical_authority(authority: Authority) -> None:
    if type(authority) is not Authority:
        raise HarnessEndpointInventoryError("Cell 13 inventory requires exact Authority type")
    canonical = load_authority()
    if authority.data != canonical.data:
        raise HarnessEndpointInventoryError("supplied authority differs from released machine authority")
    if str(authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise HarnessEndpointInventoryError("Cell 13 authority revision moved")


@dataclass(frozen=True, slots=True)
class EndpointRecord:
    endpoint_id: str
    function_role: str
    blocker_owner: str
    source_module: str
    source_object_id: str
    source_git_blob_sha: str
    current_maturity: str
    package_anchor_xyz_mm: tuple[float, float, float] | None
    package_anchor_status: str
    electrical_interface_datum_xyz_mm: None
    electrical_interface_status: str
    boundary_status: str
    mvp_required: bool
    route_ready: bool

    def __post_init__(self) -> None:
        if self.endpoint_id not in ENDPOINT_IDS:
            raise HarnessEndpointInventoryError(f"uncontrolled endpoint ID {self.endpoint_id!r}")
        for label, value in (
            ("function_role", self.function_role),
            ("source_module", self.source_module),
            ("source_object_id", self.source_object_id),
            ("package_anchor_status", self.package_anchor_status),
            ("electrical_interface_status", self.electrical_interface_status),
        ):
            _text(value, label=label)
        if self.blocker_owner not in OWNER_VOCABULARY:
            raise HarnessEndpointInventoryError(f"uncontrolled blocker owner {self.blocker_owner!r}")
        if self.source_module not in SOURCE_BLOB_BY_MODULE:
            raise HarnessEndpointInventoryError(f"endpoint source module is not provenance-bound: {self.source_module}")
        if self.source_git_blob_sha != SOURCE_BLOB_BY_MODULE[self.source_module]:
            raise HarnessEndpointInventoryError("endpoint source blob does not match controlled module identity")
        if _SHA40_RE.fullmatch(self.source_git_blob_sha) is None:
            raise HarnessEndpointInventoryError("endpoint source blob must be canonical git SHA")
        if self.current_maturity not in MATURITY_VOCABULARY:
            raise HarnessEndpointInventoryError(f"uncontrolled endpoint maturity {self.current_maturity!r}")
        canonical_anchor = _point_or_none(self.package_anchor_xyz_mm, label="package anchor")
        if canonical_anchor != self.package_anchor_xyz_mm:
            raise HarnessEndpointInventoryError("package anchor must already be canonical finite floats")
        if self.electrical_interface_datum_xyz_mm is not None:
            raise HarnessEndpointInventoryError(
                "V1 current-main inventory cannot contain an electrical mating datum before its owner releases one"
            )
        if self.boundary_status not in BOUNDARY_STATUS_VOCABULARY:
            raise HarnessEndpointInventoryError("endpoint wet/dry boundary status is uncontrolled")
        _exact_bool(self.mvp_required, label="mvp_required")
        _exact_bool(self.route_ready, label="route_ready")
        if self.route_ready:
            raise HarnessEndpointInventoryError(
                "no current-main endpoint is route-ready without a released electrical mating datum"
            )
        if self.endpoint_id == EP_COOL_OPTIONAL:
            if self.mvp_required or self.current_maturity != OPTIONAL_UNRESOLVED:
                raise HarnessEndpointInventoryError("COOL must remain optional and unresolved in the current MVP inventory")
        if self.endpoint_id in ACTUATOR_ENDPOINT_IDS:
            expected_zone = ACTUATOR_ZONE_IDS[ACTUATOR_ENDPOINT_IDS.index(self.endpoint_id)]
            if self.source_module != "src/masck_one/actuator_frames.py" or self.source_object_id != expected_zone:
                raise HarnessEndpointInventoryError("actuator endpoint must bind released Cell 7 zone identity")
            if self.current_maturity != TOPOLOGY_ONLY or self.package_anchor_xyz_mm is not None:
                raise HarnessEndpointInventoryError(
                    "released actuator-frame origins remain unresolved; model package-reference transforms are not endpoint anchors"
                )

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "endpoint_id": self.endpoint_id,
            "function_role": self.function_role,
            "blocker_owner": self.blocker_owner,
            "source_module": self.source_module,
            "source_object_id": self.source_object_id,
            "source_git_blob_sha": self.source_git_blob_sha,
            "current_maturity": self.current_maturity,
            "package_anchor_xyz_mm": None if self.package_anchor_xyz_mm is None else list(self.package_anchor_xyz_mm),
            "package_anchor_status": self.package_anchor_status,
            "electrical_interface_datum_xyz_mm": None,
            "electrical_interface_status": self.electrical_interface_status,
            "boundary_status": self.boundary_status,
            "mvp_required": self.mvp_required,
            "route_ready": self.route_ready,
        }


@dataclass(frozen=True, slots=True)
class LegacyRouteBinding:
    route_id: str
    legacy_source_interface_id: str
    legacy_target_interface_id: str
    current_source_endpoint_id: str
    current_target_endpoint_id: str
    current_disposition: str
    legacy_service_slack_note: str

    def __post_init__(self) -> None:
        if self.route_id not in LEGACY_ROUTE_IDS:
            raise HarnessEndpointInventoryError(f"uncontrolled legacy route {self.route_id!r}")
        for label, value in (
            ("legacy_source_interface_id", self.legacy_source_interface_id),
            ("legacy_target_interface_id", self.legacy_target_interface_id),
            ("legacy_service_slack_note", self.legacy_service_slack_note),
        ):
            _text(value, label=label)
        if self.current_source_endpoint_id not in ENDPOINT_IDS or self.current_target_endpoint_id not in ENDPOINT_IDS:
            raise HarnessEndpointInventoryError("legacy route must map only to controlled current endpoint IDs")
        if self.current_source_endpoint_id == self.current_target_endpoint_id:
            raise HarnessEndpointInventoryError("legacy route cannot map an endpoint to itself")
        if self.current_disposition != LEGACY_ROUTE_DISPOSITION:
            raise HarnessEndpointInventoryError("legacy route cannot be promoted without a current-source rebind")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "route_id": self.route_id,
            "legacy_source_interface_id": self.legacy_source_interface_id,
            "legacy_target_interface_id": self.legacy_target_interface_id,
            "current_source_endpoint_id": self.current_source_endpoint_id,
            "current_target_endpoint_id": self.current_target_endpoint_id,
            "current_disposition": self.current_disposition,
            "legacy_service_slack_note": self.legacy_service_slack_note,
        }


@dataclass(frozen=True, slots=True)
class HarnessEndpointInventory:
    schema: str
    authored_against_main_sha: str
    authority_revision: str
    authority_blob_sha: str
    coordinate_frame_id: str
    source_git_blob_identities: tuple[tuple[str, str], ...]
    endpoints: tuple[EndpointRecord, ...]
    legacy_routes: tuple[LegacyRouteBinding, ...]
    current_harness_centerlines_released: bool
    wet_dry_bulkhead_geometry_released: bool
    current_route_ready_count: int
    legacy_routes_reusable_without_rebind: int
    development_assembly_material_eligible: bool
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise HarnessEndpointInventoryError("unexpected Cell 13 inventory schema")
        if self.authored_against_main_sha != SOURCE_MAIN_SHA or _SHA40_RE.fullmatch(self.authored_against_main_sha) is None:
            raise HarnessEndpointInventoryError("Cell 13 inventory main identity is stale")
        if self.authority_revision != AUTHORITY_REVISION:
            raise HarnessEndpointInventoryError("Cell 13 inventory authority revision is stale")
        if self.authority_blob_sha != AUTHORITY_BLOB_SHA or _SHA40_RE.fullmatch(self.authority_blob_sha) is None:
            raise HarnessEndpointInventoryError("Cell 13 inventory authority blob is stale")
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise HarnessEndpointInventoryError("Cell 13 inventory must use the canonical authority world frame")
        if self.source_git_blob_identities != SOURCE_GIT_BLOB_IDENTITIES:
            raise HarnessEndpointInventoryError("Cell 13 source graph identity changed")
        if tuple(item.endpoint_id for item in self.endpoints) != ENDPOINT_IDS:
            raise HarnessEndpointInventoryError("Cell 13 endpoint order/identity changed")
        if tuple(item.route_id for item in self.legacy_routes) != LEGACY_ROUTE_IDS:
            raise HarnessEndpointInventoryError("Manual-B donor route order/identity changed")
        if len(set(item.endpoint_id for item in self.endpoints)) != len(self.endpoints):
            raise HarnessEndpointInventoryError("Cell 13 endpoint IDs cannot repeat")
        if len(set(item.route_id for item in self.legacy_routes)) != len(self.legacy_routes):
            raise HarnessEndpointInventoryError("Manual-B donor route IDs cannot repeat")
        _exact_bool(self.current_harness_centerlines_released, label="current_harness_centerlines_released")
        _exact_bool(self.wet_dry_bulkhead_geometry_released, label="wet_dry_bulkhead_geometry_released")
        _exact_bool(self.development_assembly_material_eligible, label="development_assembly_material_eligible")
        _exact_bool(self.physical_validation_eligible, label="physical_validation_eligible")
        if self.current_harness_centerlines_released:
            raise HarnessEndpointInventoryError("current main does not release Cell 13 harness centerlines")
        if self.wet_dry_bulkhead_geometry_released:
            raise HarnessEndpointInventoryError("current main does not release wet/dry electrical bulkhead geometry")
        expected_ready = sum(1 for item in self.endpoints if item.route_ready)
        if type(self.current_route_ready_count) is not int or self.current_route_ready_count != expected_ready or expected_ready != 0:
            raise HarnessEndpointInventoryError("current route-ready count must remain exactly zero")
        if type(self.legacy_routes_reusable_without_rebind) is not int or self.legacy_routes_reusable_without_rebind != 0:
            raise HarnessEndpointInventoryError("no Manual-B route may be reused without rebind")
        if self.development_assembly_material_eligible:
            raise HarnessEndpointInventoryError("endpoint inventory is not physical assembly material")
        if self.physical_validation_eligible:
            raise HarnessEndpointInventoryError("digital endpoint inventory cannot be physical validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise HarnessEndpointInventoryError("Cell 13 evidence status changed")
        if _SHA40_RE.fullmatch(LEGACY_DONOR_HEAD_SHA) is None or _SHA40_RE.fullmatch(LEGACY_DONOR_FILE_BLOB_SHA) is None:
            raise HarnessEndpointInventoryError("legacy donor identities must remain exact git SHAs")

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
        self.__post_init__()
        payload: dict[str, object] = {
            "schema": self.schema,
            "authored_against_main_sha": self.authored_against_main_sha,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "coordinate_frame_id": self.coordinate_frame_id,
            "source_git_blob_identities": [list(item) for item in self.source_git_blob_identities],
            "endpoints": [item.manifest() for item in self.endpoints],
            "legacy_manual_b_donor": {
                "pr_number": LEGACY_DONOR_PR,
                "head_sha": LEGACY_DONOR_HEAD_SHA,
                "source_file": LEGACY_DONOR_FILE,
                "source_file_blob_sha": LEGACY_DONOR_FILE_BLOB_SHA,
                "clearance_radius_mm": LEGACY_DONOR_CLEARANCE_RADIUS_MM,
                "status": LEGACY_DONOR_STATUS,
                "route_count": len(self.legacy_routes),
                "routes": [item.manifest() for item in self.legacy_routes],
            },
            "current_harness_centerlines_released": self.current_harness_centerlines_released,
            "wet_dry_bulkhead_geometry_released": self.wet_dry_bulkhead_geometry_released,
            "current_route_ready_count": self.current_route_ready_count,
            "legacy_routes_reusable_without_rebind": self.legacy_routes_reusable_without_rebind,
            "development_assembly_material_eligible": self.development_assembly_material_eligible,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["inventory_sha256"] = self.inventory_sha256
        return payload


def _endpoint(
    endpoint_id: str,
    function_role: str,
    blocker_owner: str,
    source_module: str,
    source_object_id: str,
    maturity: str,
    anchor: tuple[float, float, float] | None,
    anchor_status: str,
    boundary_status: str,
    *,
    mvp_required: bool = True,
) -> EndpointRecord:
    return EndpointRecord(
        endpoint_id=endpoint_id,
        function_role=function_role,
        blocker_owner=blocker_owner,
        source_module=source_module,
        source_object_id=source_object_id,
        source_git_blob_sha=SOURCE_BLOB_BY_MODULE[source_module],
        current_maturity=maturity,
        package_anchor_xyz_mm=anchor,
        package_anchor_status=anchor_status,
        electrical_interface_datum_xyz_mm=None,
        electrical_interface_status="UNRESOLVED_NO_RELEASED_ELECTRICAL_MATING_DATUM",
        boundary_status=boundary_status,
        mvp_required=mvp_required,
        route_ready=False,
    )


def _legacy_route(
    route_id: str,
    legacy_source: str,
    legacy_target: str,
    source_endpoint: str,
    target_endpoint: str,
    service_note: str = "NO_CURRENT_SERVICE_SLACK_CLAIM",
) -> LegacyRouteBinding:
    return LegacyRouteBinding(
        route_id=route_id,
        legacy_source_interface_id=legacy_source,
        legacy_target_interface_id=legacy_target,
        current_source_endpoint_id=source_endpoint,
        current_target_endpoint_id=target_endpoint,
        current_disposition=LEGACY_ROUTE_DISPOSITION,
        legacy_service_slack_note=service_note,
    )


def _build_legacy_route_bindings() -> tuple[LegacyRouteBinding, ...]:
    return (
        _legacy_route(ROUTE_BATTERY_PCB, "BATTERY-CONNECTOR-ACCESS", "PCB-POWER-EDGE", EP_BATTERY, EP_PCB, "LEGACY_SHORT_DISCONNECT_SLACK_DONOR_ONLY"),
        _legacy_route(ROUTE_ACTUATOR_A, "PCB-ACT-A", "ACTUATOR-A-ELECTRICAL", EP_PCB, EP_ACTUATOR_01),
        _legacy_route(ROUTE_ACTUATOR_B, "PCB-ACT-B", "ACTUATOR-B-ELECTRICAL", EP_PCB, EP_ACTUATOR_02),
        _legacy_route(ROUTE_ACTUATOR_C, "PCB-ACT-C", "ACTUATOR-C-ELECTRICAL", EP_PCB, EP_ACTUATOR_03),
        _legacy_route(ROUTE_ACTUATOR_D, "PCB-ACT-D", "ACTUATOR-D-ELECTRICAL", EP_PCB, EP_ACTUATOR_04),
        _legacy_route(ROUTE_WATER_PUMP, "PCB-PUMP-WATER", "WATER-PUMP-DRY-BULKHEAD", EP_PCB, EP_PUMP_WATER),
        _legacy_route(ROUTE_CLEANSER_PUMP, "PCB-PUMP-CLEANSER", "CLEANSER-PUMP-DRY-BULKHEAD", EP_PCB, EP_PUMP_CLEANSER),
        _legacy_route(ROUTE_WASTE_PUMP, "PCB-PUMP-WASTE", "WASTE-PUMP-DRY-BULKHEAD", EP_PCB, EP_PUMP_WASTE),
        _legacy_route(ROUTE_HMI, "PCB-HMI-EDGE", "HMI-SIDE-PANEL", EP_PCB, EP_HMI, "LEGACY_LOCAL_FLEX_LOOP_DONOR_ONLY"),
        _legacy_route(ROUTE_WARM_LEFT, "PCB-WARM-L", "WARM-LEFT-SEALED-FEED", EP_PCB, EP_WARM_LEFT),
        _legacy_route(ROUTE_WARM_RIGHT, "PCB-WARM-R", "WARM-RIGHT-SEALED-FEED", EP_PCB, EP_WARM_RIGHT),
        _legacy_route(ROUTE_COOL, "PCB-THERMAL-EXP", "COOL-RESERVATION", EP_PCB, EP_COOL_OPTIONAL),
        _legacy_route(ROUTE_CHARGING, "PCB-CHARGE-EDGE", "CHARGING-DRY-SIDE", EP_PCB, EP_CHARGING, "LEGACY_CONNECTOR_SERVICE_SLACK_DONOR_ONLY"),
    )


def build_harness_endpoint_inventory(model: MasckOneModel | None = None) -> HarnessEndpointInventory:
    _require_source_files_current()
    model = model or build_model()
    if type(model) is not MasckOneModel:
        raise HarnessEndpointInventoryError("model must be exact MasckOneModel")
    _require_canonical_authority(model.authority)

    if len(model.actuator_envelopes) != 4:
        raise HarnessEndpointInventoryError("released model must retain exactly four actuator package references")
    if tuple(item.name for item in model.actuator_envelopes) != tuple(f"actuator_envelope_{index}" for index in range(1, 5)):
        raise HarnessEndpointInventoryError("released model actuator package-reference identity changed")
    if any(item.status != "ALPHA_PHYSICS_REFERENCE" for item in model.actuator_envelopes):
        raise HarnessEndpointInventoryError("released model actuator package-reference maturity changed")
    if tuple(ACTUATOR_ZONE_IDS) != (
        "ACTUATOR_ZONE_SUPERIOR_LEFT",
        "ACTUATOR_ZONE_SUPERIOR_RIGHT",
        "ACTUATOR_ZONE_INFERIOR_LEFT",
        "ACTUATOR_ZONE_INFERIOR_RIGHT",
    ):
        raise HarnessEndpointInventoryError("released actuator zone identity changed")
    if model.battery_reference_envelope.status != "PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE":
        raise HarnessEndpointInventoryError("battery benchmark maturity changed; Cell 13 must rebind")
    battery_center = model.battery_reference_envelope.solid.val().Center()
    battery_anchor = (float(battery_center.x), float(battery_center.y), float(battery_center.z))
    if any(
        not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-9)
        for actual, expected in zip(battery_anchor, (0.0, 0.0, -15.0), strict=True)
    ):
        raise HarnessEndpointInventoryError("released battery benchmark placement changed; Cell 13 must rebind")

    actuator_records = tuple(
        _endpoint(
            endpoint_id,
            f"actuator zone {index} electrical load",
            OWNER_CELL_7,
            "src/masck_one/actuator_frames.py",
            zone_id,
            TOPOLOGY_ONLY,
            None,
            "RELEASED_ACTUATOR_FRAME_ORIGIN_UNRESOLVED_MODEL_PACKAGE_REFERENCE_TRANSFORM_NOT_ENDPOINT_DATUM",
            BOUNDARY_PACKAGE_CLASS_UNRESOLVED,
        )
        for index, (endpoint_id, zone_id) in enumerate(zip(ACTUATOR_ENDPOINT_IDS, ACTUATOR_ZONE_IDS, strict=True), start=1)
    )

    endpoints = (
        _endpoint(EP_BATTERY, "battery power source packaging benchmark", OWNER_CELL_12, "config/masck_one_authority.yaml", "battery_reference", CONTROLLED_ENVELOPE, battery_anchor, "RELEASED_PACKAGE_BENCHMARK_CENTER_NOT_CONNECTOR_DATUM", BOUNDARY_DRY_INTENT_UNRELEASED),
        _endpoint(EP_PCB, "control and power PCB", OWNER_CELL_12, "src/masck_one/structural_frame.py", RESERVATION_HMI_ELECTRONICS, UNRESOLVED, None, "NO_RELEASED_PCB_PACKAGE_PLACEMENT", BOUNDARY_DRY_INTENT_UNRELEASED),
        *actuator_records,
        _endpoint(EP_PUMP_WATER, "fresh-water pump electrical load", OWNER_CELL_9, "src/masck_one/fresh_pump_packaging.py", STATION_WATER, TOPOLOGY_ONLY, None, "RELEASED_STATION_ID_ONLY_PACKAGE_PLACEMENT_UNRESOLVED", BOUNDARY_WET_DRY_CROSSING_UNRELEASED),
        _endpoint(EP_PUMP_CLEANSER, "cleanser pump electrical load", OWNER_CELL_10, "src/masck_one/fresh_pump_packaging.py", STATION_CLEANSER, TOPOLOGY_ONLY, None, "RELEASED_STATION_ID_ONLY_PACKAGE_PLACEMENT_UNRESOLVED", BOUNDARY_WET_DRY_CROSSING_UNRELEASED),
        _endpoint(EP_PUMP_WASTE, "mixed-waste pump electrical load", OWNER_CELL_11, "src/masck_one/waste_pump_architecture.py", STATION_WASTE, TOPOLOGY_ONLY, None, "RELEASED_STATION_ID_ONLY_PACKAGE_PLACEMENT_UNRESOLVED", BOUNDARY_WET_DRY_CROSSING_UNRELEASED),
        _endpoint(EP_HMI, "physical HMI aggregate electrical endpoint", OWNER_CELL_14, "src/masck_one/structural_frame.py", RESERVATION_HMI_ELECTRONICS, UNRESOLVED, None, "NO_RELEASED_HMI_PACKAGE_PLACEMENT", BOUNDARY_PACKAGE_CLASS_UNRESOLVED),
        _endpoint(EP_WARM_LEFT, "left WARM thermal electrical endpoint", OWNER_CELL_14, "src/masck_one/structural_frame.py", RESERVATION_THERMAL, UNRESOLVED, None, "NO_RELEASED_WARM_LEFT_PACKAGE_PLACEMENT", BOUNDARY_PACKAGE_CLASS_UNRESOLVED),
        _endpoint(EP_WARM_RIGHT, "right WARM thermal electrical endpoint", OWNER_CELL_14, "src/masck_one/structural_frame.py", RESERVATION_THERMAL, UNRESOLVED, None, "NO_RELEASED_WARM_RIGHT_PACKAGE_PLACEMENT", BOUNDARY_PACKAGE_CLASS_UNRESOLVED),
        _endpoint(EP_COOL_OPTIONAL, "optional COOL experimental electrical endpoint", OWNER_CELL_14, "src/masck_one/structural_frame.py", RESERVATION_THERMAL, OPTIONAL_UNRESOLVED, None, "NO_RELEASED_BOUNDED_COOL_WORLD_PACKAGE", BOUNDARY_PACKAGE_CLASS_UNRESOLVED, mvp_required=False),
        _endpoint(EP_CHARGING, "charging interface electrical endpoint", OWNER_CELL_12, "src/masck_one/structural_frame.py", RESERVATION_HMI_ELECTRONICS, UNRESOLVED, None, "NO_RELEASED_CHARGING_CONNECTOR_PLACEMENT", BOUNDARY_DRY_INTENT_UNRELEASED),
    )

    return HarnessEndpointInventory(
        schema=SCHEMA,
        authored_against_main_sha=SOURCE_MAIN_SHA,
        authority_revision=AUTHORITY_REVISION,
        authority_blob_sha=AUTHORITY_BLOB_SHA,
        coordinate_frame_id=WORLD_FRAME_ID,
        source_git_blob_identities=SOURCE_GIT_BLOB_IDENTITIES,
        endpoints=endpoints,
        legacy_routes=_build_legacy_route_bindings(),
        current_harness_centerlines_released=False,
        wet_dry_bulkhead_geometry_released=False,
        current_route_ready_count=0,
        legacy_routes_reusable_without_rebind=0,
        development_assembly_material_eligible=False,
        physical_validation_eligible=False,
        evidence_status=EVIDENCE_STATUS,
    )
