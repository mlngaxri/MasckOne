from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from .surface_continuity import SurfaceContinuityError, SurfaceContinuityReport


class SurfaceTopologyError(ValueError):
    """Raised when exterior surface-topology provenance is invalid."""


_SCHEMA = "MASCK_ONE_SURFACE_TOPOLOGY_V1"
_WORLD_FRAME = "MASCK_ONE_ROOT_WORLD_MM"
_EVIDENCE_STATUS = "DIGITAL_TOPOLOGY_BINDING_ONLY_NOT_CLASS_A_OR_PHYSICAL_EVIDENCE"
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_id(value: object, label: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise SurfaceTopologyError(f"{label} must be canonical lowercase identifier text")
    return value


def _canonical_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise SurfaceTopologyError(f"{label} must be canonical lowercase SHA-256")
    return value


@dataclass(frozen=True, slots=True)
class SeamTopologyBinding:
    seam_id: str
    patch_a_id: str
    patch_b_id: str
    patch_a_boundary_id: str
    patch_b_boundary_id: str

    def __post_init__(self) -> None:
        _canonical_id(self.seam_id, "Seam identity")
        _canonical_id(self.patch_a_id, "Patch A identity")
        _canonical_id(self.patch_b_id, "Patch B identity")
        _canonical_id(self.patch_a_boundary_id, "Patch A boundary identity")
        _canonical_id(self.patch_b_boundary_id, "Patch B boundary identity")
        if self.patch_a_id == self.patch_b_id:
            raise SurfaceTopologyError("A seam must bind two distinct surface patches")
        if (self.patch_b_id, self.patch_b_boundary_id) < (self.patch_a_id, self.patch_a_boundary_id):
            raise SurfaceTopologyError("Seam patch/boundary pair must use canonical lexical orientation")

    @property
    def endpoints(self) -> tuple[tuple[str, str], tuple[str, str]]:
        return (
            (self.patch_a_id, self.patch_a_boundary_id),
            (self.patch_b_id, self.patch_b_boundary_id),
        )

    def manifest(self) -> dict[str, str]:
        self.__post_init__()
        return {
            "seam_id": self.seam_id,
            "patch_a_id": self.patch_a_id,
            "patch_b_id": self.patch_b_id,
            "patch_a_boundary_id": self.patch_a_boundary_id,
            "patch_b_boundary_id": self.patch_b_boundary_id,
        }


@dataclass(frozen=True, slots=True)
class SurfaceTopologyManifest:
    source_geometry_sha256: str
    coordinate_frame: str
    seams: tuple[SeamTopologyBinding, ...]
    evidence_status: str = _EVIDENCE_STATUS
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        _canonical_sha(self.source_geometry_sha256, "Source geometry identity")
        if self.coordinate_frame != _WORLD_FRAME:
            raise SurfaceTopologyError("Surface topology must use the controlled root/world millimetre frame")
        if not isinstance(self.seams, tuple) or not self.seams:
            raise SurfaceTopologyError("Seams must be a nonempty immutable tuple")
        if not all(isinstance(seam, SeamTopologyBinding) for seam in self.seams):
            raise SurfaceTopologyError("Every seam must be a SeamTopologyBinding")
        for seam in self.seams:
            seam.__post_init__()
        seam_ids = tuple(seam.seam_id for seam in self.seams)
        if seam_ids != tuple(sorted(seam_ids)) or len(set(seam_ids)) != len(seam_ids):
            raise SurfaceTopologyError("Seam identities must be unique and canonically sorted")
        endpoints = tuple(endpoint for seam in self.seams for endpoint in seam.endpoints)
        if len(set(endpoints)) != len(endpoints):
            raise SurfaceTopologyError("A patch boundary may participate in only one exterior seam")
        if self.evidence_status != _EVIDENCE_STATUS:
            raise SurfaceTopologyError("Surface topology evidence status is controlled")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise SurfaceTopologyError("Digital topology cannot be physical-validation evidence")

    def assert_current_geometry(self, current_geometry_sha256: object) -> None:
        self.__post_init__()
        current = _canonical_sha(current_geometry_sha256, "Current geometry identity")
        if current != self.source_geometry_sha256:
            raise SurfaceTopologyError("Surface topology manifest is stale for the current geometry")

    def assert_continuity_report(self, report: object) -> None:
        self.__post_init__()
        if not isinstance(report, SurfaceContinuityReport):
            raise SurfaceTopologyError("Continuity binding requires a SurfaceContinuityReport")
        try:
            report.__post_init__()
        except SurfaceContinuityError as exc:
            raise SurfaceTopologyError("Continuity report failed contract revalidation") from exc
        if report.source_geometry_sha256 != self.source_geometry_sha256 or report.coordinate_frame != self.coordinate_frame:
            raise SurfaceTopologyError("Continuity report provenance does not match topology")
        report_ids = tuple(seam.seam_id for seam in report.seams)
        topology_ids = tuple(seam.seam_id for seam in self.seams)
        if report_ids != topology_ids:
            raise SurfaceTopologyError("Continuity report seam identities do not match topology")

    @property
    def manifest_sha256(self) -> str:
        self.__post_init__()
        payload = {
            "schema": _SCHEMA,
            "source_geometry_sha256": self.source_geometry_sha256,
            "coordinate_frame": self.coordinate_frame,
            "seams": [seam.manifest() for seam in self.seams],
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
