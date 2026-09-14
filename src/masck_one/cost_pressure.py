"""Where a mechanism spends, against where the user can perceive it.

The design brief's cost rule is a single instruction: *invest where the customer
perceives or needs the quality, and reject an expensive architecture when a
moulded, stamped or flexural solution delivers effectively the same user
experience.* Nothing in the repository could evaluate that, because nothing
related a mechanism's cost drivers to whether anyone can tell.

This module does, in relative terms only.

No currency, deliberately
-------------------------
There are no unit costs here and there will not be until a producer quotes the
part. Inventing a figure would be exactly the fabrication the evidence firewall
exists to prevent, and a wrong cost is more dangerous than no cost because it
gets carried into decisions. What can be established without a quotation is
*relative pressure*: a mechanism needing a side action costs more to tool than
one that ejects on the main pull, on any resin, at any volume, from any
producer.

The two screens already in the repository supply real inputs. Tolerance burden
comes from `process_capability` -- a stack graded INFEASIBLE or MARGINAL means
paying for tighter process or scrapping parts. Tooling pressure comes from
`moldability` -- a zero-draft face needs a side action or a tool split, both of
which are real money.

What it is for
--------------
Two failure modes, not one. Over-investment is spending where nobody can
perceive it. Under-investment is skimping where everybody can. Both are findings.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import _contracts


class CostPressureError(ValueError):
    """Raised when a cost-pressure input or contract is invalid."""


EVIDENCE_STATUS = "RELATIVE_COST_PRESSURE_NOT_QUOTED_OR_MODELLED_UNIT_COST"


class Perceptibility(Enum):
    """How directly the user encounters a mechanism. Ordered, low to high."""

    INTERNAL_INVISIBLE = 1     # sealed inside; never seen, touched or heard
    INTERNAL_AUDIBLE = 2       # heard during use but not seen or touched
    VISIBLE_SURFACE = 3        # seen on every use
    HAND_OPERATED = 4          # deliberately operated by hand
    SKIN_CONTACT = 5           # against the face during treatment


class CostDriver(Enum):
    """Sources of cost, ordered low to high by how hard each is to remove."""

    PART_COUNT = 1             # more parts, more assembly, more stack
    ASSEMBLY_STEPS = 2         # labour and fixturing
    MATERIAL_CLASS = 3         # engineering resin, filled grade, metal insert
    TOLERANCE_BURDEN = 4       # tighter process, higher scrap
    TOOLING_ACTION = 5         # side action, tool split, unscrewing core


class Verdict(Enum):
    BALANCED = "BALANCED"
    AVOIDABLE_COST = "AVOIDABLE_COST"
    OVER_ENGINEERED = "OVER_ENGINEERED"
    UNDER_INVESTED = "UNDER_INVESTED"


@dataclass(frozen=True, slots=True)
class MechanismCostProfile:
    """One mechanism's cost drivers set against its perceptibility."""

    mechanism_id: str
    perceptibility: Perceptibility
    drivers: tuple[CostDriver, ...]
    removable_by_geometry: tuple[CostDriver, ...] = ()
    note: str = ""

    def __post_init__(self) -> None:
        _contracts.non_empty_text(self.mechanism_id, "mechanism_id", CostPressureError)
        if not isinstance(self.perceptibility, Perceptibility):
            raise CostPressureError(f"{self.mechanism_id}: perceptibility must be a Perceptibility")
        for driver in self.drivers:
            if not isinstance(driver, CostDriver):
                raise CostPressureError(f"{self.mechanism_id}: drivers must be CostDriver")
        unknown = set(self.removable_by_geometry) - set(self.drivers)
        if unknown:
            raise CostPressureError(
                f"{self.mechanism_id}: cannot remove drivers it does not have: "
                f"{sorted(d.name for d in unknown)}"
            )

    @property
    def pressure(self) -> int:
        """Total relative cost pressure. Ordinal, not a currency."""

        return sum(driver.value for driver in self.drivers)

    @property
    def removable_pressure(self) -> int:
        """Pressure that a geometry change alone would eliminate."""

        return sum(driver.value for driver in self.removable_by_geometry)

    @property
    def irreducible_pressure(self) -> int:
        return self.pressure - self.removable_pressure

    def manifest(self) -> dict[str, object]:
        return {
            "mechanism_id": self.mechanism_id,
            "perceptibility": self.perceptibility.name,
            "drivers": [d.name for d in self.drivers],
            "removable_by_geometry": [d.name for d in self.removable_by_geometry],
            "pressure": self.pressure,
            "removable_pressure": self.removable_pressure,
            "irreducible_pressure": self.irreducible_pressure,
            "note": self.note,
        }


