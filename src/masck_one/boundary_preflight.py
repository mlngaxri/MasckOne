from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from .interface_boundaries import (
    BOUNDARY_EYE_LEFT,
    BOUNDARY_EYE_RIGHT,
    BOUNDARY_IDS,
    BOUNDARY_NOSTRIL_LEFT,
    BOUNDARY_NOSTRIL_RIGHT,
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
    topology = model.interface_boundary_topology
    definitions = topology.definition_by_id
    lengths = topology.boundary_length_mm

    protected_transition_ok = True
    interface_by_id = {item.triangle_index: item for item in interface.assignments}
    coverage_by_id = {item.triangle_index: item for item in coverage.triangles}
    for boundary_id in BOUNDARY_IDS[1:]:
        definition = definitions[boundary_id]
        for edge in topology.edges_by_boundary[boundary_id]:
            if edge.protected_triangle_index is None:
                protected_transition_ok = False
                break
            if not interface_by_id[edge.contact_triangle_index].contact_intent:
                protected_transition_ok = False
                break
            if interface_by_id[edge.protected_triangle_index].contact_intent:
                protected_transition_ok = False
                break
            if coverage_by_id[edge.protected_triangle_index].region_id != definition.protected_region_id:
                protected_transition_ok = False
                break

    checks = [
        BoundaryPreflightCheck(
            "BOUNDARY_SOURCE_CHAIN",
            "PASS" if (
                topology.source_surface_id == model.facial_surface.descriptor.surface_id
                and topology.source_surface_sha256 == model.facial_surface.descriptor.source_sha256
                and topology.source_coverage_sha256 == coverage.segmentation_sha256
                and topology.source_interface_sha256 == interface.topology_sha256
            ) else "FAIL",
            "Interface-boundary topology is bound to the exact facial surface, coverage and compliant-interface revisions.",
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_SET_COMPLETENESS",
            "PASS" if tuple(topology.edges_by_boundary) == BOUNDARY_IDS and all(topology.edges_by_boundary[item] for item in BOUNDARY_IDS) else "FAIL",
            "Outer perimeter, both eyes, mouth and both nostril transitions are all present.",
            actual={item: len(topology.edges_by_boundary[item]) for item in BOUNDARY_IDS},
            expected="all six boundary edge sets non-empty",
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_LOOP_INTEGRITY",
            "PASS" if all(
                topology.boundary_component_count(item) == 1 and topology.boundary_is_closed_loop(item)
                for item in BOUNDARY_IDS
            ) else "FAIL",
            "Each controlled interface boundary is one deterministic closed edge loop on the current development mesh.",
            actual={
                item: {
                    "components": topology.boundary_component_count(item),
                    "closed": topology.boundary_is_closed_loop(item),
                }
                for item in BOUNDARY_IDS
            },
            expected="one closed component per boundary",
        ),
        BoundaryPreflightCheck(
            "PROTECTED_APERTURE_EDGE_SEMANTICS",
            "PASS" if protected_transition_ok else "FAIL",
            "Every aperture edge separates an active contact triangle from the intended protected eye, mouth or airway region.",
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_DIMENSION_AUTHORITY_DISCIPLINE",
            "PASS" if all(
                definition.nominal_transition_width_mm is None
                and definition.nominal_interface_thickness_mm is None
                for definition in topology.definitions
            ) else "FAIL",
            "No seal width, transition width or interface thickness is invented because the current authority does not define those values.",
            actual={
                item.boundary_id: {
                    "transition_width_mm": item.nominal_transition_width_mm,
                    "interface_thickness_mm": item.nominal_interface_thickness_mm,
                }
                for item in topology.definitions
            },
            expected="all unresolved",
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
            "The authority eye inner-edge roll radius is retained only as a rigid-edge design reference and is not misapplied as compliant-interface geometry.",
            actual={
                "left_mm": definitions[BOUNDARY_EYE_LEFT].rigid_roll_reference_mm,
                "right_mm": definitions[BOUNDARY_EYE_RIGHT].rigid_roll_reference_mm,
            },
            expected=authority.number("geometry", "eye", "inner_edge_roll_radius_mm"),
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_SAGITTAL_SYMMETRY",
            "PASS" if (
                abs(lengths[BOUNDARY_EYE_LEFT] - lengths[BOUNDARY_EYE_RIGHT]) <= 1e-6
                and abs(lengths[BOUNDARY_NOSTRIL_LEFT] - lengths[BOUNDARY_NOSTRIL_RIGHT]) <= 1e-6
            ) else "FAIL",
            "Neutral development eye and nostril boundary discretizations remain sagittally balanced.",
            actual={
                "eye_length_delta_mm": abs(lengths[BOUNDARY_EYE_LEFT] - lengths[BOUNDARY_EYE_RIGHT]),
                "nostril_length_delta_mm": abs(lengths[BOUNDARY_NOSTRIL_LEFT] - lengths[BOUNDARY_NOSTRIL_RIGHT]),
            },
            expected="both <= 1e-6 mm",
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_EVIDENCE_BOUNDARY",
            "PASS" if (
                topology.anatomical_validation_eligible is False
                and "NOT_SEAL_FIT_INGRESS_PRESSURE_OR_ANATOMICAL_VALIDATION" in topology.evidence_status
            ) else "FAIL",
            "Edge topology cannot satisfy seal, fit, ingress, pressure or anatomical validation gates.",
            actual={
                "anatomical_validation_eligible": topology.anatomical_validation_eligible,
                "evidence_status": topology.evidence_status,
            },
            expected={"anatomical_validation_eligible": False},
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
