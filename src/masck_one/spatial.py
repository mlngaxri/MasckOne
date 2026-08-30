from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

from .authority import Authority


class SpatialContractError(ValueError):
    """Raised when a point, vector, transform, or datum violates the spatial contract."""


_EPS = 1e-12
_ORTHONORMAL_TOL = 1e-9


def _finite(value: float, *, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise SpatialContractError(f"{label} must be finite, got {value!r}")
    return result


def _sequence(values: Sequence[float] | Iterable[float], count: int, *, label: str) -> tuple[float, ...]:
    items = tuple(values)
    if len(items) != count:
        raise SpatialContractError(f"{label} must contain exactly {count} values, got {len(items)}")
    return tuple(_finite(value, label=f"{label}[{index}]") for index, value in enumerate(items))


@dataclass(frozen=True, slots=True)
class Point2:
    """A point in a named XY plane, expressed in millimetres unless otherwise documented."""

    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite(self.x, label="Point2.x"))
        object.__setattr__(self, "y", _finite(self.y, label="Point2.y"))

    @classmethod
    def from_pair(cls, values: Sequence[float] | Iterable[float]) -> "Point2":
        x, y = _sequence(values, 2, label="Point2")
        return cls(x, y)

    def as_tuple(self) -> tuple[float, float]:
        return self.x, self.y

    def with_z(self, z: float = 0.0) -> "Point3":
        return Point3(self.x, self.y, z)

    def mirrored_across_sagittal(self) -> "Point2":
        return Point2(-self.x, self.y)


@dataclass(frozen=True, slots=True)
class Vector3:
    """A free vector in the Masck One right-handed Cartesian convention."""

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite(self.x, label="Vector3.x"))
        object.__setattr__(self, "y", _finite(self.y, label="Vector3.y"))
        object.__setattr__(self, "z", _finite(self.z, label="Vector3.z"))

    @classmethod
    def from_triple(cls, values: Sequence[float] | Iterable[float]) -> "Vector3":
        x, y, z = _sequence(values, 3, label="Vector3")
        return cls(x, y, z)

    def as_tuple(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z

    def __add__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __neg__(self) -> "Vector3":
        return Vector3(-self.x, -self.y, -self.z)

    def scaled(self, factor: float) -> "Vector3":
        factor = _finite(factor, label="scale factor")
        return Vector3(self.x * factor, self.y * factor, self.z * factor)

    def dot(self, other: "Vector3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vector3") -> "Vector3":
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def norm(self) -> float:
        return math.sqrt(self.dot(self))

    def normalized(self) -> "Vector3":
        magnitude = self.norm()
        if magnitude <= _EPS:
            raise SpatialContractError("Cannot normalize a zero-length vector")
        return self.scaled(1.0 / magnitude)

    def is_close(self, other: "Vector3", *, abs_tol: float = _ORTHONORMAL_TOL) -> bool:
        return all(
            math.isclose(a, b, rel_tol=0.0, abs_tol=abs_tol)
            for a, b in zip(self.as_tuple(), other.as_tuple(), strict=True)
        )


@dataclass(frozen=True, slots=True)
class Point3:
    """A Cartesian point in millimetres in whichever datum frame is stated by the caller."""

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite(self.x, label="Point3.x"))
        object.__setattr__(self, "y", _finite(self.y, label="Point3.y"))
        object.__setattr__(self, "z", _finite(self.z, label="Point3.z"))

    @classmethod
    def from_triple(cls, values: Sequence[float] | Iterable[float]) -> "Point3":
        x, y, z = _sequence(values, 3, label="Point3")
        return cls(x, y, z)

    def as_tuple(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z

    def translated(self, vector: Vector3) -> "Point3":
        return Point3(self.x + vector.x, self.y + vector.y, self.z + vector.z)

    def vector_to(self, other: "Point3") -> Vector3:
        return Vector3(other.x - self.x, other.y - self.y, other.z - self.z)

    def mirrored_across_sagittal(self) -> "Point3":
        return Point3(-self.x, self.y, self.z)

    def is_close(self, other: "Point3", *, abs_tol: float = _ORTHONORMAL_TOL) -> bool:
        return all(
            math.isclose(a, b, rel_tol=0.0, abs_tol=abs_tol)
            for a, b in zip(self.as_tuple(), other.as_tuple(), strict=True)
        )


@dataclass(frozen=True, slots=True)
class Matrix3:
    """Immutable 3x3 matrix used only for deterministic spatial transforms."""

    rows: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]

    def __post_init__(self) -> None:
        raw_rows = tuple(self.rows)
        if len(raw_rows) != 3:
            raise SpatialContractError("Matrix3 must contain exactly three rows")
        normalized_rows: list[tuple[float, float, float]] = []
        for row_index, row in enumerate(raw_rows):
            values = _sequence(row, 3, label=f"Matrix3.row[{row_index}]")
            normalized_rows.append((values[0], values[1], values[2]))
        object.__setattr__(self, "rows", tuple(normalized_rows))

    @classmethod
    def identity(cls) -> "Matrix3":
        return cls(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))

    @classmethod
    def from_columns(cls, x: Vector3, y: Vector3, z: Vector3) -> "Matrix3":
        return cls(((x.x, y.x, z.x), (x.y, y.y, z.y), (x.z, y.z, z.z)))

    @classmethod
    def rotation_x(cls, angle_deg: float) -> "Matrix3":
        angle = math.radians(_finite(angle_deg, label="rotation_x angle_deg"))
        c, s = math.cos(angle), math.sin(angle)
        return cls(((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c)))

    @classmethod
    def rotation_y(cls, angle_deg: float) -> "Matrix3":
        angle = math.radians(_finite(angle_deg, label="rotation_y angle_deg"))
        c, s = math.cos(angle), math.sin(angle)
        return cls(((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c)))

    @classmethod
    def rotation_z(cls, angle_deg: float) -> "Matrix3":
        angle = math.radians(_finite(angle_deg, label="rotation_z angle_deg"))
        c, s = math.cos(angle), math.sin(angle)
        return cls(((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0)))

    def apply_vector(self, vector: Vector3) -> Vector3:
        values = vector.as_tuple()
        return Vector3(
            sum(self.rows[0][i] * values[i] for i in range(3)),
            sum(self.rows[1][i] * values[i] for i in range(3)),
            sum(self.rows[2][i] * values[i] for i in range(3)),
        )

    def multiply(self, other: "Matrix3") -> "Matrix3":
        columns = tuple(zip(*other.rows, strict=True))
        rows = []
        for row in self.rows:
            rows.append(tuple(sum(row[k] * column[k] for k in range(3)) for column in columns))
        return Matrix3(tuple(rows))

    def transpose(self) -> "Matrix3":
        return Matrix3(tuple(tuple(self.rows[j][i] for j in range(3)) for i in range(3)))

    def determinant(self) -> float:
        a, b, c = self.rows[0]
        d, e, f = self.rows[1]
        g, h, i = self.rows[2]
        return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)

    def is_rotation(self, *, abs_tol: float = _ORTHONORMAL_TOL) -> bool:
        product = self.transpose().multiply(self)
        identity = Matrix3.identity()
        orthonormal = all(
            math.isclose(product.rows[r][c], identity.rows[r][c], rel_tol=0.0, abs_tol=abs_tol)
            for r in range(3)
            for c in range(3)
        )
        return orthonormal and math.isclose(self.determinant(), 1.0, rel_tol=0.0, abs_tol=abs_tol)


