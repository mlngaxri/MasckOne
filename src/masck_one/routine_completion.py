"""Executable form of the CS-015 / CS-018 routine-completion predicate.

`docs/CORE_SKETCH_P0_FEASIBILITY_CONTRACTS.md` specifies when a supported
routine may report `COMPLETE`, and `docs/contracts/core_sketch_p0_convergence_v1.json`
declares it as data. Neither is executable: the accompanying test checks that
the JSON says the right things about itself, which is a document validated
against a copy of itself rather than a predicate anything must satisfy.

This module implements the predicate.

The two rules it exists to enforce
----------------------------------
**A substitute is not the predicate.** The contract is explicit that a cycle
counter, a pump command, an aggregate coverage number, a green subsystem CI
result or an app animation cannot stand in for region completion. Those are the
things a product under schedule pressure reaches for, so they are rejected here
by type rather than by convention.

**Occlusion is not resolved by retracting one part.** If any face-facing
structure shadows skin a downstream leave-on stage requires, that stage cannot
complete until the structure clears, a secondary pass treats the region, an
independently validated route reaches it while support remains, or the region is
an explicit justified exclusion. Retracting the massage islands does not help if
a stationary annulus still covers the skin.

Not physical evidence
---------------------
This decides whether a *reported* routine state is self-consistent and whether
its completion claim is admissible. It establishes nothing about whether any
region was actually cleaned, rinsed, treated or covered. Those are physical
observables, and the contract keeps them separate on purpose: metered quantity,
deposited quantity and spatial film are three different things.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from . import _contracts


class RoutineCompletionError(ValueError):
    """Raised when a routine state or completion input is invalid."""


EVIDENCE_STATUS = "REPORTED_STATE_CONSISTENCY_NOT_PHYSICAL_TREATMENT_EVIDENCE"


class RegionState(Enum):
    """Completion state of one required facial region within one stage."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    EXCLUDED_WITH_REASON = "EXCLUDED_WITH_REASON"
    UNREACHABLE = "UNREACHABLE"
    UNSUPPORTED = "UNSUPPORTED"
    INTERRUPTED = "INTERRUPTED"
    UNKNOWN = "UNKNOWN"


# States that positively block a mandatory stage. PENDING and IN_PROGRESS mean
# "not finished yet"; these four mean "cannot finish as things stand".
BLOCKING_REGION_STATES = frozenset({
    RegionState.UNREACHABLE,
    RegionState.UNSUPPORTED,
    RegionState.INTERRUPTED,
    RegionState.UNKNOWN,
})

SATISFIED_REGION_STATES = frozenset({
    RegionState.COMPLETE,
    RegionState.EXCLUDED_WITH_REASON,
})


class ContactState(Enum):
    """State of a face-facing structure during one routine phase."""

    CONTACTING = "CONTACTING"
    NEAR_SKIN_NONCONTACT = "NEAR_SKIN_NONCONTACT"
    RETRACTED_OR_CLEARED = "RETRACTED_OR_CLEARED"
    TRANSITIONING = "TRANSITIONING"
    NOT_PRESENT = "NOT_PRESENT"
    UNKNOWN = "UNKNOWN"


# A structure in these states is not shadowing skin.
CLEAR_CONTACT_STATES = frozenset({
    ContactState.RETRACTED_OR_CLEARED,
    ContactState.NOT_PRESENT,
})


class RoutinePhase(Enum):
    PLACEMENT = 1
    CLEAN = 2
    RINSE_RECOVER = 3
    TREAT = 4
    LEAVE_ON = 5
    SETTLE = 6
    RELEASE = 7


class OcclusionResolution(Enum):
    """The four routes CS-018 allows past an occluded required region."""

    STRUCTURE_CLEARS = "STRUCTURE_CLEARS"
    SECONDARY_PASS_AFTER_CLEARING = "SECONDARY_PASS_AFTER_CLEARING"
    VALIDATED_ROUTE_WHILE_PRESENT = "VALIDATED_ROUTE_WHILE_PRESENT"
    JUSTIFIED_CLAIM_EXCLUSION = "JUSTIFIED_CLAIM_EXCLUSION"


