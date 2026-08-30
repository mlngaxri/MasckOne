"""Masck One deterministic engineering/code-CAD package.

Public objects are loaded lazily so lightweight authority/preflight commands do not
import the CAD kernel unless geometry is actually requested.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .anatomy import FacialReferenceLayer, PlanarLandmark
    from .authority import Authority
    from .coverage import CoverageEvaluation, FacialCoverageMesh, TZoneDevelopmentDefinition
    from .facial_surface import FacialSurface, FacialSurfaceDescriptor
    from .interface_boundaries import InterfaceBoundaryDefinition, InterfaceBoundaryEdge, InterfaceBoundaryTopology
    from .interface_topology import (
        CompliantInterfaceTopology,
        InterfaceParameterZone,
        InterfaceTriangleAssignment,
        NasalLobeThicknessAuthority,
    )
    from .model import MasckOneModel
    from .nasal_subsystem import (
        NasalDevelopmentBoundaries,
        NasalRoleDefinition,
        NasalSubsystemTopology,
        NasalTriangleAssignment,
    )
    from .protected_volumes import PlanarProtectedZone, ProtectedVolume, ProtectedVolumeSet
    from .reference_surfaces import ReferenceSurfaceAsset, SurfaceProvenance, SurfaceRegistration, TriangleMesh
    from .spatial import CanonicalDatums, DatumFrame, DatumPlane, Point2, Point3, RigidTransform, Vector3
    from .worn_pose import PosedZoneBounds, WornPose, WornPoseLimits, WornPoseRegressionSet

__all__ = [
    "Authority",
    "MasckOneModel",
    "FacialReferenceLayer",
    "PlanarLandmark",
    "FacialSurface",
    "FacialSurfaceDescriptor",
    "PlanarProtectedZone",
    "ProtectedVolume",
    "ProtectedVolumeSet",
    "FacialCoverageMesh",
    "CoverageEvaluation",
    "TZoneDevelopmentDefinition",
    "CompliantInterfaceTopology",
    "InterfaceParameterZone",
    "InterfaceTriangleAssignment",
    "NasalLobeThicknessAuthority",
    "InterfaceBoundaryDefinition",
    "InterfaceBoundaryEdge",
    "InterfaceBoundaryTopology",
    "NasalDevelopmentBoundaries",
    "NasalRoleDefinition",
    "NasalSubsystemTopology",
    "NasalTriangleAssignment",
    "ReferenceSurfaceAsset",
    "SurfaceProvenance",
    "SurfaceRegistration",
    "TriangleMesh",
    "CanonicalDatums",
    "DatumFrame",
    "DatumPlane",
    "Point2",
    "Point3",
    "RigidTransform",
    "Vector3",
    "WornPose",
    "WornPoseLimits",
    "WornPoseRegressionSet",
    "PosedZoneBounds",
    "load_authority",
    "build_facial_reference",
    "build_planar_development_surface",
    "build_protected_volumes",
    "build_facial_coverage_mesh",
    "build_t_zone_development_definition",
    "build_compliant_interface_topology",
    "build_interface_boundary_topology",
    "build_nasal_subsystem_topology",
    "derive_nasal_development_boundaries",
    "generate_hard_envelope_regression_set",
    "protected_zone_regression_bounds",
    "build_model",
]
__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    if name in {"Authority", "load_authority"}:
        from .authority import Authority, load_authority
        return {"Authority": Authority, "load_authority": load_authority}[name]

    if name in {"FacialReferenceLayer", "PlanarLandmark", "build_facial_reference"}:
        from .anatomy import FacialReferenceLayer, PlanarLandmark, build_facial_reference
        return {"FacialReferenceLayer": FacialReferenceLayer, "PlanarLandmark": PlanarLandmark, "build_facial_reference": build_facial_reference}[name]

    if name in {"FacialSurface", "FacialSurfaceDescriptor", "build_planar_development_surface"}:
        from .facial_surface import FacialSurface, FacialSurfaceDescriptor, build_planar_development_surface
        return {"FacialSurface": FacialSurface, "FacialSurfaceDescriptor": FacialSurfaceDescriptor, "build_planar_development_surface": build_planar_development_surface}[name]

    if name in {"PlanarProtectedZone", "ProtectedVolume", "ProtectedVolumeSet", "build_protected_volumes"}:
        from .protected_volumes import PlanarProtectedZone, ProtectedVolume, ProtectedVolumeSet, build_protected_volumes
        return {"PlanarProtectedZone": PlanarProtectedZone, "ProtectedVolume": ProtectedVolume, "ProtectedVolumeSet": ProtectedVolumeSet, "build_protected_volumes": build_protected_volumes}[name]

    if name in {"FacialCoverageMesh", "CoverageEvaluation", "TZoneDevelopmentDefinition", "build_facial_coverage_mesh", "build_t_zone_development_definition"}:
        from .coverage import CoverageEvaluation, FacialCoverageMesh, TZoneDevelopmentDefinition, build_facial_coverage_mesh, build_t_zone_development_definition
        return {
            "FacialCoverageMesh": FacialCoverageMesh,
            "CoverageEvaluation": CoverageEvaluation,
            "TZoneDevelopmentDefinition": TZoneDevelopmentDefinition,
            "build_facial_coverage_mesh": build_facial_coverage_mesh,
            "build_t_zone_development_definition": build_t_zone_development_definition,
        }[name]

    if name in {"CompliantInterfaceTopology", "InterfaceParameterZone", "InterfaceTriangleAssignment", "NasalLobeThicknessAuthority", "build_compliant_interface_topology"}:
        from .interface_topology import CompliantInterfaceTopology, InterfaceParameterZone, InterfaceTriangleAssignment, NasalLobeThicknessAuthority, build_compliant_interface_topology
        return {
            "CompliantInterfaceTopology": CompliantInterfaceTopology,
            "InterfaceParameterZone": InterfaceParameterZone,
            "InterfaceTriangleAssignment": InterfaceTriangleAssignment,
            "NasalLobeThicknessAuthority": NasalLobeThicknessAuthority,
            "build_compliant_interface_topology": build_compliant_interface_topology,
        }[name]

    if name in {"InterfaceBoundaryDefinition", "InterfaceBoundaryEdge", "InterfaceBoundaryTopology", "build_interface_boundary_topology"}:
        from .interface_boundaries import InterfaceBoundaryDefinition, InterfaceBoundaryEdge, InterfaceBoundaryTopology, build_interface_boundary_topology
        return {
            "InterfaceBoundaryDefinition": InterfaceBoundaryDefinition,
            "InterfaceBoundaryEdge": InterfaceBoundaryEdge,
            "InterfaceBoundaryTopology": InterfaceBoundaryTopology,
            "build_interface_boundary_topology": build_interface_boundary_topology,
        }[name]

    if name in {"NasalDevelopmentBoundaries", "NasalRoleDefinition", "NasalSubsystemTopology", "NasalTriangleAssignment", "build_nasal_subsystem_topology", "derive_nasal_development_boundaries"}:
        from .nasal_subsystem import (
            NasalDevelopmentBoundaries,
            NasalRoleDefinition,
            NasalSubsystemTopology,
            NasalTriangleAssignment,
            build_nasal_subsystem_topology,
            derive_nasal_development_boundaries,
        )
        return {
            "NasalDevelopmentBoundaries": NasalDevelopmentBoundaries,
            "NasalRoleDefinition": NasalRoleDefinition,
            "NasalSubsystemTopology": NasalSubsystemTopology,
            "NasalTriangleAssignment": NasalTriangleAssignment,
            "build_nasal_subsystem_topology": build_nasal_subsystem_topology,
            "derive_nasal_development_boundaries": derive_nasal_development_boundaries,
        }[name]

    if name in {"ReferenceSurfaceAsset", "SurfaceProvenance", "SurfaceRegistration", "TriangleMesh"}:
        from .reference_surfaces import ReferenceSurfaceAsset, SurfaceProvenance, SurfaceRegistration, TriangleMesh
        return {"ReferenceSurfaceAsset": ReferenceSurfaceAsset, "SurfaceProvenance": SurfaceProvenance, "SurfaceRegistration": SurfaceRegistration, "TriangleMesh": TriangleMesh}[name]

    if name in {"WornPose", "WornPoseLimits", "WornPoseRegressionSet", "PosedZoneBounds", "generate_hard_envelope_regression_set", "protected_zone_regression_bounds"}:
        from .worn_pose import PosedZoneBounds, WornPose, WornPoseLimits, WornPoseRegressionSet, generate_hard_envelope_regression_set, protected_zone_regression_bounds
        return {
            "WornPose": WornPose,
            "WornPoseLimits": WornPoseLimits,
            "WornPoseRegressionSet": WornPoseRegressionSet,
            "PosedZoneBounds": PosedZoneBounds,
            "generate_hard_envelope_regression_set": generate_hard_envelope_regression_set,
            "protected_zone_regression_bounds": protected_zone_regression_bounds,
        }[name]

    if name in {"MasckOneModel", "build_model"}:
        from .model import MasckOneModel, build_model
        return {"MasckOneModel": MasckOneModel, "build_model": build_model}[name]

    if name in {"CanonicalDatums", "DatumFrame", "DatumPlane", "Point2", "Point3", "RigidTransform", "Vector3"}:
        from .spatial import CanonicalDatums, DatumFrame, DatumPlane, Point2, Point3, RigidTransform, Vector3
        return {"CanonicalDatums": CanonicalDatums, "DatumFrame": DatumFrame, "DatumPlane": DatumPlane, "Point2": Point2, "Point3": Point3, "RigidTransform": RigidTransform, "Vector3": Vector3}[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
