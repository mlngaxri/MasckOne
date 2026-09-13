from __future__ import annotations

"""Current material/topology decision for the deterministic terminal treatment mount.

The preload element is not the normal 40 Hz reaction member, but it is what keeps the
carrier closed against the rigid master datum. If preload relaxes enough for that
contact to open, the mount can recover a microscopic dead zone and start cycling a
gap. That makes long-term preload retention a first-order precision/acoustic issue.

The earlier study selected an integral engineering-polymer tongue for part-count and
acoustic simplicity. This revision keeps that topology as a backup, but selects the
captured parallel-leaf spring cassette as the current digital V1 candidate because:

- X/Z stiffness can be independently tuned to their different clearances;
- two leaves limit shoe pitch/edge loading;
- a dog-bone root can be geometrically captured instead of left as a loose insert;
- the root can be surrounded by a lossy carrier material, reducing the high-Q path;
- the spring is not intended to carry normal 40 Hz working reaction;
- unknown polymer creep/relaxation directly consumes the no-gap preload margin.

No alloy or polymer grade is selected here. This is an architecture decision pending
aged wet/warm preload retention, force-travel, fatigue and acoustic hardware tests.
"""

import json
from pathlib import Path

from studies.treatment_parallel_preload_flexure import build_axis

SCHEMA = "MASCK_ONE_TREATMENT_TERMINAL_PRELOAD_MATERIAL_TRADE_V2"
SOURCE_TREATMENT_V6_HEAD_PARENT_SHA = "ec5f0a0197df1fc9fdcc607e215e2291b3f2ca51"

PRELOAD_TARGET_N = 0.30
CONTINUOUS_REACTION_REFERENCE_N = 0.20
TRANSIENT_REACTION_REFERENCE_N = 0.60
RELAXATION_SENSITIVITY_FRACTIONS = (0.0, 0.10, 0.20, 0.30, 1.0 / 3.0, 0.40)


def preload_retention_sensitivity() -> dict[str, object]:
    rows = []
    for loss_fraction in RELAXATION_SENSITIVITY_FRACTIONS:
        retained = PRELOAD_TARGET_N * (1.0 - loss_fraction)
        margin = retained - CONTINUOUS_REACTION_REFERENCE_N
        rows.append(
            {
                "preload_loss_fraction": loss_fraction,
                "retained_preload_N": retained,
                "continuous_contact_margin_N": margin,
                "ideal_contact_margin_positive": margin > 0.0,
            }
        )
    threshold = 1.0 - CONTINUOUS_REACTION_REFERENCE_N / PRELOAD_TARGET_N
    return {
        "rows": rows,
        "ideal_preload_loss_fraction_at_zero_margin": threshold,
        "minimum_retained_preload_fraction_for_positive_ideal_margin": (
            CONTINUOUS_REACTION_REFERENCE_N / PRELOAD_TARGET_N
        ),
        "interpretation": (
            "ANY_PRELOAD_TECHNOLOGY_MUST_BE_QUALIFIED_AGAINST_AGED_RELAXATION_BECAUSE_"
            "ABOUT_ONE_THIRD_LOSS_CONSUMES_THE_ENTIRE_IDEAL_0P10N_CONTACT_MARGIN"
        ),
    }


def captured_parallel_spring_candidate() -> dict[str, object]:
    x = build_axis("X")
    z = build_axis("Z")
    return {
        "topology": "CAPTURED_AXIS_TUNED_PARALLEL_LEAF_SPRING_CASSETTES",
        "axes": {"X": x.manifest(), "Z": z.manifest()},
        "advantages": [
            "AXIS_SPECIFIC_STIFFNESS_MATCHES_DIFFERENT_X_Z_CLEARANCES",
            "PARALLEL_LEAVES_LIMIT_SHOE_PITCH_AND_EDGE_LOADING",
            "DOG_BONE_ROOT_CAN_BE_GEOMETRICALLY_CAPTURED_WITHOUT_LOOSE_INSERT_PLAY",
            "LOW_CREEP_POTENTIAL_WITH_CORRECT_SPRING_GRADE",
            "NORMAL_40HZ_REACTION_REMAINS_ON_RIGID_MASTER_DATUMS",
        ],
        "risk_controls": [
            "LOSSY_CARRIER_SURROUND_AT_CAPTURE_ROOT_TO_REDUCE_RING_TRANSMISSION",
            "ZERO_SLOPE_TERMINAL_CAM_TO_REDUCE_EXCITATION_AT_ACQUISITION_AND_SEAT",
            "LOSSY_BACKUP_BEFORE_RIGID_ABNORMAL_STOP",
        ],
        "penalties": [
            "EXTRA_SPRING_CASSETTE_PARTS_OR_INSERT_MOLDING_OPERATION",
            "SPRING_GRADE_FORMING_AND_ROOT_CAPTURE_REQUIRE_DFM",
            "CORROSION_WET_CHEMICAL_AND_GALVANIC_ISOLATION_REQUIRE_VALIDATION",
            "BARE_METAL_CAN_RING_IF_ROOT_AND_CONTACT_PATHS_ARE_POORLY_DAMPED",
        ],
    }


