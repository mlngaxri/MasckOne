from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math

import cadquery as cq

from .authority import Authority
from .coverage import (
    FacialCoverageMesh,
    REGION_ACTIVE_OTHER,
    REGION_T_FOREHEAD,
    REGION_T_NOSE_PHILTRUM,
)
from .protected_volumes import ProtectedVolumeSet
from .spatial import Point2, Point3, Vector3


class DistributionManifoldError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ManifoldOutlet:
    outlet_id: str
    fluid_role: str
    source_triangle_index: int
    region_id: str
    center_mm: Point3
    diameter_seed_mm: float
    direction: Vector3
    position_sensitivity_mm: float
    direction_sensitivity_deg: float
    discharge_mode: str
    evidence_status: str

    def __post_init__(self) -> None:
        if self.fluid_role not in {"WATER", "CLEANSER"}:
            raise DistributionManifoldError("Outlet fluid role must be WATER or CLEANSER")
        if self.region_id not in {REGION_ACTIVE_OTHER, REGION_T_FOREHEAD, REGION_T_NOSE_PHILTRUM}:
            raise DistributionManifoldError("Outlet must terminate in an active target region")
        if abs(self.direction.z) > 1e-12:
            raise DistributionManifoldError("Development outlet direction must be lateral/subsurface, not face-directed")
        if not math.isclose(self.direction.norm(), 1.0, abs_tol=1e-12):
            raise DistributionManifoldError("Outlet direction must be a unit vector")


@dataclass(frozen=True, slots=True)
class ManifoldBranch:
    branch_id: str
    fluid_role: str
    upstream_route_id: str
    outlet_ids: tuple[str, ...]
    nominal_inner_diameter_mm: float | None
    metering_restriction_geometry: tuple[float, ...] | None
    pressure_drop_model_status: str
    flow_balance_status: str

    def __post_init__(self) -> None:
        if not self.outlet_ids:
            raise DistributionManifoldError("Every manifold branch requires at least one outlet")
        if self.nominal_inner_diameter_mm is not None or self.metering_restriction_geometry is not None:
            raise DistributionManifoldError("Branch bore/restriction geometry requires metering-rig evidence")


@dataclass(frozen=True, slots=True)
class DistributionGrooveIntent:
    groove_id: str
    outlet_id: str
    origin_mm: Point3
    lateral_direction: Vector3
    width_mm: float | None
    depth_mm: float | None
    length_mm: float | None
    surface_status: str
    evidence_status: str

    def __post_init__(self) -> None:
        if any(value is not None for value in (self.width_mm, self.depth_mm, self.length_mm)):
            raise DistributionManifoldError("Groove dimensions remain unresolved until registered surface/fluid testing")


