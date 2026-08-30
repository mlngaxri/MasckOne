"""Masck One deterministic engineering/code-CAD package.

Public objects are loaded lazily so lightweight authority/preflight commands do not
import the CAD kernel unless geometry is actually requested.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .anatomy import FacialReferenceLayer, PlanarLandmark
    from .authority import Authority
    from .model import MasckOneModel
    from .reference_surfaces import ReferenceSurfaceAsset, SurfaceProvenance, SurfaceRegistration, TriangleMesh
    from .spatial import CanonicalDatums, DatumFrame, DatumPlane, Point2, Point3, RigidTransform, Vector3

__all__ = [
    "Authority",
    "MasckOneModel",
    "FacialReferenceLayer",
    "PlanarLandmark",
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
    "load_authority",
    "build_facial_reference",
    "build_model",
]
__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    if name in {"Authority", "load_authority"}:
        from .authority import Authority, load_authority

        exports = {"Authority": Authority, "load_authority": load_authority}
        return exports[name]
    if name in {"FacialReferenceLayer", "PlanarLandmark", "build_facial_reference"}:
        from .anatomy import FacialReferenceLayer, PlanarLandmark, build_facial_reference

        exports = {
            "FacialReferenceLayer": FacialReferenceLayer,
            "PlanarLandmark": PlanarLandmark,
            "build_facial_reference": build_facial_reference,
        }
        return exports[name]
    if name in {"ReferenceSurfaceAsset", "SurfaceProvenance", "SurfaceRegistration", "TriangleMesh"}:
        from .reference_surfaces import ReferenceSurfaceAsset, SurfaceProvenance, SurfaceRegistration, TriangleMesh

        exports = {
            "ReferenceSurfaceAsset": ReferenceSurfaceAsset,
            "SurfaceProvenance": SurfaceProvenance,
            "SurfaceRegistration": SurfaceRegistration,
            "TriangleMesh": TriangleMesh,
        }
        return exports[name]
    if name in {"MasckOneModel", "build_model"}:
        from .model import MasckOneModel, build_model

        exports = {"MasckOneModel": MasckOneModel, "build_model": build_model}
        return exports[name]
    if name in {
        "CanonicalDatums",
        "DatumFrame",
        "DatumPlane",
        "Point2",
        "Point3",
        "RigidTransform",
        "Vector3",
    }:
        from .spatial import CanonicalDatums, DatumFrame, DatumPlane, Point2, Point3, RigidTransform, Vector3

        exports = {
            "CanonicalDatums": CanonicalDatums,
            "DatumFrame": DatumFrame,
            "DatumPlane": DatumPlane,
            "Point2": Point2,
            "Point3": Point3,
            "RigidTransform": RigidTransform,
            "Vector3": Vector3,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
