from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math

from .authority import Authority
from .interface_attachment import InterfaceAttachmentArchitecture


class ContactSimulationError(ValueError):
    """Raised when the Iteration-14 contact-simulation contract is violated."""


PRELOAD_CASES_N = (6.0, 9.0, 12.0, 15.0)
FRICTION_CASES = (0.20, 0.40, 0.60)
MESH_LEVELS = (
    "MESH_LEVEL_COARSE",
    "MESH_LEVEL_MEDIUM",
    "MESH_LEVEL_FINE",
)
HYPERELASTIC_MODEL_FAMILIES = (
    "YEOH",
    "OGDEN",
    "UNSELECTED_YEOH_OR_OGDEN",
)
PRESSURE_CONVERGENCE_RELATIVE_MAX = 0.05
PEAK_STRAIN_CONVERGENCE_RELATIVE_MAX = 0.03


@dataclass(frozen=True, slots=True)
class MaterialParameter:
    name: str
    value: float
    units: str
    source_reference: str

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.units.strip() or not self.source_reference.strip():
            raise ContactSimulationError("Material-parameter metadata must be explicit")
        value = float(self.value)
        if not math.isfinite(value):
            raise ContactSimulationError("Material-parameter value must be finite")
        object.__setattr__(self, "value", value)

    def manifest(self) -> dict[str, object]:
        return {
            "name": self.name,
            "value": self.value,
            "units": self.units,
            "source_reference": self.source_reference,
        }


@dataclass(frozen=True, slots=True)
class HyperelasticMaterialCard:
    card_id: str
    model_family: str
    parameters: tuple[MaterialParameter, ...]
    source_type: str
    source_reference: str | None
    source_sha256: str | None
    status: str
    evidence_eligible: bool

    def __post_init__(self) -> None:
        if not self.card_id.strip() or not self.source_type.strip() or not self.status.strip():
            raise ContactSimulationError("Material-card identity/status metadata must be explicit")
        if self.model_family not in HYPERELASTIC_MODEL_FAMILIES:
            raise ContactSimulationError(f"Unsupported hyperelastic model family {self.model_family!r}")
        if len({parameter.name for parameter in self.parameters}) != len(self.parameters):
            raise ContactSimulationError("Material-card parameter names must be unique")
        if self.evidence_eligible:
            if self.model_family == "UNSELECTED_YEOH_OR_OGDEN":
                raise ContactSimulationError("Evidence-eligible card requires a selected constitutive model family")
            if not self.parameters:
                raise ContactSimulationError("Evidence-eligible card requires sourced constitutive parameters")
            if not self.source_reference or not self.source_reference.strip():
                raise ContactSimulationError("Evidence-eligible material card requires source provenance")
            if not self.source_sha256:
                raise ContactSimulationError("Evidence-eligible material card requires a source SHA-256")
            digest = self.source_sha256.lower()
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ContactSimulationError("Material-card source hash must be SHA-256")
        else:
            if self.parameters:
                raise ContactSimulationError(
                    "Non-evidence-eligible placeholder material card cannot carry constitutive constants"
                )
            if self.source_sha256 is not None:
                raise ContactSimulationError("Placeholder material card cannot imply released source data")

    @property
    def card_sha256(self) -> str:
        payload = {
            "card_id": self.card_id,
            "model_family": self.model_family,
            "parameters": [parameter.manifest() for parameter in self.parameters],
            "source_type": self.source_type,
            "source_reference": self.source_reference,
            "source_sha256": self.source_sha256,
            "status": self.status,
            "evidence_eligible": self.evidence_eligible,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self) -> dict[str, object]:
        return {
            "card_id": self.card_id,
            "model_family": self.model_family,
            "parameters": [parameter.manifest() for parameter in self.parameters],
            "source_type": self.source_type,
            "source_reference": self.source_reference,
            "source_sha256": self.source_sha256,
            "status": self.status,
            "evidence_eligible": self.evidence_eligible,
            "card_sha256": self.card_sha256,
        }


def unresolved_material_card() -> HyperelasticMaterialCard:
    return HyperelasticMaterialCard(
        card_id="MASCK_ONE-MATERIAL-CARD-COMPLIANT-INTERFACE-UNRESOLVED",
        model_family="UNSELECTED_YEOH_OR_OGDEN",
        parameters=(),
        source_type="REQUIRED_COUPON_OR_DEFENSIBLE_SOURCE_DATA_NOT_YET_RELEASED",
        source_reference=None,
        source_sha256=None,
        status="BLOCKED_PENDING_EVIDENCE_ELIGIBLE_CONSTITUTIVE_DATA",
        evidence_eligible=False,
    )


