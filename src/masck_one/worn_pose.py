from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
import math
from typing import Iterable

from .authority import Authority
from .protected_volumes import PlanarProtectedZone, ProtectedVolumeSet
from .spatial import Point3, RigidTransform, Vector3


class WornPoseError(ValueError):
    """Raised when a worn-pose/misregistration state exceeds the current authority contract."""


@dataclass(frozen=True, slots=True)
class WornPoseLimits:
    translation_radial_max_mm: float
    rotation_max_deg: float
    z_translation_status: str = "NOT_DEFINED_BY_CURRENT_AUTHORITY_FIXED_ZERO"

    def __post_init__(self) -> None:
        radial = float(self.translation_radial_max_mm)
        rotation = float(self.rotation_max_deg)
        if not math.isfinite(radial) or radial < 0.0:
            raise WornPoseError("translation_radial_max_mm must be finite and non-negative")
        if not math.isfinite(rotation) or rotation < 0.0:
            raise WornPoseError("rotation_max_deg must be finite and non-negative")
        if self.z_translation_status != "NOT_DEFINED_BY_CURRENT_AUTHORITY_FIXED_ZERO":
            raise WornPoseError("Unexpected Z-translation policy")
        object.__setattr__(self, "translation_radial_max_mm", radial)
        object.__setattr__(self, "rotation_max_deg", rotation)

    @classmethod
    def from_authority(cls, authority: Authority) -> "WornPoseLimits":
        return cls(
            translation_radial_max_mm=authority.number("geometry", "misregistration", "translation_radial_max_mm"),
            rotation_max_deg=authority.number("geometry", "misregistration", "rotation_max_deg"),
        )


@dataclass(frozen=True, slots=True)
class WornPose:
    """Reference-anatomy pose relative to the nominal device coordinate frame.

    Translation is limited to canonical XY because the current machine authority defines
    a radial translation limit but does not define a separate Z donning offset. Z is
    therefore fixed to zero instead of being invented.

    Rotations use the repository-wide fixed/global extrinsic XYZ convention documented
    by `RigidTransform.from_extrinsic_xyz`.
    """

    translation_x_mm: float
    translation_y_mm: float
    roll_x_deg: float
    pitch_y_deg: float
    yaw_z_deg: float

    def __post_init__(self) -> None:
        for name in (
            "translation_x_mm",
            "translation_y_mm",
            "roll_x_deg",
            "pitch_y_deg",
            "yaw_z_deg",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value):
                raise WornPoseError(f"{name} must be finite")
            if abs(value) < 1e-14:
                value = 0.0
            object.__setattr__(self, name, value)

    @property
    def translation_radial_mm(self) -> float:
        return math.hypot(self.translation_x_mm, self.translation_y_mm)

    @property
    def translation_z_mm(self) -> float:
        return 0.0

    @property
    def transform(self) -> RigidTransform:
        return RigidTransform.from_extrinsic_xyz(
            Vector3(self.translation_x_mm, self.translation_y_mm, 0.0),
            roll_x_deg=self.roll_x_deg,
            pitch_y_deg=self.pitch_y_deg,
            yaw_z_deg=self.yaw_z_deg,
        )

    def validate_against(self, limits: WornPoseLimits, *, tolerance: float = 1e-10) -> None:
        if self.translation_radial_mm > limits.translation_radial_max_mm + tolerance:
            raise WornPoseError(
                f"Planar translation {self.translation_radial_mm:.9g} mm exceeds radial limit "
                f"{limits.translation_radial_max_mm:.9g} mm"
            )
        for name, value in (
            ("roll_x_deg", self.roll_x_deg),
            ("pitch_y_deg", self.pitch_y_deg),
            ("yaw_z_deg", self.yaw_z_deg),
        ):
            if abs(value) > limits.rotation_max_deg + tolerance:
                raise WornPoseError(
                    f"{name}={value:.9g} exceeds ±{limits.rotation_max_deg:.9g} deg"
                )

    def apply_point(self, point: Point3) -> Point3:
        return self.transform.apply_point(point)

    def signature_payload(self) -> tuple[float, float, float, float, float]:
        return (
            self.translation_x_mm,
            self.translation_y_mm,
            self.roll_x_deg,
            self.pitch_y_deg,
            self.yaw_z_deg,
        )


