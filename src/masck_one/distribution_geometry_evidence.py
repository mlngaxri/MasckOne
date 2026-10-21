"""Consumption-time integrity boundary for CLEAN outlet distribution geometry."""
from __future__ import annotations

from .authority import Authority
from .cleanser_storage import CleanserStorageArchitecture
from .coverage import FacialCoverageMesh
from .distribution_geometry import (
    DistributionGeometryArchitecture,
    DistributionGeometryError,
    build_distribution_geometry_architecture,
)
from .distribution_manifold import DistributionManifoldArchitecture
from .fresh_pump_packaging import FreshPumpPackagingArchitecture
from .protected_volumes import ProtectedVolumeSet
from .structural_frame import StructuralFrameTopology
from .water_reservoir import WaterReservoirArchitecture


def validate_canonical_distribution_geometry(
    geometry: DistributionGeometryArchitecture,
    *,
    authority: Authority,
    manifold: DistributionManifoldArchitecture,
    pump: FreshPumpPackagingArchitecture,
    water: WaterReservoirArchitecture,
    cleanser: CleanserStorageArchitecture,
    frame: StructuralFrameTopology,
    coverage: FacialCoverageMesh,
    protected: ProtectedVolumeSet,
) -> DistributionGeometryArchitecture:
    """Reject stale or substituted outlet selections at a consumption boundary.

    ``DistributionGeometryArchitecture.validate_current_sources`` proves that every
    supplied placement is individually legal for the current sources. This stronger
    boundary also reconstructs the deterministic farthest-sample selection, including
    the independent 18-water then 6-cleanser allocation, and requires the consumed
    architecture to be exactly that canonical result. Comparing the complete typed
    architecture, rather than trusting its stored digest alone, keeps this boundary
    fail-closed if a caller mutates both geometry and the cached digest coherently.
    """
    if type(geometry) is not DistributionGeometryArchitecture:
        raise DistributionGeometryError(
            "distribution geometry evidence must be exact DistributionGeometryArchitecture"
        )

    geometry.validate_current_sources(
        authority=authority,
        manifold=manifold,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=coverage,
        protected=protected,
    )
    expected = build_distribution_geometry_architecture(
        authority,
        manifold,
        pump,
        water,
        cleanser,
        frame,
        coverage,
        protected,
    )
    if geometry != expected:
        raise DistributionGeometryError(
            "distribution geometry does not match canonical current-source outlet selection"
        )
    return geometry
