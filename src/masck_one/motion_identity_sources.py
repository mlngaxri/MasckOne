"""Controlled source factories for digital-motion identity registries.

A registry digest is not source authority by itself. Authoritative actuator-motion
identity can be reconstructed either from explicitly supplied current engineering
sources for internal composition, or from the canonical repository model graph for
release/export use.

No retention, quick-release, service, exploded-assembly or cleansing component is
invented here. Those motion kinds remain unavailable until an equivalent released
source object exists for them.
"""
from __future__ import annotations

from .actuator_frames import ZONE_IDS, build_actuator_frame_architecture
from .authority import Authority
from .boundary_release import build_verified_interface_boundary_topology
from .digital_motion import (
    MotionIdentityBinding,
    MotionIdentityRegistry,
    MotionKind,
    MotionTrack,
    validate_track,
)
from .interface_attachment import build_interface_attachment_architecture
from .model import build_model
from .structural_frame import StructuralFrameTopology, build_structural_frame_topology


class MotionIdentitySourceError(ValueError):
    """Raised when a motion identity cannot be derived from controlled current sources."""


def build_current_actuator_motion_identity_registry(
    *,
    authority: Authority,
    structural_frame: StructuralFrameTopology,
) -> MotionIdentityRegistry:
    """Derive actuator identities from the supplied current engineering source graph.

    This composition helper deliberately accepts only the current authority and exact
    structural-frame object. It never accepts identity strings or provenance hashes
    from its caller. Release/export code should prefer
    ``build_repository_actuator_motion_identity_registry`` so even the upstream frame
    cannot be substituted by a caller.
    """

    if type(authority) is not Authority:
        raise TypeError("authority must be exact Authority")
    if type(structural_frame) is not StructuralFrameTopology:
        raise TypeError("structural_frame must be exact StructuralFrameTopology")

    architecture = build_actuator_frame_architecture(authority, structural_frame)
    architecture.validate_current_sources(structural_frame=structural_frame, authority=authority)

    if tuple(frame.zone_id for frame in architecture.frames) != ZONE_IDS:
        raise MotionIdentitySourceError("canonical actuator architecture lost controlled four-zone identities")

    bindings = tuple(
        MotionIdentityBinding(
            component_id=zone_id,
            frame_id=zone_id,
            allowed_kinds=(MotionKind.ACTUATOR,),
        )
        for zone_id in ZONE_IDS
    )
    return MotionIdentityRegistry(
        mechanism_sha256=architecture.architecture_sha256,
        source_geometry_manifest_sha256=architecture.architecture_sha256,
        bindings=bindings,
    )


def build_repository_actuator_motion_identity_registry() -> MotionIdentityRegistry:
    """Rebuild actuator motion authority from canonical repository engineering inputs.

    This is the export/release trust boundary. It accepts no authority object,
    structural frame, identity list, frame list, motion kind or digest from a caller.
    Instead it rebuilds the canonical model, verified interface boundary, attachment,
    structural frame and actuator-frame architecture in dependency order, then derives
    the registry from those exact objects. A caller therefore cannot pair a correct
    digest with invented component/frame bindings or substitute a mutated frame object.

    The resulting registry is still digital-only. Actuator placement, envelope and
    sweep readiness remain governed by the actuator-frame/actuation-sweep evidence gates.
    """

    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    structural_frame = build_structural_frame_topology(model.authority, attachment)
    return build_current_actuator_motion_identity_registry(
        authority=model.authority,
        structural_frame=structural_frame,
    )


def validate_current_actuator_motion_track(
    track: MotionTrack,
    *,
    authority: Authority,
    structural_frame: StructuralFrameTopology,
) -> MotionIdentityRegistry:
    """Validate an actuator track against an explicitly supplied current source graph."""

    if type(track) is not MotionTrack:
        raise TypeError("track must be exact MotionTrack")
    registry = build_current_actuator_motion_identity_registry(
        authority=authority,
        structural_frame=structural_frame,
    )
    validate_track(
        track,
        current_mechanism_sha256=registry.mechanism_sha256,
        current_geometry_manifest_sha256=registry.source_geometry_manifest_sha256,
        current_identity_registry=registry,
    )
    if track.kind is not MotionKind.ACTUATOR:
        raise MotionIdentitySourceError("current controlled source only authorizes ACTUATOR motion")
    return registry


def validate_repository_actuator_motion_track(track: MotionTrack) -> MotionIdentityRegistry:
    """Validate an actuator track against a fresh repository-rooted authority rebuild."""

    if type(track) is not MotionTrack:
        raise TypeError("track must be exact MotionTrack")
    registry = build_repository_actuator_motion_identity_registry()
    validate_track(
        track,
        current_mechanism_sha256=registry.mechanism_sha256,
        current_geometry_manifest_sha256=registry.source_geometry_manifest_sha256,
        current_identity_registry=registry,
    )
    if track.kind is not MotionKind.ACTUATOR:
        raise MotionIdentitySourceError("repository controlled source only authorizes ACTUATOR motion")
    return registry
