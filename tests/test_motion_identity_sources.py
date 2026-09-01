import pytest

from masck_one.actuator_frames import ZONE_IDS, build_actuator_frame_architecture
from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.digital_motion import MotionIdentityBinding, MotionIdentityRegistry, MotionKind, MotionTrack, TransformKeyframe
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.motion_identity_sources import (
    MotionIdentitySourceError,
    build_current_actuator_motion_identity_registry,
    validate_current_actuator_motion_track,
)
from masck_one.structural_frame import build_structural_frame_topology


def _current_sources():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    return model.authority, frame


def _track(registry, zone_id=ZONE_IDS[0], kind=MotionKind.ACTUATOR):
    return MotionTrack(
        track_id="ACTUATOR_TEST",
        component_id=zone_id,
        frame_id=zone_id,
        kind=kind,
        mechanism_sha256=registry.mechanism_sha256,
        identity_registry_sha256=registry.registry_sha256,
        keyframes=(
            TransformKeyframe(0.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
            TransformKeyframe(1.0, (0.1, 0.0, 0.0), (0.0, 0.0, 1.0)),
        ),
    )


def test_registry_is_rebuilt_from_current_actuator_architecture_without_caller_ids():
    authority, frame = _current_sources()
    registry = build_current_actuator_motion_identity_registry(authority=authority, structural_frame=frame)
    architecture = build_actuator_frame_architecture(authority, frame)

    assert registry.mechanism_sha256 == architecture.architecture_sha256
    assert registry.source_geometry_manifest_sha256 == architecture.architecture_sha256
    assert tuple(binding.component_id for binding in registry.bindings) == ZONE_IDS
    assert tuple(binding.frame_id for binding in registry.bindings) == ZONE_IDS
    assert all(binding.allowed_kinds == (MotionKind.ACTUATOR,) for binding in registry.bindings)


def test_current_actuator_track_validates_against_freshly_reconstructed_registry():
    authority, frame = _current_sources()
    registry = build_current_actuator_motion_identity_registry(authority=authority, structural_frame=frame)
    track = _track(registry)
    returned = validate_current_actuator_motion_track(track, authority=authority, structural_frame=frame)
    assert returned.registry_sha256 == registry.registry_sha256


def test_caller_authored_registry_cannot_substitute_for_controlled_current_source():
    authority, frame = _current_sources()
    current = build_current_actuator_motion_identity_registry(authority=authority, structural_frame=frame)
    forged = MotionIdentityRegistry(
        mechanism_sha256=current.mechanism_sha256,
        source_geometry_manifest_sha256=current.source_geometry_manifest_sha256,
        bindings=(
            MotionIdentityBinding("FICTITIOUS_PART", "FICTITIOUS_FRAME", (MotionKind.ACTUATOR,)),
        ),
    )
    forged_track = MotionTrack(
        track_id="FORGED",
        component_id="FICTITIOUS_PART",
        frame_id="FICTITIOUS_FRAME",
        kind=MotionKind.ACTUATOR,
        mechanism_sha256=forged.mechanism_sha256,
        identity_registry_sha256=forged.registry_sha256,
        keyframes=(
            TransformKeyframe(0.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
            TransformKeyframe(1.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
        ),
    )
    with pytest.raises(ValueError, match="identity registry provenance"):
        validate_current_actuator_motion_track(forged_track, authority=authority, structural_frame=frame)


def test_non_actuator_motion_remains_blocked_until_equivalent_controlled_source_exists():
    authority, frame = _current_sources()
    registry = build_current_actuator_motion_identity_registry(authority=authority, structural_frame=frame)
    with pytest.raises(ValueError, match="motion kind"):
        validate_current_actuator_motion_track(
            _track(registry, kind=MotionKind.QUICK_RELEASE),
            authority=authority,
            structural_frame=frame,
        )


def test_source_factory_rejects_structural_aliases_instead_of_duck_typing():
    authority, frame = _current_sources()

    class FakeFrame:
        reservations = frame.reservations

    with pytest.raises(TypeError, match="exact StructuralFrameTopology"):
        build_current_actuator_motion_identity_registry(authority=authority, structural_frame=FakeFrame())

    with pytest.raises(TypeError, match="exact Authority"):
        build_current_actuator_motion_identity_registry(authority=object(), structural_frame=frame)
