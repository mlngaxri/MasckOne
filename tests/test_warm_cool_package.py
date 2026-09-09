from __future__ import annotations

import pytest

from masck_one.warm_cool_package import (
    EVIDENCE_STATUS,
    SEQUENCE,
    ThermalEvidenceInputs,
    WarmCoolPackage,
    WarmCoolPackageError,
    build_warm_cool_package,
)


def test_package_builds_valid_deterministic_solids() -> None:
    package = build_warm_cool_package()
    manifest = package.manifest()
    assert manifest["source_main_sha"] == "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
    assert manifest["evidence_status"] == EVIDENCE_STATUS
    assert manifest["cool_sequence"] == list(SEQUENCE)
    assert manifest["cool_technology"] is None
    assert manifest["onboard_heat_sink_claimed"] is False
    for key in ("warm_left", "warm_right", "dock_heat_rejection_interface"):
        assert manifest[key]["volume_mm3"] > 0.0
        assert len(manifest[key]["bbox_min_mm"]) == 3
        assert len(manifest[key]["bbox_max_mm"]) == 3


def test_warm_stack_roles_cannot_silently_drop_sensor_or_insulation() -> None:
    package = build_warm_cool_package()
    with pytest.raises(WarmCoolPackageError):
        WarmCoolPackage(
            warm_left=package.warm_left,
            warm_right=package.warm_right,
            dock_heat_rejection_interface=package.dock_heat_rejection_interface,
            warm_stack_elements=("HEATER", "SPREADER"),
            cool_sequence=SEQUENCE,
            cool_technology=None,
            onboard_heat_sink_claimed=False,
        )


def test_cool_cannot_move_before_recovery() -> None:
    package = build_warm_cool_package()
    with pytest.raises(WarmCoolPackageError):
        WarmCoolPackage(
            warm_left=package.warm_left,
            warm_right=package.warm_right,
            dock_heat_rejection_interface=package.dock_heat_rejection_interface,
            warm_stack_elements=package.warm_stack_elements,
            cool_sequence=("CLEAN", "COOL_IF_COMMANDED", "RECOVERY"),
            cool_technology=None,
            onboard_heat_sink_claimed=False,
        )


def test_unproven_cool_technology_or_heat_sink_claim_is_rejected() -> None:
    package = build_warm_cool_package()
    with pytest.raises(WarmCoolPackageError):
        WarmCoolPackage(
            warm_left=package.warm_left,
            warm_right=package.warm_right,
            dock_heat_rejection_interface=package.dock_heat_rejection_interface,
            warm_stack_elements=package.warm_stack_elements,
            cool_sequence=SEQUENCE,
            cool_technology="TEC",
            onboard_heat_sink_claimed=False,
        )
    with pytest.raises(WarmCoolPackageError):
        WarmCoolPackage(
            warm_left=package.warm_left,
            warm_right=package.warm_right,
            dock_heat_rejection_interface=package.dock_heat_rejection_interface,
            warm_stack_elements=package.warm_stack_elements,
            cool_sequence=SEQUENCE,
            cool_technology=None,
            onboard_heat_sink_claimed=True,
        )


def test_thermal_ledger_requires_explicit_evidence_inputs_and_does_not_claim_skin_temperature() -> None:
    inputs = ThermalEvidenceInputs(
        heater_electrical_power_W=2.0,
        heater_to_spreader_efficiency=0.8,
        heated_effective_mass_kg=0.02,
        heated_effective_specific_heat_J_kgK=1000.0,
        conductive_loss_W=0.2,
        convective_radiative_loss_W=0.1,
        duration_s=10.0,
    )
    ledger = inputs.ledger()
    assert ledger["net_heating_W"] == pytest.approx(1.3)
    assert ledger["modeled_delta_temperature_K"] == pytest.approx(0.65)
    assert "NOT_SKIN_TEMPERATURE" in ledger["interpretation"]


def test_invalid_thermal_evidence_is_rejected() -> None:
    with pytest.raises(WarmCoolPackageError):
        ThermalEvidenceInputs(
            heater_electrical_power_W=2.0,
            heater_to_spreader_efficiency=1.2,
            heated_effective_mass_kg=0.02,
            heated_effective_specific_heat_J_kgK=1000.0,
            conductive_loss_W=0.2,
            convective_radiative_loss_W=0.1,
            duration_s=10.0,
        )
