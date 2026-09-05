from __future__ import annotations

import math

import cadquery as cq
import pytest

from masck_one.right_quick_release_latch import RELEASE_TRAVEL_MM
from masck_one.right_quick_release_latch_export import export_right_quick_release_latch
from masck_one.right_quick_release_travel import (
    STOP_OVERTRAVEL_PROBE_MM,
    RightQuickReleaseTravelError,
    build_captive_travel_contract,
)


def _intersection_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    return float(first.val().intersect(second.val()).Volume())


def test_captive_travel_contract_binds_both_positive_hard_stops() -> None:
    contract = build_captive_travel_contract()
    manifest = contract.manifest()

    assert manifest["travel_limits"] == {
        "minimum_offset_mm": 0.0,
        "maximum_offset_mm": RELEASE_TRAVEL_MM,
        "release_direction_xyz": [1.0, 0.0, 0.0],
        "limit_source": "POSITIVE_GUIDE_CAVITY_END_WALLS",
        "out_of_range_state_rejected": True,
    }
    assert manifest["inboard_hard_stop"]["contact_at_latched_limit"] is True
    assert manifest["outboard_hard_stop"]["contact_at_released_limit"] is True
    assert (
        manifest["inboard_hard_stop"]["positive_material_intersection_mm3"] > 0.0
    )
    assert (
        manifest["outboard_hard_stop"]["positive_material_intersection_mm3"] > 0.0
    )
    assert manifest["captivity"]["no_loose_ejecting_slider_in_released_state"] is True
    assert manifest["captivity"]["worst_case_radial_capture_margin_mm"] > 0.0
    assert manifest["captivity"]["worst_case_hard_stop_wall_margin_mm"] > 0.0
    assert manifest["continuous_axial_containment"] == {
        "proof_kind": "MONOTONIC_LINEAR_TRANSLATION_INTERVAL",
        "spool_inboard_face_expression": "SPOOL_XMIN_0_PLUS_OFFSET",
        "spool_outboard_face_expression": "SPOOL_XMAX_0_PLUS_OFFSET",
        "admissible_offset_interval_mm": [0.0, RELEASE_TRAVEL_MM],
        "cavity_interval_mm": [
            contract.inboard_stop_x_mm,
            contract.outboard_stop_x_mm,
        ],
        "endpoint_equalities_close_interval": True,
    }
    assert manifest["physical_validation_eligible"] is False


def test_bounded_slider_state_rejects_any_commanded_overtravel() -> None:
    contract = build_captive_travel_contract()

    for invalid in (
        -1e-9,
        RELEASE_TRAVEL_MM + 1e-9,
        float("inf"),
        float("nan"),
        True,
        "0.0",
    ):
        with pytest.raises(RightQuickReleaseTravelError):
            contract.state_at(invalid)

    states = (
        contract.state_at(0.0),
        contract.state_at(RELEASE_TRAVEL_MM / 2.0),
        contract.state_at(RELEASE_TRAVEL_MM),
    )
    assert [state.state_id for state in states] == [
        "LATCHED",
        "RELEASE_TRAVEL_IN_PROGRESS",
        "RELEASED_RESET_REQUIRED",
    ]
    for state in states:
        assert state.solid.val().isValid()
        assert len(state.solid.val().Solids()) == 1

    latched_bb = states[0].solid.val().BoundingBox()
    for state in states:
        bb = state.solid.val().BoundingBox()
        assert math.isclose(
            float(bb.xmin),
            float(latched_bb.xmin) + state.offset_mm,
            rel_tol=0.0,
            abs_tol=1e-9,
        )
        assert math.isclose(
            float(bb.xmax),
            float(latched_bb.xmax) + state.offset_mm,
            rel_tol=0.0,
            abs_tol=1e-9,
        )


def test_exported_breps_retain_positive_material_hard_stop_blocking(tmp_path) -> None:
    latch_contract = build_captive_travel_contract()
    export_right_quick_release_latch(tmp_path, latch_contract.latch)

    guide = cq.importers.importStep(str(tmp_path / "right_latch_captive_guide.step"))
    latched = cq.importers.importStep(str(tmp_path / "right_latch_captive_slider.step"))
    released = cq.importers.importStep(
        str(tmp_path / "right_latch_captive_slider_released_state.step")
    )

    for shape in (guide, latched, released):
        assert shape.val().isValid()
        assert len(shape.val().Solids()) == 1

    inboard_overtravel = latched.translate((-STOP_OVERTRAVEL_PROBE_MM, 0.0, 0.0))
    outboard_overtravel = released.translate((STOP_OVERTRAVEL_PROBE_MM, 0.0, 0.0))
    assert _intersection_mm3(inboard_overtravel, guide) > 0.0
    assert _intersection_mm3(outboard_overtravel, guide) > 0.0


def test_travel_contract_manifest_is_deterministic_and_source_bound() -> None:
    first = build_captive_travel_contract()
    second = build_captive_travel_contract()

    assert first.package_sha256 == second.package_sha256
    assert first.manifest() == second.manifest()
    assert first.manifest()["source_latch_package_sha256"] == first.latch.package_sha256
