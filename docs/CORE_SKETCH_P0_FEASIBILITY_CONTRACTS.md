# MASCK ONE P0 Whole-Routine Feasibility Contracts

Status: **Core Sketch execution contract; not engineering authority**  
Canonical backlog contracts: **CS-015, CS-016, CS-017, CS-018**  
Companion machine contract: `docs/contracts/core_sketch_p0_convergence_v1.json`  
Bench program: `docs/CORE_SKETCH_REDUCED_REGION_PROOF_PACKAGE.md`

This file does not create a second set of Core Sketch IDs. It makes the existing convergence contracts CS-015 through CS-018 explicit enough for future software, CAD, dock and validation work to consume consistently.

Live engineering authority and accepted evidence always outrank this concept layer on claims of what physically exists or works.

## 1. Product-level completion invariant

A supported routine may report `COMPLETE` only when all of the following are simultaneously true:

1. every mandatory stage in the exact prepared session completed;
2. every facial region required by every mandatory stage is complete or was deliberately excluded by a versioned, justified product/claim boundary;
3. no required region is unresolved, unreachable, unsupported or left uncertain by interruption;
4. every mandatory product is permitted in the exact application context;
5. product identity, preparation, carryover/service and resource state remain valid;
6. every required settle condition completed;
7. normal release preserved the required final leave-on state.

A cycle counter, pump command, aggregate coverage number, green subsystem CI result or app animation cannot substitute for this predicate.

Emergency/unpowered release always outranks skincare-film preservation. An emergency release may yield `INTERRUPTED` or `PARTIAL`; it must never be delayed to preserve a cosmetic layer.

---

# 2. CS-015: required-region completion

## 2.1 Stage-by-region model

For routine `R` and mandatory stage `s`, define the stage's required facial region set `Z(R,s)`. Each region has one completion state:

- `PENDING`
- `IN_PROGRESS`
- `COMPLETE`
- `EXCLUDED_WITH_REASON`
- `UNREACHABLE`
- `UNSUPPORTED`
- `INTERRUPTED`
- `UNKNOWN`

`EXCLUDED_WITH_REASON` is not a loophole. It is allowed only when the exclusion is intentional, versioned, compatible with the routine's public promise and not created merely because the hardware failed to reach the region.

Any required region in `UNREACHABLE`, `UNSUPPORTED`, `INTERRUPTED` or `UNKNOWN` blocks completion of that mandatory stage.

## 2.2 Initial conceptual facial regions

Until registered 3D anatomy supports a finer map, use stable conceptual regions rather than pretending to have clinical spatial precision:

- forehead left / centre / right;
- temple left / right when included by the routine claim;
- upper cheek left / right;
- mid cheek left / right;
- lower cheek left / right;
- nasal sidewall left / right where permitted;
- perioral skin where permitted;
- chin.

Protected eye apertures, nostril airways and mouth aperture are protected domains, not skin regions that must receive a leave-on product.

Periorbital, nasal-crease and lip-adjacent regions remain separately evidence-gated rather than being silently absorbed into broad cheek labels.

## 2.3 Stage rules

**CLEAN**
- legacy aggregate coverage gates remain valid for their original engineering scope;
- they do not prove complete-routine region coverage;
- a persistent untouched required patch blocks stage completion.

**RINSE / RECOVER**
- every cleanser-exposed required region must satisfy the eventual rinse/recovery criterion;
- waste-pump operation alone does not prove cleanser removal;
- free-liquid residual, residual cleanser concentration and dilution of the next layer are separate observables.

**TREAT / OPTICAL / THERMAL / MASSAGE**
- optional modalities define explicit target regions;
- omission of a genuinely optional modality does not invalidate a routine;
- a treatment explicitly required by the prepared routine cannot be silently skipped and still report that unchanged routine complete.

**LEAVE-ON 1..N / MOISTURISE**
- every required region must receive its required application state;
- previously occluded regions require a later access/application strategy;
- metered quantity, deposited quantity and spatial film are separate observables.

**FACIAL SPF**
- SPF is a special claims-quality application stage;
- dispensed mass or visible film cannot by themselves establish labeled protection;
- any completion claim is limited to the exact facial regions, product and application method actually validated;
- ears, neck, scalp and body remain outside the facial-mask coverage claim;
- direct aerosol spraying onto the face is not a selected default route.

**SETTLE**
- required settling is product/application driven rather than chosen to make a round marketing duration;
- interrupted required settling blocks downstream release-ready status.

**RELEASE**
- release is part of completion;
- a leave-on stage can be invalidated if normal removal materially wipes a required region.

---

# 3. CS-018: all-contact support and film-preserving transition

## 3.1 Every face-facing object is an occlusion participant

Audit at minimum:

- perimeter seals;
- support pads;
- facial retention/reaction interfaces;
- treatment/massage islands;
- stationary treatment annuli;
- thermal contact surfaces;
- face-adjacent optical carriers;
- fluid-distribution surfaces;
- fit/alignment contacts;
- any bridge, rib or support capable of covering required skin.

