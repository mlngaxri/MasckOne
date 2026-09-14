# MASCK ONE Core Sketch Agent Guide

Status: **working instructions for future repository agents**

## Read before acting

For any task that can change the product concept, UX, industrial design, feature set, dock, skincare compatibility, treatment sequencing or physical interaction:

1. `docs/CORE_SKETCH_TRIAGE_INDEX.md`
2. `docs/CORE_SKETCH_V1.md`
3. `docs/CORE_SKETCH_EXECUTION_BACKLOG.md`
4. subsystem-specific engineering docs and live authority
5. live GitHub owner PR/branch state

For historical exploration only:

- `docs/research/CORE_SKETCH_DEEP_RESEARCH_2026-09-10.md`

Do not revive archived ideas merely because they sound sophisticated.

## Broad prompts

When told “continue,” “perfect Masck,” “triage everything,” “do the next most important thing,” or similar:

- do not invent a new feature list;
- select the highest-priority backlog item whose dependencies are satisfied;
- reuse a current owner lane where one exists;
- perform material work and produce evidence;
- update the backlog only if evidence/state changes.

## Product-change prompts

When a prompt proposes a new feature:

1. classify whether it supports Tier A, B or C product intent;
2. check the explicit rejected-feature register;
3. determine what user problem it solves inside the complete-routine journey;
4. identify mass/CG, hygiene, airway, eye, leave-on, dock, service, privacy and offline consequences;
5. add/revise a backlog item before implementation if the feature is accepted;
6. do not let a local subsystem PR redefine the entire product.

## Evidence language

Use these exact concepts consistently:

- **concept target** — desired behavior/design not yet proven;
- **digitally verified** — source/CAD/simulation evidence only;
- **physical validation required** — real-world behavior remains unproven;
- **validated** — only when the relevant required evidence actually exists.

Never write “production ready,” “clinically proven,” “buttery smooth,” “comfortable,” “uniform SPF,” “safe optical exposure,” “self-cleaning,” or similar as achieved facts without the matching evidence.

## Whole-routine invariant

Always ask:

> If this change succeeds, can the user still put Masck on, run their supported routine, remove it, and be finished without touching the face again?

If not, the change conflicts with the current product definition unless explicitly approved as a concept change.

## User-product invariant

Always ask:

> Does this make Masck better at executing the user’s skincare, or does it quietly force the user to change to Masck chemistry?

The latter is rejected by default.

## Calm-object invariant

Exterior sophistication should come from proportion, surface quality, controlled interfaces and hidden function, not visible technical decoration.

Reject default additions of:

- black bezels;
- vent patterns;
- RGB lighting;
- exposed screws/plumbing;
- aggressive eye geometry;
- headset-like straps;
- fake metallic accents;
- sci-fi panel seams.

## Tactile invariant

For every user-actuated, inserted, removed, latched, docked or released element, target:

- near-zero perceptible free play;
- intended motion only;
- smooth guidance;
- deliberate progressive resistance;
- self-centering where useful;
- one clear state transition;
- authoritative seating;
- controlled unloading/return;
- no rattle, scrape, chatter, mush, uncontrolled snap, spring twang, hollow impact or cheap overtravel.

This is an experience target until physically measured/tested.

## Do not over-engineer the core sketch

The core sketch defines what Masck is and how it should feel. Detailed bearings, fasteners, pump topology, PCB routing, actuator internals, tolerances and manufacturing methods belong in the owning subsystem work after the product requirements are clear.
