# MASCK ONE P0 Whole-Routine Feasibility Contracts

Status: **Core Sketch product contract; not engineering authority**  
Scope: whole-routine completion, facial-region coverage, contact/occlusion, prepared-session validity, complete-routine resource envelope, product preservation and changeover.  
Evidence boundary: this document defines what future evidence must prove. It does not claim those physical outcomes already exist.

## 1. Why these contracts exist

The expanded Masck One promise cannot be proven by a cycle counter, an average coverage percentage, or a collection of individually green subsystems. A supported routine is complete only if the selected routine, selected products, required facial regions, required resources, contact-state transitions and final release all satisfy the same session-specific contract.

The product-level invariant is:

> A routine may report COMPLETE only when every mandatory stage completed for every facial region required by that routine, no required product or resource is unsupported or invalid, and final release preserves the required end state.

A locally successful cleanser, massage carrier, thermal store, dock service action or app state cannot override this rule.

## 2. Contract A: whole-face routine completion and coverage

### 2.1 Completion is stage-by-region, not one scalar

For each prepared routine `R`, define:

- `S(R)`: ordered stages required by that routine;
- `Z(R,s)`: facial skin regions required for stage `s`;
- `X(R,s,z)`: completion state of region `z` for stage `s`.

Allowed conceptual completion states are:

- `PENDING`
- `IN_PROGRESS`
- `COMPLETE`
- `EXCLUDED_WITH_REASON`
- `UNREACHABLE`
- `UNSUPPORTED`
- `INTERRUPTED`
- `UNKNOWN`

`EXCLUDED_WITH_REASON` is allowed only when exclusion is deliberate, versioned, visible to the routine definition and compatible with the public claim. It must never be used to hide a geometry or application failure.

A mandatory stage may be stage-complete only when every region in `Z(R,s)` is `COMPLETE` or an explicitly allowed `EXCLUDED_WITH_REASON`.

A supported routine may report `COMPLETE` only when:

1. every mandatory stage is stage-complete;
2. no required region is `UNREACHABLE`, `UNSUPPORTED`, `INTERRUPTED` or `UNKNOWN`;
3. every required product is allowed for that stage under the prepared-session validity contract;
4. required settling conditions are met;
5. release completes without invalidating the final leave-on state.

### 2.2 Conceptual facial-region set

Until registered full 3D facial anatomy is available, use a controlled conceptual region set rather than pretending to have clinical anatomical precision. The region set may later be refined or subdivided, but IDs should remain stable or explicitly versioned.

Initial region classes:

- upper forehead left / center / right;
- temple left / right where the mask's supported facial claim includes them;
- upper cheek left / right;
- mid cheek left / right;
- lower cheek left / right;
- nasal sidewall left / right where treatment/application is permitted;
- perioral skin where permitted;
- chin;
- protected eye aperture left / right;
- protected nostril airway left / right;
- protected mouth aperture.

Protected apertures are not treated as skin regions that must receive leave-on product. Their exclusion is a product/safety boundary, not a coverage failure.

Periorbital skin, lip-adjacent skin, nasal crease and other high-sensitivity boundaries must remain separately evidence-gated rather than silently grouped into broad cheek coverage.

### 2.3 Coverage rules by stage

**CLEAN**
- cleaning must reach each routine-required cleanable region;
- aggregate cleansing percentage cannot hide persistent untouched islands;
- protected apertures remain protected;
- if a structural/contact feature blocks a cleanable region, that region requires an alternate cleaning pass or the routine is not complete.

**RINSE / RECOVER**
- every region exposed to cleanser must satisfy the rinse/recovery criterion appropriate to that region;
- cleanser removal and waste recovery must not be inferred solely from pump operation;
- residual-cleanser acceptance remains a physical-validation question.

**TREAT / OPTICAL / THERMAL / MASSAGE**
- optional modalities define their own target-region sets;
- a routine can still be complete when an optional treatment is omitted by design;
- if a treatment is scheduled as mandatory, unavailable target regions block that treatment stage rather than being hidden.

**LEAVE-ON 1..N / MOISTURISE**
- every routine-required region must receive its required final application state;
- distribution must account for regions previously hidden by seals/supports/treatment contacts;
- product presence alone is insufficient: pooled, visibly discontinuous or wiped-away film remains a failed application until a physical metric is selected.

**FACIAL SPF**
- SPF is a special claims-quality stage;
- completion can be asserted only for the validated facial coverage set and the exact supported product/application profile;
- do not infer protection from dispensed volume alone;
- never imply coverage of ears, neck, scalp or body;
- do not use direct aerosol spraying to the face as the default architecture. TGA guidance explicitly warns against spraying aerosol sunscreen directly onto the face due to inhalation risk;
- label instructions and regulatory evidence remain controlling for the exact sunscreen.

