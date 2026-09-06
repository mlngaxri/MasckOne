from __future__ import annotations

"""Hostile release audit for current-main development-assembly material semantics.

This module does not compose product geometry and does not promote candidate geometry.
It reconstructs the exact current released export-selection rule, binds that result to
its source files, and reports whether nonphysical review/package geometry is entering
the development assembly.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
from pathlib import Path
import re

from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_CELL5_RELEASE_MATERIAL_TRUTH_AUDIT_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
SOURCE_MODEL_GIT_BLOB_SHA = "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"
SOURCE_EXPORT_GIT_BLOB_SHA = "a834333ec153a1bf28bb6713003291db6af7237d"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

SOURCE_GIT_BLOB_IDENTITIES = (
    ("src/masck_one/model.py", SOURCE_MODEL_GIT_BLOB_SHA),
    ("src/masck_one/export.py", SOURCE_EXPORT_GIT_BLOB_SHA),
)

PHYSICAL_MATERIAL_NAMES = ("rigid_shell",)
CURRENT_EXPORT_EXCLUSIONS = ("waste_cartridge_envelope",)
EXPECTED_CURRENT_INCLUDED_NAMES = (
    "rigid_shell",
    "nasal_lobe_membrane_reference",
    "actuator_envelope_1",
    "actuator_envelope_2",
    "actuator_envelope_3",
    "actuator_envelope_4",
    "water_reservoir_envelope",
    "battery_reference_envelope",
)
EXPECTED_NONPHYSICAL_INCLUDED_NAMES = tuple(
    name for name in EXPECTED_CURRENT_INCLUDED_NAMES if name not in PHYSICAL_MATERIAL_NAMES
)
BLOCKED_DISPOSITION = "BLOCKED_NONPHYSICAL_REFERENCE_GEOMETRY_IN_DEVELOPMENT_ASSEMBLY"
EVIDENCE_STATUS = (
    "DIGITAL_RELEASE_MATERIAL_MEMBERSHIP_AUDIT_ONLY_NOT_FIT_CLEARANCE_SERVICE_"
    "LOAD_FLUID_ELECTRICAL_THERMAL_HYGIENE_OR_PHYSICAL_VALIDATION"
)

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]


class ReleaseMaterialTruthError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_sources_current() -> None:
    seen: set[str] = set()
    for relative_path, expected in SOURCE_GIT_BLOB_IDENTITIES:
        if relative_path in seen or _SHA40.fullmatch(expected) is None:
            raise ReleaseMaterialTruthError("release-material source identity set is malformed")
        seen.add(relative_path)
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise ReleaseMaterialTruthError(f"release-material source missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise ReleaseMaterialTruthError(
                f"release-material source moved at {relative_path}; expected {expected}, got {actual}"
            )


def _component_map(model: MasckOneModel) -> dict[str, object]:
    if type(model) is not MasckOneModel:
        raise ReleaseMaterialTruthError("audit requires the exact MasckOneModel type")
    components = {component.name: component for component in model.components}
    if len(components) != len(model.components):
        raise ReleaseMaterialTruthError("released model contains duplicate component names")
    return components


def _current_export_membership(model: MasckOneModel) -> tuple[str, ...]:
    return tuple(
        component.name
        for component in model.components
        if component.status != "REFERENCE_ONLY"
        and component.name not in CURRENT_EXPORT_EXCLUSIONS
    )


@dataclass(frozen=True, slots=True)
class ReleaseMaterialTruthAudit:
    schema: str
    source_main_sha: str
    source_model_git_blob_sha: str
    source_export_git_blob_sha: str
    coordinate_frame_id: str
    included_component_names: tuple[str, ...]
    physical_material_names: tuple[str, ...]
    nonphysical_included_names: tuple[str, ...]
    included_realized_solid_count: int
    physical_realized_solid_count: int
    nonphysical_realized_solid_count: int
    release_disposition: str
    digital_mvp_release_eligible: bool
    physical_validation_eligible: bool
    evidence_status: str

    def validate(self) -> None:
        if self.schema != SCHEMA:
            raise ReleaseMaterialTruthError("unexpected release-material audit schema")
        if self.source_main_sha != SOURCE_MAIN_SHA or _SHA40.fullmatch(self.source_main_sha) is None:
            raise ReleaseMaterialTruthError("release-material audit is stale for reconstructed main")
        if self.source_model_git_blob_sha != SOURCE_MODEL_GIT_BLOB_SHA:
            raise ReleaseMaterialTruthError("release-material model source binding moved")
        if self.source_export_git_blob_sha != SOURCE_EXPORT_GIT_BLOB_SHA:
            raise ReleaseMaterialTruthError("release-material export source binding moved")
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise ReleaseMaterialTruthError("release-material audit must use canonical authority world frame")
        if self.included_component_names != EXPECTED_CURRENT_INCLUDED_NAMES:
            raise ReleaseMaterialTruthError("current development-assembly membership moved")
        if self.physical_material_names != PHYSICAL_MATERIAL_NAMES:
            raise ReleaseMaterialTruthError("physical-material identity set moved")
        if self.nonphysical_included_names != EXPECTED_NONPHYSICAL_INCLUDED_NAMES:
            raise ReleaseMaterialTruthError("nonphysical development-assembly contamination set moved")
        if type(self.included_realized_solid_count) is not int or self.included_realized_solid_count <= 0:
            raise ReleaseMaterialTruthError("included realized-solid count must be a positive exact integer")
        if type(self.physical_realized_solid_count) is not int or self.physical_realized_solid_count <= 0:
            raise ReleaseMaterialTruthError("physical realized-solid count must be a positive exact integer")
        if type(self.nonphysical_realized_solid_count) is not int or self.nonphysical_realized_solid_count <= 0:
            raise ReleaseMaterialTruthError("nonphysical realized-solid count must be a positive exact integer")
        if self.included_realized_solid_count != (
            self.physical_realized_solid_count + self.nonphysical_realized_solid_count
        ):
            raise ReleaseMaterialTruthError("realized-solid membership accounting does not balance")
        if self.release_disposition != BLOCKED_DISPOSITION:
            raise ReleaseMaterialTruthError("current false-maturity blocker cannot be silently cleared")
        if type(self.digital_mvp_release_eligible) is not bool or self.digital_mvp_release_eligible:
            raise ReleaseMaterialTruthError("contaminated development assembly cannot be digitally release-eligible")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise ReleaseMaterialTruthError("digital membership audit cannot become physical evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise ReleaseMaterialTruthError("release-material evidence firewall moved")

    @property
    def manifest_sha256(self) -> str:
        payload = self.manifest(include_sha=False)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.validate()
        payload: dict[str, object] = {
            "schema": self.schema,
            "source_main_sha": self.source_main_sha,
            "source_model_git_blob_sha": self.source_model_git_blob_sha,
            "source_export_git_blob_sha": self.source_export_git_blob_sha,
            "coordinate_frame_id": self.coordinate_frame_id,
            "included_component_names": list(self.included_component_names),
            "physical_material_names": list(self.physical_material_names),
            "nonphysical_included_names": list(self.nonphysical_included_names),
            "included_realized_solid_count": self.included_realized_solid_count,
            "physical_realized_solid_count": self.physical_realized_solid_count,
            "nonphysical_realized_solid_count": self.nonphysical_realized_solid_count,
            "release_disposition": self.release_disposition,
            "digital_mvp_release_eligible": self.digital_mvp_release_eligible,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload


def build_current_main_release_material_truth_audit(
    model: MasckOneModel | None = None,
) -> ReleaseMaterialTruthAudit:
    _require_sources_current()
    model = model or build_model()
    components = _component_map(model)
    included_names = _current_export_membership(model)
    if included_names != EXPECTED_CURRENT_INCLUDED_NAMES:
        raise ReleaseMaterialTruthError("current export selection changed and requires fresh hostile review")
    missing_physical = tuple(name for name in PHYSICAL_MATERIAL_NAMES if name not in components)
    if missing_physical:
        raise ReleaseMaterialTruthError("released physical material is missing: " + ", ".join(missing_physical))
    nonphysical_names = tuple(name for name in included_names if name not in PHYSICAL_MATERIAL_NAMES)
    included_solids = sum(len(components[name].solid.val().Solids()) for name in included_names)
    physical_solids = sum(len(components[name].solid.val().Solids()) for name in PHYSICAL_MATERIAL_NAMES)
    nonphysical_solids = sum(len(components[name].solid.val().Solids()) for name in nonphysical_names)
    audit = ReleaseMaterialTruthAudit(
        schema=SCHEMA,
        source_main_sha=SOURCE_MAIN_SHA,
        source_model_git_blob_sha=SOURCE_MODEL_GIT_BLOB_SHA,
        source_export_git_blob_sha=SOURCE_EXPORT_GIT_BLOB_SHA,
        coordinate_frame_id=WORLD_FRAME_ID,
        included_component_names=included_names,
        physical_material_names=PHYSICAL_MATERIAL_NAMES,
        nonphysical_included_names=nonphysical_names,
        included_realized_solid_count=included_solids,
        physical_realized_solid_count=physical_solids,
        nonphysical_realized_solid_count=nonphysical_solids,
        release_disposition=BLOCKED_DISPOSITION,
        digital_mvp_release_eligible=False,
        physical_validation_eligible=False,
        evidence_status=EVIDENCE_STATUS,
    )
    audit.validate()
    return audit
