from __future__ import annotations

import json
import math

import cadquery as cq

from masck_one.model import build_model
from masck_one.realized_waste_backbone_release import build_current_cell4_waste_backbone_release
from masck_one.right_quick_release_latch import RELEASE_TRAVEL_MM, WORLD_FRAME_ID
from masck_one.right_quick_release_reset import build_right_quick_release_reset_mechanics
from masck_one.right_quick_release_sweep import (
    build_right_quick_release_continuous_sweep,
    export_right_quick_release_continuous_sweep,
)


def _difference_volume_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    return float(first.val().cut(second.val()).Volume())


def test_exact_continuous_release_sweep_covers_complete_withdrawal_and_roundtrips(tmp_path) -> None:
    model = build_model()
    reset = build_right_quick_release_reset_mechanics(
        authority=model.authority,
        model=model,
    )
    sweep = build_right_quick_release_continuous_sweep(reset=reset, model=model)
    manifest = sweep.manifest()

    assert manifest["motion"] == {
        "kind": "PURE_TRANSLATION",
        "direction_xyz": [1.0, 0.0, 0.0],
        "offset_interval_mm": [0.0, RELEASE_TRAVEL_MM],
        "independent_rotation": False,
    }
    assert manifest["exact_sweep"]["complete_withdrawal_interval_covered"] is True
    assert manifest["exact_sweep"]["solid_count"] == 1
    assert manifest["legacy_conservative_bound"]["exact_sweep_outside_bound_mm3"] == 0.0
    assert manifest["legacy_conservative_bound"]["overcoverage_mm3"] > 0.0
    assert manifest["reset_partition_cross_check"]["partitions_cover_exact_complete_sweep"] is True
    assert manifest["reset_partition_cross_check"]["low_partition_outside_exact_mm3"] == 0.0
    assert manifest["reset_partition_cross_check"]["high_partition_outside_exact_mm3"] == 0.0
    assert manifest["reset_partition_cross_check"]["exact_not_covered_by_partition_mm3"] == 0.0
    assert manifest["all_complete_withdrawal_collision_checks_clear"] is True
    assert all(check["passes"] for check in manifest["collision_checks"])
    assert manifest["four_zone_actuation_preserved"] is True
    assert manifest["full_head_removal_trajectory_included"] is False
    assert manifest["physical_validation_eligible"] is False

    exact_bb = sweep.exact_slider_sweep.val().BoundingBox()
    legacy_bb = reset.latch.continuous_withdrawal_sweep.solid.val().BoundingBox()
    for exact_value, legacy_value in (
        (exact_bb.xmin, legacy_bb.xmin),
        (exact_bb.xmax, legacy_bb.xmax),
        (exact_bb.ymin, legacy_bb.ymin),
        (exact_bb.ymax, legacy_bb.ymax),
        (exact_bb.zmin, legacy_bb.zmin),
        (exact_bb.zmax, legacy_bb.zmax),
    ):
        assert math.isclose(
            float(exact_value),
            float(legacy_value),
            rel_tol=0.0,
            abs_tol=1e-9,
        )

    # Samples are only hostile regressions. The proof itself is the exact full-interval
    # swept-solid construction above, not waypoint sampling.
    for offset in (0.0, 0.37, 1.6, 3.95, 6.81, RELEASE_TRAVEL_MM):
        state = reset.latch.slider_and_grip.solid.translate((offset, 0.0, 0.0))
        assert _difference_volume_mm3(state, sweep.exact_slider_sweep) <= 1e-7

    paths = export_right_quick_release_continuous_sweep(tmp_path, sweep)
    assert {path.name for path in paths} == {
        "right_latch_exact_continuous_withdrawal_sweep.step",
        "right_quick_release_continuous_sweep_manifest.json",
    }
    step = cq.importers.importStep(
        str(tmp_path / "right_latch_exact_continuous_withdrawal_sweep.step")
    )
    assert step.val().isValid()
    assert len(step.val().Solids()) == 1
    roundtrip_bb = step.val().BoundingBox()
    for actual, expected in (
        (roundtrip_bb.xmin, exact_bb.xmin),
        (roundtrip_bb.xmax, exact_bb.xmax),
        (roundtrip_bb.ymin, exact_bb.ymin),
        (roundtrip_bb.ymax, exact_bb.ymax),
        (roundtrip_bb.zmin, exact_bb.zmin),
        (roundtrip_bb.zmax, exact_bb.zmax),
    ):
        assert math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-8)

    payload = json.loads(
        (tmp_path / "right_quick_release_continuous_sweep_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["package_sha256"] == sweep.package_sha256
    assert payload["source_reset_package_sha256"] == reset.package_sha256


def test_exact_release_sweep_is_separated_from_released_cell4_waste_service_envelopes() -> None:
    """Bind Cell 3 withdrawal to the now-released Cell 4 route reservation.

    Each route centerline bound is inflated by its controlled provisional service-envelope
    radius. A strict X separating plane is sufficient here because all released mixed-waste
    routing is wearer-left while the right latch is wearer-right. This is digital reservation
    evidence only, not tubing deformation or physical service-clearance validation.
    """
    model = build_model()
    reset = build_right_quick_release_reset_mechanics(
        authority=model.authority,
        model=model,
    )
    sweep = build_right_quick_release_continuous_sweep(reset=reset, model=model)
    sweep_xmin = float(sweep.exact_slider_sweep.val().BoundingBox().xmin)

    release = build_current_cell4_waste_backbone_release()
    assert release.realization.authority_revision == reset.latch.source_authority_revision
    for route in release.realization.routes:
        assert route.world_frame_id == WORLD_FRAME_ID
        _, route_max = route.bounds_xyz_mm
        inflated_route_xmax = float(route_max[0]) + route.service_envelope_radius_mm
        assert inflated_route_xmax < sweep_xmin
        assert sweep_xmin - inflated_route_xmax > 0.0
