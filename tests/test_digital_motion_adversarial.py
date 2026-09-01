import math

import pytest

from masck_one.digital_motion import (
    EvidenceStatus,
    MotionIdentityBinding,
    MotionIdentityRegistry,
    MotionKind,
    MotionTrack,
    TransformKeyframe,
    validate_track,
)

SHA = "1" * 64
GEOMETRY_SHA = "3" * 64


def _binding(component, frame, *kinds):
    return MotionIdentityBinding(component, frame, tuple(kinds))


def _registry():
    return MotionIdentityRegistry(
        SHA,
        GEOMETRY_SHA,
        (
            _binding("RELEASE_CARRIAGE", "ROOT", MotionKind.QUICK_RELEASE, MotionKind.SERVICE),
            _binding("ACTUATOR_FOREHEAD", "ACTUATOR_FRAME", MotionKind.ACTUATOR),
        ),
    )


def _track(registry):
    return MotionTrack(
        "QR_RELEASE",
        "RELEASE_CARRIAGE",
        "ROOT",
        MotionKind.QUICK_RELEASE,
        SHA,
        registry.registry_sha256,
        (
            TransformKeyframe(0.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
            TransformKeyframe(1.0, (1.0, 0.0, 0.0), (0.0, 0.0, 10.0)),
        ),
    )


def _validate(track, registry):
    validate_track(
        track,
        current_mechanism_sha256=SHA,
        current_geometry_manifest_sha256=GEOMETRY_SHA,
        current_identity_registry=registry,
    )


def test_registry_hash_is_semantic_order_invariant():
    first = MotionIdentityRegistry(
        SHA,
        GEOMETRY_SHA,
        (
            _binding("RELEASE_CARRIAGE", "ROOT", MotionKind.SERVICE, MotionKind.QUICK_RELEASE),
            _binding("ACTUATOR_FOREHEAD", "ACTUATOR_FRAME", MotionKind.ACTUATOR),
        ),
    )
    second = MotionIdentityRegistry(
        SHA,
        GEOMETRY_SHA,
        (
            _binding("ACTUATOR_FOREHEAD", "ACTUATOR_FRAME", MotionKind.ACTUATOR),
            _binding("RELEASE_CARRIAGE", "ROOT", MotionKind.QUICK_RELEASE, MotionKind.SERVICE),
        ),
    )
    assert first.bindings == second.bindings
    assert first.registry_sha256 == second.registry_sha256


def test_postconstruction_registry_corruption_cannot_mint_hash_or_validate_track():
    registry = _registry()
    track = _track(registry)
    object.__setattr__(registry, "bindings", registry.bindings[::-1])
    with pytest.raises(ValueError, match="canonical order"):
        _ = registry.registry_sha256
    with pytest.raises(ValueError, match="canonical order"):
        _validate(track, registry)


def test_postconstruction_track_evidence_promotion_cannot_hash_or_validate():
    registry = _registry()
    track = _track(registry)
    object.__setattr__(track, "evidence_status", "CONTROLLED_DIGITAL_ONLY")
    with pytest.raises(TypeError, match="EvidenceStatus"):
        track.manifest_sha256()
    with pytest.raises(TypeError, match="EvidenceStatus"):
        _validate(track, registry)


def test_postconstruction_keyframe_corruption_cannot_hash_interpolate_or_validate():
    registry = _registry()
    track = _track(registry)
    corrupted = track.keyframes[1]
    object.__setattr__(corrupted, "rotation_deg_xyz", (0.0, 0.0, 181.0))
    with pytest.raises(ValueError, match="canonical angles"):
        track.manifest_sha256()
    with pytest.raises(ValueError, match="canonical angles"):
        _validate(track, registry)


def test_postconstruction_negative_zero_time_cannot_change_provenance_encoding():
    registry = _registry()
    track = _track(registry)
    first = track.keyframes[0]
    object.__setattr__(first, "t_s", -0.0)
    assert first.t_s == 0.0 and math.copysign(1.0, first.t_s) < 0.0
    with pytest.raises(ValueError, match="signed zero"):
        track.manifest_sha256()
    with pytest.raises(ValueError, match="signed zero"):
        _validate(track, registry)


def test_postconstruction_registry_evidence_promotion_cannot_hash_or_validate():
    registry = _registry()
    track = _track(registry)
    object.__setattr__(registry, "evidence_status", EvidenceStatus.CONTROLLED_DIGITAL_ONLY.value)
    with pytest.raises(TypeError, match="EvidenceStatus"):
        _ = registry.registry_sha256
    with pytest.raises(TypeError, match="EvidenceStatus"):
        _validate(track, registry)


def test_postconstruction_registered_pair_kind_corruption_fails_before_consume():
    registry = _registry()
    track = _track(registry)
    binding = next(item for item in registry.bindings if item.component_id == "RELEASE_CARRIAGE")
    object.__setattr__(binding, "allowed_kinds", (MotionKind.SERVICE, MotionKind.QUICK_RELEASE))
    with pytest.raises(ValueError, match="canonical order"):
        _ = registry.registry_sha256
    with pytest.raises(ValueError, match="canonical order"):
        _validate(track, registry)
