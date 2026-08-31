"""Iteration 24 skin-facing outlet placement and lateral groove intent.

Positions are deterministic development references on the current target mesh. They
are not registered anatomical geometry. Directions remain in the local XY development
plane and point away from the nearest protected-zone center. Groove dimensions and
physical distribution performance remain unresolved.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from .authority import Authority
from .cleanser_storage import CleanserStorageArchitecture
from .coverage import (
    REGION_ACTIVE_OTHER,
    REGION_T_FOREHEAD,
    REGION_T_NOSE_PHILTRUM,
    CoverageTriangle,
    FacialCoverageMesh,
)
from .distribution_manifold import (
    DistributionManifoldArchitecture,
    DistributionManifoldError,
)
from .fresh_pump_packaging import (
    FLUID_CLEANSER,
    FLUID_FRESH_WATER,
    FreshPumpPackagingArchitecture,
)
from .protected_volumes import ProtectedVolume, ProtectedVolumeSet
from .spatial import Point2
from .structural_frame import StructuralFrameTopology
from .water_reservoir import WaterReservoirArchitecture


class DistributionGeometryError(ValueError):
    """Raised when Iteration 24 geometry or evidence boundaries are violated."""


ACTIVE_REGION_IDS = frozenset(
    {
        REGION_ACTIVE_OTHER,
        REGION_T_FOREHEAD,
        REGION_T_NOSE_PHILTRUM,
    }
)
PLACEMENT_STATUS = "DEVELOPMENT_TARGET_TRIANGLE_CENTROID_NOT_REGISTERED_ANATOMICAL_POSITION"
DIRECTION_RULE = "LATERAL_XY_AWAY_FROM_NEAREST_PROTECTED_ZONE_CENTER_NOT_DIRECT_FACE_JET"
OUTLET_EVIDENCE_STATUS = (
    "DIGITAL_POSITION_AND_DIRECTION_SENSITIVITY_SEED_ONLY_NOT_INGRESS_DISTRIBUTION_"
    "RESIDUAL_FLUID_OR_PHYSICAL_EVIDENCE"
)
GROOVE_SURFACE_STATUS = "CENTERLINE_INTENT_ONLY_REQUIRES_REGISTERED_SKIN_FACING_SURFACE"
GROOVE_EVIDENCE_STATUS = (
    "DIMENSIONS_UNRESOLVED_NOT_FLOW_CLEANABILITY_RESIDUAL_FLUID_OR_CLEANSING_EVIDENCE"
)
ARCHITECTURE_EVIDENCE_STATUS = (
    "DIGITAL_ACTIVE_TARGET_PLACEMENT_AND_LATERAL_GROOVE_INTENT_ONLY_NOT_REGISTERED_"
    "ANATOMY_INGRESS_DISTRIBUTION_CLEANABILITY_EFFICACY_OR_PHYSICAL_VALIDATION"
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _sha(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise DistributionGeometryError(f"{label} must be a canonical lowercase SHA-256")
    return value


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise DistributionGeometryError(f"{label} must be exact built-in nonblank text")
    return value


def _real(
    value: object,
    *,
    label: str,
    positive: bool = False,
    nonnegative: bool = False,
) -> float:
    if type(value) not in (int, float):
        raise DistributionGeometryError(f"{label} must be a finite real number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise DistributionGeometryError(f"{label} must be representable as a finite float") from exc
    if not math.isfinite(result):
        raise DistributionGeometryError(f"{label} must be finite")
    if positive and result <= 0.0:
        raise DistributionGeometryError(f"{label} must be positive")
    if nonnegative and result < 0.0:
        raise DistributionGeometryError(f"{label} must be non-negative")
    return result


def _point3(value: object, *, label: str) -> tuple[float, float, float]:
    if type(value) is not tuple or len(value) != 3:
        raise DistributionGeometryError(f"{label} must be an exact three-value tuple")
    result = tuple(_real(item, label=f"{label} component") for item in value)
    return result[0], result[1], result[2]


def _vector3(value: object, *, label: str) -> tuple[float, float, float]:
    result = _point3(value, label=label)
    norm = math.sqrt(sum(component * component for component in result))
    if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise DistributionGeometryError(f"{label} must be a unit vector")
    if not math.isclose(result[2], 0.0, rel_tol=0.0, abs_tol=1e-12):
        raise DistributionGeometryError(f"{label} must remain lateral in the development XY plane")
    return result


def _protected_sha256(protected: ProtectedVolumeSet) -> str:
    raw = json.dumps(
        protected.manifest(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _local_xy(point: Point2, volume: ProtectedVolume) -> tuple[float, float]:
    zone = volume.zone
    dx = point.x - zone.center.x
    dy = point.y - zone.center.y
    angle = math.radians(-zone.angle_deg)
    cosine, sine = math.cos(angle), math.sin(angle)
    return cosine * dx - sine * dy, sine * dx + cosine * dy


def _clearance_to_zone_mm(point: Point2, volume: ProtectedVolume) -> float:
    local_x, local_y = _local_xy(point, volume)
    x = abs(local_x)
    y = abs(local_y)
    a = volume.zone.envelope_width_mm / 2.0
    b = volume.zone.envelope_height_mm / 2.0
    normalized = (x / a) ** 2 + (y / b) ** 2
    if normalized <= 1.0:
        # Interior points are always ineligible. A negative conservative sentinel is
        # sufficient; exterior candidates receive the exact Euclidean solution below.
        if x <= 1e-15 and y <= 1e-15:
            return -min(a, b)
        return -min(a, b) * (1.0 - math.sqrt(normalized))
    if math.isclose(a, b, rel_tol=0.0, abs_tol=1e-15):
        return math.hypot(x, y) - a

    # For an exterior point, the closest ellipse point is obtained from the unique
    # non-negative Lagrange multiplier satisfying this monotone equation.
    def residual(multiplier: float) -> float:
        return (
            (a * x / (multiplier + a * a)) ** 2
            + (b * y / (multiplier + b * b)) ** 2
            - 1.0
        )

    lower = 0.0
    upper = max(a * x, b * y, a * a, b * b)
    while residual(upper) > 0.0:
        upper *= 2.0
    for _ in range(80):
        midpoint = (lower + upper) / 2.0
        if residual(midpoint) > 0.0:
            lower = midpoint
        else:
            upper = midpoint
    multiplier = (lower + upper) / 2.0
    closest_x = a * a * x / (multiplier + a * a)
    closest_y = b * b * y / (multiplier + b * b)
    distance = math.hypot(x - closest_x, y - closest_y)
    if distance <= 1e-15:
        return 0.0
    return distance


def _protected_clearance_mm(point: Point2, protected: ProtectedVolumeSet) -> float:
    return min(_clearance_to_zone_mm(point, volume) for volume in protected.all)


def _nearest_protected_volume(point: Point2, protected: ProtectedVolumeSet) -> ProtectedVolume:
    return min(
        protected.all,
        key=lambda volume: (
            (point.x - volume.zone.center.x) ** 2 + (point.y - volume.zone.center.y) ** 2,
            volume.zone.zone_id,
        ),
    )


def _direction_away_from_nearest(
    point: Point2,
    protected: ProtectedVolumeSet,
) -> tuple[float, float, float]:
    nearest = _nearest_protected_volume(point, protected)
    dx = point.x - nearest.zone.center.x
    dy = point.y - nearest.zone.center.y
    norm = math.hypot(dx, dy)
    if norm <= 1e-15:
        raise DistributionGeometryError("outlet cannot coincide with a protected-zone center")
    return dx / norm, dy / norm, 0.0


def _farthest_sample(
    candidates: tuple[CoverageTriangle, ...],
    count: int,
) -> tuple[CoverageTriangle, ...]:
    selected: list[CoverageTriangle] = []
    for region_id in (
        REGION_ACTIVE_OTHER,
        REGION_T_FOREHEAD,
        REGION_T_NOSE_PHILTRUM,
    ):
        regional = tuple(item for item in candidates if item.region_id == region_id)
        if not regional:
            raise DistributionGeometryError(f"no eligible outlet candidates in {region_id}")
        seed = min(
            regional,
            key=lambda item: (
                abs(item.centroid.x),
                -item.centroid.y,
                item.triangle_index,
            ),
        )
        if seed not in selected:
            selected.append(seed)
    if count < len(selected):
        raise DistributionGeometryError("outlet count cannot cover the controlled active-region seed set")
    while len(selected) < count:
        remaining = tuple(item for item in candidates if item not in selected)
        if not remaining:
            raise DistributionGeometryError("insufficient eligible triangles for outlet placement")
        selected.append(
            max(
                remaining,
                key=lambda item: (
                    min(
                        (item.centroid.x - chosen.centroid.x) ** 2
                        + (item.centroid.y - chosen.centroid.y) ** 2
                        for chosen in selected
                    ),
                    -item.triangle_index,
                ),
            )
        )
    return tuple(selected)


@dataclass(frozen=True, slots=True)
class OutletPlacement:
    outlet_id: str
    fluid_identity: str
    source_triangle_index: int
    region_id: str
    center_xyz_mm: tuple[float, float, float]
    lateral_direction_xyz: tuple[float, float, float]
    protected_clearance_mm: float
    required_clearance_mm: float
    placement_status: str
    direction_rule: str
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.outlet_id, label="outlet placement ID")
        if type(self.fluid_identity) is not str or self.fluid_identity not in {
            FLUID_FRESH_WATER,
            FLUID_CLEANSER,
        }:
            raise DistributionGeometryError("outlet placement fluid identity is not controlled")
        if type(self.source_triangle_index) is not int or self.source_triangle_index < 0:
            raise DistributionGeometryError("source triangle index must be an exact non-negative integer")
        if type(self.region_id) is not str or self.region_id not in ACTIVE_REGION_IDS:
            raise DistributionGeometryError("outlet placement must use a controlled active target region")
        center = _point3(self.center_xyz_mm, label="outlet center")
        direction = _vector3(self.lateral_direction_xyz, label="outlet lateral direction")
        margin = _real(
            self.protected_clearance_mm,
            label="protected clearance",
            nonnegative=True,
        )
        required = _real(self.required_clearance_mm, label="required clearance", positive=True)
        if margin + 1e-12 < required:
            raise DistributionGeometryError("outlet placement violates protected-region clearance")
        controlled = (
            (self.placement_status, PLACEMENT_STATUS, "outlet placement status"),
            (self.direction_rule, DIRECTION_RULE, "outlet direction rule"),
            (self.evidence_status, OUTLET_EVIDENCE_STATUS, "outlet evidence status"),
        )
        for value, expected, label in controlled:
            if type(value) is not str or value != expected:
                raise DistributionGeometryError(f"{label} must use its controlled state")
        object.__setattr__(self, "center_xyz_mm", center)
        object.__setattr__(self, "lateral_direction_xyz", direction)
        object.__setattr__(self, "protected_clearance_mm", margin)
        object.__setattr__(self, "required_clearance_mm", required)

    def manifest(self) -> dict[str, object]:
        return {
            "outlet_id": self.outlet_id,
            "fluid_identity": self.fluid_identity,
            "source_triangle_index": self.source_triangle_index,
            "region_id": self.region_id,
            "center_xyz_mm": list(self.center_xyz_mm),
            "lateral_direction_xyz": list(self.lateral_direction_xyz),
            "protected_clearance_mm": self.protected_clearance_mm,
            "required_clearance_mm": self.required_clearance_mm,
            "placement_status": self.placement_status,
            "direction_rule": self.direction_rule,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class DistributionGrooveIntent:
    groove_id: str
    outlet_id: str
    origin_xyz_mm: tuple[float, float, float]
    lateral_direction_xyz: tuple[float, float, float]
    width_mm: float | None
    depth_mm: float | None
    length_mm: float | None
    surface_status: str
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.groove_id, label="groove ID")
        _text(self.outlet_id, label="groove outlet ID")
        if self.groove_id != f"DISTRIBUTION-GROOVE-{self.outlet_id}":
            raise DistributionGeometryError("groove ID must derive from its outlet ID")
        origin = _point3(self.origin_xyz_mm, label="groove origin")
        direction = _vector3(self.lateral_direction_xyz, label="groove lateral direction")
        if any(value is not None for value in (self.width_mm, self.depth_mm, self.length_mm)):
            raise DistributionGeometryError("Iteration 24 cannot invent distribution-groove dimensions")
        if type(self.surface_status) is not str or self.surface_status != GROOVE_SURFACE_STATUS:
            raise DistributionGeometryError("groove surface status must use the controlled unresolved state")
        if type(self.evidence_status) is not str or self.evidence_status != GROOVE_EVIDENCE_STATUS:
            raise DistributionGeometryError("groove evidence status must use the controlled unresolved state")
        object.__setattr__(self, "origin_xyz_mm", origin)
        object.__setattr__(self, "lateral_direction_xyz", direction)

    def manifest(self) -> dict[str, object]:
        return {
            "groove_id": self.groove_id,
            "outlet_id": self.outlet_id,
            "origin_xyz_mm": list(self.origin_xyz_mm),
            "lateral_direction_xyz": list(self.lateral_direction_xyz),
            "width_mm": self.width_mm,
            "depth_mm": self.depth_mm,
            "length_mm": self.length_mm,
            "surface_status": self.surface_status,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class DistributionGeometryArchitecture:
    source_manifold_architecture_sha256: str
    source_coverage_segmentation_sha256: str
    source_protected_volumes_sha256: str
    eligible_candidate_count: int
    required_clearance_mm: float
    placements: tuple[OutletPlacement, ...]
    grooves: tuple[DistributionGrooveIntent, ...]
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        _sha(self.source_manifold_architecture_sha256, label="source manifold architecture")
        _sha(self.source_coverage_segmentation_sha256, label="source coverage segmentation")
        _sha(self.source_protected_volumes_sha256, label="source protected volumes")
        if type(self.eligible_candidate_count) is not int or self.eligible_candidate_count <= 0:
            raise DistributionGeometryError("eligible candidate count must be an exact positive integer")
        required = _real(self.required_clearance_mm, label="required clearance", positive=True)
        if type(self.placements) is not tuple or not self.placements or any(
            type(item) is not OutletPlacement for item in self.placements
        ):
            raise DistributionGeometryError("outlet placements must be an immutable tuple of exact records")
        outlet_ids = tuple(item.outlet_id for item in self.placements)
        if len(outlet_ids) != len(set(outlet_ids)):
            raise DistributionGeometryError("outlet placement IDs cannot repeat")
        triangle_indices = tuple(item.source_triangle_index for item in self.placements)
        if len(triangle_indices) != len(set(triangle_indices)):
            raise DistributionGeometryError("outlet placements cannot share source triangles")
        if any(item.required_clearance_mm != required for item in self.placements):
            raise DistributionGeometryError("outlet placements must retain the architecture margin rule")
        if type(self.grooves) is not tuple or any(
            type(item) is not DistributionGrooveIntent for item in self.grooves
        ):
            raise DistributionGeometryError("grooves must be an immutable tuple of exact intent records")
        if tuple(item.outlet_id for item in self.grooves) != outlet_ids:
            raise DistributionGeometryError("every outlet requires one ordered distribution-groove intent")
        for placement, groove in zip(self.placements, self.grooves, strict=True):
            if (
                groove.origin_xyz_mm != placement.center_xyz_mm
                or groove.lateral_direction_xyz != placement.lateral_direction_xyz
            ):
                raise DistributionGeometryError("groove origin and direction must bind exactly to its outlet")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise DistributionGeometryError("digital distribution geometry cannot be physical validation evidence")
        if type(self.evidence_status) is not str or self.evidence_status != ARCHITECTURE_EVIDENCE_STATUS:
            raise DistributionGeometryError("distribution geometry evidence status must use the controlled state")
        object.__setattr__(self, "required_clearance_mm", required)

    def validate_current_sources(
        self,
        *,
        authority: Authority,
        manifold: DistributionManifoldArchitecture,
        pump: FreshPumpPackagingArchitecture,
        water: WaterReservoirArchitecture,
        cleanser: CleanserStorageArchitecture,
        frame: StructuralFrameTopology,
        coverage: FacialCoverageMesh,
        protected: ProtectedVolumeSet,
    ) -> None:
        if type(authority) is not Authority:
            raise DistributionGeometryError("authority must be an exact Authority contract")
        if type(manifold) is not DistributionManifoldArchitecture:
            raise DistributionGeometryError("manifold must be an exact DistributionManifoldArchitecture")
        if type(coverage) is not FacialCoverageMesh:
            raise DistributionGeometryError("coverage must be an exact FacialCoverageMesh")
        if type(protected) is not ProtectedVolumeSet:
            raise DistributionGeometryError("protected must be an exact ProtectedVolumeSet")
        try:
            manifold.validate_current_sources(
                authority=authority,
                pump=pump,
                water=water,
                cleanser=cleanser,
                frame=frame,
            )
        except DistributionManifoldError as exc:
            raise DistributionGeometryError("manifold architecture is stale for current sources") from exc
        expected_required = (
            manifold.outlet_diameter_seed_mm / 2.0
            + manifold.outlet_position_sensitivity_mm
        )
        if self.source_manifold_architecture_sha256 != manifold.architecture_sha256:
            raise DistributionGeometryError("distribution geometry is stale for current manifold")
        if self.source_coverage_segmentation_sha256 != coverage.segmentation_sha256:
            raise DistributionGeometryError("distribution geometry is stale for current coverage")
        if self.source_protected_volumes_sha256 != _protected_sha256(protected):
            raise DistributionGeometryError("distribution geometry is stale for current protected volumes")
        if not math.isclose(
            self.required_clearance_mm,
            expected_required,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise DistributionGeometryError("distribution geometry margin rule is stale")
        if tuple(item.outlet_id for item in self.placements) != tuple(
            item.outlet_id for item in manifold.outlets
        ):
            raise DistributionGeometryError("distribution geometry outlet order is stale for manifold")
        expected_candidate_count = sum(
            1
            for triangle in coverage.target_triangles
            if triangle.region_id in ACTIVE_REGION_IDS
            and _protected_clearance_mm(
                Point2(triangle.centroid.x, triangle.centroid.y),
                protected,
            )
            + 1e-12
            >= expected_required
        )
        if self.eligible_candidate_count != expected_candidate_count:
            raise DistributionGeometryError("eligible candidate ledger is stale for current sources")
        for placement, reservation in zip(self.placements, manifold.outlets, strict=True):
            if placement.source_triangle_index >= len(coverage.triangles):
                raise DistributionGeometryError("outlet source triangle index is outside current coverage")
            triangle = coverage.triangles[placement.source_triangle_index]
            expected_center = triangle.centroid.as_tuple()
            point = Point2(triangle.centroid.x, triangle.centroid.y)
            expected_margin = _protected_clearance_mm(point, protected)
            expected_direction = _direction_away_from_nearest(point, protected)
            if not triangle.is_target or triangle.region_id not in ACTIVE_REGION_IDS:
                raise DistributionGeometryError("outlet source triangle is not an active target")
            if placement.fluid_identity != reservation.fluid_identity:
                raise DistributionGeometryError("outlet placement fluid identity is stale for manifold")
            if placement.region_id != triangle.region_id or placement.center_xyz_mm != expected_center:
                raise DistributionGeometryError("outlet placement is stale for current target triangle")
            if not math.isclose(
                placement.protected_clearance_mm,
                expected_margin,
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise DistributionGeometryError("outlet protected-region margin is stale")
            if any(
                not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12)
                for actual, expected in zip(
                    placement.lateral_direction_xyz,
                    expected_direction,
                    strict=True,
                )
            ):
                raise DistributionGeometryError("outlet direction no longer follows the protected-region rule")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "source_manifold_architecture_sha256": self.source_manifold_architecture_sha256,
            "source_coverage_segmentation_sha256": self.source_coverage_segmentation_sha256,
            "source_protected_volumes_sha256": self.source_protected_volumes_sha256,
            "eligible_candidate_count": self.eligible_candidate_count,
            "required_clearance_mm": self.required_clearance_mm,
            "placements": [item.manifest() for item in self.placements],
            "grooves": [item.manifest() for item in self.grooves],
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_distribution_geometry_architecture(
    authority: Authority,
    manifold: DistributionManifoldArchitecture,
    pump: FreshPumpPackagingArchitecture,
    water: WaterReservoirArchitecture,
    cleanser: CleanserStorageArchitecture,
    frame: StructuralFrameTopology,
    coverage: FacialCoverageMesh,
    protected: ProtectedVolumeSet,
) -> DistributionGeometryArchitecture:
    if type(authority) is not Authority:
        raise DistributionGeometryError("authority must be an exact Authority contract")
    if type(manifold) is not DistributionManifoldArchitecture:
        raise DistributionGeometryError("manifold must be an exact DistributionManifoldArchitecture")
    if type(coverage) is not FacialCoverageMesh:
        raise DistributionGeometryError("coverage must be an exact FacialCoverageMesh")
    if type(protected) is not ProtectedVolumeSet:
        raise DistributionGeometryError("protected must be an exact ProtectedVolumeSet")
    required_margin = (
        manifold.outlet_diameter_seed_mm / 2.0
        + manifold.outlet_position_sensitivity_mm
    )
    candidates = tuple(
        triangle
        for triangle in coverage.target_triangles
        if triangle.region_id in ACTIVE_REGION_IDS
        and _protected_clearance_mm(
            Point2(triangle.centroid.x, triangle.centroid.y),
            protected,
        )
        + 1e-12
        >= required_margin
    )
    water_count = manifold.water_outlet_count
    water_triangles = _farthest_sample(candidates, water_count)
    cleanser_candidates = tuple(item for item in candidates if item not in water_triangles)
    cleanser_triangles = _farthest_sample(
        cleanser_candidates,
        manifold.cleanser_outlet_count,
    )
    triangles = water_triangles + cleanser_triangles
    if len(triangles) != len(manifold.outlets):
        raise DistributionGeometryError("selected triangle count does not match manifold reservations")
    placements = tuple(
        OutletPlacement(
            outlet_id=reservation.outlet_id,
            fluid_identity=reservation.fluid_identity,
            source_triangle_index=triangle.triangle_index,
            region_id=triangle.region_id,
            center_xyz_mm=triangle.centroid.as_tuple(),
            lateral_direction_xyz=_direction_away_from_nearest(
                Point2(triangle.centroid.x, triangle.centroid.y),
                protected,
            ),
            protected_clearance_mm=_protected_clearance_mm(
                Point2(triangle.centroid.x, triangle.centroid.y),
                protected,
            ),
            required_clearance_mm=required_margin,
            placement_status=PLACEMENT_STATUS,
            direction_rule=DIRECTION_RULE,
            evidence_status=OUTLET_EVIDENCE_STATUS,
        )
        for reservation, triangle in zip(manifold.outlets, triangles, strict=True)
    )
    grooves = tuple(
        DistributionGrooveIntent(
            groove_id=f"DISTRIBUTION-GROOVE-{placement.outlet_id}",
            outlet_id=placement.outlet_id,
            origin_xyz_mm=placement.center_xyz_mm,
            lateral_direction_xyz=placement.lateral_direction_xyz,
            width_mm=None,
            depth_mm=None,
            length_mm=None,
            surface_status=GROOVE_SURFACE_STATUS,
            evidence_status=GROOVE_EVIDENCE_STATUS,
        )
        for placement in placements
    )
    architecture = DistributionGeometryArchitecture(
        source_manifold_architecture_sha256=manifold.architecture_sha256,
        source_coverage_segmentation_sha256=coverage.segmentation_sha256,
        source_protected_volumes_sha256=_protected_sha256(protected),
        eligible_candidate_count=len(candidates),
        required_clearance_mm=required_margin,
        placements=placements,
        grooves=grooves,
        physical_validation_eligible=False,
        evidence_status=ARCHITECTURE_EVIDENCE_STATUS,
    )
    architecture.validate_current_sources(
        authority=authority,
        manifold=manifold,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=coverage,
        protected=protected,
    )
    return architecture
