# MASCK ONE Five-Lane Execution Plan

Status: **product-wide execution routing; not engineering authority**  
Date: 2026-09-10  
Companion sources: `docs/CORE_SKETCH_V1.md`, `docs/CORE_SKETCH_EXECUTION_BACKLOG.md`, `docs/PRODUCT_CONCEPT.md`

## Purpose

The previous five top-level work lanes were organised around local subsystems: treatment/massage, HMI, waste cartridge, retention/quick release, and whole-product/Fusion freeze. That structure was appropriate for the earlier cleanser/treatment-mask definition, but it is no longer the best decomposition for the full-routine Masck One.

The new product hierarchy is COMPLETE FACIAL ROUTINE first, then cleaning, treatment, leave-on application and protection. The five top-level missions therefore move upward to product-level outcomes. Existing owner branches/PRs remain valuable and should be reused as subordinate packages; this plan does not authorize parallel replacement architectures.

## Lane 1/5 — Complete-Routine Facial Delivery and Interface

**Priority:** P0 existential

**Mission**
Prove and define the on-face sequence that makes the core promise possible: CLEAN -> RINSE/RECOVER -> optional TREAT -> LEAVE-ON 1..N -> MOISTURISE -> facial SPF when scheduled/validated -> SETTLE -> NON-WIPING RELEASE.

**Owns**
- reduced cheek/full-routine proof rig;
- facial contact vs leave-on application states;
- cleanser-to-leave-on transition;
- representative serum/lotion/cream application families;
- final-film survival through release;
- cross-contamination and residual cleanser boundaries;
- coverage continuity around protected anatomy;
- post-removal face condition target;
- facial-SPF deposition as a special validation-gated stage;
- integration of existing treatment/massage work only where it supports the complete routine.

**Absorbs previous lane**
Old treatment/massage convergence becomes a subordinate package here. Do not discard accepted treatment evidence; reconcile it with the new routine state machine.

**Must not own**
Dock bulk storage, app/database architecture, exterior styling, or whole-product release authority.

**First closure objective**
An off-face inert-surrogate evidence plan for the reduced sequence, with required-region, carryover, spatial-film, removal-loss and uncertainty criteria declared before testing. CS-015/018 also map whole-face support shadows; reduced-region success is not a whole-face or human-use pass.

## Lane 2/5 — Dock, Product Loading, Session Preparation and Hygiene

**Priority:** P0/P1 system enabler

**Mission**
Make many skincare products practical without putting many full reservoirs on the face. The dock owns bulk storage, recognition workflow, product changeover, preparation of isolated session doses, waste/service handling, charging and visible cleanliness confidence.

**Owns**
- bulk product reservoir UX;
- scan/identify/assign/load/confirm flow;
- mistake-proof product slot interaction;
- product changeover and reformulation handling at the physical-service level;
- session-dose preparation and handoff concept;
- waste concealment and service choreography;
- dock cleaning/service visibility;
- dock footprint, presence, nighttime behaviour and acoustic targets;
- pickup/return choreography;
- cable concealment and countertop/bedside presence;
- future travel-dock architectural allowance without making V1 depend on it.

**Absorbs previous lane**
Old waste-cartridge/premium blind-service work becomes a subordinate package here. Preserve the mature cartridge architecture and evidence, then integrate it into the new dock/session-preparation ownership loop.

**Must not own**
AI safety decisions, face application physics, final shell form, or treatment efficacy claims.

**First closure objective**
A complete ownership-loop and product-preservation contract from associating an identified product with a qualified storage interface through preparation, return, service and next-use readiness. Bulk storage does not assume universal pouring/decanting. CS-017 and the physical CS-016 preparation receipt are required.

## Lane 3/5 — Wearable Human Factors, Industrial Design and Sensory Quality

**Priority:** P0/P1

**Mission**
Make Masck One feel like one calm, premium personal-care object that can actually be worn while the user does something else. Protect visual identity, fit, vision, comfort, weight/CG, retention, HMI and all sensory interactions as one experience.

**Owns**
- front/temple/underside/rear visual hierarchy;
- perceived thinness and master surface;
- eye-opening, nose, cheek, mouth and lower-face transitions;
- size-family decision and first-10-seconds placement UX;
- sightlines/peripheral vision and ordinary activity envelope;
- hair, ears, glasses, facial-hair and accessory interaction;
- retention experience and quick-release UX;
- mass/CG/torque distribution targets as human-factors constraints;
- primary-control position, tactile character and discoverability;
- full light/haptic/sound grammar;
- CMF/material/surface-touch targets;
- seam choreography, hygiene visibility and graceful ageing;
- post-removal pressure-imprint target.

