from __future__ import annotations

from studies.treatment_parallel_preload_material_trade_v2 import (
    CONTINUOUS_REACTION_REFERENCE_N,
    FULL_SEAT_PRELOAD_N,
    build_manifest,
    build_polymer_axis,
    spring_metal_candidate,
)


def test_parallel_metal_candidate_preserves_axis_specific_zero_play_preload_logic():
    metal = spring_metal_candidate()
    assert metal["extra_insert_parts_per_station"] == 2
    for key in ("x_axis", "z_axis"):
        axis = metal[key]
        assert axis["seated_preload_N"] == FULL_SEAT_PRELOAD_N
        assert axis["continuous_contact_margin_N"] > 0.09
        assert axis["entry_force_N"] < 0.015
    assert "LOSSY_POLYMER_CAPTURE" in metal["damping_requirement"]


def test_parallel_polymer_has_low_linear_stress_but_creep_remains_first_order():
    x = build_polymer_axis("X")
    z = build_polymer_axis("Z")
    assert x.seated_preload_N == FULL_SEAT_PRELOAD_N
    assert z.seated_preload_N == FULL_SEAT_PRELOAD_N
    assert x.linear_stress_proxy_MPa < 20.0
    assert z.linear_stress_proxy_MPa < 20.0
    assert 0.004 < x.equivalent_surface_strain_proxy < 0.007
    assert 0.003 < z.equivalent_surface_strain_proxy < 0.006
    assert FULL_SEAT_PRELOAD_N > CONTINUOUS_REACTION_REFERENCE_N


def test_v1_trade_selects_stable_parallel_metal_preload_not_tight_rail_or_single_cantilever():
    manifest = build_manifest()
    assert manifest["selected_v1_architecture_candidate"].startswith(
        "AXIS_SPECIFIC_FIXED_GUIDED_SPRING_METAL"
    )
    rejected = manifest["rejected_for_current_v1_baseline"]
    assert any("SINGLE_CANTILEVER_POLYMER" in item for item in rejected)
    assert any("FULLY_RIGID_FOUR_FACE_TAPER" in item for item in rejected)
    assert any("TIGHT_LONG_RAIL" in item for item in rejected)
    assert manifest["physical_validation_eligible"] is False
    assert manifest["physical_validation"].startswith("OPEN_")
