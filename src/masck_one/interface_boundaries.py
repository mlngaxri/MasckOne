from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import math

from .authority import Authority
from .coverage import FacialCoverageMesh
from .facial_surface import FacialSurface
from .interface_topology import CompliantInterfaceTopology
from .nasal_subsystem import NasalSubsystemTopology


class InterfaceBoundaryError(ValueError):
    """Raised when the interface boundary/transition contract is violated."""


EDGE_OUTER_PERIMETER = "OUTER_PERIMETER_SEAL_INTENT"
EDGE_PROTECTED_APERTURE = "PROTECTED_APERTURE_TRANSITION"
EDGE_CONTACT_PARAMETER = "CONTACT_PARAMETER_TRANSITION"
EDGE_NASAL_MAIN = "NASAL_MAIN_INTERFACE_TRANSITION"
EDGE_NASAL_ROLE = "NASAL_ROLE_TRANSITION"

BOUNDARY_KINDS = (
    EDGE_OUTER_PERIMETER,
    EDGE_PROTECTED_APERTURE,
    EDGE_CONTACT_PARAMETER,
    EDGE_NASAL_MAIN,
    EDGE_NASAL_ROLE,
)


@dataclass(frozen=True, slots=True)
class VisibleSeamAuthority:
    gap_mm: float
    tolerance_mm: float
    flush_mismatch_max_mm: float
    authority_status: str
    application_status: str = "PLACEMENT_UNRESOLVED_UNTIL_INTERFACE_FRAME_ATTACHMENT_ARCHITECTURE"

    def __post_init__(self) -> None:
        for label in ("gap_mm", "tolerance_mm", "flush_mismatch_max_mm"):
            value = float(getattr(self, label))
            if not math.isfinite(value) or value < 0.0:
                raise InterfaceBoundaryError(f"{label} must be finite and non-negative")
            object.__setattr__(self, label, value)
        if not self.authority_status.strip() or not self.application_status.strip():
            raise InterfaceBoundaryError("Visible-seam status fields must be explicit")

    @property
    def allowed_gap_range_mm(self) -> tuple[float, float]:
        return self.gap_mm - self.tolerance_mm, self.gap_mm + self.tolerance_mm

    def manifest(self) -> dict[str, object]:
        return {
            "gap_mm": self.gap_mm,
            "tolerance_mm": self.tolerance_mm,
            "allowed_gap_range_mm": list(self.allowed_gap_range_mm),
            "flush_mismatch_max_mm": self.flush_mismatch_max_mm,
            "authority_status": self.authority_status,
            "application_status": self.application_status,
        }


@dataclass(frozen=True, slots=True)
class EyeInnerEdgeRollAuthority:
    radius_mm: float
    authority_status: str
    application_status: str = "VISUAL_APERTURE_INNER_EDGE_NOT_MAPPED_TO_CONSERVATIVE_PROTECTED_ENVELOPE_TRANSITION"

    def __post_init__(self) -> None:
        radius = float(self.radius_mm)
        if not math.isfinite(radius) or radius <= 0.0:
            raise InterfaceBoundaryError("Eye inner-edge roll radius must be finite and positive")
        if not self.authority_status.strip() or not self.application_status.strip():
            raise InterfaceBoundaryError("Eye-roll authority status fields must be explicit")
        object.__setattr__(self, "radius_mm", radius)

    def manifest(self) -> dict[str, object]:
        return {
            "radius_mm": self.radius_mm,
            "authority_status": self.authority_status,
            "application_status": self.application_status,
        }