def integral_polymer_candidate() -> dict[str, object]:
    # Retained as the lower-part-count fallback. Exact grade and creep are unknown;
    # therefore no numerical aged preload-retention claim is made here.
    return {
        "topology": "AXIS_TUNED_INTEGRAL_ENGINEERED_POLYMER_FLEXURE_BACKUP",
        "advantages": [
            "LOWEST_PART_COUNT",
            "NO_SEPARATE_METAL_INSERT_ROOT",
            "INHERENTLY_LOSSY_STRUCTURAL_MATERIAL_CAN_REDUCE_RINGING",
            "DIRECT_CARRIER_INTEGRATION",
        ],
        "penalties": [
            "AGED_PRELOAD_RELAXATION_DIRECTLY_CONSUMES_NO_GAP_CONTACT_MARGIN",
            "TEMPERATURE_AND_WET_CHEMICAL_SENSITIVITY_REQUIRE_GRADE_SPECIFIC_DATA",
            "MOLD_ROOT_RADIUS_WELD_LINE_AND_PROCESS_HISTORY_BECOME_FORCE_CTQS",
            "CREEP_FAILURE_CAN_PRESENT_AS_RATTLE_BEFORE_GROSS_GEOMETRIC_FAILURE",
        ],
        "promotion_gate": (
            "ONLY_PROMOTE_OVER_SPRING_CASSETTE_IF_AGED_WET_WARM_PRELOAD_RETENTION_FATIGUE_"
            "AND_FORCE_TRAVEL_TESTING_CLOSE_WITH_USEFUL_MARGIN"
        ),
    }


def build_manifest() -> dict[str, object]:
    spring = captured_parallel_spring_candidate()
    polymer = integral_polymer_candidate()
    relaxation = preload_retention_sensitivity()
    return {
        "schema": SCHEMA,
        "source_treatment_v6_head_parent_sha": SOURCE_TREATMENT_V6_HEAD_PARENT_SHA,
        "preload_target_N": PRELOAD_TARGET_N,
        "continuous_reaction_reference_N": CONTINUOUS_REACTION_REFERENCE_N,
        "transient_reaction_reference_N": TRANSIENT_REACTION_REFERENCE_N,
        "captured_parallel_spring_candidate": spring,
        "integral_polymer_candidate": polymer,
        "preload_retention_sensitivity": relaxation,
        "selected_v1_digital_candidate": "CAPTURED_AXIS_TUNED_PARALLEL_LEAF_SPRING_CASSETTES",
        "selection_reason": (
            "NO_GAP_PRELOAD_RETENTION_IS_MORE_CRITICAL_THAN MINIMUM PART COUNT AT THIS STAGE. "
            "THE CAPTURED PARALLEL SPRING TOPOLOGY REDUCES RELAXATION RISK, MATCHES X/Z CLEARANCE "
            "SEPARATELY AND AVOIDS A LOOSE ROOT; INTEGRAL POLYMER REMAINS A SIMPLIFICATION BACKUP "
            "IF AGED PHYSICAL TESTING PROVES RETENTION."
        ),
        "digital_screen_checks": {
            "preload_exceeds_continuous_reference": PRELOAD_TARGET_N > CONTINUOUS_REACTION_REFERENCE_N,
            "x_entry_force_below_0p015_N": build_axis("X").entry_force_N < 0.015,
            "z_entry_force_below_0p015_N": build_axis("Z").entry_force_N < 0.015,
            "x_backup_before_transient": build_axis("X").backup_first_engagement_force_N < TRANSIENT_REACTION_REFERENCE_N,
            "z_backup_before_transient": build_axis("Z").backup_first_engagement_force_N < TRANSIENT_REACTION_REFERENCE_N,
            "one_third_preload_loss_consumes_ideal_margin": abs(
                relaxation["ideal_preload_loss_fraction_at_zero_margin"] - 1.0 / 3.0
            ) < 1e-12,
        },
        "physical_validation_eligible": False,
        "physical_validation": (
            "OPEN_EXACT_SPRING_ALLOY_FORMING_RESIDUAL_STRESS_FATIGUE_ROOT_CAPTURE_DAMPING_ACOUSTICS_"
            "CORROSION_WET_CHEMICAL_FORCE_TRAVEL_TOLERANCE_AND_AGED_POLYMER_COMPARISON"
        ),
    }


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True))
