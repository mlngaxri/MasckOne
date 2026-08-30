from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.metadata
import json
from pathlib import Path
import re
import sys
from typing import Iterable

from .anatomy import FacialReferenceError, build_facial_reference
from .authority import Authority, AuthorityError, load_authority
from .coverage import CoverageError, build_facial_coverage_mesh
from .facial_surface import FacialSurfaceError, build_planar_development_surface
from .interface_topology import (
    InterfaceTopologyError,
    ZONE_T_NOSE_PHILTRUM,
    build_compliant_interface_topology,
)
from .protected_volumes import ProtectedVolumeError, build_protected_volumes
from .reference_surfaces import (
    ReferenceSurfaceAsset,
    ReferenceSurfaceError,
    SurfaceProvenance,
    TriangleMesh,
    identity_registration,
)
from .spatial import CanonicalDatums, Point3, SpatialContractError
from .worn_pose import WornPoseError, generate_hard_envelope_regression_set, protected_zone_regression_bounds


REQUIRED_PYTHON = (3, 13)
EXPECTED_DISTRIBUTIONS = {
    "cadquery": "2.8.0",
    "jsonschema": "4.26.0",
    "PyYAML": "6.0.3",
}
LEGACY_PRODUCT_TOKEN = "F" + "CW"


@dataclass(frozen=True)
class PreflightCheck:
    id: str
    status: str
    message: str
    actual: object | None = None
    expected: object | None = None

    def to_dict(self) -> dict[str, object | None]:
        return asdict(self)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _check_python() -> PreflightCheck:
    actual = [sys.version_info.major, sys.version_info.minor]
    return PreflightCheck(
        "PYTHON_VERSION",
        "PASS" if tuple(actual) == REQUIRED_PYTHON else "FAIL",
        "Runtime uses the repository's controlled Python major/minor version.",
        actual,
        list(REQUIRED_PYTHON),
    )


def _check_dependencies() -> list[PreflightCheck]:
    checks: list[PreflightCheck] = []
    for distribution, expected in EXPECTED_DISTRIBUTIONS.items():
        try:
            actual = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        checks.append(
            PreflightCheck(
                f"DEPENDENCY_{re.sub(r'[^A-Za-z0-9]+', '_', distribution).upper()}",
                "PASS" if actual == expected else "FAIL",
                "Runtime dependency matches the controlled repository version.",
                actual,
                expected,
            )
        )
    return checks


def _check_authority() -> tuple[list[PreflightCheck], Authority | None]:
    try:
        authority = load_authority()
    except AuthorityError as exc:
        return [PreflightCheck("AUTHORITY_LOAD", "FAIL", "Machine authority must load without schema or semantic errors.", str(exc), "valid authority")], None

    checks = [
        PreflightCheck("AUTHORITY_LOAD", "PASS", "Machine authority loads successfully."),
        PreflightCheck(
            "AUTHORITY_CONTRACT",
            "PASS" if authority.validation_report.valid else "FAIL",
            "Authority passes strict schema and deterministic semantic validation.",
            len(authority.validation_report.issues),
            0,
        ),
        PreflightCheck(
            "PRODUCT_NAME",
            "PASS" if authority.get("project", "name") == "Masck One" else "FAIL",
            "Human-facing product name is exactly Masck One.",
            authority.get("project", "name"),
            "Masck One",
        ),
        PreflightCheck(
            "PROJECT_ID",
            "PASS" if authority.get("project", "id") == "MASCK_ONE" else "FAIL",
            "Machine project identifier is stable.",
            authority.get("project", "id"),
            "MASCK_ONE",
        ),
        PreflightCheck(
            "AUTHORITY_SCHEMA_VERSION",
            "PASS" if authority.get("project", "schema_version") == "1.0.0" else "FAIL",
            "Authority schema version is explicit and controlled.",
            authority.get("project", "schema_version"),
            "1.0.0",
        ),
    ]
    return checks, authority


