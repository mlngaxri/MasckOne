from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from .interface_boundaries import (
    BOUNDARY_EYE_LEFT,
    BOUNDARY_EYE_RIGHT,
    BOUNDARY_IDS,
    BOUNDARY_NOSTRIL_LEFT,
    BOUNDARY_NOSTRIL_RIGHT,
    PHYSICAL_BOUNDARY_IDS,
    build_interface_boundary_topology,
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


def run_boundary_preflight() -> dict[str, object]:
    model = build_model()
    authority = model.authority
    coverage = model.coverage_mesh
    interface = model.compliant_interface_topology
    topology = build_interface_boundary_topology(authority, model.facial_surface, coverage, interface)
    definitions = topology.definition_by_id
    provenance_lengths = topology.boundary_length_mm

    protected_transition_ok = True
    interface_by_id = {item.triangle_index: item for item in interface.assignments}
    coverage_by_id = {item.triangle_index: item for item in coverage.triangles}
    for boundary_id in BOUNDARY_IDS[1:]:
        definition = definitions[boundary_id]
        for edge in topology.edges_by_boundary[boundary_id]:
            protected_id = edge.protected_triangle_index
            if protected_id is None:
                protected_transition_ok = False
                break
            if not interface_by_id[edge.contact_triangle_index].contact_intent:
                protected_transition_ok = False
                break
            if interface_by_id[protected_id].contact_intent:
                protected_transition_ok = False
                break
            if coverage_by_id[protected_id].region_id != definition.protected_region_id:
                protected_transition_ok = False
                break

    physical_loop_ok = all(
        topology.physical_boundary_component_count(item) == 1
        and topology.physical_boundary_is_closed_loop(item)
        for item in PHYSICAL_BOUNDARY_IDS
    )

    checks = [
        BoundaryPreflightCheck(
            "BOUNDARY_SOURCE_CHAIN",
            "PASS" if (
                topology.source_surface_id == model.facial_surface.descriptor.surface_id
                and topology.source_surface_sha256 == model.facial_surface.descriptor.source_sha256
                and topology.source_registered_mesh_sha256 == model.facial_surface.mesh.normalized_sha256()
                and topology.source_surface_revision == model.facial_surface.descriptor.source_revision
                and topology.source_coverage_sha256 == coverage.segmentation_sha256
                and topology.source_interface_sha256 == interface.topology_sha256
            ) else "FAIL",
            "Boundary topology records the exact source asset, registered mesh, registration revision, coverage and compliant-interface revisions.",
            actual={
                "registered_mesh_sha256": topology.source_registered_mesh_sha256,
                "surface_revision": topology.source_surface_revision,
                "coverage_sha256": topology.source_coverage_sha256,
                "interface_sha256": topology.source_interface_sha256,
            },
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_PROVENANCE_COMPLETENESS",
            "PASS" if tuple(topology.edges_by_boundary) == BOUNDARY_IDS and all(topology.edges_by_boundary[item] for item in BOUNDARY_IDS) else "FAIL",
            "All six source-region provenance partitions are retained, including separate left/right eye and nostril labels.",
            actual={item: len(topology.edges_by_boundary[item]) for item in BOUNDARY_IDS},
        ),
        BoundaryPreflightCheck(
            "PHYSICAL_BOUNDARY_LOOP_INTEGRITY",
            "PASS" if physical_loop_ok else "FAIL",
            "Physical material/no-material boundaries are evaluated as four closed systems: outer perimeter, bilateral eye union, mouth and bilateral nostril union.",
            actual={
                item: {
                    "components": topology.physical_boundary_component_count(item),
                    "closed": topology.physical_boundary_is_closed_loop(item),
                    "edge_count": len(topology.physical_edges_by_boundary[item]),
                }
                for item in PHYSICAL_BOUNDARY_IDS
            },
            expected="one closed component per physical boundary",
        ),
        BoundaryPreflightCheck(
            "PROTECTED_APERTURE_EDGE_SEMANTICS",
            "PASS" if protected_transition_ok else "FAIL",
            "Every aperture edge separates active contact from the source-labelled protected eye, mouth or airway region.",
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_DIMENSION_AUTHORITY_DISCIPLINE",
            "PASS" if all(
                definition.nominal_transition_width_mm is None
                and definition.nominal_interface_thickness_mm is None
                for definition in topology.definitions
            ) else "FAIL",
            "No seal width, transition width or general interface thickness is invented where authority is absent.",
        ),
        BoundaryPreflightCheck(
            "EYE_RIGID_ROLL_REFERENCE",
            "PASS" if (
                definitions[BOUNDARY_EYE_LEFT].rigid_roll_reference_mm
                == authority.number("geometry", "eye", "inner_edge_roll_radius_mm")
                == definitions[BOUNDARY_EYE_RIGHT].rigid_roll_reference_mm
                and "NOT_COMPLIANT_PROFILE" in definitions[BOUNDARY_EYE_LEFT].rigid_roll_reference_status
                and "NOT_COMPLIANT_PROFILE" in definitions[BOUNDARY_EYE_RIGHT].rigid_roll_reference_status
            ) else "FAIL",
            "The eye inner-edge roll remains a rigid-edge reference only, not compliant seal geometry.",
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_PROVENANCE_SAGITTAL_BALANCE",
            "PASS" if (
                abs(provenance_lengths[BOUNDARY_EYE_LEFT] - provenance_lengths[BOUNDARY_EYE_RIGHT]) <= 1e-6
                and abs(provenance_lengths[BOUNDARY_NOSTRIL_LEFT] - provenance_lengths[BOUNDARY_NOSTRIL_RIGHT]) <= 1e-6
            ) else "FAIL",
            "Left/right provenance partitions remain sagittally balanced even though physical closure is checked on bilateral unions.",
            actual={
                "eye_delta_mm": abs(provenance_lengths[BOUNDARY_EYE_LEFT] - provenance_lengths[BOUNDARY_EYE_RIGHT]),
                "nostril_delta_mm": abs(provenance_lengths[BOUNDARY_NOSTRIL_LEFT] - provenance_lengths[BOUNDARY_NOSTRIL_RIGHT]),
            },
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_EVIDENCE_BOUNDARY",
            "PASS" if (
                topology.anatomical_validation_eligible is False
                and "NOT_SEAL_FIT_INGRESS_PRESSURE_OR_ANATOMICAL_VALIDATION" in topology.evidence_status
            ) else "FAIL",
            "Digital edge topology does not close seal, fit, ingress, pressure, material or anatomical evidence gates.",
        ),
    ]

    result = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {
        "project": "Masck One",
        "phase": 2,
        "iteration": 12,
        "result": result,
        "checks": [check.to_dict() for check in checks],
        "boundary_topology_sha256": topology.topology_sha256,
    }


def main() -> int:
    report = run_boundary_preflight()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
