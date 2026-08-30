from __future__ import annotations

from dataclasses import dataclass
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
class SurfaceDeviationReport:
    paired_sample_count: int
    rms_deviation_mm: float
    maximum_deviation_mm: float
    rms_limit_mm: float
    maximum_limit_mm: float
    numeric_gate_passed: bool
    product_validation_status: str


@dataclass(frozen=True, slots=True)
class ClassAReferenceWorkflow:
    rms_limit_mm: float
    maximum_limit_mm: float
    reference_surface_id: str | None
    reference_surface_sha256: str | None
    release_status: str
    evidence_status: str

    def evaluate(
        self,
        engineering: Iterable[SurfaceSample],
        reference: Iterable[SurfaceSample],
    ) -> SurfaceDeviationReport:
        engineering_by_id = {sample.sample_id: sample for sample in engineering}
        reference_by_id = {sample.sample_id: sample for sample in reference}
        if not engineering_by_id or engineering_by_id.keys() != reference_by_id.keys():
            raise SurfaceWorkflowError("Engineering and Class-A samples must have identical non-empty IDs")
        deviations = []
        for sample_id in sorted(engineering_by_id):
            a = engineering_by_id[sample_id].point
            b = reference_by_id[sample_id].point
            deviations.append(math.dist(a.as_tuple(), b.as_tuple()))
        rms = math.sqrt(sum(value * value for value in deviations) / len(deviations))
        maximum = max(deviations)
        numeric_pass = rms <= self.rms_limit_mm and maximum <= self.maximum_limit_mm
        released = bool(self.reference_surface_id and self.reference_surface_sha256)
        return SurfaceDeviationReport(
            len(deviations), rms, maximum, self.rms_limit_mm, self.maximum_limit_mm,
            numeric_pass,
            "CAD_CLOSURE_NUMERIC_PASS" if numeric_pass and released else "BLOCKED_UNTIL_RELEASED_CLASS_A_REFERENCE",
        )


def build_class_a_workflow(authority: Authority) -> ClassAReferenceWorkflow:
    return ClassAReferenceWorkflow(
        rms_limit_mm=authority.number("manufacturing", "a_surface", "rms_deviation_max_mm"),
        maximum_limit_mm=authority.number("manufacturing", "a_surface", "max_deviation_mm"),
        reference_surface_id=None,
        reference_surface_sha256=None,
        release_status="REFERENCE_SURFACE_NOT_YET_AUTHORED_OR_RELEASED",
        evidence_status="ITERATION16_WORKFLOW_ONLY_NOT_CLASS_A_RELEASE_OR_MANUFACTURING_VALIDATION",
    )