**SETTLE**
- settle time is driven by the product/application requirement, not a marketing-friendly round number;
- interrupting a required settle interval prevents the downstream release-ready state.

**RELEASE**
- release is part of routine completion, not an afterthought;
- a completed leave-on stage can be invalidated if release materially wipes or redistributes the final film;
- release therefore has both safety and product-preservation criteria.

## 3. Contract B: contact, occlusion and non-wiping state transition

### 3.1 Core rule

Every face-facing structure is an occlusion participant until proven otherwise.

This includes:

- perimeter seals;
- support pads;
- retention reaction interfaces;
- treatment/massage islands;
- thermal contact surfaces;
- optical carriers close enough to shadow or block application;
- fluid distribution interfaces;
- stationary bridges/ribs/supports near the face;
- any temporary fit/alignment feature that covers skin required later in the routine.

Retracting only moving massage islands is not sufficient if another structure still blocks a required leave-on region.

### 3.2 Required state declaration

For every face-facing contact class, define its state across:

`PLACEMENT -> CLEAN -> RINSE_RECOVER -> TREAT -> LEAVE_ON -> SETTLE -> RELEASE`.

At each phase, record conceptually:

- `CONTACTING`
- `NEAR_SKIN_NONCONTACT`
- `RETRACTED_OR_CLEARED`
- `TRANSITIONING`
- `NOT_PRESENT`

Also record the facial regions that element can occlude.

### 3.3 Occlusion exit rule

If an element occludes a region required for a leave-on stage, one of these must be true:

1. the element stops occluding before that stage is allowed to complete; or
2. that region receives a later secondary application pass after occlusion ends; or
3. an independently validated application path reaches the region while the element remains present; or
4. the region is explicitly excluded from that specific product claim for a justified reason.

Anything else is a P0 completion failure.

### 3.4 Non-wiping rule

From the point a region receives its final required leave-on layer, subsequent device motion must not drag a broad face-facing surface across that region unless BENCH evidence demonstrates that the motion preserves the required film.

The Core Sketch therefore freezes the functional state sequence, not the detailed mechanism:

- `CONTACT / TREATMENT STATE`
- `APPLICATION-CLEAR STATE`
- `SETTLE / RELEASE-READY STATE`
- `NON-WIPING RELEASE STATE`

The mechanism may later use retraction, segmentation, staged unloading, alternate support transfer, local application after support release, or another architecture. The product requirement is that coverage and film preservation survive the transition.

### 3.5 Emergency release

Emergency/unpowered release always outranks product preservation. A safety release may interrupt or disturb the final skincare film; the session must then report an interrupted/partial state rather than false COMPLETE.

## 4. Contract C: prepared-session validity and readiness

### 4.1 READY is derived, never cached as truth

`READY` means:

> If the user presses the physical primary control now, the exact prepared routine can safely execute under the locally available validated state.

A prior `READY` flag is invalid after any material state change.

### 4.2 Prepared-session identity

Every prepared session must bind at minimum:

- unique prepared-session ID;
- routine ID and routine version;
- intended AM/PM/day context when schedule-dependent;
- ordered mandatory and optional stages;
- exact assigned product identity per product stage;
- product market/formulation/version identifier when known;
- product trust/evidence state;
- application-profile version;
- prepared dose quantity or bounded quantity state;
- preparation timestamp and freshness/age rule where relevant;
- source reservoir/slot identity;
- product-change/changeover state;
- contamination/service state;
- water/rinse-resource sufficiency;
- waste-capacity sufficiency;
- battery/energy sufficiency;
- thermal readiness for scheduled thermal stages;
- device/dock fault state;
- local offline copy of the routine and application constraints required to execute it.

### 4.3 Minimum readiness predicates

A session cannot report READY if any mandatory predicate is false or unknown:

- routine definition is internally valid;
- every mandatory stage has a supported execution path;
- every required product is permitted for automated execution;
- prepared dose identity matches expected product identity;
- prepared dose is not invalidated by age/changeover/state rules;
- mandatory product quantity is sufficient;
- water/rinse resource is sufficient;
- waste capacity is sufficient;
- energy reserve is sufficient with safety margin defined by engineering later;
- required thermal subsystem is ready if used;
- no unresolved service/cleaning fault invalidates the wet path;
- no product mismatch/reformulation warning requires acknowledgement;
- the required local control data exists even without network/cloud.

### 4.4 Mandatory invalidation events

Invalidate the prepared session on:

