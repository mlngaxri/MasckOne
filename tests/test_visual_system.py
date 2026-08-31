import pytest

from masck_one.visual_system import AdaptiveVisualSystem, AppearanceRole, TypographyRole, VisualSystemError

SHA = "a" * 64


class LyingStr(str):
    def __eq__(self, other): return True
    def __ne__(self, other): return False
    def __hash__(self): return str.__hash__(self)


def system(**kwargs):
    base = dict(
        contract_id="masck-one.visual-v1",
        design_language_sha256=SHA,
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
    base.update(kwargs)
    return AdaptiveVisualSystem(**base)


def test_manifest_is_deterministic_and_freshness_bound():
    first, second = system(), system()
    assert first.manifest_sha256 == second.manifest_sha256
    first.assert_current_design_language(SHA)
    with pytest.raises(VisualSystemError):
        first.assert_current_design_language("b" * 64)


def test_rejects_hostile_or_noncanonical_provenance():
    with pytest.raises(VisualSystemError): system(design_language_sha256=LyingStr(SHA))
    with pytest.raises(VisualSystemError): system().assert_current_design_language(LyingStr(SHA))
    with pytest.raises(VisualSystemError): system(design_language_sha256="A" * 64)


def test_requires_complete_adaptive_appearance_set():
    valid = system().appearances
    with pytest.raises(VisualSystemError): system(appearances=valid[:-1])
    duplicate_dark = (valid[0], valid[1], AppearanceRole("appearance.light", "dark", "#111111", "#ffffff", "#eeeeee", "#aaaaaa", "#ffffff"))
    with pytest.raises(VisualSystemError): system(appearances=duplicate_dark)


def test_rejects_insufficient_text_or_focus_contrast():
    with pytest.raises(VisualSystemError):
        AppearanceRole("x", "light", "#ffffff", "#777777", "#000000", "#cccccc", "#000000")
    with pytest.raises(VisualSystemError):
        AppearanceRole("x", "light", "#ffffff", "#000000", "#111111", "#cccccc", "#999999")
    AppearanceRole("x", "light", "#ffffff", "#767676", "#111111", "#cccccc", "#949494")


def test_identity_difference_does_not_masquerade_as_accessibility():
    with pytest.raises(VisualSystemError):
        AppearanceRole("x", "light", "#ffffff", "#fffffe", "#000000", "#cccccc", "#000000")
    with pytest.raises(VisualSystemError):
        AppearanceRole("x", "light", "#ffffff", "#000000", "#111111", "#cccccc", "#fffffe")


def test_typography_bounds_fail_closed():
    with pytest.raises(VisualSystemError): TypographyRole("body", "text.primary", 0.5, 1.5, 400, 0.0, 60)
    with pytest.raises(VisualSystemError): TypographyRole("body", "text.primary", 1.0, 1.5, 950, 0.0, 60)
    with pytest.raises(VisualSystemError): TypographyRole("body", "text.primary", 1.0, 1.5, 400, 0.0, 100)
    with pytest.raises(VisualSystemError): TypographyRole("body", "text.primary", 10**10000, 1.5, 400, 0.0, 60)


def test_bool_nan_inf_and_unsorted_groups_are_rejected():
    with pytest.raises(VisualSystemError): TypographyRole("body", "text.primary", True, 1.5, 400, 0.0, 60)
    with pytest.raises(VisualSystemError): TypographyRole("body", "text.primary", float("nan"), 1.5, 400, 0.0, 60)
    with pytest.raises(VisualSystemError): TypographyRole("body", "text.primary", 1.0, float("inf"), 400, 0.0, 60)
    typography = system().typography
    with pytest.raises(VisualSystemError): system(typography=tuple(reversed(typography)))


def test_visual_semantic_change_changes_digest():
    first = system()
    changed = system(typography=(
        TypographyRole("body", "text.primary", 1.0, 1.55, 450, 0.0, 68),
        TypographyRole("display", "display.primary", 4.0, 0.98, 520, -0.035, 32),
        TypographyRole("metadata", "text.primary", 0.75, 1.35, 550, 0.04, 48),
    ))
    assert first.manifest_sha256 != changed.manifest_sha256


def test_evidence_firewall_is_exact():
    with pytest.raises(VisualSystemError): system(physical_validation_eligible=True)
    with pytest.raises(VisualSystemError): system(physical_validation_eligible=1)
    with pytest.raises(VisualSystemError): system(evidence_status=LyingStr("PRESENTATION_CONTRACT_ONLY_NOT_ENGINEERING_OR_PHYSICAL_EVIDENCE"))
