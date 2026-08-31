from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re


class VisualSystemError(ValueError):
    """Raised when shared Masck One visual semantics are ambiguous or unsafe."""


_SCHEMA = "MASCK_ONE_VISUAL_SYSTEM_V1"
_EVIDENCE = "PRESENTATION_CONTRACT_ONLY_NOT_ENGINEERING_OR_PHYSICAL_EVIDENCE"
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_HEX_RE = re.compile(r"^#[0-9a-f]{6}$")
_ALLOWED_APPEARANCES = frozenset(("light", "dark", "high-contrast"))
_ALLOWED_TYPE_ROLES = frozenset(("display", "title", "body", "label", "metadata", "numeric"))
_MIN_TEXT_CONTRAST = 4.5
_MIN_FOCUS_CONTRAST = 3.0


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value:
        raise VisualSystemError(f"{label} must be exact nonempty built-in text")
    return value


def _id(value: object, label: str) -> str:
    value = _text(value, label)
    if not _ID_RE.fullmatch(value):
        raise VisualSystemError(f"{label} must be a canonical lowercase identifier")
    return value


def _sha(value: object, label: str) -> str:
    value = _text(value, label)
    if not _SHA_RE.fullmatch(value):
        raise VisualSystemError(f"{label} must be canonical SHA-256")
    return value


def _hex(value: object, label: str) -> str:
    value = _text(value, label)
    if not _HEX_RE.fullmatch(value):
        raise VisualSystemError(f"{label} must be canonical six-digit lowercase hex")
    return value


def _number(value: object, label: str, *, minimum: float, maximum: float) -> float:
    if type(value) not in (int, float):
        raise VisualSystemError(f"{label} must be an exact numeric value")
    try:
        result = float(value)
    except (OverflowError, ValueError):
        raise VisualSystemError(f"{label} must be representable as finite binary64") from None
    if not minimum <= result <= maximum:
        raise VisualSystemError(f"{label} must be within [{minimum}, {maximum}]")
    return 0.0 if result == 0.0 else result


def _relative_luminance(color: str) -> float:
    """WCAG sRGB relative luminance for an already canonical #rrggbb color."""
    channels = tuple(int(color[index:index + 2], 16) / 255.0 for index in (1, 3, 5))
    linear = tuple(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels)
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


@dataclass(frozen=True, slots=True)
class TypographyRole:
    role_id: str
    family_id: str
    size_rem: float
    line_height: float
    weight: int
    tracking_em: float
    max_line_chars: int

    def __post_init__(self) -> None:
        role = _id(self.role_id, "Typography role")
        if role not in _ALLOWED_TYPE_ROLES:
            raise VisualSystemError("Typography role is outside the shared semantic vocabulary")
        _id(self.family_id, "Font family identity")
        object.__setattr__(self, "size_rem", _number(self.size_rem, "Type size", minimum=0.6875, maximum=8.0))
        object.__setattr__(self, "line_height", _number(self.line_height, "Line height", minimum=0.9, maximum=2.0))
        if type(self.weight) is not int or not 100 <= self.weight <= 900:
            raise VisualSystemError("Font weight must be an exact integer from 100 to 900")
        object.__setattr__(self, "tracking_em", _number(self.tracking_em, "Tracking", minimum=-0.08, maximum=0.2))
        if type(self.max_line_chars) is not int or not 20 <= self.max_line_chars <= 90:
            raise VisualSystemError("Maximum line length must be an exact integer from 20 to 90 characters")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "role_id": self.role_id,
            "family_id": self.family_id,
            "size_rem": self.size_rem,
            "line_height": self.line_height,
            "weight": self.weight,
            "tracking_em": self.tracking_em,
            "max_line_chars": self.max_line_chars,
        }


@dataclass(frozen=True, slots=True)
class AppearanceRole:
    role_id: str
    appearance: str
    surface: str
    text: str
    accent: str
    divider: str
    focus: str

    def __post_init__(self) -> None:
        _id(self.role_id, "Appearance role")
        appearance = _id(self.appearance, "Appearance")
        if appearance not in _ALLOWED_APPEARANCES:
            raise VisualSystemError("Appearance must be light, dark, or high-contrast")
        for label, value in (("Surface", self.surface), ("Text", self.text), ("Accent", self.accent), ("Divider", self.divider), ("Focus", self.focus)):
            _hex(value, label)
        if _contrast_ratio(self.surface, self.text) < _MIN_TEXT_CONTRAST:
            raise VisualSystemError("Text must provide at least 4.5:1 contrast against its surface")
        if _contrast_ratio(self.surface, self.focus) < _MIN_FOCUS_CONTRAST:
            raise VisualSystemError("Focus indication must provide at least 3:1 contrast against its surface")

    def manifest(self) -> dict[str, str]:
        self.__post_init__()
        return {key: getattr(self, key) for key in ("role_id", "appearance", "surface", "text", "accent", "divider", "focus")}


@dataclass(frozen=True, slots=True)
class AdaptiveVisualSystem:
    contract_id: str
    design_language_sha256: str
    typography: tuple[TypographyRole, ...]
    appearances: tuple[AppearanceRole, ...]
    evidence_status: str = _EVIDENCE
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        _id(self.contract_id, "Contract identity")
        _sha(self.design_language_sha256, "Design-language SHA")
        self._group(self.typography, TypographyRole, "typography", lambda item: item.role_id)
        self._group(self.appearances, AppearanceRole, "appearances", lambda item: item.role_id)
        appearance_names = tuple(item.appearance for item in self.appearances)
        if set(appearance_names) != _ALLOWED_APPEARANCES or len(appearance_names) != len(_ALLOWED_APPEARANCES):
            raise VisualSystemError("Exactly one light, dark, and high-contrast appearance is required")
        if type(self.evidence_status) is not str or self.evidence_status != _EVIDENCE:
            raise VisualSystemError("Evidence status is controlled")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise VisualSystemError("Visual-system tokens cannot become physical evidence")

    @staticmethod
    def _group(values: object, expected: type, label: str, identity) -> None:
        if type(values) is not tuple or not values or not all(type(item) is expected for item in values):
            raise VisualSystemError(f"{label} must be a nonempty immutable tuple of exact token types")
        for item in values:
            item.__post_init__()
        ids = tuple(identity(item) for item in values)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise VisualSystemError(f"{label} identities must be unique and canonically sorted")

    def assert_current_design_language(self, current_sha256: object) -> None:
        self.__post_init__()
        if _sha(current_sha256, "Current design-language SHA") != self.design_language_sha256:
            raise VisualSystemError("Visual system is stale for current design language")

    @property
    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "schema": _SCHEMA,
            "contract_id": self.contract_id,
            "design_language_sha256": self.design_language_sha256,
            "typography": [item.manifest() for item in self.typography],
            "appearances": [item.manifest() for item in self.appearances],
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }

    @property
    def manifest_sha256(self) -> str:
        payload = json.dumps(self.manifest, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
