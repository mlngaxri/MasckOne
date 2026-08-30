from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from .authority import load_authority
from .spatial import Point3
from .surface_workflow import (
    ReleasedSurfaceReference,
    SurfaceSample,
    SurfaceWorkflowError,
    build_class_a_workflow,
    sha256_bytes,
    surface_sample_manifest_sha256,
)


@dataclass(frozen=True)
class SurfaceWorkflowPreflightCheck:
    id: str
    status: str
    message: str
    actual: object | None = None
    expected: object | None = None

    def to_dict(self) -> dict[str, object | None]:
        return asdict(self)


def run_surface_workflow_preflight() -> dict[str, object]:
    authority = load_authority()
    workflow = build_class_a_workflow(authority)
    engineering = (
        SurfaceSample("P0", Point3(0.0, 0.0, 0.0)),
        SurfaceSample("P1", Point3(10.0, 0.0, 0.0)),
    )
    reference = (
        SurfaceSample("P0", Point3(0.0, 0.0, 0.10)),
        SurfaceSample("P1", Point3(10.0, 0.0, 0.10)),
    )
    report = workflow.evaluate(engineering, reference)

    manifest_sha = surface_sample_manifest_sha256(reference)
    released_reference = ReleasedSurfaceReference(
        surface_id="MASCK_ONE-CLASS-A-PREFLIGHT",
        source_asset_sha256=sha256_bytes(b"iteration16-controlled-synthetic-source-asset"),
        reference_sample_manifest_sha256=manifest_sha,
        revision="PREFLIGHT-R1",
        release_status="RELEASED_CLASS_A_REFERENCE",
    )
    released_report = build_class_a_workflow(authority, reference=released_reference).evaluate(engineering, reference)

    mismatch_rejected = False
    substituted_reference = (
        reference[0],
        SurfaceSample("P1", Point3(10.0, 0.0, 0.20)),
    )
    try:
        build_class_a_workflow(authority, reference=released_reference).evaluate(engineering, substituted_reference)
    except SurfaceWorkflowError as exc:
        mismatch_rejected = "manifest hash does not match" in str(exc)

    checks = [
        SurfaceWorkflowPreflightCheck(
            "CLASS_A_AUTHORITY_BINDING",
            "PASS" if (
                workflow.rms_limit_mm == authority.number("manufacturing", "a_surface", "rms_deviation_max_mm")
                and workflow.maximum_limit_mm == authority.number("manufacturing", "a_surface", "max_deviation_mm")
                and workflow.authority_status == str(authority.get("manufacturing", "a_surface", "status"))
            ) else "FAIL",
            "Class-A deviation criteria and status are consumed directly from machine authority.",
            actual={"rms_limit_mm": workflow.rms_limit_mm, "maximum_limit_mm": workflow.maximum_limit_mm, "status": workflow.authority_status},
        ),
        SurfaceWorkflowPreflightCheck(
            "CLASS_A_REFERENCE_RELEASE_GATE",
            "PASS" if (workflow.reference is None and report.product_validation_status == "BLOCKED_RELEASE_REFERENCE_REQUIRED") else "FAIL",
            "A numerical deviation pass cannot close CAD release until an authored, identified, hashed and explicitly released Class-A reference exists.",
            actual=report.product_validation_status,
        ),
        SurfaceWorkflowPreflightCheck(
            "CLASS_A_REFERENCE_SAMPLE_PROVENANCE",
            "PASS" if (
                released_report.reference_release_eligible
                and released_report.reference_sample_manifest_sha256 == manifest_sha
                and mismatch_rejected
            ) else "FAIL",
            "Release eligibility is bound to the exact canonical reference-sample manifest; substituted or stale sample geometry is rejected.",
            actual={
                "manifest_sha256": released_report.reference_sample_manifest_sha256,
                "substituted_reference_rejected": mismatch_rejected,
            },
        ),
        SurfaceWorkflowPreflightCheck(
            "CLASS_A_RELEASE_RECORD_PROVENANCE",
            "PASS" if (
                released_report.reference_surface_id == released_reference.surface_id
                and released_report.reference_revision == released_reference.revision
                and released_report.reference_source_asset_sha256 == released_reference.source_asset_sha256
                and released_report.reference_release_record_sha256 == released_reference.release_record_sha256
            ) else "FAIL",
            "Eligible reports preserve the released surface ID, revision, source-asset SHA-256 and complete release-record SHA-256, not only the derivative sample hash.",
            actual={
                "surface_id": released_report.reference_surface_id,
                "revision": released_report.reference_revision,
                "source_asset_sha256": released_report.reference_source_asset_sha256,
                "release_record_sha256": released_report.reference_release_record_sha256,
            },
        ),
        SurfaceWorkflowPreflightCheck(
            "CLASS_A_ENGINEERING_INPUT_TRACEABILITY",
            "PASS" if released_report.engineering_sample_manifest_sha256 == surface_sample_manifest_sha256(engineering) else "FAIL",
            "The report records the exact engineering sample-set identity as well as the released reference identity.",
            actual=released_report.engineering_sample_manifest_sha256,
        ),
        SurfaceWorkflowPreflightCheck(
            "CLASS_A_NUMERIC_EVALUATOR",
            "PASS" if (report.numeric_gate_passed and report.paired_sample_count == 2) else "FAIL",
            "Deterministic paired-sample RMS and maximum-deviation calculation operates on a controlled synthetic fixture.",
            actual={"paired_sample_count": report.paired_sample_count, "rms_mm": report.rms_deviation_mm, "max_mm": report.maximum_deviation_mm},
        ),
        SurfaceWorkflowPreflightCheck(
            "CLASS_A_EVIDENCE_BOUNDARY",
            "PASS" if (workflow.physical_validation_eligible is False and "NOT_CLASS_A_AUTHORING_MANUFACTURING_OR_PHYSICAL_VALIDATION" in workflow.evidence_status) else "FAIL",
            "The workflow cannot promote digital surface comparison into manufacturing or physical validation evidence.",
            actual=workflow.evidence_status,
        ),
    ]
    result = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {"project": "Masck One", "phase": 3, "iteration": 16, "result": result, "checks": [check.to_dict() for check in checks]}


def main() -> int:
    report = run_surface_workflow_preflight()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
