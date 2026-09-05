from __future__ import annotations

"""Fail-closed retention DFM boundary for released-main Masck One geometry.

This module records the digital engineering closure still required before retention can
participate in an MVP manufacturing freeze. It deliberately does not consume unmerged
Cell 3 geometry as release authority and does not invent an adjustment range, material,
fit claim, force, comfort result or production process.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from .whole_product_dfm import (
    MATURITY_RELEASED_TOPOLOGY,
    MATURITY_UNRESOLVED_REQUIRED,
    SOURCE_MAIN_SHA as DFM_SOURCE_MAIN_SHA,
    WholeProductDfmArchitecture,
    build_whole_product_dfm_architecture,
)

SCHEMA = "MASCK_ONE_RETENTION_DFM_GATE_V1"
SOURCE_MAIN_SHA = "628ec5f5766937433b1bdf8f30edc372924cf41e"
OPEN = "OPEN_DIGITAL_DFM_REQUIREMENT"
DIGITAL_ONLY = "DIGITAL_RETENTION_DFM_BOUNDARY_ONLY_NOT_FIT_COMFORT_STRENGTH_OR_PHYSICAL_VALIDATION"

_REACTION_FRAME_ID = "MASCK_ONE-DFM-REACTION-FRAME"
_RETENTION_PART_IDS = (
    "MASCK_ONE-DFM-RETENTION-HALO-LEFT",
    "MASCK_ONE-DFM-RETENTION-HALO-RIGHT-TONGUE",
    "MASCK_ONE-DFM-RETENTION-LEFT-PIVOT-PIN",
    "MASCK_ONE-DFM-LATCH-SOCKET-GUIDE",
    "MASCK_ONE-DFM-LATCH-SLIDER-GRIP",
    "MASCK_ONE-DFM-LATCH-CAPTURE-PIN",
    "MASCK_ONE-DFM-LATCH-GUIDE-CLOSURE",
)
_REQUIREMENT_IDS = (
    "RETENTION_OCCIPITAL_CONTACT_CARRIER",
    "RETENTION_WEARER_SIDE_EDGE_TREATMENT",
    "RETENTION_FRAME_SIDE_POSITIVE_CAPTURE",
    "RETENTION_CROWN_SUPPORT_ARCHITECTURE",
    "RETENTION_FIT_ACCOMMODATION_ARCHITECTURE",
    "RETENTION_NON_TELEPORTING_ASSEMBLY_ACCESS",
    "RETENTION_POST_RELEASE_WHOLE_HEAD_REMOVAL",
)
_SHA64 = re.compile(r"^[0-9a-f]{64}$")


class RetentionDfmError(ValueError):
    pass


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise RetentionDfmError(f"{label} must be exact nonblank text")
    return value


@dataclass(frozen=True, slots=True)
class RetentionClosureRequirement:
    requirement_id: str
    closure: str
    status: str = OPEN
    evidence_status: str = DIGITAL_ONLY

    def __post_init__(self) -> None:
        _text(self.requirement_id, label="retention requirement ID")
        _text(self.closure, label="retention closure")
        if self.status != OPEN:
            raise RetentionDfmError("released-main retention requirement cannot be marked closed without audit rebind")
        if self.evidence_status != DIGITAL_ONLY:
            raise RetentionDfmError("retention requirement cannot promote physical evidence")

    def manifest(self) -> dict[str, object]:
        return {
            "requirement_id": self.requirement_id,
            "closure": self.closure,
            "status": self.status,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class RetentionDfmGate:
    source_main_sha: str
    source_dfm_architecture_sha256: str
    requirements: tuple[RetentionClosureRequirement, ...]
    physical_validation_eligible: bool = False
    production_validation_eligible: bool = False
    evidence_status: str = DIGITAL_ONLY

    def __post_init__(self) -> None:
        if self.source_main_sha != SOURCE_MAIN_SHA or self.source_main_sha != DFM_SOURCE_MAIN_SHA:
            raise RetentionDfmError("retention DFM gate is stale for released main")
        if type(self.source_dfm_architecture_sha256) is not str or _SHA64.fullmatch(self.source_dfm_architecture_sha256) is None:
            raise RetentionDfmError("retention DFM gate requires a canonical 64-hex source architecture digest")
        if type(self.requirements) is not tuple:
            raise RetentionDfmError("retention DFM requirements must be an immutable tuple")
        if tuple(item.requirement_id for item in self.requirements) != _REQUIREMENT_IDS:
            raise RetentionDfmError("retention DFM requirement set or order drifted")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise RetentionDfmError("digital retention DFM cannot become physical validation evidence")
        if type(self.production_validation_eligible) is not bool or self.production_validation_eligible:
            raise RetentionDfmError("digital retention DFM cannot become production validation evidence")
        if self.evidence_status != DIGITAL_ONLY:
            raise RetentionDfmError("retention DFM evidence boundary drifted")

    @property
    def digital_retention_freeze_ready(self) -> bool:
        return all(item.status != OPEN for item in self.requirements)

    @property
    def gate_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": self.source_main_sha,
            "source_dfm_architecture_sha256": self.source_dfm_architecture_sha256,
            "requirements": [item.manifest() for item in self.requirements],
            "digital_retention_freeze_ready": self.digital_retention_freeze_ready,
            "adjustment_authority_boundary": (
                "NO_FROZEN_ADJUSTMENT_MECHANISM_OR_ANTHROPOMETRIC_TRAVEL;"
                "DIGITAL_FREEZE_REQUIRES_EITHER_CONTROLLED_FIT_ACCOMMODATION_OR_EXPLICIT_SINGLE_SIZE_HEADFORM_ARCHITECTURE"
            ),
            "physical_validation_eligible": self.physical_validation_eligible,
            "production_validation_eligible": self.production_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["retention_dfm_gate_sha256"] = self.gate_sha256
        return payload


def _requirements() -> tuple[RetentionClosureRequirement, ...]:
    return (
        RetentionClosureRequirement(
            "RETENTION_OCCIPITAL_CONTACT_CARRIER",
            "REALIZE_RELEASED_OCCIPITAL_STABILIZATION_AND_CONTACT_CARRIER_PART_BOUNDARIES_WITHOUT_CONFLATING_CROWN_OR_FACIAL_REACTION",
        ),
        RetentionClosureRequirement(
            "RETENTION_WEARER_SIDE_EDGE_TREATMENT",
            "CONTROL_RIGID_WEARER_SIDE_EDGES_OR_REALIZE_A_COVERING_CONTACT_LAYER_ENVELOPE;NO_COMFORT_OR_SKIN_SAFETY_CLAIM",
        ),
        RetentionClosureRequirement(
            "RETENTION_FRAME_SIDE_POSITIVE_CAPTURE",
            "REALIZE_FRAME_SIDE_CLEVIS_PIN_CLOSURE_OR_EQUIVALENT_POSITIVE_CAPTURE_WITH_RETAINER_AND_ASSEMBLY_ACCESS;FRICTION_ONLY_ATTACHMENT_FORBIDDEN",
        ),
        RetentionClosureRequirement(
            "RETENTION_CROWN_SUPPORT_ARCHITECTURE",
            "REALIZE_CROWN_SUPPORT_MEMBER_AND_JOIN_LOAD_PATH_OR_EXPLICITLY_CONTROL_A_NO_CROWN_ARCHITECTURE;DO_NOT_INFER_FROM_OCCIPITAL_GEOMETRY",
        ),
        RetentionClosureRequirement(
            "RETENTION_FIT_ACCOMMODATION_ARCHITECTURE",
            "REALIZE_BOUNDED_FIT_ACCOMMODATION_WITH_STOPS_AND_CAPTURE_OR_EXPLICITLY_CONTROL_A_SINGLE_SIZE_TARGET_HEADFORM;DO_NOT_INVENT_TRAVEL_RANGE",
        ),
        RetentionClosureRequirement(
            "RETENTION_NON_TELEPORTING_ASSEMBLY_ACCESS",
            "PROVE_COLLISION_FREE_INSERTION_CLOSURE_AND_TOOL_OR_PROCESS_ACCESS_FOR_RETENTION_PARTS_AND_POSITIVE_CAPTURE_HARDWARE",
        ),
        RetentionClosureRequirement(
            "RETENTION_POST_RELEASE_WHOLE_HEAD_REMOVAL",
            "PROVE_A_DIGITAL_WHOLE_HEAD_REMOVAL_PATH_AFTER_RELEASE_WITHOUT_TREATING_SLIDER_TRAVEL_AS_HEAD_REMOVAL_EVIDENCE",
        ),
    )


def build_retention_dfm_gate(
    architecture: WholeProductDfmArchitecture | None = None,
) -> RetentionDfmGate:
    architecture = architecture or build_whole_product_dfm_architecture()
    if type(architecture) is not WholeProductDfmArchitecture:
        raise RetentionDfmError("retention DFM gate requires the exact whole-product DFM architecture type")
    if architecture.source_main_sha != SOURCE_MAIN_SHA:
        raise RetentionDfmError("whole-product DFM source main moved and requires retention audit rebind")

    by_id = {part.part_id: part for part in architecture.parts}
    if _REACTION_FRAME_ID not in by_id:
        raise RetentionDfmError("reaction-frame DFM part is missing")
    if by_id[_REACTION_FRAME_ID].maturity != MATURITY_RELEASED_TOPOLOGY:
        raise RetentionDfmError("reaction-frame maturity moved and requires retention audit rebind")
    for part_id in _RETENTION_PART_IDS:
        if part_id not in by_id:
            raise RetentionDfmError(f"required retention DFM part is missing: {part_id}")
        if by_id[part_id].maturity != MATURITY_UNRESOLVED_REQUIRED:
            raise RetentionDfmError("retention part maturity moved and requires retention audit rebind")

    source_manifest = architecture.manifest()
    source_sha = source_manifest.get("dfm_architecture_sha256")
    if type(source_sha) is not str:
        raise RetentionDfmError("whole-product DFM architecture digest is missing")
    return RetentionDfmGate(
        source_main_sha=SOURCE_MAIN_SHA,
        source_dfm_architecture_sha256=source_sha,
        requirements=_requirements(),
    )