**Absorbs previous lanes**
Old HMI and retention/quick-release work become subordinate packages here. Reuse their owner lineages and accepted evidence. Do not restart those mechanisms from scratch merely because the mission is broader.

**Must not own**
Product-database semantics, detailed dock fluid architecture, or clinical/efficacy claims.

**First closure objective**
One coherent worn-state product specification and human-factors envelope that all packaging/CAD work must fit inside, including sightlines, fit/sizing hypothesis, CG/mass targets, control feel, sensory grammar and no-feature rules.

## Lane 4/5 — Routine OS, Product Intelligence and Offline UX

**Priority:** P0/P1

**Mission**
Define the intelligence that lets Masck execute the user's own products safely and predictably while keeping normal operation independent of phone/cloud/AI availability.

**Owns**
- canonical routine state model shared by mask/dock/app;
- AM/PM/day-of-week schedules;
- alternate-night routines and validated interval/incompatibility rules;
- temporary one-day overrides, quick routine and skip-stage behaviour;
- product identity using barcode/QR/OCR/search/ingredient confirmation;
- SKU/market/formulation-version model;
- KNOWN / CHARACTERISED / VALIDATED / RESTRICTED internal trust ladder;
- unknown-product onboarding and conservative fallback behaviour;
- community-discovery versus MASCK-verification distinction;
- product application profiles;
- bounded AI assistance above deterministic safety/application limits;
- offline default-routine storage and physical-button behaviour;
- privacy, accessibility and calm failure-state copy;
- depletion/readiness logic and user-facing routine confidence.

**Absorbs previous work**
None of the old five lanes maps cleanly to this mission; this is a genuinely new top-level lane created by the full-routine concept.

**Must not own**
Detailed pump/valve mechanics, optical hardware design, or changing protected-anatomy engineering authority.

**First closure objective**
A versioned conceptual data/state contract showing exactly how one identified product becomes a bounded application profile, how routines are scheduled and overridden, how unknown products fail safely, and how the mask can execute the currently eligible prepared session with no network or phone. The last prepared/default routine is not executable when its physical contents or validity have changed.

## Lane 5/5 — Treatment Stack and Whole-Product Integration Conductor

**Priority:** P0 integration

**Mission**
Keep one product truth while integrating cleaning, massage, WARM/COOL, optical treatment, leave-on application, SPF, dock preparation, dry-side packaging, power, service and the digital state model. This lane coordinates sequencing and integration conflicts. It cannot overrule Lane 1 application/film evidence, Lane 3 protected fit/release constraints or qualified physical-validation gates. It does not redesign healthy owner subsystems.

**Owns**
- product-wide dependency graph and integration order;
- whole-routine feature hierarchy;
- treatment-modality selection and sequencing;
- red/NIR/deep-NIR optical benchmark research and original MASCK optical UX target;
- deliberate WARM/COOL role versus incidental heat prohibition;
- deciding when a treatment modality is optional, scheduled or excluded;
- product-wide mass/volume/power/service budgets at concept level;
- source/authority/evidence reconciliation across owner lanes;
- interface contracts between Lane 1 facial delivery, Lane 2 dock, Lane 3 wearable, and Lane 4 Routine OS;
- concept-to-engineering handoff and eventual Fusion/product freeze;
- proof matrix for what remains DIGITAL/BENCH/HUMAN/REG/SUPPLIER gated;
- explicit rejection of generic competitor feature creep.

**Absorbs previous lane**
Old whole-product conductor/Fusion freeze becomes this lane, but the mission changes from 'freeze the current cleanser-centric product' to 'integrate the new complete-routine architecture without losing accepted engineering'. Existing thermal, dry-side and optical/treatment packages route through this conductor as needed.

**Must not own**
Day-to-day implementation of every subsystem. It should integrate and arbitrate, not create duplicate local owner branches.

**First closure objective**
A coherent whole-product integration map showing that every Core Sketch feature has exactly one owner lane, all P0 dependencies are ordered, existing PRs are mapped rather than duplicated, and no old subsystem assumption silently blocks the complete-routine promise.

## Rescheduling of the old five tasks