class RoutineOutcome(Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INTERRUPTED = "INTERRUPTED"
    BLOCKED = "BLOCKED"


# Things a routine under schedule pressure reaches for instead of the predicate.
# Named so the refusal is explicit rather than assumed.
FORBIDDEN_COMPLETION_SUBSTITUTES = frozenset({
    "cycle_count",
    "pump_command_count",
    "aggregate_coverage_fraction",
    "subsystem_ci_result",
    "app_animation_state",
})


@dataclass(frozen=True, slots=True)
class RegionStatus:
    """One required facial region's state within one stage.

    An exclusion carries its justification and the claim version it was agreed
    under. The contract is emphatic that `EXCLUDED_WITH_REASON` is not a
    loophole: it is for a deliberate, versioned product decision, never for a
    region the hardware simply failed to reach. That distinction is the whole
    point, so it is enforced rather than trusted.
    """

    region_id: str
    state: RegionState
    exclusion_reason: str = ""
    exclusion_claim_version: str = ""
    excluded_due_to_hardware_limitation: bool = False

    def __post_init__(self) -> None:
        _contracts.non_empty_text(self.region_id, "region_id", RoutineCompletionError)
        if not isinstance(self.state, RegionState):
            raise RoutineCompletionError(f"{self.region_id}: state must be a RegionState")

        if self.state is RegionState.EXCLUDED_WITH_REASON:
            _contracts.non_empty_text(
                self.exclusion_reason, f"{self.region_id} exclusion_reason", RoutineCompletionError
            )
            _contracts.non_empty_text(
                self.exclusion_claim_version,
                f"{self.region_id} exclusion_claim_version",
                RoutineCompletionError,
            )
            if self.excluded_due_to_hardware_limitation:
                raise RoutineCompletionError(
                    f"{self.region_id}: a region the hardware could not reach is UNREACHABLE, "
                    "not EXCLUDED_WITH_REASON; the exclusion state is for deliberate, "
                    "versioned product decisions only"
                )
        elif self.exclusion_reason or self.exclusion_claim_version:
            raise RoutineCompletionError(
                f"{self.region_id}: exclusion metadata is only meaningful with "
                "EXCLUDED_WITH_REASON"
            )

    @property
    def is_satisfied(self) -> bool:
        return self.state in SATISFIED_REGION_STATES

    @property
    def is_blocking(self) -> bool:
        return self.state in BLOCKING_REGION_STATES

    def manifest(self) -> dict[str, object]:
        return {
            "region_id": self.region_id,
            "state": self.state.value,
            "satisfied": self.is_satisfied,
            "blocking": self.is_blocking,
            "exclusion_reason": self.exclusion_reason,
            "exclusion_claim_version": self.exclusion_claim_version,
        }


@dataclass(frozen=True, slots=True)
class ContactElement:
    """A face-facing structure and the regions it can shadow.

    Every object that can cover skin is an occlusion participant -- perimeter
    seals, support pads, retention interfaces, treatment islands, stationary
    annuli, thermal surfaces, optical carriers, distribution surfaces, alignment
    contacts, and any bridge or rib capable of covering required skin.
    """

    element_id: str
    phase_states: dict[RoutinePhase, ContactState]
    occludable_regions: frozenset[str] = frozenset()
    structural_function: str = ""

    def __post_init__(self) -> None:
        _contracts.non_empty_text(self.element_id, "element_id", RoutineCompletionError)
        missing = set(RoutinePhase) - set(self.phase_states)
        if missing:
            raise RoutineCompletionError(
                f"{self.element_id}: every phase must declare a state; missing "
                f"{sorted(p.name for p in missing)}"
            )
        for phase, state in self.phase_states.items():
            if not isinstance(state, ContactState):
                raise RoutineCompletionError(
                    f"{self.element_id}: {phase.name} state must be a ContactState"
                )

    def occludes_during(self, phase: RoutinePhase, region_id: str) -> bool:
        if region_id not in self.occludable_regions:
            return False
        return self.phase_states[phase] not in CLEAR_CONTACT_STATES

    def manifest(self) -> dict[str, object]:
        return {
            "element_id": self.element_id,
            "structural_function": self.structural_function,
            "occludable_regions": sorted(self.occludable_regions),
            "phase_states": {p.name: s.value for p, s in sorted(
                self.phase_states.items(), key=lambda kv: kv[0].value
            )},
        }


@dataclass(frozen=True, slots=True)
class Stage:
    """One stage of a prepared routine."""

    stage_id: str
    phase: RoutinePhase
    regions: tuple[RegionStatus, ...]
    mandatory: bool = True
    requires_settle: bool = False
    settle_completed: bool = False
    # Regions whose occlusion has been resolved, and by which route.
    occlusion_resolutions: dict[str, OcclusionResolution] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _contracts.non_empty_text(self.stage_id, "stage_id", RoutineCompletionError)
        if not isinstance(self.phase, RoutinePhase):
            raise RoutineCompletionError(f"{self.stage_id}: phase must be a RoutinePhase")
        seen: set[str] = set()
        for region in self.regions:
            if not isinstance(region, RegionStatus):
                raise RoutineCompletionError(f"{self.stage_id}: regions must be RegionStatus")
            if region.region_id in seen:
                raise RoutineCompletionError(
                    f"{self.stage_id}: region {region.region_id} declared twice"
                )
            seen.add(region.region_id)

    @property
    def region_ids(self) -> frozenset[str]:
        return frozenset(r.region_id for r in self.regions)

    def manifest(self) -> dict[str, object]:
        return {
            "stage_id": self.stage_id,
            "phase": self.phase.name,
            "mandatory": self.mandatory,
            "requires_settle": self.requires_settle,
            "settle_completed": self.settle_completed,
            "regions": [r.manifest() for r in self.regions],
            "occlusion_resolutions": {
                k: v.value for k, v in sorted(self.occlusion_resolutions.items())
            },
        }


@dataclass(frozen=True, slots=True)
class Blocker:
    """One reason a routine may not report COMPLETE."""

    code: str
    stage_id: str
    detail: str

    def manifest(self) -> dict[str, str]:
        return {"code": self.code, "stage_id": self.stage_id, "detail": self.detail}


@dataclass(frozen=True)
class RoutineAssessment:
    routine_id: str
    outcome: RoutineOutcome
    blockers: tuple[Blocker, ...]
    emergency_release_invoked: bool

    @property
    def may_claim_complete(self) -> bool:
        return self.outcome is RoutineOutcome.COMPLETE

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "MASCK_ONE_ROUTINE_COMPLETION_V1",
            "evidence_status": EVIDENCE_STATUS,
            "routine_id": self.routine_id,
            "outcome": self.outcome.value,
            "may_claim_complete": self.may_claim_complete,
            "emergency_release_invoked": self.emergency_release_invoked,
            "blockers": [b.manifest() for b in self.blockers],
            "not_evidence_of": [
                "actual cleansing, rinsing or treatment of any region",
                "deposited product quantity or spatial film",
                "labeled SPF protection",
                "skin outcome or comfort",
            ],
        }


