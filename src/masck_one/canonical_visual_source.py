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
    authenticated_design_language_sha256: object,
) -> UnifiedDesignLanguage:
    """Revalidate a language and require an externally authenticated exact identity.

    This module deliberately does not decide whether an upstream design-language
    manifest is released or authentic. That responsibility belongs to the digital
    release boundary. The authenticated digest is therefore a mandatory input, not
    a value reconstructed or invented here.
    """
    if type(language) is not UnifiedDesignLanguage:
        raise CanonicalVisualSourceError("Design language must be the exact shared contract type")
    expected = _sha(authenticated_design_language_sha256, "Authenticated design-language SHA")
    try:
        language.__post_init__()
        actual = language.manifest_sha256
    except DesignLanguageError:
        raise CanonicalVisualSourceError("Design language failed invariant revalidation") from None
    if actual != expected:
        raise CanonicalVisualSourceError("Design language does not match authenticated upstream identity")
    return language


def build_canonical_visual_system(
    language: object,
    *,
    authenticated_design_language_sha256: object,
) -> AdaptiveVisualSystem:
    """Build the canonical Cell-2 adaptive presentation system.

    Typography and appearance values are presentation semantics only. They are not
    geometry authority, CMF approval, hardware evidence, or physical validation.
    The caller must provide the exact authenticated digest of the supplied upstream
    design-language manifest. No fixture or placeholder provenance is accepted.
    """
    validated = _validated_language(language, authenticated_design_language_sha256)
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
    authenticated_design_language_sha256: object,
) -> tuple[DigitalTargetExport, DigitalTargetExport]:
    """Return canonically ordered web/app exports from one authenticated language."""
    system = build_canonical_visual_system(
        language,
        authenticated_design_language_sha256=authenticated_design_language_sha256,
    )
    web = export_visual_system(system, "web")
    app = export_visual_system(system, "app")
    if web.visual_system_sha256 != app.visual_system_sha256 or web.payload_sha256 != app.payload_sha256:
        raise CanonicalVisualSourceError("Canonical web/app exports diverged in shared visual semantics")
    return web, app
