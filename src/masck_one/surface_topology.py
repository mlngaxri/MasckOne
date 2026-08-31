from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from .surface_continuity import SeamContinuityMetrics, SurfaceContinuityError, SurfaceContinuityReport


class SurfaceTopologyError(ValueError):
    """Raised when exterior surface-topology provenance is invalid."""


_SCHEMA = "MASCK_ONE_SURFACE_TOPOLOGY_V1"
_BINDING_SCHEMA = "MASCK_ONE_TOPOLOGY_CONTINUITY_BINDING_V1"
_WORLD_FRAME = "MASCK_ONE_ROOT_WORLD_MM"
_EVIDENCE_STATUS = "DIGITAL_TOPOLOGY_BINDING_ONLY_NOT_CLASS_A_OR_PHYSICAL_EVIDENCE"
_CONTINUITY_EVIDENCE_STATUS = "DIGITAL_SURFACE_CONTINUITY_METRICS_ONLY_NOT_CLASS_A_OR_PHYSICAL_EVIDENCE"
_ALLOWED_TARGETS = ("G0", "G1", "G2")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_id(value: object, label: str) -> str:
    if type(value) is not str or not _ID_RE.fullmatch(value):
        raise SurfaceTopologyError(f"{label} must be exact canonical lowercase identifier text")
    return value


def _canonical_sha(value: object, label: str) -> str:
    if type(value) is not str or not _SHA_RE.fullmatch(value):
        raise SurfaceTopologyError(f"{label} must be exact canonical lowercase SHA-256")
    return value


def _canonical_controlled_text(value: object, expected: str, label: str) -> str:
    if type(value) is not str or value != expected:
        raise SurfaceTopologyError(f"{label} is controlled")
    return value


def _validate_continuity_report(report: object) -> SurfaceContinuityReport:
    if type(report) is not SurfaceContinuityReport:
        raise SurfaceTopologyError("Topology continuity binding requires an exact SurfaceContinuityReport")
    try:
        report.__post_init__()
    except (SurfaceContinuityError, TypeError, ValueError) as exc:
        raise SurfaceTopologyError("Continuity report failed contract revalidation") from exc
    _canonical_sha(report.source_geometry_sha256, "Continuity source geometry identity")
    _canonical_controlled_text(report.coordinate_frame, _WORLD_FRAME, "Continuity coordinate frame")
    _canonical_controlled_text(report.evidence_status, _CONTINUITY_EVIDENCE_STATUS, "Continuity evidence status")
    if type(report.physical_validation_eligible) is not bool or report.physical_validation_eligible:
        raise SurfaceTopologyError("Continuity report cannot be physical-validation evidence")
    if type(report.seams) is not tuple or not report.seams:
        raise SurfaceTopologyError("Continuity seams must be a nonempty immutable tuple")
    for seam in report.seams:
        if type(seam) is not SeamContinuityMetrics:
            raise SurfaceTopologyError("Every continuity seam must be an exact SeamContinuityMetrics")
        _canonical_id(seam.seam_id, "Continuity seam identity")
        if type(seam.target) is not str or seam.target not in _ALLOWED_TARGETS:
            raise SurfaceTopologyError("Continuity target must be exact controlled G0, G1, or G2 text")
    return report


@dataclass(frozen=True, slots=True)
class SeamTopologyBinding:
    seam_id: str
    patch_a_id: str
    patch_b_id: str
    patch_a_boundary_id: str
    patch_b_boundary_id: str

    def __post_init__(self) -> None:
        seam_id = _canonical_id(self.seam_id, "Seam identity")
        patch_a_id = _canonical_id(self.patch_a_id, "Patch A identity")
        patch_b_id = _canonical_id(self.patch_b_id, "Patch B identity")
        patch_a_boundary_id = _canonical_id(self.patch_a_boundary_id, "Patch A boundary identity")
        patch_b_boundary_id = _canonical_id(self.patch_b_boundary_id, "Patch B boundary identity")
        if patch_a_id == patch_b_id:
            raise SurfaceTopologyError("A seam must bind two distinct surface patches")
        if (patch_b_id, patch_b_boundary_id) < (patch_a_id, patch_a_boundary_id):
            raise SurfaceTopologyError("Seam patch/boundary pair must use canonical lexical orientation")
        if seam_id != self.seam_id:
            raise SurfaceTopologyError("Seam identity failed canonicalization")

    @property
    def endpoints(self) -> tuple[tuple[str, str], tuple[str, str]]:
        self.__post_init__()
        return ((self.patch_a_id, self.patch_a_boundary_id), (self.patch_b_id, self.patch_b_boundary_id))

    def manifest(self) -> dict[str, str]:
        self.__post_init__()
        return {"seam_id": self.seam_id, "patch_a_id": self.patch_a_id, "patch_b_id": self.patch_b_id, "patch_a_boundary_id": self.patch_a_boundary_id, "patch_b_boundary_id": self.patch_b_boundary_id}


