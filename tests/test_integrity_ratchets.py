"""Guards against the ways an automated contributor quietly weakens this repo.

Several autonomous agents work this repository in parallel, and more than one
toolchain now edits it. That is a fine way to build quickly and a very easy way
to lose rigour, because the cheapest route past a failing gate is almost always
to soften the gate rather than fix the design. ENGINEERING_GOVERNANCE.md forbids
that; this file makes it fail.

Each guard is a **ratchet**: it pins where the repository stands today and
allows movement in the safe direction only. A contributor may add tests, add
evidence gates, and tighten tolerances freely. Removing tests, hiding failures
behind skips, deleting evidence gates, loosening a numerical tolerance or
relaxing a frozen safety requirement all fail, loudly, with the reason.

None of these guards judge *design*. They judge whether the repository's own
safeguards are still standing. Raising a pinned number is not forbidden -- it is
forbidden to do it silently, which is the point: the diff that raises it is the
conversation.
"""

from __future__ import annotations

import ast
from pathlib import Path
import re

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
SRC = ROOT / "src" / "masck_one"
AUTHORITY = ROOT / "config" / "masck_one_authority.yaml"


# ---------------------------------------------------------------------------
# baselines, measured at the commit that introduced this file
# ---------------------------------------------------------------------------

MIN_TEST_FUNCTIONS = 1016
MAX_SKIP_MARKERS = 2          # the two git-history skips in test_pinned_commits
MIN_EVIDENCE_MARKERS = 152

# Numerical tolerances may shrink, never grow. Loosening one of these is the
# classic way to make a geometry failure disappear without fixing the geometry.
MAX_TOLERANCES: dict[tuple[str, str], float] = {
    ("model.py", "CAD_BREP_BOUND_TOLERANCE_MM"): 2e-6,
    ("model.py", "CAD_PLANAR_FACE_SPAN_TOLERANCE_MM"): 1e-10,
    ("model.py", "CAD_AXIS_NORMAL_TOLERANCE"): 1e-9,
    ("step_integrity.py", "INTEGRATION_TOLERANCE"): 1e-12,
    ("step_integrity.py", "STEP_SOLID_VOLUME_LIMIT_MM3"): 2e-4,
    ("step_integrity.py", "STEP_BOUND_LIMIT_MM"): 2e-6,
    ("step_integrity.py", "STEP_MATERIAL_DIFFERENCE_LIMIT_MM3"): 1e-7,
}

_SKIP_MARKER = re.compile(
    r"@pytest\.mark\.(skip|skipif|xfail)\b|pytest\.mark\.(skip|skipif|xfail)\s*\(|"
    r"pytest\.(skip|xfail)\s*\("
)
_EVIDENCE_MARKER = re.compile(
    r"VALIDATION_GATED|FROZEN_SAFETY_REQUIREMENT|FROZEN_REQUIREMENT|FROZEN_DATUM|"
    r"FROZEN_ARCHITECTURE|BLOCKED|NOT_[A-Z_]*EVIDENCE"
)


def _test_files() -> list[Path]:
    return sorted(TESTS.glob("test_*.py"))


def _source_files() -> list[Path]:
    return sorted(SRC.glob("*.py"))


@pytest.fixture(scope="module")
def authority_yaml() -> dict:
    return yaml.safe_load(AUTHORITY.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# coverage may not be deleted
# ---------------------------------------------------------------------------

def test_test_function_count_does_not_fall() -> None:
    """Deleting a test is how a failing design becomes a passing one."""

    total = 0
    for path in _test_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        total += sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        )

    assert total >= MIN_TEST_FUNCTIONS, (
        f"{total} test functions, down from the pinned floor of {MIN_TEST_FUNCTIONS}. "
        "Tests were removed. If a test is genuinely obsolete, lower "
        "MIN_TEST_FUNCTIONS in the same commit and say why."
    )


def test_failures_are_not_hidden_behind_skips() -> None:
    """A skip added to get green is indistinguishable from a deleted test."""

    found: list[str] = []
    for path in _test_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _SKIP_MARKER.search(line):
                found.append(f"{path.relative_to(ROOT)}:{lineno}")

    assert len(found) <= MAX_SKIP_MARKERS, (
        f"{len(found)} skip/xfail markers, above the pinned ceiling of "
        f"{MAX_SKIP_MARKERS}:\n  " + "\n  ".join(found)
        + "\n\nA skipped test proves nothing. Fix the design, or raise the ceiling "
        "in the same commit and say why."
    )


def test_every_skip_states_a_reason() -> None:
    """An unexplained skip cannot be reviewed."""

    for path in _test_files():
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"pytest\.mark\.skipif\s*\((.{0,400}?)\)\n", text, re.DOTALL):
            assert "reason" in match.group(1), (
                f"{path.relative_to(ROOT)} has a skipif without a reason"
            )


# ---------------------------------------------------------------------------
# the evidence firewall may not be dismantled
# ---------------------------------------------------------------------------

def test_evidence_gate_markers_do_not_fall() -> None:
    """The firewall between "checked digitally" and "physically validated".

    Deleting these markers is how an unvalidated value becomes an asserted fact.
    """

    total = sum(
        len(_EVIDENCE_MARKER.findall(path.read_text(encoding="utf-8")))
        for path in _source_files() + [AUTHORITY]
    )
    assert total >= MIN_EVIDENCE_MARKERS, (
        f"{total} evidence-gate markers, down from the pinned floor of "
        f"{MIN_EVIDENCE_MARKERS}. Gates were removed. Closing one legitimately "
        "means citing the evidence that closed it."
    )


