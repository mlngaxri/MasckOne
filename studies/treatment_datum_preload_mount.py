from __future__ import annotations

"""Deterministic datum + preload + overload-backup study for the treatment mount.

The V3 four-face terminal taper is elegant at nominal geometry but is over-constrained
once independent dimensional error is admitted. This successor study separates the
jobs instead of asking one shallow taper/detent pair to solve all of them:

- the long Cell 6 rail remains a generous low-drag acquisition guide;
- one rigid master datum per X and Z axis defines the seated coordinate;
- an opposite compliant preload shoe keeps the carrier continuously seated against
  that master datum through the normal 40 Hz reaction envelope;
- a close, lossy hard backup takes abnormal reverse/transient load before the preload
  leaf is asked to carry the 0.60 N transient reference;
- the Y terminal stop and axial detent are therefore freed from lateral wedge
  back-drive and can be tuned for smooth insertion/release rather than brute retention.

All numeric values below are architecture-study seeds only. Material grade, friction,
fatigue, force, sound, wear, tolerance and human-use performance remain physical-open.
"""

import json
from pathlib import Path

CONTINUOUS_REACTION_REFERENCE_N = 0.20
TRANSIENT_REACTION_REFERENCE_N = 0.60
NORMAL_PRELOAD_TARGET_N = 0.24
BACKUP_TRAVEL_SEED_MM = 0.04

# Thin spring-metal leaf analytical seed. This is deliberately not a selected grade.
SPRING_MODULUS_STUDY_MPA = 190000.0
SPRING_LEAF_WIDTH_MM = 1.00
SPRING_LEAF_THICKNESS_MM = 0.15
SPRING_LEAF_LENGTH_MM = 5.00

SCHEMA = "MASCK_ONE_TREATMENT_DATUM_PRELOAD_MOUNT_V1"
SOURCE_CELL6_HEAD_SHA = "fcccde02b31cc1c4e01136630d92e550e4e09a11"
SOURCE_TREATMENT_TOLERANCE_HEAD_SHA = "190de811ce84fdeac70c50f9d8dc7f4dcc373970"


def spring_leaf_screen() -> dict[str, float]:
    b = SPRING_LEAF_WIDTH_MM
    t = SPRING_LEAF_THICKNESS_MM
    length = SPRING_LEAF_LENGTH_MM
    inertia = b * t**3 / 12.0
    stiffness = 3.0 * SPRING_MODULUS_STUDY_MPA * inertia / length**3
    preload_deflection = NORMAL_PRELOAD_TARGET_N / stiffness
    backup_engagement_force = NORMAL_PRELOAD_TARGET_N + stiffness * BACKUP_TRAVEL_SEED_MM
    preload_root_stress = 6.0 * NORMAL_PRELOAD_TARGET_N * length / (b * t**2)
    backup_root_stress = 6.0 * backup_engagement_force * length / (b * t**2)
    return {
        "second_moment_mm4": inertia,
        "linear_tip_stiffness_N_per_mm": stiffness,
        "normal_preload_target_N": NORMAL_PRELOAD_TARGET_N,
        "preload_deflection_seed_mm": preload_deflection,
        "backup_travel_seed_mm": BACKUP_TRAVEL_SEED_MM,
        "force_when_backup_first_engages_N": backup_engagement_force,
        "preload_root_bending_stress_proxy_MPa": preload_root_stress,
        "backup_engagement_root_bending_stress_proxy_MPa": backup_root_stress,
    }


def load_path_screen() -> dict[str, object]:
    spring = spring_leaf_screen()
    return {
        "continuous_reference_N": CONTINUOUS_REACTION_REFERENCE_N,
        "transient_reference_N": TRANSIENT_REACTION_REFERENCE_N,
        "preload_target_N": NORMAL_PRELOAD_TARGET_N,
        "continuous_contact_margin_N": NORMAL_PRELOAD_TARGET_N - CONTINUOUS_REACTION_REFERENCE_N,
        "backup_first_engagement_force_N": spring["force_when_backup_first_engages_N"],
        "continuous_reaction_keeps_master_datum_closed": NORMAL_PRELOAD_TARGET_N > CONTINUOUS_REACTION_REFERENCE_N,
        "backup_engages_before_leaf_would_carry_full_transient": spring["force_when_backup_first_engages_N"] < TRANSIENT_REACTION_REFERENCE_N,
        "working_rule": (
            "NORMAL_40HZ_REACTION_REMAINS_PRELOADED_AGAINST_MASTER_DATUM; "
            "ABNORMAL_REVERSE_LOAD_USES_LOSSY_BACKUP_THEN_RIGID_STOP"
        ),
    }


def build_manifest() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "source_cell6_head_sha": SOURCE_CELL6_HEAD_SHA,
        "source_treatment_tolerance_head_sha": SOURCE_TREATMENT_TOLERANCE_HEAD_SHA,
        "selected_terminal_mount_direction": (
            "LOW_DRAG_PARALLEL_RAIL -> PROGRESSIVE_TERMINAL_ACQUISITION -> "
            "RIGID_MASTER_X_DATUM_PLUS_OPPOSED_PRELOAD_SHOE -> "
            "RIGID_MASTER_Z_DATUM_PLUS_OPPOSED_PRELOAD_SHOE -> "
            "RIGID_Y_SEAT -> GENTLE_AXIAL_DETENT -> LOSSY_CLOSE_BACKUPS -> RIGID_OVERLOAD_STOPS"
        ),
        "reason_for_superseding_four_face_taper_as_baseline": (
            "DETERMINISTIC_DATUMING_REMOVES_FOUR_FACE_MATCHED_CONTACT_OVERCONSTRAINT_AND_"
            "DECOUPLES_SMOOTH_RELEASE_FROM_TRANSIENT_RETENTION"
        ),
        "spring_leaf_screen": spring_leaf_screen(),
        "load_path_screen": load_path_screen(),
        "normal_user_feel_intent": (
            "FREE_APPROACH_WITHOUT_SCRAPE -> SOFT_PROGRESSIVE_FINAL_ACQUISITION -> "
            "NO_PERCEPTIBLE_SEATED_ROCK -> MUTED_POSITIVE_SEAT -> CLEAN_CONTROLLED_WITHDRAWAL"
        ),
        "mechanical_separation_of_functions": {
            "rail": "COARSE_GUIDANCE_AND_SERVICE_ALIGNMENT_ONLY",
            "master_datums": "POSITION_AND_NORMAL_WORKING_REACTION",
            "preload_shoes": "TAKE_UP_CLEARANCE_AND_KEEP_MASTER_DATUMS CLOSED",
            "lossy_backups": "ARREST_RARE_REVERSE_TRAVEL_WITHOUT_SHARP_CLACK",
            "rigid_backup_stops": "TRANSIENT_OVERLOAD_REACTION_AFTER_LOSSY_TAKEUP",
            "axial_detent": "SEATING_BIAS_AND_CAPTURE_STATE_NOT_LATERAL_40HZ_REACTION",
        },
        "physical_validation_eligible": False,
        "physical_validation": (
            "OPEN_NONLINEAR_FLEXURE_STRESS_FATIGUE_MATERIAL_GRADE_PRELOAD_TOLERANCE_FRICTION_"
            "CONTACT_PRESSURE_WEAR_CREEP_DAMPING_ACOUSTICS_WET_CONTAMINATION_AND_ASSEMBLY"
        ),
    }


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True))
