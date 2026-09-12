# Regional plan compiler (Packet M3)

**Status:** non-authoritative concept logic. `human_use_eligible` is `False` on
every result. Nothing here qualifies a policy, measures hardware, or establishes
that cleansing works.

## The question the controller was not asking

The canonical cleansing architecture merged in #155 answers the runtime question
well. `RegionalLedger.permits`, `shared_channel_permitted` and
`SessionLedger.authorize_shared` together decide whether *this* action, *right
now*, is authorized by every region its footprint touches. Budgets are never
averaged and a shared channel is refused the moment any region it reaches stops
consenting.

That check is local, and one failure mode is not local.

Suppose the left cheek still needs cleaning, the forehead is already `COMPLETE`,
and every `CLEAN` action whose footprint reaches the left cheek also reaches the
forehead. Every one of those actions is refused, correctly, by the forehead's
ledger. Run the session anyway and the left cheek never completes — with no
single refusal that explains why. The routine asked for a demand partition the
mechanism cannot execute, and nothing in the repository said so.

`cleansing_scheduler.compile_plan` answers that question before the session
starts, and returns exactly one of:

| Outcome | Meaning |
| --- | --- |
| `PLAN_COMPILED` | a bounded ordered step list exists |
| `HARDWARE_UNEXECUTABLE` | no ordering completes every required region; a witness says why |
| `BLOCKED_UNQUALIFIED` | a policy envelope or session resource is missing |
| `NO_PLAN_WITHIN_BOUND` | the step bound was reached |

## What the compiler consumes

`Action` declares the **whole** affected footprint, not the intended target. An
action that incidentally sweeps a neighbouring region must say so: that
incidental reach is the entire subject of the module. There is no assumption of
one actuator per cell, and a footprint cell belonging to no declared region is
**refused** rather than treated as reaching nothing — not knowing what an action
touches is missing information, and missing information never becomes harmless.

## Selection order

Lexicographic, in the contract's own order. Constraint satisfaction is not a
ranking term because an action that violates a constraint is never a candidate:
progress, then mechanical burden, then chemical exposure, then treating a region
that has already finished this stage, then mechanism complexity, then action id
so two runs on the same input produce the same plan.

Worth stating plainly: the compiler is *good* at avoiding stranding. Given wide
actions and narrow ones, it prefers the wide action while every touched region
still consents, which is exactly what keeps regions finishing together. Three
separate attempts to write a stranding fixture compiled successfully instead,
because the compiler found the ordering that worked. The test that now pins the
behaviour is one where no ordering exists at all.

## The witness

`HARDWARE_UNEXECUTABLE` names the trapped region, the trapped stage, the exact
uncovered cells, and why — distinguishing four different failures, because they
have four different remedies:

- `COMPLETED_REGION_NOT_BYPASSABLE` — a finished region cannot be avoided
- `EXHAUSTED_REGION_NOT_BYPASSABLE` — a region hit its ceiling mid-routine
- `SESSION_RESOURCE_EXHAUSTED` — shared water or cleanser ran out
- `NO_ACTION_REACHES_REGION` — no action of that kind reaches it at all

Reporting an exhausted region as unreachable would be false: actions do reach it,
and something else rejected them. Each witness carries
`minimum_capability_change`, phrased as a capability requirement to hand back to
the owning mechanical lane rather than a hardware change made here.

## What remains UNKNOWN

Footprints are declared inputs. Until Packet L / PR #157 supplies a source-bound
contact and affected-cell capability model, the topology this compiler reasons
over is whatever the caller passed it, and a compiled plan says only that the
demand is reachable under those declared footprints. It is not evidence that any
region was cleaned, that a dose was delivered, or that the mechanism can apply
the ranked burden safely to a person.

## Tests

`tests/test_cleansing_scheduler.py` — 21 hostile tests. Mutation-tested: letting
actions touch finished regions, ignoring per-region ceilings, treating unmapped
footprint cells as harmless, advancing a stage on partial cell coverage, and
proceeding without qualified limits each fail the test that defends them.
