from dataclasses import replace

import pytest

from masck_one.distribution_geometry import DistributionGeometryError
from masck_one.thermal_control import ThermalCommandInterlock, ThermalMode
from masck_one.treatment_clean_distribution_evidence import build_treatment_clean_distribution_evidence
from masck_one.treatment_full_evidence import (
    build_full_treatment_evidence,
    validate_full_treatment_evidence,
)
from masck_one.treatment_integrated_evidence import build_integrated_treatment_evidence
from masck_one.treatment_massage_thermal_evidence import build_treatment_massage_thermal_evidence
from masck_one.treatment_recovery_readiness import screen_treatment_recovery_readiness
from masck_one.treatment_thermal_handoff import command_thermal_from_full_treatment_evidence
from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_overflow_guard import screen_cartridge_overflow_guard
from tests.test_actuation_zone_system_response import _parameters, _sweep
from tests.test_distribution_geometry import built


def _recovery():
    budget = build_authority_waste_fluid_budget()
    guard = screen_cartridge_overflow_guard(
        budget,
        prime_events_by_cycle=[0] * budget.service_cycles,
        prime_recovery_ratio_contract=1.0,
    )
    return screen_treatment_recovery_readiness(guard)


def _sources(built):
    model, water, cleanser, frame, pump, manifold, geometry = built
    return geometry, dict(
        authority=model.authority,
        manifold=manifold,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=model.coverage_mesh,
        protected=model.protected_volumes,
    )


def _full(built):
    geometry, sources = _sources(built)
    recovery = _recovery()
    clean = build_treatment_clean_distribution_evidence(geometry, recovery, **sources)
    parameters = _parameters()
    sweep = _sweep(parameters)
    massage_thermal = build_treatment_massage_thermal_evidence(sweep, parameters)
    integrated = build_integrated_treatment_evidence(recovery, sweep, parameters, massage_thermal)
    full = build_full_treatment_evidence(
        clean, integrated, sweep=sweep, parameters=parameters, **sources
    )
    return sources, parameters, sweep, full


def test_accepts_one_shared_recovery_tree_across_all_treatment_subsystems(built):
    sources, parameters, sweep, full = _full(built)
    assert full.clean.recovery is full.integrated.recovery
    assert validate_full_treatment_evidence(
        full, sweep=sweep, parameters=parameters, **sources
    ) is full


def test_rejects_independently_qualified_recovery_trees_even_when_both_are_valid(built):
    geometry, sources = _sources(built)
    clean = build_treatment_clean_distribution_evidence(geometry, _recovery(), **sources)
    parameters = _parameters()
    sweep = _sweep(parameters)
    integrated = build_integrated_treatment_evidence(
        _recovery(), sweep, parameters, build_treatment_massage_thermal_evidence(sweep, parameters)
    )
    with pytest.raises(WasteFluidAccountingError, match="one shared recovery qualification"):
        build_full_treatment_evidence(
            clean, integrated, sweep=sweep, parameters=parameters, **sources
        )


def test_rejects_forged_clean_distribution_binding_inside_full_tree(built):
    sources, parameters, sweep, full = _full(built)
    forged_clean = replace(full.clean, source_distribution_sha256="0" * 64)
    with pytest.raises(DistributionGeometryError, match="digest does not match"):
        validate_full_treatment_evidence(
            replace(full, clean=forged_clean), sweep=sweep, parameters=parameters, **sources
        )


def test_rejects_wrong_full_evidence_type(built):
    _, sources = _sources(built)
    parameters = _parameters()
    with pytest.raises(TypeError, match="exact FullTreatmentEvidence"):
        validate_full_treatment_evidence(
            object(), sweep=_sweep(parameters), parameters=parameters, **sources
        )


def test_full_treatment_evidence_can_enable_cool_only_after_complete_revalidation(built):
    sources, parameters, sweep, full = _full(built)
    command = command_thermal_from_full_treatment_evidence(
        ThermalCommandInterlock(), sweep, parameters, full,
        **sources, warm_requested=False, cool_requested=True,
    )
    assert command.mode is ThermalMode.COOL
    assert command.cool_enable
    assert not command.inhibited


def test_full_treatment_thermal_boundary_rejects_forged_clean_distribution_before_cool(built):
    sources, parameters, sweep, full = _full(built)
    forged = replace(full, clean=replace(full.clean, source_distribution_sha256="0" * 64))
    with pytest.raises(DistributionGeometryError, match="digest does not match"):
        command_thermal_from_full_treatment_evidence(
            ThermalCommandInterlock(), sweep, parameters, forged,
            **sources, warm_requested=False, cool_requested=True,
        )


def test_full_treatment_thermal_boundary_rejects_substituted_recovery_before_cool(built):
    sources, parameters, sweep, full = _full(built)
    substituted = replace(full, integrated=replace(full.integrated, recovery=_recovery()))
    with pytest.raises(WasteFluidAccountingError, match="one shared recovery qualification"):
        command_thermal_from_full_treatment_evidence(
            ThermalCommandInterlock(), sweep, parameters, substituted,
            **sources, warm_requested=False, cool_requested=True,
        )


def test_full_treatment_thermal_boundary_preserves_simultaneous_mode_inhibition(built):
    sources, parameters, sweep, full = _full(built)
    command = command_thermal_from_full_treatment_evidence(
        ThermalCommandInterlock(), sweep, parameters, full,
        **sources, warm_requested=True, cool_requested=True,
    )
    assert command.mode is ThermalMode.OFF
    assert not command.warm_enable
    assert not command.cool_enable
    assert command.inhibited


def test_full_treatment_thermal_boundary_preserves_warm_command_semantics(built):
    sources, parameters, sweep, full = _full(built)
    command = command_thermal_from_full_treatment_evidence(
        ThermalCommandInterlock(), sweep, parameters, full,
        **sources, warm_requested=True, cool_requested=False,
    )
    assert command.mode is ThermalMode.WARM
    assert command.warm_enable
    assert not command.cool_enable
    assert not command.inhibited