- saved routine change affecting the prepared routine;
- mandatory product swap;
- slot reassignment;
- suspected wrong-product event;
- detected/declared reformulation requiring re-characterisation;
- expiry of an age-sensitive prepared dose;
- interrupted dock preparation;
- incomplete wet-path service/changeover;
- contamination warning;
- loss of sufficient water or product quantity;
- waste capacity becoming insufficient;
- battery/energy becoming insufficient;
- required thermal reset not completed;
- device fault affecting a mandatory stage;
- application profile or safety-rule update that invalidates the old preparation;
- physical removal/reinstallation of a prepared-dose module when identity cannot be maintained.

Network loss alone must not invalidate an otherwise locally complete prepared session.

### 4.5 Degraded but honest states

Use separate user/system states rather than overloading READY:

- `READY`
- `PREPARING`
- `NEEDS_ATTENTION`
- `PARTIAL_ROUTINE_AVAILABLE`
- `NOT_READY`
- `SAFETY_HOLD`

A partial routine may be offered only when the user explicitly chooses it and the UI does not call it the originally scheduled complete routine.

## 5. Contract D: complete-routine resource envelope

### 5.1 Purpose

The cleanser-era product cannot be expanded by independently adding serum, moisturiser, SPF, optics and thermal features without a single session-level budget. Every candidate routine must close simultaneously on fluid mass, dry mass, CG, torque, energy, thermal readiness, time, dock capacity and waste.

### 5.2 Session variables

For a prepared routine define:

- `V_water`: fresh water/rinse volume;
- `V_cleanser`: cleanser dose;
- `V_leaveon[i]`: each treatment/serum/essence dose;
- `V_moist`: moisturiser dose;
- `V_spf`: facial sunscreen dose when used;
- `V_purge`: session-attributable purge/changeover allowance carried on-head, if any;
- `V_recovered`: recovered liquid entering waste;
- `V_residual`: residual liquid remaining in facial/wet paths after the session;
- `m_session_fluids`: total on-head liquid mass at start;
- `m_loaded`: dry wearable mass plus all session-carried liquids and any routine-specific modules;
- `CG_loaded`: loaded centre of gravity;
- `tau_head`: wearer torque contribution;
- `E_electrical`: electrical energy required by pumps/control/actuation/optics/etc.;
- `E_thermal`: thermal-state requirement where WARM/COOL is scheduled;
- `t_routine`: complete routine duration including required settle periods;
- `N_bulk_slots`: dock bulk-product slots needed for the ownership model;
- `V_session_storage`: isolated session-dose storage volume;
- `V_waste_required`: waste capacity required with margin.

Historical targets such as dry mass <=215 g, loaded mass <255 g, CG Z <=30 mm and torque <=0.070 N*m remain engineering constraints to verify against live authority; this document does not promote them as physically achieved.

### 5.3 Required planning scenarios

Maintain at least three routine scenarios:

**MINIMUM SUPPORTED**
- clean;
- rinse/recover;
- one supported leave-on/moisturising finish;
- settle if needed;
- release.

**NORMAL PM**
- clean;
- rinse/recover;
- optional treatment modality;
- one treatment/serum;
- moisturiser;
- settle;
- release.

**DEMANDING AM**
- clean;
- rinse/recover;
- optional validated treatment;
- one or more leave-ons;
- moisturiser where routine requires it;
- facial SPF when validated;
- required settle;
- release.

For each scenario, unknown numerical values remain variables or bounded research inputs until measured. Do not fabricate clinically correct doses merely to close a spreadsheet.

### 5.4 Budget gates

A routine architecture cannot progress to integrated digital freeze if the demanding supported routine cannot plausibly remain within:

- loaded mass target;
- CG/torque target;
- available session-dose volume;
- waste capacity;
- electrical energy budget;
- thermal readiness budget;
- acceptable ownership-loop preparation time;
- a routine duration the target customer can plausibly accept.

Failure of one budget is an architecture conflict, not permission to weaken the budget silently.

## 6. Contract E: product preservation, carryover and changeover

### 6.1 Separate five truths

For every third-party skincare product, keep these independent:

1. **IDENTITY**: what exact product is loaded;
2. **PHYSICAL CHARACTERISATION**: how it behaves in the delivery system;
3. **COMPATIBILITY**: whether its material/chemical/packaging interaction is supported;
4. **CONTAMINATION STATE**: what else may be present in its path/reservoir/session dose;
5. **APPLICATION VALIDATION**: whether Masck has evidence that the selected application profile performs adequately for the claimed use.

A product that can physically flow is not automatically compatible or validated.

### 6.2 Trust ladder

Internal states remain:

