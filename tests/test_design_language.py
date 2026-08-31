import pytest

from masck_one.design_language import ColorRole, DesignLanguageError, MotionToken, ShapeToken, UnifiedDesignLanguage

SHA = "a" * 64


class LyingStr(str):
    def __eq__(self, other): return True
    def __ne__(self, other): return False
    def __hash__(self): return str.__hash__(self)


def contract(**kwargs):
    base = dict(
        contract_id="masck-one.launch-v1",
        engineering_manifest_sha256=SHA,
        colors=(ColorRole("surface.primary", "#e8e5dc", "#1d211f"),),
        shapes=(ShapeToken("aperture.primary", 12.0, "shell.eye-aperture"),),
        motions=(MotionToken("reveal.primary", 620, "decelerate", "fade"),),
    )
    base.update(kwargs)
    return UnifiedDesignLanguage(**base)


def test_contract_is_deterministic_and_freshness_bound():
    first, second = contract(), contract()
    assert first.manifest_sha256 == second.manifest_sha256
    first.assert_current_engineering_manifest(SHA)


def test_manifest_changes_when_visual_semantics_change():
    first = contract()
    second = contract(colors=(ColorRole("surface.primary", "#e7e4db", "#1d211f"),))
    assert first.manifest_sha256 != second.manifest_sha256


def test_rejects_stale_or_hostile_engineering_identity():
    item = contract()
    with pytest.raises(DesignLanguageError): item.assert_current_engineering_manifest("b" * 64)
    with pytest.raises(DesignLanguageError): contract(engineering_manifest_sha256=LyingStr(SHA))
    with pytest.raises(DesignLanguageError): item.assert_current_engineering_manifest(LyingStr(SHA))


def test_tokens_require_canonical_sorted_unique_exact_types():
    with pytest.raises(DesignLanguageError): contract(colors=(ColorRole("z", "#ffffff", "#000000"), ColorRole("a", "#ffffff", "#000000")))
    with pytest.raises(DesignLanguageError): contract(colors=(ColorRole("a", "#ffffff", "#000000"), ColorRole("a", "#eeeeee", "#000000")))
    with pytest.raises(DesignLanguageError): ColorRole("Surface", "#ffffff", "#000000")
    with pytest.raises(DesignLanguageError): ColorRole("surface", "#FFFFFF", "#000000")


def test_color_roles_enforce_wcag_aa_normal_text_contrast():
    ColorRole("surface", "#ffffff", "#767676")
    with pytest.raises(DesignLanguageError):
        ColorRole("surface", "#ffffff", "#777777")
    with pytest.raises(DesignLanguageError):
        ColorRole("surface", "#ffffff", "#fffffe")
    with pytest.raises(DesignLanguageError):
        ColorRole("surface", "#123456", "#123456")


def test_numeric_and_motion_boundaries_fail_closed():
    for bad in (True, float("nan"), float("inf"), -1.0):
        with pytest.raises(DesignLanguageError): ShapeToken("shape", bad, "shell.edge")
    with pytest.raises(DesignLanguageError): MotionToken("motion", True, "linear", "fade")
    with pytest.raises(DesignLanguageError): MotionToken("motion", 5001, "linear", "fade")
    with pytest.raises(DesignLanguageError): MotionToken("motion", 100, "linear", "zoom")


def test_oversized_integer_shape_radius_fails_through_controlled_boundary():
    huge = 10 ** 10000
    for value in (huge, -huge):
        with pytest.raises(DesignLanguageError):
            ShapeToken("shape", value, "shell.edge")
    control = ShapeToken("shape", 10 ** 100, "shell.edge")
    assert control.radius_mm == float(10 ** 100)


def test_shared_motion_easing_is_portable_not_engine_specific():
    for easing in ("linear", "standard", "decelerate", "accelerate", "emphasized"):
        MotionToken("motion", 100, easing, "fade")
    for easing in ("power2.out", "cubic-bezier", "spring.ios", "ease-in-out"):
        with pytest.raises(DesignLanguageError): MotionToken("motion", 100, easing, "fade")


def test_reduced_motion_requires_explicit_comprehension_preserving_fallback():
    for behavior in ("fade", "instant", "static"):
        MotionToken("motion", 100, "standard", behavior)
    for behavior in ("none", "inherit", "auto", "disabled"):
        with pytest.raises(DesignLanguageError):
            MotionToken("motion", 100, "standard", behavior)
    with pytest.raises(DesignLanguageError):
        MotionToken("motion", 100, "standard", LyingStr("fade"))


def test_signed_zero_shape_radius_has_one_canonical_identity():
    positive = contract(shapes=(ShapeToken("shape", 0.0, "shell.edge"),))
    negative = contract(shapes=(ShapeToken("shape", -0.0, "shell.edge"),))
    assert negative.shapes[0].radius_mm == 0.0
    assert negative.manifest == positive.manifest
    assert negative.manifest_sha256 == positive.manifest_sha256


def test_presentation_contract_cannot_promote_physical_evidence():
    with pytest.raises(DesignLanguageError): contract(physical_validation_eligible=True)
    with pytest.raises(DesignLanguageError): contract(evidence_status="PHYSICALLY_VALIDATED")


def test_post_construction_corruption_is_detected():
    item = contract()
    object.__setattr__(item, "engineering_manifest_sha256", "b" * 64)
    with pytest.raises(DesignLanguageError): item.assert_current_engineering_manifest(SHA)