Retracting massage islands alone does not solve the complete-routine problem if another stationary element still shadows skin that requires a final layer.

## 3.2 Phase declaration

For every contact class declare its state across:

`PLACEMENT -> CLEAN -> RINSE_RECOVER -> TREAT -> LEAVE_ON -> SETTLE -> RELEASE`

Allowed state vocabulary:

- `CONTACTING`
- `NEAR_SKIN_NONCONTACT`
- `RETRACTED_OR_CLEARED`
- `TRANSITIONING`
- `NOT_PRESENT`
- `UNKNOWN`

Also record which required regions it can occlude and which structural/support function it performs.

## 3.3 Occlusion exit rule

If a structure occludes skin required by a downstream leave-on stage, before that stage can complete at least one of these must be demonstrated:

1. the structure clears the region;
2. a secondary application pass treats that region after clearing;
3. an independently validated application route reaches the region while support remains present;
4. the region is a justified, explicit product/claim exclusion.

Persistent unresolved occlusion is a P0 blocker.

## 3.4 Non-wiping transition

Once a region has received its final required leave-on film, later normal device motion must not drag a broad face-facing surface across it unless BENCH evidence shows the film remains within the selected acceptance criterion.

The Core Sketch freezes the functional states, not a mechanism:

- contact/treatment state;
- application-clear state;
- settle/release-ready state;
- non-wiping normal-release state.

Possible engineering mechanisms remain open until evidence selects them.

---

# 4. CS-016: prepared-session validity and interruption

## 4.1 READY is derived, not remembered

`READY` means:

> If the user presses the primary physical control now, the exact prepared session is eligible to execute using the locally available validated state.

A previous `READY` flag cannot survive a material state change without re-evaluation.

## 4.2 Every prepared session binds

- unique session ID;
- routine ID and version;
- scheduled context where relevant;
- deliberate temporary overrides;
- mandatory and optional stages;
- exact product identity per required stage;
- market/formulation/version when known;
- product evidence state;
- application-profile version;
- physical slot/reservoir association;
- preparation receipt;
- prepared quantity/state;
- preparation time and hold-history fields when relevant;
- product-change/reformulation state;
- changeover/contamination state;
- water/rinse sufficiency;
- waste capacity;
- battery/energy sufficiency;
- thermal readiness for required thermal stages;
- required service/cleaning completion;
- active fault state;
- local offline data required to execute safely.

## 4.3 Invalidation events

Re-evaluate or invalidate the prepared session on:

- routine change affecting the prepared session;
- required product swap or slot reassignment;
- wrong-product suspicion;
- reformulation requiring re-characterisation;
- prepared-dose age/hold-history limit exceeded;
- interrupted preparation or required service;
- contamination/changeover uncertainty;
- insufficient required water/product quantity;
- insufficient waste capacity;
- insufficient energy;
- required thermal reset not ready;
- fault affecting a mandatory stage;
- profile/safety-rule revision that invalidates the old preparation;
- loss of prepared-dose identity.

Network loss by itself does **not** invalidate an otherwise locally eligible session.

## 4.4 Honest degraded states

Use distinct concepts:

- `READY`
- `PREPARING`
- `NEEDS_ATTENTION`
- `PARTIAL_ROUTINE_AVAILABLE`
- `NOT_READY`
- `SAFETY_HOLD`

If a user chooses a permissible reduced/changed routine, it becomes a new eligible session. Do not describe it as completion of the unchanged scheduled routine.

For interruption, preserve what is known and what is uncertain. A software command log cannot prove an uncertain physical dose was delivered exactly once.

---

# 5. CS-017 and product-integrity contract

Keep five product truths separate:

1. `IDENTITY`: what exact product is loaded;
2. `PHYSICAL_CHARACTERISATION`: how it behaves through the system;
3. `COMPATIBILITY`: whether product/material/storage interactions are supported;
4. `CONTAMINATION_STATE`: what unwanted material may be present;
5. `APPLICATION_VALIDATION`: whether the selected application method has enough evidence for its claimed use.

A product that can be pumped is not automatically compatible or validated.

Internal evidence states remain:

- `KNOWN`
- `CHARACTERISED`
- `VALIDATED`
- `RESTRICTED_OR_UNSUPPORTED`

Community data may accelerate identity discovery and characterisation. It may not automatically promote a safety/claims-critical product to `VALIDATED`.

Product preservation must consider what the retail package may be doing for the formulation: containment, light exposure, air exposure, compatible contact material and storage history. Dock-side bulk storage does not automatically authorize universal open decanting.

Carryover must be investigated separately across:

- cleanser -> rinse;
- rinse -> first leave-on;
- leave-on A -> leave-on B;
- leave-on -> moisturiser;
- moisturiser -> SPF where both are used;
- product changeover;
- dock/service-fluid residues;
- shared downstream interfaces and returns.

An apparently empty line or executed purge command is not proof of acceptable carryover.