@dataclass(frozen=True, slots=True)
class PerimeterComplianceIntent:
    seal_intent: bool = True
    seal_width_mm: float | None = None
    seal_thickness_mm: float | None = None
    compression_mm: float | None = None
    compression_ratio: float | None = None
    preload_N: float | None = None
    geometry_status: str = "TOPOLOGY_ONLY_NUMERIC_SEAL_GEOMETRY_UNRESOLVED"
    evidence_status: str = "FUNCTIONAL_INTENT_ONLY_NOT_SEAL_PRESSURE_LEAK_OR_FIT_EVIDENCE"

    def __post_init__(self) -> None:
        if not self.seal_intent:
            raise InterfaceBoundaryError("Iteration-12 perimeter contract requires explicit seal/compliance intent")
        unresolved = (
            self.seal_width_mm,
            self.seal_thickness_mm,
            self.compression_mm,
            self.compression_ratio,
            self.preload_N,
        )
        if any(value is not None for value in unresolved):
            raise InterfaceBoundaryError(
                "Iteration 12 must not invent seal width, thickness, compression, compression ratio or preload"
            )
        if not self.geometry_status.strip() or not self.evidence_status.strip():
            raise InterfaceBoundaryError("Perimeter compliance statuses must be explicit")

    def manifest(self) -> dict[str, object]:
        return {
            "seal_intent": self.seal_intent,
            "seal_width_mm": self.seal_width_mm,
            "seal_thickness_mm": self.seal_thickness_mm,
            "compression_mm": self.compression_mm,
            "compression_ratio": self.compression_ratio,
            "preload_N": self.preload_N,
            "geometry_status": self.geometry_status,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class InterfaceBoundaryEdge:
    vertex_indices: tuple[int, int]
    kind: str
    length_mm: float
    incident_triangle_indices: tuple[int, ...]
    interface_zone_ids: tuple[str, ...]
    nasal_role_ids: tuple[str, ...]
    protected_zone_id: str | None
    seal_intent: bool
    material_bridge_allowed: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if len(self.vertex_indices) != 2 or self.vertex_indices[0] >= self.vertex_indices[1]:
            raise InterfaceBoundaryError("Boundary edge key must be a sorted pair of distinct vertex indices")
        if self.kind not in BOUNDARY_KINDS:
            raise InterfaceBoundaryError(f"Unknown interface-boundary kind {self.kind!r}")
        length = float(self.length_mm)
        if not math.isfinite(length) or length <= 0.0:
            raise InterfaceBoundaryError("Boundary-edge length must be finite and positive")
        object.__setattr__(self, "length_mm", length)
        if len(self.incident_triangle_indices) not in {1, 2}:
            raise InterfaceBoundaryError("Boundary edge must have one or two incident triangles")
        if len(set(self.incident_triangle_indices)) != len(self.incident_triangle_indices):
            raise InterfaceBoundaryError("Incident triangle IDs cannot repeat")
        if not self.evidence_status.strip():
            raise InterfaceBoundaryError("Boundary-edge evidence status must be explicit")

        if self.kind == EDGE_OUTER_PERIMETER:
            if len(self.incident_triangle_indices) != 1 or not self.seal_intent:
                raise InterfaceBoundaryError("Outer perimeter edges require one incident triangle and seal intent")
            if self.protected_zone_id is not None:
                raise InterfaceBoundaryError("Outer perimeter cannot be labeled as a protected-aperture transition")
        elif self.kind == EDGE_PROTECTED_APERTURE:
            if len(self.incident_triangle_indices) != 2 or self.protected_zone_id is None:
                raise InterfaceBoundaryError("Protected aperture transitions require two triangles and one protected-zone ID")
            if self.material_bridge_allowed or self.seal_intent:
                raise InterfaceBoundaryError("Protected opening transitions cannot bridge material or inherit outer seal intent")
        else:
            if len(self.incident_triangle_indices) != 2:
                raise InterfaceBoundaryError("Internal transition edges require two incident triangles")
            if self.protected_zone_id is not None:
                raise InterfaceBoundaryError("Contact/nasal transitions cannot carry protected-zone identity")

    @property
    def edge_id(self) -> str:
        return f"MASCK_ONE-EDGE-{self.vertex_indices[0]:05d}-{self.vertex_indices[1]:05d}"

    def manifest(self) -> list[object]:
        return [
            self.edge_id,
            list(self.vertex_indices),
            self.kind,
            round(self.length_mm, 12),
            list(self.incident_triangle_indices),
            list(self.interface_zone_ids),
            list(self.nasal_role_ids),
            self.protected_zone_id,
            self.seal_intent,
            self.material_bridge_allowed,
            self.evidence_status,
        ]


@dataclass(frozen=True, slots=True)
class InterfaceBoundaryTopology:
    source_surface_id: str
    source_surface_sha256: str
    source_coverage_sha256: str
    source_interface_sha256: str
    source_nasal_sha256: str
    mesh_unique_edge_count: int
    mesh_outer_edge_count: int
    edges: tuple[InterfaceBoundaryEdge, ...]
    perimeter_intent: PerimeterComplianceIntent
    visible_seam_authority: VisibleSeamAuthority
    eye_inner_edge_roll_authority: EyeInnerEdgeRollAuthority
    topology_status: str
    evidence_status: str
    anatomical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.mesh_unique_edge_count <= 0 or self.mesh_outer_edge_count <= 0:
            raise InterfaceBoundaryError("Mesh edge accounting must be positive")
        for digest in (
            self.source_surface_sha256,
            self.source_coverage_sha256,
            self.source_interface_sha256,
            self.source_nasal_sha256,
        ):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.lower()):
                raise InterfaceBoundaryError("Interface boundary source hashes must be SHA-256 values")
        if self.anatomical_validation_eligible:
            raise InterfaceBoundaryError("Development interface boundaries cannot be anatomical-validation evidence")
        if not self.edges:
            raise InterfaceBoundaryError("Interface boundary topology cannot be empty")
        keys = [edge.vertex_indices for edge in self.edges]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise InterfaceBoundaryError("Boundary edges must be unique and deterministically sorted")
        if len(self.outer_perimeter_edges) != self.mesh_outer_edge_count:
            raise InterfaceBoundaryError("Every surface outer edge must appear exactly once as perimeter seal intent")
        if not self.topology_status.strip() or not self.evidence_status.strip():
            raise InterfaceBoundaryError("Topology/evidence status must be explicit")

    @property
    def edges_by_kind(self) -> dict[str, tuple[InterfaceBoundaryEdge, ...]]:
        return {
            kind: tuple(edge for edge in self.edges if edge.kind == kind)
            for kind in BOUNDARY_KINDS
        }

    @property
    def outer_perimeter_edges(self) -> tuple[InterfaceBoundaryEdge, ...]:
        return tuple(edge for edge in self.edges if edge.kind == EDGE_OUTER_PERIMETER)

    @property
    def protected_aperture_edges(self) -> tuple[InterfaceBoundaryEdge, ...]:
        return tuple(edge for edge in self.edges if edge.kind == EDGE_PROTECTED_APERTURE)

    @property
    def kind_length_mm(self) -> dict[str, float]:
        return {
            kind: sum(edge.length_mm for edge in self.edges if edge.kind == kind)
            for kind in BOUNDARY_KINDS
        }

    @property
    def protected_transition_length_mm(self) -> dict[str, float]:
        result: dict[str, float] = defaultdict(float)
        for edge in self.protected_aperture_edges:
            assert edge.protected_zone_id is not None
            result[edge.protected_zone_id] += edge.length_mm
        return dict(sorted(result.items()))

    @property
    def topology_sha256(self) -> str:
        payload = {
            "source_surface_id": self.source_surface_id,
            "source_surface_sha256": self.source_surface_sha256,
            "source_coverage_sha256": self.source_coverage_sha256,
            "source_interface_sha256": self.source_interface_sha256,
            "source_nasal_sha256": self.source_nasal_sha256,
            "mesh_unique_edge_count": self.mesh_unique_edge_count,
            "mesh_outer_edge_count": self.mesh_outer_edge_count,
            "edges": [edge.manifest() for edge in self.edges],
            "perimeter_intent": self.perimeter_intent.manifest(),
            "visible_seam_authority": self.visible_seam_authority.manifest(),
            "eye_inner_edge_roll_authority": self.eye_inner_edge_roll_authority.manifest(),
            "topology_status": self.topology_status,
            "evidence_status": self.evidence_status,
            "anatomical_validation_eligible": self.anatomical_validation_eligible,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def manifest(self) -> dict[str, object]:
        return {
            "source_surface_id": self.source_surface_id,
            "source_surface_sha256": self.source_surface_sha256,
            "source_coverage_sha256": self.source_coverage_sha256,
            "source_interface_sha256": self.source_interface_sha256,
            "source_nasal_sha256": self.source_nasal_sha256,
            "mesh_unique_edge_count": self.mesh_unique_edge_count,
            "mesh_outer_edge_count": self.mesh_outer_edge_count,
            "boundary_edge_count": len(self.edges),
            "edge_count_by_kind": {kind: len(edges) for kind, edges in self.edges_by_kind.items()},
            "development_length_mm_by_kind": self.kind_length_mm,
            "protected_transition_development_length_mm": self.protected_transition_length_mm,
            "perimeter_intent": self.perimeter_intent.manifest(),
            "visible_seam_authority": self.visible_seam_authority.manifest(),
            "eye_inner_edge_roll_authority": self.eye_inner_edge_roll_authority.manifest(),
            "topology_status": self.topology_status,
            "evidence_status": self.evidence_status,
            "anatomical_validation_eligible": self.anatomical_validation_eligible,
            "topology_sha256": self.topology_sha256,
        }


def _edge_length_mm(surface: FacialSurface, edge: tuple[int, int]) -> float:
    a = surface.mesh.vertices[edge[0]]
    b = surface.mesh.vertices[edge[1]]
    return a.vector_to(b).norm()


def build_interface_boundary_topology(
    authority: Authority,
    surface: FacialSurface,
    coverage: FacialCoverageMesh,
    interface: CompliantInterfaceTopology,
    nasal: NasalSubsystemTopology,
) -> InterfaceBoundaryTopology:
    """Build development-only perimeter and transition topology without inventing seal geometry."""

    if coverage.source_surface_id != surface.descriptor.surface_id:
        raise InterfaceBoundaryError("Coverage and facial surface IDs differ")
    if coverage.source_surface_sha256 != surface.descriptor.source_sha256:
        raise InterfaceBoundaryError("Coverage and facial surface hashes differ")
    if interface.coverage_segmentation_sha256 != coverage.segmentation_sha256:
        raise InterfaceBoundaryError("Interface/coverage segmentation source chain differs")
    if nasal.source_interface_sha256 != interface.topology_sha256:
        raise InterfaceBoundaryError("Nasal/interface source chain differs")

    triangle_by_id = {triangle.triangle_index: triangle for triangle in coverage.triangles}
    interface_by_id = {assignment.triangle_index: assignment for assignment in interface.assignments}
    nasal_role_by_triangle = {assignment.triangle_index: assignment.role_id for assignment in nasal.assignments}
    if set(triangle_by_id) != set(interface_by_id):
        raise InterfaceBoundaryError("Coverage/interface triangle domains differ")

    edge_to_triangles: dict[tuple[int, int], list[int]] = defaultdict(list)
    for triangle in coverage.triangles:
        a, b, c = triangle.vertex_indices
        for u, v in ((a, b), (b, c), (c, a)):
            edge_to_triangles[tuple(sorted((u, v)))].append(triangle.triangle_index)

    non_manifold = {edge: ids for edge, ids in edge_to_triangles.items() if len(ids) not in {1, 2}}
    if non_manifold:
        raise InterfaceBoundaryError(f"Non-manifold mesh edges found: {sorted(non_manifold)[:5]}")

    boundary_edges: list[InterfaceBoundaryEdge] = []
    for edge_key, incident in sorted(edge_to_triangles.items()):
        incident_ids = tuple(sorted(incident))
        triangles = tuple(triangle_by_id[index] for index in incident_ids)
        assignments = tuple(interface_by_id[index] for index in incident_ids)
        interface_zone_ids = tuple(sorted({item.parameter_zone_id for item in assignments}))
        nasal_role_ids = tuple(sorted({nasal_role_by_triangle[index] for index in incident_ids if index in nasal_role_by_triangle}))
        length = _edge_length_mm(surface, edge_key)

        if len(incident_ids) == 1:
            if not triangles[0].is_target:
                raise InterfaceBoundaryError(
                    "Current development outer perimeter intersects a protected region; perimeter seal intent requires review"
                )
            boundary_edges.append(InterfaceBoundaryEdge(
                vertex_indices=edge_key,
                kind=EDGE_OUTER_PERIMETER,
                length_mm=length,
                incident_triangle_indices=incident_ids,
                interface_zone_ids=interface_zone_ids,
                nasal_role_ids=nasal_role_ids,
                protected_zone_id=None,
                seal_intent=True,
                material_bridge_allowed=True,
                evidence_status="DEVELOPMENT_OUTER_PERIMETER_SEAL_INTENT_NOT_FIT_LEAK_OR_PRESSURE_EVIDENCE",
            ))
            continue

        first, second = triangles
        if first.is_target != second.is_target:
            protected = first if not first.is_target else second
            if protected.protected_zone_id is None:
                raise InterfaceBoundaryError("Protected transition triangle has no protected-zone identity")
            boundary_edges.append(InterfaceBoundaryEdge(
                vertex_indices=edge_key,
                kind=EDGE_PROTECTED_APERTURE,
                length_mm=length,
                incident_triangle_indices=incident_ids,
                interface_zone_ids=interface_zone_ids,
                nasal_role_ids=nasal_role_ids,
                protected_zone_id=protected.protected_zone_id,
                seal_intent=False,
                material_bridge_allowed=False,
                evidence_status="CONSERVATIVE_PROTECTED_ENVELOPE_TRANSITION_NOT_FINAL_APERTURE_EDGE_GEOMETRY",
            ))
            continue

        if not first.is_target and not second.is_target:
            continue

        first_nasal = nasal_role_by_triangle.get(first.triangle_index)
        second_nasal = nasal_role_by_triangle.get(second.triangle_index)
        if first_nasal is not None and second_nasal is not None and first_nasal != second_nasal:
            kind = EDGE_NASAL_ROLE
        elif (first_nasal is None) != (second_nasal is None):
            kind = EDGE_NASAL_MAIN
        elif assignments[0].parameter_zone_id != assignments[1].parameter_zone_id:
            kind = EDGE_CONTACT_PARAMETER
        else:
            continue

        boundary_edges.append(InterfaceBoundaryEdge(
            vertex_indices=edge_key,
            kind=kind,
            length_mm=length,
            incident_triangle_indices=incident_ids,
            interface_zone_ids=interface_zone_ids,
            nasal_role_ids=nasal_role_ids,
            protected_zone_id=None,
            seal_intent=False,
            material_bridge_allowed=True,
            evidence_status="DEVELOPMENT_CONTACT_PARAMETER_BOUNDARY_NOT_PHYSICAL_SEAM_OR_MATERIAL_DISCONTINUITY",
        ))

    seam = VisibleSeamAuthority(
        gap_mm=authority.number("geometry", "visible_seam", "gap_mm"),
        tolerance_mm=authority.number("geometry", "visible_seam", "tolerance_mm"),
        flush_mismatch_max_mm=authority.number("geometry", "visible_seam", "flush_mismatch_max_mm"),
        authority_status=str(authority.get("geometry", "visible_seam", "status")),
    )
    eye_roll = EyeInnerEdgeRollAuthority(
        radius_mm=authority.number("geometry", "eye", "inner_edge_roll_radius_mm"),
        authority_status=str(authority.get("geometry", "eye", "aperture_status")),
    )
    topology = InterfaceBoundaryTopology(
        source_surface_id=surface.descriptor.surface_id,
        source_surface_sha256=surface.descriptor.source_sha256,
        source_coverage_sha256=coverage.segmentation_sha256,
        source_interface_sha256=interface.topology_sha256,
        source_nasal_sha256=nasal.topology_sha256,
        mesh_unique_edge_count=len(edge_to_triangles),
        mesh_outer_edge_count=sum(1 for incident in edge_to_triangles.values() if len(incident) == 1),
        edges=tuple(boundary_edges),
        perimeter_intent=PerimeterComplianceIntent(),
        visible_seam_authority=seam,
        eye_inner_edge_roll_authority=eye_roll,
        topology_status="PHASE2_ITERATION12_INTERFACE_BOUNDARY_TOPOLOGY",
        evidence_status="DETERMINISTIC_DEVELOPMENT_BOUNDARIES_NOT_ANATOMICAL_SEAL_FIT_LEAK_OR_PRESSURE_EVIDENCE",
        anatomical_validation_eligible=False,
    )

    protected_zone_ids = {triangle.protected_zone_id for triangle in coverage.protected_triangles if triangle.protected_zone_id}
    transition_zone_ids = {edge.protected_zone_id for edge in topology.protected_aperture_edges}
    missing_transitions = protected_zone_ids - transition_zone_ids
    if missing_transitions:
        raise InterfaceBoundaryError(f"Protected zones have no contact transition: {sorted(missing_transitions)}")
    return topology
