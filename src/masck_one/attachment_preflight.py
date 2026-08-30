from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from .boundary_release import build_verified_interface_boundary_topology
from .interface_attachment import (
    LAYER_IDS,
    build_interface_attachment_architecture,
)
from .interface_boundaries import PHYSICAL_BOUNDARY_OUTER_PERIMETER
from .model import build_model


@dataclass(frozen=True)
class AttachmentPreflightCheck:
    id: str
    status: str
    message: str
    actual: object | None = None
    expected: object | None = None

    def to_dict(self) -> dict[str, object | None]:
        return asdict(self)


def run_attachment_preflight() -> dict[str, object]:
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    outer_edges = tuple(
        sorted(
            boundaries.physical_edges_by_boundary[PHYSICAL_BOUNDARY_OUTER_PERIMETER],
            key=lambda edge: edge.edge_index,
        )
    )

    assignment_edges = tuple(item.source_boundary_edge_index for item in attachment.assignments)
    source_edges = tuple(edge.edge_index for edge in outer_edges)
    assignment_vertices = tuple(item.vertex_indices for item in attachment.assignments)
    source_vertices = tuple(edge.vertex_indices for edge in outer_edges)
    source_length = sum(edge.length_mm for edge in outer_edges)

    unresolved = {
        "clamp_band_width_mm": attachment.clamp_band_width_mm,
        "capture_depth_mm": attachment.capture_depth_mm,
        "interface_preload_N": attachment.interface_preload_N,
        "fastener_count": attachment.fastener_count,
        "fastener_pitch_mm": attachment.fastener_pitch_mm,
        "interface_compression_percent": attachment.interface_compression_percent,
        "retention_member_material": attachment.retention_member_material,
    }

    checks = [
        AttachmentPreflightCheck(
            "ATTACHMENT_SOURCE_CHAIN",
            "PASS" if (
                attachment.source_boundary_topology_sha256 == boundaries.topology_sha256
                and attachment.source_registered_mesh_sha256 == boundaries.source_registered_mesh_sha256
                and attachment.source_surface_revision == boundaries.source_surface_revision
            ) else "FAIL",
            "Attachment architecture is bound to the exact verified Iteration-12 boundary revision.",
        ),
        AttachmentPreflightCheck(
            "ATTACHMENT_OUTER_PATH_EXACTNESS",
            "PASS" if assignment_edges == source_edges and assignment_vertices == source_vertices else "FAIL",
            "Every physical outer-perimeter edge is captured exactly once with unchanged edge and vertex identity.",
            actual={"assignment_count": len(assignment_edges), "source_edge_count": len(source_edges)},
            expected="exact one-to-one mapping",
        ),
        AttachmentPreflightCheck(
            "ATTACHMENT_PATH_LENGTH_CONSERVATION",
            "PASS" if abs(attachment.total_path_length_mm - source_length) <= 1e-9 else "FAIL",
            "Attachment path length is inherited from the source boundary without geometric invention.",
            actual=attachment.total_path_length_mm,
            expected=source_length,
        ),
        AttachmentPreflightCheck(
            "STRUCTURAL_FRAME_REFERENCE_AUTHORITY",
            "PASS" if (
                attachment.structural_frame_reference_xy_mm
                == model.authority.pair("geometry", "functional_frame_xy_mm")
                and attachment.structural_frame_reference_status
                == str(model.authority.get("geometry", "functional_frame_status"))
            ) else "FAIL",
            "Only the authority functional-frame XY reference is carried forward; structural-frame topology remains deferred.",
            actual={
                "xy_mm": list(attachment.structural_frame_reference_xy_mm),
                "status": attachment.structural_frame_reference_status,
            },
        ),
        AttachmentPreflightCheck(
            "ATTACHMENT_LAYER_ROLE_COMPLETENESS",
            "PASS" if tuple(layer.layer_id for layer in attachment.layers) == LAYER_IDS else "FAIL",
            "The development capture stack preserves explicit frame-side, compliant-interface and retention-side roles.",
        ),
        AttachmentPreflightCheck(
            "ATTACHMENT_DIMENSION_AUTHORITY_DISCIPLINE",
            "PASS" if all(value is None for value in unresolved.values()) else "FAIL",
            "No clamp width, capture depth, preload, fastener scheme, compression target or retention material is invented.",
            actual=unresolved,
            expected="all unresolved",
        ),
        AttachmentPreflightCheck(
            "STRUCTURAL_FRAME_DEPENDENCY_DISCIPLINE",
            "PASS" if "DEFERRED_TO_ITERATION15" in attachment.structural_frame_topology_status else "FAIL",
            "Iteration 13 does not pretend the Iteration-15 structural frame topology already exists.",
            actual=attachment.structural_frame_topology_status,
        ),
        AttachmentPreflightCheck(
            "ATTACHMENT_EVIDENCE_BOUNDARY",
            "PASS" if (
                attachment.physical_validation_eligible is False
                and "NOT_SEAL_RETENTION_LOAD_DURABILITY_ASSEMBLY_OR_PHYSICAL_VALIDATION"
                in attachment.evidence_status
            ) else "FAIL",
            "Digital attachment topology cannot satisfy seal, retention, load, durability, assembly or physical-validation gates.",
        ),
    ]

    result = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {
        "project": "Masck One",
        "phase": 2,
        "iteration": 13,
        "result": result,
        "checks": [check.to_dict() for check in checks],
        "attachment_topology_sha256": attachment.topology_sha256,
    }


def main() -> int:
    report = run_attachment_preflight()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