def test_planar_development_surface_can_never_be_anatomical_evidence() -> None:
    """The single most load-bearing refusal in the repository.

    Every coverage, T-zone and misregistration result sits on a flat plane at
    Z=0. If that surface can ever claim anatomical eligibility, all of it
    silently becomes fit evidence.
    """

    from masck_one.facial_surface import FacialSurfaceDescriptor, FacialSurfaceError

    with pytest.raises(FacialSurfaceError):
        FacialSurfaceDescriptor(
            surface_id="X",
            kind="PLANAR_DEVELOPMENT_REFERENCE",
            evidence_status="X",
            source_asset_id=None,
            source_revision="X",
            source_sha256="0" * 64,
            anatomical_validation_eligible=True,
        )


# ---------------------------------------------------------------------------
# numerical tolerances may only tighten
# ---------------------------------------------------------------------------

def test_geometry_role_is_declared_not_inferred() -> None:
    """Role must be a fact about the body, not a restatement of assembly membership.

    Inferring it silently promoted reference envelopes to manufactured material
    and demoted unregistered real parts to reference geometry.
    """

    text = (SRC / "export.py").read_text(encoding="utf-8")
    assert '"PHYSICAL_MATERIAL" if included' not in text, (
        "geometry_role is being inferred from assembly inclusion again"
    )
    assert "component.geometry_role.value" in text


def test_named_tolerances_do_not_loosen() -> None:
    """Widening a tolerance makes a geometry failure vanish without a fix.

    ENGINEERING_GOVERNANCE forbids it; this makes it fail. A genuine kernel
    artifact is answered with a better invariant, not a bigger number.
    """

    loosened: list[str] = []
    for (filename, constant), ceiling in sorted(MAX_TOLERANCES.items()):
        text = (SRC / filename).read_text(encoding="utf-8")
        match = re.search(rf"^{re.escape(constant)}\s*=\s*([0-9.eE+-]+)", text, re.MULTILINE)
        if match is None:
            loosened.append(f"{filename}:{constant} no longer exists")
            continue
        value = float(match.group(1))
        if value > ceiling:
            loosened.append(f"{filename}:{constant} {value:g} > pinned {ceiling:g}")

    assert not loosened, "tolerances loosened or removed:\n  " + "\n  ".join(loosened)


# ---------------------------------------------------------------------------
# frozen safety requirements may not be relaxed
# ---------------------------------------------------------------------------

def test_frozen_authority_statuses_are_still_frozen(authority_yaml) -> None:
    frozen = {
        ("coordinate_system", "status"): "FROZEN_DATUM",
        ("safety", "airway", "no_collapse_status"): "FROZEN_SAFETY_REQUIREMENT",
        ("safety", "quick_release", "time_status"): "FROZEN_SAFETY_REQUIREMENT",
        ("safety", "quick_release", "one_hand_wet_unpowered_status"): "FROZEN_SAFETY_REQUIREMENT",
        ("actuation", "architecture_status"): "FROZEN_ARCHITECTURE",
    }
    for path, expected in frozen.items():
        node = authority_yaml
        for key in path:
            node = node[key]
        assert node == expected, f"{'.'.join(path)} is no longer {expected}"


def test_wearer_safety_limits_only_move_in_the_safe_direction(authority_yaml) -> None:
    """Protected anatomy and escape are not packaging variables.

    Each bound below is pinned in the direction that protects the wearer:
    airway openings may grow, escape time may shrink, head load may fall.
    """

    airway = authority_yaml["safety"]["airway"]
    quick = authority_yaml["safety"]["quick_release"]
    mass = authority_yaml["mass"]

    assert airway["minimum_area_each_mm2"] >= 120.0, "nostril opening area reduced"
    assert airway["minimum_local_dimension_mm"] >= 8.0, "nostril opening dimension reduced"
    assert airway["no_collapse_test_flow_lpm"] >= 120.0, "no-collapse test flow weakened"
    assert airway["no_collapse_required"] is True, "no-collapse requirement removed"
    assert quick["time_max_s"] <= 2.0, "quick-release escape time relaxed"
    assert quick["one_hand_wet_unpowered"] is True, "one-hand wet unpowered release removed"
    assert mass["pitch_torque_max_Nm"] <= 0.070, "wearer head-load limit relaxed"
    assert mass["loaded_absolute_max_g"] <= 255.0, "loaded mass limit relaxed"


def test_protected_facial_apertures_are_not_shrunk_for_packaging(authority_yaml) -> None:
    """Eye and mouth openings are visibility and comfort, not spare volume."""

    geometry = authority_yaml["geometry"]
    eye_w, eye_h = geometry["eye"]["visual_aperture_wh_mm"]
    mouth_w, mouth_h = geometry["mouth"]["visual_aperture_wh_mm"]

    assert eye_w >= 46.0 and eye_h >= 30.0, "eye aperture reduced"
    assert mouth_w >= 58.0 and mouth_h >= 32.0, "mouth aperture reduced"
    assert geometry["misregistration"]["translation_radial_max_mm"] >= 5.0, (
        "misregistration screen weakened"
    )
    assert geometry["misregistration"]["rotation_max_deg"] >= 4.0, (
        "misregistration screen weakened"
    )