@dataclass(frozen=True, slots=True)
class DistributionManifoldArchitecture:
    source_coverage_sha256: str
    outlets: tuple[ManifoldOutlet, ...]
    branches: tuple[ManifoldBranch, ...]
    grooves: tuple[DistributionGrooveIntent, ...]
    outlet_count_status: str
    geometry_status: str
    evidence_status: str
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_coverage_sha256) != 64:
            raise DistributionManifoldError("Manifold must bind to an exact coverage SHA-256")
        water = [outlet for outlet in self.outlets if outlet.fluid_role == "WATER"]
        cleanser = [outlet for outlet in self.outlets if outlet.fluid_role == "CLEANSER"]
        if len(water) != 18 or len(cleanser) != 6:
            raise DistributionManifoldError("First-manifold baseline requires 18 water and 6 cleanser outlets")
        ids = [outlet.outlet_id for outlet in self.outlets]
        if len(ids) != len(set(ids)):
            raise DistributionManifoldError("Outlet IDs must be unique")
        if {groove.outlet_id for groove in self.grooves} != set(ids):
            raise DistributionManifoldError("Each outlet requires exactly one distribution-groove intent")
        if self.physical_validation_eligible:
            raise DistributionManifoldError("Digital manifold topology is not distribution or efficacy evidence")

    def cad_outlet_references(self, fluid_role: str) -> cq.Workplane:
        selected = [outlet for outlet in self.outlets if outlet.fluid_role == fluid_role]
        if not selected:
            raise DistributionManifoldError(f"No outlets for role {fluid_role!r}")
        radius = selected[0].diameter_seed_mm / 2.0
        points = [(outlet.center_mm.x, outlet.center_mm.y) for outlet in selected]
        wires = cq.Workplane("XY").pushPoints(points).circle(radius)
        return cq.Workplane("XY").newObject([cq.Compound.makeCompound(wires.vals())])

    @property
    def topology_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        result: dict[str, object] = {
            "source_coverage_sha256": self.source_coverage_sha256,
            "outlets": [
                {
                    **asdict(outlet),
                    "center_mm": list(outlet.center_mm.as_tuple()),
                    "direction": list(outlet.direction.as_tuple()),
                }
                for outlet in self.outlets
            ],
            "branches": [asdict(branch) for branch in self.branches],
            "grooves": [
                {
                    **asdict(groove),
                    "origin_mm": list(groove.origin_mm.as_tuple()),
                    "lateral_direction": list(groove.lateral_direction.as_tuple()),
                }
                for groove in self.grooves
            ],
            "outlet_count_status": self.outlet_count_status,
            "geometry_status": self.geometry_status,
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            result["topology_sha256"] = self.topology_sha256
        return result


def _protected_margin_mm(point: Point2, protected: ProtectedVolumeSet) -> float:
    margins = []
    for volume in protected.all:
        margins.append(volume.zone.conservative_radial_margin_xy_mm(point))
    return min(margins)


def _farthest_sample(candidates, count: int, required_regions: tuple[str, ...]):
    selected = []
    for region in required_regions:
        regional = [triangle for triangle in candidates if triangle.region_id == region]
        if not regional:
            raise DistributionManifoldError(f"No eligible outlet candidates in {region}")
        seed = min(regional, key=lambda triangle: (abs(triangle.centroid.x), -triangle.centroid.y, triangle.triangle_index))
        if seed not in selected:
            selected.append(seed)
    while len(selected) < count:
        remaining = [triangle for triangle in candidates if triangle not in selected]
        if not remaining:
            raise DistributionManifoldError("Insufficient eligible triangles for outlet count")
        next_triangle = max(
            remaining,
            key=lambda triangle: (
                min(math.dist(triangle.centroid.as_tuple(), item.centroid.as_tuple()) for item in selected),
                -triangle.triangle_index,
            ),
        )
        selected.append(next_triangle)
    return tuple(selected)


def build_distribution_manifold(
    authority: Authority,
    coverage: FacialCoverageMesh,
    protected: ProtectedVolumeSet,
) -> DistributionManifoldArchitecture:
    diameter = authority.number("fluid", "outlets", "manifold_outlet_diameter_seed_mm")
    position_sensitivity = authority.number("fluid", "outlets", "outlet_position_sensitivity_mm")
    direction_sensitivity = authority.number("fluid", "outlets", "outlet_direction_sensitivity_deg")
    clearance = diameter / 2.0 + position_sensitivity
    candidates = tuple(
        triangle
        for triangle in coverage.target_triangles
        if _protected_margin_mm(Point2(triangle.centroid.x, triangle.centroid.y), protected) >= clearance
    )
    water_count = int(authority.number("fluid", "outlets", "water_count_first_manifold"))
    cleanser_count = int(authority.number("fluid", "outlets", "cleanser_count_first_manifold"))
    water_triangles = _farthest_sample(
        candidates, water_count, (REGION_ACTIVE_OTHER, REGION_T_FOREHEAD, REGION_T_NOSE_PHILTRUM)
    )
    cleanser_candidates = tuple(triangle for triangle in candidates if triangle not in water_triangles)
    cleanser_triangles = _farthest_sample(
        cleanser_candidates, cleanser_count, (REGION_ACTIVE_OTHER, REGION_T_FOREHEAD, REGION_T_NOSE_PHILTRUM)
    )

    outlets = []
    for fluid_role, triangles in (("WATER", water_triangles), ("CLEANSER", cleanser_triangles)):
        for index, triangle in enumerate(triangles, start=1):
            sign = -1.0 if triangle.centroid.x < 0.0 else 1.0
            if abs(triangle.centroid.x) <= 1e-9:
                sign = -1.0 if index % 2 else 1.0
            outlets.append(
                ManifoldOutlet(
                    f"OUTLET_{fluid_role}_{index:02d}", fluid_role, triangle.triangle_index,
                    triangle.region_id, triangle.centroid, diameter, Vector3(sign, 0.0, 0.0),
                    position_sensitivity, direction_sensitivity,
                    "LATERAL_OR_SUBSURFACE_INTO_SKIN_FACING_GROOVE_NOT_DIRECT_FACE_JET",
                    "DEVELOPMENT_POSITION_AND_DIRECTION_SEED_REQUIRES_METERING_AND_INGRESS_RIG",
                )
            )
    outlet_tuple = tuple(outlets)
    branches = tuple(
        ManifoldBranch(
            f"MANIFOLD_BRANCH_{role}", role, f"ROUTE_{role}_PUMP_TO_MANIFOLD_I23",
            tuple(outlet.outlet_id for outlet in outlet_tuple if outlet.fluid_role == role),
            None, None,
            "BLOCKED_UNTIL_BORE_RESTRICTION_VISCOSITY_AND_PUMP_CURVE_ARE_CONTROLLED",
            "TARGET_EQUALIZATION_MODEL_SCHEMA_ONLY_NO_METERING_RIG_EVIDENCE",
        )
        for role in ("WATER", "CLEANSER")
    )
    grooves = tuple(
        DistributionGrooveIntent(
            f"GROOVE_{outlet.outlet_id}", outlet.outlet_id, outlet.center_mm, outlet.direction,
            None, None, None,
            "CENTERLINE_DIRECTION_INTENT_ONLY_REQUIRES_REGISTERED_SKIN_FACING_SURFACE",
            "NOT_DISTRIBUTION_RESIDUAL_FLUID_CLEANABILITY_OR_CLEANSING_EVIDENCE",
        )
        for outlet in outlet_tuple
    )
    return DistributionManifoldArchitecture(
        coverage.segmentation_sha256, outlet_tuple, branches, grooves,
        str(authority.get("fluid", "outlets", "count_status")),
        "ITERATIONS23_24_PARAMETRIC_BRANCH_OUTLET_AND_LATERAL_GROOVE_INTENT",
        "NOT_METERING_PRESSURE_DROP_INGRESS_DISTRIBUTION_RESIDUAL_OR_EFFICACY_VALIDATION",
    )