@dataclass(frozen=True, slots=True)
class RigidTransform:
    """Right-handed rigid transform mapping source-frame coordinates to destination coordinates."""

    rotation: Matrix3
    translation: Vector3

    def __post_init__(self) -> None:
        if not self.rotation.is_rotation():
            raise SpatialContractError("RigidTransform rotation must be orthonormal and right-handed")

    @classmethod
    def identity(cls) -> "RigidTransform":
        return cls(Matrix3.identity(), Vector3(0.0, 0.0, 0.0))

    @classmethod
    def from_translation(cls, translation: Vector3) -> "RigidTransform":
        return cls(Matrix3.identity(), translation)

    @classmethod
    def from_extrinsic_xyz(
        cls,
        translation: Vector3,
        *,
        roll_x_deg: float = 0.0,
        pitch_y_deg: float = 0.0,
        yaw_z_deg: float = 0.0,
    ) -> "RigidTransform":
        """Build an implementation-convention pose using fixed/global X, then Y, then Z rotations.

        The resulting matrix is Rz(yaw) * Ry(pitch) * Rx(roll). This is a software
        convention for deterministic pose composition, not a promoted product requirement.
        """

        rotation = (
            Matrix3.rotation_z(yaw_z_deg)
            .multiply(Matrix3.rotation_y(pitch_y_deg))
            .multiply(Matrix3.rotation_x(roll_x_deg))
        )
        return cls(rotation, translation)

    def apply_vector(self, vector: Vector3) -> Vector3:
        return self.rotation.apply_vector(vector)

    def apply_point(self, point: Point3) -> Point3:
        rotated = self.rotation.apply_vector(Vector3(point.x, point.y, point.z))
        return Point3(
            rotated.x + self.translation.x,
            rotated.y + self.translation.y,
            rotated.z + self.translation.z,
        )

    def inverse(self) -> "RigidTransform":
        inverse_rotation = self.rotation.transpose()
        inverse_translation = inverse_rotation.apply_vector(-self.translation)
        return RigidTransform(inverse_rotation, inverse_translation)

    def followed_by(self, next_transform: "RigidTransform") -> "RigidTransform":
        """Return the transform obtained by applying self, then next_transform."""

        rotation = next_transform.rotation.multiply(self.rotation)
        rotated_translation = next_transform.rotation.apply_vector(self.translation)
        translation = rotated_translation + next_transform.translation
        return RigidTransform(rotation, translation)


