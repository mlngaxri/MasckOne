from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import hashlib
import json
import math

from .authority import Authority
from .coverage import (
    FacialCoverageMesh,
    REGION_PROTECTED_EYE_LEFT,
    REGION_PROTECTED_EYE_RIGHT,
    REGION_PROTECTED_MOUTH,
    REGION_PROTECTED_NOSTRIL_LEFT,
    REGION_PROTECTED_NOSTRIL_RIGHT,
)
from .facial_surface import FacialSurface
from .interface_topology import CompliantInterfaceTopology


class InterfaceBoundaryError(ValueError):
    """Raised when perimeter/protected-union edge topology violates its contract."""


BOUNDARY_OUTER_PERIMETER = "INTERFACE_BOUNDARY_OUTER_PERIMETER"
BOUNDARY_EYE_PROTECTED_UNION = "INTERFACE_BOUNDARY_EYE_PROTECTED_UNION"
BOUNDARY_MOUTH = "INTERFACE_BOUNDARY_MOUTH"
BOUNDARY_NOSTRIL_PROTECTED_UNION = "INTERFACE_BOUNDARY_NOSTRIL_PROTECTED_UNION"

BOUNDARY_IDS = (
    BOUNDARY_OUTER_PERIMETER,
    BOUNDARY_EYE_PROTECTED_UNION,
    BOUNDARY_MOUTH,
    BOUNDARY_NOSTRIL_PROTECTED_UNION,
)

_PROTECTED_REGION_TO_BOUNDARY = {
    REGION_PROTECTED_EYE_LEFT: BOUNDARY_EYE_PROTECTED_UNION,
    REGION_PROTECTED_EYE_RIGHT: BOUNDARY_EYE_PROTECTED_UNION,
    REGION_PROTECTED_MOUTH: BOUNDARY_MOUTH,
    REGION_PROTECTED_NOSTRIL_LEFT: BOUNDARY_NOSTRIL_PROTECTED_UNION,
    REGION_PROTECTED_NOSTRIL_RIGHT: BOUNDARY_NOSTRIL_PROTECTED_UNION,
}


