from dataclasses import replace

import pytest

from masck_one.authority import load_authority
from masck_one.power_thermal_contract import (
    BATTERY_REFERENCE_STATUS,
    CHARGING_PREFERENCE,
    ENERGY_BOUND_STATUS,
    LOAD_IDS,
    THERMAL_RISK_IDS,
    BatteryPackagingBenchmark,
    ChargingArchitectureBoundary,
    ChargingConventionStatus,
    LoadStatus,
    PowerBudget,
    PowerLoadWindow,
    PowerThermalContractError,
    PowerThermalEvidenceContract,
    ThermalRiskGate,
    ThermalStatus,
    build_cell4_power_thermal_contract,
)


def test_reference_contract_binds_current_authority_without_promoting_evidence() -> None:
    authority = load_authority()
    contract = build_cell4_power_thermal_contract(authority)

    assert contract.authority_revision == authority.get("project", "authority_revision")
    assert contract.battery.candidate == "EEMB LP603450HA"
    assert contract.battery.status == BATTERY_REFERENCE_STATUS
    assert contract.battery.production_selected is False
    assert contract.battery.runtime_claim_eligible is False
    assert contract.battery.nominal_reference_energy_Wh == pytest.approx(4.07)
    assert tuple(item.load_id for item in contract.power_budget.loads) == LOAD_IDS
    assert all(item.status is LoadStatus.UNRESOLVED for item in contract.power_budget.loads)
    assert tuple(item.risk_id for item in contract.thermal_gates) == THERMAL_RISK_IDS
    assert all(item.status is ThermalStatus.BLOCKED for item in contract.thermal_gates)
    assert contract.physical_validation_eligible is False
    contract.validate_current_authority(authority)


def test_reference_nameplate_energy_does_not_authorize_runtime() -> None:
    contract = build_cell4_power_thermal_contract(load_authority())
    assert contract.battery.nominal_reference_energy_Wh > 0.0
    assert contract.battery.runtime_claim_eligible is False
    assert contract.power_budget.runtime_claim_eligible is False
    with pytest.raises(PowerThermalContractError, match="cannot close"):
        contract.power_budget.energy_bounds_Wh()


def test_packaging_benchmark_cannot_be_promoted_to_production_or_runtime() -> None:
    contract = build_cell4_power_thermal_contract(load_authority())
    with pytest.raises(PowerThermalContractError, match="production-selected"):
        replace(contract.battery, production_selected=True)
    with pytest.raises(PowerThermalContractError, match="runtime claims"):
        replace(contract.battery, runtime_claim_eligible=True)
    with pytest.raises(PowerThermalContractError, match="packaging-benchmark status"):
        replace(contract.battery, status="PRODUCTION_APPROVED")


def test_battery_benchmark_rejects_hostile_numeric_and_container_aliases() -> None:
    class FloatAlias(float):
        pass

    class TupleAlias(tuple):
        pass

    contract = build_cell4_power_thermal_contract(load_authority())
    with pytest.raises(PowerThermalContractError, match="exact finite numeric scalar"):
        replace(contract.battery, nominal_voltage_V=FloatAlias(3.7))
    with pytest.raises(PowerThermalContractError, match="immutable exact tuple"):
        replace(contract.battery, envelope_mm=TupleAlias(contract.battery.envelope_mm))
    with pytest.raises(PowerThermalContractError, match="negative signed zero"):
        replace(contract.battery, mass_g=-0.0)


def test_unresolved_load_cannot_smuggle_numeric_inputs_or_evidence() -> None:
    with pytest.raises(PowerThermalContractError, match="UNRESOLVED"):
        PowerLoadWindow("WATER_PUMP", LoadStatus.UNRESOLVED, minimum_power_W=0.1)
    with pytest.raises(PowerThermalContractError, match="UNRESOLVED"):
        PowerLoadWindow("WATER_PUMP", LoadStatus.UNRESOLVED, evidence_ids=("FAKE",))


