import math

import pytest

from masck_one.digital_motion import (
    EvidenceStatus,
    InterpolationPolicy,
    MotionIdentityBinding,
    MotionIdentityRegistry,
    MotionKind,
    MotionTrack,
    RotationConvention,
    TransformKeyframe,
    interpolate_keyframes,
    rotation_matrix_xyz,
    validate_track,
)

SHA = "1" * 64
OTHER = "2" * 64
GEOMETRY_SHA = "3" * 64
OTHER_GEOMETRY_SHA = "4" * 64
HUGE_POS = 10**10000
HUGE_NEG = -HUGE_POS


def k(t, x=0.0):
    return TransformKeyframe(t, (x, 0.0, 0.0), (0.0, 0.0, 0.0))


def registry(**kw):
    values = dict(
        mechanism_sha256=SHA,
        source_geometry_manifest_sha256=GEOMETRY_SHA,
        bindings=(
            MotionIdentityBinding("RELEASE_CARRIAGE", "ROOT", (MotionKind.QUICK_RELEASE,)),
            MotionIdentityBinding("ACTUATOR_FOREHEAD", "ACTUATOR_FRAME", (MotionKind.ACTUATOR,)),
            MotionIdentityBinding("SERVICE_CARTRIDGE", "SERVICE_FRAME", (MotionKind.SERVICE,)),
        ),
    )
    values.update(kw)
    return MotionIdentityRegistry(**values)


def track(**kw):
    current_registry = kw.pop("registry", None) or registry()
    values = dict(
        track_id="QR_RELEASE",
        component_id="RELEASE_CARRIAGE",
        frame_id="ROOT",
        kind=MotionKind.QUICK_RELEASE,
        mechanism_sha256=SHA,
        identity_registry_sha256=current_registry.registry_sha256,
        keyframes=(k(0), k(0.25, 4.0)),
    )
    values.update(kw)
    return MotionTrack(**values)


def validate(candidate, *, current_registry=None, mechanism_sha=SHA, geometry_sha=GEOMETRY_SHA):
    validate_track(
        candidate,
        current_mechanism_sha256=mechanism_sha,
        current_geometry_manifest_sha256=geometry_sha,
        current_identity_registry=current_registry or registry(),
    )


def test_valid_track_is_provenance_bound_and_deterministic():
    current_registry = registry()
    a = track(registry=current_registry)
    b = track(registry=current_registry)
    validate(a, current_registry=current_registry)
    assert a.manifest_sha256() == b.manifest_sha256()
    assert a.identity_registry_sha256 == current_registry.registry_sha256
    assert a.evidence_status is EvidenceStatus.CONTROLLED_DIGITAL_ONLY
    assert a.rotation_convention is RotationConvention.ACTIVE_RH_EXTRINSIC_XYZ
    assert a.interpolation_policy is InterpolationPolicy.LINEAR_TRANSLATION_SHORTEST_EULER


def test_registry_is_geometry_and_mechanism_provenance_bound():
    current_registry = registry()
    candidate = track(registry=current_registry)
    with pytest.raises(ValueError, match="registry mechanism"):
        validate(candidate, current_registry=current_registry, mechanism_sha=OTHER)
    with pytest.raises(ValueError, match="registry geometry"):
        validate(candidate, current_registry=current_registry, geometry_sha=OTHER_GEOMETRY_SHA)


def test_stale_track_registry_hash_fails_closed():
    current_registry = registry()
    stale_registry = registry(
        bindings=(
            MotionIdentityBinding("RELEASE_CARRIAGE", "ROOT", (MotionKind.QUICK_RELEASE,)),
            MotionIdentityBinding("ACTUATOR_FOREHEAD", "ACTUATOR_FRAME", (MotionKind.ACTUATOR,)),
        )
    )
    candidate = track(registry=stale_registry)
    with pytest.raises(ValueError, match="identity registry provenance"):
        validate(candidate, current_registry=current_registry)


