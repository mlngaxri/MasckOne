# Routine and product intelligence (CS-016 / CS-017 producers)

**Status:** non-authoritative concept logic. Nothing in these modules controls
hardware, measures a fluid, or creates BENCH, HUMAN, REG_CLAIM or SUPPLIER
evidence. Every result returns `hardware_execution_authorized: False`.

## Why these modules exist

`core_sketch_contracts.py` already owns the two gates this lane is judged on:

- `assess_readiness` derives CS-016 READY from a prepared session, and
- `assess_integrity` keeps the five CS-017 product truths separate.

Both gates are sound and neither is replaced here. Both, however, **read fields
that some earlier writer chose**. `assess_readiness` refuses a product unless
`trust == "VALIDATED"` and `promoted_by` is neither `COMMUNITY` nor `AI` — but
nothing in the repository decided that value. A learning system that concluded a
product "looks fine" only had to write the word `VALIDATED` into a record, and
both gates would have waved it through, correctly, by their own rules.

The same gap sat under invalidation. `invalidate(session, event)` applies an
event that somebody already knew about, and `assess_readiness` then refuses a
session whose epoch moved. Nothing decided an event had happened. A reservoir
could be unscrewed, emptied, refilled with a different SKU and screwed back on,
and every digest comparison downstream would still agree with itself.

These three modules are the missing producers.

| Module | Produces | Consumed by |
| --- | --- | --- |
| `product_lifecycle.py` | product trust and lifecycle state | `assess_readiness`, `assess_integrity` |
| `dock_preparation.py` | invalidation events, dose manifest, inventory columns | `invalidate`, `assess_readiness`, `core_sketch_resources` |
| `routine_schedule.py` | routine identity, session plan, offline manifest, presented state | user-facing state, `assess_readiness` inputs |

## `product_lifecycle.py` — who may promote, and how far

States are `UNKNOWN → KNOWN → CHARACTERISED → VALIDATED`, with
`RESTRICTED_OR_UNSUPPORTED` reachable from anywhere. The rungs match the
internal evidence states in CS-017 §5; `UNKNOWN` is the floor below `KNOWN`,
where a product sits before its identity resolves.

Three rules carry the weight:

1. **Promotion is earned and attributed.** `AI`, `COMMUNITY`, `USER_SELF_REPORT`
   and `RETAILER_LISTING` may observe, report and restrict. They may never
   promote, *even when the evidence they cite is complete and correctly scoped*.
   Community data accelerates discovery; it does not qualify a product.
2. **Restriction is free; promotion is one rung at a time.** Anyone may move a
   product toward refusal at any moment, because that is the safe direction.
   `UNKNOWN → VALIDATED` is refused even for a bench lab.
3. **Evidence is bound to an identity version.** `scope_for()` puts
   `identity_version` inside every evidence scope, so a reformulation demotes a
   product *by construction*: evidence scoped to `v1` simply stops covering
   `v2`. Nobody has to remember to revoke anything.

Two narrower refusals come straight from CS-017 §5. A similar flow fingerprint
does not prove chemical identity, so `identity.resolved_by == "FLOW_FINGERPRINT"`
never resolves identity. And validation is per application class: a product
validated for `MOISTURISE` is not thereby validated for `FACIAL_SPF`, which
additionally requires `HUMAN` and `REG_CLAIM` evidence, because a protection
factor is a regulated outcome and not a deposition.

## `dock_preparation.py` — a reservoir is an object somebody can swap

`observe_reservoirs(previous, current)` compares the dock between preparations
and **derives** invalidation events. Every event it emits is a member of the
existing `INVALIDATION_EVENTS` set, so `apply_observed_events` hands them
straight to `invalidate` rather than inventing a second notion of staleness.

Detected: SKU, market, lot, fill-epoch, identity-version and binding changes;
slot moves; location changes; unreadable identity; and volume that *rose*
without a declared refill, which is a top-up mixing an unproven quantity of new
fluid into old. An unreadable reservoir is never treated as an unchanged one.

`derive_session_doses` is the other place a silent zero could enter. A product
the routine requires and the dock does not hold is `BLOCKED_NOT_PREPARED` with
`quantity_ml: None` — never a dose of zero, and never dropped from the manifest,
because both of those turn a skipped step into a completed one. Unknown
quantities flow through `core_sketch_resources.Bound`, where `unknown × 0`
remains unknown.

`account_inventory` keeps dock bulk and wearable inventory in separate columns
and never sums them. Bulk in the dock is the reason the wearable can be small;
adding it to worn mass would misreport the product, and offering it as session
supply would misreport the session.

Carryover follows CS-017's own list of investigation classes.
`required_carryover_classes` returns only what a given routine actually owes —
a PM routine with no leave-on stage does not owe the moisturiser-to-SPF pair —
and `assess_carryover` holds one line absolutely: residue of unknown origin is
never clean, because there is no ordered pair to run a carryover test on.

## `routine_schedule.py` — the routine is a record, not a run-time choice

A routine carries an id and a revision, and may not carry substitution rules: a
routine that can silently become a different routine at run time defeats the
revision it is versioned by.

**Sun protection** gets its own handling throughout. It is scheduled in the
morning, never twice, never satisfied by any member of
`FORBIDDEN_SPF_SUBSTITUTES` — a moisturiser with an SPF claim on its carton, a
leave-on containing a UV filter, an extended moisturise stage, yesterday's
residual film, or an AI judgement that protection is adequate.

**A reduced routine is a different routine.** `resolve_session` gives it its own
`session_plan_digest` and sets `completes_scheduled_routine: False`. Per CS-016
§4.4 a permissible reduced routine is a new eligible session, and reporting it
as the scheduled routine finishing is the exact failure the promise forbids.

**Normal configured use is phone-, cloud- and internet-independent.**
`assess_offline_execution` accepts `network_reachable` so that no caller can
claim the question was never considered, and then excludes it from every
blocker. A reachable network never substitutes for missing local state, an
unreachable one never unreadies a properly prepared device, and a residency
entry marked `resolved_from: NETWORK_AT_RUN_TIME` fails the routine outright.

`derive_presented_state` collapses the gates into the six honest CS-016 §4.4
states. Ordering matters: `SAFETY_HOLD` outranks everything, and a device with
real blockers is `NOT_READY` rather than the softer `NEEDS_ATTENTION`.

## What remains UNKNOWN or BLOCKED

These modules judge **declared records for internal consistency**. They do not
establish any of the following, and no passing test here should be read as
having done so:

- No real product has been characterised, and no dose window is a measured dose.
- No carryover result exists; the contracts only say which are owed and unproved.
- No SPF validation exists. The contract states what SPF evidence must include.
- Reservoir identity is a declared field. Physical identity sensing is hardware
  this lane does not own and has not specified.
- Flow-fingerprint tolerances are caller-supplied. No tolerance here is derived
  from a measured product.
- Dock bulk preservation is unproved. CS-017 §5 warns that a retail package may
  be doing containment, light and air work for a formulation; decanting into
  dock bulk does not inherit that, and nothing here claims chemical preservation.

## Tests

`tests/test_routine_product_intelligence.py` (97 tests) is written from the
attacker's side. The question is never whether the happy path works but whether
the system can be made to report that a step happened when it did not.

The guards were mutation-tested: removing the promoter check, the SKU-change
detection, the unknown-dose protection, the SPF-context rule, the reduced-routine
honesty, the network exclusion, or the identity-version evidence binding each
causes exactly the test that claims to defend it to fail.