def test_bounded_load_requires_complete_ordered_bounds_and_provenance() -> None:
    with pytest.raises(PowerThermalContractError, match="complete power and duration bounds"):
        PowerLoadWindow(
            "WATER_PUMP",
            LoadStatus.BOUNDED_MODEL_INPUT,
            minimum_power_W=0.1,
            maximum_power_W=0.2,
            minimum_duration_s=1.0,
            evidence_ids=("BOUND-1",),
        )
    with pytest.raises(PowerThermalContractError, match="minimum power"):
        PowerLoadWindow(
            "WATER_PUMP",
            LoadStatus.BOUNDED_MODEL_INPUT,
            minimum_power_W=0.3,
            maximum_power_W=0.2,
            minimum_duration_s=1.0,
            maximum_duration_s=2.0,
            evidence_ids=("BOUND-1",),
        )
    with pytest.raises(PowerThermalContractError, match="explicit evidence provenance"):
        PowerLoadWindow(
            "WATER_PUMP",
            LoadStatus.BOUNDED_MODEL_INPUT,
            minimum_power_W=0.1,
            maximum_power_W=0.2,
            minimum_duration_s=1.0,
            maximum_duration_s=2.0,
        )


def test_complete_bounded_power_budget_computes_energy_only_not_runtime() -> None:
    loads = tuple(
        PowerLoadWindow(
            load_id,
            LoadStatus.BOUNDED_MODEL_INPUT,
            minimum_power_W=1.0,
            maximum_power_W=2.0,
            minimum_duration_s=3.0,
            maximum_duration_s=6.0,
            evidence_ids=(f"BOUND-{index}",),
        )
        for index, load_id in enumerate(LOAD_IDS)
    )
    budget = PowerBudget(loads=loads, result_status=ENERGY_BOUND_STATUS)
    minimum, maximum = budget.energy_bounds_Wh()
    assert minimum == pytest.approx(len(LOAD_IDS) * 3.0 / 3600.0)
    assert maximum == pytest.approx(len(LOAD_IDS) * 12.0 / 3600.0)
    assert budget.runtime_claim_eligible is False


def test_power_ledger_must_be_complete_canonical_and_immutable() -> None:
    contract = build_cell4_power_thermal_contract(load_authority())
    with pytest.raises(PowerThermalContractError, match="complete controlled load set"):
        replace(contract.power_budget, loads=contract.power_budget.loads[:-1])
    with pytest.raises(PowerThermalContractError, match="complete controlled load set"):
        replace(contract.power_budget, loads=tuple(reversed(contract.power_budget.loads)))
    with pytest.raises(PowerThermalContractError, match="immutable exact tuple"):
        replace(contract.power_budget, loads=list(contract.power_budget.loads))
    with pytest.raises(PowerThermalContractError, match="modeled-only"):
        replace(contract.power_budget, result_status="RUNTIME_VERIFIED")
    with pytest.raises(PowerThermalContractError, match="runtime claims"):
        replace(contract.power_budget, runtime_claim_eligible=True)


def test_blocked_thermal_gates_cannot_carry_invented_bounds_or_evidence() -> None:
    with pytest.raises(PowerThermalContractError, match="BLOCKED"):
        ThermalRiskGate(
            "BATTERY_SELF_HEATING",
            ThermalStatus.BLOCKED,
            model_bounds=(20.0, 30.0),
            unit="degC",
        )
    with pytest.raises(PowerThermalContractError, match="BLOCKED"):
        ThermalRiskGate(
            "BATTERY_SELF_HEATING",
            ThermalStatus.BLOCKED,
            evidence_ids=("FAKE",),
        )


def test_bounded_thermal_gate_requires_ordered_bounds_unit_and_provenance() -> None:
    gate = ThermalRiskGate(
        "BATTERY_SELF_HEATING",
        ThermalStatus.BOUNDED_MODEL,
        model_bounds=(0.0, 12.0),
        unit="temperature_rise_degC",
        evidence_ids=("THERMAL-MODEL-1",),
    )
    assert gate.model_bounds == (0.0, 12.0)
    with pytest.raises(PowerThermalContractError, match="lower bound"):
        replace(gate, model_bounds=(13.0, 12.0))
    with pytest.raises(PowerThermalContractError, match="nonblank unit"):
        replace(gate, unit="")
    with pytest.raises(PowerThermalContractError, match="evidence provenance"):
        replace(gate, evidence_ids=())