def evaluate_routine(
    routine_id: str,
    stages: tuple[Stage, ...],
    contacts: tuple[ContactElement, ...] = (),
    *,
    emergency_release_invoked: bool = False,
    release_preserved_leave_on: bool = True,
    session_state_valid: bool = True,
    completion_substitutes: dict[str, object] | None = None,
) -> RoutineAssessment:
    """Decide whether a reported routine state may claim COMPLETE.

    Emergency release outranks everything. An emergency release may yield
    INTERRUPTED or PARTIAL and must never be delayed to preserve a cosmetic
    layer, so it is evaluated before any film-preservation consideration.
    """

    _contracts.non_empty_text(routine_id, "routine_id", RoutineCompletionError)
    if not stages:
        raise RoutineCompletionError("a routine must declare at least one stage")

    if completion_substitutes:
        offered = set(completion_substitutes) & FORBIDDEN_COMPLETION_SUBSTITUTES
        if offered:
            raise RoutineCompletionError(
                "a cycle counter, pump command, aggregate coverage number, subsystem CI "
                "result or app animation cannot substitute for region completion; "
                f"refused: {sorted(offered)}"
            )

    seen: set[str] = set()
    for stage in stages:
        if stage.stage_id in seen:
            raise RoutineCompletionError(f"stage {stage.stage_id} declared twice")
        seen.add(stage.stage_id)

    blockers: list[Blocker] = []

    for stage in stages:
        if not stage.mandatory:
            # Omitting a genuinely optional modality does not invalidate a routine.
            continue

        for region in stage.regions:
            if region.is_blocking:
                blockers.append(Blocker(
                    f"REGION_{region.state.value}", stage.stage_id,
                    f"required region {region.region_id} is {region.state.value}",
                ))
            elif not region.is_satisfied:
                blockers.append(Blocker(
                    "REGION_NOT_COMPLETE", stage.stage_id,
                    f"required region {region.region_id} is {region.state.value}",
                ))

        # CS-018: a downstream leave-on stage cannot complete over skin that a
        # face-facing structure is still shadowing.
        if stage.phase in (RoutinePhase.LEAVE_ON, RoutinePhase.SETTLE):
            for region in stage.regions:
                if region.state is RegionState.EXCLUDED_WITH_REASON:
                    continue
                occluders = [
                    c.element_id for c in contacts
                    if c.occludes_during(stage.phase, region.region_id)
                ]
                if occluders and region.region_id not in stage.occlusion_resolutions:
                    blockers.append(Blocker(
                        "UNRESOLVED_OCCLUSION", stage.stage_id,
                        f"{region.region_id} is shadowed by {sorted(occluders)} with no "
                        "declared clearing, secondary pass, validated route or exclusion",
                    ))

        if stage.requires_settle and not stage.settle_completed:
            blockers.append(Blocker(
                "SETTLE_INCOMPLETE", stage.stage_id,
                "required settling did not complete, so downstream release-ready status is blocked",
            ))

    if not session_state_valid:
        blockers.append(Blocker(
            "SESSION_STATE_INVALID", "-",
            "product identity, preparation, carryover/service or resource state is not valid",
        ))

    # Release is part of completion: a leave-on stage is invalidated if normal
    # removal materially wipes a required region.
    if not release_preserved_leave_on and not emergency_release_invoked:
        blockers.append(Blocker(
            "RELEASE_DID_NOT_PRESERVE_LEAVE_ON", "-",
            "normal release did not preserve the required final leave-on state",
        ))

    if emergency_release_invoked:
        outcome = RoutineOutcome.INTERRUPTED if blockers else RoutineOutcome.PARTIAL
    elif not blockers:
        outcome = RoutineOutcome.COMPLETE
    elif any(b.code.startswith("REGION_") and b.code != "REGION_NOT_COMPLETE" for b in blockers):
        outcome = RoutineOutcome.BLOCKED
    elif any(b.code in {"UNRESOLVED_OCCLUSION", "SESSION_STATE_INVALID"} for b in blockers):
        outcome = RoutineOutcome.BLOCKED
    else:
        outcome = RoutineOutcome.PARTIAL

    return RoutineAssessment(
        routine_id=routine_id,
        outcome=outcome,
        blockers=tuple(blockers),
        emergency_release_invoked=emergency_release_invoked,
    )