@dataclass(frozen=True, slots=True)
class DatumFrame:
    """Named right-handed orthonormal frame expressed in global Masck One coordinates."""

    name: str
    origin: Point3
    x_axis: Vector3
    y_axis: Vector3
    z_axis: Vector3

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise SpatialContractError("DatumFrame.name must be non-empty")
        rotation = Matrix3.from_columns(self.x_axis, self.y_axis, self.z_axis)
        if not rotation.is_rotation():
            raise SpatialContractError(f"Datum frame {self.name!r} axes must be orthonormal and right-handed")

    @property
    def local_to_global_transform(self) -> RigidTransform:
        return RigidTransform(
            Matrix3.from_columns(self.x_axis, self.y_axis, self.z_axis),
            Vector3(self.origin.x, self.origin.y, self.origin.z),
        )

    @property
    def global_to_local_transform(self) -> RigidTransform:
        return self.local_to_global_transform.inverse()

    def local_to_global(self, point: Point3) -> Point3:
        return self.local_to_global_transform.apply_point(point)

    def global_to_local(self, point: Point3) -> Point3:
        return self.global_to_local_transform.apply_point(point)


@dataclass(frozen=True, slots=True)
class DatumPlane:
    """Named plane represented by a global origin and unit normal."""

    name: str
    origin: Point3
    normal: Vector3

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise SpatialContractError("DatumPlane.name must be non-empty")
        unit = self.normal.normalized()
        object.__setattr__(self, "normal", unit)

    def signed_distance(self, point: Point3) -> float:
        return self.origin.vector_to(point).dot(self.normal)

    def project(self, point: Point3) -> Point3:
        distance = self.signed_distance(point)
        return point.translated(self.normal.scaled(-distance))


@dataclass(frozen=True, slots=True)
class CanonicalDatums:
    """Frozen Masck One spatial references derived directly from the machine authority."""

    global_frame: DatumFrame
    sagittal_plane: DatumPlane
    transverse_plane: DatumPlane
    coronal_plane: DatumPlane

    @classmethod
    def from_authority(cls, authority: Authority) -> "CanonicalDatums":
        origin = Point3.from_triple(authority.get("coordinate_system", "origin"))
        x_positive = authority.get("coordinate_system", "x_positive")
        y_positive = authority.get("coordinate_system", "y_positive")
        z_positive = authority.get("coordinate_system", "z_positive")
        expected = ("wearer_right", "superior", "anterior")
        actual = (x_positive, y_positive, z_positive)
        if actual != expected:
            raise SpatialContractError(
                "Canonical axis semantics drifted: "
                f"expected {expected!r}, got {actual!r}"
            )

        x_axis = Vector3(1.0, 0.0, 0.0)
        y_axis = Vector3(0.0, 1.0, 0.0)
        z_axis = Vector3(0.0, 0.0, 1.0)
        frame = DatumFrame("MASCK_ONE_GLOBAL", origin, x_axis, y_axis, z_axis)
        return cls(
            global_frame=frame,
            sagittal_plane=DatumPlane("MASCK_ONE_SAGITTAL_X0", origin, x_axis),
            transverse_plane=DatumPlane("MASCK_ONE_TRANSVERSE_Y0", origin, y_axis),
            coronal_plane=DatumPlane("MASCK_ONE_CORONAL_Z0", origin, z_axis),
        )

    def mirror_sagittal(self, point: Point3) -> Point3:
        distance = self.sagittal_plane.signed_distance(point)
        return point.translated(self.sagittal_plane.normal.scaled(-2.0 * distance))


def authority_point2(authority: Authority, *path: str) -> Point2:
    """Read one authority XY point without allowing call-site-specific tuple conventions."""

    return Point2.from_pair(authority.get(*path))


def authority_point3(authority: Authority, *path: str) -> Point3:
    """Read one authority XYZ point without allowing call-site-specific tuple conventions."""

    return Point3.from_triple(authority.get(*path))
