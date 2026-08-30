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
from .facial_surface import FacialSurfaceError, build_planar_development_surface
from .protected_volumes import ProtectedVolumeError, build_protected_volumes
from .reference_surfaces import (
    ReferenceSurfaceAsset,
    ReferenceSurfaceError,
    SurfaceProvenance,
    TriangleMesh,
    identity_registration,
)
from .spatial import CanonicalDatums, Point3, SpatialContractError


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
    status = "PASS" if tuple(actual) == REQUIRED_PYTHON else "FAIL"
    return PreflightCheck(
        id="PYTHON_VERSION",
        status=status,
        message="Runtime uses the repository's controlled Python major/minor version.",
        actual=actual,
        expected=list(REQUIRED_PYTHON),
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
                id=f"DEPENDENCY_{re.sub(r'[^A-Za-z0-9]+', '_', distribution).upper()}",
                status="PASS" if actual == expected else "FAIL",
                message="Runtime dependency matches the controlled repository version.",
                actual=actual,
                expected=expected,
            )
        )
    return checks


def _check_authority() -> tuple[list[PreflightCheck], Authority | None]:
    try:
        authority = load_authority()
    except AuthorityError as exc:
        return ([PreflightCheck(
            id="AUTHORITY_LOAD",
            status="FAIL",
            message="Machine authority must load without schema or semantic errors.",
            actual=str(exc),
            expected="valid authority",
        )], None)

    checks = [
        PreflightCheck("AUTHORITY_LOAD", "PASS", "Machine authority loads successfully."),
        PreflightCheck(
            "AUTHORITY_CONTRACT",
            "PASS" if authority.validation_report.valid else "FAIL",
            "Authority passes strict JSON Schema and deterministic semantic validation.",
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
        return PreflightCheck(
            "SPATIAL_CONTRACT", "FAIL",
            "Canonical spatial datums require a valid machine authority.",
            None, "valid authority and right-handed canonical datums",
        ), None
    try:
        datums = CanonicalDatums.from_authority(authority)
    except SpatialContractError as exc:
        return PreflightCheck(
            "SPATIAL_CONTRACT", "FAIL",
            "Canonical spatial datums must be finite, orthonormal, right-handed, and authority-aligned.",
            str(exc), "valid canonical datums",
        ), None
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
    return PreflightCheck(
        "SPATIAL_CONTRACT", "PASS" if actual == expected else "FAIL",
        "Canonical origin, axes and principal datum planes match the frozen Masck One convention.",
        actual, expected,
    ), datums


def _check_facial_reference(authority: Authority | None, datums: CanonicalDatums | None) -> PreflightCheck:
    if authority is None or datums is None:
        return PreflightCheck(
            "FACIAL_REFERENCE_CONTRACT", "FAIL",
            "Facial reference requires valid authority and canonical datums.",
            None, "valid authority/datums and neutral landmark layer",
        )
    try:
        reference = build_facial_reference(authority, datums)
    except FacialReferenceError as exc:
        return PreflightCheck(
            "FACIAL_REFERENCE_CONTRACT", "FAIL",
            "Authority facial landmarks must form a unique, symmetric neutral-baseline projection with no invented 3D depth.",
            str(exc), "valid neutral 2D facial reference",
        )
    metrics = reference.metrics
    actual = {
        "reference_kind": reference.reference_kind,
        "landmark_count": len(reference.landmarks),
        "landmark_ids": [landmark.id for landmark in reference.landmarks],
        "unresolved_3d_count": len(reference.unresolved_3d_landmarks()),
        "interpupillary_center_spacing_mm": metrics.interpupillary_center_spacing_mm,
        "nostril_center_spacing_mm": metrics.nostril_center_spacing_mm,
        "eye_to_mouth_center_vertical_mm": metrics.eye_to_mouth_center_vertical_mm,
    }
    expected = {
        "reference_kind": "NEUTRAL_2D_CAD_BASELINE_PROJECTION",
        "landmark_count": 5,
        "landmark_ids": [
            "MASCK_ONE-LMK-EYE-LEFT-CENTER", "MASCK_ONE-LMK-EYE-RIGHT-CENTER",
            "MASCK_ONE-LMK-NOSTRIL-LEFT-CENTER", "MASCK_ONE-LMK-NOSTRIL-RIGHT-CENTER",
            "MASCK_ONE-LMK-MOUTH-CENTER",
        ],
        "unresolved_3d_count": 5,
        "interpupillary_center_spacing_mm": 63.0,
        "nostril_center_spacing_mm": 21.0,
        "eye_to_mouth_center_vertical_mm": 85.0,
    }
    return PreflightCheck(
        "FACIAL_REFERENCE_CONTRACT", "PASS" if actual == expected else "FAIL",
        "Facial landmark IDs, authority coordinates, bilateral symmetry, derived neutral metrics, and unresolved 3D status are deterministic.",
        actual, expected,
    )


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
        edge_mm = registered.vertices[0].vector_to(registered.vertices[1]).norm()
        manifest = asset.registration_manifest()
    except (ReferenceSurfaceError, SpatialContractError) as exc:
        return PreflightCheck(
            "REFERENCE_SURFACE_INGESTION", "FAIL",
            "Reference surfaces must preserve provenance, units, handedness and explicit rigid registration.",
            str(exc), "valid traceable ingestion contract",
        )
    actual = {
        "edge_mm": edge_mm,
        "source_units": manifest["source_units"],
        "scale_to_mm": manifest["source_scale_to_mm"],
        "handedness": manifest["source_handedness"],
        "vertex_count": manifest["mesh"]["vertex_count"],
        "triangle_count": manifest["mesh"]["triangle_count"],
    }
    expected = {
        "edge_mm": 10.0, "source_units": "cm", "scale_to_mm": 10.0,
        "handedness": "right", "vertex_count": 3, "triangle_count": 1,
    }
    return PreflightCheck(
        "REFERENCE_SURFACE_INGESTION", "PASS" if actual == expected else "FAIL",
        "Reference-surface ingestion preserves units/provenance and produces deterministic Masck One-global geometry.",
        actual, expected,
    )


def _check_neutral_facial_surface(authority: Authority | None, datums: CanonicalDatums | None) -> PreflightCheck:
    if authority is None or datums is None:
        return PreflightCheck(
            "NEUTRAL_FACIAL_SURFACE", "FAIL",
            "Neutral facial surface requires valid authority and canonical datums.",
            None, "deterministic development surface",
        )
    try:
        reference = build_facial_reference(authority, datums)
        surface = build_planar_development_surface(authority)
        projections = surface.project_reference_landmarks(reference)
    except (FacialSurfaceError, FacialReferenceError) as exc:
        return PreflightCheck(
            "NEUTRAL_FACIAL_SURFACE", "FAIL",
            "Development facial surface must be deterministic and explicitly non-anatomical until a registered source exists.",
            str(exc), "valid topology-only surface",
        )
    actual = {
        "kind": surface.descriptor.kind,
        "validation_eligible": surface.descriptor.anatomical_validation_eligible,
        "planar": surface.is_planar,
        "vertex_count": surface.mesh.vertex_count,
        "triangle_count": surface.mesh.triangle_count,
        "projection_count": len(projections),
        "max_projection_error_mm_lt_3": max(p.xy_error_mm for p in projections) < 3.0,
    }
    expected = {
        "kind": "PLANAR_DEVELOPMENT_REFERENCE", "validation_eligible": False, "planar": True,
        "vertex_count": surface.mesh.vertex_count, "triangle_count": surface.mesh.triangle_count,
        "projection_count": 5, "max_projection_error_mm_lt_3": True,
    }
    passed = actual == expected and surface.mesh.vertex_count > 1000 and surface.mesh.triangle_count > 1500
    return PreflightCheck(
        "NEUTRAL_FACIAL_SURFACE", "PASS" if passed else "FAIL",
        "Neutral surface provides deterministic topology while refusing to masquerade as anatomical fit evidence.",
        actual, expected,
    )


def _check_protected_volumes(authority: Authority | None, datums: CanonicalDatums | None) -> PreflightCheck:
    if authority is None or datums is None:
        return PreflightCheck(
            "PROTECTED_VOLUME_CONTRACT", "FAIL",
            "Protected volumes require valid authority and canonical datums.",
            None, "five authority-derived protected targets",
        )
    try:
        reference = build_facial_reference(authority, datums)
        surface = build_planar_development_surface(authority)
        protected = build_protected_volumes(authority, reference, surface)
    except (FacialReferenceError, FacialSurfaceError, ProtectedVolumeError) as exc:
        return PreflightCheck(
            "PROTECTED_VOLUME_CONTRACT", "FAIL",
            "Eye, mouth and airway analytical keep-outs must preserve authority clearances and unresolved 3D status.",
            str(exc), "valid conservative protected-volume set",
        )
    actual_clearances = {
        volume.zone.zone_id: volume.zone.required_rigid_clearance_mm for volume in protected.all
    }
    expected_clearances = {
        "MASCK_ONE-PROTECTED-EYE-LEFT": 8.5,
        "MASCK_ONE-PROTECTED-EYE-RIGHT": 8.5,
        "MASCK_ONE-PROTECTED-MOUTH": 9.5,
        "MASCK_ONE-PROTECTED-NOSTRIL-LEFT": 7.5,
        "MASCK_ONE-PROTECTED-NOSTRIL-RIGHT": 7.5,
    }
    actual = {
        "count": len(protected.all),
        "clearances_mm": actual_clearances,
        "z_policies": sorted({volume.z_policy for volume in protected.all}),
        "any_validation_eligible": any(volume.anatomical_validation_eligible for volume in protected.all),
        "dynamic_geometry_blocked": "3D_DYNAMIC_GEOMETRY_BLOCKED" in protected.evidence_status,
    }
    expected = {
        "count": 5,
        "clearances_mm": expected_clearances,
        "z_policies": ["UNBOUNDED_UNTIL_REGISTERED_ANATOMICAL_SURFACE"],
        "any_validation_eligible": False,
        "dynamic_geometry_blocked": True,
    }
    return PreflightCheck(
        "PROTECTED_VOLUME_CONTRACT", "PASS" if actual == expected else "FAIL",
        "Five conservative eye/mouth/airway protected footprints are deterministic while dynamic 3D anatomy remains explicitly blocked.",
        actual, expected,
    )


def _iter_text_files(root: Path) -> Iterable[Path]:
    ignored_parts = {".git", ".pytest_cache", "__pycache__", ".venv", "generated"}
    allowed_suffixes = {".py", ".md", ".toml", ".yaml", ".yml", ".json", ".txt"}
    for path in root.rglob("*"):
        if not path.is_file() or any(part in ignored_parts for part in path.parts):
            continue
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
    return PreflightCheck(
        "LEGACY_PRODUCT_NAMING", "PASS" if not offenders else "FAIL",
        "No legacy product naming appears in source-controlled text artifacts.",
        offenders, [],
    )


def _check_required_structure(root: Path) -> PreflightCheck:
    required = [
        "README.md", "pyproject.toml", "config/masck_one_authority.yaml",
        "schemas/masck_one_authority.schema.json",
        "src/masck_one/__init__.py", "src/masck_one/authority.py", "src/masck_one/spatial.py",
        "src/masck_one/anatomy.py", "src/masck_one/reference_surfaces.py",
        "src/masck_one/facial_surface.py", "src/masck_one/protected_volumes.py",
        "src/masck_one/model.py", "src/masck_one/assertions.py", "src/masck_one/export.py", "src/masck_one/cli.py",
        "tests/test_authority.py", "tests/test_authority_contract.py", "tests/test_spatial.py",
        "tests/test_anatomy.py", "tests/test_reference_surfaces.py", "tests/test_facial_surface.py",
        "tests/test_protected_volumes.py", "tests/test_model.py",
        "docs/COORDINATE_SYSTEM.md", "docs/REFERENCE_SURFACE_INGESTION.md",
        "docs/NEUTRAL_FACIAL_SURFACE.md", "docs/PROTECTED_VOLUMES.md", "docs/DEVELOPMENT_ROADMAP.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    return PreflightCheck(
        "REPOSITORY_STRUCTURE", "PASS" if not missing else "FAIL",
        "Required Phase 1 source files exist at deterministic paths.",
        missing, [],
    )


def run_preflight() -> dict[str, object]:
    root = repository_root()
    authority_checks, authority = _check_authority()
    spatial_check, datums = _build_datums(authority)
    checks = [
        _check_python(), *_check_dependencies(), *authority_checks, spatial_check,
        _check_facial_reference(authority, datums),
        _check_reference_surface_ingestion(),
        _check_neutral_facial_surface(authority, datums),
        _check_protected_volumes(authority, datums),
        _check_legacy_naming(root),
        _check_required_structure(root),
    ]
    result = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {
        "project": "Masck One",
        "phase": "1",
        "iteration": "7",
        "result": result,
        "checks": [check.to_dict() for check in checks],
    }


def main() -> int:
    report = run_preflight()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
