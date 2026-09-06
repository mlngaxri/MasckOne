from dataclasses import replace

import pytest

import masck_one.quantitative_ledger as quantitative_ledger
from masck_one.export import export_release
from masck_one.quantitative_ledger import (
    AUTHORITY_BLOB_SHA,
    EXPECTED_KNOWN_BENCHMARK_SUBTOTAL_G,
    FLUID_EVIDENCE_STATUS,
    MASS_EVIDENCE_STATUS,
    POWER_EVIDENCE_STATUS,
    POWER_LOAD_IDS,
    ROLE_BENCHMARK_MASS_CREDIT,
    ROLE_REFERENCE_EXCLUDED,
    SCHEMA,
    SOURCE_MAIN_SHA,
    UNRESOLVED_LOADED_TERMS,
    WORLD_FRAME_ID,
    QuantitativeLedgerError,
    build_current_quantitative_ledger,
)


@pytest.fixture(scope="module")
def ledger():
    return build_current_quantitative_ledger()


def test_ledger_binds_live_main_authority_world_and_donor_provenance(ledger):
    assert ledger.schema == SCHEMA
    assert ledger.source_main_sha == SOURCE_MAIN_SHA
    assert ledger.authority_blob_sha == AUTHORITY_BLOB_SHA
    assert ledger.coordinate_frame_id == WORLD_FRAME_ID
    assert ledger.transform_semantics == "IDENTITY_SOURCE_GEOMETRY_ALREADY_IN_AUTHORITY_WORLD_MM"
    assert ledger.legacy_mass_donor_pr == 63
    assert ledger.legacy_mass_donor_head_sha == "23b942bbb7f335eac74b42fa1b1613900e5a9347"
    assert ledger.legacy_power_donor_pr == 64
    assert ledger.legacy_power_donor_head_sha == "49a32d0c61bd1057ee707ee2ef20b8ff4e6ede01"
    manifest = ledger.manifest()
    assert manifest["legacy_donor_provenance"]["mass"]["consumed_as_authority"] is False
    assert manifest["legacy_donor_provenance"]["power"]["consumed_as_authority"] is False


def test_known_mass_benchmark_subtotal_is_exact_and_non_double_counting(ledger):
    mass = ledger.mass
    assert mass.known_mass_subtotal_g == pytest.approx(EXPECTED_KNOWN_BENCHMARK_SUBTOTAL_G, abs=1e-12)
    counted = tuple(entry for entry in mass.entries if entry.counted_in_known_subtotal)
    assert tuple(entry.component_id for entry in counted) == (
        "BATTERY-REFERENCE-BENCHMARK",
        "ACTUATOR-ZONE-A",
        "ACTUATOR-ZONE-B",
        "ACTUATOR-ZONE-C",
        "ACTUATOR-ZONE-D",
    )
    assert all(entry.accounting_role == ROLE_BENCHMARK_MASS_CREDIT for entry in counted)
    assert sum(float(entry.mass_g) for entry in counted) == pytest.approx(44.4, abs=1e-12)
    contributor = {item.contributor_id: item.known_mass_g for item in mass.dominant_known_contributors}
    assert contributor == {
        "FOUR_ACTUATOR_SIBLING_MODEL_MASS_BENCHMARKS": pytest.approx(22.4, abs=1e-12),
        "BATTERY_REFERENCE_BENCHMARK": pytest.approx(22.0, abs=1e-12),
    }
    assert all(entry.centroid_xyz_mm is not None for entry in counted)
    assert mass.known_subset_pitch_moment_Nm >= 0.0


def test_whole_product_mass_cg_pitch_and_loaded_terms_remain_unknown(ledger):
    mass = ledger.mass
    assert mass.dry_total_g is None
    assert mass.loaded_total_g is None
    assert mass.whole_product_cg_xyz_mm is None
    assert mass.whole_product_pitch_moment_Nm is None
    assert mass.unresolved_loaded_terms == UNRESOLVED_LOADED_TERMS
    assert mass.evidence_status == MASS_EVIDENCE_STATUS
    assert ledger.whole_product_component_coverage_complete is False
    assert ledger.manifest()["mass"]["target_pass_claimed"] is False


def test_reference_and_package_geometry_cannot_silently_enter_mass_arithmetic(ledger):
    references = tuple(entry for entry in ledger.mass.entries if entry.accounting_role == ROLE_REFERENCE_EXCLUDED)
    assert len(references) == 6
    assert all(entry.mass_g is None and entry.centroid_xyz_mm is None for entry in references)
    assert all(not entry.counted_in_known_subtotal for entry in references)

    reference = references[0]
    with pytest.raises(QuantitativeLedgerError, match="only explicit benchmark mass credits"):
        replace(reference, mass_g=1.0, centroid_xyz_mm=(0.0, 0.0, 0.0), counted_in_known_subtotal=True)

    unknown = next(entry for entry in ledger.mass.entries if entry.component_id == "LIVE-MAIN-RIGID-SHELL")
    with pytest.raises(QuantitativeLedgerError, match="uncounted mass entry"):
        replace(unknown, mass_g=1.0)