def test_thermal_ledger_must_be_complete_canonical_and_immutable() -> None:
    contract = build_cell4_power_thermal_contract(load_authority())
    with pytest.raises(PowerThermalContractError, match="complete controlled risk set"):
        replace(contract, thermal_gates=contract.thermal_gates[:-1])
    with pytest.raises(PowerThermalContractError, match="complete controlled risk set"):
        replace(contract, thermal_gates=tuple(reversed(contract.thermal_gates)))
    with pytest.raises(PowerThermalContractError, match="immutable exact tuple"):
        replace(contract, thermal_gates=list(contract.thermal_gates))


def test_charging_convention_remains_preference_not_selected_hardware() -> None:
    charging = build_cell4_power_thermal_contract(load_authority()).charging
    assert charging.convention == CHARGING_PREFERENCE
    assert charging.status is ChargingConventionStatus.COMMERCIAL_PREFERENCE_ONLY
    assert charging.active_wet_cycle_charging_allowed is False
    assert charging.app_required_for_charge_recovery is False
    assert charging.ingress_architecture_verified is False
    assert charging.electrical_protection_verified is False

    with pytest.raises(PowerThermalContractError, match="not yet architecture-selected"):
        replace(charging, status=ChargingConventionStatus.ARCHITECTURE_SELECTED)
    with pytest.raises(PowerThermalContractError, match="active wet cycle"):
        replace(charging, active_wet_cycle_charging_allowed=True)
    with pytest.raises(PowerThermalContractError, match="app-only"):
        replace(charging, app_required_for_charge_recovery=True)
    with pytest.raises(PowerThermalContractError, match="cannot be promoted"):
        replace(charging, ingress_architecture_verified=True)
    with pytest.raises(PowerThermalContractError, match="cannot be promoted"):
        replace(charging, electrical_protection_verified=True)


def test_direct_construction_cannot_promote_physical_validation() -> None:
    contract = build_cell4_power_thermal_contract(load_authority())
    with pytest.raises(PowerThermalContractError, match="not physical validation evidence"):
        replace(contract, physical_validation_eligible=True)


def test_current_authority_validation_rejects_revision_and_battery_drift() -> None:
    authority = load_authority()
    contract = build_cell4_power_thermal_contract(authority)
    stale_revision = replace(contract, authority_revision="STALE")
    with pytest.raises(PowerThermalContractError, match="stale for current authority revision"):
        stale_revision.validate_current_authority(authority)

    stale_battery = replace(
        contract.battery,
        capacity_mAh=contract.battery.capacity_mAh + 1.0,
    )
    stale_contract = replace(contract, battery=stale_battery)
    with pytest.raises(PowerThermalContractError, match="stale for current authority"):
        stale_contract.validate_current_authority(authority)


def test_contract_rejects_subclassed_nested_types_and_status_aliases() -> None:
    class BatteryAlias(BatteryPackagingBenchmark):
        pass

    contract = build_cell4_power_thermal_contract(load_authority())
    aliased_battery = BatteryAlias(
        candidate=contract.battery.candidate,
        nominal_voltage_V=contract.battery.nominal_voltage_V,
        capacity_mAh=contract.battery.capacity_mAh,
        envelope_mm=contract.battery.envelope_mm,
        mass_g=contract.battery.mass_g,
        status=contract.battery.status,
    )
    with pytest.raises(PowerThermalContractError, match="exact controlled type"):
        replace(contract, battery=aliased_battery)
    with pytest.raises(PowerThermalContractError, match="exact controlled enum"):
        replace(contract.power_budget.loads[0], status="UNRESOLVED")


def test_charge_boundary_constructor_rejects_uncontrolled_convention() -> None:
    with pytest.raises(PowerThermalContractError, match="controlled commercial preference"):
        ChargingArchitectureBoundary(
            convention="PROPRIETARY_MAGNETIC_SELECTED",
            status=ChargingConventionStatus.COMMERCIAL_PREFERENCE_ONLY,
            active_wet_cycle_charging_allowed=False,
            app_required_for_charge_recovery=False,
            ingress_architecture_verified=False,
            electrical_protection_verified=False,
        )


def test_power_thermal_contract_constructor_rejects_wrong_nested_types() -> None:
    contract = build_cell4_power_thermal_contract(load_authority())
    with pytest.raises(PowerThermalContractError, match="exact controlled type"):
        PowerThermalEvidenceContract(
            authority_revision=contract.authority_revision,
            battery=object(),
            power_budget=contract.power_budget,
            thermal_gates=contract.thermal_gates,
            charging=contract.charging,
        )
