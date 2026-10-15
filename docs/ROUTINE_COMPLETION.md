# Routine completion — the predicate, executable

Read this before changing what a routine reports, or before adding a signal that
looks like it proves a stage finished.

## What this implements

`docs/CORE_SKETCH_P0_FEASIBILITY_CONTRACTS.md` (CS-015, CS-018) specifies when a
supported routine may report `COMPLETE`, and
`docs/contracts/core_sketch_p0_convergence_v1.json` declares it as data.

Neither was executable. The accompanying test checks that the JSON says the
right things about itself — a document validated against a copy of itself,
rather than a predicate anything has to satisfy.

`src/masck_one/routine_completion.py` implements it.

## The two rules it exists to enforce

### A substitute is not the predicate

The contract is explicit that none of these can stand in for region completion:

- a cycle counter
- a pump command count
- an aggregate coverage number
- a green subsystem CI result
- an app animation state

These are exactly what a product under schedule pressure reaches for, so
`evaluate_routine` **refuses them by name**. Passing any of them raises. Passing
unrelated telemetry does not — the refusal is specific, not a blanket ban.

### Occlusion is not resolved by retracting one part

> Retracting massage islands alone does not solve the complete-routine problem
> if another stationary element still shadows skin that requires a final layer.

Every face-facing object is an occlusion participant: perimeter seals, support
pads, retention interfaces, treatment islands, stationary annuli, thermal
surfaces, optical carriers, distribution surfaces, alignment contacts, and any
bridge or rib capable of covering required skin. Each declares a state across all
seven phases — a `ContactElement` missing a phase fails closed.

Only `RETRACTED_OR_CLEARED` and `NOT_PRESENT` count as not shadowing.
`NEAR_SKIN_NONCONTACT` and `TRANSITIONING` still block, and `UNKNOWN` is never a
pass.

A declared `STRUCTURE_CLEARS` or `SECONDARY_PASS_AFTER_CLEARING` route requires
all declared contacts covering the region to report cleared or absent during the
stage. A route label cannot override a still-shadowing contact snapshot. The
secondary-pass route also requires the region's reported completion state; this
module cannot observe whether that pass happened.

`VALIDATED_ROUTE_WHILE_PRESENT` requires a nonblank entry for that region in
`Stage.validated_route_references`. This is a declared evidence reference for
traceability, not authentication, an evidence registry lookup, or verification
that the referenced physical study exists or supports the route. The caller is
responsible for binding a reviewed study to its actual configuration.

`JUSTIFIED_CLAIM_EXCLUSION` requires the region to be
`EXCLUDED_WITH_REASON`, including its reason and claim version. String route
labels, resolutions for undeclared regions, and orphan route references raise
`RoutineCompletionError`. Contact phase mappings and stage resolution mappings
are copied into read-only snapshots; changing a caller's dictionaries cannot
change the assessment inputs later. Region collections are also snapshotted.

## Exclusion is not a loophole

`EXCLUDED_WITH_REASON` requires a reason **and** a claim version, and it
explicitly rejects an exclusion flagged as caused by hardware limitation:

> a region the hardware could not reach is `UNREACHABLE`, not
> `EXCLUDED_WITH_REASON`

That is the distinction the contract calls out, so it is enforced rather than
trusted. Exclusion metadata on a non-excluded region also fails closed.

## Blocking versus unfinished

Four states positively block a mandatory stage — `UNREACHABLE`, `UNSUPPORTED`,
`INTERRUPTED`, `UNKNOWN`. `PENDING` and `IN_PROGRESS` mean *not finished yet*,
which yields `PARTIAL` rather than `BLOCKED`. Those are different situations and
the outcome distinguishes them.

Omitting a genuinely optional modality does not invalidate a routine. A
mandatory stage left pending does. A mandatory stage must declare at least one
region, and a routine containing only optional stages is `BLOCKED`.

## Supplying positive completion evidence

`evaluate_routine` defaults `session_state_valid` and
`release_preserved_leave_on` to `None` (unknown). Omitted or unknown evidence
blocks a normal `COMPLETE` claim. Callers migrating from the earlier optimistic
defaults must explicitly supply their reported evidence:

```python
assessment = evaluate_routine(
    "session-17", stages, contacts,
    session_state_valid=session_checks_passed,
    release_preserved_leave_on=normal_removal_preserved_layer,
)
```

Those two inputs accept only `True`, `False`, or `None`. Stage boolean flags,
`emergency_release_invoked`, and `excluded_due_to_hardware_limitation` require
actual booleans: strings and integers cannot stand in for evidence. Duplicate
stage, region, or contact-element identifiers are rejected.

The host-only offline journal's `REPORT_SEQUENCE_FINISHED` state is not one of
these positive evidence inputs. Recording every software stage report does not
establish regional completion, session validity, or film preservation.

## Safety ordering

The assessment does not command, enable, or inhibit a release mechanism.
Unpowered emergency release must remain independent of this software and its
inputs. Reporting an emergency release always prevents `COMPLETE`, even when
all reported regions are satisfied.

Emergency release outranks film preservation. It may
yield `INTERRUPTED` or `PARTIAL`, and a leave-on layer wiped by an emergency
release is **not** held against the routine — it must never be delayed to
preserve a cosmetic layer.

Normal release is different: release is part of completion, so a normal release
that materially wipes a required region blocks it.

## What this is not

`REPORTED_STATE_CONSISTENCY_NOT_PHYSICAL_TREATMENT_EVIDENCE`.

It decides whether a *reported* routine state is self-consistent and whether its
completion claim is admissible. It establishes nothing about whether any region
was actually cleaned, rinsed, treated or covered.

The contract keeps those separate on purpose: metered quantity, deposited
quantity and spatial film are three different observables, and dispensed mass or
a visible film cannot by themselves establish labeled SPF protection.
