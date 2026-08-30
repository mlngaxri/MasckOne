from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from .coverage import REGION_T_NOSE_PHILTRUM
from .model import build_model
from .nasal_subsystem import (
    ROLE_BRIDGE_DORSUM,
    ROLE_LOBE,
    ROLE_PHILTRUM,
    ROLE_SIDEWALL_LEFT,
    ROLE_SIDEWALL_RIGHT,
)


CAD_BREP_BOUND_TOLERANCE_MM = 2e-6


@dataclass(frozen=True)
class NasalPreflightCheck:
    id: str
    status: str
    message: str
    actual: object | None = None
    expected: object | None = None

    def to_dict(self) -> dict[str, object | None]:
        return asdict(self)


def run_nasal_preflight() -> dict[str, object]:
    model = build_model()
    a = model.authority
    coverage = model.coverage_mesh
    interface = model.compliant_interface_topology
    nasal = model.nasal_subsystem_topology
    roles = nasal.role_by_id
    role_areas = nasal.role_area_mm2

    central_targets = [
        triangle
        for triangle in coverage.triangles
        if triangle.region_id == REGION_T_NOSE_PHILTRUM and triangle.is_target
    ]
    central_ids = {triangle.triangle_index for triangle in central_targets}
    central_area = sum(triangle.area_mm2 for triangle in central_targets)
    interface_central_ids = {
        assignment.triangle_index
        for assignment in interface.contact_assignments
        if assignment.parameter_zone_id == "INTERFACE_T_ZONE_NOSE_PHILTRUM"
    }

    lobe = roles[ROLE_LOBE]
    unresolved_role_ids = (
        ROLE_BRIDGE_DORSUM,
        ROLE_SIDEWALL_LEFT,
        ROLE_SIDEWALL_RIGHT,
        ROLE_PHILTRUM,
    )
    cad_bb = model.nasal_interface.solid.val().BoundingBox()
    cad_zlen_mm = float(cad_bb.zlen)
    authored_lobe_thickness_mm = a.number("geometry", "nasal_lobe_membrane", "thickness_center_mm")
    coverage_by_id = {triangle.triangle_index: triangle for triangle in coverage.triangles}

    checks = [
        NasalPreflightCheck(
            "NASAL_SOURCE_CHAIN",
            "PASS" if (
                nasal.source_surface_id == coverage.source_surface_id
                and nasal.source_surface_sha256 == coverage.source_surface_sha256
                and nasal.source_coverage_sha256 == coverage.segmentation_sha256
                and nasal.source_interface_sha256 == interface.topology_sha256
            ) else "FAIL",
            "Nasal topology is bound to the exact surface, coverage and compliant-interface revisions it partitions.",
        ),
        NasalPreflightCheck(
            "NASAL_ASSIGNMENT_CLOSURE",
            "PASS" if nasal.triangle_indices == frozenset(central_ids) == frozenset(interface_central_ids) else "FAIL",
            "Every central nose/philtrum target triangle is assigned exactly once and agrees with the interface topology.",
            actual=len(nasal.assignments),
            expected=len(central_ids),
        ),
        NasalPreflightCheck(
            "NASAL_AREA_CONSERVATION",
            "PASS" if abs(nasal.total_target_area_mm2 - central_area) <= 1e-8 else "FAIL",
            "Nasal functional roles conserve the complete central T-zone target area.",
            actual=nasal.total_target_area_mm2,
            expected=central_area,
        ),
        NasalPreflightCheck(
            "NASAL_ROLE_POPULATION",
            "PASS" if all(role_areas[role_id] > 0.0 for role_id in role_areas) else "FAIL",
            "Bridge/dorsum, both sidewalls, lobe and philtrum roles are all represented on the current development mesh.",
            actual=role_areas,
            expected="all five role areas > 0",
        ),
        NasalPreflightCheck(
            "NASAL_SAGITTAL_BALANCE",
            "PASS" if abs(role_areas[ROLE_SIDEWALL_LEFT] - role_areas[ROLE_SIDEWALL_RIGHT]) <= 1e-6 else "FAIL",
            "Neutral development sidewall partition remains sagittally balanced.",
            actual=abs(role_areas[ROLE_SIDEWALL_LEFT] - role_areas[ROLE_SIDEWALL_RIGHT]),
            expected="<= 1e-6 mm2",
        ),
        NasalPreflightCheck(
            "NASAL_LOBE_THICKNESS_LOCALIZATION",
            "PASS" if (
                lobe.nominal_thickness_mm == authored_lobe_thickness_mm
                and lobe.thickness_doe_mm == tuple(float(value) for value in a.get("geometry", "nasal_lobe_membrane", "thickness_doe_mm"))
                and all(roles[role_id].nominal_thickness_mm is None for role_id in unresolved_role_ids)
                and all(roles[role_id].thickness_doe_mm == () for role_id in unresolved_role_ids)
            ) else "FAIL",
            "The authority 0.30 mm / 0.25-0.35 mm thickness family is localized to the nasal-lobe role only.",
            actual={
                "lobe_nominal_mm": lobe.nominal_thickness_mm,
                "lobe_doe_mm": list(lobe.thickness_doe_mm),
                "other_numeric_thicknesses": {
                    role_id: roles[role_id].nominal_thickness_mm for role_id in unresolved_role_ids
                },
            },
            expected={"lobe_nominal_mm": authored_lobe_thickness_mm, "lobe_doe_mm": [0.25, 0.30, 0.35], "other_numeric_thicknesses": None},
        ),
        NasalPreflightCheck(
            "NASAL_PROTECTED_OPENING_EXCLUSION",
            "PASS" if all(
                coverage_by_id[assignment.triangle_index].protected_zone_id is None
                for assignment in nasal.assignments
            ) else "FAIL",
            "No eye/mouth/nostril protected triangle can enter the dedicated nasal contact-role partition.",
        ),
        NasalPreflightCheck(
            "NASAL_LOBE_CAD_LOCALIZATION",
            "PASS" if (
                model.nasal_interface.name == "nasal_lobe_membrane_reference"
                and model.nasal_interface.status == "DEVELOPMENT_LOCAL_THICKNESS_REFERENCE"
                and abs(cad_zlen_mm - authored_lobe_thickness_mm) <= CAD_BREP_BOUND_TOLERANCE_MM
            ) else "FAIL",
            "Generated CAD is explicitly a local nasal-lobe development reference. The authored thickness is checked exactly in the role authority and the post-boolean B-rep bound is checked only against the controlled OpenCascade numerical tolerance, not a product/manufacturing tolerance.",
            actual={
                "name": model.nasal_interface.name,
                "status": model.nasal_interface.status,
                "authored_thickness_mm": authored_lobe_thickness_mm,
                "brep_zlen_mm": cad_zlen_mm,
                "brep_bound_error_mm": abs(cad_zlen_mm - authored_lobe_thickness_mm),
            },
            expected={
                "name": "nasal_lobe_membrane_reference",
                "status": "DEVELOPMENT_LOCAL_THICKNESS_REFERENCE",
                "authored_thickness_mm": authored_lobe_thickness_mm,
                "brep_bound_error_mm_max": CAD_BREP_BOUND_TOLERANCE_MM,
            },
        ),
        NasalPreflightCheck(
            "NASAL_EVIDENCE_BOUNDARY",
            "PASS" if nasal.anatomical_validation_eligible is False and "NOT_ANATOMICAL" in nasal.evidence_status else "FAIL",
            "Development nasal topology cannot be promoted to fit, pressure, airway or efficacy validation evidence.",
            actual={"anatomical_validation_eligible": nasal.anatomical_validation_eligible, "evidence_status": nasal.evidence_status},
            expected={"anatomical_validation_eligible": False},
        ),
    ]

    result = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {
        "project": "Masck One",
        "phase": 2,
        "iteration": 11,
        "result": result,
        "checks": [check.to_dict() for check in checks],
        "nasal_topology_sha256": nasal.topology_sha256,
    }


def main() -> int:
    report = run_nasal_preflight()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