@dataclass(frozen=True, slots=True)
class PosedZoneBounds:
    zone_id: str
    pose_index: int
    min_x_mm: float
    max_x_mm: float
    min_y_mm: float
    max_y_mm: float
    min_z_mm: float
    max_z_mm: float

    @property
    def width_x_mm(self) -> float:
        return self.max_x_mm - self.min_x_mm

    @property
    def height_y_mm(self) -> float:
        return self.max_y_mm - self.min_y_mm


@dataclass(frozen=True, slots=True)
class WornPoseRegressionSet:
    limits: WornPoseLimits
    poses: tuple[WornPose, ...]
    radial_direction_count: int
    evidence_status: str = "DETERMINISTIC_DISCRETE_SCREEN_NOT_MEASURED_DONNING_DISTRIBUTION"

    def __post_init__(self) -> None:
        if self.radial_direction_count < 4:
            raise WornPoseError("radial_direction_count must be at least 4")
        if not self.poses:
            raise WornPoseError("WornPoseRegressionSet cannot be empty")
        if not self.evidence_status.strip():
            raise WornPoseError("evidence_status must be non-empty")
        signatures: set[tuple[float, float, float, float, float]] = set()
        for pose in self.poses:
            pose.validate_against(self.limits)
            signature = tuple(round(value, 12) for value in pose.signature_payload())
            if signature in signatures:
                raise WornPoseError(f"Duplicate deterministic pose {signature}")
            signatures.add(signature)

    @property
    def pose_count(self) -> int:
        return len(self.poses)

    @property
    def identity_pose_index(self) -> int:
        target = (0.0, 0.0, 0.0, 0.0, 0.0)
        for index, pose in enumerate(self.poses):
            if pose.signature_payload() == target:
                return index
        raise WornPoseError("Regression set has no identity pose")

    @property
    def maximum_sampled_radial_translation_mm(self) -> float:
        return max(pose.translation_radial_mm for pose in self.poses)

    @property
    def maximum_sampled_absolute_rotation_deg(self) -> float:
        return max(
            abs(value)
            for pose in self.poses
            for value in (pose.roll_x_deg, pose.pitch_y_deg, pose.yaw_z_deg)
        )

    @property
    def sha256(self) -> str:
        payload = {
            "limits": {
                "translation_radial_max_mm": self.limits.translation_radial_max_mm,
                "rotation_max_deg": self.limits.rotation_max_deg,
                "z_translation_status": self.limits.z_translation_status,
            },
            "radial_direction_count": self.radial_direction_count,
            "poses": [list(pose.signature_payload()) for pose in self.poses],
            "evidence_status": self.evidence_status,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self) -> dict[str, object]:
        return {
            "pose_count": self.pose_count,
            "radial_direction_count": self.radial_direction_count,
            "translation_radial_max_mm": self.limits.translation_radial_max_mm,
            "rotation_max_deg": self.limits.rotation_max_deg,
            "translation_z_mm": 0.0,
            "z_translation_status": self.limits.z_translation_status,
            "maximum_sampled_radial_translation_mm": self.maximum_sampled_radial_translation_mm,
            "maximum_sampled_absolute_rotation_deg": self.maximum_sampled_absolute_rotation_deg,
            "identity_pose_index": self.identity_pose_index,
            "sha256": self.sha256,
            "evidence_status": self.evidence_status,
        }