def test_unknown_component_unknown_frame_and_cross_frame_misuse_fail_closed():
    current_registry = registry()
    with pytest.raises(ValueError, match="unknown motion component"):
        validate(track(registry=current_registry, component_id="FICTITIOUS_PART"), current_registry=current_registry)
    with pytest.raises(ValueError, match="unknown motion frame"):
        validate(track(registry=current_registry, frame_id="MARS"), current_registry=current_registry)
    with pytest.raises(ValueError, match="relationship is not registered"):
        validate(
            track(registry=current_registry, component_id="ACTUATOR_FOREHEAD", frame_id="ROOT", kind=MotionKind.ACTUATOR),
            current_registry=current_registry,
        )


def test_motion_kind_must_be_allowed_for_registered_component_frame_pair():
    current_registry = registry()
    with pytest.raises(ValueError, match="motion kind is not allowed"):
        validate(track(registry=current_registry, kind=MotionKind.SERVICE), current_registry=current_registry)


def test_registry_rejects_duplicate_or_mutable_bindings_and_kind_aliases():
    binding = MotionIdentityBinding("RELEASE_CARRIAGE", "ROOT", (MotionKind.QUICK_RELEASE,))
    with pytest.raises(TypeError):
        MotionIdentityRegistry(SHA, GEOMETRY_SHA, [binding])
    with pytest.raises(ValueError, match="unique"):
        MotionIdentityRegistry(SHA, GEOMETRY_SHA, (binding, binding))
    with pytest.raises(TypeError):
        MotionIdentityBinding("RELEASE_CARRIAGE", "ROOT", [MotionKind.QUICK_RELEASE])
    with pytest.raises(TypeError):
        MotionIdentityBinding("RELEASE_CARRIAGE", "ROOT", ("QUICK_RELEASE",))
    with pytest.raises(ValueError, match="duplicates"):
        MotionIdentityBinding("RELEASE_CARRIAGE", "ROOT", (MotionKind.QUICK_RELEASE, MotionKind.QUICK_RELEASE))


def test_registry_hash_is_deterministic_and_changes_with_binding_semantics():
    a = registry()
    b = registry()
    assert a.registry_sha256 == b.registry_sha256
    changed = registry(
        bindings=(
            MotionIdentityBinding("RELEASE_CARRIAGE", "ROOT", (MotionKind.QUICK_RELEASE, MotionKind.SERVICE)),
            MotionIdentityBinding("ACTUATOR_FOREHEAD", "ACTUATOR_FRAME", (MotionKind.ACTUATOR,)),
            MotionIdentityBinding("SERVICE_CARTRIDGE", "SERVICE_FRAME", (MotionKind.SERVICE,)),
        )
    )
    assert changed.registry_sha256 != a.registry_sha256


def test_stale_mechanism_fails_closed():
    current_registry = registry()
    with pytest.raises(ValueError, match="stale digital motion provenance"):
        validate(track(registry=current_registry, mechanism_sha256=OTHER), current_registry=current_registry)


def test_timeline_must_start_zero_and_be_strictly_increasing():
    with pytest.raises(ValueError):
        track(keyframes=(k(0.1), k(0.2)))
    with pytest.raises(ValueError):
        track(keyframes=(k(0), k(0)))


@pytest.mark.parametrize("bad", [True, "1", float("nan"), float("inf")])
def test_numeric_aliases_and_nonfinite_values_rejected(bad):
    with pytest.raises((TypeError, ValueError)):
        TransformKeyframe(bad, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))


@pytest.mark.parametrize(
    "huge",
    [pytest.param(HUGE_POS, id="huge-positive"), pytest.param(HUGE_NEG, id="huge-negative")],
)
def test_unrepresentable_exact_integer_time_fails_closed_without_raw_overflow(huge):
    with pytest.raises(ValueError, match="representable"):
        TransformKeyframe(huge, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))


@pytest.mark.parametrize("field", ["translation", "rotation"])
@pytest.mark.parametrize(
    "huge",
    [pytest.param(HUGE_POS, id="huge-positive"), pytest.param(HUGE_NEG, id="huge-negative")],
)
def test_unrepresentable_exact_integer_transform_fails_closed_without_raw_overflow(field, huge):
    translation = (huge, 0.0, 0.0) if field == "translation" else (0.0, 0.0, 0.0)
    rotation = (huge, 0.0, 0.0) if field == "rotation" else (0.0, 0.0, 0.0)
    with pytest.raises(ValueError, match="representable"):
        TransformKeyframe(0.0, translation, rotation)


