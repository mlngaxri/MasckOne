"""Controlled source factories and authority gates for digital actuator motion.

A motion identity registry proves only that a component/frame/kind relationship exists
in the current engineering source graph. It does not prove that arbitrary transform
keyframes are mechanically meaningful, collision-free, frequency-correct or physically
validated.

Repository-rooted identity validation therefore remains intentionally separate from
spatial-trajectory authority. The latter fails closed until actuator placement, local
axis, mount datum, envelope and sweep readiness exist, and until a dedicated transform
mapping binds keyframes to released displacement and timing semantics.

No retention, quick-release, service, exploded-assembly or cleansing component is
invented here. Those motion kinds remain unavailable until equivalent controlled
source objects exist for them.
"""
from __future__ import annotations

from .actuation_sweep_contract import (
    ActuationSweepContractError,
    build_actuation_displacement_contract,
)
from .actuator_frames import (
    ZONE_IDS,
    ActuatorFrameArchitecture,
    build_actuator_frame_architecture,
)
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
    """Raised when controlled identity or trajectory-authority boundaries are violated."""


def _registry_from_architecture(architecture: ActuatorFrameArchitecture) -> MotionIdentityRegistry:
    if type(architecture) is not ActuatorFrameArchitecture:
        raise TypeError("architecture must be exact ActuatorFrameArchitecture")
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


def build_current_actuator_motion_identity_registry(
    *,
    authority: Authority,
    structural_frame: StructuralFrameTopology,
) -> MotionIdentityRegistry:
    """Derive actuator identity only from supplied exact current engineering sources.

    The caller cannot supply IDs, kinds or provenance hashes. Release/export code should
    prefer :func:`build_repository_actuator_motion_identity_registry` so even the source
    objects cannot be substituted by a caller.
    """

    if type(authority) is not Authority:
        raise TypeError("authority must be exact Authority")
    if type(structural_frame) is not StructuralFrameTopology:
        raise TypeError("structural_frame must be exact StructuralFrameTopology")
    architecture = build_actuator_frame_architecture(authority, structural_frame)
    architecture.validate_current_sources(structural_frame=structural_frame, authority=authority)
    return _registry_from_architecture(architecture)


def _build_repository_actuator_sources() -> tuple[
    Authority,
    StructuralFrameTopology,
    ActuatorFrameArchitecture,
    MotionIdentityRegistry,
]:
    """Reconstruct the canonical repository source chain once for release-bound checks."""

    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    structural_frame = build_structural_frame_topology(model.authority, attachment)
    architecture = build_actuator_frame_architecture(model.authority, structural_frame)
    architecture.validate_current_sources(structural_frame=structural_frame, authority=model.authority)
    registry = _registry_from_architecture(architecture)
    return model.authority, structural_frame, architecture, registry


def build_repository_actuator_motion_identity_registry() -> MotionIdentityRegistry:
    """Rebuild actuator component/frame/kind identity from repository engineering truth.

    This function authenticates identity relationships only. It does not authorize the
    numerical keyframes of any :class:`MotionTrack` as a physical or collision-valid
    actuator trajectory.
    """

    _, _, _, registry = _build_repository_actuator_sources()
    return registry


def _validate_identity_against_registry(track: MotionTrack, registry: MotionIdentityRegistry) -> None:
    if type(track) is not MotionTrack:
        raise TypeError("track must be exact MotionTrack")
    if type(registry) is not MotionIdentityRegistry:
        raise TypeError("registry must be exact MotionIdentityRegistry")
    validate_track(
        track,
        current_mechanism_sha256=registry.mechanism_sha256,
        current_geometry_manifest_sha256=registry.source_geometry_manifest_sha256,
        current_identity_registry=registry,
    )
    if track.kind is not MotionKind.ACTUATOR:
        raise MotionIdentitySourceError("controlled actuator source only authorizes ACTUATOR identity")


def validate_current_actuator_motion_identity(
    track: MotionTrack,
    *,
    authority: Authority,
    structural_frame: StructuralFrameTopology,
) -> MotionIdentityRegistry:
    """Validate only actuator component/frame/kind identity against supplied current sources.

    Successful return is not trajectory authority. Keyframe displacement, direction,
    rotation, timing, frequency and collision behavior remain unproven by this API.
    """

    registry = build_current_actuator_motion_identity_registry(
        authority=authority,
        structural_frame=structural_frame,
    )
    _validate_identity_against_registry(track, registry)
    return registry


def validate_repository_actuator_motion_identity(track: MotionTrack) -> MotionIdentityRegistry:
    """Validate only actuator identity against a fresh repository-rooted source rebuild.

    This is safe for choosing which digital component/frame namespace a visualization
    track belongs to. It must never be interpreted as approval of the track's numerical
    transforms or timing.
    """

    _, _, _, registry = _build_repository_actuator_sources()
    _validate_identity_against_registry(track, registry)
    return registry


def require_repository_actuator_spatial_trajectory_authority(track: MotionTrack) -> None:
    """Fail closed unless an actuator transform track has full mechanical authority.

    Identity is checked first. The current repository then reconstructs the authoritative
    displacement contract and requires complete actuator sweep readiness. Today the
    released actuator-frame architecture deliberately leaves origins, azimuths, mount
    datums and supplier envelopes unresolved, so this gate must fail.

    Even after geometry becomes sweep-ready, a generic MotionTrack remains insufficient:
    a future dedicated trajectory binding must prove the mapping from displacement to a
    local transform axis plus CLEAN frequency/phase/timing semantics and collision/sweep
    provenance. Until that contract exists, no actuator transform digest is release-
    consumable as mechanically authoritative motion.
    """

    authority, structural_frame, architecture, registry = _build_repository_actuator_sources()
    _validate_identity_against_registry(track, registry)
    displacement = build_actuation_displacement_contract(authority, architecture)
    try:
        displacement.require_geometry_ready(
            authority=authority,
            architecture=architecture,
            structural_frame=structural_frame,
        )
    except ActuationSweepContractError as exc:
        raise MotionIdentitySourceError(
            "actuator spatial trajectory authority is blocked by unresolved geometry/sweep readiness"
        ) from exc
    raise MotionIdentitySourceError(
        "actuator spatial trajectory authority requires a released displacement-axis and frequency/timing binding; "
        "generic MotionTrack keyframes are visualization data only"
    )


def validate_current_actuator_motion_track(
    track: MotionTrack,
    *,
    authority: Authority,
    structural_frame: StructuralFrameTopology,
) -> MotionIdentityRegistry:
    """Retired ambiguous API. Use the explicit identity or trajectory-authority gate."""

    if type(track) is not MotionTrack:
        raise TypeError("track must be exact MotionTrack")
    if type(authority) is not Authority:
        raise TypeError("authority must be exact Authority")
    if type(structural_frame) is not StructuralFrameTopology:
        raise TypeError("structural_frame must be exact StructuralFrameTopology")
    raise MotionIdentitySourceError(
        "validate_current_actuator_motion_track is retired because identity validation does not prove trajectory authority; "
        "use validate_current_actuator_motion_identity"
    )


def validate_repository_actuator_motion_track(track: MotionTrack) -> MotionIdentityRegistry:
    """Retired ambiguous API. Use the explicit identity or trajectory-authority gate."""

    if type(track) is not MotionTrack:
        raise TypeError("track must be exact MotionTrack")
    raise MotionIdentitySourceError(
        "validate_repository_actuator_motion_track is retired because identity validation does not prove trajectory authority; "
        "use validate_repository_actuator_motion_identity or require_repository_actuator_spatial_trajectory_authority"
    )
