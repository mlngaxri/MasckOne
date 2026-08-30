from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from .interface_boundaries import (
    BOUNDARY_KINDS,
    EDGE_NASAL_MAIN,
    EDGE_NASAL_ROLE,
    EDGE_OUTER_PERIMETER,
    EDGE_PROTECTED_APERTURE,
)
from .model import build_model


@dataclass(frozen=True)
class BoundaryPreflightCheck:
    id: str
    status: str
    message: str
    actual: object | None = None
    expected: object | None = None

    def to_dict(self) -> dict[str, object | None]:
        return asdict(self)


def run_interface_boundary_preflight() -> dict[str, object]:
    model = build_model()
    authority = model.authority
    topology = model.interface_boundary_topology
    coverage = model.coverage_mesh
    interface = model.compliant_interface_topology
    nasal = model.nasal_subsystem_topology

    counts = {kind: len(topology.edges_by_kind[kind]) for kind in BOUNDARY_KINDS}
    protected_ids = {
        triangle.protected_zone_id
        for triangle in coverage.protected_triangles
        if triangle.protected_zone_id is not None
    }
    transition_ids = {edge.protected_zone_id for edge in topology.protected_aperture_edges}
    nostril_edges = [
        edge
        for edge in topology.protected_aperture_edges
        if edge.protected_zone_id in {
            "MASCK_ONE-PROTECTED-NOSTRIL-LEFT",
            "MASCK_ONE-PROTECTED-NOSTRIL-RIGHT",
        }
    ]
    intent = topology.perimeter_intent
    seam = topology.visible_seam_authority
    eye_roll = topology.eye_inner_edge_roll_authority

    checks = [
        BoundaryPreflightCheck(
            "BOUNDARY_SOURCE_CHAIN",
            "PASS" if (
                topology.source_surface_id == model.facial_surface.descriptor.surface_id
                and topology.source_surface_sha256 == model.facial_surface.descriptor.source_sha256
                and topology.source_coverage_sha256 == coverage.segmentation_sha256
                and topology.source_interface_sha256 == interface.topology_sha256
                and topology.source_nasal_sha256 == nasal.topology_sha256
            ) else "FAIL",
            "Interface-boundary topology is cryptographically bound to the exact surface, coverage, interface and nasal revisions it classifies.",
        ),
        BoundaryPreflightCheck(
            "OUTER_PERIMETER_CLOSURE",
            "PASS" if (
                topology.mesh_outer_edge_count > 0
                and counts[EDGE_OUTER_PERIMETER] == topology.mesh_outer_edge_count
                and all(edge.seal_intent for edge in topology.outer_perimeter_edges)
            ) else "FAIL",
            "Every one-incident-triangle surface edge is represented exactly once as outer perimeter seal/compliance intent.",
            actual={"mesh_outer_edges": topology.mesh_outer_edge_count, "classified_outer_edges": counts[EDGE_OUTER_PERIMETER]},
            expected="equal positive counts",
        ),
        BoundaryPreflightCheck(
            "PERIMETER_NUMERIC_DISCIPLINE",
            "PASS" if (
                intent.seal_intent
                and intent.seal_width_mm is None
                and intent.seal_thickness_mm is None
                and intent.compression_mm is None
                and intent.compression_ratio is None
                and intent.preload_N is None
            ) else "FAIL",
            "Iteration 12 carries perimeter seal/compliance intent without inventing width, thickness, compression or preload values absent from authority.",
            actual=intent.manifest(),
            expected={"seal_intent": True, "numeric_geometry_and_preload": None},
        ),
        BoundaryPreflightCheck(
            "PROTECTED_APERTURE_TRANSITION_CLOSURE",
            "PASS" if (
                transition_ids == protected_ids
                and counts[EDGE_PROTECTED_APERTURE] > 0
                and all(not edge.material_bridge_allowed and not edge.seal_intent for edge in topology.protected_aperture_edges)
            ) else "FAIL",
            "Every protected eye/mouth/nostril region has explicit contact-to-protected transition edges and none permit material bridging.",
            actual={"protected_zone_ids": sorted(protected_ids), "transition_zone_ids": sorted(item for item in transition_ids if item)},
            expected=sorted(protected_ids),
        ),
        BoundaryPreflightCheck(
            "AIRWAY_TRANSITION_NONBRIDGING",
            "PASS" if (
                bool(nostril_edges)
                and {edge.protected_zone_id for edge in nostril_edges} == {
                    "MASCK_ONE-PROTECTED-NOSTRIL-LEFT",
                    "MASCK_ONE-PROTECTED-NOSTRIL-RIGHT",
                }
                and all(not edge.material_bridge_allowed for edge in nostril_edges)
            ) else "FAIL",
            "Both nostril/airway protected transitions remain explicit no-material-bridge boundaries.",
            actual=len(nostril_edges),
            expected="> 0 edges spanning both protected nostril IDs",
        ),
        BoundaryPreflightCheck(
            "NASAL_TRANSITION_TOPOLOGY",
            "PASS" if counts[EDGE_NASAL_MAIN] > 0 and counts[EDGE_NASAL_ROLE] > 0 else "FAIL",
            "Dedicated nasal subsystem boundaries expose both nasal-to-main-interface and internal nasal-role transitions.",
            actual={"nasal_main_edges": counts[EDGE_NASAL_MAIN], "nasal_role_edges": counts[EDGE_NASAL_ROLE]},
            expected="both positive",
        ),
        BoundaryPreflightCheck(
            "VISIBLE_SEAM_AUTHORITY_BOUNDARY",
            "PASS" if (
                seam.gap_mm == authority.number("geometry", "visible_seam", "gap_mm")
                and seam.tolerance_mm == authority.number("geometry", "visible_seam", "tolerance_mm")
                and seam.flush_mismatch_max_mm == authority.number("geometry", "visible_seam", "flush_mismatch_max_mm")
                and "PLACEMENT_UNRESOLVED" in seam.application_status
            ) else "FAIL",
            "Visible-seam numbers are preserved exactly but are not assigned to an unproven perimeter/frame seam location.",
            actual=seam.manifest(),
            expected={"gap_mm": 0.40, "tolerance_mm": 0.15, "flush_mismatch_max_mm": 0.15, "placement": "unresolved"},
        ),
        BoundaryPreflightCheck(
            "EYE_ROLL_AUTHORITY_BOUNDARY",
            "PASS" if (
                eye_roll.radius_mm == authority.number("geometry", "eye", "inner_edge_roll_radius_mm")
                and "NOT_MAPPED_TO_CONSERVATIVE_PROTECTED_ENVELOPE_TRANSITION" in eye_roll.application_status
            ) else "FAIL",
            "The 3 mm visual-aperture inner-edge roll authority is preserved without falsely applying it to the larger conservative protected-envelope boundary.",
            actual=eye_roll.manifest(),
            expected={"radius_mm": 3.0, "mapping": "unresolved"},
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_EVIDENCE_STATUS",
            "PASS" if (
                topology.anatomical_validation_eligible is False
                and "NOT_ANATOMICAL" in topology.evidence_status
                and len(topology.topology_sha256) == 64
            ) else "FAIL",
            "Development edge lengths/topology remain ineligible as anatomical fit, seal, leak or pressure evidence.",
            actual={"anatomical_validation_eligible": topology.anatomical_validation_eligible, "sha256_length": len(topology.topology_sha256)},
            expected={"anatomical_validation_eligible": False, "sha256_length": 64},
        ),
    ]

    result = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {
        "project": "Masck One",
        "phase": 2,
        "iteration": 12,
        "result": result,
        "checks": [check.to_dict() for check in checks],
        "boundary_manifest": topology.manifest(),
    }


def main() -> int:
    report = run_interface_boundary_preflight()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