def test_large_representable_translation_is_accepted_but_rotation_is_bounded():
    value = 10**300
    frame = TransformKeyframe(0, (value, 0, 0), (0, 360, 0))
    assert math.isfinite(frame.translation_mm[0])
    assert frame.translation_mm[0] == float(value)
    assert frame.rotation_deg_xyz == (0.0, 0.0, 0.0)
    with pytest.raises(ValueError, match="one declared turn"):
        TransformKeyframe(0, (0, 0, 0), (0, 361, 0))
    with pytest.raises(ValueError, match="one declared turn"):
        TransformKeyframe(0, (0, 0, 0), (0, -361, 0))


def test_signed_zero_regenerates_identically():
    current_registry = registry()
    assert track(registry=current_registry, keyframes=(k(0), k(1, -0.0))).manifest_sha256() == track(
        registry=current_registry, keyframes=(k(0), k(1, 0.0))
    ).manifest_sha256()


def test_rotation_aliases_canonicalize_before_provenance_hashing():
    current_registry = registry()
    zero = TransformKeyframe(0.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    full_turn = TransformKeyframe(0.0, (0.0, 0.0, 0.0), (360.0, -360.0, 0.0))
    positive_half_turn = TransformKeyframe(1.0, (0.0, 0.0, 0.0), (180.0, 0.0, 0.0))
    negative_half_turn = TransformKeyframe(1.0, (0.0, 0.0, 0.0), (-180.0, 0.0, 0.0))
    assert full_turn.rotation_deg_xyz == zero.rotation_deg_xyz
    assert positive_half_turn.rotation_deg_xyz == negative_half_turn.rotation_deg_xyz
    assert track(registry=current_registry, keyframes=(zero, positive_half_turn)).manifest_sha256() == track(
        registry=current_registry, keyframes=(full_turn, negative_half_turn)
    ).manifest_sha256()


def test_identity_aliases_rejected():
    for bad in ("root", " ROOT", "ROOT/LOCAL", "RÖÖT", ""):
        with pytest.raises(ValueError):
            track(frame_id=bad)


def test_hostile_str_subclass_rejected_at_all_provenance_boundaries():
    class LyingStr(str):
        def __eq__(self, other):
            return True

    current_registry = registry()
    candidate = track(registry=current_registry)
    with pytest.raises(TypeError):
        validate(candidate, current_registry=current_registry, mechanism_sha=LyingStr(OTHER))
    with pytest.raises(TypeError):
        validate(candidate, current_registry=current_registry, geometry_sha=LyingStr(OTHER_GEOMETRY_SHA))
    with pytest.raises(TypeError):
        track(registry=current_registry, mechanism_sha256=LyingStr(SHA))
    with pytest.raises(TypeError):
        MotionIdentityRegistry(LyingStr(SHA), GEOMETRY_SHA, current_registry.bindings)


def test_mutable_or_structural_aliases_rejected():
    with pytest.raises(TypeError):
        track(keyframes=[k(0), k(1)])

    class FakeTrack:
        mechanism_sha256 = SHA

    with pytest.raises(TypeError):
        validate(FakeTrack())
    with pytest.raises(TypeError):
        validate(track(), current_registry=object())


def test_rotation_and_interpolation_aliases_rejected():
    for bad in ("ACTIVE_RH_EXTRINSIC_XYZ", None, 1):
        with pytest.raises(TypeError):
            track(rotation_convention=bad)
    for bad in ("LINEAR_TRANSLATION_SHORTEST_EULER", None, 1):
        with pytest.raises(TypeError):
            track(interpolation_policy=bad)


def test_noncommuting_rotation_has_one_canonical_composition():
    matrix = rotation_matrix_xyz((0.0, 90.0, 90.0))
    expected = ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0), (-1.0, 0.0, 0.0))
    for row, reference in zip(matrix, expected):
        assert row == pytest.approx(reference, abs=1e-12)
    ex = tuple(row[0] for row in matrix)
    ey = tuple(row[1] for row in matrix)
    ez = tuple(row[2] for row in matrix)
    assert ex == pytest.approx((0.0, 0.0, -1.0), abs=1e-12)
    assert ey == pytest.approx((-1.0, 0.0, 0.0), abs=1e-12)
    assert ez == pytest.approx((0.0, 1.0, 0.0), abs=1e-12)


