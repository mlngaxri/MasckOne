from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Iterable

from .anatomy import FacialReferenceLayer, PlanarLandmark
from .authority import Authority
from .reference_surfaces import ReferenceSurfaceAsset, TriangleMesh
from .spatial import Point2, Point3


class FacialSurfaceError(ValueError):
    """Raised when a neutral facial reference surface violates its contract."""


@dataclass(frozen=True, slots=True)
class FacialSurfaceDescriptor:
    surface_id: str
    kind: str
    evidence_status: str
    source_asset_id: str | None
    source_revision: str
    source_sha256: str
    anatomical_validation_eligible: bool

    def __post_init__(self) -> None:
        for label, value in {
            "surface_id": self.surface_id,
            "kind": self.kind,
            "evidence_status": self.evidence_status,
            "source_revision": self.source_revision,
            "source_sha256": self.source_sha256,
        }.items():
            if not str(value).strip():
                raise FacialSurfaceError(f"{label} must be non-empty")
        digest = self.source_sha256.lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise FacialSurfaceError("source_sha256 must be a 64-character hexadecimal digest")
        object.__setattr__(self, "source_sha256", digest)
        if self.kind == "PLANAR_DEVELOPMENT_REFERENCE" and self.anatomical_validation_eligible:
            raise FacialSurfaceError("Planar development surfaces can never be anatomical-validation evidence")


@dataclass(frozen=True, slots=True)
class SurfaceLandmarkProjection:
    landmark_id: str
    surface_point: Point3
    xy_error_mm: float
    projection_method: str
    evidence_status: str

    def __post_init__(self) -> None:
        if not self.landmark_id.strip() or not self.projection_method.strip() or not self.evidence_status.strip():
            raise FacialSurfaceError("Landmark projection metadata must be non-empty")
        error = float(self.xy_error_mm)
        if not math.isfinite(error) or error < 0.0:
            raise FacialSurfaceError("xy_error_mm must be finite and non-negative")
        object.__setattr__(self, "xy_error_mm", error)


@dataclass(frozen=True, slots=True)
class FacialSurface:
    """Neutral facial-reference mesh in canonical Masck One global millimetres."""

    descriptor: FacialSurfaceDescriptor
    mesh: TriangleMesh

    @property
    def xy_bounds_mm(self) -> tuple[float, float, float, float]:
        xs = [vertex.x for vertex in self.mesh.vertices]
        ys = [vertex.y for vertex in self.mesh.vertices]
        return min(xs), max(xs), min(ys), max(ys)

    @property
    def z_bounds_mm(self) -> tuple[float, float]:
        zs = [vertex.z for vertex in self.mesh.vertices]
        return min(zs), max(zs)

    @property
    def is_planar(self) -> bool:
        z_min, z_max = self.z_bounds_mm
        return math.isclose(z_min, z_max, rel_tol=0.0, abs_tol=1e-12)

    def nearest_vertex_xy(self, point: Point2) -> tuple[Point3, float]:
        best_vertex: Point3 | None = None
        best_distance = math.inf
        for vertex in self.mesh.vertices:
            distance = math.hypot(vertex.x - point.x, vertex.y - point.y)
            if distance < best_distance:
                best_distance = distance
                best_vertex = vertex
        if best_vertex is None:
            raise FacialSurfaceError("Facial surface has no vertices")
        return best_vertex, best_distance

    def project_landmark(self, landmark: PlanarLandmark) -> SurfaceLandmarkProjection:
        vertex, error = self.nearest_vertex_xy(landmark.point_xy)
        if self.descriptor.kind == "PLANAR_DEVELOPMENT_REFERENCE":
            status = "DEVELOPMENT_PROJECTION_NOT_ANATOMICAL_EVIDENCE"
        else:
            status = "REFERENCE_MESH_VERTEX_PROJECTION"
        return SurfaceLandmarkProjection(
            landmark_id=landmark.id,
            surface_point=vertex,
            xy_error_mm=error,
            projection_method="NEAREST_VERTEX_XY",
            evidence_status=status,
        )

    def project_reference_landmarks(self, reference: FacialReferenceLayer) -> tuple[SurfaceLandmarkProjection, ...]:
        return tuple(self.project_landmark(landmark) for landmark in reference.landmarks)

    def manifest(self) -> dict[str, object]:
        return {
            "surface_id": self.descriptor.surface_id,
            "kind": self.descriptor.kind,
            "evidence_status": self.descriptor.evidence_status,
            "source_asset_id": self.descriptor.source_asset_id,
            "source_revision": self.descriptor.source_revision,
            "source_sha256": self.descriptor.source_sha256,
            "anatomical_validation_eligible": self.descriptor.anatomical_validation_eligible,
            "mesh": {
                "vertex_count": self.mesh.vertex_count,
                "triangle_count": self.mesh.triangle_count,
                "mesh_sha256": self.mesh.normalized_sha256(),
                "xy_bounds_mm": list(self.xy_bounds_mm),
                "z_bounds_mm": list(self.z_bounds_mm),
            },
        }