def _build_datums(authority: Authority | None) -> tuple[PreflightCheck, CanonicalDatums | None]:
    if authority is None:
        return PreflightCheck("SPATIAL_CONTRACT", "FAIL", "Canonical spatial datums require valid authority.", None, "valid canonical datums"), None
    try:
        datums = CanonicalDatums.from_authority(authority)
    except SpatialContractError as exc:
        return PreflightCheck("SPATIAL_CONTRACT", "FAIL", "Canonical datums must be finite, orthonormal, right-handed and authority-aligned.", str(exc), "valid canonical datums"), None

    actual = {
        "origin": datums.global_frame.origin.as_tuple(),
        "x_axis": datums.global_frame.x_axis.as_tuple(),
        "y_axis": datums.global_frame.y_axis.as_tuple(),
        "z_axis": datums.global_frame.z_axis.as_tuple(),
        "planes": [datums.sagittal_plane.name, datums.transverse_plane.name, datums.coronal_plane.name],
    }
    expected = {
        "origin": (0.0, 0.0, 0.0),
        "x_axis": (1.0, 0.0, 0.0),
        "y_axis": (0.0, 1.0, 0.0),
        "z_axis": (0.0, 0.0, 1.0),
        "planes": ["MASCK_ONE_SAGITTAL_X0", "MASCK_ONE_TRANSVERSE_Y0", "MASCK_ONE_CORONAL_Z0"],
    }
    return PreflightCheck("SPATIAL_CONTRACT", "PASS" if actual == expected else "FAIL", "Canonical origin, axes and principal datum planes match the frozen convention.", actual, expected), datums


def _check_facial_reference(authority: Authority | None, datums: CanonicalDatums | None) -> PreflightCheck:
    if authority is None or datums is None:
        return PreflightCheck("FACIAL_REFERENCE_CONTRACT", "FAIL", "Facial reference requires valid authority and datums.")
    try:
        reference = build_facial_reference(authority, datums)
    except FacialReferenceError as exc:
        return PreflightCheck("FACIAL_REFERENCE_CONTRACT", "FAIL", "Facial reference must preserve authority landmarks without invented depth.", str(exc), "valid neutral reference")
    actual = {
        "count": len(reference.landmarks),
        "unresolved_3d_count": len(reference.unresolved_3d_landmarks()),
        "eye_spacing_mm": reference.metrics.interpupillary_center_spacing_mm,
        "nostril_spacing_mm": reference.metrics.nostril_center_spacing_mm,
        "eye_to_mouth_vertical_mm": reference.metrics.eye_to_mouth_center_vertical_mm,
    }
    expected = {"count": 5, "unresolved_3d_count": 5, "eye_spacing_mm": 63.0, "nostril_spacing_mm": 21.0, "eye_to_mouth_vertical_mm": 85.0}
    return PreflightCheck("FACIAL_REFERENCE_CONTRACT", "PASS" if actual == expected else "FAIL", "Authority-derived neutral landmark layer is deterministic.", actual, expected)


def _check_reference_surface_ingestion() -> PreflightCheck:
    try:
        mesh = TriangleMesh(
            vertices=(Point3(0.0, 0.0, 0.0), Point3(1.0, 0.0, 0.0), Point3(0.0, 1.0, 0.0)),
            triangles=((0, 1, 2),),
        )
        provenance = SurfaceProvenance(
            asset_id="PREFLIGHT-SYNTHETIC-TRIANGLE",
            source_kind="SYNTHETIC_TEST_FIXTURE",
            source_label="preflight unit triangle",
            source_revision="v1",
            source_units="cm",
            handedness="right",
            x_positive="explicit test +X",
            y_positive="explicit test +Y",
            z_positive="explicit test +Z",
            source_sha256=mesh.normalized_sha256(),
            evidence_status="SYNTHETIC_TEST_ONLY",
        )
        asset = ReferenceSurfaceAsset(provenance, mesh, identity_registration())
        registered = asset.registered_mesh
        manifest = asset.registration_manifest()
        edge_mm = registered.vertices[0].vector_to(registered.vertices[1]).norm()
    except (ReferenceSurfaceError, SpatialContractError) as exc:
        return PreflightCheck("REFERENCE_SURFACE_INGESTION", "FAIL", "Reference surfaces must preserve provenance, units, handedness and rigid registration.", str(exc), "valid ingestion contract")
    actual = {"edge_mm": edge_mm, "source_units": manifest["source_units"], "scale_to_mm": manifest["source_scale_to_mm"], "handedness": manifest["source_handedness"]}
    expected = {"edge_mm": 10.0, "source_units": "cm", "scale_to_mm": 10.0, "handedness": "right"}
    return PreflightCheck("REFERENCE_SURFACE_INGESTION", "PASS" if actual == expected else "FAIL", "Reference-surface ingestion produces deterministic Masck One-global geometry.", actual, expected)


