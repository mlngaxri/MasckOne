"""Independent algebraic closure checks for cycle-resolved fluid profiles.

These checks verify internal conservation and decision arithmetic without claiming
physical validation of recovery, leakage, retained capacity, pressure, or flow.
"""
from __future__ import annotations

import math

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_profile import ServiceFluidProfile

_TOL = 1e-12


def _close(actual: float, expected: float, label: str) -> None:
    if not math.isfinite(float(actual)) or not math.isfinite(float(expected)):
        raise WasteFluidAccountingError(f"{label} must remain finite")
    if not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=_TOL):
        raise WasteFluidAccountingError(f"{label} is inconsistent with cycle evidence")


def validate_service_profile_closure(profile: ServiceFluidProfile) -> ServiceFluidProfile:
    """Fail closed when stored cycle decisions disagree with their own volumes.

    ``ServiceFluidProfile.__post_init__`` protects structure and basic occupancy
    closure. This validator independently reconstructs the capacity margins and
    booleans that are consumed by service-life and treatment integration so a
    stale derived field cannot survive merely because its type is valid.
    """
    if type(profile) is not ServiceFluidProfile:
        raise WasteFluidAccountingError("profile closure requires exact ServiceFluidProfile evidence")
    profile.__post_init__()

    usable = float(profile.usable_capacity_mL)
    for state in profile.cycles:
        current_margin = usable - float(state.maximum_cartridge_inflow_mL)
        minimum_recovery_margin = usable - float(state.minimum_recovered_nominal_mL)
        mandatory_margin = usable - float(state.minimum_projected_service_end_recovered_mL)
        projected_margin = usable - float(state.minimum_projected_service_end_inflow_mL)

        _close(state.requirement_margin_mL, current_margin, "cycle requirement margin")
        _close(state.projected_mandatory_recovery_margin_mL, mandatory_margin, "projected mandatory-recovery margin")
        _close(state.projected_service_end_margin_mL, projected_margin, "projected service-end margin")

        expected_capacity = current_margin >= -_TOL
        expected_minimum_recovery = minimum_recovery_margin >= -_TOL
        expected_mandatory_target = mandatory_margin >= -_TOL
        expected_service_target = projected_margin >= -_TOL
        if state.capacity_satisfied is not expected_capacity:
            raise WasteFluidAccountingError("cycle capacity decision is inconsistent with capacity margin")
        if state.minimum_recovery_capacity_satisfied is not expected_minimum_recovery:
            raise WasteFluidAccountingError("minimum-recovery capacity decision is inconsistent with recovered volume")
        if state.mandatory_recovery_service_target_feasible is not expected_mandatory_target:
            raise WasteFluidAccountingError("mandatory-recovery target decision is inconsistent with projected margin")
        if state.service_target_feasible is not expected_service_target:
            raise WasteFluidAccountingError("service target decision is inconsistent with projected margin")

        if state.minimum_projected_service_end_recovered_mL + _TOL < state.minimum_recovered_nominal_mL:
            raise WasteFluidAccountingError("projected mandatory recovery cannot be below already recovered volume")
        if state.minimum_projected_service_end_inflow_mL + _TOL < state.maximum_cartridge_inflow_mL:
            raise WasteFluidAccountingError("projected cartridge inflow cannot be below already accumulated inflow")
        if state.minimum_projected_service_end_inflow_mL + _TOL < state.minimum_projected_service_end_recovered_mL:
            raise WasteFluidAccountingError("projected cartridge inflow cannot be below mandatory recovered volume")

    return profile
