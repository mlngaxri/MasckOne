from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Iterable

from .authority import Authority
from .spatial import Point3


class SurfaceWorkflowError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SurfaceSample:
    sample_id: str
    point: Point3


@dataclass(frozen=True, slots=True)
class ReleasedSurfaceReference:
    surface_id: str
    sha256: str
    revision: str
    release_status: str

    def __post_init__(self) -> None:
        if not self.surface_id.strip() or not self.revision.strip():
            raise SurfaceWorkflowError("Released Class-A reference requires non-empty id and revision")
        if len(self.sha256) != 64 or any(c not in "0123456789abcdef" for c in self.sha256.lower()):
            raise SurfaceWorkflowError("Released Class-A reference requires a 64-character SHA-256")
        if self.release_status != "RELEASED_CLASS_A_REFERENCE":
            raise SurfaceWorkflowError("Class-A reference cannot be treated as released without explicit release status")


@dataclass(frozen=True, slots=True)
class SurfaceDeviationReport:
    paired_sample_count: int
    rms_deviation_mm: float
    maximum_deviation_mm: float
    rms_limit_mm: float
    maximum_limit_mm: float
    numeric_gate_passed: bool
    reference_release_eligible: bool
    product_validation_status: str


@dataclass(frozen=True, slots=True)
class ClassAReferenceWorkflow:
    rms_limit_mm: float
    maximum_limit_mm: float
    authority_status: str
    reference: ReleasedSurfaceReference | None
    evidence_status: str
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.rms_limit_mm <= 0 or self.maximum_limit_mm <= 0:
            raise SurfaceWorkflowError("Class-A deviation limits must be positive")
        if self.rms_limit_mm > self.maximum_limit_mm:
            raise SurfaceWorkflowError("RMS Class-A deviation limit cannot exceed the maximum-deviation limit")
        if self.physical_validation_eligible:
            raise SurfaceWorkflowError("Digital Class-A deviation workflow is not physical validation evidence")

    @staticmethod
    def _index(samples: Iterable[SurfaceSample], label: str) -> dict[str, SurfaceSample]:
        indexed: dict[str, SurfaceSample] = {}
        for sample in samples:
            if not sample.sample_id.strip():
                raise SurfaceWorkflowError(f"{label} sample IDs must be non-empty")
            if sample.sample_id in indexed:
                raise SurfaceWorkflowError(f"{label} sample IDs must be unique")
            indexed[sample.sample_id] = sample
        if not indexed:
            raise SurfaceWorkflowError(f"{label} sample set must be non-empty")
        return indexed

    def evaluate(self, engineering: Iterable[SurfaceSample], reference: Iterable[SurfaceSample]) -> SurfaceDeviationReport:
        engineering_by_id = self._index(engineering, "Engineering")
        reference_by_id = self._index(reference, "Reference")
        if engineering_by_id.keys() != reference_by_id.keys():
            raise SurfaceWorkflowError("Engineering and Class-A samples must have identical IDs")

        deviations: list[float] = []
        for sample_id in sorted(engineering_by_id):
            a = engineering_by_id[sample_id].point
            b = reference_by_id[sample_id].point
            values = (*a.as_tuple(), *b.as_tuple())
            if not all(math.isfinite(v) for v in values):
                raise SurfaceWorkflowError("Surface samples must contain finite coordinates")
            deviations.append(math.dist(a.as_tuple(), b.as_tuple()))

        rms = math.sqrt(sum(value * value for value in deviations) / len(deviations))
        maximum = max(deviations)
        numeric_pass = rms <= self.rms_limit_mm and maximum <= self.maximum_limit_mm
        released = self.reference is not None
        if numeric_pass and released:
            status = "CAD_CLOSURE_NUMERIC_PASS_AGAINST_RELEASED_REFERENCE"
        elif numeric_pass:
            status = "BLOCKED_RELEASE_REFERENCE_REQUIRED"
        else:
            status = "CAD_CLOSURE_NUMERIC_FAIL"
        return SurfaceDeviationReport(
            paired_sample_count=len(deviations),
            rms_deviation_mm=rms,
            maximum_deviation_mm=maximum,
            rms_limit_mm=self.rms_limit_mm,
            maximum_limit_mm=self.maximum_limit_mm,
            numeric_gate_passed=numeric_pass,
            reference_release_eligible=released,
            product_validation_status=status,
        )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_class_a_workflow(authority: Authority, reference: ReleasedSurfaceReference | None = None) -> ClassAReferenceWorkflow:
    return ClassAReferenceWorkflow(
        rms_limit_mm=authority.number("manufacturing", "a_surface", "rms_deviation_max_mm"),
        maximum_limit_mm=authority.number("manufacturing", "a_surface", "max_deviation_mm"),
        authority_status=str(authority.get("manufacturing", "a_surface", "status")),
        reference=reference,
        evidence_status="ITERATION16_DIGITAL_DEVIATION_GOVERNANCE_NOT_CLASS_A_AUTHORING_MANUFACTURING_OR_PHYSICAL_VALIDATION",
    )
