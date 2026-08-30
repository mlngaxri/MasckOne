from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Mapping

from .actuation_sweep_contract import ActuationDisplacementContract
from .actuator_coupling import ActuatorCouplingArchitecture
from .actuator_frames import ActuatorFrameArchitecture
from .authority import Authority


class ActuationParameterError(ValueError):
    """Raised when Iteration-19 actuation parameter or test-handoff semantics are invalid."""


def _finite(value: object, *, label: str, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActuationParameterError(f"{label} must be a finite real number")
    out = float(value)
    if not math.isfinite(out) or (positive and out <= 0.0):
        raise ActuationParameterError(f"{label} must be {'positive ' if positive else ''}finite")
    return out


def _text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ActuationParameterError(f"{label} must be an exact nonblank string")
    return value


def _sha(value: object, *, label: str) -> str:
    text = _text(value, label=label)
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise ActuationParameterError(f"{label} must be a canonical lowercase SHA-256 digest")
    return text


@dataclass(frozen=True, slots=True)
class ActuationParameterSet:
    source_authority_revision: str
    source_actuator_architecture_sha256: str
    source_displacement_contract_sha256: str
    source_coupling_architecture_sha256: str
    clean_frequency_baseline_hz: float
    displacement_pp_baseline_mm: float
    axis_angle_baseline_deg: float
    axis_angle_doe_deg: tuple[float, ...]
    continuous_force_requirement_N: float
    transient_force_requirement_N: float
    frequency_sensitivity_points_hz: tuple[float, ...] | None
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        _text(self.source_authority_revision, label="authority revision")
        for label, digest in (
            ("actuator architecture identity", self.source_actuator_architecture_sha256),
            ("displacement contract identity", self.source_displacement_contract_sha256),
            ("coupling architecture identity", self.source_coupling_architecture_sha256),
        ):
            _sha(digest, label=label)
        frequency = _finite(self.clean_frequency_baseline_hz, label="CLEAN frequency", positive=True)
        displacement = _finite(self.displacement_pp_baseline_mm, label="peak-to-peak displacement", positive=True)
        baseline = _finite(self.axis_angle_baseline_deg, label="axis-angle baseline")
        doe = tuple(_finite(v, label="axis-angle DOE value") for v in self.axis_angle_doe_deg)
        if not doe or tuple(sorted(set(doe))) != doe or baseline not in doe:
            raise ActuationParameterError("Axis-angle DOE must be unique, ascending, and include the authority baseline")
        continuous = _finite(self.continuous_force_requirement_N, label="continuous force requirement", positive=True)
        transient = _finite(self.transient_force_requirement_N, label="transient force requirement", positive=True)
        if transient < continuous:
            raise ActuationParameterError("Transient force requirement cannot be below continuous force requirement")
        if self.frequency_sensitivity_points_hz is not None:
            raise ActuationParameterError("Frequency sensitivity points remain unresolved; Iteration 19 cannot invent a frequency DOE")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise ActuationParameterError("Digital actuation parameter definitions cannot be physical validation evidence")
        _text(self.evidence_status, label="evidence status")
        object.__setattr__(self, "clean_frequency_baseline_hz", frequency)
        object.__setattr__(self, "displacement_pp_baseline_mm", displacement)
        object.__setattr__(self, "axis_angle_baseline_deg", baseline)
        object.__setattr__(self, "axis_angle_doe_deg", doe)
        object.__setattr__(self, "continuous_force_requirement_N", continuous)
        object.__setattr__(self, "transient_force_requirement_N", transient)

    @property
    def parameter_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def validate_current_sources(
        self,
        *,
        authority: Authority,
        actuator_architecture: ActuatorFrameArchitecture,
        displacement_contract: ActuationDisplacementContract,
        coupling_architecture: ActuatorCouplingArchitecture,
    ) -> None:
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise ActuationParameterError("Actuation parameter set is stale for the current authority revision")
        if self.source_actuator_architecture_sha256 != actuator_architecture.architecture_sha256:
            raise ActuationParameterError("Actuation parameter set is stale for the actuator architecture")
        if self.source_displacement_contract_sha256 != displacement_contract.contract_sha256:
            raise ActuationParameterError("Actuation parameter set is stale for the displacement contract")
        if self.source_coupling_architecture_sha256 != coupling_architecture.architecture_sha256:
            raise ActuationParameterError("Actuation parameter set is stale for the coupling architecture")
        expected = {
            "clean_frequency_baseline_hz": float(authority.get("actuation", "clean", "frequency_baseline_hz")),
            "displacement_pp_baseline_mm": float(authority.get("actuation", "clean", "displacement_pp_baseline_mm")),
            "axis_angle_baseline_deg": float(authority.get("actuation", "clean", "axis_angle_baseline_deg")),
            "continuous_force_requirement_N": float(authority.get("actuation", "clean", "continuous_force_requirement_N")),
            "transient_force_requirement_N": float(authority.get("actuation", "clean", "transient_force_requirement_N")),
        }
        for field_name, expected_value in expected.items():
            if getattr(self, field_name) != expected_value:
                raise ActuationParameterError(f"{field_name} no longer matches machine authority")
        if self.axis_angle_doe_deg != tuple(float(v) for v in authority.get("actuation", "clean", "axis_angle_doe_deg")):
            raise ActuationParameterError("Axis-angle DOE no longer matches machine authority")

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "source_authority_revision": self.source_authority_revision,
            "source_actuator_architecture_sha256": self.source_actuator_architecture_sha256,
            "source_displacement_contract_sha256": self.source_displacement_contract_sha256,
            "source_coupling_architecture_sha256": self.source_coupling_architecture_sha256,
            "clean_frequency_baseline_hz": self.clean_frequency_baseline_hz,
            "frequency_sensitivity_points_hz": self.frequency_sensitivity_points_hz,
            "displacement_pp_baseline_mm": self.displacement_pp_baseline_mm,
            "axis_angle_baseline_deg": self.axis_angle_baseline_deg,
            "axis_angle_doe_deg": list(self.axis_angle_doe_deg),
            "continuous_force_requirement_N": self.continuous_force_requirement_N,
            "transient_force_requirement_N": self.transient_force_requirement_N,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["parameter_sha256"] = self.parameter_sha256
        return payload


@dataclass(frozen=True, slots=True)
class ImpedanceTestRecord:
    record_id: str
    source_parameter_sha256: str
    specimen_id: str
    source_kind: str
    frequency_hz: float
    commanded_displacement_pp_mm: float
    axis_angle_deg: float
    measured_force_N: float | None = None
    measured_displacement_pp_mm: float | None = None
    measured_phase_deg: float | None = None
    measured_temperature_C: float | None = None
    evidence_uri: str | None = None

    def __post_init__(self) -> None:
        _text(self.record_id, label="record ID")
        _sha(self.source_parameter_sha256, label="parameter identity")
        _text(self.specimen_id, label="specimen ID")
        if self.source_kind not in {"PREDICTED", "MEASURED"}:
            raise ActuationParameterError("Impedance record source_kind must be PREDICTED or MEASURED")
        _finite(self.frequency_hz, label="test frequency", positive=True)
        _finite(self.commanded_displacement_pp_mm, label="commanded peak-to-peak displacement", positive=True)
        _finite(self.axis_angle_deg, label="test axis angle")
        measured = (self.measured_force_N, self.measured_displacement_pp_mm, self.measured_phase_deg, self.measured_temperature_C)
        if self.source_kind == "PREDICTED":
            if any(value is not None for value in measured) or self.evidence_uri is not None:
                raise ActuationParameterError("Predicted impedance records cannot masquerade as measured evidence")
        else:
            if self.measured_force_N is None or self.measured_displacement_pp_mm is None or self.measured_phase_deg is None:
                raise ActuationParameterError("Measured impedance records require force, displacement and phase observations")
            _finite(self.measured_force_N, label="measured force", positive=True)
            _finite(self.measured_displacement_pp_mm, label="measured displacement", positive=True)
            _finite(self.measured_phase_deg, label="measured phase")
            if self.measured_temperature_C is not None:
                _finite(self.measured_temperature_C, label="measured temperature")
            if self.evidence_uri is None:
                raise ActuationParameterError("Measured impedance records require evidence provenance")
            _text(self.evidence_uri, label="evidence URI")

    def manifest(self) -> Mapping[str, object]:
        return {
            "record_id": self.record_id,
            "source_parameter_sha256": self.source_parameter_sha256,
            "specimen_id": self.specimen_id,
            "source_kind": self.source_kind,
            "frequency_hz": self.frequency_hz,
            "commanded_displacement_pp_mm": self.commanded_displacement_pp_mm,
            "axis_angle_deg": self.axis_angle_deg,
            "measured_force_N": self.measured_force_N,
            "measured_displacement_pp_mm": self.measured_displacement_pp_mm,
            "measured_phase_deg": self.measured_phase_deg,
            "measured_temperature_C": self.measured_temperature_C,
            "evidence_uri": self.evidence_uri,
        }


def build_actuation_parameter_set(
    authority: Authority,
    actuator_architecture: ActuatorFrameArchitecture,
    displacement_contract: ActuationDisplacementContract,
    coupling_architecture: ActuatorCouplingArchitecture,
) -> ActuationParameterSet:
    parameters = ActuationParameterSet(
        source_authority_revision=str(authority.get("project", "authority_revision")),
        source_actuator_architecture_sha256=actuator_architecture.architecture_sha256,
        source_displacement_contract_sha256=displacement_contract.contract_sha256,
        source_coupling_architecture_sha256=coupling_architecture.architecture_sha256,
        clean_frequency_baseline_hz=float(authority.get("actuation", "clean", "frequency_baseline_hz")),
        displacement_pp_baseline_mm=float(authority.get("actuation", "clean", "displacement_pp_baseline_mm")),
        axis_angle_baseline_deg=float(authority.get("actuation", "clean", "axis_angle_baseline_deg")),
        axis_angle_doe_deg=tuple(float(v) for v in authority.get("actuation", "clean", "axis_angle_doe_deg")),
        continuous_force_requirement_N=float(authority.get("actuation", "clean", "continuous_force_requirement_N")),
        transient_force_requirement_N=float(authority.get("actuation", "clean", "transient_force_requirement_N")),
        frequency_sensitivity_points_hz=None,
        physical_validation_eligible=False,
        evidence_status="AUTHORITY_BOUND_ACTUATION_PARAMETER_AND_IMPEDANCE_HANDOFF_ONLY_NOT_FORCE_IMPEDANCE_EFFICACY_OR_PHYSICAL_VALIDATION",
    )
    parameters.validate_current_sources(
        authority=authority,
        actuator_architecture=actuator_architecture,
        displacement_contract=displacement_contract,
        coupling_architecture=coupling_architecture,
    )
    return parameters
