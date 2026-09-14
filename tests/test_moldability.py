"""Draft screen on the released shell geometry."""

from __future__ import annotations

import math

import pytest

from masck_one.model import build_model
from masck_one.moldability import (
    EVIDENCE_STATUS,
    MIN_DRAFT_POLISHED_DEG,
    PULL_DIRECTION,
    Finish,
    MoldabilityError,
    draft_angle_deg,
    required_draft_deg,
    screen_component_draft,
)


class _Normal:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z


@pytest.fixture(scope="module")
def screen():
    return screen_component_draft(build_model().shell)


# --------------------------------------------------------------------------
# draft geometry
# --------------------------------------------------------------------------

def test_face_perpendicular_to_pull_releases_immediately() -> None:
    assert draft_angle_deg(_Normal(0, 0, 1)) == pytest.approx(90.0)


def test_face_parallel_to_pull_has_no_draft() -> None:
    """The failure mode: a wall that drags the whole way out of the tool."""

    assert draft_angle_deg(_Normal(1, 0, 0)) == pytest.approx(0.0)
    assert draft_angle_deg(_Normal(0, 1, 0)) == pytest.approx(0.0)


def test_draft_is_symmetric_about_the_pull_axis() -> None:
    assert draft_angle_deg(_Normal(0, 0, -1)) == pytest.approx(90.0)


def test_a_tilted_wall_reports_its_tilt() -> None:
    # 5 degrees off parallel.
    n = _Normal(math.cos(math.radians(5)), 0.0, math.sin(math.radians(5)))
    assert draft_angle_deg(n) == pytest.approx(5.0, abs=1e-9)


def test_zero_length_normal_fails_closed() -> None:
    with pytest.raises(MoldabilityError):
        draft_angle_deg(_Normal(0, 0, 0))


# --------------------------------------------------------------------------
# draft and texture are coupled
# --------------------------------------------------------------------------

def test_texture_increases_the_required_draft() -> None:
    """Roughly one degree per 0.025 mm of texture depth."""

    polished = required_draft_deg(Finish.POLISHED)
    satin = required_draft_deg(Finish.FINE_SATIN, 0.040)
    assert polished == MIN_DRAFT_POLISHED_DEG
    assert satin > polished
    assert required_draft_deg(Finish.FINE_SATIN, 0.080) > satin


def test_deeper_texture_needs_proportionally_more_draft() -> None:
    shallow = required_draft_deg(Finish.FINE_SATIN, 0.025)
    deep = required_draft_deg(Finish.FINE_SATIN, 0.050)
    assert (deep - MIN_DRAFT_POLISHED_DEG) == pytest.approx(
        2 * (shallow - MIN_DRAFT_POLISHED_DEG)
    )


@pytest.mark.parametrize("bad", [-0.1, float("nan"), float("inf")])
def test_invalid_texture_depth_fails_closed(bad) -> None:
    with pytest.raises(MoldabilityError):
        required_draft_deg(Finish.FINE_SATIN, bad)


def test_non_finish_enum_fails_closed() -> None:
    with pytest.raises(MoldabilityError):
        required_draft_deg("FINE_SATIN", 0.04)


# --------------------------------------------------------------------------
# the finding: aperture walls have no draft
# --------------------------------------------------------------------------

def test_every_protected_aperture_wall_has_zero_draft(screen) -> None:
    """The shell's apertures are straight-extruded cutters.

    Three elliptical (both eyes and the mouth) and two cylindrical (the
    nostrils) walls sit at exactly 0 deg to the pull direction. A 0 deg wall in
    a 1.8 mm section cannot eject without dragging, and these are the most
    visible, most-touched edges on the product.
    """

    zero = screen.zero_draft_faces
    assert len(zero) == 5
    kinds = sorted(face.geom_type for face in zero)
    assert kinds == ["CYLINDER", "CYLINDER", "EXTRUSION", "EXTRUSION", "EXTRUSION"]
    assert screen.minimum_draft_deg == pytest.approx(0.0, abs=1e-9)


def test_zero_draft_faces_do_not_increase(screen) -> None:
    """Ratchet. Five undrafted aperture walls was the state when measured.

    The shell is CAD_BASELINE development geometry, so this does not fail the
    build. It fails if the problem gets worse.
    """

    assert len(screen.zero_draft_faces) <= 5
    assert screen.zero_draft_area_fraction <= 0.012


def test_the_lofted_shell_surfaces_are_adequately_drafted(screen) -> None:
    """The problem is local to the apertures, not the body."""

    lofted = [f for f in screen.faces if f.geom_type == "BSPLINE"]
    assert lofted, "expected lofted shell surfaces"
    assert all(f.draft_deg > screen.required_draft_deg for f in lofted)


def test_required_draft_reflects_the_specified_satin_finish(screen) -> None:
    assert screen.required_draft_deg == pytest.approx(2.10, abs=1e-9)
    assert screen.undrafted_faces == screen.zero_draft_faces


# --------------------------------------------------------------------------
# contract
# --------------------------------------------------------------------------

def test_pull_direction_is_declared_not_assumed(screen) -> None:
    """The shell lofts along +Z and every cutter extrudes along +Z."""

    assert screen.pull_direction == PULL_DIRECTION == (0.0, 0.0, 1.0)
    assert screen.manifest()["pull_direction"] == [0.0, 0.0, 1.0]


def test_screen_does_not_claim_a_moulding_simulation(screen) -> None:
    manifest = screen.manifest()
    assert manifest["evidence_status"] == EVIDENCE_STATUS
    disclaimed = " ".join(manifest["not_evidence_of"]).lower()
    for topic in ("warp", "ejection", "weld-line", "texture release"):
        assert topic in disclaimed


def test_manifest_is_deterministic() -> None:
    model = build_model()
    assert (
        screen_component_draft(model.shell).manifest()
        == screen_component_draft(model.shell).manifest()
    )


def test_areas_sum_to_the_total(screen) -> None:
    assert screen.total_area_mm2 == pytest.approx(
        math.fsum(f.area_mm2 for f in screen.faces)
    )
