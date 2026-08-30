from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from collections import defaultdict, deque
from typing import Iterable

from .anatomy import FacialReferenceLayer
from .authority import Authority
from .facial_surface import FacialSurface
from .protected_volumes import ProtectedVolumeSet
from .spatial import Point2, Point3


class CoverageError(ValueError):
    """Raised when facial-region segmentation or coverage evaluation violates its contract."""


REGION_ACTIVE_OTHER = "ACTIVE_FACE_OTHER"
REGION_T_FOREHEAD = "T_ZONE_FOREHEAD"
REGION_T_NOSE_PHILTRUM = "T_ZONE_NOSE_PHILTRUM"
REGION_PROTECTED_EYE_LEFT = "PROTECTED_EYE_LEFT"
REGION_PROTECTED_EYE_RIGHT = "PROTECTED_EYE_RIGHT"
REGION_PROTECTED_MOUTH = "PROTECTED_MOUTH"
REGION_PROTECTED_NOSTRIL_LEFT = "PROTECTED_NOSTRIL_LEFT"
REGION_PROTECTED_NOSTRIL_RIGHT = "PROTECTED_NOSTRIL_RIGHT"

PROTECTED_REGION_BY_ZONE_ID = {
    "MASCK_ONE-PROTECTED-EYE-LEFT": REGION_PROTECTED_EYE_LEFT,
    "MASCK_ONE-PROTECTED-EYE-RIGHT": REGION_PROTECTED_EYE_RIGHT,
    "MASCK_ONE-PROTECTED-MOUTH": REGION_PROTECTED_MOUTH,
    "MASCK_ONE-PROTECTED-NOSTRIL-LEFT": REGION_PROTECTED_NOSTRIL_LEFT,
    "MASCK_ONE-PROTECTED-NOSTRIL-RIGHT": REGION_PROTECTED_NOSTRIL_RIGHT,
}