@dataclass(frozen=True, slots=True)
class ContactSimulationCase:
    case_id: str
    preload_N: float
    friction_coefficient: float
    material_card_id: str
    solver_execution_status: str

    def __post_init__(self) -> None:
        if not self.case_id.strip() or not self.material_card_id.strip() or not self.solver_execution_status.strip():
            raise ContactSimulationError("Simulation-case metadata must be explicit")
        preload = float(self.preload_N)
        friction = float(self.friction_coefficient)
        if preload not in PRELOAD_CASES_N:
            raise ContactSimulationError("Preload case is outside the controlled Iteration-14 sensitivity set")
        if friction not in FRICTION_CASES:
            raise ContactSimulationError("Friction case is outside the controlled Iteration-14 sensitivity set")
        object.__setattr__(self, "preload_N", preload)
        object.__setattr__(self, "friction_coefficient", friction)

    def manifest(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "preload_N": self.preload_N,
            "friction_coefficient": self.friction_coefficient,
            "material_card_id": self.material_card_id,
            "solver_execution_status": self.solver_execution_status,
        }


@dataclass(frozen=True, slots=True)
class ContactSimulationResult:
    case_id: str
    mesh_level: str
    material_card_sha256: str
    bridge_p95_kPa: float
    cheek_p95_kPa: float
    membrane_p95_strain_percent: float
    membrane_local_max_strain_percent: float
    result_provenance: str
    synthetic_regression_fixture: bool
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if not self.case_id.strip() or not self.result_provenance.strip():
            raise ContactSimulationError("Simulation-result metadata must be explicit")
        if self.mesh_level not in MESH_LEVELS:
            raise ContactSimulationError(f"Unsupported mesh level {self.mesh_level!r}")
        digest = self.material_card_sha256.lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ContactSimulationError("Result material-card binding must be SHA-256")
        for field_name in (
            "bridge_p95_kPa",
            "cheek_p95_kPa",
            "membrane_p95_strain_percent",
            "membrane_local_max_strain_percent",
        ):
            value = float(getattr(self, field_name))
            if not math.isfinite(value) or value < 0.0:
                raise ContactSimulationError(f"{field_name} must be finite and non-negative")
            object.__setattr__(self, field_name, value)
        if self.physical_validation_eligible:
            raise ContactSimulationError(
                "Iteration-14 solver result cannot be promoted directly to physical-validation evidence"
            )
        if self.synthetic_regression_fixture and "SYNTHETIC" not in self.result_provenance.upper():
            raise ContactSimulationError("Synthetic regression result must state synthetic provenance")

    def manifest(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "mesh_level": self.mesh_level,
            "material_card_sha256": self.material_card_sha256,
            "bridge_p95_kPa": self.bridge_p95_kPa,
            "cheek_p95_kPa": self.cheek_p95_kPa,
            "membrane_p95_strain_percent": self.membrane_p95_strain_percent,
            "membrane_local_max_strain_percent": self.membrane_local_max_strain_percent,
            "result_provenance": self.result_provenance,
            "synthetic_regression_fixture": self.synthetic_regression_fixture,
            "physical_validation_eligible": self.physical_validation_eligible,
        }


@dataclass(frozen=True, slots=True)
class ConvergenceReport:
    case_id: str
    coarse_mesh_level: str
    fine_mesh_level: str
    bridge_p95_relative_change: float
    cheek_p95_relative_change: float
    pressure_p95_relative_change_max: float
    peak_strain_relative_change: float
    pressure_converged: bool
    peak_strain_converged: bool
    converged: bool
    status: str
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.physical_validation_eligible:
            raise ContactSimulationError("Numerical convergence is not physical-validation evidence")

    def manifest(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "coarse_mesh_level": self.coarse_mesh_level,
            "fine_mesh_level": self.fine_mesh_level,
            "bridge_p95_relative_change": self.bridge_p95_relative_change,
            "cheek_p95_relative_change": self.cheek_p95_relative_change,
            "pressure_p95_relative_change_max": self.pressure_p95_relative_change_max,
            "peak_strain_relative_change": self.peak_strain_relative_change,
            "pressure_converged": self.pressure_converged,
            "peak_strain_converged": self.peak_strain_converged,
            "converged": self.converged,
            "status": self.status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }


def _relative_change(previous: float, current: float) -> float:
    denominator = max(abs(current), 1e-12)
    return abs(current - previous) / denominator


def evaluate_mesh_convergence(
    coarse: ContactSimulationResult,
    fine: ContactSimulationResult,
) -> ConvergenceReport:
    if coarse.case_id != fine.case_id:
        raise ContactSimulationError("Convergence comparison requires results from the same case")
    if coarse.material_card_sha256 != fine.material_card_sha256:
        raise ContactSimulationError("Convergence comparison requires the same material-card revision")
    if coarse.mesh_level == fine.mesh_level:
        raise ContactSimulationError("Convergence comparison requires different mesh levels")

    bridge_change = _relative_change(coarse.bridge_p95_kPa, fine.bridge_p95_kPa)
    cheek_change = _relative_change(coarse.cheek_p95_kPa, fine.cheek_p95_kPa)
    pressure_change = max(bridge_change, cheek_change)
    peak_strain_change = _relative_change(
        coarse.membrane_local_max_strain_percent,
        fine.membrane_local_max_strain_percent,
    )
    pressure_converged = pressure_change < PRESSURE_CONVERGENCE_RELATIVE_MAX
    strain_converged = peak_strain_change < PEAK_STRAIN_CONVERGENCE_RELATIVE_MAX
    converged = pressure_converged and strain_converged
    return ConvergenceReport(
        case_id=coarse.case_id,
        coarse_mesh_level=coarse.mesh_level,
        fine_mesh_level=fine.mesh_level,
        bridge_p95_relative_change=bridge_change,
        cheek_p95_relative_change=cheek_change,
        pressure_p95_relative_change_max=pressure_change,
        peak_strain_relative_change=peak_strain_change,
        pressure_converged=pressure_converged,
        peak_strain_converged=strain_converged,
        converged=converged,
        status=(
            "NUMERICAL_CONVERGENCE_SCREEN_PASS_NOT_PHYSICAL_VALIDATION"
            if converged
            else "NUMERICAL_CONVERGENCE_SCREEN_FAIL_REFINEMENT_REQUIRED"
        ),
        physical_validation_eligible=False,
    )


@dataclass(frozen=True, slots=True)
class ContactSimulationFramework:
    source_attachment_topology_sha256: str
    source_registered_mesh_sha256: str
    material_card: HyperelasticMaterialCard
    preload_cases_N: tuple[float, ...]
    friction_cases: tuple[float, ...]
    mesh_levels: tuple[str, ...]
    cases: tuple[ContactSimulationCase, ...]
    pressure_limits_kPa: tuple[tuple[str, float], ...]
    membrane_strain_limits_percent: tuple[tuple[str, float], ...]
    pressure_convergence_relative_max: float
    peak_strain_convergence_relative_max: float
    framework_status: str
    solver_execution_ready: bool
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        for digest in (self.source_attachment_topology_sha256, self.source_registered_mesh_sha256):
            value = digest.lower()
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise ContactSimulationError("Simulation-framework source hashes must be SHA-256")
        if self.preload_cases_N != PRELOAD_CASES_N:
            raise ContactSimulationError("Preload sensitivity set must remain controlled")
        if self.friction_cases != FRICTION_CASES:
            raise ContactSimulationError("Friction sensitivity set must remain controlled")
        if self.mesh_levels != MESH_LEVELS:
            raise ContactSimulationError("Mesh-level identities must remain controlled")
        expected_case_count = len(PRELOAD_CASES_N) * len(FRICTION_CASES)
        if len(self.cases) != expected_case_count:
            raise ContactSimulationError("Simulation framework must contain the complete preload/friction matrix")
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ContactSimulationError("Simulation case IDs must be unique")
        if self.pressure_convergence_relative_max != PRESSURE_CONVERGENCE_RELATIVE_MAX:
            raise ContactSimulationError("Pressure convergence criterion changed unexpectedly")
        if self.peak_strain_convergence_relative_max != PEAK_STRAIN_CONVERGENCE_RELATIVE_MAX:
            raise ContactSimulationError("Peak-strain convergence criterion changed unexpectedly")
        if self.solver_execution_ready != self.material_card.evidence_eligible:
            raise ContactSimulationError("Solver readiness must follow material-card evidence eligibility")
        if self.physical_validation_eligible:
            raise ContactSimulationError("Simulation framework cannot be physical-validation evidence")
        if not self.framework_status.strip():
            raise ContactSimulationError("Simulation-framework status must be explicit")

    @property
    def framework_sha256(self) -> str:
        payload = self.manifest(include_sha=False)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "source_attachment_topology_sha256": self.source_attachment_topology_sha256,
            "source_registered_mesh_sha256": self.source_registered_mesh_sha256,
            "material_card": self.material_card.manifest(),
            "preload_cases_N": list(self.preload_cases_N),
            "friction_cases": list(self.friction_cases),
            "mesh_levels": list(self.mesh_levels),
            "cases": [case.manifest() for case in self.cases],
            "pressure_limits_kPa": {key: value for key, value in self.pressure_limits_kPa},
            "membrane_strain_limits_percent": {
                key: value for key, value in self.membrane_strain_limits_percent
            },
            "pressure_convergence_relative_max": self.pressure_convergence_relative_max,
            "peak_strain_convergence_relative_max": self.peak_strain_convergence_relative_max,
            "framework_status": self.framework_status,
            "solver_execution_ready": self.solver_execution_ready,
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["framework_sha256"] = self.framework_sha256
        return payload


