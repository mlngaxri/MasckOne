import pytest

from masck_one.canonical_visual_source import (
    CanonicalVisualSourceError,
    build_canonical_digital_exports,
    build_canonical_visual_system,
)
from masck_one.design_language import ColorRole, MotionToken, ShapeToken, UnifiedDesignLanguage


class LyingStr(str):
    def __eq__(self, other): return True
    def __ne__(self, other): return False
    def __hash__(self): return str.__hash__(self)


def language(*, engineering_sha: str = "a" * 64) -> UnifiedDesignLanguage:
    return UnifiedDesignLanguage(
        contract_id="masck-one.launch-v1",
        engineering_manifest_sha256=engineering_sha,
        colors=(ColorRole("surface.primary", "#e8e5dc", "#1d211f"),),
        shapes=(ShapeToken("aperture.primary", 12.0, "shell.eye-aperture"),),
        motions=(MotionToken("reveal.primary", 620, "decelerate", "fade"),),
    )


def test_canonical_visual_source_is_deterministic_and_exactly_bound() -> None:
    upstream = language()
    expected = upstream.manifest_sha256
    first = build_canonical_visual_system(upstream, expected_design_language_sha256=expected)
    second = build_canonical_visual_system(language(), expected_design_language_sha256=expected)

    assert first.manifest == second.manifest
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.contract_id == "masck-one.visual-v1"
    assert first.design_language_sha256 == expected
    assert tuple(role.role_id for role in first.typography) == ("body", "display", "metadata")
    assert tuple(role.appearance for role in first.appearances) == ("dark", "high-contrast", "light")
    assert first.physical_validation_eligible is False


def test_requires_exact_upstream_identity_without_placeholder_fallback() -> None:
    upstream = language()
    with pytest.raises(CanonicalVisualSourceError):
        build_canonical_visual_system(upstream, expected_design_language_sha256="b" * 64)
    with pytest.raises(CanonicalVisualSourceError):
        build_canonical_visual_system(upstream, expected_design_language_sha256=LyingStr(upstream.manifest_sha256))
    with pytest.raises(CanonicalVisualSourceError):
        build_canonical_visual_system(upstream, expected_design_language_sha256="fixture")
    with pytest.raises(CanonicalVisualSourceError):
        build_canonical_visual_system(object(), expected_design_language_sha256="a" * 64)


def test_post_construction_upstream_corruption_fails_closed() -> None:
    upstream = language()
    expected = upstream.manifest_sha256
    object.__setattr__(upstream, "engineering_manifest_sha256", "not-a-sha")
    with pytest.raises(CanonicalVisualSourceError):
        build_canonical_visual_system(upstream, expected_design_language_sha256=expected)


def test_upstream_semantic_change_requires_new_expected_identity() -> None:
    original = language()
    expected = original.manifest_sha256
    changed = UnifiedDesignLanguage(
        contract_id="masck-one.launch-v1",
        engineering_manifest_sha256="a" * 64,
        colors=(ColorRole("surface.primary", "#e7e4db", "#1d211f"),),
        shapes=original.shapes,
        motions=original.motions,
    )
    assert changed.manifest_sha256 != expected
    with pytest.raises(CanonicalVisualSourceError):
        build_canonical_visual_system(changed, expected_design_language_sha256=expected)


def test_web_and_app_exports_share_both_required_semantic_hashes() -> None:
    upstream = language()
    web, app = build_canonical_digital_exports(
        upstream,
        expected_design_language_sha256=upstream.manifest_sha256,
    )
    assert (web.target, app.target) == ("web", "app")
    assert web.visual_system_sha256 == app.visual_system_sha256
    assert web.payload_sha256 == app.payload_sha256
    assert web.payload == app.payload
    assert web.manifest_sha256 != app.manifest_sha256
    assert web.physical_validation_eligible is False
    assert app.physical_validation_eligible is False


def test_engineering_identity_change_propagates_through_dual_hash_chain() -> None:
    first = language(engineering_sha="a" * 64)
    second = language(engineering_sha="b" * 64)
    first_web, _ = build_canonical_digital_exports(
        first,
        expected_design_language_sha256=first.manifest_sha256,
    )
    second_web, _ = build_canonical_digital_exports(
        second,
        expected_design_language_sha256=second.manifest_sha256,
    )
    assert first.manifest_sha256 != second.manifest_sha256
    assert first_web.visual_system_sha256 != second_web.visual_system_sha256
    assert first_web.payload_sha256 == second_web.payload_sha256
    assert first_web.manifest_sha256 != second_web.manifest_sha256