- `KNOWN`
- `CHARACTERISED`
- `VALIDATED`
- `RESTRICTED_OR_UNSUPPORTED`

Community data may promote discovery confidence and characterisation evidence, but cannot by itself promote a safety/claims-critical product to `VALIDATED`.

### 6.3 Carryover boundaries

The architecture must separately validate:

- cleanser -> rinse transition;
- rinse -> first leave-on transition;
- leave-on A -> leave-on B carryover;
- leave-on -> moisturiser;
- moisturiser -> SPF where both are used;
- reservoir/product changeover;
- service/cleaning-fluid residues where applicable.

Define carryover metrics before declaring a wet path clean enough. Do not treat an empty line or a purge command as proof of acceptable residual contamination.

### 6.4 Wrong-product and reformulation handling

If a slot is expected to contain Product A but observed physical behaviour strongly contradicts the expected profile, the system must stop automated preparation/use and ask the user to confirm whether the product changed.

A renamed/reformulated product can require re-characterisation even if branding and barcode remain similar. Track SKU/market/formulation-version metadata where practical.

### 6.5 Unsupported product behavior

An unsupported required product blocks the prepared complete routine. The system may suggest a supported alternative routine only if it is presented honestly as a different routine and the user chooses it.

## 7. Shared-interface writing ownership

Each cross-lane contract has exactly one writing owner. Other lanes may consume, review and submit evidence but should not maintain competing versions.

| Shared contract | Writing owner | Required consumers |
| --- | --- | --- |
| stage-by-region completion | Lane 5 whole-product conductor | Lanes 1, 3, 4 |
| face-contact/occlusion state table | Lane 1 complete-routine facial delivery | Lanes 3, 5 |
| prepared-session validity/readiness | Lane 4 Routine OS/product intelligence | Lanes 1, 2, 5 |
| complete-routine resource envelope | Lane 5 whole-product conductor | Lanes 1, 2, 3, 4 |
| product identity/preservation/changeover semantics | Lane 4 for identity/evidence semantics; Lane 2 for physical service implementation | Lanes 1, 5 |
| non-wiping release acceptance | Lane 3 wearable/human factors, consuming Lane 1 film-survival evidence | Lanes 1, 5 |

Where two lanes contribute, only the stated contract owner writes the canonical interface definition; the adjacent lane owns its implementation evidence.

## 8. Promotion invariants

The following are fail-closed product invariants:

- no required stage reaches COMPLETE with a required facial region `UNREACHABLE`, `UNSUPPORTED`, `INTERRUPTED` or `UNKNOWN`;
- no prepared session reports READY while any mandatory validity predicate is false/unknown;
- no unsupported mandatory product can produce routine COMPLETE;
- no documentation, CAD or simulation alone may promote BENCH/HUMAN/REG/CLAIM/SUPPLIER evidence;
- no shared interface may have two canonical writing owners;
- no green subsystem CI result may close a P0 physical proof gate;
- no emergency-release requirement may be weakened to preserve skincare film;
- no SPF completion claim may exceed the exact validated facial region/product/application envelope.

## 9. Immediate P0 dependency order

1. Freeze this completion/readiness/contact/resource/product-integrity contract set.
2. Build the reduced-region CLEAN -> RINSE -> thin leave-on -> thicker leave-on -> final leave-on -> settle -> non-wiping release proof package.
3. Establish a representative product-family envelope and carryover metrics.
4. Close a first whole-routine resource spreadsheet/model for minimum, normal PM and demanding AM sessions.
5. Map every face-facing support/seal/treatment surface to its routine contact/occlusion state and identify uncovered islands.
6. Only then expand to whole-face application and sizing/fit validation.
7. Keep facial SPF as a separate higher-rigor application/claims lane until ordinary leave-on success is credible.

## 10. Pivot conditions

Evidence should force a major product review if any of these persist across credible alternative architectures:

- required facial regions cannot be reached after contact/support structures clear;
- final leave-on film cannot survive safe removal;
- cleanser/product carryover cannot be reduced to an acceptable physical criterion;
- normal third-party product families cannot be delivered without impractical product restrictions;
- complete-routine session resources make wearable mass/CG/torque unacceptable;
- dock preparation/cleaning becomes so burdensome that the product no longer removes routine friction;
- supported complete routines become materially slower or more effortful than the manual routines they replace;
- safe facial SPF deposition cannot support truthful claims, in which case SPF should be postponed rather than faked;
- whole-routine coverage and fit cannot be achieved across a commercially useful size range without unacceptable complexity.

The first response to a failed proof is architecture refinement. Repeated failure of the core promise under credible alternatives is a reason to reconsider the product, not to relabel an incomplete routine as complete.
