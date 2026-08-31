from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from .visual_system import AdaptiveVisualSystem


class DigitalExportError(ValueError):
    """Raised when a web/app export is ambiguous, stale, or unsafe."""


_SCHEMA = "MASCK_ONE_DIGITAL_EXPORT_V1"
_EVIDENCE = "PRESENTATION_EXPORT_ONLY_NOT_ENGINEERING_OR_PHYSICAL_EVIDENCE"
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_TARGETS = frozenset(("web", "app"))


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value:
        raise DigitalExportError(f"{label} must be exact nonempty built-in text")
    return value


def _id(value: object, label: str) -> str:
    value = _text(value, label)
    if not _ID_RE.fullmatch(value):
        raise DigitalExportError(f"{label} must be a canonical lowercase identifier")
    return value


def _sha(value: object, label: str) -> str:
    value = _text(value, label)
    if not _SHA_RE.fullmatch(value):
        raise DigitalExportError(f"{label} must be canonical SHA-256")
    return value


@dataclass(frozen=True, slots=True)
class DigitalTargetExport:
    target: str
    visual_system_sha256: str
    payload_sha256: str
    payload: tuple[tuple[str, str], ...]
    evidence_status: str = _EVIDENCE
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        target = _id(self.target, "Target")
        if target not in _TARGETS:
            raise DigitalExportError("Target must be web or app")
        _sha(self.visual_system_sha256, "Visual-system SHA")
        _sha(self.payload_sha256, "Payload SHA")
        if type(self.payload) is not tuple or not self.payload:
            raise DigitalExportError("Payload must be a nonempty immutable tuple")
        if not all(type(item) is tuple and len(item) == 2 and type(item[0]) is str and type(item[1]) is str for item in self.payload):
            raise DigitalExportError("Payload entries must be exact built-in text pairs")
        keys = tuple(item[0] for item in self.payload)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise DigitalExportError("Payload keys must be unique and canonically sorted")
        for key, value in self.payload:
            _id(key, "Payload key")
            _text(value, "Payload value")
        if self.payload_sha256 != self._computed_payload_sha256():
            raise DigitalExportError("Payload SHA does not match canonical payload")
        if type(self.evidence_status) is not str or self.evidence_status != _EVIDENCE:
            raise DigitalExportError("Evidence status is controlled")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise DigitalExportError("Digital exports cannot become physical evidence")

    def _computed_payload_sha256(self) -> str:
        encoded = json.dumps(dict(self.payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @property
    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "schema": _SCHEMA,
            "target": self.target,
            "visual_system_sha256": self.visual_system_sha256,
            "payload_sha256": self.payload_sha256,
            "payload": dict(self.payload),
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }

    @property
    def manifest_sha256(self) -> str:
        encoded = json.dumps(self.manifest, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def export_visual_system(system: AdaptiveVisualSystem, target: object) -> DigitalTargetExport:
    if type(system) is not AdaptiveVisualSystem:
        raise DigitalExportError("Visual system must be the exact shared contract type")
    system.__post_init__()
    target = _id(target, "Target")
    if target not in _TARGETS:
        raise DigitalExportError("Target must be web or app")

    payload: dict[str, str] = {}
    for role in system.typography:
        prefix = f"type.{role.role_id}"
        payload[f"{prefix}.family"] = role.family_id
        payload[f"{prefix}.size-rem"] = format(role.size_rem, ".12g")
        payload[f"{prefix}.line-height"] = format(role.line_height, ".12g")
        payload[f"{prefix}.weight"] = str(role.weight)
        payload[f"{prefix}.tracking-em"] = format(role.tracking_em, ".12g")
        payload[f"{prefix}.max-line-chars"] = str(role.max_line_chars)
    for appearance in system.appearances:
        prefix = f"appearance.{appearance.appearance}"
        for name in ("surface", "text", "accent", "divider", "focus"):
            payload[f"{prefix}.{name}"] = getattr(appearance, name)

    canonical = tuple(sorted(payload.items()))
    encoded = json.dumps(dict(canonical), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    payload_sha = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return DigitalTargetExport(target, system.manifest_sha256, payload_sha, canonical)
