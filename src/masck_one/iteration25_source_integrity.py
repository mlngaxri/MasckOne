"""Canonical source-graph integrity for the Iteration 25 Cell-4 release boundary.

This module deliberately does not promote any geometry or physical evidence. It closes a
software provenance problem: a graph of frozen dataclasses can be post-construction mutated
with ``object.__setattr__`` or rebuilt from mutually-consistent stale inputs. Iteration 25
must not treat such a graph as current merely because sibling hashes still agree.

The release boundary therefore uses two independent checks:

1. the supplied Authority must exactly match the validated repository authority file/schema;
2. every supplied dataclass graph is recursively reconstructed to re-run constructor
   invariants, then compared with a deterministic canonical Iteration 15/20-24 graph rebuilt
   from that repository authority.

The canonical graph is the current planar-development engineering lineage used by released
Iterations 15 and 20-25. Registered-anatomy, supplier-evidence, or compatibility-evidence
variants require their own explicit released provenance lineage; they are not silently
accepted here.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import math
from pathlib import Path

from .anatomy import build_facial_reference
from .authority import (
    Authority,
    AuthorityValidationReport,
    default_authority_path,
    default_schema_path,
    load_authority,
)
from .boundary_release import build_verified_interface_boundary_topology
from .cleanser_storage import CleanserStorageArchitecture, CompatibilityEvidence, build_cleanser_storage_architecture
from .coverage import FacialCoverageMesh, build_facial_coverage_mesh
from .distribution_geometry import DistributionGeometryArchitecture, build_distribution_geometry_architecture
from .distribution_manifold import DistributionManifoldArchitecture, build_distribution_manifold_architecture
from .facial_surface import build_planar_development_surface
from .fresh_pump_packaging import FreshPumpPackagingArchitecture, build_fresh_pump_packaging_architecture
from .interface_attachment import build_interface_attachment_architecture
from .interface_topology import build_compliant_interface_topology
from .protected_volumes import ProtectedVolumeSet, build_protected_volumes
from .spatial import CanonicalDatums
from .structural_frame import StructuralFrameTopology, build_structural_frame_topology
from .water_reservoir import WaterReservoirArchitecture, build_water_reservoir_architecture


class Iteration25SourceIntegrityError(ValueError):
    """Raised when the Iteration-25 inherited source graph cannot be trusted as current."""


@dataclass(frozen=True, slots=True)
class CanonicalIteration25Sources:
    """Deterministically rebuilt current source graph for Iteration 25."""

    authority: Authority
    water: WaterReservoirArchitecture
    cleanser: CleanserStorageArchitecture
    frame: StructuralFrameTopology
    pump: FreshPumpPackagingArchitecture
    manifold: DistributionManifoldArchitecture
    coverage: FacialCoverageMesh
    protected: ProtectedVolumeSet
    distribution: DistributionGeometryArchitecture


def _exact_json_tree(value: object, *, path: str) -> None:
    """Reject Python aliases that serialize like authority JSON but violate exact types."""

    if value is None:
        return
    if type(value) is bool:
        return
    if type(value) is str:
        return
    if type(value) is int:
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise Iteration25SourceIntegrityError(f"{path} contains a non-finite authority scalar")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _exact_json_tree(item, path=f"{path}[{index}]")
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise Iteration25SourceIntegrityError(f"{path} contains a non-string authority key")
            _exact_json_tree(item, path=f"{path}.{key}")
        return
    raise Iteration25SourceIntegrityError(
        f"{path} contains non-canonical authority value type {type(value).__name__}"
    )


def _revalidate_exact_graph(value: object, *, path: str) -> None:
    """Recursively reconstruct dataclasses so post-construction corruption fails closed."""

    if value is None:
        return
    if type(value) is bool:
        return
    if type(value) is str:
        return
    if type(value) is int:
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise Iteration25SourceIntegrityError(f"{path} contains a non-finite scalar")
        return
    if type(value) is tuple:
        for index, item in enumerate(value):
            _revalidate_exact_graph(item, path=f"{path}[{index}]")
        return
    if type(value) is frozenset:
        for index, item in enumerate(sorted(value, key=repr)):
            _revalidate_exact_graph(item, path=f"{path}{{{index}}}")
        return
    if is_dataclass(value) and not isinstance(value, type):
        cls = type(value)
        kwargs: dict[str, object] = {}
        for field in fields(value):
            field_value = getattr(value, field.name)
            _revalidate_exact_graph(field_value, path=f"{path}.{field.name}")
            if field.init:
                kwargs[field.name] = field_value
        try:
            cls(**kwargs)
        except Exception as exc:
            raise Iteration25SourceIntegrityError(
                f"{path} fails constructor invariant revalidation: {exc}"
            ) from exc
        return
    raise Iteration25SourceIntegrityError(
        f"{path} contains unsupported/non-canonical type {type(value).__name__}"
    )


def _require_exact_graph(actual: object, expected: object, *, path: str) -> None:
    """Compare canonical graphs without Python cross-type equality or signed-zero aliases."""

    if type(actual) is not type(expected):
        raise Iteration25SourceIntegrityError(
            f"{path} type {type(actual).__name__} differs from canonical type {type(expected).__name__}"
        )

    if actual is None or type(actual) in {bool, str, int}:
        if actual != expected:
            raise Iteration25SourceIntegrityError(
                f"{path} differs from the canonical current repository source graph"
            )
        return

    if type(actual) is float:
        if not math.isfinite(actual) or not math.isfinite(expected) or actual != expected:
            raise Iteration25SourceIntegrityError(
                f"{path} differs from the canonical current repository source graph"
            )
        if actual == 0.0 and math.copysign(1.0, actual) != math.copysign(1.0, expected):
            raise Iteration25SourceIntegrityError(
                f"{path} signed zero differs from the canonical current repository source graph"
            )
        return

    if type(actual) is list:
        if len(actual) != len(expected):
            raise Iteration25SourceIntegrityError(
                f"{path} length differs from the canonical current repository source graph"
            )
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected, strict=True)):
            _require_exact_graph(actual_item, expected_item, path=f"{path}[{index}]")
        return

    if type(actual) is dict:
        if len(actual) != len(expected) or set(actual) != set(expected):
            raise Iteration25SourceIntegrityError(
                f"{path} keys differ from the canonical current repository source graph"
            )
        for key in sorted(expected):
            if type(key) is not str or type(next(k for k in actual if k == key)) is not str:
                raise Iteration25SourceIntegrityError(f"{path} contains a non-canonical mapping key")
            _require_exact_graph(actual[key], expected[key], path=f"{path}.{key}")
        return

    if type(actual) is tuple:
        if len(actual) != len(expected):
            raise Iteration25SourceIntegrityError(
                f"{path} length differs from the canonical current repository source graph"
            )
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected, strict=True)):
            _require_exact_graph(actual_item, expected_item, path=f"{path}[{index}]")
        return

    if type(actual) is frozenset:
        actual_items = sorted(actual, key=lambda item: (type(item).__qualname__, repr(item)))
        expected_items = sorted(expected, key=lambda item: (type(item).__qualname__, repr(item)))
        if len(actual_items) != len(expected_items):
            raise Iteration25SourceIntegrityError(
                f"{path} size differs from the canonical current repository source graph"
            )
        for index, (actual_item, expected_item) in enumerate(
            zip(actual_items, expected_items, strict=True)
        ):
            _require_exact_graph(actual_item, expected_item, path=f"{path}{{{index}}}")
        return

    if is_dataclass(actual) and not isinstance(actual, type):
        actual_fields = fields(actual)
        expected_fields = fields(expected)
        if tuple(field.name for field in actual_fields) != tuple(field.name for field in expected_fields):
            raise Iteration25SourceIntegrityError(
                f"{path} dataclass field schema differs from the canonical source graph"
            )
        for field in actual_fields:
            _require_exact_graph(
                getattr(actual, field.name),
                getattr(expected, field.name),
                path=f"{path}.{field.name}",
            )
        return

    raise Iteration25SourceIntegrityError(
        f"{path} contains unsupported canonical comparison type {type(actual).__name__}"
    )


def _repository_authority(authority: Authority) -> Authority:
    if type(authority) is not Authority:
        raise Iteration25SourceIntegrityError("authority must be the exact Authority contract")
    if type(authority.validation_report) is not AuthorityValidationReport:
        raise Iteration25SourceIntegrityError("authority validation report must use the exact report type")

    expected_source = default_authority_path().resolve()
    expected_schema = default_schema_path().resolve()
    try:
        supplied_source = Path(authority.source).resolve()
        report_source = Path(authority.validation_report.source).resolve()
        report_schema = Path(authority.validation_report.schema).resolve()
    except Exception as exc:
        raise Iteration25SourceIntegrityError("authority provenance paths are not canonical") from exc

    if supplied_source != expected_source or report_source != expected_source:
        raise Iteration25SourceIntegrityError(
            "Iteration 25 accepts only the repository machine-authority source"
        )
    if report_schema != expected_schema:
        raise Iteration25SourceIntegrityError(
            "Iteration 25 accepts only the repository authority schema"
        )
    if type(authority.validation_report.valid) is not bool or not authority.validation_report.valid:
        raise Iteration25SourceIntegrityError("authority validation report is not valid")
    if type(authority.validation_report.issues) is not tuple or authority.validation_report.issues:
        raise Iteration25SourceIntegrityError("authority validation report contains unresolved issues")

    _exact_json_tree(authority.data, path="authority.data")
    try:
        fresh = load_authority(expected_source, schema_path=expected_schema)
    except Exception as exc:
        raise Iteration25SourceIntegrityError(
            "repository authority cannot be freshly loaded and validated"
        ) from exc
    _require_exact_graph(authority.data, fresh.data, path="authority.data")
    return fresh


def _canonical_sources(authority: Authority) -> CanonicalIteration25Sources:
    datums = CanonicalDatums.from_authority(authority)
    reference = build_facial_reference(authority, datums)
    surface = build_planar_development_surface(authority)
    protected = build_protected_volumes(authority, reference, surface)
    coverage = build_facial_coverage_mesh(authority, reference, surface, protected)
    interface = build_compliant_interface_topology(authority, coverage)
    boundaries = build_verified_interface_boundary_topology(
        authority,
        surface,
        coverage,
        interface,
    )
    attachment = build_interface_attachment_architecture(authority, boundaries)
    frame = build_structural_frame_topology(authority, attachment)
    water = build_water_reservoir_architecture(authority)
    cleanser = build_cleanser_storage_architecture(authority)
    pump = build_fresh_pump_packaging_architecture(authority, water, cleanser, frame)
    manifold = build_distribution_manifold_architecture(
        authority,
        pump,
        water,
        cleanser,
        frame,
    )
    distribution = build_distribution_geometry_architecture(
        authority,
        manifold,
        pump,
        water,
        cleanser,
        frame,
        coverage,
        protected,
    )
    return CanonicalIteration25Sources(
        authority=authority,
        water=water,
        cleanser=cleanser,
        frame=frame,
        pump=pump,
        manifold=manifold,
        coverage=coverage,
        protected=protected,
        distribution=distribution,
    )


def canonical_iteration25_sources(
    authority: Authority,
    *,
    distribution: DistributionGeometryArchitecture | None = None,
) -> CanonicalIteration25Sources:
    """Rebuild the released canonical source graph from repository authority.

    When ``distribution`` is supplied it must itself be the exact current Iteration 24
    distribution object. This gives downstream iterations a strict compatibility bridge:
    they may omit the inherited source objects, but they may not omit source proof.
    """

    fresh_authority = _repository_authority(authority)
    canonical = _canonical_sources(fresh_authority)
    if distribution is not None:
        if type(distribution) is not DistributionGeometryArchitecture:
            raise Iteration25SourceIntegrityError(
                "distribution must use the exact Iteration 24 architecture type"
            )
        _revalidate_exact_graph(distribution, path="distribution geometry")
        _require_exact_graph(
            distribution,
            canonical.distribution,
            path="distribution geometry",
        )
    return canonical


def validate_iteration25_source_graph(
    *,
    authority: Authority,
    water: WaterReservoirArchitecture,
    cleanser: CleanserStorageArchitecture,
    frame: StructuralFrameTopology,
    pump: FreshPumpPackagingArchitecture,
    manifold: DistributionManifoldArchitecture,
    coverage: FacialCoverageMesh,
    protected: ProtectedVolumeSet,
    distribution: DistributionGeometryArchitecture,
) -> None:
    """Prove Iteration-25 inputs are canonical, uncorrupted and current for this repo.

    This is a digital provenance gate only. Passing it does not prove hydraulic,
    anatomical, hygiene, service, orientation, leakage, or cleansing performance.
    """

    exact_types = (
        (water, WaterReservoirArchitecture, "water"),
        (cleanser, CleanserStorageArchitecture, "cleanser"),
        (frame, StructuralFrameTopology, "frame"),
        (pump, FreshPumpPackagingArchitecture, "pump"),
        (manifold, DistributionManifoldArchitecture, "manifold"),
        (coverage, FacialCoverageMesh, "coverage"),
        (protected, ProtectedVolumeSet, "protected"),
        (distribution, DistributionGeometryArchitecture, "distribution"),
    )
    for value, expected_type, label in exact_types:
        if type(value) is not expected_type:
            raise Iteration25SourceIntegrityError(
                f"{label} must use exact type {expected_type.__name__}"
            )
        _revalidate_exact_graph(value, path=label)

    evidence = cleanser.compatibility_evidence
    if type(evidence) is not tuple or any(type(item) is not CompatibilityEvidence for item in evidence):
        raise Iteration25SourceIntegrityError(
            "cleanser compatibility evidence must remain an exact immutable evidence tuple"
        )
    if evidence:
        raise Iteration25SourceIntegrityError(
            "cleanser compatibility evidence is not part of the released canonical Iteration 25 lineage"
        )
    canonical = canonical_iteration25_sources(authority)

    _require_exact_graph(water, canonical.water, path="water architecture")
    _require_exact_graph(cleanser, canonical.cleanser, path="cleanser architecture")
    _require_exact_graph(frame, canonical.frame, path="structural-frame topology")
    _require_exact_graph(coverage, canonical.coverage, path="coverage segmentation")
    _require_exact_graph(protected, canonical.protected, path="protected-volume set")
    _require_exact_graph(pump, canonical.pump, path="fresh-pump architecture")
    _require_exact_graph(manifold, canonical.manifold, path="distribution manifold")
    _require_exact_graph(distribution, canonical.distribution, path="distribution geometry")