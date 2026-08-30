from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Iterable, Mapping, Sequence

from .spatial import Point3, RigidTransform, SpatialContractError, Vector3


class ReferenceSurfaceError(ValueError):
    """Raised when external/reference surface data violates the ingestion contract."""


UNIT_TO_MM: Mapping[str, float] = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
    "in": 25.4,
}

_ALLOWED_HANDEDNESS = {"right", "left"}
_ALLOWED_SOURCE_KINDS = {
    "HEADFORM_SCAN",
    "FACE_SCAN",
    "SUPPLIER_REFERENCE",
    "SYNTHETIC_TEST_FIXTURE",
    "ANALYTICAL_DEVELOPMENT_REFERENCE",
}


def _finite(value: float, *, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ReferenceSurfaceError(f"{label} must be finite, got {value!r}")
    return result


def _canonical_float(value: float) -> str:
    return format(float(value), ".17g")


@dataclass(frozen=True, slots=True)
class SurfaceProvenance:
    """Traceability required before a reference surface may influence Masck One CAD.

    `source_sha256` is the hash of the original source artifact or normalized payload,
    not a hash of the registered/transformed mesh. The registration transform is
    intentionally separate so provenance survives deterministic re-registration.
    """

    asset_id: str
    source_kind: str
    source_label: str
    source_revision: str
    source_units: str
    handedness: str
    x_positive: str
    y_positive: str
    z_positive: str
    source_sha256: str
    evidence_status: str

    def __post_init__(self) -> None:
        text_fields = {
            "asset_id": self.asset_id,
            "source_label": self.source_label,
            "source_revision": self.source_revision,
            "x_positive": self.x_positive,
            "y_positive": self.y_positive,
            "z_positive": self.z_positive,
            "evidence_status": self.evidence_status,
        }
        for label, value in text_fields.items():
            if not str(value).strip():
                raise ReferenceSurfaceError(f"{label} must be non-empty")
        if self.source_kind not in _ALLOWED_SOURCE_KINDS:
            raise ReferenceSurfaceError(f"Unsupported source_kind {self.source_kind!r}")
        if self.source_units not in UNIT_TO_MM:
            raise ReferenceSurfaceError(
                f"Unsupported source_units {self.source_units!r}; expected one of {sorted(UNIT_TO_MM)}"
            )
        if self.handedness not in _ALLOWED_HANDEDNESS:
            raise ReferenceSurfaceError(f"Unsupported handedness {self.handedness!r}")
        digest = self.source_sha256.lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ReferenceSurfaceError("source_sha256 must be a 64-character hexadecimal SHA-256 digest")
        object.__setattr__(self, "source_sha256", digest)


@dataclass(frozen=True, slots=True)
class TriangleMesh:
    """Minimal immutable triangular surface representation in source coordinates."""

    vertices: tuple[Point3, ...]
    triangles: tuple[tuple[int, int, int], ...]

    def __post_init__(self) -> None:
        vertices = tuple(self.vertices)
        triangles = tuple(tuple(face) for face in self.triangles)
        if len(vertices) < 3:
            raise ReferenceSurfaceError("TriangleMesh requires at least three vertices")
        if not triangles:
            raise ReferenceSurfaceError("TriangleMesh requires at least one triangle")

        normalized_faces: list[tuple[int, int, int]] = []
        for face_index, face in enumerate(triangles):
            if len(face) != 3:
                raise ReferenceSurfaceError(f"Triangle {face_index} must contain exactly three vertex indices")
            try:
                indices = tuple(int(index) for index in face)
            except (TypeError, ValueError) as exc:
                raise ReferenceSurfaceError(f"Triangle {face_index} contains a non-integer index") from exc
            if len(set(indices)) != 3:
                raise ReferenceSurfaceError(f"Triangle {face_index} repeats a vertex index")
            if min(indices) < 0 or max(indices) >= len(vertices):
                raise ReferenceSurfaceError(f"Triangle {face_index} references a vertex outside the mesh")
            a, b, c = (vertices[index] for index in indices)
            area_vector = a.vector_to(b).cross(a.vector_to(c))
            if area_vector.norm() <= 1e-12:
                raise ReferenceSurfaceError(f"Triangle {face_index} is degenerate")
            normalized_faces.append(indices)

        object.__setattr__(self, "vertices", vertices)
        object.__setattr__(self, "triangles", tuple(normalized_faces))

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    @property
    def triangle_count(self) -> int:
        return len(self.triangles)

    def normalized_payload(self) -> dict[str, object]:
        return {
            "vertices": [[_canonical_float(v.x), _canonical_float(v.y), _canonical_float(v.z)] for v in self.vertices],
            "triangles": [list(face) for face in self.triangles],
        }

    def normalized_sha256(self) -> str:
        payload = json.dumps(self.normalized_payload(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class SurfaceRegistration:
    """Explicit rigid registration from unit-normalized source coordinates to MASCK_ONE_GLOBAL."""

    source_to_global: RigidTransform
    method: str
    registration_revision: str
    rms_error_mm: float | None = None
    max_error_mm: float | None = None
    evidence_status: str = "UNVALIDATED_REGISTRATION"

    def __post_init__(self) -> None:
        if not self.method.strip():
            raise ReferenceSurfaceError("Registration method must be non-empty")
        if not self.registration_revision.strip():
            raise ReferenceSurfaceError("Registration revision must be non-empty")
        if not self.evidence_status.strip():
            raise ReferenceSurfaceError("Registration evidence_status must be non-empty")
        if self.rms_error_mm is not None:
            rms = _finite(self.rms_error_mm, label="rms_error_mm")
            if rms < 0.0:
                raise ReferenceSurfaceError("rms_error_mm cannot be negative")
            object.__setattr__(self, "rms_error_mm", rms)
        if self.max_error_mm is not None:
            maximum = _finite(self.max_error_mm, label="max_error_mm")
            if maximum < 0.0:
                raise ReferenceSurfaceError("max_error_mm cannot be negative")
            object.__setattr__(self, "max_error_mm", maximum)
        if self.rms_error_mm is not None and self.max_error_mm is not None:
            if self.rms_error_mm > self.max_error_mm:
                raise ReferenceSurfaceError("Registration RMS error cannot exceed maximum error")


@dataclass(frozen=True, slots=True)
class ReferenceSurfaceAsset:
    """A source mesh plus provenance and explicit registration into Masck One coordinates."""

    provenance: SurfaceProvenance
    source_mesh: TriangleMesh
    registration: SurfaceRegistration

    def __post_init__(self) -> None:
        if self.provenance.handedness != "right":
            raise ReferenceSurfaceError(
                "Left-handed sources are not silently reflected. Convert them in a documented preprocessing step, "
                "hash the corrected artifact, and ingest the corrected right-handed source."
            )

    @property
    def source_scale_to_mm(self) -> float:
        return UNIT_TO_MM[self.provenance.source_units]

    def source_point_to_global(self, point: Point3) -> Point3:
        scale = self.source_scale_to_mm
        normalized = Point3(point.x * scale, point.y * scale, point.z * scale)
        return self.registration.source_to_global.apply_point(normalized)

    def source_vector_to_global(self, vector: Vector3) -> Vector3:
        scale = self.source_scale_to_mm
        normalized = Vector3(vector.x * scale, vector.y * scale, vector.z * scale)
        return self.registration.source_to_global.apply_vector(normalized)

    @property
    def registered_mesh(self) -> TriangleMesh:
        return TriangleMesh(
            vertices=tuple(self.source_point_to_global(vertex) for vertex in self.source_mesh.vertices),
            triangles=self.source_mesh.triangles,
        )

    def registration_manifest(self) -> dict[str, object]:
        rotation = self.registration.source_to_global.rotation.rows
        translation = self.registration.source_to_global.translation.as_tuple()
        return {
            "asset_id": self.provenance.asset_id,
            "source_kind": self.provenance.source_kind,
            "source_label": self.provenance.source_label,
            "source_revision": self.provenance.source_revision,
            "source_sha256": self.provenance.source_sha256,
            "source_units": self.provenance.source_units,
            "source_scale_to_mm": self.source_scale_to_mm,
            "source_handedness": self.provenance.handedness,
            "axis_semantics": {
                "+X": self.provenance.x_positive,
                "+Y": self.provenance.y_positive,
                "+Z": self.provenance.z_positive,
            },
            "registration": {
                "method": self.registration.method,
                "revision": self.registration.registration_revision,
                "rotation_rows": [list(row) for row in rotation],
                "translation_mm": list(translation),
                "rms_error_mm": self.registration.rms_error_mm,
                "max_error_mm": self.registration.max_error_mm,
                "evidence_status": self.registration.evidence_status,
            },
            "mesh": {
                "vertex_count": self.source_mesh.vertex_count,
                "triangle_count": self.source_mesh.triangle_count,
                "normalized_mesh_sha256": self.source_mesh.normalized_sha256(),
            },
        }


def mesh_from_payload(payload: Mapping[str, object]) -> TriangleMesh:
    """Parse a normalized JSON-like mesh payload without guessing units or axes."""

    if set(payload) != {"vertices", "triangles"}:
        raise ReferenceSurfaceError("Mesh payload must contain exactly 'vertices' and 'triangles'")
    raw_vertices = payload["vertices"]
    raw_triangles = payload["triangles"]
    if not isinstance(raw_vertices, Sequence) or isinstance(raw_vertices, (str, bytes)):
        raise ReferenceSurfaceError("vertices must be a sequence")
    if not isinstance(raw_triangles, Sequence) or isinstance(raw_triangles, (str, bytes)):
        raise ReferenceSurfaceError("triangles must be a sequence")

    vertices: list[Point3] = []
    for index, raw in enumerate(raw_vertices):
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) != 3:
            raise ReferenceSurfaceError(f"Vertex {index} must contain exactly three coordinates")
        try:
            vertices.append(Point3(float(raw[0]), float(raw[1]), float(raw[2])))
        except (TypeError, ValueError, SpatialContractError) as exc:
            raise ReferenceSurfaceError(f"Vertex {index} is invalid") from exc

    triangles: list[tuple[int, int, int]] = []
    for index, raw in enumerate(raw_triangles):
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) != 3:
            raise ReferenceSurfaceError(f"Triangle {index} must contain exactly three indices")
        try:
            triangles.append((int(raw[0]), int(raw[1]), int(raw[2])))
        except (TypeError, ValueError) as exc:
            raise ReferenceSurfaceError(f"Triangle {index} contains an invalid index") from exc

    return TriangleMesh(tuple(vertices), tuple(triangles))


def provenance_from_payload(payload: Mapping[str, object]) -> SurfaceProvenance:
    required = {
        "asset_id",
        "source_kind",
        "source_label",
        "source_revision",
        "source_units",
        "handedness",
        "x_positive",
        "y_positive",
        "z_positive",
        "source_sha256",
        "evidence_status",
    }
    if set(payload) != required:
        missing = sorted(required - set(payload))
        unexpected = sorted(set(payload) - required)
        raise ReferenceSurfaceError(f"Invalid provenance fields; missing={missing}, unexpected={unexpected}")
    return SurfaceProvenance(**{key: str(payload[key]) for key in required})


def verify_source_digest(mesh: TriangleMesh, expected_sha256: str) -> None:
    """Verify normalized payload integrity when the normalized mesh itself is the source artifact.

    Binary STL/OBJ/PLY assets should retain the hash of their original bytes in provenance.
    This helper is specifically for normalized JSON-like payloads and test fixtures.
    """

    expected = expected_sha256.lower()
    actual = mesh.normalized_sha256()
    if actual != expected:
        raise ReferenceSurfaceError(f"Source digest mismatch: expected {expected}, calculated {actual}")


def identity_registration(*, revision: str = "identity-v1") -> SurfaceRegistration:
    return SurfaceRegistration(
        source_to_global=RigidTransform.identity(),
        method="EXPLICIT_IDENTITY_ALREADY_IN_MASCK_ONE_GLOBAL",
        registration_revision=revision,
        rms_error_mm=0.0,
        max_error_mm=0.0,
        evidence_status="DIGITAL_IDENTITY_TRANSFORM",
    )
