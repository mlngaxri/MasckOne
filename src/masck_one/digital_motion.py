"""Deterministic, simulation-only motion semantics for digital consumers.

This module is a trust boundary, not physical evidence. It defines canonical IDs,
frames, rotation/interpolation semantics and provenance checks for Web/App motion.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
import re
from typing import Tuple

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


class MotionKind(str, Enum):
    FOUR_ZONE_CLEANSING = "FOUR_ZONE_CLEANSING"
    EXPLODED_ASSEMBLY = "EXPLODED_ASSEMBLY"
    ACTUATOR = "ACTUATOR"
    RETENTION_DON_DOFF = "RETENTION_DON_DOFF"
    QUICK_RELEASE = "QUICK_RELEASE"
    SERVICE = "SERVICE"


class EvidenceStatus(str, Enum):
    CONTROLLED_DIGITAL_ONLY = "CONTROLLED_DIGITAL_ONLY"


class RotationConvention(str, Enum):
    """Active RH fixed-axis X then Y then Z, column vectors: Rz @ Ry @ Rx."""

    ACTIVE_RH_EXTRINSIC_XYZ = "ACTIVE_RH_EXTRINSIC_XYZ"


class InterpolationPolicy(str, Enum):
    """Linear translation; shortest Euler component delta in [-180, 180), -180 tie."""

    LINEAR_TRANSLATION_SHORTEST_EULER = "LINEAR_TRANSLATION_SHORTEST_EULER"


def _exact_text(value: object, name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be exact built-in str")
    return value


def _canonical_id(value: object, name: str) -> str:
    text = _exact_text(value, name)
    if not _ID.fullmatch(text):
        raise ValueError(f"{name} must be canonical ASCII uppercase identifier")
    return text


def _sha(value: object, name: str = "mechanism_sha256") -> str:
    text = _exact_text(value, name)
    if not _SHA256.fullmatch(text):
        raise ValueError(f"{name} must be canonical lowercase SHA-256")
    return text


def _finite(value: object, name: str) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{name} must be exact int or float")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be representable as finite binary64") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return 0.0 if result == 0.0 else result


def _is_negative_zero(value: float) -> bool:
    return value == 0.0 and math.copysign(1.0, value) < 0.0


def _canonical_angle_deg(value: object, name: str = "rotation_deg_xyz") -> float:
    angle = _finite(value, name)
    if angle < -360.0 or angle > 360.0:
        raise ValueError(f"{name} must stay within one declared turn [-360, 360]")
    canonical = (angle + 180.0) % 360.0 - 180.0
    return 0.0 if canonical == 0.0 else canonical


def _shortest_angle_delta_deg(start: float, end: float) -> float:
    return _canonical_angle_deg(end - start, "rotation delta")


@dataclass(frozen=True)
class MotionIdentityBinding:
    component_id: str
    frame_id: str
    allowed_kinds: Tuple[MotionKind, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_id", _canonical_id(self.component_id, "component_id"))
        object.__setattr__(self, "frame_id", _canonical_id(self.frame_id, "frame_id"))
        if type(self.allowed_kinds) is not tuple or not self.allowed_kinds:
            raise TypeError("allowed_kinds must be exact nonempty tuple")
        if any(type(kind) is not MotionKind for kind in self.allowed_kinds):
            raise TypeError("allowed_kinds must contain exact MotionKind values")
        if len(set(self.allowed_kinds)) != len(self.allowed_kinds):
            raise ValueError("allowed_kinds must not contain duplicates")
        object.__setattr__(self, "allowed_kinds", tuple(sorted(self.allowed_kinds, key=lambda kind: kind.value)))

    def validate_invariants(self) -> None:
        _canonical_id(self.component_id, "component_id")
        _canonical_id(self.frame_id, "frame_id")
        if type(self.allowed_kinds) is not tuple or not self.allowed_kinds:
            raise TypeError("allowed_kinds must be exact nonempty tuple")
        if any(type(kind) is not MotionKind for kind in self.allowed_kinds):
            raise TypeError("allowed_kinds must contain exact MotionKind values")
        if len(set(self.allowed_kinds)) != len(self.allowed_kinds):
            raise ValueError("allowed_kinds must not contain duplicates")
        if self.allowed_kinds != tuple(sorted(self.allowed_kinds, key=lambda kind: kind.value)):
            raise ValueError("allowed_kinds must use canonical order")


@dataclass(frozen=True)
class MotionIdentityRegistry:
    """Digital identity registry bound to exact mechanism and geometry-manifest provenance."""

    mechanism_sha256: str
    source_geometry_manifest_sha256: str
    bindings: Tuple[MotionIdentityBinding, ...]
    evidence_status: EvidenceStatus = EvidenceStatus.CONTROLLED_DIGITAL_ONLY

    def __post_init__(self) -> None:
        object.__setattr__(self, "mechanism_sha256", _sha(self.mechanism_sha256))
        object.__setattr__(
            self,
            "source_geometry_manifest_sha256",
            _sha(self.source_geometry_manifest_sha256, "source_geometry_manifest_sha256"),
        )
        if type(self.evidence_status) is not EvidenceStatus:
            raise TypeError("evidence_status must be exact EvidenceStatus")
        if type(self.bindings) is not tuple or not self.bindings:
            raise TypeError("bindings must be exact nonempty tuple")
        if any(type(binding) is not MotionIdentityBinding for binding in self.bindings):
            raise TypeError("bindings must contain exact MotionIdentityBinding values")
        pairs = [(binding.component_id, binding.frame_id) for binding in self.bindings]
        if len(set(pairs)) != len(pairs):
            raise ValueError("component/frame bindings must be unique")
        object.__setattr__(self, "bindings", tuple(sorted(self.bindings, key=lambda item: (item.component_id, item.frame_id))))

    def validate_invariants(self) -> None:
        _sha(self.mechanism_sha256)
        _sha(self.source_geometry_manifest_sha256, "source_geometry_manifest_sha256")
        if type(self.evidence_status) is not EvidenceStatus:
            raise TypeError("evidence_status must be exact EvidenceStatus")
        if type(self.bindings) is not tuple or not self.bindings:
            raise TypeError("bindings must be exact nonempty tuple")
        if any(type(binding) is not MotionIdentityBinding for binding in self.bindings):
            raise TypeError("bindings must contain exact MotionIdentityBinding values")
        for binding in self.bindings:
            binding.validate_invariants()
        pairs = [(binding.component_id, binding.frame_id) for binding in self.bindings]
        if len(set(pairs)) != len(pairs):
            raise ValueError("component/frame bindings must be unique")
        if self.bindings != tuple(sorted(self.bindings, key=lambda item: (item.component_id, item.frame_id))):
            raise ValueError("component/frame bindings must use canonical order")

    @property
    def registry_sha256(self) -> str:
        self.validate_invariants()
        payload = {
            "schema": "MASCK_ONE_MOTION_IDENTITY_REGISTRY_V1",
            "mechanism_sha256": self.mechanism_sha256,
            "source_geometry_manifest_sha256": self.source_geometry_manifest_sha256,
            "evidence_status": self.evidence_status.value,
            "bindings": [
                {
                    "component_id": binding.component_id,
                    "frame_id": binding.frame_id,
                    "allowed_kinds": [kind.value for kind in binding.allowed_kinds],
                }
                for binding in self.bindings
            ],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class TransformKeyframe:
    t_s: float
    translation_mm: Tuple[float, float, float]
    rotation_deg_xyz: Tuple[float, float, float]

    def __post_init__(self) -> None:
        t_s = _finite(self.t_s, "t_s")
        if t_s < 0.0:
            raise ValueError("t_s must be nonnegative")
        if type(self.translation_mm) is not tuple or len(self.translation_mm) != 3:
            raise TypeError("translation_mm must be exact 3-tuple")
        if type(self.rotation_deg_xyz) is not tuple or len(self.rotation_deg_xyz) != 3:
            raise TypeError("rotation_deg_xyz must be exact 3-tuple")
        object.__setattr__(self, "t_s", t_s)
        object.__setattr__(self, "translation_mm", tuple(_finite(value, "translation_mm") for value in self.translation_mm))
        object.__setattr__(self, "rotation_deg_xyz", tuple(_canonical_angle_deg(value) for value in self.rotation_deg_xyz))

    def validate_invariants(self) -> None:
        if type(self.t_s) is not float or not math.isfinite(self.t_s) or self.t_s < 0.0:
            raise ValueError("stored t_s must be canonical nonnegative finite float")
        if _is_negative_zero(self.t_s):
            raise ValueError("stored t_s must canonicalize signed zero")
        if type(self.translation_mm) is not tuple or len(self.translation_mm) != 3:
            raise TypeError("translation_mm must be exact 3-tuple")
        if type(self.rotation_deg_xyz) is not tuple or len(self.rotation_deg_xyz) != 3:
            raise TypeError("rotation_deg_xyz must be exact 3-tuple")
        if any(type(value) is not float or not math.isfinite(value) for value in self.translation_mm):
            raise ValueError("stored translation_mm must contain canonical finite floats")
        if any(type(value) is not float or not math.isfinite(value) or not -180.0 <= value < 180.0 for value in self.rotation_deg_xyz):
            raise ValueError("stored rotation_deg_xyz must contain canonical angles in [-180,180)")
        if any(_is_negative_zero(value) for value in self.translation_mm + self.rotation_deg_xyz):
            raise ValueError("stored transform values must canonicalize signed zero")


@dataclass(frozen=True)
class MotionTrack:
    track_id: str
    component_id: str
    frame_id: str
    kind: MotionKind
    mechanism_sha256: str
    identity_registry_sha256: str
    keyframes: Tuple[TransformKeyframe, ...]
    evidence_status: EvidenceStatus = EvidenceStatus.CONTROLLED_DIGITAL_ONLY
    rotation_convention: RotationConvention = RotationConvention.ACTIVE_RH_EXTRINSIC_XYZ
    interpolation_policy: InterpolationPolicy = InterpolationPolicy.LINEAR_TRANSLATION_SHORTEST_EULER

    def __post_init__(self) -> None:
        object.__setattr__(self, "track_id", _canonical_id(self.track_id, "track_id"))
        object.__setattr__(self, "component_id", _canonical_id(self.component_id, "component_id"))
        object.__setattr__(self, "frame_id", _canonical_id(self.frame_id, "frame_id"))
        if type(self.kind) is not MotionKind:
            raise TypeError("kind must be exact MotionKind")
        if type(self.evidence_status) is not EvidenceStatus:
            raise TypeError("evidence_status must be exact EvidenceStatus")
        if type(self.rotation_convention) is not RotationConvention:
            raise TypeError("rotation_convention must be exact RotationConvention")
        if type(self.interpolation_policy) is not InterpolationPolicy:
            raise TypeError("interpolation_policy must be exact InterpolationPolicy")
        object.__setattr__(self, "mechanism_sha256", _sha(self.mechanism_sha256))
        object.__setattr__(self, "identity_registry_sha256", _sha(self.identity_registry_sha256, "identity_registry_sha256"))
        if type(self.keyframes) is not tuple:
            raise TypeError("keyframes must be exact tuple")
        if len(self.keyframes) < 2:
            raise ValueError("keyframes must contain at least two entries")
        if any(type(keyframe) is not TransformKeyframe for keyframe in self.keyframes):
            raise TypeError("keyframes must contain exact TransformKeyframe values")
        times = [keyframe.t_s for keyframe in self.keyframes]
        if times[0] != 0.0 or any(next_t <= previous_t for previous_t, next_t in zip(times, times[1:])):
            raise ValueError("keyframe time must start at zero and increase strictly")

    def validate_invariants(self) -> None:
        _canonical_id(self.track_id, "track_id")
        _canonical_id(self.component_id, "component_id")
        _canonical_id(self.frame_id, "frame_id")
        if type(self.kind) is not MotionKind:
            raise TypeError("kind must be exact MotionKind")
        if type(self.evidence_status) is not EvidenceStatus:
            raise TypeError("evidence_status must be exact EvidenceStatus")
        if type(self.rotation_convention) is not RotationConvention:
            raise TypeError("rotation_convention must be exact RotationConvention")
        if type(self.interpolation_policy) is not InterpolationPolicy:
            raise TypeError("interpolation_policy must be exact InterpolationPolicy")
        _sha(self.mechanism_sha256)
        _sha(self.identity_registry_sha256, "identity_registry_sha256")
        if type(self.keyframes) is not tuple or len(self.keyframes) < 2:
            raise TypeError("keyframes must be exact tuple with at least two entries")
        if any(type(keyframe) is not TransformKeyframe for keyframe in self.keyframes):
            raise TypeError("keyframes must contain exact TransformKeyframe values")
        for keyframe in self.keyframes:
            keyframe.validate_invariants()
        times = [keyframe.t_s for keyframe in self.keyframes]
        if times[0] != 0.0 or any(next_t <= previous_t for previous_t, next_t in zip(times, times[1:])):
            raise ValueError("keyframe time must start at zero and increase strictly")

    def _digest_unvalidated_context(self) -> str:
        """Hash internally valid content only; callers must not treat this as release validation."""
        self.validate_invariants()
        payload = {
            "schema": "MASCK_ONE_DIGITAL_MOTION_V5",
            "track_id": self.track_id,
            "component_id": self.component_id,
            "frame_id": self.frame_id,
            "kind": self.kind.value,
            "mechanism_sha256": self.mechanism_sha256,
            "identity_registry_sha256": self.identity_registry_sha256,
            "evidence_status": self.evidence_status.value,
            "rotation_convention": self.rotation_convention.value,
            "interpolation_policy": self.interpolation_policy.value,
            "rotation_semantics": {
                "handedness": "RIGHT_HANDED",
                "action": "ACTIVE",
                "axes": "EXTRINSIC_XYZ",
                "vector_convention": "COLUMN",
                "matrix_composition": "RZ_RY_RX",
                "angle_unit": "DEGREE",
                "declared_angle_input_interval": "[-360,360]",
                "angle_component_interval": "[-180,180)",
                "angle_delta_interval": "[-180,180)",
                "angle_180_tie": "NEGATIVE_180",
            },
            "keyframes": [
                {
                    "t_s": keyframe.t_s,
                    "translation_mm": keyframe.translation_mm,
                    "rotation_deg_xyz": keyframe.rotation_deg_xyz,
                }
                for keyframe in self.keyframes
            ],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
        return hashlib.sha256(raw).hexdigest()

    def manifest_sha256(self) -> str:
        """Return deterministic content digest; release consumers must first call validate_track()."""
        return self._digest_unvalidated_context()

    def validated_manifest_sha256(
        self,
        *,
        current_mechanism_sha256: str,
        current_geometry_manifest_sha256: str,
        current_identity_registry: MotionIdentityRegistry,
    ) -> str:
        """Return a digest only after current identity and geometry provenance is proven."""
        validate_track(
            self,
            current_mechanism_sha256=current_mechanism_sha256,
            current_geometry_manifest_sha256=current_geometry_manifest_sha256,
            current_identity_registry=current_identity_registry,
        )
        return self._digest_unvalidated_context()


def rotation_matrix_xyz(rotation_deg_xyz: Tuple[float, float, float]) -> Tuple[Tuple[float, float, float], ...]:
    """Return Rz @ Ry @ Rx for ACTIVE_RH_EXTRINSIC_XYZ."""
    if type(rotation_deg_xyz) is not tuple or len(rotation_deg_xyz) != 3:
        raise TypeError("rotation_deg_xyz must be exact 3-tuple")
    x_deg, y_deg, z_deg = (_canonical_angle_deg(value) for value in rotation_deg_xyz)
    x, y, z = (math.radians(value) for value in (x_deg, y_deg, z_deg))
    cx, sx = math.cos(x), math.sin(x)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(z), math.sin(z)
    return (
        (cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
        (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx),
        (-sy, cy * sx, cy * cx),
    )


def interpolate_keyframes(a: TransformKeyframe, b: TransformKeyframe, alpha: float) -> TransformKeyframe:
    if type(a) is not TransformKeyframe or type(b) is not TransformKeyframe:
        raise TypeError("a and b must be exact TransformKeyframe values")
    a.validate_invariants()
    b.validate_invariants()
    u = _finite(alpha, "alpha")
    if not 0.0 <= u <= 1.0:
        raise ValueError("alpha must be within [0,1]")
    if u == 0.0:
        return a
    if u == 1.0:
        return b
    translation = tuple(start + (end - start) * u for start, end in zip(a.translation_mm, b.translation_mm))
    rotation = tuple(
        start + _shortest_angle_delta_deg(start, end) * u
        for start, end in zip(a.rotation_deg_xyz, b.rotation_deg_xyz)
    )
    return TransformKeyframe(a.t_s + (b.t_s - a.t_s) * u, translation, rotation)


def validate_track(
    track: MotionTrack,
    *,
    current_mechanism_sha256: str,
    current_geometry_manifest_sha256: str,
    current_identity_registry: MotionIdentityRegistry,
) -> None:
    """Fail closed unless a track targets an allowed pair in the current registry."""
    if type(track) is not MotionTrack:
        raise TypeError("track must be exact MotionTrack")
    if type(current_identity_registry) is not MotionIdentityRegistry:
        raise TypeError("current_identity_registry must be exact MotionIdentityRegistry")
    track.validate_invariants()
    current_identity_registry.validate_invariants()
    mechanism_sha = _sha(current_mechanism_sha256)
    geometry_sha = _sha(current_geometry_manifest_sha256, "current_geometry_manifest_sha256")
    if current_identity_registry.mechanism_sha256 != mechanism_sha:
        raise ValueError("stale motion identity registry mechanism provenance")
    if current_identity_registry.source_geometry_manifest_sha256 != geometry_sha:
        raise ValueError("stale motion identity registry geometry provenance")
    if track.mechanism_sha256 != mechanism_sha:
        raise ValueError("stale digital motion provenance")
    if track.identity_registry_sha256 != current_identity_registry.registry_sha256:
        raise ValueError("stale digital motion identity registry provenance")
    components = {binding.component_id for binding in current_identity_registry.bindings}
    frames = {binding.frame_id for binding in current_identity_registry.bindings}
    if track.component_id not in components:
        raise ValueError("unknown motion component_id")
    if track.frame_id not in frames:
        raise ValueError("unknown motion frame_id")
    matching = tuple(
        binding
        for binding in current_identity_registry.bindings
        if binding.component_id == track.component_id and binding.frame_id == track.frame_id
    )
    if not matching:
        raise ValueError("component_id/frame_id relationship is not registered")
    if track.kind not in matching[0].allowed_kinds:
        raise ValueError("motion kind is not allowed for component_id/frame_id relationship")