If observed physical behavior strongly contradicts the expected product profile, automated preparation/use should stop and request product confirmation. A similar flow fingerprint does not prove chemical identity.

---

# 6. Complete-routine resource envelope

Lane 5 owns one whole-session ledger. Lane 2, Lane 1, Lane 3 and Lane 4 supply the physical/resource inputs.

Track at minimum:

- `V_water`
- `V_cleanser`
- `V_leaveon[i]`
- `V_moist`
- `V_spf`
- `V_purge`
- `V_recovered`
- `V_residual`
- total session fluid mass
- dry wearable mass
- loaded wearable mass
- loaded CG
- wearer pitch torque
- electrical energy
- thermal state/energy requirement
- complete routine duration including required settle time
- dock bulk-slot demand
- isolated session-dose storage volume
- waste-capacity demand
- fault-releasable fluid inventory.

Required planning cases:

1. `MINIMUM_SUPPORTED`
2. `NORMAL_PM`
3. `DEMANDING_AM`

At the current released authority observed on 2026-09-11, the relevant constraints include dry target <=215 g, loaded absolute max 255 g, CG-Z max **27.9 mm**, and pitch torque <=0.070 N*m. The authority explicitly tightened CG-Z from 30.0 mm because 255 g at 30 mm would not close the torque limit. Refresh live authority before any engineering action; these values in a concept document are a dated reconciliation snapshot, not a substitute for authority.

Known cleanser-era quantities such as the 3.2 mL face-water, 0.60 mL cleanser and 0.80 mL post-flush values remain scoped to the released clean-cycle baseline. They are not evidence that an expanded complete routine fits the wearable or that extra leave-on/changeover volume is free.

Unknown serum/moisturiser/SPF doses remain unknown or bounded research inputs until the exact product/application owner supplies evidence. Do not invent convenient values merely to make the budget close.

---

# 7. Shared-interface writing ownership

To prevent competing truths:

| Shared interface | Canonical writing owner | Key consumers |
| --- | --- | --- |
| CS-015 required-region completion | Lane 1 | Lanes 4, 5 |
| CS-018 contact/occlusion requirement map | Lane 1 | Lanes 3, 5 |
| CS-016 prepared-session validity | Lane 4 | Lanes 1, 2, 5 |
| complete-routine resource envelope | Lane 5 | Lanes 1, 2, 3, 4 |
| product identity/evidence semantics | Lane 4 | Lanes 1, 2, 5 |
| CS-017 physical product preservation/changeover | Lane 2 | Lanes 1, 4, 5 |
| normal non-wiping release acceptance | Lane 3, consuming Lane 1 film evidence | Lanes 1, 5 |

The consumer may submit evidence or interface-change requests. It should not maintain a second canonical contract.

---

# 8. Fail-closed invariants

The machine-readable companion contract and tests must preserve these rules:

- blocking required-region state prevents stage completion;
- invalid prepared session prevents READY;
- unsupported mandatory product prevents routine COMPLETE;
- unresolved required contact shadow prevents final stage completion;
- documentation/CAD/simulation cannot promote physical validation;
- green subsystem CI cannot close a P0 BENCH/HUMAN/REG/CLAIM gate;
- each shared interface has one canonical writing owner;
- emergency release cannot be weakened to preserve a cosmetic film;
- SPF claim cannot exceed the exact validated facial/product/application envelope;
- engineering work must refresh current authority rather than trusting this dated concept snapshot.

---

# 9. Immediate P0 execution order

1. Maintain CS-015 through CS-018 as the canonical shared contracts.
2. Execute the reduced-region proof package for CLEAN -> RINSE/RECOVER -> thin leave-on -> thicker leave-on -> final leave-on -> SETTLE -> non-wiping release.
3. Define repeatable coverage, carryover and final-film-survival measurements before counting attractive demonstrations as evidence.
4. Build the all-contact phase/occlusion map against current treatment, seal, thermal, fluid and retention concepts.
5. Close the first whole-routine resource ledger for minimum, normal PM and demanding AM scenarios.
6. Establish a representative third-party product-family envelope and product-preservation/changeover evidence plan.
7. Expand only successful reduced-region behavior toward whole-face fit/coverage.
8. Keep facial SPF on its own higher-rigor application and claims path.

---

# 10. Pivot conditions

Escalate to explicit product review when repeated credible architectures cannot resolve one or more of:

- required regions hidden by necessary support/contact structures;
- cleanser-to-leave-on contamination;
- practical thin-fluid boundary control;
- thick-product distribution;
- final-film survival during safe normal release;
- meaningful third-party product compatibility;
- complete-routine mass/CG/torque/resource closure;
- a dock/service burden low enough to preserve the product's time/effort advantage;
- a commercially useful fit/coverage range;
- truthful facial-SPF performance.

One failed prototype is a design result, not an automatic kill. Repeated failure of the locked core promise across credible alternatives is grounds to reconsider the concept rather than quietly redefining an incomplete routine as complete.
