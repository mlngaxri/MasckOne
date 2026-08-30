from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from .boundary_release import build_verified_interface_boundary_topology
from .interface_attachment import build_interface_attachment_architecture
from .model import build_model
from .structural_frame import (
    DATUM_IDS,
    RESERVATION_IDS,
    build_structural_frame_topology,
)


@dataclass(frozen=True)
class StructuralFramePreflightCheck:
    id: str
    status: str
    message: str
    actual: object | None = None
    expected: object | None = None

    def to_dict(self) -> dict[str, object | None]:
        return asdict(self)


def run_structural_frame_preflight() -> dict[str, object]:
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)

    attachment_edge_indices = tuple(item.source_boundary_edge_index for item in attachment.assignments)
    frame_edge_indices = frame.perimeter_reaction_path.source_attachment_edge_indices
    datum_by_id = {datum.datum_id: datum for datum in frame.datums}
    fw, fh = frame.functional_frame_xy_mm
    reservation_by_id = {item.reservation_id: item for item in frame.reservations}

    checks = [
        StructuralFramePreflightCheck(
            "FRAME_SOURCE_CHAIN",
            "PASS" if (
                frame.source_attachment_topology_sha256 == attachment.topology_sha256
                and frame.source_registered_mesh_sha256 == attachment.source_registered_mesh_sha256
            ) else "FAIL",
            "Structural topology is bound to the exact verified Iteration-13 attachment and registered mesh.",
        ),
        StructuralFramePreflightCheck(
            "FRAME_PERIMETER_REACTION_PATH",
            "PASS" if frame_edge_indices == attachment_edge_indices else "FAIL",
            "The first structural reaction loop inherits every attachment perimeter edge exactly once.",
            actual={"frame_edge_count": len(frame_edge_indices), "attachment_edge_count": len(attachment_edge_indices)},
            expected="exact identity-preserving mapping",
        ),
        StructuralFramePreflightCheck(
            "FRAME_FUNCTIONAL_REFERENCE_AUTHORITY",
            "PASS" if (
                frame.functional_frame_xy_mm == model.authority.pair("geometry", "functional_frame_xy_mm")
                and frame.functional_frame_status == str(model.authority.get("geometry", "functional_frame_status"))
            ) else "FAIL",
            "Functional-frame XY reference and status are consumed directly from machine authority.",
            actual={"xy_mm": list(frame.functional_frame_xy_mm), "status": frame.functional_frame_status},
        ),
        StructuralFramePreflightCheck(
            "FRAME_DATUM_NETWORK",
            "PASS" if (
                tuple(datum.datum_id for datum in frame.datums) == DATUM_IDS
                and datum_by_id[DATUM_IDS[0]].x_mm == 0.0
                and datum_by_id[DATUM_IDS[0]].y_mm == 0.0
                and datum_by_id[DATUM_IDS[1]].y_mm == fh / 2.0
                and datum_by_id[DATUM_IDS[2]].y_mm == -fh / 2.0
                and datum_by_id[DATUM_IDS[3]].x_mm == -fw / 2.0
                and datum_by_id[DATUM_IDS[4]].x_mm == fw / 2.0
                and all(datum.manifest()["z_mm"] is None for datum in frame.datums)
            ) else "FAIL",
            "Frame XY datums are derived from the authority reference while unsupported 3D Z placement remains unresolved.",
            actual=[datum.manifest() for datum in frame.datums],
        ),
        StructuralFramePreflightCheck(
            "FRAME_RESERVATION_COMPLETENESS",
            "PASS" if tuple(item.reservation_id for item in frame.reservations) == RESERVATION_IDS else "FAIL",
            "Structural topology reserves interfaces for actuation, fresh fluid, waste, retention, HMI/electronics and thermal systems.",
            actual=[item.reservation_id for item in frame.reservations],
            expected=list(RESERVATION_IDS),
        ),
        StructuralFramePreflightCheck(
            "FRAME_ACTUATION_ARCHITECTURE_BINDING",
            "PASS" if reservation_by_id[RESERVATION_IDS[0]].interface_count == int(model.authority.number("actuation", "count")) else "FAIL",
            "Frame actuation reservation preserves the frozen four-zone architecture without inventing mount positions.",
            actual=reservation_by_id[RESERVATION_IDS[0]].interface_count,
            expected=int(model.authority.number("actuation", "count")),
        ),
        StructuralFramePreflightCheck(
            "FRAME_ANALYSIS_REQUIREMENT_CARRY_FORWARD",
            "PASS" if (
                frame.frame_deflection_p95_max_mm == float(model.authority.get("structure", "frame_deflection_p95_max_mm"))
                and frame.frame_deflection_status == str(model.authority.get("structure", "frame_deflection_status"))
                and frame.first_mode_preferred_min_hz == float(model.authority.get("structure", "frame_first_mode_preferred_min_hz"))
                and frame.first_mode_status == str(model.authority.get("structure", "frame_first_mode_status"))
            ) else "FAIL",
            "Deflection and first-mode requirements are carried with original statuses without fabricating analysis results.",
            actual={
                "deflection_p95_max_mm": frame.frame_deflection_p95_max_mm,
                "deflection_status": frame.frame_deflection_status,
                "first_mode_preferred_min_hz": frame.first_mode_preferred_min_hz,
                "first_mode_status": frame.first_mode_status,
            },
        ),
        StructuralFramePreflightCheck(
            "FRAME_DIMENSION_MATERIAL_DISCIPLINE",
            "PASS" if frame.cross_section_dimensions_mm is None and frame.material_selection is None else "FAIL",
            "No structural cross-section or material is invented before geometry/material evidence exists.",
            actual={
                "cross_section_dimensions_mm": frame.cross_section_dimensions_mm,
                "material_selection": frame.material_selection,
            },
            expected="both unresolved",
        ),
        StructuralFramePreflightCheck(
            "FRAME_EVIDENCE_BOUNDARY",
            "PASS" if (
                frame.physical_validation_eligible is False
                and "NOT_DEFLECTION_MODAL_LOAD_FATIGUE_FIT_OR_PHYSICAL_VALIDATION" in frame.evidence_status
            ) else "FAIL",
            "Digital structural topology does not close deflection, modal, load, fatigue, fit or physical-validation gates.",
            actual=frame.evidence_status,
        ),
    ]

    result = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {
        "project": "Masck One",
        "phase": 3,
        "iteration": 15,
        "result": result,
        "checks": [check.to_dict() for check in checks],
        "structural_frame_topology_sha256": frame.topology_sha256,
    }


def main() -> int:
    report = run_structural_frame_preflight()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