@dataclass(frozen=True, slots=True)
class TopologyContinuityBinding:
    """Immutable proof that continuity metrics were evaluated for one exact topology."""

    topology_manifest_sha256: str
    report: SurfaceContinuityReport
    evidence_status: str = _EVIDENCE_STATUS
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        _canonical_sha(self.topology_manifest_sha256, "Topology manifest identity")
        _validate_continuity_report(self.report)
        _canonical_controlled_text(self.evidence_status, _EVIDENCE_STATUS, "Topology continuity evidence status")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise SurfaceTopologyError("Digital topology continuity cannot be physical-validation evidence")

    @property
    def binding_sha256(self) -> str:
        self.__post_init__()
        payload = {"schema": _BINDING_SCHEMA, "topology_manifest_sha256": self.topology_manifest_sha256, "continuity_report_sha256": self.report.report_sha256, "evidence_status": self.evidence_status, "physical_validation_eligible": self.physical_validation_eligible}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SurfaceTopologyManifest:
    source_geometry_sha256: str
    coordinate_frame: str
    seams: tuple[SeamTopologyBinding, ...]
    evidence_status: str = _EVIDENCE_STATUS
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        _canonical_sha(self.source_geometry_sha256, "Source geometry identity")
        _canonical_controlled_text(self.coordinate_frame, _WORLD_FRAME, "Surface topology coordinate frame")
        if type(self.seams) is not tuple or not self.seams:
            raise SurfaceTopologyError("Seams must be a nonempty immutable tuple")
        if not all(type(seam) is SeamTopologyBinding for seam in self.seams):
            raise SurfaceTopologyError("Every seam must be an exact SeamTopologyBinding")
        for seam in self.seams: seam.__post_init__()
        seam_ids = tuple(seam.seam_id for seam in self.seams)
        if seam_ids != tuple(sorted(seam_ids)) or len(set(seam_ids)) != len(seam_ids):
            raise SurfaceTopologyError("Seam identities must be unique and canonically sorted")
        endpoints = tuple(endpoint for seam in self.seams for endpoint in seam.endpoints)
        if len(set(endpoints)) != len(endpoints):
            raise SurfaceTopologyError("A patch boundary may participate in only one exterior seam")
        _canonical_controlled_text(self.evidence_status, _EVIDENCE_STATUS, "Surface topology evidence status")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise SurfaceTopologyError("Digital topology cannot be physical-validation evidence")

    def assert_current_geometry(self, current_geometry_sha256: object) -> None:
        self.__post_init__(); current = _canonical_sha(current_geometry_sha256, "Current geometry identity")
        if current != self.source_geometry_sha256: raise SurfaceTopologyError("Surface topology manifest is stale for the current geometry")

    def bind_continuity_report(self, report: SurfaceContinuityReport) -> TopologyContinuityBinding:
        self._assert_report_contract(report)
        return TopologyContinuityBinding(self.manifest_sha256, report)

    def assert_continuity_report(self, binding: object) -> None:
        self.__post_init__()
        if type(binding) is not TopologyContinuityBinding: raise SurfaceTopologyError("Continuity binding requires an exact TopologyContinuityBinding")
        binding.__post_init__(); bound_topology = _canonical_sha(binding.topology_manifest_sha256, "Bound topology manifest identity")
        if bound_topology != self.manifest_sha256: raise SurfaceTopologyError("Continuity binding belongs to a different topology manifest")
        self._assert_report_contract(binding.report)

    def _assert_report_contract(self, report: object) -> None:
        report = _validate_continuity_report(report)
        report_sha = _canonical_sha(report.source_geometry_sha256, "Continuity source geometry identity")
        report_frame = _canonical_controlled_text(report.coordinate_frame, _WORLD_FRAME, "Continuity coordinate frame")
        if report_sha != self.source_geometry_sha256 or report_frame != self.coordinate_frame: raise SurfaceTopologyError("Continuity report provenance does not match topology")
        report_ids = tuple(_canonical_id(seam.seam_id, "Continuity seam identity") for seam in report.seams)
        topology_ids = tuple(_canonical_id(seam.seam_id, "Topology seam identity") for seam in self.seams)
        if report_ids != topology_ids: raise SurfaceTopologyError("Continuity report seam identities do not match topology")

    @property
    def manifest_sha256(self) -> str:
        self.__post_init__()
        payload = {"schema": _SCHEMA, "source_geometry_sha256": self.source_geometry_sha256, "coordinate_frame": self.coordinate_frame, "seams": [seam.manifest() for seam in self.seams], "evidence_status": self.evidence_status, "physical_validation_eligible": self.physical_validation_eligible}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