def _translation_states(radius_mm: float, radial_direction_count: int) -> tuple[tuple[float, float], ...]:
    if radial_direction_count < 4:
        raise WornPoseError("radial_direction_count must be at least 4")
    states: list[tuple[float, float]] = [(0.0, 0.0)]
    if radius_mm == 0.0:
        return tuple(states)
    for index in range(radial_direction_count):
        angle = 2.0 * math.pi * index / radial_direction_count
        x = radius_mm * math.cos(angle)
        y = radius_mm * math.sin(angle)
        if abs(x) < 1e-14:
            x = 0.0
        if abs(y) < 1e-14:
            y = 0.0
        states.append((x, y))
    return tuple(states)


def generate_hard_envelope_regression_set(
    authority: Authority,
    *,
    radial_direction_count: int = 16,
) -> WornPoseRegressionSet:
    """Generate deterministic boundary/interior samples for continuous authority limits.

    This is a regression screen, not a mathematical proof over the full continuous pose
    domain and not the later Monte Carlo model based on measured donning distributions.
    """

    limits = WornPoseLimits.from_authority(authority)
    translations = _translation_states(limits.translation_radial_max_mm, radial_direction_count)
    rotation_states = (-limits.rotation_max_deg, 0.0, limits.rotation_max_deg)

    poses: list[WornPose] = []
    for tx, ty in translations:
        for roll, pitch, yaw in itertools.product(rotation_states, repeat=3):
            pose = WornPose(tx, ty, roll, pitch, yaw)
            pose.validate_against(limits)
            poses.append(pose)

    return WornPoseRegressionSet(limits, tuple(poses), radial_direction_count)


def protected_zone_boundary_points(
    zone: PlanarProtectedZone,
    *,
    samples: int = 32,
    z_reference_mm: float = 0.0,
) -> tuple[Point3, ...]:
    """Sample one neutral protected-zone boundary for deterministic transform regression.

    The Z reference is only a mathematical transform plane. Because Iteration-7 volumes
    are unbounded in Z, these samples must not be interpreted as their actual 3D boundary.
    """

    if samples < 8:
        raise WornPoseError("Protected-zone boundary sampling requires at least 8 points")
    if not math.isfinite(float(z_reference_mm)):
        raise WornPoseError("z_reference_mm must be finite")

    a = zone.envelope_width_mm / 2.0
    b = zone.envelope_height_mm / 2.0
    zone_angle = math.radians(zone.angle_deg)
    c_zone, s_zone = math.cos(zone_angle), math.sin(zone_angle)
    points: list[Point3] = []
    for index in range(samples):
        theta = 2.0 * math.pi * index / samples
        x_local = a * math.cos(theta)
        y_local = b * math.sin(theta)
        x = zone.center.x + c_zone * x_local - s_zone * y_local
        y = zone.center.y + s_zone * x_local + c_zone * y_local
        points.append(Point3(x, y, float(z_reference_mm)))
    return tuple(points)


def posed_zone_bounds(
    zone: PlanarProtectedZone,
    pose: WornPose,
    *,
    pose_index: int = 0,
    boundary_samples: int = 32,
) -> PosedZoneBounds:
    points = [pose.apply_point(point) for point in protected_zone_boundary_points(zone, samples=boundary_samples)]
    return PosedZoneBounds(
        zone_id=zone.zone_id,
        pose_index=pose_index,
        min_x_mm=min(point.x for point in points),
        max_x_mm=max(point.x for point in points),
        min_y_mm=min(point.y for point in points),
        max_y_mm=max(point.y for point in points),
        min_z_mm=min(point.z for point in points),
        max_z_mm=max(point.z for point in points),
    )


def protected_zone_regression_bounds(
    protected: ProtectedVolumeSet,
    regression: WornPoseRegressionSet,
    *,
    boundary_samples: int = 32,
) -> tuple[PosedZoneBounds, ...]:
    return tuple(
        posed_zone_bounds(volume.zone, pose, pose_index=pose_index, boundary_samples=boundary_samples)
        for pose_index, pose in enumerate(regression.poses)
        for volume in protected.all
    )
