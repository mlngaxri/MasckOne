"""Exact released/candidate source receipt for the dedicated CLEANSER graph.

Cell 10 uses this module to separate released repository truth from moving candidate
geometry before downstream routing work is allowed to consume either. It does not
promote candidate CAD, invent route centerlines, select a pump, or create physical
performance evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from .authority import Authority
from .boundary_release import build_verified_interface_boundary_topology
from .cleanser_storage import (
    CLEANSER_STORAGE_ID,
    PORT_OUTLET,
    PORT_PURGE,
    PORT_REFILL,
    CleanserStorageArchitecture,
    build_cleanser_storage_architecture,
)
from .distribution_geometry import (
    DistributionGeometryArchitecture,
    build_distribution_geometry_architecture,
)
from .distribution_manifold import (
    BRANCH_CLEANSER,
    INLET_CLEANSER,
    DistributionManifoldArchitecture,
    build_distribution_manifold_architecture,
)
from .fresh_pump_packaging import (
    FLUID_CLEANSER,
    INTERFACE_CLEANSER_PUMP_OUTLET,
    ROUTE_CLEANSER_MANIFOLD,
    ROUTE_CLEANSER_SOURCE,
    STATION_CLEANSER,
    FreshPumpPackagingArchitecture,
    build_fresh_pump_packaging_architecture,
)
from .interface_attachment import build_interface_attachment_architecture
from .model import MasckOneModel, build_model
from .structural_frame import StructuralFrameTopology, build_structural_frame_topology
from .water_reservoir import WaterReservoirArchitecture, build_water_reservoir_architecture

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
FLUID_IDENTITY = "CLEANSER"

AUTHORED_AGAINST_RELEASED_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"

RELEASED_SOURCE_BLOBS: tuple[tuple[str, str, str], ...] = (
    (
        "AUTHORITY",
        "config/masck_one_authority.yaml",
        "2608dda483b995539de422290371c219668a1527",
    ),
    (
        "CLEANSER_STORAGE_ARCHITECTURE",
        "src/masck_one/cleanser_storage.py",
        "5e087ca8b05da8352ad4800b2ef8280ea8ddcf29",
    ),
    (
        "FRESH_PUMP_PACKAGING_ARCHITECTURE",
        "src/masck_one/fresh_pump_packaging.py",
        "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4",
    ),
    (
        "DISTRIBUTION_MANIFOLD_ARCHITECTURE",
        "src/masck_one/distribution_manifold.py",
        "8f2a6c784b51734aba4d1f3809015707fc328405",
    ),
    (
        "DISTRIBUTION_GEOMETRY_ARCHITECTURE",
        "src/masck_one/distribution_geometry.py",
        "d2dd8b47bb6a2aa1edf57ac0632778228add7997",
    ),
)

CANDIDATE_STORAGE_PR = 80
CANDIDATE_STORAGE_HEAD = "6e3e05812406620072b37f54827b8345ed55ccea"
CANDIDATE_STORAGE_BLOBS: tuple[tuple[str, str], ...] = (
    ("src/masck_one/realized_cleanser_storage.py", "7c7eca7a12b14526946f759740161c33c13e5cb4"),
    ("src/masck_one/cleanser_service_interfaces.py", "7977c6d12e3b2883a246ca00d1570ad683229243"),
    ("src/masck_one/cleanser_service_envelope.py", "1944487af9baa1c9fe27004eceed52eeb8a08167"),
)

CANDIDATE_PUMP_PR = 94
CANDIDATE_PUMP_HEAD = "1eb826fe859c6d5ee6dc0097aa58a67944bb530b"
CANDIDATE_PUMP_BLOBS: tuple[tuple[str, str], ...] = (
    ("src/masck_one/realized_cleanser_pump.py", "bf66ed54e19abdd6c840c1431ef9634409cefc2e"),
)

CANDIDATE_ROUTING_AUDIT_PR = 99
CANDIDATE_ROUTING_AUDIT_HEAD = "072d59bd7a278385818cf19af38dbca58b8b1bd7"
CANDIDATE_ROUTING_AUDIT_BLOBS: tuple[tuple[str, str], ...] = (
    ("src/masck_one/fluid_routing_dfm.py", "395f53b575b298c73c19d4cf1762d005edd0345a"),
)

DISPOSITION_REWORK = "CANDIDATE_REWORK_NOT_RELEASED"
DISPOSITION_REBASE_REQUIRED = "CANDIDATE_REBASE_REQUIRED_NOT_RELEASED"
DISPOSITION_AUDIT_ONLY = "CANDIDATE_AUDIT_ONLY_NOT_GEOMETRY_OR_RELEASED_TRUTH"
CANDIDATE_DISPOSITIONS = frozenset(
    {DISPOSITION_REWORK, DISPOSITION_REBASE_REQUIRED, DISPOSITION_AUDIT_ONLY}
)

STORAGE_RELEASE_STATUS = "RELEASED_TOPOLOGY_ONLY_REALIZED_CAD_NOT_ON_MAIN"
PUMP_RELEASE_STATUS = "RELEASED_TOPOLOGY_ONLY_REALIZED_PACKAGE_NOT_ON_MAIN"
SOURCE_ROUTE_STATUS = "UNRESOLVED_NO_RELEASED_WORLD_CENTERLINE"
MANIFOLD_ROUTE_STATUS = "UNRESOLVED_NO_RELEASED_WORLD_CENTERLINE"
MANIFOLD_BRANCH_STATUS = "RELEASED_TOPOLOGY_ONLY_CENTERLINE_AND_BORE_UNRESOLVED"
OUTLET_STATUS = "RELEASED_SIX_DEVELOPMENT_DATUMS_NOT_REGISTERED_ANATOMICAL_GEOMETRY"
GROOVE_STATUS = "RELEASED_CENTERLINE_INTENT_ONLY_DIMENSIONS_UNRESOLVED"
PHYSICAL_EVIDENCE_STATUS = (
    "DIGITAL_SOURCE_GRAPH_AND_RELEASED_OUTLET_DATUM_RECEIPT_ONLY_NOT_CLEANSER_"
    "COMPATIBILITY_VISCOSITY_DOSING_HYDRAULIC_LEAK_SERVICE_HYGIENE_OR_PHYSICAL_EVIDENCE"
)

_GIT_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class CleanserGraphError(ValueError):
    """Raised when released/candidate cleanser graph identity is corrupted."""


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise CleanserGraphError(f"{label} must be exact built-in nonblank text")
    return value


def _git_sha(value: object, *, label: str) -> str:
    if type(value) is not str or _GIT_SHA_RE.fullmatch(value) is None:
        raise CleanserGraphError(f"{label} must be canonical lowercase 40-hex Git identity")
    return value


def _sha256(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise CleanserGraphError(f"{label} must be canonical lowercase SHA-256")
    return value


def _point3(value: object, *, label: str) -> tuple[float, float, float]:
    if type(value) is not tuple or len(value) != 3:
        raise CleanserGraphError(f"{label} must be an exact three-value tuple")
    result: list[float] = []
    for component in value:
        if type(component) not in (int, float):
            raise CleanserGraphError(f"{label} components must be finite built-in numbers")
        number = float(component)
        if not math.isfinite(number):
            raise CleanserGraphError(f"{label} components must be finite")
        result.append(0.0 if number == 0.0 else number)
    return result[0], result[1], result[2]


@dataclass(frozen=True, slots=True)
class ReleasedSourceBlob:
    source_id: str
    path: str
    blob_sha: str

    def __post_init__(self) -> None:
        _text(self.source_id, label="released source ID")
        _text(self.path, label="released source path")
        _git_sha(self.blob_sha, label="released source blob")

    def manifest(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "path": self.path,
            "blob_sha": self.blob_sha,
            "release_role": "RELEASED_SOURCE",
        }


@dataclass(frozen=True, slots=True)
class CandidateSourceReceipt:
    candidate_id: str
    pr_number: int
    head_sha: str
    source_blobs: tuple[tuple[str, str], ...]
    disposition: str
    consumable_as_release_authority: bool = False

    def __post_init__(self) -> None:
        _text(self.candidate_id, label="candidate ID")
        if type(self.pr_number) is not int or self.pr_number <= 0:
            raise CleanserGraphError("candidate PR number must be an exact positive integer")
        _git_sha(self.head_sha, label="candidate head")
        if type(self.source_blobs) is not tuple or not self.source_blobs:
            raise CleanserGraphError("candidate requires immutable source-blob bindings")
        paths: list[str] = []
        for item in self.source_blobs:
            if type(item) is not tuple or len(item) != 2:
                raise CleanserGraphError("candidate source binding must be exact (path, blob) tuple")
            path, blob = item
            _text(path, label="candidate source path")
            _git_sha(blob, label="candidate source blob")
            paths.append(path)
        if len(paths) != len(set(paths)):
            raise CleanserGraphError("candidate source paths cannot repeat")
        if type(self.disposition) is not str or self.disposition not in CANDIDATE_DISPOSITIONS:
            raise CleanserGraphError("candidate disposition cannot imply released authority")
        if type(self.consumable_as_release_authority) is not bool or self.consumable_as_release_authority:
            raise CleanserGraphError("moving candidate cannot be consumed as released authority")

    def manifest(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "source_blobs": [
                {"path": path, "blob_sha": blob} for path, blob in self.source_blobs
            ],
            "disposition": self.disposition,
            "consumable_as_release_authority": self.consumable_as_release_authority,
        }


@dataclass(frozen=True, slots=True)
class CleanserOutletDatum:
    outlet_id: str
    source_triangle_index: int
    region_id: str
    center_world_mm: tuple[float, float, float]
    lateral_direction_world: tuple[float, float, float]
    protected_clearance_mm: float
    fluid_identity: str = FLUID_IDENTITY
    frame_id: str = WORLD_FRAME_ID

    def __post_init__(self) -> None:
        _text(self.outlet_id, label="cleanser outlet ID")
        if not self.outlet_id.startswith("MANIFOLD-OUTLET-CLEANSER-"):
            raise CleanserGraphError("cleanser outlet ID must retain exact CLEANSER namespace")
        if type(self.source_triangle_index) is not int or self.source_triangle_index < 0:
            raise CleanserGraphError("cleanser outlet triangle index must be exact nonnegative integer")
        _text(self.region_id, label="cleanser outlet region")
        center = _point3(self.center_world_mm, label="cleanser outlet center")
        direction = _point3(self.lateral_direction_world, label="cleanser outlet direction")
        norm = math.sqrt(sum(component * component for component in direction))
        if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise CleanserGraphError("cleanser outlet direction must be unit length")
        if not math.isclose(direction[2], 0.0, rel_tol=0.0, abs_tol=1e-12):
            raise CleanserGraphError("released cleanser outlet direction must remain lateral in XY")
        if type(self.protected_clearance_mm) not in (int, float):
            raise CleanserGraphError("cleanser outlet protected clearance must be a finite number")
        clearance = float(self.protected_clearance_mm)
        if not math.isfinite(clearance) or clearance < 0.0:
            raise CleanserGraphError("cleanser outlet protected clearance must be finite nonnegative")
        if self.fluid_identity != FLUID_IDENTITY:
            raise CleanserGraphError("released outlet datum must retain exact CLEANSER identity")
        if self.frame_id != WORLD_FRAME_ID:
            raise CleanserGraphError("released outlet datum must retain canonical world frame")
        object.__setattr__(self, "center_world_mm", center)
        object.__setattr__(self, "lateral_direction_world", direction)
        object.__setattr__(self, "protected_clearance_mm", clearance)

    def manifest(self) -> dict[str, object]:
        return {
            "outlet_id": self.outlet_id,
            "fluid_identity": self.fluid_identity,
            "frame_id": self.frame_id,
            "source_triangle_index": self.source_triangle_index,
            "region_id": self.region_id,
            "center_world_mm": list(self.center_world_mm),
            "lateral_direction_world": list(self.lateral_direction_world),
            "protected_clearance_mm": self.protected_clearance_mm,
        }


@dataclass(frozen=True, slots=True)
class CleanserGraphReceipt:
    authored_against_released_main_sha: str
    authority_revision: str
    source_cleanser_architecture_sha256: str
    source_pump_architecture_sha256: str
    source_manifold_architecture_sha256: str
    source_distribution_architecture_sha256: str
    released_sources: tuple[ReleasedSourceBlob, ...]
    moving_candidates: tuple[CandidateSourceReceipt, ...]
    outlet_datums: tuple[CleanserOutletDatum, ...]
    storage_release_status: str
    pump_release_status: str
    source_route_status: str
    manifold_route_status: str
    manifold_branch_status: str
    outlet_status: str
    groove_status: str
    fluid_identity: str = FLUID_IDENTITY
    frame_id: str = WORLD_FRAME_ID
    reservoir_id: str = CLEANSER_STORAGE_ID
    source_port_id: str = PORT_OUTLET
    pump_station_id: str = STATION_CLEANSER
    pump_outlet_interface_id: str = INTERFACE_CLEANSER_PUMP_OUTLET
    source_route_id: str = ROUTE_CLEANSER_SOURCE
    manifold_route_id: str = ROUTE_CLEANSER_MANIFOLD
    manifold_branch_id: str = BRANCH_CLEANSER
    manifold_inlet_id: str = INLET_CLEANSER
    physical_validation_eligible: bool = False
    evidence_status: str = PHYSICAL_EVIDENCE_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    def validate_invariants(self) -> None:
        _git_sha(self.authored_against_released_main_sha, label="released main authorship")
        _text(self.authority_revision, label="authority revision")
        for label, value in (
            ("cleanser architecture", self.source_cleanser_architecture_sha256),
            ("pump architecture", self.source_pump_architecture_sha256),
            ("manifold architecture", self.source_manifold_architecture_sha256),
            ("distribution architecture", self.source_distribution_architecture_sha256),
        ):
            _sha256(value, label=label)
        if self.fluid_identity != FLUID_IDENTITY:
            raise CleanserGraphError("cleanser graph cannot alias another fluid identity")
        if self.frame_id != WORLD_FRAME_ID:
            raise CleanserGraphError("cleanser graph must use canonical world frame")
        expected_ids = (
            CLEANSER_STORAGE_ID,
            PORT_OUTLET,
            STATION_CLEANSER,
            INTERFACE_CLEANSER_PUMP_OUTLET,
            ROUTE_CLEANSER_SOURCE,
            ROUTE_CLEANSER_MANIFOLD,
            BRANCH_CLEANSER,
            INLET_CLEANSER,
        )
        actual_ids = (
            self.reservoir_id,
            self.source_port_id,
            self.pump_station_id,
            self.pump_outlet_interface_id,
            self.source_route_id,
            self.manifold_route_id,
            self.manifold_branch_id,
            self.manifold_inlet_id,
        )
        if actual_ids != expected_ids:
            raise CleanserGraphError("stable CLEANSER component/route/interface identity changed")

        expected_sources = tuple(
            ReleasedSourceBlob(*item) for item in RELEASED_SOURCE_BLOBS
        )
        if type(self.released_sources) is not tuple or self.released_sources != expected_sources:
            raise CleanserGraphError("released cleanser source-blob receipt changed")
        if type(self.moving_candidates) is not tuple or len(self.moving_candidates) != 3:
            raise CleanserGraphError("cleanser graph requires exact storage/pump/routing candidate receipts")
        for candidate in self.moving_candidates:
            if type(candidate) is not CandidateSourceReceipt:
                raise CleanserGraphError("moving candidates must use exact candidate receipt type")
        if len({candidate.pr_number for candidate in self.moving_candidates}) != 3:
            raise CleanserGraphError("candidate PR identities cannot repeat")

        if type(self.outlet_datums) is not tuple or len(self.outlet_datums) != 6:
            raise CleanserGraphError("released cleanser graph must contain exactly six outlet datums")
        if any(type(item) is not CleanserOutletDatum for item in self.outlet_datums):
            raise CleanserGraphError("cleanser outlet datums must use exact receipt type")
        expected_outlet_ids = tuple(
            f"MANIFOLD-OUTLET-CLEANSER-{index:02d}" for index in range(1, 7)
        )
        if tuple(item.outlet_id for item in self.outlet_datums) != expected_outlet_ids:
            raise CleanserGraphError("released cleanser outlet identity/order changed")
        if len({item.source_triangle_index for item in self.outlet_datums}) != 6:
            raise CleanserGraphError("released cleanser outlet source triangles cannot repeat")

        controlled_statuses = (
            (self.storage_release_status, STORAGE_RELEASE_STATUS),
            (self.pump_release_status, PUMP_RELEASE_STATUS),
            (self.source_route_status, SOURCE_ROUTE_STATUS),
            (self.manifold_route_status, MANIFOLD_ROUTE_STATUS),
            (self.manifold_branch_status, MANIFOLD_BRANCH_STATUS),
            (self.outlet_status, OUTLET_STATUS),
            (self.groove_status, GROOVE_STATUS),
            (self.evidence_status, PHYSICAL_EVIDENCE_STATUS),
        )
        if any(type(actual) is not str or actual != expected for actual, expected in controlled_statuses):
            raise CleanserGraphError("cleanser graph maturity/evidence status was promoted or corrupted")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise CleanserGraphError("digital cleanser graph cannot become physical validation evidence")

    def validate_current_sources(
        self,
        *,
        authority: Authority,
        cleanser: CleanserStorageArchitecture,
        pump: FreshPumpPackagingArchitecture,
        manifold: DistributionManifoldArchitecture,
        distribution: DistributionGeometryArchitecture,
    ) -> None:
        self.validate_invariants()
        if type(authority) is not Authority:
            raise CleanserGraphError("authority must use exact Authority type")
        if type(cleanser) is not CleanserStorageArchitecture:
            raise CleanserGraphError("cleanser source must use exact CleanserStorageArchitecture type")
        if type(pump) is not FreshPumpPackagingArchitecture:
            raise CleanserGraphError("pump source must use exact FreshPumpPackagingArchitecture type")
        if type(manifold) is not DistributionManifoldArchitecture:
            raise CleanserGraphError("manifold source must use exact DistributionManifoldArchitecture type")
        if type(distribution) is not DistributionGeometryArchitecture:
            raise CleanserGraphError("distribution source must use exact DistributionGeometryArchitecture type")

        if self.authority_revision != str(authority.get("project", "authority_revision")):
            raise CleanserGraphError("cleanser graph authority revision is stale")
        if self.source_cleanser_architecture_sha256 != cleanser.architecture_sha256:
            raise CleanserGraphError("cleanser graph storage architecture is stale")
        if self.source_pump_architecture_sha256 != pump.architecture_sha256:
            raise CleanserGraphError("cleanser graph pump architecture is stale")
        if self.source_manifold_architecture_sha256 != manifold.architecture_sha256:
            raise CleanserGraphError("cleanser graph manifold architecture is stale")
        if self.source_distribution_architecture_sha256 != distribution.architecture_sha256:
            raise CleanserGraphError("cleanser graph distribution architecture is stale")

        if tuple(port.port_id for port in cleanser.ports) != (
            PORT_REFILL,
            PORT_OUTLET,
            PORT_PURGE,
        ):
            raise CleanserGraphError("cleanser storage port identity/order changed")
        if {port.fluid_identity for port in cleanser.ports} != {FLUID_IDENTITY}:
            raise CleanserGraphError("cleanser storage port fluid identity changed")

        station = next((item for item in pump.stations if item.station_id == STATION_CLEANSER), None)
        if station is None or (
            station.fluid_identity,
            station.source_port_id,
            station.pump_outlet_interface_id,
        ) != (FLUID_IDENTITY, PORT_OUTLET, INTERFACE_CLEANSER_PUMP_OUTLET):
            raise CleanserGraphError("cleanser pump station identity/binding changed")
        routes = {
            item.route_id: item for item in pump.routes if item.fluid_identity == FLUID_IDENTITY
        }
        if set(routes) != {ROUTE_CLEANSER_SOURCE, ROUTE_CLEANSER_MANIFOLD}:
            raise CleanserGraphError("cleanser route identity set changed")
        if routes[ROUTE_CLEANSER_SOURCE].source_interface_id != PORT_OUTLET:
            raise CleanserGraphError("cleanser source route no longer starts at storage outlet")
        if routes[ROUTE_CLEANSER_SOURCE].target_interface_id != STATION_CLEANSER:
            raise CleanserGraphError("cleanser source route no longer terminates at cleanser pump")
        if routes[ROUTE_CLEANSER_MANIFOLD].source_interface_id != INTERFACE_CLEANSER_PUMP_OUTLET:
            raise CleanserGraphError("cleanser manifold route no longer starts at pump outlet")
        if routes[ROUTE_CLEANSER_MANIFOLD].target_interface_id != INLET_CLEANSER:
            raise CleanserGraphError("cleanser manifold route no longer terminates at cleanser manifold inlet")

        branch = next((item for item in manifold.branches if item.branch_id == BRANCH_CLEANSER), None)
        if branch is None or (
            branch.fluid_identity,
            branch.upstream_route_id,
            branch.inlet_interface_id,
        ) != (FLUID_IDENTITY, ROUTE_CLEANSER_MANIFOLD, INLET_CLEANSER):
            raise CleanserGraphError("cleanser manifold branch identity/binding changed")
        if branch.centerline_xyz_mm is not None or branch.nominal_inner_diameter_mm is not None:
            raise CleanserGraphError("released cleanser manifold branch geometry maturity changed")

        released_placements = tuple(
            item for item in distribution.placements if item.fluid_identity == FLUID_IDENTITY
        )
        if len(released_placements) != 6:
            raise CleanserGraphError("released cleanser distribution no longer contains six placements")
        expected = tuple(
            (
                item.outlet_id,
                item.source_triangle_index,
                item.region_id,
                item.center_xyz_mm,
                item.lateral_direction_xyz,
                item.protected_clearance_mm,
            )
            for item in released_placements
        )
        actual = tuple(
            (
                item.outlet_id,
                item.source_triangle_index,
                item.region_id,
                item.center_world_mm,
                item.lateral_direction_world,
                item.protected_clearance_mm,
            )
            for item in self.outlet_datums
        )
        if actual != expected:
            raise CleanserGraphError("released cleanser outlet datum receipt is stale")

        cleanser_grooves = tuple(
            groove
            for groove, placement in zip(
                distribution.grooves, distribution.placements, strict=True
            )
            if placement.fluid_identity == FLUID_IDENTITY
        )
        if len(cleanser_grooves) != 6 or any(
            value is not None
            for groove in cleanser_grooves
            for value in (groove.width_mm, groove.depth_mm, groove.length_mm)
        ):
            raise CleanserGraphError("released cleanser groove maturity changed")

    @property
    def receipt_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.validate_invariants()
        payload: dict[str, object] = {
            "authored_against_released_main_sha": self.authored_against_released_main_sha,
            "authority_revision": self.authority_revision,
            "frame_id": self.frame_id,
            "fluid_identity": self.fluid_identity,
            "stable_identity": {
                "reservoir_id": self.reservoir_id,
                "source_port_id": self.source_port_id,
                "pump_station_id": self.pump_station_id,
                "pump_outlet_interface_id": self.pump_outlet_interface_id,
                "source_route_id": self.source_route_id,
                "manifold_route_id": self.manifold_route_id,
                "manifold_branch_id": self.manifold_branch_id,
                "manifold_inlet_id": self.manifold_inlet_id,
            },
            "architecture_sources": {
                "cleanser_storage_sha256": self.source_cleanser_architecture_sha256,
                "pump_packaging_sha256": self.source_pump_architecture_sha256,
                "manifold_sha256": self.source_manifold_architecture_sha256,
                "distribution_sha256": self.source_distribution_architecture_sha256,
            },
            "released_sources": [item.manifest() for item in self.released_sources],
            "moving_candidates": [item.manifest() for item in self.moving_candidates],
            "maturity": {
                "storage": self.storage_release_status,
                "pump": self.pump_release_status,
                "source_route": self.source_route_status,
                "pump_to_manifold_route": self.manifold_route_status,
                "manifold_branch": self.manifold_branch_status,
                "outlets": self.outlet_status,
                "grooves": self.groove_status,
            },
            "outlet_datums": [item.manifest() for item in self.outlet_datums],
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            raw = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            payload["receipt_sha256"] = sha256(raw).hexdigest()
        return payload


@dataclass(frozen=True, slots=True)
class CurrentCleanserGraphSources:
    model: MasckOneModel
    water: WaterReservoirArchitecture
    cleanser: CleanserStorageArchitecture
    frame: StructuralFrameTopology
    pump: FreshPumpPackagingArchitecture
    manifold: DistributionManifoldArchitecture
    distribution: DistributionGeometryArchitecture


def build_current_cleanser_graph_sources() -> CurrentCleanserGraphSources:
    model = build_model()
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
    pump = build_fresh_pump_packaging_architecture(
        model.authority,
        water,
        cleanser,
        frame,
    )
    manifold = build_distribution_manifold_architecture(
        model.authority,
        pump,
        water,
        cleanser,
        frame,
    )
    distribution = build_distribution_geometry_architecture(
        model.authority,
        manifold,
        pump,
        water,
        cleanser,
        frame,
        model.coverage_mesh,
        model.protected_volumes,
    )
    return CurrentCleanserGraphSources(
        model=model,
        water=water,
        cleanser=cleanser,
        frame=frame,
        pump=pump,
        manifold=manifold,
        distribution=distribution,
    )


def build_cleanser_graph_receipt(
    sources: CurrentCleanserGraphSources | None = None,
) -> CleanserGraphReceipt:
    current = build_current_cleanser_graph_sources() if sources is None else sources
    if type(current) is not CurrentCleanserGraphSources:
        raise CleanserGraphError("cleanser graph sources must use exact CurrentCleanserGraphSources type")

    released_sources = tuple(ReleasedSourceBlob(*item) for item in RELEASED_SOURCE_BLOBS)
    moving_candidates = (
        CandidateSourceReceipt(
            candidate_id="CELL4-CLEANSER-STORAGE-SERVICE",
            pr_number=CANDIDATE_STORAGE_PR,
            head_sha=CANDIDATE_STORAGE_HEAD,
            source_blobs=CANDIDATE_STORAGE_BLOBS,
            disposition=DISPOSITION_REWORK,
        ),
        CandidateSourceReceipt(
            candidate_id="CELL4-CLEANSER-PUMP-PACKAGE",
            pr_number=CANDIDATE_PUMP_PR,
            head_sha=CANDIDATE_PUMP_HEAD,
            source_blobs=CANDIDATE_PUMP_BLOBS,
            disposition=DISPOSITION_REBASE_REQUIRED,
        ),
        CandidateSourceReceipt(
            candidate_id="CELL5-FLUID-ROUTING-DFM-AUDIT",
            pr_number=CANDIDATE_ROUTING_AUDIT_PR,
            head_sha=CANDIDATE_ROUTING_AUDIT_HEAD,
            source_blobs=CANDIDATE_ROUTING_AUDIT_BLOBS,
            disposition=DISPOSITION_AUDIT_ONLY,
        ),
    )
    placements = tuple(
        item
        for item in current.distribution.placements
        if item.fluid_identity == FLUID_IDENTITY
    )
    outlet_datums = tuple(
        CleanserOutletDatum(
            outlet_id=item.outlet_id,
            source_triangle_index=item.source_triangle_index,
            region_id=item.region_id,
            center_world_mm=item.center_xyz_mm,
            lateral_direction_world=item.lateral_direction_xyz,
            protected_clearance_mm=item.protected_clearance_mm,
        )
        for item in placements
    )
    receipt = CleanserGraphReceipt(
        authored_against_released_main_sha=AUTHORED_AGAINST_RELEASED_MAIN_SHA,
        authority_revision=str(current.model.authority.get("project", "authority_revision")),
        source_cleanser_architecture_sha256=current.cleanser.architecture_sha256,
        source_pump_architecture_sha256=current.pump.architecture_sha256,
        source_manifold_architecture_sha256=current.manifold.architecture_sha256,
        source_distribution_architecture_sha256=current.distribution.architecture_sha256,
        released_sources=released_sources,
        moving_candidates=moving_candidates,
        outlet_datums=outlet_datums,
        storage_release_status=STORAGE_RELEASE_STATUS,
        pump_release_status=PUMP_RELEASE_STATUS,
        source_route_status=SOURCE_ROUTE_STATUS,
        manifold_route_status=MANIFOLD_ROUTE_STATUS,
        manifold_branch_status=MANIFOLD_BRANCH_STATUS,
        outlet_status=OUTLET_STATUS,
        groove_status=GROOVE_STATUS,
    )
    receipt.validate_current_sources(
        authority=current.model.authority,
        cleanser=current.cleanser,
        pump=current.pump,
        manifold=current.manifold,
        distribution=current.distribution,
    )
    return receipt