# Pressure a mechanism may irreducibly carry before its perceptibility has to
# justify it. Ordinal thresholds, tuned so that a mechanism nobody perceives
# cannot quietly accumulate tooling actions.
_JUSTIFIED_PRESSURE = {
    Perceptibility.INTERNAL_INVISIBLE: 4,
    Perceptibility.INTERNAL_AUDIBLE: 6,
    Perceptibility.VISIBLE_SURFACE: 9,
    Perceptibility.HAND_OPERATED: 12,
    Perceptibility.SKIN_CONTACT: 12,
}

# Below this, a highly perceptible mechanism is probably being skimped.
_MINIMUM_PRESSURE = {
    Perceptibility.HAND_OPERATED: 4,
    Perceptibility.SKIN_CONTACT: 4,
}

# Removable pressure at or above this is a finding in its own right: cost the
# design is paying that a geometry change would delete.
AVOIDABLE_PRESSURE_THRESHOLD = 3


@dataclass(frozen=True, slots=True)
class InvestmentAssessment:
    profile: MechanismCostProfile
    verdict: Verdict
    justified_pressure: int
    reason: str

    def manifest(self) -> dict[str, object]:
        return {
            **self.profile.manifest(),
            "verdict": self.verdict.value,
            "justified_pressure": self.justified_pressure,
            "reason": self.reason,
            "evidence_status": EVIDENCE_STATUS,
        }


def assess_investment(profile: MechanismCostProfile) -> InvestmentAssessment:
    """Is this mechanism spending where the user can tell?

    Avoidable cost is checked first and outranks the rest. A mechanism whose
    pressure a geometry change would delete is not an architecture to be judged
    on its merits -- it is an architecture to be changed, which is precisely
    what the brief's cost rule instructs. Judging only irreducible pressure
    would report such a design as balanced and bury the finding.
    """

    if not isinstance(profile, MechanismCostProfile):
        raise CostPressureError("profile must be a MechanismCostProfile")

    ceiling = _JUSTIFIED_PRESSURE[profile.perceptibility]
    floor = _MINIMUM_PRESSURE.get(profile.perceptibility, 0)
    irreducible = profile.irreducible_pressure

    if profile.removable_pressure >= AVOIDABLE_PRESSURE_THRESHOLD:
        verdict = Verdict.AVOIDABLE_COST
        removable = ", ".join(d.name for d in profile.removable_by_geometry)
        reason = (
            f"{profile.removable_pressure} of {profile.pressure} pressure points "
            f"are removable by a geometry change ({removable}); change the geometry "
            "rather than pay for the architecture"
        )
    elif irreducible > ceiling:
        verdict = Verdict.OVER_ENGINEERED
        reason = (
            f"irreducible pressure {irreducible} exceeds what "
            f"{profile.perceptibility.name} justifies ({ceiling})"
        )
    elif irreducible < floor:
        verdict = Verdict.UNDER_INVESTED
        reason = (
            f"irreducible pressure {irreducible} is below the minimum "
            f"{profile.perceptibility.name} warrants ({floor})"
        )
    else:
        verdict = Verdict.BALANCED
        reason = f"irreducible pressure {irreducible} is within {ceiling} for {profile.perceptibility.name}"

    return InvestmentAssessment(profile, verdict, ceiling, reason)


# ---------------------------------------------------------------------------
# applied: the zero-draft apertures
# ---------------------------------------------------------------------------

def aperture_tooling_profiles() -> tuple[MechanismCostProfile, MechanismCostProfile]:
    """The shell apertures, before and after tapering the cutters.

    `moldability.py` measures all five protected aperture walls at 0.00 deg
    against a 2.10 deg requirement. Left as they are, releasing them needs a
    side action or a tool split -- the most expensive driver there is, on the
    most perceptible surface on the product.

    Tapering the cutters removes that driver outright for the cost of a CAD
    edit, which is exactly the substitution the brief's cost rule asks for:
    reject the expensive architecture when a moulded solution delivers the same
    user experience.
    """

    as_built = MechanismCostProfile(
        mechanism_id="SHELL_APERTURES_ZERO_DRAFT",
        perceptibility=Perceptibility.SKIN_CONTACT,
        drivers=(
            CostDriver.TOOLING_ACTION,   # side action or tool split to release
            CostDriver.TOLERANCE_BURDEN, # a witness line lands on a visible edge
            CostDriver.MATERIAL_CLASS,
            CostDriver.PART_COUNT,
        ),
        removable_by_geometry=(CostDriver.TOOLING_ACTION, CostDriver.TOLERANCE_BURDEN),
        note="five aperture walls at 0.00 deg against a 2.10 deg requirement",
    )
    tapered = MechanismCostProfile(
        mechanism_id="SHELL_APERTURES_TAPERED",
        perceptibility=Perceptibility.SKIN_CONTACT,
        drivers=(CostDriver.MATERIAL_CLASS, CostDriver.PART_COUNT),
        note="cutters drafted to >=2.10 deg; releases on the main pull",
    )
    return as_built, tapered