def _linspace(start: float, stop: float, count: int) -> tuple[float, ...]:
    if count < 2:
        raise FacialSurfaceError("Grid axis requires at least two samples")
    step = (stop - start) / (count - 1)
    return tuple(start + index * step for index in range(count))


def _planar_mesh(width_mm: float, height_mm: float, *, x_samples: int, y_samples: int) -> TriangleMesh:
    if width_mm <= 0.0 or height_mm <= 0.0:
        raise FacialSurfaceError("Development surface dimensions must be positive")
    if x_samples < 5 or y_samples < 5:
        raise FacialSurfaceError("Development surface requires at least 5x5 samples")
    if x_samples % 2 == 0:
        raise FacialSurfaceError("Development surface x_samples must be odd so X=0 is an explicit sagittal vertex column")

    xs = _linspace(-width_mm / 2.0, width_mm / 2.0, x_samples)
    ys = _linspace(-height_mm / 2.0, height_mm / 2.0, y_samples)
    vertex_index: dict[tuple[int, int], int] = {}
    vertices: list[Point3] = []

    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            ellipse_value = (x / (width_mm / 2.0)) ** 2 + (y / (height_mm / 2.0)) ** 2
            if ellipse_value <= 1.0 + 1e-12:
                vertex_index[(i, j)] = len(vertices)
                vertices.append(Point3(x, y, 0.0))

    triangles: list[tuple[int, int, int]] = []
    sagittal_cell_boundary = (x_samples - 1) / 2.0
    for j in range(y_samples - 1):
        for i in range(x_samples - 1):
            corners = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
            if all(corner in vertex_index for corner in corners):
                a, b, c, d = (vertex_index[corner] for corner in corners)
                # Mirror the cell-diagonal topology across X=0. A single global
                # diagonal direction created a small but real left/right area bias
                # when protected boundaries were sampled triangle-by-triangle.
                # The mirrored topology preserves the same vertices, envelope and
                # total area while making the neutral development mesh itself obey
                # the project's sagittal-symmetry baseline.
                if i < sagittal_cell_boundary:
                    triangles.append((a, b, c))
                    triangles.append((a, c, d))
                else:
                    triangles.append((a, b, d))
                    triangles.append((b, c, d))

    if not triangles:
        raise FacialSurfaceError("Development surface grid produced no triangles")
    return TriangleMesh(tuple(vertices), tuple(triangles))


def build_planar_development_surface(
    authority: Authority,
    *,
    x_samples: int = 81,
    y_samples: int = 105,
) -> FacialSurface:
    """Build a deterministic topology/reference surface without inventing facial depth.

    The default 81 x 105 grid is approximately 2 mm in both development-plane axes for
    the current 155 x 202 mm functional frame. Iteration 10 increased the former coarse
    grid after it created a false two-triangle philtrum contact island: the continuous
    protected-zone geometry left a real corridor, but the coarse conservative triangle
    sampling could not resolve it. The refined grid is a digital-resolution baseline,
    not anatomical evidence, and callers may still supply explicit sample counts for
    sensitivity/convergence studies.

    This surface exists so region topology, IDs and algorithms can be implemented before
    registered headform/face geometry is available. It is deliberately planar at Z=0 and
    is categorically forbidden from satisfying anatomical fit/clearance validation.
    """

    width_mm, height_mm = authority.pair("geometry", "functional_frame_xy_mm")
    mesh = _planar_mesh(width_mm, height_mm, x_samples=x_samples, y_samples=y_samples)
    descriptor = FacialSurfaceDescriptor(
        surface_id="MASCK_ONE-FACE-SURFACE-PLANAR-DEV-V1",
        kind="PLANAR_DEVELOPMENT_REFERENCE",
        evidence_status="SYNTHETIC_TOPOLOGY_ONLY_NOT_ANATOMICAL_EVIDENCE",
        source_asset_id=None,
        source_revision=str(authority.get("project", "authority_revision")),
        source_sha256=mesh.normalized_sha256(),
        anatomical_validation_eligible=False,
    )
    return FacialSurface(descriptor, mesh)


def facial_surface_from_registered_asset(
    asset: ReferenceSurfaceAsset,
    *,
    surface_id: str,
    anatomical_validation_eligible: bool = False,
    evidence_status: str | None = None,
) -> FacialSurface:
    """Promote a registered external mesh into the neutral facial-surface abstraction.

    `anatomical_validation_eligible` defaults to False. Importing a real scan does not
    automatically prove representativeness, fit relevance, registration quality or safety.
    """

    registered = asset.registered_mesh
    status = evidence_status or (
        "REGISTERED_REFERENCE_NOT_YET_APPROVED_FOR_ANATOMICAL_VALIDATION"
        if not anatomical_validation_eligible
        else "EXTERNALLY_APPROVED_ANATOMICAL_REFERENCE"
    )
    descriptor = FacialSurfaceDescriptor(
        surface_id=surface_id,
        kind="REGISTERED_EXTERNAL_REFERENCE",
        evidence_status=status,
        source_asset_id=asset.provenance.asset_id,
        source_revision=asset.registration.registration_revision,
        source_sha256=asset.provenance.source_sha256,
        anatomical_validation_eligible=anatomical_validation_eligible,
    )
    return FacialSurface(descriptor, registered)