@dataclass(frozen=True, slots=True)
class TZoneDevelopmentDefinition:
    """Deterministic development-only T-zone segmentation.

    The authority freezes T-zone coverage targets but does not freeze an anatomical
    T-zone boundary. This definition therefore derives a reproducible engineering
    baseline from existing authority landmarks/apertures. It is not promoted to an
    anatomical definition or product-validation truth.
    """

    stem_half_width_mm: float
    stem_y_min_mm: float
    stem_y_max_mm: float
    forehead_half_width_mm: float
    forehead_y_min_mm: float
    evidence_status: str = "CAD_CLOSURE_BASELINE_DERIVED_FROM_AUTHORITY_GEOMETRY_NOT_ANATOMICAL_VALIDATION"

    def __post_init__(self) -> None:
        values = {
            "stem_half_width_mm": self.stem_half_width_mm,
            "stem_y_min_mm": self.stem_y_min_mm,
            "stem_y_max_mm": self.stem_y_max_mm,
            "forehead_half_width_mm": self.forehead_half_width_mm,
            "forehead_y_min_mm": self.forehead_y_min_mm,
        }
        for label, raw in values.items():
            value = float(raw)
            if not math.isfinite(value):
                raise CoverageError(f"{label} must be finite")
            object.__setattr__(self, label, value)
        if self.stem_half_width_mm <= 0.0 or self.forehead_half_width_mm <= 0.0:
            raise CoverageError("T-zone widths must be positive")
        if self.stem_y_min_mm >= self.stem_y_max_mm:
            raise CoverageError("T-zone stem must have positive Y extent")
        if not math.isclose(self.stem_y_max_mm, self.forehead_y_min_mm, rel_tol=0.0, abs_tol=1e-12):
            raise CoverageError("T-zone stem and forehead crossbar must meet without an unexplained Y gap")
        if not self.evidence_status.strip():
            raise CoverageError("T-zone evidence_status must be non-empty")

    def region_for(self, point: Point2) -> str | None:
        if (
            abs(point.x) <= self.stem_half_width_mm + 1e-12
            and self.stem_y_min_mm - 1e-12 <= point.y <= self.stem_y_max_mm + 1e-12
        ):
            return REGION_T_NOSE_PHILTRUM
        if (
            abs(point.x) <= self.forehead_half_width_mm + 1e-12
            and point.y >= self.forehead_y_min_mm - 1e-12
        ):
            return REGION_T_FOREHEAD
        return None

    @property
    def t_zone_region_ids(self) -> tuple[str, str]:
        return (REGION_T_FOREHEAD, REGION_T_NOSE_PHILTRUM)

    def manifest(self) -> dict[str, object]:
        return {
            "stem_half_width_mm": self.stem_half_width_mm,
            "stem_y_min_mm": self.stem_y_min_mm,
            "stem_y_max_mm": self.stem_y_max_mm,
            "forehead_half_width_mm": self.forehead_half_width_mm,
            "forehead_y_min_mm": self.forehead_y_min_mm,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class CoverageTriangle:
    triangle_index: int
    vertex_indices: tuple[int, int, int]
    centroid: Point3
    area_mm2: float
    region_id: str
    protected_zone_id: str | None
    is_target: bool
    is_t_zone_target: bool

    def __post_init__(self) -> None:
        if self.triangle_index < 0:
            raise CoverageError("triangle_index cannot be negative")
        if len(set(self.vertex_indices)) != 3:
            raise CoverageError("Coverage triangle must have three distinct vertices")
        area = float(self.area_mm2)
        if not math.isfinite(area) or area <= 0.0:
            raise CoverageError("Coverage triangle area must be finite and positive")
        object.__setattr__(self, "area_mm2", area)
        if not self.region_id.strip():
            raise CoverageError("Coverage triangle region_id must be non-empty")
        if self.is_t_zone_target and not self.is_target:
            raise CoverageError("A T-zone target triangle must also be an active target triangle")
        if self.protected_zone_id is not None and self.is_target:
            raise CoverageError("Protected-zone triangles cannot be active cleansing targets")


@dataclass(frozen=True, slots=True)
class CoverageEvaluation:
    aggregate_percent: float
    t_zone_percent: float
    largest_uncovered_hole_mm2: float
    aggregate_min_percent: float
    t_zone_min_percent: float
    unexplained_hole_max_mm2: float
    numeric_gate_passed: bool
    product_validation_status: str
    evidence_status: str
    covered_target_triangle_count: int
    target_triangle_count: int
    covered_target_area_mm2: float
    target_area_mm2: float
    covered_t_zone_area_mm2: float
    t_zone_target_area_mm2: float
    evaluation_sha256: str

    def manifest(self) -> dict[str, object]:
        return {
            "aggregate_percent": self.aggregate_percent,
            "t_zone_percent": self.t_zone_percent,
            "largest_uncovered_hole_mm2": self.largest_uncovered_hole_mm2,
            "aggregate_min_percent": self.aggregate_min_percent,
            "t_zone_min_percent": self.t_zone_min_percent,
            "unexplained_hole_max_mm2": self.unexplained_hole_max_mm2,
            "numeric_gate_passed": self.numeric_gate_passed,
            "product_validation_status": self.product_validation_status,
            "evidence_status": self.evidence_status,
            "covered_target_triangle_count": self.covered_target_triangle_count,
            "target_triangle_count": self.target_triangle_count,
            "covered_target_area_mm2": self.covered_target_area_mm2,
            "target_area_mm2": self.target_area_mm2,
            "covered_t_zone_area_mm2": self.covered_t_zone_area_mm2,
            "t_zone_target_area_mm2": self.t_zone_target_area_mm2,
            "evaluation_sha256": self.evaluation_sha256,
        }


@dataclass(frozen=True, slots=True)
class FacialCoverageMesh:
    source_surface_id: str
    source_surface_sha256: str
    triangles: tuple[CoverageTriangle, ...]
    t_zone_definition: TZoneDevelopmentDefinition
    aggregate_min_percent: float
    t_zone_min_percent: float
    unexplained_hole_max_mm2: float
    segmentation_status: str
    anatomical_validation_eligible: bool

    def __post_init__(self) -> None:
        if not self.source_surface_id.strip() or not self.source_surface_sha256.strip():
            raise CoverageError("Coverage mesh source identity must be explicit")
        if len(self.source_surface_sha256) != 64:
            raise CoverageError("Coverage mesh source SHA-256 must be 64 characters")
        if not self.triangles:
            raise CoverageError("Coverage mesh cannot be empty")
        indices = [triangle.triangle_index for triangle in self.triangles]
        if indices != list(range(len(self.triangles))):
            raise CoverageError("Coverage triangle indices must be contiguous and deterministic")
        for label, value in {
            "aggregate_min_percent": self.aggregate_min_percent,
            "t_zone_min_percent": self.t_zone_min_percent,
            "unexplained_hole_max_mm2": self.unexplained_hole_max_mm2,
        }.items():
            number = float(value)
            if not math.isfinite(number) or number < 0.0:
                raise CoverageError(f"{label} must be finite and non-negative")
            object.__setattr__(self, label, number)
        if self.aggregate_min_percent > 100.0 or self.t_zone_min_percent > 100.0:
            raise CoverageError("Coverage percentage thresholds cannot exceed 100")
        if not self.segmentation_status.strip():
            raise CoverageError("segmentation_status must be non-empty")
        if self.target_area_mm2 <= 0.0 or self.t_zone_target_area_mm2 <= 0.0:
            raise CoverageError("Coverage mesh must contain nonzero active and T-zone target area")

    @property
    def total_surface_area_mm2(self) -> float:
        return sum(triangle.area_mm2 for triangle in self.triangles)

    @property
    def target_triangles(self) -> tuple[CoverageTriangle, ...]:
        return tuple(triangle for triangle in self.triangles if triangle.is_target)

    @property
    def protected_triangles(self) -> tuple[CoverageTriangle, ...]:
        return tuple(triangle for triangle in self.triangles if not triangle.is_target)

    @property
    def t_zone_target_triangles(self) -> tuple[CoverageTriangle, ...]:
        return tuple(triangle for triangle in self.triangles if triangle.is_t_zone_target)

    @property
    def target_area_mm2(self) -> float:
        return sum(triangle.area_mm2 for triangle in self.target_triangles)

    @property
    def protected_area_mm2(self) -> float:
        return sum(triangle.area_mm2 for triangle in self.protected_triangles)

    @property
    def t_zone_target_area_mm2(self) -> float:
        return sum(triangle.area_mm2 for triangle in self.t_zone_target_triangles)

    @property
    def area_conservation_error_mm2(self) -> float:
        return abs(self.total_surface_area_mm2 - self.target_area_mm2 - self.protected_area_mm2)

    @property
    def region_area_mm2(self) -> dict[str, float]:
        areas: dict[str, float] = defaultdict(float)
        for triangle in self.triangles:
            areas[triangle.region_id] += triangle.area_mm2
        return dict(sorted(areas.items()))

    @property
    def philtrum_target_area_mm2(self) -> float:
        return sum(
            triangle.area_mm2
            for triangle in self.triangles
            if triangle.is_target
            and triangle.region_id == REGION_T_NOSE_PHILTRUM
            and self.t_zone_definition.stem_y_min_mm <= triangle.centroid.y <= 0.0
        )

    @property
    def segmentation_sha256(self) -> str:
        payload = {
            "source_surface_id": self.source_surface_id,
            "source_surface_sha256": self.source_surface_sha256,
            "t_zone_definition": self.t_zone_definition.manifest(),
            "thresholds": {
                "aggregate_min_percent": self.aggregate_min_percent,
                "t_zone_min_percent": self.t_zone_min_percent,
                "unexplained_hole_max_mm2": self.unexplained_hole_max_mm2,
            },
            "triangles": [
                [
                    t.triangle_index,
                    list(t.vertex_indices),
                    t.region_id,
                    t.protected_zone_id,
                    t.is_target,
                    t.is_t_zone_target,
                    round(t.area_mm2, 12),
                ]
                for t in self.triangles
            ],
            "segmentation_status": self.segmentation_status,
            "anatomical_validation_eligible": self.anatomical_validation_eligible,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self) -> dict[str, object]:
        return {
            "source_surface_id": self.source_surface_id,
            "source_surface_sha256": self.source_surface_sha256,
            "triangle_count": len(self.triangles),
            "target_triangle_count": len(self.target_triangles),
            "protected_triangle_count": len(self.protected_triangles),
            "t_zone_target_triangle_count": len(self.t_zone_target_triangles),
            "total_surface_area_mm2": self.total_surface_area_mm2,
            "target_area_mm2": self.target_area_mm2,
            "protected_area_mm2": self.protected_area_mm2,
            "t_zone_target_area_mm2": self.t_zone_target_area_mm2,
            "philtrum_target_area_mm2": self.philtrum_target_area_mm2,
            "area_conservation_error_mm2": self.area_conservation_error_mm2,
            "region_area_mm2": self.region_area_mm2,
            "t_zone_definition": self.t_zone_definition.manifest(),
            "aggregate_min_percent": self.aggregate_min_percent,
            "t_zone_min_percent": self.t_zone_min_percent,
            "unexplained_hole_max_mm2": self.unexplained_hole_max_mm2,
            "segmentation_status": self.segmentation_status,
            "anatomical_validation_eligible": self.anatomical_validation_eligible,
            "segmentation_sha256": self.segmentation_sha256,
        }

    def _target_adjacency(self) -> dict[int, set[int]]:
        target_ids = {triangle.triangle_index for triangle in self.target_triangles}
        edge_to_triangles: dict[tuple[int, int], list[int]] = defaultdict(list)
        for triangle in self.target_triangles:
            a, b, c = triangle.vertex_indices
            for u, v in ((a, b), (b, c), (c, a)):
                edge_to_triangles[tuple(sorted((u, v)))].append(triangle.triangle_index)
        adjacency: dict[int, set[int]] = {triangle_id: set() for triangle_id in target_ids}
        for incident in edge_to_triangles.values():
            if len(incident) > 1:
                for source in incident:
                    for destination in incident:
                        if source != destination and destination in target_ids:
                            adjacency[source].add(destination)
        return adjacency

    def largest_uncovered_component_area_mm2(self, covered_target_triangle_indices: Iterable[int]) -> float:
        covered = set(int(index) for index in covered_target_triangle_indices)
        target_ids = {triangle.triangle_index for triangle in self.target_triangles}
        unknown = covered - target_ids
        if unknown:
            raise CoverageError(f"Coverage set contains non-target or unknown triangle indices: {sorted(unknown)[:8]}")
        uncovered = target_ids - covered
        if not uncovered:
            return 0.0

        triangle_by_id = {triangle.triangle_index: triangle for triangle in self.target_triangles}
        adjacency = self._target_adjacency()
        visited: set[int] = set()
        largest = 0.0
        for start in sorted(uncovered):
            if start in visited:
                continue
            queue: deque[int] = deque([start])
            visited.add(start)
            area = 0.0
            while queue:
                current = queue.popleft()
                area += triangle_by_id[current].area_mm2
                for neighbor in adjacency[current]:
                    if neighbor in uncovered and neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            largest = max(largest, area)
        return largest

    def evaluate(
        self,
        covered_target_triangle_indices: Iterable[int],
        *,
        evidence_status: str,
        evidence_eligible: bool = False,
    ) -> CoverageEvaluation:
        if not evidence_status.strip():
            raise CoverageError("Coverage evaluation evidence_status must be non-empty")
        covered = frozenset(int(index) for index in covered_target_triangle_indices)
        target_by_id = {triangle.triangle_index: triangle for triangle in self.target_triangles}
        unknown = set(covered) - set(target_by_id)
        if unknown:
            raise CoverageError(f"Coverage set contains non-target or unknown triangle indices: {sorted(unknown)[:8]}")

        covered_area = sum(target_by_id[index].area_mm2 for index in covered)
        t_zone_ids = {triangle.triangle_index for triangle in self.t_zone_target_triangles}
        covered_t_zone_area = sum(target_by_id[index].area_mm2 for index in covered if index in t_zone_ids)
        aggregate_percent = 100.0 * covered_area / self.target_area_mm2
        t_zone_percent = 100.0 * covered_t_zone_area / self.t_zone_target_area_mm2
        largest_hole = self.largest_uncovered_component_area_mm2(covered)
        numeric_pass = (
            aggregate_percent + 1e-12 >= self.aggregate_min_percent
            and t_zone_percent + 1e-12 >= self.t_zone_min_percent
            and largest_hole <= self.unexplained_hole_max_mm2 + 1e-12
        )

        can_validate = evidence_eligible and self.anatomical_validation_eligible
        if numeric_pass and can_validate:
            validation_status = "NUMERIC_GATE_PASS_WITH_EVIDENCE_ELIGIBLE_SURFACE_REQUIRES_PROTOCOL_ACCEPTANCE"
        elif numeric_pass:
            validation_status = "NUMERIC_SCREEN_PASS_NOT_PRODUCT_VALIDATION"
        else:
            validation_status = "NUMERIC_GATE_FAIL"

        payload = {
            "covered": sorted(covered),
            "surface": self.source_surface_sha256,
            "segmentation": self.segmentation_sha256,
            "evidence_status": evidence_status,
            "evidence_eligible": bool(evidence_eligible),
            "aggregate_percent": round(aggregate_percent, 12),
            "t_zone_percent": round(t_zone_percent, 12),
            "largest_hole_mm2": round(largest_hole, 12),
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

        return CoverageEvaluation(
            aggregate_percent=aggregate_percent,
            t_zone_percent=t_zone_percent,
            largest_uncovered_hole_mm2=largest_hole,
            aggregate_min_percent=self.aggregate_min_percent,
            t_zone_min_percent=self.t_zone_min_percent,
            unexplained_hole_max_mm2=self.unexplained_hole_max_mm2,
            numeric_gate_passed=numeric_pass,
            product_validation_status=validation_status,
            evidence_status=evidence_status,
            covered_target_triangle_count=len(covered),
            target_triangle_count=len(target_by_id),
            covered_target_area_mm2=covered_area,
            target_area_mm2=self.target_area_mm2,
            covered_t_zone_area_mm2=covered_t_zone_area,
            t_zone_target_area_mm2=self.t_zone_target_area_mm2,
            evaluation_sha256=digest,
        )


def _triangle_centroid(a: Point3, b: Point3, c: Point3) -> Point3:
    return Point3(
        (a.x + b.x + c.x) / 3.0,
        (a.y + b.y + c.y) / 3.0,
        (a.z + b.z + c.z) / 3.0,
    )


def _triangle_area_mm2(a: Point3, b: Point3, c: Point3) -> float:
    return 0.5 * a.vector_to(b).cross(a.vector_to(c)).norm()


def build_t_zone_development_definition(
    authority: Authority,
    reference: FacialReferenceLayer,
    protected: ProtectedVolumeSet,
) -> TZoneDevelopmentDefinition:
    """Derive a reproducible T-zone development baseline from existing geometry only."""

    nostril_outer = max(
        abs(protected.nostril_left.zone.center.x) + protected.nostril_left.zone.envelope_width_mm / 2.0,
        abs(protected.nostril_right.zone.center.x) + protected.nostril_right.zone.envelope_width_mm / 2.0,
    )

    eye_w, eye_h = authority.pair("geometry", "eye", "visual_aperture_wh_mm")
    forehead_half_width = max(
        abs(reference.eye_pair.left.point_xy.x),
        abs(reference.eye_pair.right.point_xy.x),
    ) + eye_w / 2.0
    forehead_y_min = reference.eye_pair.left.point_xy.y + eye_h / 2.0

    mouth_zone = protected.mouth.zone
    mouth_superior_protected_boundary = mouth_zone.center.y + mouth_zone.envelope_height_mm / 2.0

    return TZoneDevelopmentDefinition(
        stem_half_width_mm=nostril_outer,
        stem_y_min_mm=mouth_superior_protected_boundary,
        stem_y_max_mm=forehead_y_min,
        forehead_half_width_mm=forehead_half_width,
        forehead_y_min_mm=forehead_y_min,
    )


def _protected_zone_for_triangle(
    points: tuple[Point3, Point3, Point3],
    centroid: Point3,
    protected: ProtectedVolumeSet,
) -> str | None:
    """Conservatively exclude a triangle if a vertex or centroid enters a protected XY footprint."""

    samples = (*points, centroid)
    for volume in protected.all:
        if any(volume.contains_point(sample) for sample in samples):
            return volume.zone.zone_id
    return None


def build_facial_coverage_mesh(
    authority: Authority,
    reference: FacialReferenceLayer,
    surface: FacialSurface,
    protected: ProtectedVolumeSet,
) -> FacialCoverageMesh:
    if protected.source_surface_id != surface.descriptor.surface_id:
        raise CoverageError("Protected-volume source surface does not match coverage surface")

    t_zone = build_t_zone_development_definition(authority, reference, protected)
    cells: list[CoverageTriangle] = []
    vertices = surface.mesh.vertices

    for triangle_index, vertex_indices in enumerate(surface.mesh.triangles):
        ia, ib, ic = vertex_indices
        a, b, c = vertices[ia], vertices[ib], vertices[ic]
        centroid = _triangle_centroid(a, b, c)
        area = _triangle_area_mm2(a, b, c)
        if area <= 0.0:
            raise CoverageError(f"Degenerate triangle at index {triangle_index}")

        protected_zone_id = _protected_zone_for_triangle((a, b, c), centroid, protected)
        if protected_zone_id is not None:
            region_id = PROTECTED_REGION_BY_ZONE_ID.get(protected_zone_id)
            if region_id is None:
                raise CoverageError(f"Unknown protected zone ID {protected_zone_id!r}")
            is_target = False
            is_t_zone = False
        else:
            region_id = t_zone.region_for(Point2(centroid.x, centroid.y)) or REGION_ACTIVE_OTHER
            is_target = True
            is_t_zone = region_id in t_zone.t_zone_region_ids

        cells.append(
            CoverageTriangle(
                triangle_index=triangle_index,
                vertex_indices=vertex_indices,
                centroid=centroid,
                area_mm2=area,
                region_id=region_id,
                protected_zone_id=protected_zone_id,
                is_target=is_target,
                is_t_zone_target=is_t_zone,
            )
        )

    segmentation_status = (
        "DETERMINISTIC_DEVELOPMENT_SEGMENTATION;"
        f"{t_zone.evidence_status};"
        f"SOURCE_SURFACE={surface.descriptor.evidence_status};"
        "PROTECTED_TRIANGLES_CONSERVATIVE_VERTEX_OR_CENTROID_EXCLUSION"
    )

    coverage = FacialCoverageMesh(
        source_surface_id=surface.descriptor.surface_id,
        source_surface_sha256=surface.mesh.normalized_sha256(),
        triangles=tuple(cells),
        t_zone_definition=t_zone,
        aggregate_min_percent=authority.number("coverage", "aggregate_min_percent"),
        t_zone_min_percent=authority.number("coverage", "t_zone_min_percent"),
        unexplained_hole_max_mm2=authority.number("coverage", "unexplained_hole_max_mm2"),
        segmentation_status=segmentation_status,
        anatomical_validation_eligible=surface.descriptor.anatomical_validation_eligible,
    )

    if coverage.area_conservation_error_mm2 > 1e-8:
        raise CoverageError(f"Coverage partition area does not conserve surface area: {coverage.area_conservation_error_mm2}")
    if coverage.philtrum_target_area_mm2 <= 0.0:
        raise CoverageError("Development segmentation contains no active nose-to-upper-lip/philtrum target area")
    return coverage
