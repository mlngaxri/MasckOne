from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math

from .authority import Authority
from .interface_boundaries import (
    BOUNDARY_OUTER_PERIMETER,
    PHYSICAL_BOUNDARY_OUTER_PERIMETER,
    InterfaceBoundaryTopology,
)


class InterfaceAttachmentError(ValueError):
    """Raised when the interface-to-frame attachment contract is violated."""


LAYER_STRUCTURAL_FRAME = "ATTACHMENT_LAYER_STRUCTURAL_FRAME_SIDE"
LAYER_COMPLIANT_INTERFACE = "ATTACHMENT_LAYER_COMPLIANT_INTERFACE_PERIMETER"
LAYER_RETENTION_MEMBER = "ATTACHMENT_LAYER_RETENTION_MEMBER_SIDE"
LAYER_IDS = (
    LAYER_STRUCTURAL_FRAME,
    LAYER_COMPLIANT_INTERFACE,
    LAYER_RETENTION_MEMBER,
)

ATTACHMENT_MODE = "MECHANICAL_PERIMETER_CAPTURE_DEVELOPMENT_ARCHITECTURE"


@dataclass(frozen=True, slots=True)
class AttachmentLayerRole:
    layer_id: str
    functional_role: str
    geometry_status: str
    material_status: str
    evidence_status: str

    def __post_init__(self) -> None:
        if self.layer_id not in LAYER_IDS:
            raise InterfaceAttachmentError(f"Unknown attachment layer ID {self.layer_id!r}")
        for value in (
            self.functional_role,
            self.geometry_status,
            self.material_status,
            self.evidence_status,
        ):
            if not str(value).strip():
                raise InterfaceAttachmentError("Attachment layer metadata must be explicit")

    def manifest(self) -> dict[str, object]:
        return {
            "layer_id": self.layer_id,
            "functional_role": self.functional_role,
            "geometry_status": self.geometry_status,
            "material_status": self.material_status,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class AttachmentEdgeAssignment:
    assignment_index: int
    source_boundary_edge_index: int
    vertex_indices: tuple[int, int]
    length_mm: float
    source_boundary_id: str = BOUNDARY_OUTER_PERIMETER
    physical_boundary_id: str = PHYSICAL_BOUNDARY_OUTER_PERIMETER
    attachment_intent: str = "PERIMETER_CAPTURE_PATH_INTENT"

    def __post_init__(self) -> None:
        if self.assignment_index < 0 or self.source_boundary_edge_index < 0:
            raise InterfaceAttachmentError("Attachment indices cannot be negative")
        if len(self.vertex_indices) != 2 or self.vertex_indices[0] >= self.vertex_indices[1]:
            raise InterfaceAttachmentError("Attachment vertex pair must be sorted and distinct")
        if self.source_boundary_id != BOUNDARY_OUTER_PERIMETER:
            raise InterfaceAttachmentError("Iteration 13 attachment path must derive from the outer perimeter")
        if self.physical_boundary_id != PHYSICAL_BOUNDARY_OUTER_PERIMETER:
            raise InterfaceAttachmentError("Iteration 13 physical attachment path must be the outer perimeter")
        length = float(self.length_mm)
        if not math.isfinite(length) or length <= 0.0:
            raise InterfaceAttachmentError("Attachment edge length must be finite and positive")
        if not self.attachment_intent.strip():
            raise InterfaceAttachmentError("Attachment intent must be explicit")
        object.__setattr__(self, "length_mm", length)

    def manifest(self) -> dict[str, object]:
        return {
            "assignment_index": self.assignment_index,
            "source_boundary_edge_index": self.source_boundary_edge_index,
            "vertex_indices": list(self.vertex_indices),
            "length_mm": self.length_mm,
            "source_boundary_id": self.source_boundary_id,
            "physical_boundary_id": self.physical_boundary_id,
            "attachment_intent": self.attachment_intent,
        }


@dataclass(frozen=True, slots=True)
class InterfaceAttachmentArchitecture:
    source_boundary_topology_sha256: str
    source_registered_mesh_sha256: str
    source_surface_revision: str
    structural_frame_reference_xy_mm: tuple[float, float]
    structural_frame_reference_status: str
    attachment_mode: str
    architecture_status: str
    structural_frame_topology_status: str
    layers: tuple[AttachmentLayerRole, ...]
    assignments: tuple[AttachmentEdgeAssignment, ...]
    clamp_band_width_mm: float | None
    capture_depth_mm: float | None
    interface_preload_N: float | None
    fastener_count: int | None
    fastener_pitch_mm: float | None
    interface_compression_percent: float | None
    retention_member_material: str | None
    evidence_status: str
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        for digest in (self.source_boundary_topology_sha256, self.source_registered_mesh_sha256):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.lower()):
                raise InterfaceAttachmentError("Attachment source hashes must be SHA-256 values")
        for value in (
            self.source_surface_revision,
            self.structural_frame_reference_status,
            self.attachment_mode,
            self.architecture_status,
            self.structural_frame_topology_status,
            self.evidence_status,
        ):
            if not str(value).strip():
                raise InterfaceAttachmentError("Attachment source/status metadata must be explicit")
        if self.attachment_mode != ATTACHMENT_MODE:
            raise InterfaceAttachmentError("Unsupported Iteration-13 attachment mode")
        width, height = (float(value) for value in self.structural_frame_reference_xy_mm)
        if not math.isfinite(width) or not math.isfinite(height) or width <= 0.0 or height <= 0.0:
            raise InterfaceAttachmentError("Structural-frame reference dimensions must be finite and positive")
        object.__setattr__(self, "structural_frame_reference_xy_mm", (width, height))
        if tuple(layer.layer_id for layer in self.layers) != LAYER_IDS:
            raise InterfaceAttachmentError("Attachment layer roles must follow the controlled three-layer order")
        if not self.assignments:
            raise InterfaceAttachmentError("Attachment architecture requires perimeter edge assignments")
        if [item.assignment_index for item in self.assignments] != list(range(len(self.assignments))):
            raise InterfaceAttachmentError("Attachment assignment indices must be contiguous and deterministic")
        if len({item.source_boundary_edge_index for item in self.assignments}) != len(self.assignments):
            raise InterfaceAttachmentError("A source perimeter edge cannot be assigned more than once")
        unsupported_numeric = {
            "clamp_band_width_mm": self.clamp_band_width_mm,
            "capture_depth_mm": self.capture_depth_mm,
            "interface_preload_N": self.interface_preload_N,
            "fastener_count": self.fastener_count,
            "fastener_pitch_mm": self.fastener_pitch_mm,
            "interface_compression_percent": self.interface_compression_percent,
        }
        supplied = {key: value for key, value in unsupported_numeric.items() if value is not None}
        if supplied:
            raise InterfaceAttachmentError(
                f"Iteration 13 cannot invent unresolved attachment dimensions/load/counts: {sorted(supplied)}"
            )
        if self.retention_member_material is not None:
            raise InterfaceAttachmentError("Iteration 13 cannot select a retention-member material without evidence")
        if self.physical_validation_eligible:
            raise InterfaceAttachmentError("Digital attachment architecture cannot be physical-validation evidence")

    @property
    def total_path_length_mm(self) -> float:
        return sum(item.length_mm for item in self.assignments)

    @property
    def topology_sha256(self) -> str:
        payload = {
            "source_boundary_topology_sha256": self.source_boundary_topology_sha256,
            "source_registered_mesh_sha256": self.source_registered_mesh_sha256,
            "source_surface_revision": self.source_surface_revision,
            "structural_frame_reference_xy_mm": list(self.structural_frame_reference_xy_mm),
            "structural_frame_reference_status": self.structural_frame_reference_status,
            "attachment_mode": self.attachment_mode,
            "architecture_status": self.architecture_status,
            "structural_frame_topology_status": self.structural_frame_topology_status,
            "layers": [layer.manifest() for layer in self.layers],
            "assignments": [item.manifest() for item in self.assignments],
            "clamp_band_width_mm": self.clamp_band_width_mm,
            "capture_depth_mm": self.capture_depth_mm,
            "interface_preload_N": self.interface_preload_N,
            "fastener_count": self.fastener_count,
            "fastener_pitch_mm": self.fastener_pitch_mm,
            "interface_compression_percent": self.interface_compression_percent,
            "retention_member_material": self.retention_member_material,
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self) -> dict[str, object]:
        return {
            "source_boundary_topology_sha256": self.source_boundary_topology_sha256,
            "source_registered_mesh_sha256": self.source_registered_mesh_sha256,
            "source_surface_revision": self.source_surface_revision,
            "structural_frame_reference_xy_mm": list(self.structural_frame_reference_xy_mm),
            "structural_frame_reference_status": self.structural_frame_reference_status,
            "attachment_mode": self.attachment_mode,
            "architecture_status": self.architecture_status,
            "structural_frame_topology_status": self.structural_frame_topology_status,
            "layers": [layer.manifest() for layer in self.layers],
            "assignment_count": len(self.assignments),
            "assignments": [item.manifest() for item in self.assignments],
            "total_path_length_mm": self.total_path_length_mm,
            "clamp_band_width_mm": self.clamp_band_width_mm,
            "capture_depth_mm": self.capture_depth_mm,
            "interface_preload_N": self.interface_preload_N,
            "fastener_count": self.fastener_count,
            "fastener_pitch_mm": self.fastener_pitch_mm,
            "interface_compression_percent": self.interface_compression_percent,
            "retention_member_material": self.retention_member_material,
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
            "topology_sha256": self.topology_sha256,
        }