| Old task | New top-level destination | Treatment of existing work |
| --- | --- | --- |
| Treatment / massage convergence | Lane 1, with treatment modality integration reviewed by Lane 5 | Preserve accepted geometry/evidence; adapt to complete-routine contact-state transitions |
| Primary control / HMI | Lane 3 | Preserve owner lineage; refine within whole worn-state sensory grammar |
| Waste cartridge / premium blind service | Lane 2 | Preserve owner lineage; integrate with dock-led product/waste/service loop |
| Retention / quick release | Lane 3 | Preserve owner lineage; integrate with fit, hair/ear/accessory and non-wiping removal requirements |
| Whole-product conductor / Fusion freeze | Lane 5 | Keep conductor role; postpone final freeze until new P0 complete-routine architecture is reconciled |

**New Lane 4 is created by the concept pivot.** Its work should not be forced into an old mechanical owner lane.

## Concurrency rule

The five lanes may run concurrently only where their dependencies permit. Lane 1 existential evidence and Lane 3 human-factors envelopes should constrain later geometry rather than be papered over by Lane 5. Lane 2 and Lane 4 can progress strongly in parallel at the specification/data-contract level. Lane 5 must continuously reconcile interfaces and prevent duplicate architecture branches.

## Freeze rule

Do not perform a final whole-product/Fusion freeze merely because the old five subsystem lanes are green. A new freeze requires, at minimum:

1. the complete-routine state machine and ownership split are stable;
2. required-region, carryover and non-wiping feasibility have scoped evidence, including the whole-face stationary-contact/support-transition problem;
3. the multi-product dock/session-dose architecture includes preservation, hold-history, changeover and prepared-session validity;
4. the fit/sizing/worn-state envelope is selected;
5. Routine OS/product-identity contracts exist;
6. treatment/optical/thermal roles are reconciled;
7. all remaining unsupported capabilities remain explicitly evidence-gated;
8. required G0..G5 outcomes and joint mass/CG/torque/fault/service budgets are satisfied for the selected scope. A blocked required stage cannot be hidden by labeling the entire product frozen.

## One producer per shared artifact

This table resolves the previous ambiguous joint ownership. A consumer supplies acceptance criteria and can reject an interface; it does not fork the producer's source. Lane numbers route work, not grant authority to edit every subordinate branch.

| Shared artifact | Writing/geometry producer | Required consumers and acceptance |
|---|---|---|
| Required-region and all-contact phase map | Lane 1, CS-015/018 | Lane 3 supplies fit/support geometry; Lane 5 checks whole-product phase consistency |
| Retention, support transfer and continuous normal/emergency removal geometry | Lane 3 through existing retention owner | Lane 1 supplies film/coverage criteria; Lane 5 integrates exact geometry; emergency release remains independent |
| Existing massage carrier and face-side delivery geometry | Lane 1 through the current treatment/fluid producers | Lane 3 package/fit; Lane 5 treatment budgets; no second carrier or fluid truth |
| Bulk-to-session physical graph, cassette and preparation receipt | Lane 2 | Lane 1 face-side interface; Lane 3 package acceptance; Lane 4 receipt schema/eligibility; Lane 5 resource totals |
| Product-profile, prepared-session and routine state contract | Lane 4 | Lane 1 application evidence; Lane 2 actual contents/service; Lane 3 user interaction; Lane 5 capability matrix |
| Thermal/optical package and per-phase treatment budget | Lane 5 through current thermal and any explicitly activated optical owner | Lane 1 contact/film constraints; Lane 2 reset/service; Lane 3 package/fit; Lane 4 eligible sequencing |
| Whole-product mass/CG/power ledger and canonical component registry | Lane 5 through existing ledger/integration producers | Lane 3 owns human-factors acceptance; all lanes supply exact components and state-dependent resources |
| Wearable CMF, controls and sensory language | Lane 3 through existing exterior/HMI/brand producers | Lane 2 dock family consistency; Lane 4 readiness/failure semantics; no decorative activity cues |

New Lane 4 and the new required-region/product-preservation work need bounded owner activation; no active implementation owner was identified merely from their appearance in concept docs. Until activated, their implementation status remains unassigned/PROVE, not silently delegated to a mechanical branch.

## Work admission and existing owners

Use G0..G5 in the backlog rather than the order of document sections. Existing treatment/HMI/cartridge/retention/dry-side/frame owners may finish bounded defects and exact evidence. Reuse unchanged accepted inputs; do not rerun a full CAD suite for a concept-only edit.

Before expanding an owner, require its smallest new interface input: Lane 1 contact domain for delivery/retention changes, Lane 2 physical receipt for Routine OS, or the joint resource budget for optional modalities. The live owner/evidence snapshot is in [repository mapping](CORE_SKETCH_REPO_MAPPING.md). No current open conductor PR was observed; released registry/provenance work is the starting point, not a still-active historical PR.
