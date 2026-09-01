from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math

from .actuator_frames import ActuatorFrameArchitecture, ActuatorFrameError
from .authority import Authority
from .structural_frame import StructuralFrameTopology


class ActuationSweepContractError(ValueError):
    """Raised when actuator motion semantics are stale, ambiguous, or unsupported."""


def _canonical_sha256(value: object, *, label: str) -> str:
    if type(value) is not str or value != value.strip() or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ActuationSweepContractError(f"{label} must be an exact lowercase canonical SHA-256 digest")
    return value


def _canonical_text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ActuationSweepContractError(f"{label} must be an exact built-in nonblank canonical string")
    return value


def _finite_positive(value: object, *, label: str) -> float:
    if type(value) not in (int, float):
        raise ActuationSweepContractError(f"{label} must be a positive finite exact numeric scalar")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ActuationSweepContractError(f"{label} must be representable as a positive finite real number") from exc
    if not math.isfinite(result) or result <= 0.0:
        raise ActuationSweepContractError(f"{label} must be a positive finite real number")
    return result


@dataclass(frozen=True, slots=True)
class ActuationDisplacementContract:
    """Authority-bound symmetric displacement semantics, independent of unresolved placement geometry."""

    source_actuator_architecture_sha256: str
    source_authority_revision: str
    displacement_pp_mm: float
    displacement_peak_from_neutral_mm: float
    semantic: str
    physical_validation_eligible: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_actuator_architecture_sha256",
            _canonical_sha256(self.source_actuator_architecture_sha256, label="Actuator architecture identity"),
        )
        object.__setattr__(
            self,
            "source_authority_revision",
            _canonical_text(self.source_authority_revision, label="Authority revision"),
        )
        pp = _finite_positive(self.displacement_pp_mm, label="Peak-to-peak displacement")
        peak = _finite_positive(self.displacement_peak_from_neutral_mm, label="Peak displacement from neutral")
        if not math.isclose(peak * 2.0, pp, rel_tol=0.0, abs_tol=1e-12):
            raise ActuationSweepContractError("Peak displacement must equal exactly half the authority peak-to-peak displacement")
        if type(self.semantic) is not str or self.semantic != "SYMMETRIC_PEAK_TO_PEAK_ABOUT_NEUTRAL":
            raise ActuationSweepContractError("Actuator displacement semantic must explicitly preserve peak-to-peak authority meaning")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise ActuationSweepContractError("Digital displacement semantics cannot be promoted to physical validation evidence")
        object.__setattr__(self, "displacement_pp_mm", pp)
        object.__setattr__(self, "displacement_peak_from_neutral_mm", peak)

    def validate_invariants(self) -> None:
        """Revalidate all stored semantics without mutating the contract."""

        if _canonical_sha256(
            self.source_actuator_architecture_sha256,
            label="Actuator architecture identity",
        ) != self.source_actuator_architecture_sha256:
            raise ActuationSweepContractError("Actuator architecture identity is not canonical")
        if _canonical_text(self.source_authority_revision, label="Authority revision") != self.source_authority_revision:
            raise ActuationSweepContractError("Authority revision is not canonical")
        if type(self.displacement_pp_mm) is not float:
            raise ActuationSweepContractError("Stored peak-to-peak displacement must be canonical float")
        if type(self.displacement_peak_from_neutral_mm) is not float:
            raise ActuationSweepContractError("Stored peak displacement must be canonical float")
        pp = _finite_positive(self.displacement_pp_mm, label="Peak-to-peak displacement")
        peak = _finite_positive(self.displacement_peak_from_neutral_mm, label="Peak displacement from neutral")
        if not math.isclose(peak * 2.0, pp, rel_tol=0.0, abs_tol=1e-12):
            raise ActuationSweepContractError("Peak displacement must equal exactly half the authority peak-to-peak displacement")
        if type(self.semantic) is not str or self.semantic != "SYMMETRIC_PEAK_TO_PEAK_ABOUT_NEUTRAL":
            raise ActuationSweepContractError("Actuator displacement semantic must explicitly preserve peak-to-peak authority meaning")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise ActuationSweepContractError("Digital displacement semantics cannot be promoted to physical validation evidence")

    @property
    def neutral_relative_interval_mm(self) -> tuple[float, float]:
        self.validate_invariants()
        return (-self.displacement_peak_from_neutral_mm, self.displacement_peak_from_neutral_mm)

    @property
    def contract_sha256(self) -> str:
        self.validate_invariants()
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def validate_current_sources(self, *, authority: Authority, architecture: ActuatorFrameArchitecture) -> None:
        self.validate_invariants()
        current_revision = _canonical_text(authority.get("project", "authority_revision"), label="Current authority revision")
        if self.source_authority_revision != current_revision:
            raise ActuationSweepContractError("Displacement contract is stale for the current authority revision")
        if self.source_actuator_architecture_sha256 != architecture.architecture_sha256:
            raise ActuationSweepContractError("Displacement contract is stale for the current actuator-frame architecture")
        current_pp = _finite_positive(
            authority.get("actuation", "clean", "displacement_pp_baseline_mm"),
            label="Authority peak-to-peak displacement",
        )
        if self.displacement_pp_mm != current_pp:
            raise ActuationSweepContractError("Displacement contract no longer matches authority peak-to-peak displacement")

    def require_geometry_ready(
        self,
        *,
        authority: Authority,
        architecture: ActuatorFrameArchitecture,
        structural_frame: StructuralFrameTopology,
    ) -> None:
        """Prove motion semantics and the complete live structural provenance chain before geometry use."""
        self.validate_invariants()
        self.validate_current_sources(authority=authority, architecture=architecture)
        try:
            architecture.require_sweep_ready(structural_frame=structural_frame, authority=authority)
        except ActuatorFrameError as exc:
            raise ActuationSweepContractError(f"Actuator sweep geometry remains blocked: {exc}") from exc

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.validate_invariants()
        payload: dict[str, object] = {
            "source_actuator_architecture_sha256": self.source_actuator_architecture_sha256,
            "source_authority_revision": self.source_authority_revision,
            "displacement_pp_mm": self.displacement_pp_mm,
            "displacement_peak_from_neutral_mm": self.displacement_peak_from_neutral_mm,
            "neutral_relative_interval_mm": [
                -self.displacement_peak_from_neutral_mm,
                self.displacement_peak_from_neutral_mm,
            ],
            "semantic": self.semantic,
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["contract_sha256"] = self.contract_sha256
        return payload


def build_actuation_displacement_contract(authority: Authority, architecture: ActuatorFrameArchitecture) -> ActuationDisplacementContract:
    pp = _finite_positive(
        authority.get("actuation", "clean", "displacement_pp_baseline_mm"),
        label="Authority peak-to-peak displacement",
    )
    contract = ActuationDisplacementContract(
        source_actuator_architecture_sha256=architecture.architecture_sha256,
        source_authority_revision=_canonical_text(authority.get("project", "authority_revision"), label="Authority revision"),
        displacement_pp_mm=pp,
        displacement_peak_from_neutral_mm=pp / 2.0,
        semantic="SYMMETRIC_PEAK_TO_PEAK_ABOUT_NEUTRAL",
        physical_validation_eligible=False,
    )
    contract.validate_current_sources(authority=authority, architecture=architecture)
    return contract
