from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from .boundary_release import build_verified_interface_boundary_topology
from .contact_simulation import (
    FRICTION_CASES,
    MESH_LEVELS,
    PEAK_STRAIN_CONVERGENCE_RELATIVE_MAX,
    PRELOAD_CASES_N,
    PRESSURE_CONVERGENCE_RELATIVE_MAX,
    build_contact_simulation_framework,
)
from .interface_attachment import build_interface_attachment_architecture
from .model import build_model


@dataclass(frozen=True)
class ContactSimulationPreflightCheck:
    id: str
    status: str
    message: str
    actual: object | None = None
    expected: object | None = None

    def to_dict(self) -> dict[str, object | None]:
        return asdict(self)


def run_contact_simulation_preflight() -> dict[str, object]:
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    framework = build_contact_simulation_framework(model.authority, attachment)

    case_pairs = tuple((case.preload_N, case.friction_coefficient) for case in framework.cases)
    expected_pairs = tuple(
        (preload, friction)
        for preload in PRELOAD_CASES_N
        for friction in FRICTION_CASES
    )
    pressure_limits = dict(framework.pressure_limits_kPa)
    strain_limits = dict(framework.membrane_strain_limits_percent)

    checks = [
        ContactSimulationPreflightCheck(
            "CONTACT_FRAMEWORK_SOURCE_CHAIN",
            "PASS" if (
                framework.source_attachment_topology_sha256 == attachment.topology_sha256
                and framework.source_registered_mesh_sha256 == attachment.source_registered_mesh_sha256
            ) else "FAIL",
            "Contact framework is bound to the exact Iteration-13 attachment and registered-mesh revision.",
        ),
        ContactSimulationPreflightCheck(
            "CONTACT_CASE_MATRIX",
            "PASS" if case_pairs == expected_pairs else "FAIL",
            "All controlled preload/friction sensitivity cases exist exactly once.",
            actual={"case_count": len(case_pairs), "pairs": [list(pair) for pair in case_pairs]},
            expected={"case_count": len(expected_pairs), "pairs": [list(pair) for pair in expected_pairs]},
        ),
        ContactSimulationPreflightCheck(
            "CONTACT_MESH_LEVEL_IDENTITIES",
            "PASS" if framework.mesh_levels == MESH_LEVELS else "FAIL",
            "Mesh refinement levels are explicit without inventing unsupported element sizes.",
            actual=list(framework.mesh_levels),
            expected=list(MESH_LEVELS),
        ),
        ContactSimulationPreflightCheck(
            "CONTACT_MATERIAL_EVIDENCE_GATE",
            "PASS" if (
                framework.material_card.evidence_eligible is False
                and framework.material_card.parameters == ()
                and framework.solver_execution_ready is False
                and all(case.solver_execution_status == "BLOCKED_MATERIAL_CARD_REQUIRED" for case in framework.cases)
            ) else "FAIL",
            "No constitutive constants are fabricated; material-dependent solver execution remains blocked.",
            actual=framework.material_card.manifest(),
            expected="unresolved evidence-gated material card with zero numeric parameters",
        ),
        ContactSimulationPreflightCheck(
            "CONTACT_PRESSURE_LIMITS_AUTHORITY",
            "PASS" if pressure_limits == {
                "bridge_p95_max_kPa": float(model.authority.get("safety", "pressure", "bridge_p95_max_kPa")),
                "bridge_steady_max_kPa": float(model.authority.get("safety", "pressure", "bridge_steady_max_kPa")),
                "cheek_p95_max_kPa": float(model.authority.get("safety", "pressure", "cheek_p95_max_kPa")),
                "dynamic_max_kPa": float(model.authority.get("safety", "pressure", "dynamic_max_kPa")),
            } else "FAIL",
            "Pressure result fields carry the exact validation-gated authority limits without claiming a pass.",
            actual=pressure_limits,
        ),
        ContactSimulationPreflightCheck(
            "CONTACT_STRAIN_LIMITS_AUTHORITY",
            "PASS" if strain_limits == {
                "p95_max_percent": float(model.authority.get("safety", "membrane_strain", "p95_max_percent")),
                "local_max_percent": float(model.authority.get("safety", "membrane_strain", "local_max_percent")),
            } else "FAIL",
            "Membrane result fields carry the exact validation-gated authority strain limits without claiming a pass.",
            actual=strain_limits,
        ),
        ContactSimulationPreflightCheck(
            "CONTACT_NUMERICAL_CONVERGENCE_CRITERIA",
            "PASS" if (
                framework.pressure_convergence_relative_max == PRESSURE_CONVERGENCE_RELATIVE_MAX
                and framework.peak_strain_convergence_relative_max == PEAK_STRAIN_CONVERGENCE_RELATIVE_MAX
            ) else "FAIL",
            "Numerical convergence uses the controlled <5% p95-pressure and <3% peak-strain refinement criteria.",
            actual={
                "pressure_relative_max": framework.pressure_convergence_relative_max,
                "peak_strain_relative_max": framework.peak_strain_convergence_relative_max,
            },
        ),
        ContactSimulationPreflightCheck(
            "CONTACT_EVIDENCE_BOUNDARY",
            "PASS" if (
                framework.physical_validation_eligible is False
                and "MATERIAL_DEPENDENT_PREDICTION_BLOCKED" in framework.framework_status
            ) else "FAIL",
            "Framework readiness cannot be promoted to pressure, strain, fit, comfort or physical-validation evidence.",
            actual=framework.framework_status,
        ),
    ]

    result = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {
        "project": "Masck One",
        "phase": 2,
        "iteration": 14,
        "result": result,
        "checks": [check.to_dict() for check in checks],
        "contact_framework_sha256": framework.framework_sha256,
    }


def main() -> int:
    report = run_contact_simulation_preflight()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
