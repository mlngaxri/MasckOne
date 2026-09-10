# Verifying contributions from multiple agents

This repository is edited concurrently by several autonomous agents and, now, by
more than one toolchain. That is a fast way to build and a very easy way to lose
rigour, because **the cheapest route past a failing gate is almost always to
soften the gate rather than fix the design.**

`docs/ENGINEERING_GOVERNANCE.md` forbids that. This document describes the
machinery that makes it fail.

## Where verification lives

Verification lives **in the repository**, not in any agent's session.

That is a deliberate choice. An agent-side reviewer — scheduled, polling, or
watching — only verifies the contributions it happens to observe, only while
that session is alive, only with whatever repository access it holds, and only
for the toolchain it was set up to watch. A check committed to the repository
runs on every push and every pull request, for every contributor, human or
otherwise, forever, with no coordination between them.

If a partner's agent, a contractor, or a future toolchain edits this repository,
these gates apply to it without anyone configuring anything.

## The fast gate

`.github/workflows/ci.yml` runs an `integrity-ratchets` job **before** the
engineering suite. It needs no CAD toolchain — every guard reads source, tests
and the authority as text — and completes in about **1.5 seconds**. A weakening
change is rejected before the six-minute engineering suite starts, and reports
as its own named check rather than one failure among hundreds.

## What it guards

Each guard is a **ratchet**. It pins where the repository stands and permits
movement in the safe direction only. Adding tests, adding evidence gates and
tightening tolerances are all free.

| Guard | Fails when |
|---|---|
| `test_test_function_count_does_not_fall` | any test function is deleted |
| `test_failures_are_not_hidden_behind_skips` | a `skip`/`xfail` marker is added |
| `test_every_skip_states_a_reason` | a skip carries no reason |
| `test_evidence_gate_markers_do_not_fall` | any `VALIDATION_GATED` / `BLOCKED` / `FROZEN_*` / `NOT_*_EVIDENCE` marker is removed |
| `test_planar_development_surface_can_never_be_anatomical_evidence` | the flat Z=0 surface becomes eligible as fit evidence |
| `test_named_tolerances_do_not_loosen` | a named CAD or STEP tolerance grows, or disappears |
| `test_frozen_authority_statuses_are_still_frozen` | a `FROZEN_*` status is downgraded |
| `test_wearer_safety_limits_only_move_in_the_safe_direction` | airway openings shrink, escape time grows, or head load rises |
| `test_protected_facial_apertures_are_not_shrunk_for_packaging` | eye/mouth apertures shrink or the misregistration screen weakens |

Alongside them the same job runs `test_pinned_commits.py` (no new unverifiable
provenance) and `test_program_position.py` (README, roadmap and build report
cannot drift apart).

Every guard has been verified to fire on a **single-unit** regression: one
deleted test function, one removed evidence gate, one added skip, one loosened
tolerance, one relaxed safety limit.

## Raising a pinned number

Pinned numbers are not sacred, and raising one is not forbidden. Doing it
*silently* is.

To retire a genuinely obsolete test, lower `MIN_TEST_FUNCTIONS` in the same
commit and say why in the message. To close an evidence gate, cite the evidence
that closed it. To widen a tolerance, demonstrate the kernel artifact
rigorously — and prefer replacing the check with a better invariant over
enlarging the number, per `ENGINEERING_GOVERNANCE.md`.

The diff that changes a pin is the conversation. That is the entire mechanism.

## What this does not do

These guards judge whether the repository's own safeguards are still standing.
They do not judge design, and they are not a review.

They cannot tell you that a new mechanism is manufacturable, that a load path
closes, that a tolerance stack survives at MMC and LMC, or that any of it is
physically valid. A green `integrity-ratchets` check means only that nothing was
quietly weakened — which is exactly the failure mode that concurrent automated
contribution produces, and exactly the one that is hardest to spot by reading a
diff.