def _check_neutral_facial_surface(authority: Authority | None, datums: CanonicalDatums | None) -> PreflightCheck:
    if authority is None or datums is None:
        return PreflightCheck("NEUTRAL_FACIAL_SURFACE", "FAIL", "Neutral facial surface requires valid authority and datums.")
    try:
        reference = build_facial_reference(authority, datums)
        surface = build_planar_development_surface(authority)
        projections = surface.project_reference_landmarks(reference)
    except (FacialSurfaceError, FacialReferenceError) as exc:
        return PreflightCheck("NEUTRAL_FACIAL_SURFACE", "FAIL", "Development facial surface must be deterministic and explicitly non-anatomical.", str(exc), "valid topology-only surface")
    actual = {
        "kind": surface.descriptor.kind,
        "validation_eligible": surface.descriptor.anatomical_validation_eligible,
        "planar": surface.is_planar,
        "vertex_count_gt_1000": surface.mesh.vertex_count > 1000,
        "triangle_count_gt_1500": surface.mesh.triangle_count > 1500,
        "projection_count": len(projections),
        "max_projection_error_lt_3_mm": max(p.xy_error_mm for p in projections) < 3.0,
    }
    expected = {"kind": "PLANAR_DEVELOPMENT_REFERENCE", "validation_eligible": False, "planar": True, "vertex_count_gt_1000": True, "triangle_count_gt_1500": True, "projection_count": 5, "max_projection_error_lt_3_mm": True}
    return PreflightCheck("NEUTRAL_FACIAL_SURFACE", "PASS" if actual == expected else "FAIL", "Neutral topology surface exists without being promoted to anatomical evidence.", actual, expected)


def _check_protected_volumes(authority: Authority | None, datums: CanonicalDatums | None) -> PreflightCheck:
    if authority is None or datums is None:
        return PreflightCheck("PROTECTED_VOLUME_CONTRACT", "FAIL", "Protected volumes require valid authority and datums.")
    try:
        reference = build_facial_reference(authority, datums)
        surface = build_planar_development_surface(authority)
        protected = build_protected_volumes(authority, reference, surface)
    except (FacialReferenceError, FacialSurfaceError, ProtectedVolumeError) as exc:
        return PreflightCheck("PROTECTED_VOLUME_CONTRACT", "FAIL", "Eye, mouth and airway keep-outs must preserve authority clearances and unresolved 3D status.", str(exc), "valid protected-volume set")
    actual = {
        "count": len(protected.all),
        "clearances": {volume.zone.zone_id: volume.zone.required_rigid_clearance_mm for volume in protected.all},
        "z_policy": sorted({volume.z_policy for volume in protected.all}),
        "any_validation_eligible": any(volume.anatomical_validation_eligible for volume in protected.all),
    }
    expected = {
        "count": 5,
        "clearances": {
            "MASCK_ONE-PROTECTED-EYE-LEFT": 8.5,
            "MASCK_ONE-PROTECTED-EYE-RIGHT": 8.5,
            "MASCK_ONE-PROTECTED-MOUTH": 9.5,
            "MASCK_ONE-PROTECTED-NOSTRIL-LEFT": 7.5,
            "MASCK_ONE-PROTECTED-NOSTRIL-RIGHT": 7.5,
        },
        "z_policy": ["UNBOUNDED_UNTIL_REGISTERED_ANATOMICAL_SURFACE"],
        "any_validation_eligible": False,
    }
    return PreflightCheck("PROTECTED_VOLUME_CONTRACT", "PASS" if actual == expected else "FAIL", "Conservative protected footprints remain deterministic while 3D anatomy stays evidence-gated.", actual, expected)


