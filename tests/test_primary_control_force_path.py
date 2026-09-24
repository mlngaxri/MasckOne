from dataclasses import replace
import itertools
import math

import cadquery as cq
import pytest

from masck_one import primary_control_haptic as v1
from masck_one import primary_control_haptic_v9 as v9
from masck_one import primary_control_haptic_v11 as current
from masck_one.primary_control_force_path import ButtonForcePathError, SeriesSpringInputs, evaluate_series_spring
from masck_one.primary_control_touch_surface import datum_segment, mark_profile


def _inputs():
    return SeriesSpringInputs(**current.force_path_screen()["inputs"])


def test_selected_series_spring_cannot_drive_dome_before_bind():
    screen = current.force_path_screen()
    assert screen["maximum_elastic_force_before_bind_or_stop_N"] < 0.060
    assert screen["lowest_captured_typical_trip_N"] == pytest.approx(0.980665)
    assert screen["force_margin_to_typical_low_N"] < -0.92
    assert screen["compression_required_for_typical_low_trip_mm"] > 15.0
    assert screen["available_elastic_compression_upper_bound_mm"] < 1.0
    assert screen["reaches_typical_trip_before_bind_or_stop"] is False
    assert screen["decision"] == "REJECTED_SERIES_FORCE_PATH"
    assert screen["functional_architecture_eligible"] is False
    with pytest.raises(current.PrimaryControlHapticV11Error, match="REJECTED_SERIES_FORCE_PATH"):
        current.require_functional_architecture()


def test_tuning_only_rate_cannot_preserve_low_postcollapse_increment():
    screen = current.force_path_screen()
    assert screen["rate_only_repair_has_feasible_interval"] is False
    assert screen["minimum_rate_to_reach_typical_low_trip_N_per_mm"] > screen["maximum_rate_for_postcollapse_increment_N_per_mm"]
    assert screen["minimum_postcollapse_increment_if_rate_repaired_N"] > 0.77
    # A stiffer spring can pass this necessary force bound. It is still not a
    # qualified button and its post-collapse load violates the existing target.
    stiff = evaluate_series_spring(replace(_inputs(), shear_modulus_seed_N_mm2=2_000_000.0))
    assert stiff["reaches_typical_trip_before_bind_or_stop"] is True
    assert stiff["functional_architecture_eligible"] is False


def test_sensitivity_cannot_hide_failure_with_small_coil_seed_adjustments():
    p = _inputs()
    # Deliberately broad design sensitivity, not controlled production tolerances.
    for wire, mean, modulus in itertools.product((0.11, 0.12, 0.13), (2.15, 2.2, 2.25), (0.8, 1.0, 1.2)):
        screen = evaluate_series_spring(replace(p, wire_mm=wire, mean_coil_mm=mean, shear_modulus_seed_N_mm2=p.shear_modulus_seed_N_mm2 * modulus))
        assert screen["reaches_typical_trip_before_bind_or_stop"] is False


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, 0.0, -0.1])
def test_nonfinite_and_nonpositive_force_inputs_are_rejected(bad):
    with pytest.raises(ButtonForcePathError):
        evaluate_series_spring(replace(_inputs(), wire_mm=bad))


def test_coil_bind_bound_does_not_assume_dome_has_collapsed():
    screen = current.force_path_screen()
    assert screen["coil_bind_cap_travel_if_dome_locked_mm"] == pytest.approx(0.88)
    assert screen["coil_bind_may_precede_cap_hard_stop"] is True
    assert "NOT_PREDICTED_ACTUAL_TRAVEL" in screen["evidence"]["coil_bind_location"]
    assert "NOT_PERMITTED_TRAVEL" in screen["evidence"]["dome_height"]


def test_functional_export_is_blocked_before_writing_cad(tmp_path):
    target = tmp_path / "functional"
    with pytest.raises(current.PrimaryControlHapticV11Error, match="REJECTED_SERIES_FORCE_PATH"):
        current.export_primary_control_haptic_architecture_v11(target, purpose="functional")
    assert not target.exists()


def test_plunger_reference_covers_interior_poses_and_exact_analytic_volume():
    rest = 0.0
    travel = v1.HARD_STOP_MM + v9.PLUNGER_HEAD_Z0_FROM_TRIM_MM - v9.PLUNGER_RETAINING_LEDGE_FROM_TRIM_MM
    part = current._near_contact_plunger(rest)
    sweep = current._plunger_translation_sweep(rest, travel)
    assert sweep.isValid() and len(sweep.Solids()) == 1
    expected = part.Volume() + math.pi * (v9.PLUNGER_HEAD_DIAMETER_MM / 2)**2 * travel
    assert sweep.Volume() == pytest.approx(expected, abs=1e-7)
    # Construction is analytic. Interior-pose probes here are hostile regression
    # witnesses against reverting to an endpoint compound, not the motion proof.
    for fraction in (0.0, 0.23, 0.5, 0.77, 1.0):
        pose = part.translate((0, 0, -travel * fraction))
        assert sum(s.Volume() for s in pose.cut(sweep).Solids()) < 1e-7
    endpoints = part.fuse(part.translate((0, 0, -travel)))
    middle = part.translate((0, 0, -travel / 2))
    assert middle.cut(endpoints).Volume() > 0.1


def test_mark_segments_preserve_world_datums_and_reflection_symmetry():
    x, y = v1.MOUNT_X_MM, v1.MOUNT_Y_MM
    for p0, p1 in (((x-2.1, y-1.6), (x-2.1, y+1.6)), ((x-2.1, y+1.6), (x-0.32, y+0.05))):
        segment = datum_segment(p0, p1, 0.38, 0.11, 0.0)
        centre = segment.Center()
        assert centre.x == pytest.approx((p0[0]+p1[0])/2, abs=1e-9)
        assert centre.y == pytest.approx((p0[1]+p1[1])/2, abs=1e-9)
    mark = mark_profile(0.0)
    left = cq.Compound.makeCompound(list(mark.Solids())[:2])
    right = cq.Compound.makeCompound(list(mark.Solids())[2:])
    reflected = left.mirror("YZ", (x, 0, 0))
    assert reflected.cut(right).Volume() < 1e-7
