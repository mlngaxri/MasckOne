from __future__ import annotations

import re

from .design_language import DesignLanguageError, UnifiedDesignLanguage
from .digital_export import DigitalTargetExport, export_visual_system
from .visual_system import AdaptiveVisualSystem, AppearanceRole, TypographyRole


class CanonicalVisualSourceError(ValueError):
    """Raised when canonical Cell-2 presentation semantics cannot bind safely upstream."""


_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_CONTRACT_ID = "masck-one.visual-v1"


def _sha(value: object, label: str) -> str:
    if type(value) is not str or not _SHA_RE.fullmatch(value):
        raise CanonicalVisualSourceError(f"{label} must be an exact canonical SHA-256")
    return value


def _validated_language(
    language: object,
    expected_design_language_sha256: object,
) -> UnifiedDesignLanguage:
    """Revalidate a language and require one exact externally supplied identity.

    This is an equality/freshness guard, not an authentication mechanism. The caller
    is responsible for obtaining the expected digest from a separately authenticated
    release boundary. No release state is inferred from a syntactically valid hash.
    """
    if type(language) is not UnifiedDesignLanguage:
        raise CanonicalVisualSourceError("Design language must be the exact shared contract type")
    expected = _sha(expected_design_language_sha256, "Expected design-language SHA")
    try:
        language.__post_init__()
        actual = language.manifest_sha256
    except DesignLanguageError:
        raise CanonicalVisualSourceError("Design language failed invariant revalidation") from None
    if actual != expected:
        raise CanonicalVisualSourceError("Design language does not match expected upstream identity")
    return language


def build_canonical_visual_system(
    language: object,
    *,
    expected_design_language_sha256: object,
) -> AdaptiveVisualSystem:
    """Build canonical Cell-2 presentation semantics against one exact upstream identity.

    Typography and appearance values are presentation semantics only. They are not
    geometry authority, CMF approval, engineering evidence, or physical validation.
    The expected digest is only a freshness guard here. A production caller must get
    it from an authenticated release artifact; this module does not authenticate it.
    """
    validated = _validated_language(language, expected_design_language_sha256)
    return AdaptiveVisualSystem(
        contract_id=_CONTRACT_ID,
        design_language_sha256=validated.manifest_sha256,
        typography=(
            TypographyRole("body", "text.primary", 1.0, 1.5, 450, 0.0, 68),
            TypographyRole("display", "display.primary", 4.0, 0.98, 520, -0.035, 32),
            TypographyRole("metadata", "text.primary", 0.75, 1.35, 550, 0.04, 48),
        ),
        appearances=(
            AppearanceRole("appearance.dark", "dark", "#171917", "#f0eee7", "#b7c9b0", "#4b504b", "#d6e7cf"),
            AppearanceRole("appearance.high-contrast", "high-contrast", "#000000", "#ffffff", "#ffffff", "#ffffff", "#ffffff"),
            AppearanceRole("appearance.light", "light", "#e8e5dc", "#1d211f", "#526a55", "#a8aaa3", "#314f38"),
        ),
    )


def build_canonical_digital_exports(
    language: object,
    *,
    expected_design_language_sha256: object,
) -> tuple[DigitalTargetExport, DigitalTargetExport]:
    """Return canonically ordered web/app exports from one exact upstream identity."""
    system = build_canonical_visual_system(
        language,
        expected_design_language_sha256=expected_design_language_sha256,
    )
    web = export_visual_system(system, "web")
    app = export_visual_system(system, "app")
    if web.visual_system_sha256 != app.visual_system_sha256 or web.payload_sha256 != app.payload_sha256:
        raise CanonicalVisualSourceError("Canonical web/app exports diverged in shared visual semantics")
    return web, app