def _check_worn_pose(authority: Authority | None, datums: CanonicalDatums | None) -> PreflightCheck:
    if authority is None or datums is None:
        return PreflightCheck("WORN_POSE_CONTRACT", "FAIL", "Worn-pose regression requires valid authority and datums.")
    try:
        reference = build_facial_reference(authority, datums)
        surface = build_planar_development_surface(authority)
        protected = build_protected_volumes(authority, reference, surface)
        regression = generate_hard_envelope_regression_set(authority)
        posed_bounds = protected_zone_regression_bounds(protected, regression, boundary_samples=16)
    except (FacialReferenceError, FacialSurfaceError, ProtectedVolumeError, WornPoseError) as exc:
        return PreflightCheck("WORN_POSE_CONTRACT", "FAIL", "Deterministic authority-bounded worn poses must build and transform protected zones without inventing Z translation.", str(exc), "valid 459-state regression")

    manifest = regression.manifest()
    actual = {
        "pose_count": regression.pose_count,
        "radial_direction_count": regression.radial_direction_count,
        "translation_radial_max_mm": manifest["translation_radial_max_mm"],
        "rotation_max_deg": manifest["rotation_max_deg"],
        "translation_z_mm": manifest["translation_z_mm"],
        "z_translation_status": manifest["z_translation_status"],
        "identity_present": regression.identity_pose_index >= 0,
        "sha256_length": len(regression.sha256),
        "posed_bound_count": len(posed_bounds),
        "evidence_status": regression.evidence_status,
    }
    expected = {
        "pose_count": 459,
        "radial_direction_count": 16,
        "translation_radial_max_mm": 5.0,
        "rotation_max_deg": 4.0,
        "translation_z_mm": 0.0,
        "z_translation_status": "NOT_DEFINED_BY_CURRENT_AUTHORITY_FIXED_ZERO",
        "identity_present": True,
        "sha256_length": 64,
        "posed_bound_count": 459 * 5,
        "evidence_status": "DETERMINISTIC_DISCRETE_SCREEN_NOT_MEASURED_DONNING_DISTRIBUTION",
    }
    return PreflightCheck("WORN_POSE_CONTRACT", "PASS" if actual == expected else "FAIL", "Worn-pose limits, deterministic boundary sampling, protected-zone transforms and evidence status are explicit.", actual, expected)


def _build_coverage(authority: Authority, datums: CanonicalDatums):
    reference = build_facial_reference(authority, datums)
    surface = build_planar_development_surface(authority)
    protected = build_protected_volumes(authority, reference, surface)
    coverage = build_facial_coverage_mesh(authority, reference, surface, protected)
    return reference, surface, protected, coverage


def _check_coverage_mesh(authority: Authority | None, datums: CanonicalDatums | None) -> PreflightCheck:
    if authority is None or datums is None:
        return PreflightCheck("COVERAGE_MESH_CONTRACT", "FAIL", "Coverage mesh requires valid authority and datums.")
    try:
        _, surface, _, coverage = _build_coverage(authority, datums)
        all_target_ids = [triangle.triangle_index for triangle in coverage.target_triangles]
        synthetic_full = coverage.evaluate(
            all_target_ids,
            evidence_status="PREFLIGHT_SYNTHETIC_ALL_TARGETS",
            evidence_eligible=True,
        )
    except (FacialReferenceError, FacialSurfaceError, ProtectedVolumeError, CoverageError) as exc:
        return PreflightCheck("COVERAGE_MESH_CONTRACT", "FAIL", "Facial target/protected/T-zone segmentation and coverage metrics must build deterministically without being promoted to efficacy evidence.", str(exc), "valid deterministic coverage topology")

    actual = {
        "triangle_count_matches_surface": len(coverage.triangles) == surface.mesh.triangle_count,
        "target_area_positive": coverage.target_area_mm2 > 0.0,
        "protected_area_positive": coverage.protected_area_mm2 > 0.0,
        "t_zone_area_positive": coverage.t_zone_target_area_mm2 > 0.0,
        "philtrum_area_positive": coverage.philtrum_target_area_mm2 > 0.0,
        "area_conservation_error_lt_1e_8": coverage.area_conservation_error_mm2 < 1e-8,
        "aggregate_min_percent": coverage.aggregate_min_percent,
        "t_zone_min_percent": coverage.t_zone_min_percent,
        "unexplained_hole_max_mm2": coverage.unexplained_hole_max_mm2,
        "segmentation_sha256_length": len(coverage.segmentation_sha256),
        "anatomical_validation_eligible": coverage.anatomical_validation_eligible,
        "synthetic_full_numeric_pass": synthetic_full.numeric_gate_passed,
        "synthetic_full_aggregate_percent": synthetic_full.aggregate_percent,
        "synthetic_full_t_zone_percent": synthetic_full.t_zone_percent,
        "synthetic_full_largest_hole_mm2": synthetic_full.largest_uncovered_hole_mm2,
        "synthetic_full_product_status": synthetic_full.product_validation_status,
        "t_zone_development_status": coverage.t_zone_definition.evidence_status,
    }
    expected = {
        "triangle_count_matches_surface": True,
        "target_area_positive": True,
        "protected_area_positive": True,
        "t_zone_area_positive": True,
        "philtrum_area_positive": True,
        "area_conservation_error_lt_1e_8": True,
        "aggregate_min_percent": 90.0,
        "t_zone_min_percent": 90.0,
        "unexplained_hole_max_mm2": 100.0,
        "segmentation_sha256_length": 64,
        "anatomical_validation_eligible": False,
        "synthetic_full_numeric_pass": True,
        "synthetic_full_aggregate_percent": 100.0,
        "synthetic_full_t_zone_percent": 100.0,
        "synthetic_full_largest_hole_mm2": 0.0,
        "synthetic_full_product_status": "NUMERIC_SCREEN_PASS_NOT_PRODUCT_VALIDATION",
        "t_zone_development_status": "CAD_CLOSURE_BASELINE_DERIVED_FROM_AUTHORITY_GEOMETRY_NOT_ANATOMICAL_VALIDATION",
    }
    return PreflightCheck("COVERAGE_MESH_CONTRACT", "PASS" if actual == expected else "FAIL", "Coverage topology conserves area, includes T-zone/philtrum targets, consumes authority thresholds and refuses to turn synthetic numeric success into product validation.", actual, expected)