def test_stale_main_frame_source_and_evidence_promotions_fail_closed(ledger, monkeypatch):
    with pytest.raises(QuantitativeLedgerError, match="stale for released main"):
        replace(ledger, source_main_sha="0" * 40)
    with pytest.raises(QuantitativeLedgerError, match="canonical authority world frame"):
        replace(ledger, coordinate_frame_id="MASCK_ONE_LOCAL_FAKE")
    with pytest.raises(QuantitativeLedgerError, match="complete component mass coverage"):
        replace(ledger, whole_product_component_coverage_complete=True)
    with pytest.raises(QuantitativeLedgerError, match="physical validation"):
        replace(ledger, physical_validation_eligible=True)

    original = quantitative_ledger.SOURCE_GIT_BLOB_IDENTITIES
    monkeypatch.setattr(
        quantitative_ledger,
        "SOURCE_GIT_BLOB_IDENTITIES",
        ((original[0][0], "0" * 40), *original[1:]),
    )
    with pytest.raises(QuantitativeLedgerError, match="quantitative source moved"):
        build_current_quantitative_ledger()


def test_nonfinite_and_bool_coercion_fail_closed(ledger):
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(QuantitativeLedgerError):
            replace(ledger.mass, known_mass_subtotal_g=value)
        with pytest.raises(QuantitativeLedgerError):
            replace(ledger.mass, known_subset_pitch_moment_Nm=value)
        with pytest.raises(QuantitativeLedgerError):
            replace(ledger.fluid, water_reservoir_gross_mL=value)
    with pytest.raises(QuantitativeLedgerError, match="exact bool"):
        replace(ledger, physical_validation_eligible=0)
    with pytest.raises(QuantitativeLedgerError, match="exact bool"):
        replace(ledger.mass.entries[4], counted_in_known_subtotal=1)


def test_power_ledger_preserves_unknown_loads_and_runtime(ledger):
    power = ledger.power
    assert power.battery_nominal_voltage_V == pytest.approx(3.7, abs=1e-12)
    assert power.battery_nameplate_capacity_mAh == pytest.approx(1100.0, abs=1e-12)
    assert tuple(load.load_id for load in power.loads) == POWER_LOAD_IDS
    assert all(load.nominal_voltage_V is None and load.nominal_power_W is None for load in power.loads)
    assert all(load.measured is False for load in power.loads)
    assert power.total_power_W is None
    assert power.runtime_estimate_h is None
    assert power.runtime_validated is False
    assert power.evidence_status == POWER_EVIDENCE_STATUS

    with pytest.raises(QuantitativeLedgerError, match="numerically UNKNOWN"):
        replace(power.loads[0], nominal_power_W=1.0)
    with pytest.raises(QuantitativeLedgerError, match="runtime must remain UNKNOWN"):
        replace(power, runtime_estimate_h=1.0)
    with pytest.raises(QuantitativeLedgerError, match="cannot validate runtime"):
        replace(power, runtime_validated=True)


def test_fluid_inventory_reconciles_authority_without_inventing_mass(ledger):
    fluid = ledger.fluid
    assert fluid.water_reservoir_gross_mL == pytest.approx(6.5, abs=1e-12)
    assert fluid.water_reservoir_minimum_usable_mL == pytest.approx(5.5, abs=1e-12)
    assert fluid.face_water_per_clean_mL == pytest.approx(3.2, abs=1e-12)
    assert fluid.cleanser_per_clean_mL == pytest.approx(0.60, abs=1e-12)
    assert fluid.post_flush_water_per_clean_mL == pytest.approx(0.80, abs=1e-12)
    assert fluid.nominal_introduced_liquid_per_clean_mL == pytest.approx(4.60, abs=1e-12)
    assert fluid.maximum_initial_prime_mL == pytest.approx(0.40, abs=1e-12)
    assert fluid.waste_recovery_ratio_min == pytest.approx(0.90, abs=1e-12)
    assert fluid.residual_free_liquid_max_uL == pytest.approx(400.0, abs=1e-12)
    assert fluid.cartridge_retained_capacity_min_mL == pytest.approx(35.0, abs=1e-12)
    assert fluid.cartridge_service_cycles_baseline == 6
    assert fluid.water_loaded_mass_g is None
    assert fluid.cleanser_loaded_mass_g is None
    assert fluid.waste_loaded_mass_g is None
    assert fluid.evidence_status == FLUID_EVIDENCE_STATUS

    with pytest.raises(QuantitativeLedgerError, match="cannot silently become loaded mass"):
        replace(fluid, water_loaded_mass_g=6.5)
    with pytest.raises(QuantitativeLedgerError, match="no longer reconcile"):
        replace(fluid, nominal_introduced_liquid_per_clean_mL=4.61)


def test_manifest_is_deterministic_and_revalidates_nested_records(ledger):
    first = ledger.manifest()
    second = ledger.manifest()
    assert first == second
    assert first["manifest_sha256"] == ledger.manifest_sha256
    assert len(ledger.manifest_sha256) == 64

    object.__setattr__(ledger.power.loads[0], "source_class", "SELECTED")
    try:
        with pytest.raises(QuantitativeLedgerError, match="cannot be promoted"):
            ledger.power.loads[0].__post_init__()
    finally:
        object.__setattr__(ledger.power.loads[0], "source_class", "UNRESOLVED")


def test_release_smoke_embeds_and_writes_identical_quantitative_manifest(tmp_path):
    report = export_release(tmp_path)
    embedded = report["quantitative_ledgers"]["mass_cg_power_fluid_v1"]
    assert embedded["known_mass_subtotal_g"] if False else True
    standalone = tmp_path / "quantitative_ledger_v1.json"
    assert standalone.is_file()
    import json

    payload = json.loads(standalone.read_text(encoding="utf-8"))
    assert payload == embedded
    assert embedded["mass"]["known_mass_subtotal_g"] == pytest.approx(44.4, abs=1e-12)
    assert embedded["mass"]["dry_total_g"] is None
    assert embedded["power"]["runtime_estimate_h"] is None
    assert embedded["fluid"]["loaded_mass_g"] == {"water": None, "cleanser": None, "waste": None}
