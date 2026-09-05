from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Final

from .authority import Authority, load_authority
from .spatial import CanonicalDatums, Matrix3, RigidTransform, SpatialContractError, Vector3


class FrameContractError(ValueError):
    """Raised when a cross-system coordinate binding is ambiguous or non-canonical."""


CANONICAL_FRAME_ID: Final[str] = "MASCK_ONE_AUTHORITY_WORLD_MM"
CANONICAL_LENGTH_UNIT: Final[str] = "mm"
CANONICAL_ANGLE_UNIT: Final[str] = "deg"
CANONICAL_HANDEDNESS: Final[str] = "right"
CANONICAL_AXIS_SEMANTICS: Final[tuple[str, str, str]] = (
    "wearer_right",
    "superior",
    "anterior",
)
LEGACY_INTERNAL_FRAME_ALIASES: Final[tuple[str, ...]] = ("MASCK_ONE_GLOBAL",)
LOCAL_FRAME_PREFIX: Final[str] = "MASCK_ONE_LOCAL_"
EVIDENCE_STATUS: Final[str] = (
    "DIGITAL_COORDINATE_AND_TRANSFORM_CONTRACT_ONLY_NOT_PHYSICAL_FIT_CLEARANCE_OR_PERFORMANCE_EVIDENCE"
)


def _exact_text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise FrameContractError(f"{label} must be exact nonblank text")
    return value


def _identity_transform() -> RigidTransform:
    return RigidTransform.identity()


def _is_identity(transform: RigidTransform) -> bool:
    return transform == _identity_transform()


def _transform_manifest(transform: RigidTransform) -> dict[str, object]:
    return {
        "rotation_rows": [list(row) for row in transform.rotation.rows],
        "translation_mm": list(transform.translation.as_tuple()),
        "determinant": transform.rotation.determinant(),
    }


@dataclass(frozen=True, slots=True)
class FrameBinding:
    """One explicit rigid mapping into the authority-world millimetre frame.

    RigidTransform contains no scale term. Therefore both ends of every accepted
    cross-system binding are millimetres. Unit conversion must happen at ingestion,
    before a source is allowed to participate in product geometry.
    """

    source_frame_id: str
    target_frame_id: str
    source_length_unit: str
    target_length_unit: str
    transform: RigidTransform
    binding_kind: str

    def __post_init__(self) -> None:
        source = _exact_text(self.source_frame_id, label="source frame ID")
        target = _exact_text(self.target_frame_id, label="target frame ID")
        source_unit = _exact_text(self.source_length_unit, label="source length unit")
        target_unit = _exact_text(self.target_length_unit, label="target length unit")
        kind = _exact_text(self.binding_kind, label="binding kind")
        if type(self.transform) is not RigidTransform:
            raise FrameContractError("frame binding transform must be an exact RigidTransform")
        if target != CANONICAL_FRAME_ID:
            raise FrameContractError("cross-system target frame must be the canonical authority-world frame")
        if source_unit != CANONICAL_LENGTH_UNIT or target_unit != CANONICAL_LENGTH_UNIT:
            raise FrameContractError(
                "rigid cross-system transforms cannot hide unit conversion; both frames must already be millimetres"
            )
        if not self.transform.rotation.is_rotation() or self.transform.rotation.determinant() <= 0.0:
            raise FrameContractError("cross-system transform must preserve the right-handed proper basis")

        if source == CANONICAL_FRAME_ID:
            if kind != "AUTHORITY_WORLD_IDENTITY" or not _is_identity(self.transform):
                raise FrameContractError("authority-world coordinates cannot carry a hidden repositioning transform")
        elif source in LEGACY_INTERNAL_FRAME_ALIASES:
            if kind != "LEGACY_INTERNAL_ALIAS_EXPLICIT_IDENTITY" or not _is_identity(self.transform):
                raise FrameContractError("legacy global alias is permitted only as an explicit identity binding")
        elif source.startswith(LOCAL_FRAME_PREFIX):
            if kind != "EXPLICIT_LOCAL_TO_AUTHORITY_WORLD":
                raise FrameContractError("local subsystem frames require an explicit local-to-world binding kind")
        else:
            raise FrameContractError(
                f"unknown source frame {source!r}; cross-system geometry cannot rely on an implicit coordinate convention"
            )

    @property
    def binding_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "source_frame_id": self.source_frame_id,
            "target_frame_id": self.target_frame_id,
            "source_length_unit": self.source_length_unit,
            "target_length_unit": self.target_length_unit,
            "binding_kind": self.binding_kind,
            "transform": _transform_manifest(self.transform),
        }
        if include_sha:
            payload["binding_sha256"] = self.binding_sha256
        return payload