def _check_compliant_interface(authority: Authority | None, datums: CanonicalDatums | None) -> PreflightCheck:
    if authority is None or datums is None:
        return PreflightCheck("COMPLIANT_INTERFACE_CONTRACT", "FAIL", "Compliant-interface topology requires valid authority and datums.")
    try:
        _, _, _, coverage = _build_coverage(authority, datums)
        topology = build_compliant_interface_topology(authority, coverage)
        nose_zone = topology.zone_by_id[ZONE_T_NOSE_PHILTRUM]
        component_count = topology.contact_component_count(coverage)
    except (
        FacialReferenceError,
        FacialSurfaceError,
        ProtectedVolumeError,
        CoverageError,
        InterfaceTopologyError,
    ) as exc:
        return PreflightCheck("COMPLIANT_INTERFACE_CONTRACT", "FAIL", "Main interface contact/protected topology must be deterministic, area-conserving and evidence-bounded.", str(exc), "valid compliant-interface topology")

    nasal = topology.nasal_lobe_thickness_authority
    actual = {
        "assignment_count_matches_coverage": len(topology.assignments) == len(coverage.triangles),
        "contact_area_matches_coverage": abs(topology.contact_area_mm2 - coverage.target_area_mm2) <= 1e-8,
        "protected_area_matches_coverage": abs(topology.protected_opening_area_mm2 - coverage.protected_area_mm2) <= 1e-8,
        "t_zone_area_matches_coverage": abs(topology.t_zone_contact_area_mm2 - coverage.t_zone_target_area_mm2) <= 1e-8,
        "contact_component_count": component_count,
        "nasal_center_thickness_mm": nasal.center_thickness_mm,
        "nasal_doe_mm": list(nasal.doe_mm),
        "nasal_application_status": nasal.application_status,
        "full_t_zone_numeric_thickness_is_unassigned": nose_zone.nominal_thickness_mm is None and nose_zone.thickness_doe_mm == (),
        "anatomical_validation_eligible": topology.anatomical_validation_eligible,
        "topology_sha256_length": len(topology.topology_sha256),
    }
    expected = {
        "assignment_count_matches_coverage": True,
        "contact_area_matches_coverage": True,
        "protected_area_matches_coverage": True,
        "t_zone_area_matches_coverage": True,
        "contact_component_count": 1,
        "nasal_center_thickness_mm": 0.30,
        "nasal_doe_mm": [0.25, 0.30, 0.35],
        "nasal_application_status": "BOUNDARY_UNRESOLVED_UNTIL_DEDICATED_NASAL_SUBSYSTEM",
        "full_t_zone_numeric_thickness_is_unassigned": True,
        "anatomical_validation_eligible": False,
        "topology_sha256_length": 64,
    }
    return PreflightCheck(
        "COMPLIANT_INTERFACE_CONTRACT",
        "PASS" if actual == expected else "FAIL",
        "Interface parameter zones cover every target/protected triangle, preserve airway/opening exclusions, retain the nose-to-upper-lip target, and do not spread the nasal-lobe thickness value beyond its unresolved subsystem boundary.",
        actual,
        expected,
    )


