from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re


class DesignLanguageError(ValueError):
    """Raised when a Masck One presentation contract is ambiguous or unsafe."""


_SCHEMA = "MASCK_ONE_DESIGN_LANGUAGE_V1"
_EVIDENCE = "PRESENTATION_CONTRACT_ONLY_NOT_ENGINEERING_OR_PHYSICAL_EVIDENCE"
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_HEX_RE = re.compile(r"^#[0-9a-f]{6}$")
_PORTABLE_EASINGS = frozenset(("linear", "standard", "decelerate", "accelerate", "emphasized"))
_REDUCED_MOTION_BEHAVIORS = frozenset(("fade", "instant", "static"))
_MIN_TEXT_CONTRAST = 4.5


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value:
        raise DesignLanguageError(f"{label} must be exact nonempty built-in text")
    return value


def _id(value: object, label: str) -> str:
    value = _text(value, label)
    if not _ID_RE.fullmatch(value):
        raise DesignLanguageError(f"{label} must be a canonical lowercase identifier")
    return value


def _hex(value: object, label: str) -> str:
    value = _text(value, label)
    if not _HEX_RE.fullmatch(value):
        raise DesignLanguageError(f"{label} must be canonical six-digit lowercase hex")
    return value


def _number(value: object, label: str, *, minimum: float = 0.0) -> float:
    if type(value) not in (int, float):
        raise DesignLanguageError(f"{label} must be an exact numeric value")
    try:
        result = float(value)
    except (OverflowError, ValueError):
        raise DesignLanguageError(f"{label} must be representable as a finite binary64 value") from None
    if not minimum <= result < float("inf"):
        raise DesignLanguageError(f"{label} must be finite and >= {minimum}")
    return 0.0 if result == 0.0 else result


def _relative_luminance(value: str) -> float:
    """WCAG sRGB relative luminance for a canonical opaque six-digit hex color."""
    value = _hex(value, "Color")
    channels = tuple(int(value[index:index + 2], 16) / 255.0 for index in (1, 3, 5))

    def linearize(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linearize(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast_ratio(first: str, second: str) -> float:
    high, low = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@dataclass(frozen=True, slots=True)
class ColorRole:
    """Opaque surface color plus its default normal-text color.

    Shared launch tokens require WCAG AA normal-text contrast (4.5:1). Large-text,
    translucent and composited presentation colors need separate explicit semantics
    rather than weakening this portable baseline.
    """

    role_id: str
    value: str
    contrast_text: str

    def __post_init__(self) -> None:
        _id(self.role_id, "Color role")
        _hex(self.value, "Color value")
        _hex(self.contrast_text, "Contrast text")
        if _contrast_ratio(self.value, self.contrast_text) < _MIN_TEXT_CONTRAST:
            raise DesignLanguageError("Color role default text contrast must be at least 4.5:1")

    def manifest(self) -> dict[str, str]:
        self.__post_init__()
        return {"role_id": self.role_id, "value": self.value, "contrast_text": self.contrast_text}


@dataclass(frozen=True, slots=True)
class ShapeToken:
    token_id: str
    radius_mm: float
    source_feature_id: str

    def __post_init__(self) -> None:
        _id(self.token_id, "Shape token")
        canonical = _number(self.radius_mm, "Shape radius")
        if canonical != self.radius_mm or (canonical == 0.0 and math.copysign(1.0, float(self.radius_mm)) < 0.0):
            object.__setattr__(self, "radius_mm", canonical)
        _id(self.source_feature_id, "Source feature")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {"token_id": self.token_id, "radius_mm": _number(self.radius_mm, "Shape radius"), "source_feature_id": self.source_feature_id}


@dataclass(frozen=True, slots=True)
class MotionToken:
    token_id: str
    duration_ms: int
    easing: str
    reduced_motion: str

    def __post_init__(self) -> None:
        _id(self.token_id, "Motion token")
        if type(self.duration_ms) is not int or not 0 <= self.duration_ms <= 5000:
            raise DesignLanguageError("Motion duration must be an exact integer from 0 to 5000 ms")
        easing = _id(self.easing, "Motion easing")
        if easing not in _PORTABLE_EASINGS:
            raise DesignLanguageError("Motion easing must use the portable shared vocabulary")
        reduced = _id(self.reduced_motion, "Reduced-motion behavior")
        if reduced not in _REDUCED_MOTION_BEHAVIORS:
            raise DesignLanguageError("Reduced-motion behavior must explicitly preserve comprehension as fade, instant, or static")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {"token_id": self.token_id, "duration_ms": self.duration_ms, "easing": self.easing, "reduced_motion": self.reduced_motion}


@dataclass(frozen=True, slots=True)
class UnifiedDesignLanguage:
    """Split-ready presentation vocabulary shared by hardware-derived web/app surfaces.

    This contract intentionally contains presentation semantics only. Geometry remains
    authoritative in released engineering manifests and must never be reconstructed
    from these tokens.
    """

    contract_id: str
    engineering_manifest_sha256: str
    colors: tuple[ColorRole, ...]
    shapes: tuple[ShapeToken, ...]
    motions: tuple[MotionToken, ...]
    evidence_status: str = _EVIDENCE
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        _id(self.contract_id, "Contract identity")
        sha = _text(self.engineering_manifest_sha256, "Engineering manifest SHA")
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise DesignLanguageError("Engineering manifest SHA must be canonical SHA-256")
        self._validate_group(self.colors, ColorRole, "colors")
        self._validate_group(self.shapes, ShapeToken, "shapes")
        self._validate_group(self.motions, MotionToken, "motions")
        if type(self.evidence_status) is not str or self.evidence_status != _EVIDENCE:
            raise DesignLanguageError("Evidence status is controlled")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise DesignLanguageError("Presentation tokens cannot become physical evidence")

    @staticmethod
    def _validate_group(values: object, expected: type, label: str) -> None:
        if type(values) is not tuple or not values:
            raise DesignLanguageError(f"{label} must be a nonempty immutable tuple")
        if not all(type(item) is expected for item in values):
            raise DesignLanguageError(f"{label} contains an invalid token type")
        for item in values:
            item.__post_init__()
        ids = tuple(item.role_id if expected is ColorRole else item.token_id for item in values)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise DesignLanguageError(f"{label} identities must be unique and canonically sorted")

    def assert_current_engineering_manifest(self, current_sha256: object) -> None:
        self.__post_init__()
        current = _text(current_sha256, "Current engineering manifest SHA")
        if not re.fullmatch(r"[0-9a-f]{64}", current) or current != self.engineering_manifest_sha256:
            raise DesignLanguageError("Design language is stale for current engineering presentation geometry")

    @property
    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "schema": _SCHEMA,
            "contract_id": self.contract_id,
            "engineering_manifest_sha256": self.engineering_manifest_sha256,
            "colors": [item.manifest() for item in self.colors],
            "shapes": [item.manifest() for item in self.shapes],
            "motions": [item.manifest() for item in self.motions],
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }

    @property
    def manifest_sha256(self) -> str:
        payload = json.dumps(self.manifest, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