@dataclass(frozen=True, slots=True)
class CrossSystemFrameContract:
    authority_revision: str
    canonical_frame_id: str
    length_unit: str
    angle_unit: str
    handedness: str
    axis_semantics: tuple[str, str, str]
    origin_xyz_mm: tuple[float, float, float]
    spatial_datum_frame_id: str
    legacy_internal_aliases: tuple[str, ...]
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        _exact_text(self.authority_revision, label="authority revision")
        if self.canonical_frame_id != CANONICAL_FRAME_ID:
            raise FrameContractError("canonical frame ID drifted")
        if self.length_unit != CANONICAL_LENGTH_UNIT:
            raise FrameContractError("canonical length unit drifted")
        if self.angle_unit != CANONICAL_ANGLE_UNIT:
            raise FrameContractError("canonical angle unit drifted")
        if self.handedness != CANONICAL_HANDEDNESS:
            raise FrameContractError("canonical handedness drifted")
        if self.axis_semantics != CANONICAL_AXIS_SEMANTICS:
            raise FrameContractError("canonical axis semantics drifted")
        if self.origin_xyz_mm != (0.0, 0.0, 0.0):
            raise FrameContractError("frozen authority-world origin drifted")
        if self.spatial_datum_frame_id not in (CANONICAL_FRAME_ID, *LEGACY_INTERNAL_FRAME_ALIASES):
            raise FrameContractError("spatial datum uses an unknown global-frame identifier")
        if self.legacy_internal_aliases != LEGACY_INTERNAL_FRAME_ALIASES:
            raise FrameContractError("legacy internal alias registry drifted")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise FrameContractError("digital frame audit cannot become physical validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise FrameContractError("frame-contract evidence boundary drifted")

    @classmethod
    def from_authority(cls, authority: Authority) -> "CrossSystemFrameContract":
        if type(authority) is not Authority:
            raise FrameContractError("authority must be an exact Authority contract")
        if not authority.validation_report.valid:
            raise FrameContractError("frame contract requires a valid machine authority")

        length_unit = str(authority.get("project", "units", "length"))
        angle_unit = str(authority.get("project", "units", "angle"))
        axis_semantics = (
            str(authority.get("coordinate_system", "x_positive")),
            str(authority.get("coordinate_system", "y_positive")),
            str(authority.get("coordinate_system", "z_positive")),
        )
        origin = tuple(float(value) for value in authority.get("coordinate_system", "origin"))
        if len(origin) != 3:
            raise FrameContractError("authority-world origin must contain exactly three values")

        try:
            datums = CanonicalDatums.from_authority(authority)
        except SpatialContractError as exc:
            raise FrameContractError("canonical spatial datums do not satisfy the authority") from exc

        basis = Matrix3.from_columns(
            datums.global_frame.x_axis,
            datums.global_frame.y_axis,
            datums.global_frame.z_axis,
        )
        if basis != Matrix3.identity() or not basis.is_rotation() or basis.determinant() != 1.0:
            raise FrameContractError("authority-world basis must remain identity and right-handed")

        return cls(
            authority_revision=str(authority.get("project", "authority_revision")),
            canonical_frame_id=CANONICAL_FRAME_ID,
            length_unit=length_unit,
            angle_unit=angle_unit,
            handedness=CANONICAL_HANDEDNESS,
            axis_semantics=axis_semantics,
            origin_xyz_mm=(origin[0], origin[1], origin[2]),
            spatial_datum_frame_id=datums.global_frame.name,
            legacy_internal_aliases=LEGACY_INTERNAL_FRAME_ALIASES,
            physical_validation_eligible=False,
            evidence_status=EVIDENCE_STATUS,
        )

    def authority_world_identity_binding(self) -> FrameBinding:
        return FrameBinding(
            source_frame_id=CANONICAL_FRAME_ID,
            target_frame_id=CANONICAL_FRAME_ID,
            source_length_unit=CANONICAL_LENGTH_UNIT,
            target_length_unit=CANONICAL_LENGTH_UNIT,
            transform=RigidTransform.identity(),
            binding_kind="AUTHORITY_WORLD_IDENTITY",
        )

    def legacy_spatial_alias_binding(self) -> FrameBinding:
        if self.spatial_datum_frame_id == CANONICAL_FRAME_ID:
            return self.authority_world_identity_binding()
        return FrameBinding(
            source_frame_id=self.spatial_datum_frame_id,
            target_frame_id=CANONICAL_FRAME_ID,
            source_length_unit=CANONICAL_LENGTH_UNIT,
            target_length_unit=CANONICAL_LENGTH_UNIT,
            transform=RigidTransform.identity(),
            binding_kind="LEGACY_INTERNAL_ALIAS_EXPLICIT_IDENTITY",
        )

    def local_to_world_binding(self, *, local_frame_id: str, transform: RigidTransform) -> FrameBinding:
        return FrameBinding(
            source_frame_id=local_frame_id,
            target_frame_id=CANONICAL_FRAME_ID,
            source_length_unit=CANONICAL_LENGTH_UNIT,
            target_length_unit=CANONICAL_LENGTH_UNIT,
            transform=transform,
            binding_kind="EXPLICIT_LOCAL_TO_AUTHORITY_WORLD",
        )

    @property
    def contract_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        alias_binding = self.legacy_spatial_alias_binding()
        payload: dict[str, object] = {
            "schema": "MASCK_ONE_CROSS_SYSTEM_FRAME_CONTRACT_V1",
            "authority_revision": self.authority_revision,
            "canonical_frame_id": self.canonical_frame_id,
            "length_unit": self.length_unit,
            "angle_unit": self.angle_unit,
            "handedness": self.handedness,
            "axis_semantics": {
                "x_positive": self.axis_semantics[0],
                "y_positive": self.axis_semantics[1],
                "z_positive": self.axis_semantics[2],
            },
            "origin_xyz_mm": list(self.origin_xyz_mm),
            "spatial_datum_frame_id": self.spatial_datum_frame_id,
            "legacy_internal_aliases": list(self.legacy_internal_aliases),
            "spatial_datum_to_authority_world": alias_binding.manifest(),
            "cross_system_rule": (
                "EXTERNAL_GEOMETRY_MUST_DECLARE_MASCK_ONE_AUTHORITY_WORLD_MM_OR_AN_EXPLICIT_MASCK_ONE_LOCAL_FRAME_WITH_RIGID_MM_TRANSFORM"
            ),
            "unit_ingestion_rule": "CONVERT_TO_MM_BEFORE_RIGID_CROSS_SYSTEM_BINDING",
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            payload["contract_sha256"] = hashlib.sha256(raw).hexdigest()
        return payload


def build_cross_system_frame_contract(authority: Authority) -> CrossSystemFrameContract:
    return CrossSystemFrameContract.from_authority(authority)


def main() -> int:
    contract = build_cross_system_frame_contract(load_authority())
    print(json.dumps(contract.manifest(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
