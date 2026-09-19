"""Cross-requirement closure checks for nominal CLEAN-cycle liquid.

This module reconciles the recovery floor with the residual-fluid and external-
leakage ceilings without treating those ceilings as measured sinks. The result is
a synthetic requirement-consistency bound, not a physical fluid-loss model.
"""
from __future__ import annotations

from dataclasses import dataclass

from .waste_fluid_accounting import WasteFluidBudget


@dataclass(frozen=True)
class NonrecoveryClosure:
    """Requirement-space accounting for nominal liquid not recovered as waste."""

    maximum_unrecovered_nominal_mL: float
    residual_ceiling_mL: float
    external_leakage_ceiling_mL: float
    classified_nonrecovery_ceiling_mL: float
    unclassified_nonrecovery_allowance_mL: float
    classified_sink_headroom_mL: float
    closes_using_only_classified_sinks: bool


def screen_nonrecovery_closure(budget: WasteFluidBudget) -> NonrecoveryClosure:
    """Reconcile recovery, residual and leakage requirements for one nominal cycle.

    At the minimum recovery ratio, ``maximum_unrecovered_nominal_mL`` is the
    largest nominal volume that may remain outside recovered waste. Residual and
    external leakage are independent ceilings, not predictions, so they are summed
    only to ask whether those two named sinks can account for that unrecovered
    allowance in requirement space.

    A positive ``unclassified_nonrecovery_allowance_mL`` means the recovery floor
    permits more unrecovered liquid than the two named sink ceilings can explain.
    A positive ``classified_sink_headroom_mL`` means the named ceilings are wider
    than the unrecovered allowance. Neither quantity is evidence that fluid follows
    any particular route.
    """
    budget.validate()
    unrecovered = budget.maximum_unrecovered_nominal_mL_per_cycle
    classified = budget.maximum_classified_nonrecovery_mL_per_cycle
    gap = unrecovered - classified
    tolerance = 1e-12
    return NonrecoveryClosure(
        maximum_unrecovered_nominal_mL=unrecovered,
        residual_ceiling_mL=budget.residual_free_liquid_max_mL,
        external_leakage_ceiling_mL=budget.external_leakage_max_mL_per_cycle,
        classified_nonrecovery_ceiling_mL=classified,
        unclassified_nonrecovery_allowance_mL=max(0.0, gap),
        classified_sink_headroom_mL=max(0.0, -gap),
        closes_using_only_classified_sinks=gap <= tolerance,
    )
