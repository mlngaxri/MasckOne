"""Canonical source-graph integrity for the Iteration 25 Cell-4 release boundary.

This module deliberately does not promote any geometry or physical evidence.  It closes a
software provenance problem: a graph of frozen dataclasses can be post-construction mutated
with ``object.__setattr__`` or rebuilt from mutually-consistent stale inputs.  Iteration 25
must not treat such a graph as current merely because sibling hashes still agree.

The release boundary therefore uses two independent checks:

1. the supplied Authority must exactly match the validated repository authority file/schema;
2. every supplied dataclass graph is recursively reconstructed to re-run constructor
   invariants, then compared with a deterministic canonical Iteration 15/20-24 graph rebuilt
   from that repository authority.

The canonical graph is the current planar-development engineering lineage used by released
Iterations 15 and 20-25.  Registered-anatomy or supplier-evidence variants require their own
explicit release lineage; they are not silently accepted here.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import math
from pathlib import Path
from typing import Any

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
    if authority.data != fresh.data:
        raise Iteration25SourceIntegrityError(
            "in-memory Authority data differs from the current repository authority file"
        )
    return fresh


def _canonical_sources(
    authority: Authority,
    compatibility_evidence: tuple[CompatibilityEvidence, ...],
) -> CanonicalIteration25Sources:
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
    if compatibility_evidence:
        cleanser = cleanser.with_compatibility_evidence(compatibility_evidence)
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


def _require_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise Iteration25SourceIntegrityError(
            f"{label} differs from the canonical current repository source graph"
        )


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

    This is a digital provenance gate only.  Passing it does not prove hydraulic,
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

    fresh_authority = _repository_authority(authority)
    evidence = cleanser.compatibility_evidence
    if type(evidence) is not tuple or any(type(item) is not CompatibilityEvidence for item in evidence):
        raise Iteration25SourceIntegrityError(
            "cleanser compatibility evidence must remain an exact immutable evidence tuple"
        )
    canonical = _canonical_sources(fresh_authority, evidence)

    _require_equal(
        "water architecture",
        water.manifest(include_sha=False),
        canonical.water.manifest(include_sha=False),
    )
    _require_equal(
        "cleanser architecture",
        cleanser.manifest(include_sha=False),
        canonical.cleanser.manifest(include_sha=False),
    )
    _require_equal(
        "structural-frame topology",
        frame.manifest(include_sha=False),
        canonical.frame.manifest(include_sha=False),
    )
    _require_equal("coverage segmentation", coverage.manifest(), canonical.coverage.manifest())
    _require_equal("protected-volume set", protected.manifest(), canonical.protected.manifest())
    _require_equal(
        "fresh-pump architecture",
        pump.manifest(include_sha=False),
        canonical.pump.manifest(include_sha=False),
    )
    _require_equal(
        "distribution manifold",
        manifold.manifest(include_sha=False),
        canonical.manifold.manifest(include_sha=False),
    )
    _require_equal(
        "distribution geometry",
        distribution.manifest(include_sha=False),
        canonical.distribution.manifest(include_sha=False),
    )