def build_contact_simulation_framework(
    authority: Authority,
    attachment: InterfaceAttachmentArchitecture,
    material_card: HyperelasticMaterialCard | None = None,
) -> ContactSimulationFramework:
    """Create the solver-agnostic Iteration-14 contact-analysis contract.

    The default material card is intentionally unresolved. The framework therefore defines
    cases, evidence bindings, result fields and convergence rules without inventing silicone
    constitutive constants or claiming that solver execution is ready.
    """

    card = material_card or unresolved_material_card()
    cases = tuple(
        ContactSimulationCase(
            case_id=f"MASCK_ONE-CONTACT-P{int(preload):02d}-MU{int(round(friction * 100)):02d}",
            preload_N=preload,
            friction_coefficient=friction,
            material_card_id=card.card_id,
            solver_execution_status=(
                "READY_FOR_SOLVER_EXECUTION_WITH_EVIDENCE_ELIGIBLE_MATERIAL_CARD"
                if card.evidence_eligible
                else "BLOCKED_MATERIAL_CARD_REQUIRED"
            ),
        )
        for preload in PRELOAD_CASES_N
        for friction in FRICTION_CASES
    )

    pressure_limits = (
        ("bridge_p95_max_kPa", float(authority.get("safety", "pressure", "bridge_p95_max_kPa"))),
        ("bridge_steady_max_kPa", float(authority.get("safety", "pressure", "bridge_steady_max_kPa"))),
        ("cheek_p95_max_kPa", float(authority.get("safety", "pressure", "cheek_p95_max_kPa"))),
        ("dynamic_max_kPa", float(authority.get("safety", "pressure", "dynamic_max_kPa"))),
    )
    strain_limits = (
        (
            "p95_max_percent",
            float(authority.get("safety", "membrane_strain", "p95_max_percent")),
        ),
        (
            "local_max_percent",
            float(authority.get("safety", "membrane_strain", "local_max_percent")),
        ),
    )

    return ContactSimulationFramework(
        source_attachment_topology_sha256=attachment.topology_sha256,
        source_registered_mesh_sha256=attachment.source_registered_mesh_sha256,
        material_card=card,
        preload_cases_N=PRELOAD_CASES_N,
        friction_cases=FRICTION_CASES,
        mesh_levels=MESH_LEVELS,
        cases=cases,
        pressure_limits_kPa=pressure_limits,
        membrane_strain_limits_percent=strain_limits,
        pressure_convergence_relative_max=PRESSURE_CONVERGENCE_RELATIVE_MAX,
        peak_strain_convergence_relative_max=PEAK_STRAIN_CONVERGENCE_RELATIVE_MAX,
        framework_status=(
            "SOLVER_AGNOSTIC_CONTACT_FRAMEWORK_READY_MATERIAL_DEPENDENT_PREDICTION_BLOCKED"
            if not card.evidence_eligible
            else "SOLVER_AGNOSTIC_CONTACT_FRAMEWORK_READY_FOR_CONTROLLED_SOLVER_HANDOFF"
        ),
        solver_execution_ready=card.evidence_eligible,
        physical_validation_eligible=False,
    )
