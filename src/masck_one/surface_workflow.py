from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Iterable, Mapping

from .authority import Authority
from .spatial import Point3


class SurfaceWorkflowError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SurfaceSample:
    sample_id: str
    point: Point3


def _index_samples(samples: Iterable[SurfaceSample], label: str) -> dict[str, SurfaceSample]:
    indexed: dict[str, SurfaceSample] = {}
    for sample in samples:
        if not sample.sample_id.strip():
            raise SurfaceWorkflowError(f"{label} sample IDs must be non-empty")
        if sample.sample_id in indexed:
            raise SurfaceWorkflowError(f"{label} sample IDs must be unique")
        if not all(math.isfinite(value) for value in sample.point.as_tuple()):
            raise SurfaceWorkflowError(f"{label} surface samples must contain finite coordinates")
        indexed[sample.sample_id] = sample
    if not indexed:
        raise SurfaceWorkflowError(f"{label} sample set must be non-empty")
    return indexed


def _sample_manifest_sha256(indexed: Mapping[str, SurfaceSample]) -> str:
    # Float.hex() is used deliberately so the manifest binds the exact binary
    # floating-point coordinates without locale or decimal-format ambiguity.
    payload = {
        "schema": "MASCK_ONE_SURFACE_SAMPLE_MANIFEST_V1",
        "coordinate_unit": "mm",
        "samples": [
            {
                "sample_id": sample_id,
                "point_mm_float_hex": [float(value).hex() for value in indexed[sample_id].point.as_tuple()],
            }
            for sample_id in sorted(indexed)
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def surface_sample_manifest_sha256(samples: Iterable[SurfaceSample]) -> str:
    """Return the deterministic identity of an exact released comparison sample set."""
    return _sample_manifest_sha256(_index_samples(samples, "Reference"))


@dataclass(frozen=True, slots=True)
class ReleasedSurfaceReference:
    surface_id: str
    source_asset_sha256: str
    reference_sample_manifest_sha256: str
    revision: str
    release_status: str

    def __post_init__(self) -> None:
        if not self.surface_id.strip() or not self.revision.strip():
            raise SurfaceWorkflowError("Released Class-A reference requires non-empty id and revision")
        for label, digest in (
            ("source asset", self.source_asset_sha256),
            ("reference sample manifest", self.reference_sample_manifest_sha256),
        ):
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
                raise SurfaceWorkflowError(f"Released Class-A reference {label} requires a 64-character SHA-256")
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
    reference_sample_manifest_sha256: str
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

    def evaluate(self, engineering: Iterable[SurfaceSample], reference: Iterable[SurfaceSample]) -> SurfaceDeviationReport:
        engineering_by_id = _index_samples(engineering, "Engineering")
        reference_by_id = _index_samples(reference, "Reference")
        if engineering_by_id.keys() != reference_by_id.keys():
            raise SurfaceWorkflowError("Engineering and Class-A samples must have identical IDs")

        reference_manifest_sha256 = _sample_manifest_sha256(reference_by_id)
        if (
            self.reference is not None
            and reference_manifest_sha256.lower() != self.reference.reference_sample_manifest_sha256.lower()
        ):
            raise SurfaceWorkflowError(
                "Released Class-A reference sample manifest hash does not match supplied reference samples"
            )

        deviations: list[float] = []
        for sample_id in sorted(engineering_by_id):
            a = engineering_by_id[sample_id].point
            b = reference_by_id[sample_id].point
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
            reference_sample_manifest_sha256=reference_manifest_sha256,
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
