"""Controlled source factories for digital-motion identity registries.

This module closes a critical trust-boundary distinction: a registry digest is not
source authority by itself. Authoritative actuator-motion identity is reconstructed
from the current engineering authority and structural frame, then bound to the
canonical actuator-frame architecture produced by repository code.

No retention, quick-release, service, exploded-assembly or cleansing component is
invented here. Those motion kinds remain unavailable until an equivalent released
source object exists for them.
"""
from __future__ import annotations

from .actuator_frames import ZONE_IDS, build_actuator_frame_architecture
from .authority import Authority
from .digital_motion import (
    MotionIdentityBinding,
    MotionIdentityRegistry,
    MotionKind,
    MotionTrack,
    validate_track,
)
from .structural_frame import StructuralFrameTopology


class MotionIdentitySourceError(ValueError):
    """Raised when a motion identity cannot be derived from controlled current sources."""


def build_current_actuator_motion_identity_registry(
    *,
    authority: Authority,
    structural_frame: StructuralFrameTopology,
) -> MotionIdentityRegistry:
    """Rebuild the only currently source-backed actuator motion registry.

    The caller does not supply component IDs, frame IDs, allowed motion kinds, a
    mechanism SHA, or a geometry SHA. All of those values are derived from the
    current canonical actuator-frame architecture. Each actuator zone ID is also
    the stable identity of that zone's local frame until a more granular released
    frame registry exists.
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


def validate_current_actuator_motion_track(
    track: MotionTrack,
    *,
    authority: Authority,
    structural_frame: StructuralFrameTopology,
) -> MotionIdentityRegistry:
    """Validate an actuator track against a freshly reconstructed current registry.

    Returning the registry lets export code serialize the exact registry identity
    used for validation without accepting a caller-authored identity ledger.
    """

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
