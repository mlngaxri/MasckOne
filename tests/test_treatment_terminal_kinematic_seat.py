from __future__ import annotations

import math

from masck_one.structural_frame_actuator_reactions import REACTION_IDS
from masck_one.treatment_terminal_kinematic_seat import (
    BACK_ENVELOPE_AVAILABLE_MM,
    BACK_ENVELOPE_MARGIN_MM,
    DETENT_RETAINED_DEFLECTION_SEED_MM,
    RUNNING_X_CLEARANCE_MM,
    RUNNING_Z_CLEARANCE_MM,
    SOURCE_CELL6_HEAD_SHA,
    TAPER_OVERTRAVEL_EXTENSION_MM,
    X_TAPER_SPAN_MM,
    Z_TAPER_SPAN_MM,
    build_terminal_kinematic_seats,
    detent_linear_proxy,
    seating_backdrive_screen,
    taper_half_angles_deg,
)


def test_four_terminal_seats_are_nominally_clear_and_directionally_constrained():
    architecture = build_terminal_kinematic_seats()
    assert tuple(seat.reaction_id for seat in architecture.seats) == REACTION_IDS
    assert architecture.source_cell6_head_sha == SOURCE_CELL6_HEAD_SHA
    assert architecture.physical_validation_eligible is False

    for seat in architecture.seats:
        assert seat.nominal_source_intersection_mm3 == 0.0
        assert seat.axial_overtravel_intersection_mm3 > 0.0
        assert min(seat.lateral_probe_intersections_mm3) > 0.0
        assert min(seat.vertical_probe_intersections_mm3) > 0.0
        assert seat.service_retraction_intersection_mm3 == 0.0
        assert seat.service_retraction_sweep.isValid()
        assert tuple(name for name, _shape in seat.pad_parts) == (
            "x_left_datum",
            "x_right_datum",
            "z_lower_datum",
            "z_upper_datum",
        )


def test_taper_uses_running_clearance_only_at_terminal_seat_and_fits_back_envelope():
    ax, az = taper_half_angles_deg()
    assert math.isclose(math.tan(math.radians(ax)), RUNNING_X_CLEARANCE_MM / X_TAPER_SPAN_MM, rel_tol=1e-12)
    assert math.isclose(math.tan(math.radians(az)), RUNNING_Z_CLEARANCE_MM / Z_TAPER_SPAN_MM, rel_tol=1e-12)
    assert 10.0 < ax < 20.0
    assert 10.0 < az < 20.0
    assert TAPER_OVERTRAVEL_EXTENSION_MM <= BACK_ENVELOPE_AVAILABLE_MM - BACK_ENVELOPE_MARGIN_MM


def test_retention_screen_keeps_working_load_off_the_anti_rattle_spring():
    screen = seating_backdrive_screen()
    proxy = detent_linear_proxy()
    assert DETENT_RETAINED_DEFLECTION_SEED_MM == 0.09
    assert proxy["retained_force_proxy_N"] > 0.0
    assert screen["ideal_frictionless_transient_axial_backdrive_upper_bound_N"] > 0.0
    # This is only a linear architecture screen. The positive proxy margin is a
    # reason to keep this topology in the DOE, not a physical retention claim.
    assert screen["proxy_margin_N"] > 0.0
    assert screen["self_release_mu_threshold_x"] > 0.0
    assert screen["self_release_mu_threshold_z"] > 0.0


def test_manifest_is_explicit_about_buttery_intent_and_evidence_firewall():
    manifest = build_terminal_kinematic_seats().manifest()
    assert manifest["schema"] == "MASCK_ONE_TREATMENT_TERMINAL_KINEMATIC_SEAT_V1"
    assert manifest["physical_validation_eligible"] is False
    for seat in manifest["seats"]:
        assert seat["architecture"].startswith("PARALLEL_LOW_DRAG_APPROACH_PLUS_TERMINAL")
        assert seat["working_reaction_path"].startswith("RIGID_TAPER_FACES_TO_CELL6_RIGID_SHOULDER")
        assert seat["nominal_seated_geometric_dead_zone"].startswith("ZERO_IN_IDEAL_RIGID_DATUM_MODEL")
        assert seat["tolerance_status"].endswith("FEA_PHYSICAL_OPEN")
        assert seat["physical_validation"].startswith("OPEN_")