def _iter_text_files(root: Path) -> Iterable[Path]:
    ignored_parts = {".git", ".pytest_cache", "__pycache__", ".venv", "generated"}
    allowed_suffixes = {".py", ".md", ".toml", ".yaml", ".yml", ".json", ".txt"}
    for path in root.rglob("*"):
        if path.is_file() and not any(part in ignored_parts for part in path.parts):
            if path.name == ".gitignore" or path.suffix.lower() in allowed_suffixes:
                yield path


def _check_legacy_naming(root: Path) -> PreflightCheck:
    offenders: list[str] = []
    for path in _iter_text_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.resolve() == Path(__file__).resolve():
            text = text.replace('"F" + "CW"', '"legacy"')
        if LEGACY_PRODUCT_TOKEN.lower() in text.lower():
            offenders.append(path.relative_to(root).as_posix())
    return PreflightCheck("LEGACY_PRODUCT_NAMING", "PASS" if not offenders else "FAIL", "No legacy product naming appears in source-controlled text artifacts.", offenders, [])


def _check_required_structure(root: Path) -> PreflightCheck:
    required = [
        "README.md",
        "pyproject.toml",
        "config/masck_one_authority.yaml",
        "schemas/masck_one_authority.schema.json",
        "src/masck_one/__init__.py",
        "src/masck_one/authority.py",
        "src/masck_one/spatial.py",
        "src/masck_one/anatomy.py",
        "src/masck_one/reference_surfaces.py",
        "src/masck_one/facial_surface.py",
        "src/masck_one/protected_volumes.py",
        "src/masck_one/worn_pose.py",
        "src/masck_one/coverage.py",
        "src/masck_one/interface_topology.py",
        "src/masck_one/model.py",
        "src/masck_one/assertions.py",
        "src/masck_one/export.py",
        "src/masck_one/cli.py",
        "tests/test_authority.py",
        "tests/test_authority_contract.py",
        "tests/test_spatial.py",
        "tests/test_anatomy.py",
        "tests/test_reference_surfaces.py",
        "tests/test_facial_surface.py",
        "tests/test_protected_volumes.py",
        "tests/test_worn_pose.py",
        "tests/test_coverage.py",
        "tests/test_interface_topology.py",
        "tests/test_model.py",
        "docs/COORDINATE_SYSTEM.md",
        "docs/REFERENCE_SURFACE_INGESTION.md",
        "docs/NEUTRAL_FACIAL_SURFACE.md",
        "docs/PROTECTED_VOLUMES.md",
        "docs/WORN_POSE.md",
        "docs/COVERAGE_MESH.md",
        "docs/COMPLIANT_INTERFACE_TOPOLOGY.md",
        "docs/ITERATION_10_ACCEPTANCE.md",
        "docs/PHASE_2_ITERATION_10.md",
        "docs/DEVELOPMENT_ROADMAP.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    return PreflightCheck("REPOSITORY_STRUCTURE", "PASS" if not missing else "FAIL", "Required Phase 2 Iteration-10 source files exist at deterministic paths.", missing, [])


def run_preflight() -> dict[str, object]:
    root = repository_root()
    authority_checks, authority = _check_authority()
    spatial_check, datums = _build_datums(authority)
    checks = [
        _check_python(),
        *_check_dependencies(),
        *authority_checks,
        spatial_check,
        _check_facial_reference(authority, datums),
        _check_reference_surface_ingestion(),
        _check_neutral_facial_surface(authority, datums),
        _check_protected_volumes(authority, datums),
        _check_worn_pose(authority, datums),
        _check_coverage_mesh(authority, datums),
        _check_compliant_interface(authority, datums),
        _check_legacy_naming(root),
        _check_required_structure(root),
    ]
    result = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {
        "project": "Masck One",
        "phase": "2",
        "iteration": "10",
        "result": result,
        "checks": [check.to_dict() for check in checks],
    }


def main() -> int:
    report = run_preflight()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