def _layers() -> tuple[AttachmentLayerRole, ...]:
    return (
        AttachmentLayerRole(
            LAYER_STRUCTURAL_FRAME,
            "future structural-frame reaction side of the perimeter capture",
            "REFERENCE_ROLE_ONLY_STRUCTURAL_FRAME_TOPOLOGY_DEFERRED_TO_ITERATION15",
            "UNSELECTED_VALIDATION_GATED",
            "ARCHITECTURAL_ROLE_ONLY_NOT_LOAD_PATH_OR_DURABILITY_EVIDENCE",
        ),
        AttachmentLayerRole(
            LAYER_COMPLIANT_INTERFACE,
            "compliant-interface outer perimeter captured between structural and retention roles",
            "SOURCE_BOUNDARY_TOPOLOGY_BOUND_CAPTURE_PROFILE_UNRESOLVED",
            "UNSELECTED_VALIDATION_GATED",
            "CAPTURE_INTENT_ONLY_NOT_COMPRESSION_SEAL_OR_RETENTION_VALIDATION",
        ),
        AttachmentLayerRole(
            LAYER_RETENTION_MEMBER,
            "abstract mechanical retention side completing the perimeter capture stack",
            "ABSTRACT_RETENTION_ROLE_GEOMETRY_FASTENING_AND_SERVICE_STRATEGY_UNRESOLVED",
            "UNSELECTED_VALIDATION_GATED",
            "DEVELOPMENT_ARCHITECTURE_ROLE_NOT_PRODUCTION_COMPONENT_FREEZE",
        ),
    )


