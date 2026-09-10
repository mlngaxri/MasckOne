"""Can a manufacturing process actually hold the tolerances the CAD assumes?

`mechanism_tolerance.py` does worst-case interval arithmetic on dimension
chains and says so plainly: it "does not claim manufacturing capability". That
leaves the question `ENGINEERING_GOVERNANCE` and the design brief both insist
on -- *a 0.02 mm CAD clearance is meaningless if the moulding process cannot
hold the full stack* -- unanswered anywhere in the repository.

This module answers it. It converts a tolerance budget into the per-contributor
tolerance a design would need, compares that against what a named process can
plausibly hold over a dimension chain of that length, and reports feasible,
marginal or infeasible.

Two structural facts drive every result:

**Achievable tolerance scales with the length of the dimension chain, not with
the part.** A 20 mm feature referenced to a local mating datum is held far
tighter than the same feature referenced across a 200 mm outline, in the same
tool, in the same shot. Shortening the chain is usually cheaper than tightening
the process.

**Worst-case stacking is the only defensible method here.** Statistical (RSS)
stacking assumes known, centred, capable processes -- it needs Cp/Cpk from a
qualified supplier running a qualified tool. No such data exists for this
programme. RSS is therefore computed for reference and explicitly refused as a
basis for a decision until capability evidence exists.

Everything below is a **planning value**, quoted as a band rather than a
constant, in the spirit of ISO 20457 / DIN 16901 general tolerance guidance for
moulded plastics. It is not a quotation, not a supplier commitment, and not
measured capability. A real tolerance budget is agreed with the producer who
will cut the tool.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from . import _contracts


class ProcessCapabilityError(ValueError):
    """Raised when a capability query or feasibility input is invalid."""


EVIDENCE_STATUS = "PLANNING_VALUES_NOT_SUPPLIER_OR_MEASURED_PROCESS_CAPABILITY"


class ProcessClass(Enum):
    """Manufacturing routes this programme plausibly uses."""

    INJECTION_MOULDED = "INJECTION_MOULDED"
    INJECTION_MOULDED_FILLED = "INJECTION_MOULDED_FILLED"
    LSR_MOULDED = "LSR_MOULDED"
    MACHINED_METAL = "MACHINED_METAL"
    STAMPED_SPRING_STEEL = "STAMPED_SPRING_STEEL"


# (base tolerance at 10 mm, growth per additional 10 mm of chain), as
# (optimistic, typical) pairs in mm. Tolerance grows with chain length because
# shrinkage, warp and datum transfer all accumulate along the dimension.
_CAPABILITY: dict[ProcessClass, tuple[tuple[float, float], tuple[float, float]]] = {
    #                        base at 10 mm      growth per 10 mm
    ProcessClass.INJECTION_MOULDED:        ((0.030, 0.060), (0.0090, 0.0150)),
    ProcessClass.INJECTION_MOULDED_FILLED: ((0.025, 0.050), (0.0075, 0.0135)),
    ProcessClass.LSR_MOULDED:              ((0.050, 0.100), (0.0150, 0.0250)),
    ProcessClass.MACHINED_METAL:           ((0.010, 0.025), (0.0020, 0.0050)),
    ProcessClass.STAMPED_SPRING_STEEL:     ((0.015, 0.035), (0.0040, 0.0080)),
}

# Below this ratio of achievable-to-required the design has no room at all.
MARGINAL_RATIO = 1.0
# Above this it is comfortably held even at the pessimistic end of the band.
COMFORTABLE_RATIO = 0.70


def _positive(value: float, label: str) -> float:
    return _contracts.positive(value, label, ProcessCapabilityError)


def achievable_tolerance_mm(
    process: ProcessClass, chain_length_mm: float
) -> tuple[float, float]:
    """Plausible +/- tolerance over a dimension chain of this length.

    Returns (optimistic, typical). The optimistic figure assumes a dedicated
    tooled dimension under tight process control; the typical figure is what a
    competent producer holds without heroics.
    """

    if not isinstance(process, ProcessClass):
        raise ProcessCapabilityError("process must be a ProcessClass")
    length = _positive(chain_length_mm, "chain_length_mm")
    (base_lo, base_hi), (grow_lo, grow_hi) = _CAPABILITY[process]
    steps = max(length - 10.0, 0.0) / 10.0
    return (base_lo + grow_lo * steps, base_hi + grow_hi * steps)


def required_per_contributor_mm(total_budget_mm: float, contributor_count: int) -> float:
    """Per-contributor tolerance a worst-case stack allows.

    Worst-case adds magnitudes, so N equal contributors each get budget/N. This
    is why removing one contributor from a chain buys more than tightening the
    survivors.
    """

    budget = _positive(total_budget_mm, "total_budget_mm")
    if contributor_count < 1:
        raise ProcessCapabilityError("contributor_count must be at least 1")
    return budget / contributor_count


def rss_per_contributor_mm(total_budget_mm: float, contributor_count: int) -> float:
    """Per-contributor tolerance an RSS stack would allow.

    Reference only. RSS assumes known, centred, capable processes. Without
    supplier Cp/Cpk this number is not a basis for a decision, and
    StackFeasibility refuses to use it.
    """

    budget = _positive(total_budget_mm, "total_budget_mm")
    if contributor_count < 1:
        raise ProcessCapabilityError("contributor_count must be at least 1")
    return budget / math.sqrt(contributor_count)


class Feasibility(Enum):
    FEASIBLE = "FEASIBLE"          # held even at the pessimistic end of the band
    MARGINAL = "MARGINAL"          # held only at the optimistic end
    INFEASIBLE = "INFEASIBLE"      # not held even optimistically


@dataclass(frozen=True, slots=True)
class StackFeasibility:
    """Whether a named process can hold a tolerance budget over a chain."""

    stack_id: str
    process: ProcessClass
    chain_length_mm: float
    contributor_count: int
    total_budget_mm: float
    required_per_contributor_mm: float
    achievable_optimistic_mm: float
    achievable_typical_mm: float
    feasibility: Feasibility
    shortfall_factor: float
    rss_per_contributor_mm: float

    @property
    def rss_is_usable(self) -> bool:
        """Always False. RSS needs supplier Cp/Cpk that does not exist here."""

        return False

    def manifest(self) -> dict[str, object]:
        return {
            "stack_id": self.stack_id,
            "process": self.process.value,
            "chain_length_mm": self.chain_length_mm,
            "contributor_count": self.contributor_count,
            "total_budget_mm": self.total_budget_mm,
            "required_per_contributor_mm": round(self.required_per_contributor_mm, 6),
            "achievable_optimistic_mm": round(self.achievable_optimistic_mm, 6),
            "achievable_typical_mm": round(self.achievable_typical_mm, 6),
            "feasibility": self.feasibility.value,
            "shortfall_factor": round(self.shortfall_factor, 4),
            "rss_per_contributor_mm": round(self.rss_per_contributor_mm, 6),
            "rss_is_usable": self.rss_is_usable,
            "rss_refusal_reason": (
                "RSS assumes known, centred, capable processes. No supplier Cp/Cpk "
                "exists for this programme, so worst-case is the only defensible method."
            ),
            "evidence_status": EVIDENCE_STATUS,
        }


def assess_stack(
    stack_id: str,
    *,
    process: ProcessClass,
    chain_length_mm: float,
    contributor_count: int,
    total_budget_mm: float,
) -> StackFeasibility:
    """Can this process hold this budget across this many contributors?"""

    if not stack_id.strip():
        raise ProcessCapabilityError("stack_id must be non-empty")

    required = required_per_contributor_mm(total_budget_mm, contributor_count)
    optimistic, typical = achievable_tolerance_mm(process, chain_length_mm)

    if typical <= required:
        feasibility = Feasibility.FEASIBLE
    elif optimistic <= required:
        feasibility = Feasibility.MARGINAL
    else:
        feasibility = Feasibility.INFEASIBLE

    return StackFeasibility(
        stack_id=stack_id,
        process=process,
        chain_length_mm=float(chain_length_mm),
        contributor_count=int(contributor_count),
        total_budget_mm=float(total_budget_mm),
        required_per_contributor_mm=required,
        achievable_optimistic_mm=optimistic,
        achievable_typical_mm=typical,
        feasibility=feasibility,
        # How much coarser the pessimistic capability is than the requirement.
        shortfall_factor=typical / required,
        rss_per_contributor_mm=rss_per_contributor_mm(total_budget_mm, contributor_count),
    )


# ---------------------------------------------------------------------------
# applied case: the exterior visible seam
# ---------------------------------------------------------------------------

# A seam gap referenced to the global part outline accumulates three
# contributors: each shell's edge position relative to the common locating
# frame, plus the frame itself.
SEAM_BUTT_JOINT_CONTRIBUTORS = 3
SEAM_BUTT_JOINT_CHAIN_MM = 200.0

# A self-locating seam -- the two shells mate to each other at the seam via a
# shiplap or tongue -- removes the frame term and collapses the chain to the
# local mating feature.
SEAM_SELF_LOCATING_CONTRIBUTORS = 2
SEAM_SELF_LOCATING_CHAIN_MM = 20.0


def seam_feasibility(authority, *, self_locating: bool = True) -> StackFeasibility:
    """Screen the authority's visible-seam tolerance against moulding capability.

    `geometry.visible_seam.tolerance_mm` is the total budget the gap may vary by.
    Whether it is holdable depends entirely on how the seam is located, which is
    an industrial-design and part-split decision, not a process decision.
    """

    budget = authority.number("geometry", "visible_seam", "tolerance_mm")
    if self_locating:
        stack_id, contributors, chain = (
            "VISIBLE_SEAM_SELF_LOCATING",
            SEAM_SELF_LOCATING_CONTRIBUTORS,
            SEAM_SELF_LOCATING_CHAIN_MM,
        )
    else:
        stack_id, contributors, chain = (
            "VISIBLE_SEAM_BUTT_JOINT_TO_GLOBAL_OUTLINE",
            SEAM_BUTT_JOINT_CONTRIBUTORS,
            SEAM_BUTT_JOINT_CHAIN_MM,
        )

    return assess_stack(
        stack_id,
        process=ProcessClass.INJECTION_MOULDED_FILLED,
        chain_length_mm=chain,
        contributor_count=contributors,
        total_budget_mm=budget,
    )
