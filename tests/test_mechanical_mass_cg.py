import hashlib
import json

import pytest

from masck_one.authority import load_authority
from masck_one.mechanical_mass_cg import (
    SCHEMA,
    SUPPLIER_ACTUATOR_MASS_SOURCE_MODEL,
    SUPPLIER_ACTUATOR_MODEL,
    SUPPLIER_ACTUATOR_PROVENANCE,
    SUPPLIER_ACTUATOR_SOURCE_URL,
    SUPPLIER_ACTUATOR_TOTAL_MASS_G,
    build_mechanical_mass_cg_ledger,
)


@pytest.fixture(scope="module")
def ledger():
    return build_mechanical_mass_cg_ledger(load_authority())


def test_mass_ledger_is_deterministic_and_provenance_explicit(ledger):
    assert ledger.manifest()["schema"] == SCHEMA
    payload = ledger.manifest(include_sha=False)
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert ledger.ledger_sha256 == digest
    assert len({entry.component_id for entry in ledger.entries}) == len(ledger.entries)


def test_known_dry_subset_is_battery_plus_four_traceable_actuator_benchmarks_only(ledger):
    authority = load_authority()
    expected = float(authority.get("battery_reference", "mass_g")) + 4.0 * SUPPLIER_ACTUATOR_TOTAL_MASS_G
    assert ledger.known_mass_subtotal_g == pytest.approx(expected)
    assert ledger.known_mass_subtotal_g == pytest.approx(44.4)

    actuators = tuple(entry for entry in ledger.entries if entry.component_id.startswith("ACTUATOR-ZONE-"))
    assert len(actuators) == 4
    assert all(entry.mass_g == pytest.approx(SUPPLIER_ACTUATOR_TOTAL_MASS_G) for entry in actuators)
    assert all(SUPPLIER_ACTUATOR_MODEL in entry.source_reference for entry in actuators)
    assert all(SUPPLIER_ACTUATOR_MASS_SOURCE_MODEL in entry.source_reference for entry in actuators)
    assert all(SUPPLIER_ACTUATOR_SOURCE_URL in entry.source_reference for entry in actuators)
    assert all(entry.source_kind == "SUPPLIER_SIBLING_MODEL_MASS_BENCHMARK" for entry in actuators)
    assert all(entry.mass_status == SUPPLIER_ACTUATOR_PROVENANCE for entry in actuators)
    assert all("NOT_EXACT_2IBH" in entry.mass_status for entry in actuators)


def test_alternate_service_shell_state_is_not_double_counted_as_a_component(ledger):
    ids = {entry.component_id for entry in ledger.entries}
    assert "LIVE-MAIN-RIGID-SHELL" in ids
    assert "SERVICE-STATE-SHELL" not in ids


def test_unknown_material_components_remain_unresolved_and_do_not_enter_cg_arithmetic(ledger):
    assert ledger.unresolved_component_ids
    unresolved = tuple(entry for entry in ledger.entries if not entry.known)
    assert all(entry.mass_g is None for entry in unresolved)
    assert all(entry.centroid_xyz_mm is None for entry in unresolved)
    assert "FRAME-PERIMETER-REACTION" in ledger.unresolved_component_ids
    assert "RETENTION-HALO-OCCIPITAL-CROWN" in ledger.unresolved_component_ids
    assert "WATER-RESERVOIR-DRY-ASSEMBLY" in ledger.unresolved_component_ids
    assert "WASTE-CARTRIDGE-DRY-ASSEMBLY" in ledger.unresolved_component_ids


def test_known_subset_cg_and_pitch_are_reported_but_never_promoted_to_whole_product(ledger):
    assert all(isinstance(value, float) for value in ledger.known_subset_cg_xyz_mm)
    assert ledger.known_subset_pitch_moment_Nm >= 0.0
    assert ledger.dry_total_g is None
    assert ledger.loaded_total_g is None
    assert ledger.whole_product_cg_xyz_mm is None
    assert ledger.whole_product_pitch_moment_Nm is None
    assert "EXACT_2IBH_MASS_UNRESOLVED" in ledger.evidence_status
    assert "FULL_DRY_LOADED_CG_AND_PITCH_REMAIN_BLOCKED" in ledger.evidence_status


def test_dominant_known_contributors_are_actuator_benchmark_then_battery_without_claiming_full_mass_dominance(ledger):
    contributors = ledger.dominant_known_contributors
    assert tuple(item.contributor_id for item in contributors) == (
        "FOUR_ACTUATOR_SIBLING_MODEL_MASS_BENCHMARKS",
        "BATTERY_REFERENCE_BENCHMARK",
    )
    assert contributors[0].known_mass_g == pytest.approx(22.4)
    assert contributors[1].known_mass_g == pytest.approx(22.0)
    assert sum(item.fraction_of_known_subtotal for item in contributors) == pytest.approx(1.0)


def test_live_mass_targets_are_carried_as_comparison_targets_not_pass_claims(ledger):
    authority = load_authority()
    assert ledger.dry_target_max_g == pytest.approx(float(authority.get("mass", "dry_target_max_g")))
    assert ledger.loaded_absolute_max_g == pytest.approx(float(authority.get("mass", "loaded_absolute_max_g")))
    assert ledger.cg_z_max_mm == pytest.approx(float(authority.get("mass", "cg_z_max_mm")))
    assert ledger.pitch_torque_max_Nm == pytest.approx(float(authority.get("mass", "pitch_torque_max_Nm")))
    assert ledger.unresolved_loaded_terms