@dataclass(frozen=True, slots=True)
class InterfaceBoundaryDefinition:
    boundary_id: str
    functional_role: str
    boundary_kind: str
    protected_region_ids: tuple[str, ...]
    compliance_intent: bool
    fluid_containment_intent: bool
    protected_opening_exclusion_intent: bool
    nominal_transition_width_mm: float | None
    nominal_interface_thickness_mm: float | None
    rigid_roll_reference_mm: float | None
    rigid_roll_reference_status: str
    geometry_status: str
    material_status: str
    evidence_status: str

    def __post_init__(self) -> None:
        if self.boundary_id not in BOUNDARY_IDS:
            raise InterfaceBoundaryError(f"Unknown boundary ID {self.boundary_id!r}")
        if self.boundary_kind not in {"OUTER_PERIMETER", "PROTECTED_UNION"}:
            raise InterfaceBoundaryError(f"Unsupported boundary kind {self.boundary_kind!r}")
        for value in (
            self.functional_role,
            self.rigid_roll_reference_status,
            self.geometry_status,
            self.material_status,
            self.evidence_status,
        ):
            if not str(value).strip():
                raise InterfaceBoundaryError("Boundary metadata must be explicit")
        if self.boundary_kind == "OUTER_PERIMETER" and self.protected_region_ids:
            raise InterfaceBoundaryError("Outer perimeter cannot reference protected regions")
        if self.boundary_kind == "PROTECTED_UNION" and not self.protected_region_ids:
            raise InterfaceBoundaryError("Protected-union boundary requires source protected regions")
        if len(set(self.protected_region_ids)) != len(self.protected_region_ids):
            raise InterfaceBoundaryError("Protected source-region IDs cannot repeat")
        if self.nominal_transition_width_mm is not None or self.nominal_interface_thickness_mm is not None:
            raise InterfaceBoundaryError(
                "Iteration 12 cannot assign numeric transition width/interface thickness without authority"
            )
        if self.rigid_roll_reference_mm is not None:
            value = float(self.rigid_roll_reference_mm)
            if not math.isfinite(value) or value <= 0.0:
                raise InterfaceBoundaryError("Rigid roll reference must be finite and positive")
            object.__setattr__(self, "rigid_roll_reference_mm", value)

    def manifest(self) -> dict[str, object]:
        return {
            "boundary_id": self.boundary_id,
            "functional_role": self.functional_role,
            "boundary_kind": self.boundary_kind,
            "protected_region_ids": list(self.protected_region_ids),
            "compliance_intent": self.compliance_intent,
            "fluid_containment_intent": self.fluid_containment_intent,
            "protected_opening_exclusion_intent": self.protected_opening_exclusion_intent,
            "nominal_transition_width_mm": self.nominal_transition_width_mm,
            "nominal_interface_thickness_mm": self.nominal_interface_thickness_mm,
            "rigid_roll_reference_mm": self.rigid_roll_reference_mm,
            "rigid_roll_reference_status": self.rigid_roll_reference_status,
            "geometry_status": self.geometry_status,
            "material_status": self.material_status,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class InterfaceBoundaryEdge:
    edge_index: int
    boundary_id: str
    vertex_indices: tuple[int, int]
    incident_triangle_indices: tuple[int, ...]
    contact_triangle_index: int
    protected_triangle_index: int | None
    protected_region_id: str | None
    length_mm: float

    def __post_init__(self) -> None:
        if self.edge_index < 0 or self.contact_triangle_index < 0:
            raise InterfaceBoundaryError("Boundary/contact indices cannot be negative")
        if self.boundary_id not in BOUNDARY_IDS:
            raise InterfaceBoundaryError(f"Unknown edge boundary ID {self.boundary_id!r}")
        if len(self.vertex_indices) != 2 or self.vertex_indices[0] >= self.vertex_indices[1]:
            raise InterfaceBoundaryError("Boundary vertex pair must be sorted and distinct")
        if len(self.incident_triangle_indices) not in {1, 2}:
            raise InterfaceBoundaryError("Boundary edge must have one or two incident triangles")
        if self.contact_triangle_index not in self.incident_triangle_indices:
            raise InterfaceBoundaryError("Contact triangle must be incident to its boundary edge")
        if self.protected_triangle_index is None:
            if self.protected_region_id is not None:
                raise InterfaceBoundaryError("Outer edge cannot carry protected-region identity")
        else:
            if self.protected_triangle_index < 0 or self.protected_triangle_index not in self.incident_triangle_indices:
                raise InterfaceBoundaryError("Protected triangle must be a valid incident triangle")
            if not self.protected_region_id:
                raise InterfaceBoundaryError("Protected transition edge requires source-region identity")
        length = float(self.length_mm)
        if not math.isfinite(length) or length <= 0.0:
            raise InterfaceBoundaryError("Boundary edge length must be finite and positive")
        object.__setattr__(self, "length_mm", length)


@dataclass(frozen=True, slots=True)
class InterfaceBoundaryTopology:
    source_surface_id: str
    source_surface_sha256: str
    source_coverage_sha256: str
    source_interface_sha256: str
    definitions: tuple[InterfaceBoundaryDefinition, ...]
    edges: tuple[InterfaceBoundaryEdge, ...]
    topology_status: str
    evidence_status: str
    anatomical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.source_surface_id,
            self.source_surface_sha256,
            self.source_coverage_sha256,
            self.source_interface_sha256,
            self.topology_status,
            self.evidence_status,
        ):
            if not str(value).strip():
                raise InterfaceBoundaryError("Boundary source/status metadata must be explicit")
        for digest in (self.source_surface_sha256, self.source_coverage_sha256, self.source_interface_sha256):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.lower()):
                raise InterfaceBoundaryError("Boundary source hashes must be SHA-256 values")
        if self.anatomical_validation_eligible:
            raise InterfaceBoundaryError("Development edge topology cannot be anatomical-validation evidence")
        if tuple(item.boundary_id for item in self.definitions) != BOUNDARY_IDS:
            raise InterfaceBoundaryError("Boundary definitions must follow the controlled four-system order")
        if [edge.edge_index for edge in self.edges] != list(range(len(self.edges))):
            raise InterfaceBoundaryError("Boundary edge indices must be contiguous and deterministic")
        if len({edge.vertex_indices for edge in self.edges}) != len(self.edges):
            raise InterfaceBoundaryError("A mesh edge cannot belong to multiple material/no-material boundaries")

    @property
    def definition_by_id(self) -> dict[str, InterfaceBoundaryDefinition]:
        return {item.boundary_id: item for item in self.definitions}

    @property
    def edges_by_boundary(self) -> dict[str, tuple[InterfaceBoundaryEdge, ...]]:
        return {boundary_id: tuple(edge for edge in self.edges if edge.boundary_id == boundary_id) for boundary_id in BOUNDARY_IDS}

    @property
    def boundary_length_mm(self) -> dict[str, float]:
        return {boundary_id: sum(edge.length_mm for edge in edges) for boundary_id, edges in self.edges_by_boundary.items()}

    def source_region_length_mm(self, boundary_id: str, region_id: str) -> float:
        return sum(edge.length_mm for edge in self.edges_by_boundary[boundary_id] if edge.protected_region_id == region_id)

    def source_region_edge_count(self, boundary_id: str, region_id: str) -> int:
        return sum(1 for edge in self.edges_by_boundary[boundary_id] if edge.protected_region_id == region_id)

    def boundary_component_count(self, boundary_id: str) -> int:
        edges = self.edges_by_boundary[boundary_id]
        vertex_to_edges: dict[int, set[int]] = defaultdict(set)
        for edge in edges:
            for vertex in edge.vertex_indices:
                vertex_to_edges[vertex].add(edge.edge_index)
        remaining = {edge.edge_index for edge in edges}
        edge_by_index = {edge.edge_index: edge for edge in edges}
        components = 0
        while remaining:
            components += 1
            start = min(remaining)
            remaining.remove(start)
            queue: deque[int] = deque([start])
            while queue:
                current = queue.popleft()
                edge = edge_by_index[current]
                neighbors: set[int] = set()
                for vertex in edge.vertex_indices:
                    neighbors.update(vertex_to_edges[vertex])
                for neighbor in sorted(neighbors):
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        queue.append(neighbor)
        return components

    def boundary_is_closed_loop(self, boundary_id: str) -> bool:
        edges = self.edges_by_boundary[boundary_id]
        if not edges:
            return False
        degrees: dict[int, int] = defaultdict(int)
        for edge in edges:
            for vertex in edge.vertex_indices:
                degrees[vertex] += 1
        return all(degree == 2 for degree in degrees.values()) and self.boundary_component_count(boundary_id) == 1

    @property
    def topology_sha256(self) -> str:
        payload = {
            "source_surface_id": self.source_surface_id,
            "source_surface_sha256": self.source_surface_sha256,
            "source_coverage_sha256": self.source_coverage_sha256,
            "source_interface_sha256": self.source_interface_sha256,
            "definitions": [definition.manifest() for definition in self.definitions],
            "edges": [
                [edge.edge_index, edge.boundary_id, list(edge.vertex_indices), list(edge.incident_triangle_indices), edge.contact_triangle_index, edge.protected_triangle_index, edge.protected_region_id, round(edge.length_mm, 12)]
                for edge in self.edges
            ],
            "topology_status": self.topology_status,
            "evidence_status": self.evidence_status,
            "anatomical_validation_eligible": self.anatomical_validation_eligible,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def manifest(self) -> dict[str, object]:
        return {
            "source_surface_id": self.source_surface_id,
            "source_surface_sha256": self.source_surface_sha256,
            "source_coverage_sha256": self.source_coverage_sha256,
            "source_interface_sha256": self.source_interface_sha256,
            "definitions": [definition.manifest() for definition in self.definitions],
            "edge_count": len(self.edges),
            "boundary_edge_count": {item: len(edges) for item, edges in self.edges_by_boundary.items()},
            "boundary_length_mm": self.boundary_length_mm,
            "boundary_component_count": {item: self.boundary_component_count(item) for item in BOUNDARY_IDS},
            "boundary_closed_loop": {item: self.boundary_is_closed_loop(item) for item in BOUNDARY_IDS},
            "topology_status": self.topology_status,
            "evidence_status": self.evidence_status,
            "anatomical_validation_eligible": self.anatomical_validation_eligible,
            "topology_sha256": self.topology_sha256,
        }


def _definitions(authority: Authority) -> tuple[InterfaceBoundaryDefinition, ...]:
    common = {
        "compliance_intent": True,
        "nominal_transition_width_mm": None,
        "nominal_interface_thickness_mm": None,
        "geometry_status": "EDGE_TOPOLOGY_ONLY_WIDTH_PROFILE_AND_3D_CONFORMITY_UNRESOLVED",
        "material_status": "UNSELECTED_VALIDATION_GATED",
        "evidence_status": "FUNCTIONAL_EDGE_INTENT_ONLY_NOT_SEAL_FIT_INGRESS_OR_PRESSURE_VALIDATION",
    }
    protected = {"fluid_containment_intent": True, "protected_opening_exclusion_intent": True, **common}
    eye_roll = authority.number("geometry", "eye", "inner_edge_roll_radius_mm")
    return (
        InterfaceBoundaryDefinition(
            BOUNDARY_OUTER_PERIMETER,
            "outer compliant-interface perimeter and fluid-containment transition",
            "OUTER_PERIMETER", (),
            fluid_containment_intent=True,
            protected_opening_exclusion_intent=False,
            rigid_roll_reference_mm=None,
            rigid_roll_reference_status="NO_NUMERIC_RIGID_ROLL_REFERENCE_ASSIGNED",
            **common,
        ),
        InterfaceBoundaryDefinition(
            BOUNDARY_EYE_PROTECTED_UNION,
            "combined material/no-material boundary of overlapping bilateral eye protected envelopes",
            "PROTECTED_UNION", (REGION_PROTECTED_EYE_LEFT, REGION_PROTECTED_EYE_RIGHT),
            rigid_roll_reference_mm=eye_roll,
            rigid_roll_reference_status="RIGID_EYE_INNER_EDGE_DESIGN_BASELINE_REFERENCE_NOT_COMPLIANT_PROFILE",
            **protected,
        ),
        InterfaceBoundaryDefinition(
            BOUNDARY_MOUTH,
            "mouth material/no-material protected transition",
            "PROTECTED_UNION", (REGION_PROTECTED_MOUTH,),
            rigid_roll_reference_mm=None,
            rigid_roll_reference_status="NO_AUTHORITY_ROLL_RADIUS_DEFINED",
            **protected,
        ),
        InterfaceBoundaryDefinition(
            BOUNDARY_NOSTRIL_PROTECTED_UNION,
            "combined material/no-material boundary of overlapping bilateral nostril protected envelopes",
            "PROTECTED_UNION", (REGION_PROTECTED_NOSTRIL_LEFT, REGION_PROTECTED_NOSTRIL_RIGHT),
            rigid_roll_reference_mm=None,
            rigid_roll_reference_status="NO_AUTHORITY_ROLL_RADIUS_DEFINED",
            **protected,
        ),
    )


def build_interface_boundary_topology(authority: Authority, surface: FacialSurface, coverage: FacialCoverageMesh, interface: CompliantInterfaceTopology) -> InterfaceBoundaryTopology:
    """Extract true material/no-material boundary systems from the development segmentation."""
    if coverage.source_surface_id != surface.descriptor.surface_id or coverage.source_surface_sha256 != surface.descriptor.source_sha256:
        raise InterfaceBoundaryError("Coverage and facial surface source identities differ")
    if interface.source_surface_id != surface.descriptor.surface_id or interface.coverage_segmentation_sha256 != coverage.segmentation_sha256:
        raise InterfaceBoundaryError("Interface and coverage source identities differ")

    assignments = {item.triangle_index: item for item in interface.assignments}
    triangles = {item.triangle_index: item for item in coverage.triangles}
    if set(assignments) != set(triangles):
        raise InterfaceBoundaryError("Interface/coverage triangle sets differ")

    incidence: dict[tuple[int, int], list[int]] = defaultdict(list)
    for triangle in coverage.triangles:
        a, b, c = triangle.vertex_indices
        for u, v in ((a, b), (b, c), (c, a)):
            incidence[tuple(sorted((u, v)))].append(triangle.triangle_index)

    candidates: list[tuple[str, tuple[int, int], tuple[int, ...], int, int | None, str | None]] = []
    for vertex_pair, raw in sorted(incidence.items()):
        incident = tuple(sorted(raw))
        if len(incident) > 2:
            raise InterfaceBoundaryError(f"Non-manifold mesh edge {vertex_pair} has {len(incident)} triangles")
        if len(incident) == 1:
            triangle_id = incident[0]
            if not assignments[triangle_id].contact_intent:
                raise InterfaceBoundaryError("Protected region unexpectedly reaches outer development perimeter")
            candidates.append((BOUNDARY_OUTER_PERIMETER, vertex_pair, incident, triangle_id, None, None))
            continue
        first, second = incident
        first_contact = assignments[first].contact_intent
        second_contact = assignments[second].contact_intent
        if first_contact == second_contact:
            continue
        contact_id, protected_id = (first, second) if first_contact else (second, first)
        region_id = triangles[protected_id].region_id
        try:
            boundary_id = _PROTECTED_REGION_TO_BOUNDARY[region_id]
        except KeyError as exc:
            raise InterfaceBoundaryError(f"Unrecognized contact/protected transition region {region_id!r}") from exc
        candidates.append((boundary_id, vertex_pair, incident, contact_id, protected_id, region_id))

    vertices = surface.mesh.vertices
    edges = tuple(
        InterfaceBoundaryEdge(
            edge_index=index,
            boundary_id=boundary_id,
            vertex_indices=pair,
            incident_triangle_indices=incident,
            contact_triangle_index=contact_id,
            protected_triangle_index=protected_id,
            protected_region_id=region_id,
            length_mm=vertices[pair[0]].vector_to(vertices[pair[1]]).norm(),
        )
        for index, (boundary_id, pair, incident, contact_id, protected_id, region_id) in enumerate(candidates)
    )
    topology = InterfaceBoundaryTopology(
        source_surface_id=surface.descriptor.surface_id,
        source_surface_sha256=surface.descriptor.source_sha256,
        source_coverage_sha256=coverage.segmentation_sha256,
        source_interface_sha256=interface.topology_sha256,
        definitions=_definitions(authority),
        edges=edges,
        topology_status="PHASE2_ITERATION12_MATERIAL_NO_MATERIAL_UNION_BOUNDARY_TOPOLOGY",
        evidence_status="DETERMINISTIC_EDGE_TOPOLOGY_NOT_SEAL_FIT_INGRESS_PRESSURE_OR_ANATOMICAL_VALIDATION",
        anatomical_validation_eligible=False,
    )
    missing = [item for item, edge_set in topology.edges_by_boundary.items() if not edge_set]
    if missing:
        raise InterfaceBoundaryError(f"Boundary extraction produced empty systems: {missing}")
    for boundary_id in BOUNDARY_IDS:
        if not topology.boundary_is_closed_loop(boundary_id):
            raise InterfaceBoundaryError(f"Material/no-material boundary {boundary_id} is not one closed loop")
    for definition in topology.definitions:
        observed = {edge.protected_region_id for edge in topology.edges_by_boundary[definition.boundary_id] if edge.protected_region_id}
        if observed != set(definition.protected_region_ids):
            raise InterfaceBoundaryError(f"Boundary {definition.boundary_id} lost protected source-region provenance")
    return topology
