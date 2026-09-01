import pytest

from masck_one.appearance_shell_dfm import AppearanceShellDFMError, validate_appearance_shell_dfm


def good():
    return {
        "ID_SHELL_WALL_MIN": 1.9,
        "ID_SHELL_WALL_MAX": 2.2,
        "ID_SHELL_VISIBLE_DRAFT_MIN": 1.5,
        "ID_SHELL_MAX_RIB_THICKNESS": 1.2,
        "ID_SHELL_MAX_BOSS_WALL": 1.35,
        "ID_SHELL_NOMINAL_WALL": 2.0,
    }


def test_accepts_balanced_visible_shell_dfm_evidence():
    validate_appearance_shell_dfm(good())


@pytest.mark.parametrize("key,value", [
    ("ID_SHELL_WALL_MIN", 1.7),
    ("ID_SHELL_WALL_MAX", 2.6),
    ("ID_SHELL_VISIBLE_DRAFT_MIN", 0.5),
    ("ID_SHELL_MAX_RIB_THICKNESS", 1.3),
    ("ID_SHELL_MAX_BOSS_WALL", 1.5),
])
def test_rejects_sink_warp_or_release_risk(key, value):
    v = good(); v[key] = value
    with pytest.raises(AppearanceShellDFMError):
        validate_appearance_shell_dfm(v)


def test_rejects_excessive_wall_range_even_inside_absolute_band():
    v = good(); v["ID_SHELL_WALL_MIN"] = 1.8; v["ID_SHELL_WALL_MAX"] = 2.3
    with pytest.raises(AppearanceShellDFMError):
        validate_appearance_shell_dfm(v)


def test_fails_closed_on_missing_or_nonfinite_evidence():
    v = good(); del v["ID_SHELL_VISIBLE_DRAFT_MIN"]
    with pytest.raises(AppearanceShellDFMError): validate_appearance_shell_dfm(v)
    v = good(); v["ID_SHELL_WALL_MAX"] = float("nan")
    with pytest.raises(AppearanceShellDFMError): validate_appearance_shell_dfm(v)