def test_rotation_helper_rejects_ambiguous_nonfinite_and_multi_turn_inputs():
    with pytest.raises(TypeError):
        rotation_matrix_xyz([0.0, 0.0, 0.0])
    with pytest.raises(TypeError):
        rotation_matrix_xyz((True, 0.0, 0.0))
    with pytest.raises(ValueError):
        rotation_matrix_xyz((float("nan"), 0.0, 0.0))
    with pytest.raises(ValueError, match="one declared turn"):
        rotation_matrix_xyz((1e300, 0.0, 0.0))
    full_turn = rotation_matrix_xyz((360.0, 0.0, 0.0))
    identity = rotation_matrix_xyz((0.0, 0.0, 0.0))
    for row, reference in zip(full_turn, identity):
        assert row == pytest.approx(reference, abs=1e-12)


def test_interpolation_crosses_wrap_by_shortest_path_and_has_deterministic_tie():
    a = TransformKeyframe(0.0, (0.0, 0.0, 0.0), (0.0, 0.0, 179.0))
    b = TransformKeyframe(1.0, (10.0, 0.0, 0.0), (0.0, 0.0, -179.0))
    mid = interpolate_keyframes(a, b, 0.5)
    assert mid.translation_mm == pytest.approx((5.0, 0.0, 0.0))
    assert mid.rotation_deg_xyz == pytest.approx((0.0, 0.0, -180.0))
    tie = interpolate_keyframes(
        TransformKeyframe(0.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
        TransformKeyframe(1.0, (0.0, 0.0, 0.0), (0.0, 0.0, 180.0)),
        0.5,
    )
    assert tie.rotation_deg_xyz[2] == pytest.approx(-90.0)


def test_full_turn_requires_explicit_intermediate_keyframes():
    direct_start = TransformKeyframe(0.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    direct_end = TransformKeyframe(1.0, (0.0, 0.0, 0.0), (0.0, 0.0, 360.0))
    assert direct_end.rotation_deg_xyz == direct_start.rotation_deg_xyz
    assert interpolate_keyframes(direct_start, direct_end, 0.5).rotation_deg_xyz[2] == 0.0
    frames = (
        TransformKeyframe(0.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
        TransformKeyframe(1.0, (0.0, 0.0, 0.0), (0.0, 0.0, 90.0)),
        TransformKeyframe(2.0, (0.0, 0.0, 0.0), (0.0, 0.0, 180.0)),
        TransformKeyframe(3.0, (0.0, 0.0, 0.0), (0.0, 0.0, -90.0)),
        TransformKeyframe(4.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
    )
    assert [interpolate_keyframes(a, b, 0.5).rotation_deg_xyz[2] for a, b in zip(frames, frames[1:])] == pytest.approx(
        [45.0, 135.0, -135.0, -45.0]
    )


def test_interpolation_rejects_invalid_alpha_and_preserves_endpoints():
    a = TransformKeyframe(0.0, (1.0, 2.0, 3.0), (10.0, 20.0, 30.0))
    b = TransformKeyframe(2.0, (4.0, 5.0, 6.0), (40.0, 50.0, 60.0))
    assert interpolate_keyframes(a, b, 0.0) == a
    assert interpolate_keyframes(a, b, 1.0) == b
    for bad in (-0.1, 1.1, float("nan"), True):
        with pytest.raises((TypeError, ValueError)):
            interpolate_keyframes(a, b, bad)


def test_manifest_changes_with_mechanism_registry_and_motion():
    current_registry = registry()
    assert track(registry=current_registry).manifest_sha256() != track(registry=current_registry, mechanism_sha256=OTHER).manifest_sha256()
    assert track(registry=current_registry).manifest_sha256() != track(registry=current_registry, identity_registry_sha256="5" * 64).manifest_sha256()
    assert track(registry=current_registry).manifest_sha256() != track(registry=current_registry, keyframes=(k(0), k(0.25, 4.1))).manifest_sha256()
