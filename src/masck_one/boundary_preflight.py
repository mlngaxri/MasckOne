from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from .coverage import (
    REGION_PROTECTED_EYE_LEFT,
    REGION_PROTECTED_EYE_RIGHT,
    REGION_PROTECTED_NOSTRIL_LEFT,
    REGION_PROTECTED_NOSTRIL_RIGHT,
)
from .interface_boundaries import (
    BOUNDARY_EYE_PROTECTED_UNION,
    BOUNDARY_IDS,
    BOUNDARY_NOSTRIL_PROTECTED_UNION,
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
    interface_by_id = {item.triangle_index: item for item in interface.assignments}
    coverage_by_id = {item.triangle_index: item for item in coverage.triangles}

    protected_transition_ok = True
    source_provenance_ok = True
    for boundary_id in BOUNDARY_IDS[1:]:
        definition = definitions[boundary_id]
        observed_regions: set[str] = set()
        for edge in topology.edges_by_boundary[boundary_id]:
            if edge.protected_triangle_index is None or edge.protected_region_id is None:
                protected_transition_ok = False
                break
            observed_regions.add(edge.protected_region_id)
            if not interface_by_id[edge.contact_triangle_index].contact_intent:
                protected_transition_ok = False
                break
            if interface_by_id[edge.protected_triangle_index].contact_intent:
                protected_transition_ok = False
                break
            if coverage_by_id[edge.protected_triangle_index].region_id != edge.protected_region_id:
                protected_transition_ok = False
                break
        if observed_regions != set(definition.protected_region_ids):
            source_provenance_ok = False

    eye_left_length = topology.source_region_length_mm(BOUNDARY_EYE_PROTECTED_UNION, REGION_PROTECTED_EYE_LEFT)
    eye_right_length = topology.source_region_length_mm(BOUNDARY_EYE_PROTECTED_UNION, REGION_PROTECTED_EYE_RIGHT)
    nostril_left_length = topology.source_region_length_mm(BOUNDARY_NOSTRIL_PROTECTED_UNION, REGION_PROTECTED_NOSTRIL_LEFT)
    nostril_right_length = topology.source_region_length_mm(BOUNDARY_NOSTRIL_PROTECTED_UNION, REGION_PROTECTED_NOSTRIL_RIGHT)

    checks = [
        BoundaryPreflightCheck(
            "BOUNDARY_SOURCE_CHAIN",
            "PASS" if (
                topology.source_surface_id == model.facial_surface.descriptor.surface_id
                and topology.source_surface_sha256 == model.facial_surface.descriptor.source_sha256
                and topology.source_coverage_sha256 == coverage.segmentation_sha256
                and topology.source_interface_sha256 == interface.topology_sha256
            ) else "FAIL",
            "Boundary topology is bound to the exact surface, coverage and compliant-interface revisions.",
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_SET_COMPLETENESS",
            "PASS" if tuple(topology.edges_by_boundary) == BOUNDARY_IDS and all(topology.edges_by_boundary[item] for item in BOUNDARY_IDS) else "FAIL",
            "The actual material/no-material topology contains outer perimeter, combined eye protected union, mouth and combined nostril protected union systems.",
            actual={item: len(topology.edges_by_boundary[item]) for item in BOUNDARY_IDS},
            expected="all four material/no-material systems non-empty",
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_LOOP_INTEGRITY",
            "PASS" if all(topology.boundary_component_count(item) == 1 and topology.boundary_is_closed_loop(item) for item in BOUNDARY_IDS) else "FAIL",
            "Every actual material/no-material boundary is one deterministic closed loop after overlapping bilateral protected regions are unioned.",
            actual={item: {"components": topology.boundary_component_count(item), "closed": topology.boundary_is_closed_loop(item)} for item in BOUNDARY_IDS},
            expected="one closed component per material/no-material boundary",
        ),
        BoundaryPreflightCheck(
            "PROTECTED_UNION_EDGE_SEMANTICS",
            "PASS" if protected_transition_ok and source_provenance_ok else "FAIL",
            "Every protected-union edge separates active contact from a protected source region, while left/right provenance remains complete inside bilateral unions.",
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_DIMENSION_AUTHORITY_DISCIPLINE",
            "PASS" if all(definition.nominal_transition_width_mm is None and definition.nominal_interface_thickness_mm is None for definition in topology.definitions) else "FAIL",
            "No seal width, transition width or interface thickness is invented because current authority does not define those values.",
        ),
        BoundaryPreflightCheck(
            "EYE_RIGID_ROLL_REFERENCE",
            "PASS" if (
                definitions[BOUNDARY_EYE_PROTECTED_UNION].rigid_roll_reference_mm == authority.number("geometry", "eye", "inner_edge_roll_radius_mm")
                and "NOT_COMPLIANT_PROFILE" in definitions[BOUNDARY_EYE_PROTECTED_UNION].rigid_roll_reference_status
            ) else "FAIL",
            "The authority eye inner-edge roll radius remains only a rigid-edge reference.",
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_BILATERAL_PROVENANCE_BALANCE",
            "PASS" if abs(eye_left_length - eye_right_length) <= 1e-6 and abs(nostril_left_length - nostril_right_length) <= 1e-6 else "FAIL",
            "Neutral left/right semantic contributions to bilateral union boundaries remain sagittally balanced.",
            actual={"eye_source_length_delta_mm": abs(eye_left_length-eye_right_length), "nostril_source_length_delta_mm": abs(nostril_left_length-nostril_right_length)},
            expected="both <= 1e-6 mm",
        ),
        BoundaryPreflightCheck(
            "BOUNDARY_EVIDENCE_BOUNDARY",
            "PASS" if topology.anatomical_validation_eligible is False and "NOT_SEAL_FIT_INGRESS_PRESSURE_OR_ANATOMICAL_VALIDATION" in topology.evidence_status else "FAIL",
            "Edge topology cannot satisfy seal, fit, ingress, pressure or anatomical validation gates.",
        ),
    ]
    result = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {"project":"Masck One","phase":2,"iteration":12,"result":result,"checks":[check.to_dict() for check in checks],"boundary_topology_sha256":topology.topology_sha256}


def main() -> int:
    report = run_boundary_preflight()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
