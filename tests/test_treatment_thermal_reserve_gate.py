import itertools

import pytest

from masck_one.thermal_control import (
    ThermalCommand,
    ThermalCommandInterlock,
    ThermalInhibitReason,
    ThermalMode,
)
from masck_one.treatment_recovery_readiness import screen_treatment_recovery_readiness
from masck_one.treatment_thermal_reserve_gate import command_thermal_after_reserved_treatment
from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_capacity_reserve import (
    CartridgeCapacityReserve,
    screen_cartridge_capacity_reserve_evidence,
)
from masck_one.waste_fluid_overflow_guard import screen_cartridge_overflow_guard


def _reserved_readiness(*, prime_events=(0,), reserve=None):
    budget = build_authority_waste_fluid_budget()
    reserve = reserve or CartridgeCapacityReserve()
    evidence = screen_cartridge_capacity_reserve_evidence(
        budget,
        reserve,
        prime_events_by_cycle=prime_events,
        prime_recovery_ratio_contract=1.0,
    )
    return screen_treatment_recovery_readiness(evidence)


def test_reserved_thermal_boundary_preserves_exact_reserve_composition():
    reserve = CartridgeCapacityReserve(
        fill_sensor_trip_mL=1.0,
        foam_allowance_mL=2.0,
        manufacturing_tolerance_mL=1.5,
        other_integration_mL=1.0,
    )
    readiness = _reserved_readiness(reserve=reserve)
    command = command_thermal_after_reserved_treatment(
        ThermalCommandInterlock(), readiness, warm_requested=False, cool_requested=True
    )
    assert readiness.source_capacity_reserve_evidence.reserve is reserve
    assert readiness.source_capacity_guard.capacity_reserve_mL == pytest.approx(5.5)
    assert command.mode is ThermalMode.COOL


def test_scalar_only_capacity_guard_cannot_cross_reserved_thermal_boundary():
    budget = build_authority_waste_fluid_budget()
    guard = screen_cartridge_overflow_guard(
        budget,
        prime_events_by_cycle=(0,),
        prime_recovery_ratio_contract=1.0,
        capacity_reserve_mL=5.5,
    )
    readiness = screen_treatment_recovery_readiness(guard)
    assert readiness.source_capacity_reserve_evidence is None
    with pytest.raises(WasteFluidAccountingError, match="typed CapacityReservedOverflowGuard"):
        command_thermal_after_reserved_treatment(
            ThermalCommandInterlock(), readiness, warm_requested=False, cool_requested=True
        )


def test_reserved_boundary_preserves_closed_wire_state_space():
    readiness = _reserved_readiness()
    observed = set()
    for warm_requested, cool_requested in itertools.product((False, True), repeat=2):
        command = command_thermal_after_reserved_treatment(
            ThermalCommandInterlock(),
            readiness,
            warm_requested=warm_requested,
            cool_requested=cool_requested,
        )
        wire = command.to_wire()
        assert ThermalCommand.from_wire(wire) == command
        observed.add((wire["mode"], wire["warm_enable"], wire["cool_enable"], wire["inhibited"], wire["reason"]))
    assert len(observed) == 4


def test_reserved_boundary_exhausts_permitted_and_blocked_recovery_states():
    permitted = _reserved_readiness()
    blocked = _reserved_readiness(
        reserve=CartridgeCapacityReserve(other_integration_mL=34.0)
    )
    assert permitted.post_recovery_handoff_permitted is True
    assert blocked.post_recovery_handoff_permitted is False

    expected = {
        (False, False, True): ThermalCommand(ThermalMode.OFF, False, False),
        (True, False, True): ThermalCommand(ThermalMode.WARM, True, False),
        (False, True, True): ThermalCommand(ThermalMode.COOL, False, True),
        (True, True, True): ThermalCommand(
            ThermalMode.OFF,
            False,
            False,
            inhibited=True,
            reason=ThermalInhibitReason.CONFLICTING_REQUESTS,
        ),
        (False, False, False): ThermalCommand(ThermalMode.OFF, False, False),
        (True, False, False): ThermalCommand(ThermalMode.WARM, True, False),
        (False, True, False): ThermalCommand(
            ThermalMode.OFF,
            False,
            False,
            inhibited=True,
            reason=ThermalInhibitReason.RECOVERY_INCOMPLETE,
        ),
        (True, True, False): ThermalCommand(
            ThermalMode.OFF,
            False,
            False,
            inhibited=True,
            reason=ThermalInhibitReason.CONFLICTING_REQUESTS,
        ),
    }

    for readiness in (permitted, blocked):
        recovery_permitted = readiness.post_recovery_handoff_permitted
        for warm_requested, cool_requested in itertools.product((False, True), repeat=2):
            command = command_thermal_after_reserved_treatment(
                ThermalCommandInterlock(),
                readiness,
                warm_requested=warm_requested,
                cool_requested=cool_requested,
            )
            assert command == expected[
                (warm_requested, cool_requested, recovery_permitted)
            ]
            assert ThermalCommand.from_wire(command.to_wire()) == command


@pytest.mark.parametrize("readiness", [True, object(), None])
def test_reserved_boundary_rejects_untyped_readiness(readiness):
    with pytest.raises(WasteFluidAccountingError, match="exact TreatmentRecoveryReadiness"):
        command_thermal_after_reserved_treatment(
            ThermalCommandInterlock(), readiness, warm_requested=False, cool_requested=True
        )