def build_interface_attachment_architecture(
    authority: Authority,
    boundaries: InterfaceBoundaryTopology,
) -> InterfaceAttachmentArchitecture:
    """Bind a development mechanical-capture architecture to the exact outer boundary.

    This iteration chooses a mechanical perimeter-capture architecture at the role/topology
    level. It deliberately does not invent clamp width, capture depth, preload, fasteners,
    compression, retention material or the future structural-frame geometry.
    """

    if boundaries.physical_boundary_component_count(PHYSICAL_BOUNDARY_OUTER_PERIMETER) != 1:
        raise InterfaceAttachmentError("Source outer perimeter must contain one physical component")
    if not boundaries.physical_boundary_is_closed_loop(PHYSICAL_BOUNDARY_OUTER_PERIMETER):
        raise InterfaceAttachmentError("Source outer perimeter must be a closed physical loop")
    outer_edges = boundaries.physical_edges_by_boundary[PHYSICAL_BOUNDARY_OUTER_PERIMETER]
    if not outer_edges:
        raise InterfaceAttachmentError("Source boundary topology contains no outer-perimeter edges")
    if any(edge.boundary_id != BOUNDARY_OUTER_PERIMETER for edge in outer_edges):
        raise InterfaceAttachmentError("Outer physical boundary contains non-outer provenance edges")

    assignments = tuple(
        AttachmentEdgeAssignment(
            assignment_index=index,
            source_boundary_edge_index=edge.edge_index,
            vertex_indices=edge.vertex_indices,
            length_mm=edge.length_mm,
        )
        for index, edge in enumerate(sorted(outer_edges, key=lambda item: item.edge_index))
    )

    return InterfaceAttachmentArchitecture(
        source_boundary_topology_sha256=boundaries.topology_sha256,
        source_registered_mesh_sha256=boundaries.source_registered_mesh_sha256,
        source_surface_revision=boundaries.source_surface_revision,
        structural_frame_reference_xy_mm=authority.pair("geometry", "functional_frame_xy_mm"),
        structural_frame_reference_status=str(authority.get("geometry", "functional_frame_status")),
        attachment_mode=ATTACHMENT_MODE,
        architecture_status="DEVELOPMENT_ARCHITECTURE_CANDIDATE_NOT_PRODUCTION_FREEZE",
        structural_frame_topology_status="DEFERRED_TO_ITERATION15_ONLY_AUTHORITY_FRAME_XY_REFERENCE_USED",
        layers=_layers(),
        assignments=assignments,
        clamp_band_width_mm=None,
        capture_depth_mm=None,
        interface_preload_N=None,
        fastener_count=None,
        fastener_pitch_mm=None,
        interface_compression_percent=None,
        retention_member_material=None,
        evidence_status=(
            "DIGITAL_ATTACHMENT_TOPOLOGY_ONLY_NOT_SEAL_RETENTION_LOAD_DURABILITY_ASSEMBLY_OR_PHYSICAL_VALIDATION"
        ),
        physical_validation_eligible=False,
    )
