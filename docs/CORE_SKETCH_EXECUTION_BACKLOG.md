# MASCK ONE Core Sketch Execution Backlog

Status: **product-wide triage and execution queue**  
Date: 2026-09-10  
Companion specification: `docs/CORE_SKETCH_V1.md`  
Research archive: `docs/research/CORE_SKETCH_DEEP_RESEARCH_2026-09-10.md`

## 0. Purpose

This is the durable, dependency-ordered **step-by-step to-do list for work that changes Masck One**.

It exists to prevent three recurring failure modes:

1. agents improving a local subsystem while accidentally changing the product concept;
2. multiple chats creating parallel architecture truths for the same subsystem;
3. “good idea” features being implemented before the product-level UX, evidence boundary and dependencies are resolved.

Every substantive future task should be traceable to this backlog or explicitly add a new backlog item before changing the concept.

This file is not engineering authority. It orchestrates work; released authority, source/CAD and accepted evidence remain controlling.

---

# 1. Triage vocabulary

Every item is assigned one state.

- **LOCKED** — core-sketch intent. Do not change casually; changing it requires explicit product-concept review.
- **SELECTED** — chosen direction, still requires detailed implementation/refinement.
- **PROVE** — concept is desirable but must be physically or empirically validated before promotion.
- **EXPLORE** — bounded R&D question; alternatives are allowed within the locked intent.
- **INTEGRATE** — subsystem work exists and needs whole-product integration.
- **BLOCKED** — cannot close until named dependency/evidence exists.
- **REJECTED** — explored idea that should not be revived without new evidence.
- **DONE** — accepted evidence/implementation closes the backlog item at its required level.

Priority:

- **P0** — identity/existential; failure can invalidate the whole product.
- **P1** — required for coherent V1.
- **P2** — important supporting quality/capability.
- **P3** — later/future only.

Evidence classes:

- **DOC** — coherent specification/decision record.
- **DIGITAL** — source/CAD/simulation/verifier evidence.
- **BENCH** — physical subsystem/coupon evidence.
- **HUMAN** — supervised human-factors/usability evidence.
- **REG/CLAIM** — regulatory/claims-quality evidence where applicable.
- **SUPPLIER** — production/supplier/material evidence.

---

# 2. Global execution rules

Before every substantive action:

- reconstruct live `main`, relevant owner branch/PR, exact head, CI and current authority;
- reuse the existing owning lineage instead of opening a competing architecture lane;
- read `docs/CORE_SKETCH_V1.md` and the subsystem’s governing engineering docs;
- keep concept targets separate from physical proof;
- preserve protected anatomy, airway, leakage, mass/CG, quick-release and other existing hard constraints;
- never make CI green by weakening requirements or evidence firewalls;
- never promote a research benchmark into a Masck specification without an explicit selection/evidence step;
- record meaningful decisions in repo docs, not only chat history;
- when a backlog item changes meaningfully, update this file’s status/notes in the same lineage.

Definition of “closed”:

> An item is not DONE because a plausible geometry or app screen exists. It is DONE only when the acceptance criteria and required evidence class below are satisfied at the stated level.

---

# 3. Phase 0 — freeze the product identity before expanding hardware

## CS-000 — Complete-routine hierarchy

**Priority:** P0  
**State:** LOCKED  
**Owner:** product concept / conductor  
**Evidence:** DOC

**Intent**  
Preserve Masck One as a complete automated facial-skincare system, not an LED mask, cleanser or gadget collection.

**Acceptance**

- all new feature PRs describe how they support the complete routine;
- no subsystem becomes the product identity in public/product copy;
- hierarchy remains COMPLETE ROUTINE → cleaning/treatment/application/protection;
- no “automated cleanser plus manual skincare afterward” fallback is silently introduced.

## CS-001 — End-state promise

**Priority:** P0  
**State:** LOCKED  
**Evidence:** DOC + later HUMAN

**Intent**  
When Masck comes off after a supported routine, no additional manual facial skincare step is required.

**Acceptance**

- routine state model ends with non-wiping release;
- final leave-on layer survives removal;
- product copy never calls an incomplete routine “complete”;
- later human testing specifically measures whether users feel any need to manually finish the face.

## CS-002 — Facial-skincare boundary

**Priority:** P0  
**State:** LOCKED

**Acceptance**

- V1 whole-routine claim explicitly excludes decorative cosmetics/makeup;
- no future agent expands scope to waterproof mascara/foundation removal without a new concept decision;
- sunscreen language remains facial-only and never implies ears/neck/body coverage.

## CS-003 — User-product compatibility principle

**Priority:** P0  
**State:** LOCKED

**Acceptance**

- product does not require MASCK-made cleanser/serum/moisturizer/SPF;
- compatibility system is designed around third-party consumer skincare;
- proprietary chemistry may be tested as a reference but cannot become the default lock-in strategy without explicit product review.

## CS-004 — Offline physical independence

**Priority:** P0  
**State:** LOCKED

**Acceptance**

- configured routine can start and complete safely without phone/internet/cloud/account authentication;
- physical emergency release never depends on software/cloud;
- external AI outage cannot brick normal device use.

---

# 4. Phase 1 — existential full-routine proof

Nothing downstream should be considered product-safe until the complete sequence is shown to be physically plausible.

## CS-010 — Reduced full-routine cheek rig

**Priority:** P0, G1\
**State:** PROVE; acceptance thresholds not yet established\
**Dependencies:** CS-000..004, CS-014/015 acceptance domain; CS-018 supplies interface-edge cases\
**Owner:** Lane 1; existing treatment geometry remains with its current producer\
**Evidence:** off-face inert-surrogate BENCH evidence only at this gate

**Question**

Can the reduced CLEAN -> RINSE/RECOVER -> representative thin and thicker leave-on -> SETTLE -> NON-WIPING RELEASE sequence preserve distinct layers without unacceptable carryover, pooling or loss?

**Acceptance**

- Before an acceptance run, identify the required region and prohibited analog boundaries, surrogate families, reference application, measurement uncertainty and decision thresholds. Bounds requiring formulation/biological/protection expertise remain BLOCKED until specified by the qualified evidence owner.
- Separately quantify cleaning-tracer residue, each deposited layer, spatial nonuniformity, pooled/collected/device-resident quantity and final-film loss during release. Do not count commanded volume as deposited volume or visual cleanliness as chemical purity.
- Include representative curvature, interface edges, repeated trials and declared fit variation; report uncertainty and failures, not only the best demonstration.
- Close a per-layer quantity balance and compare before/after-release spatial maps. Preserve the existing leakage and protected-region criteria.
- Treat the result as reduced-region evidence only. It cannot certify whole-face coverage, SPF, skin safety, efficacy or powered on-face operation. CS-018 and qualified later validation remain separate gates.
- Exploratory off-face measurements may establish unknown inputs; they cannot retrospectively supply a passing acceptance criterion.
- No optional optical or thermal subsystem is required to answer this first transfer question. No human cosmetic-use procedure is specified by this task.

## CS-011 — Barrier-preservation proof plan

**Priority:** P0  
**State:** PROVE  
**Dependencies:** CS-010  
**Evidence:** BENCH → HUMAN

**Acceptance**

- define appropriate manual gentle-cleansing control;
- choose skin-barrier/hydration measurements with qualified expert input;
- define stop conditions for irritation/damage;
- demonstrate that Masck’s cleaning concept can be tuned without obvious barrier penalty before efficacy marketing.

## CS-012 — Leave-on survival through release

**Priority:** P0  
**State:** PROVE  
**Dependencies:** CS-010

**Acceptance**

- quantify/visualize where final leave-on film remains after removal;
- no broad contact surface drags across the newly coated face during release;
- repeat across representative face curvature/fit variation;
- identify zones requiring geometry/application refinement.

**Convergence acceptance, 2026-09-10**

- Use the required-domain map from CS-015 and all-contact map from CS-018, including stationary supports and thermal/fluid surfaces.
- Report local loss as well as total retained quantity, before and after normal release. A high global retained fraction cannot hide a stripped required region.
- Emergency release remains independent and takes priority; do not make film preservation a prerequisite for release.

## CS-013 — Multi-product contamination proof

**Priority:** P0  
**State:** PROVE

**Acceptance**

- demonstrate that cleanser/rinse water does not meaningfully contaminate serum/moisturizer delivery;
- demonstrate that one leave-on product does not unpredictably back-contaminate another stored product;
- define acceptable carryover metrics before full architecture freeze.

**Convergence acceptance, 2026-09-10**

- Set carryover metrics and uncertainty before the experiment, not after viewing results. Distinguish residual free water, residual cleaning tracer and subsequent layer dilution.
- Trace contamination through the whole product-contact graph, including shared downstream interfaces, dock returns and stored-product backflow.
- The legacy 0.90 recovery and 400 µL free-liquid targets remain controlling for their original scope; they do not close residue composition or layered-product compatibility.

## CS-014 — Product family envelope

**Priority:** P0  
**State:** EXPLORE

**Intent**  
Define the practical range of consumer liquids/gels/lotions/creams Masck intends to support.

**Acceptance**

- create representative physical families: watery essence, low-viscosity serum, shear-thinning serum, lotion, cream/emulsion, gel cleanser, cream cleanser, sunscreen families;
- explicitly identify classes not currently supportable;
- avoid claiming “all liquids” literally;
- use this envelope to drive loading/application/service work.

**Convergence acceptance, 2026-09-10**

- Define a representative target-user product/routine cohort jointly with CS-291/293 before selecting only easy families. Preserve difficult thin/thick and sunscreen questions explicitly.
- Characterisation, formulation preservation and a validated application context are separate gates. Do not promise universal compatibility, dilution, heating or other reformulation to make a product fit the machine.
- Report both supported individual products and supported complete routines. A collection of compatible products can still fail to cover the user's actual sequence.

---

## CS-015 — Required-region completion contract

**Priority:** P0, G0\
**State:** PROVE\
**Owner:** Lane 1; Lane 4 consumes the versioned completion semantics\
**Dependencies:** CS-000..004, representative cohort from CS-014/293\
**Evidence:** DIGITAL definition, later qualified application evidence

**Acceptance**

- Define each stage's required facial domain from its intended product/routine use, prohibited anatomy, permitted fit/hardware range and coverage/film acceptance basis before optimizing the mask.
- Enumerate seams, eye/mouth boundaries, nose/cheek transitions and support-shadow regions. Any required region with no valid delivery/release path is an explicit blocker, not a silently excluded patch.
- Preserve legacy cleansing coverage gates without treating their aggregate percentage as full-routine completion evidence.
- Separate metered quantity, deposited quantity, spatial film, validated method and real-time machine observables. Do not invent a sensor to make completion appear observable.
- An unavailable required stage or unresolved application uncertainty prevents COMPLETE for that selected routine. Facial SPF completion never implies other body coverage or removal of future label obligations.

## CS-016 — Prepared-session validity and interruption contract

**Priority:** P0, G3\
**State:** SELECTED contract direction; implementation and validity limits PROVE\
**Owner:** Lane 4; Lane 2 produces the physical preparation receipt\
**Dependencies:** CS-015; initial identity/context definitions from CS-080 and storage-history fields from CS-017. CS-094 consumes the resulting contract; its completed implementation is not a prerequisite.

**Acceptance**

- Bind routine revision, temporary overrides, exact product/version and slot association, preparation receipt, physical dose state, storage/hold history, profile/hardware revisions, service result and resource availability.
- READY is re-evaluated at use. Unknown hold time, incomplete service, changed contents or missing required resource cannot inherit yesterday's READY.
- Revalidate skip/reorder/substitution independently. A requested product not onboard requires re-preparation; a valid temporary session never overwrites the saved routine.
- Persist progress and uncertainty across interruption. Do not replay an uncertain physical dose or claim software transaction logs prove exact fluid delivery.
- Specify local clock/version validity, received revocation handling and unknown remote-update risk without silently adding a network requirement to normal use.
- Supply deterministic non-hardware examples for changed routine, expired preparation, partial delivery, lost power, missing required SPF and valid optional-stage omission. No safety-critical limits are invented in this concept contract.

## CS-017 — Product preservation across dock and session storage

**Priority:** P0, G3\
**State:** PROVE; formulation/hygiene compatibility BLOCKED on qualified evidence\
**Owner:** Lane 2; Lane 4 stores the versioned evidence context\
**Dependencies:** CS-014/070 product and slot envelope

**Acceptance**

- Identify which retail-package functions must be preserved: containment, light/air exposure control, material contact and intended storage history. Dock bulk storage does not select universal open pouring or unqualified repackaging.
- Compare original-container interfaces and qualified serviceable reservoirs at architecture level, including changeover, residue traps, assembly/service work and waste.
- Define product-contact materials and hold-history evidence needed for bulk and prepared doses. No unmeasured shelf life, chemical equivalence, sanitation or preservation claim.
- Bind changed product/formulation, opened/loaded state, unknown age and interrupted service to CS-016 readiness. Physical flow similarity is not chemical identification.

## CS-018 — All-contact support and film-preserving transition

**Priority:** P0, G2\
**State:** PROVE\
**Owner:** Lane 1 produces contact/occlusion requirements; Lane 3 owns retention/removal geometry\
**Dependencies:** CS-015; current treatment, thermal, fluid, exterior and retention geometry

**Acceptance**

- For contact, leave-on, settle and release, classify every moving island, stationary annulus, seal, support and other possible contact surface; include required facial patches hidden beneath them.
- Show the structural support/reaction path during each state and how every required patch can become accessible without wiping an already finished patch.
- Consume current authority/world frames and protected envelopes. Require exact forbidden-material collision checks and continuous conservative motion evidence where motion matters; sampled poses alone are insufficient.
- Keep the emergency-release path independently available. No optical/thermal plate, face contact or cosmetic shell becomes an accidental release stop.
- An off-face cheek pass cannot close whole-face load transfer, fit, sightlines or film preservation. Record remaining measured-human questions separately.

---

# 5. Phase 2 — complete routine state machine

## CS-020 — Canonical routine state model

**Priority:** P0  
**State:** SELECTED

**Required stages**

- PREPARED
- PLACED / FIT CONFIRMED
- CLEAN
- RINSE / RECOVER
- TREAT (optional submodes)
- LEAVE-ON 1..N
- MOISTURISE
- FACIAL SPF when scheduled/validated
- SETTLE when needed
- RELEASE READY
- COMPLETE
- RETURN / SERVICE

**Acceptance**

- every stage has entry/exit preconditions;
- optional stages do not create invalid sequence combinations;
- early removal can report exactly what completed;
- an unavailable mandatory step prevents false “complete” status;
- the state model is shared by device/app/dock concepts.

**Convergence acceptance, 2026-09-10**

- Consume CS-015/016. Completion refers to the selected eligible session, not an unchanged saved routine when the user made a deliberate exception.
- Include incomplete, uncertain-dose and service-incomplete outcomes; none may silently converge to COMPLETE. Emergency release does not wait for state reconciliation.

## CS-021 — Phase-transition experience

**Priority:** P1  
**State:** SELECTED

**Acceptance**

- CLEAN feels active but gentle;
- RINSE feels like a clean transition, not more washing;
- OPTICAL feels still/quiet;
- LEAVE-ON feels materially different from cleansing;
- final stages do not leave the user wondering whether cleanser is still present;
- distinctions come primarily from real behavior, not beeps/RGB theater.

## CS-022 — Timing philosophy

**Priority:** P1  
**State:** EXPLORE

**Acceptance**

- separate stage time into minimum physical/chemical requirement versus “nice round number”;
- allow routines to omit unnecessary stages;
- support a quick routine only if it remains meaningfully complete for its selected purpose;
- do not shorten sunscreen settling or other stages merely to meet marketing duration.

---

# 6. Phase 3 — industrial-design master surface

## CS-030 — Front-face archetype

**Priority:** P0  
**State:** LOCKED / INTEGRATE

**Acceptance**

- one calm continuous facial volume;
- no goggle rings/eye bezels;
- no nose cone;
- no respirator grille;
- no fake vents;
- no visible actuator pods;
- no arbitrary panelization;
- eye openings feel carved from the shell rather than attached rings;
- whole front reads as premium personal care at 3 m distance.

## CS-031 — Eye-opening refinement

**Priority:** P1  
**State:** INTEGRATE

**Acceptance**

- reconcile released protected anatomy with ~63×47 mm class ID direction where possible;
- preserve thin-looking inner edge and controlled roll;
- no aggressive superhero/VR eye cant;
- test exterior reflections and interior sightline together;
- no dark bezel that visually turns the product into goggles.

## CS-032 — Nose / cheek transition

**Priority:** P1  
**State:** EXPLORE

**Acceptance**

- central facial volume feels anatomical but abstracted;
- airway openings are real but visually quiet;
- cheek volume transitions continuously around the nose;
- no visual “muzzle” or respirator cue;
- preserve nasal protected geometry and evidence gates.

## CS-033 — Lower-face / mouth termination

**Priority:** P1  
**State:** EXPLORE

**Acceptance**

- mouth opening remains usable and visually clean;
- lower shell avoids jaw-armor geometry;
- perimeter appears thin/light;
- release/removal path does not drag on leave-on film.

## CS-034 — Temple / control composition

**Priority:** P1  
**State:** INTEGRATE

**Acceptance**

- primary control discoverable by touch;
- visually restrained from front view;
- Warm Porcelain distinction remains subtle;
- control surface/mark follows shell geometry and does not look stuck on;
- existing HMI owner lineage is reused.

## CS-035 — Rear architecture visual recession

**Priority:** P1  
**State:** EXPLORE

**Acceptance**

- rear hardware is compact and subordinate;
- no VR halo appearance;
- no large visible counterweight pod;
- Smoke Graphite used only where visual recession genuinely helps;
- hair/ear clearance considered with ID, not added later.

## CS-036 — Seam choreography

**Priority:** P1  
**State:** SELECTED

**Acceptance**

- every visible seam has service/manufacturing reason;
- no eye seam rings;
- no arbitrary front panel seams;
- master gap/flush targets are documented;
- seam hierarchy remains coherent around dock/service interfaces.

## CS-037 — Perceived thinness study

**Priority:** P1  
**State:** EXPLORE

**Acceptance**

- define which silhouette edges must read thinnest;
- protect eye/temple/lower-face edge treatment from internal packaging growth;
- evaluate front, 3/4, profile and worn views;
- do not optimize central depth at cost of unstable CG or fit.

## CS-038 — Surface/radius/highlight language

**Priority:** P2  
**State:** EXPLORE

**Acceptance**

- create a small family of edge-radius categories;
- broad, continuous highlights on main shell;
- no toy-soft global rounding;
- no razor tech chamfers near face;
- render under bathroom/bedroom daylight and warm artificial light.

---

# 7. Phase 4 — CMF and tactile identity

## CS-040 — CMF token preservation

**Priority:** P0  
**State:** LOCKED

**Tokens**

- Mineral Ivory `#E9E5DC`
- Warm Porcelain `#DED9CF`
- Soft Stone `#CFC8BC`
- Smoke Graphite `#454542`
- Opal Neutral `#F2EFE7`

**Acceptance**

- tokens remain product/brand intent until material-qualified;
- no black-front “tech” variant becomes default;
- no chrome/fake metal accent introduced as premium shorthand.

## CS-041 — Exterior finish samples

**Priority:** P1  
**State:** PROVE

**Acceptance**

- compare satin-matte textures under cleanser/oil/sunscreen contamination;
- evaluate fingerprints, staining, cleaning and scratch visibility;
- reject rubberized coatings that age tacky;
- select a premium dry-touch finish with broad soft highlights.

## CS-042 — Skin-contact surface family

**Priority:** P0  
**State:** PROVE

**Acceptance**

- low tack on clean/damp skin;
- non-absorptive;
- inspectable;
- cleanable;
- resists representative skincare staining/swelling;
- no exposed wet textile foam;
- subjective comfort tested across routine duration.

## CS-043 — Branding restraint

**Priority:** P1  
**State:** LOCKED

**Acceptance**

- M-Cut, M/1 and Aperture Mark roles remain distinct;
- no repeated wordmark wallpaper;
- front face is visually product-first;
- primary-control mark is integrated, not printed decoration.

**Convergence acceptance, 2026-09-10**

- Reconcile the concept Aperture Mark micro-control intent with the released brand authority's M-Cut control assignment through the existing brand/HMI owners. This review does not change either machine authority or current cap geometry. It is a detail/authority task, not an existential product redesign.

---

# 8. Phase 5 — fit, sizing and on-face human factors

## CS-050 — Size-family decision

**Priority:** P0  
**State:** PROVE

**Selected hypothesis**

Limited size family (likely 2–3) + passive/adaptive fit.

**Acceptance**

- anthropometric dataset/study defines size boundaries;
- compare 1-size, 2-size, 3-size coverage and fit burden;
- choose smallest number that meets fit/coverage/airway/comfort requirements;
- no custom scan/manufacture required for ordinary ownership unless evidence forces it.

## CS-051 — First-10-seconds placement study

**Priority:** P0  
**State:** HUMAN

**Acceptance**

Users can:

- identify orientation immediately;
- place without mirror dependence where practical;
- achieve secure state without repeated strap adjustments;
- perceive airway open;
- avoid hair pinching;
- avoid localized painful pressure;
- understand “ready to start.”

## CS-052 — Retention UX

**Priority:** P0  
**State:** INTEGRATE / PROVE

**Acceptance**

- retention force stays inside engineering/comfort evidence limits;
- secure without “helmet tightening” ritual;
- quick release ≤ existing requirement;
- release is discoverable by touch;
- no uncontrolled snap/slap;
- existing retention owner lane remains canonical.

## CS-053 — Mass/CG after full-routine expansion

**Priority:** P0  
**State:** PROVE

**Acceptance**

- complete session product load included in mass model;
- optical/thermal/application additions included;
- dry/loaded mass, CG Z and torque reconciled with current targets;
- no hidden assumption of rear counterweight solving poor front packaging;
- comfort evaluated dynamically, not only static CAD mass properties.

**Convergence acceptance, 2026-09-10**

- Lane 5 produces one mass/CG/torque ledger; Lane 3 owns human-factors acceptance. Include prepared, operating, interrupted and retained-waste states, all new isolation hardware and uncertainty.
- Couple mass and pitch torque using the actual common datum. At 255 g with a 30 mm horizontal lever, gravity gives 0.075021 N m; this conditional example exceeds 0.070 N m and must not be treated as independent budget headroom. It is not a new CG requirement.

## CS-054 — Forward/peripheral vision

**Priority:** P1  
**State:** PROVE

**Acceptance**

- quantify visual field for selected sizes/fit states;
- laptop/phone/TV use evaluated;
- safe indoor mobility boundary defined;
- marketing never implies unrestricted vision if not achieved.

## CS-055 — Corrective glasses

**Priority:** P2  
**State:** EXPLORE

**Acceptance**

- test representative frame widths/nose bridges;
- decide supported/unsupported frame envelope;
- no lens/frame compression into face;
- if glasses cannot be supported, onboarding/product copy states this clearly.

## CS-056 — Hair / ears / jewelry

**Priority:** P1  
**State:** HUMAN

**Acceptance**

- long hair, tied hair, short hair tested;
- no routine hair trapping at temple/rear;
- common small earrings clear;
- large/hoop earring boundary documented;
- common ear piercings not loaded by hard moving elements.

## CS-057 — Facial hair

**Priority:** P2  
**State:** PROVE

**Acceptance**

- characterize cleansing/application limits over stubble/moustache/beard zones;
- define supported facial-hair envelope;
- do not assume bare-skin coverage metrics transfer unchanged.

## CS-058 — Speaking / mouth use

**Priority:** P2  
**State:** HUMAN

**Acceptance**

- normal short speech does not destabilize fit or create unsafe fluid behavior;
- product does not promise drinking/eating while worn unless separately validated.

---

# 9. Phase 6 — sensory system

## CS-060 — Opal status grammar

**Priority:** P1  
**State:** SELECTED

**Acceptance**

Document and prototype:

- invisible/asleep;
- ready/healthy;
- preparing/servicing;
- command accepted;
- attention needed;
- safety-critical alert.

Color is never the sole information channel. Normal system is Opal-neutral rather than rainbow-coded.

## CS-061 — Light-source invisibility

**Priority:** P1  
**State:** PROVE

**Acceptance**

- no visible LED-strip aesthetic;
- emitter/hotspot pattern minimized through material/optical treatment;
- off-state reads as material, not electronics;
- nighttime dock brightness tested in dark bedroom.

## CS-062 — Haptic vocabulary

**Priority:** P2  
**State:** EXPLORE

**Acceptance**

- define at most a small set of unmistakable haptic events;
- no continuous “activity buzz” unless it is the real treatment itself;
- completion distinguishable from warning;
- accessible redundancy with light/text.

## CS-063 — Sound budget and sound quality

**Priority:** P1  
**State:** PROVE

**Acceptance**

- measure operating sound in quiet room;
- characterize tonal whine, pump pulses, gurgle, rattles and mechanism impact separately from dBA;
- no startup jingle;
- no phase chirps required for normal use;
- no intentional metallic ping;
- completion sound optional or unnecessary;
- bedroom/bathroom target documented from user testing.

## CS-064 — Motion quality grammar

**Priority:** P1  
**State:** INTEGRATE

**Acceptance**

All user-perceived transitions target:

- smooth onset;
- exactly constrained motion;
- no friction spike;
- no chatter;
- resolved state;
- controlled unloading/return;
- no hollow impact.

Apply this grammar to primary button, retention/release, cartridge/service interactions, dock settlement and facial-interface state transition.

---

# 10. Phase 7 — product loading and product identity

## CS-070 — Bulk-slot count study

**Priority:** P0  
**State:** EXPLORE

**Acceptance**

- derive required slot count from real routines, not arbitrary “4/5 slots”;
- support common AM/PM routine diversity without turning dock huge;
- evaluate cleanser, treatment A/B/C, moisturizer, SPF and optional shared products;
- decide whether some slots are role-agnostic;
- preserve future expansion without giant V1 dock.

## CS-071 — Load-product user flow

**Priority:** P0  
**State:** SELECTED

**Flow**

**choose bay → scan/search → confirm exact product → load → close → system check → ready**

**Acceptance**

- no engineering terminology in consumer UI;
- one clear product/bay association;
- user can correct a mis-identification before loading;
- identity and compatibility state remain visible later.

## CS-072 — Physical mistake-proofing

**Priority:** P0  
**State:** PROVE

**Acceptance**

- tactile orientation for low vision;
- color not sole discriminator;
- wrong bay / wrong closure hard to do silently;
- product cannot easily be poured into waste/service opening;
- spill cleanup considered.

## CS-073 — Barcode/QR identification

**Priority:** P1  
**State:** EXPLORE

**Acceptance**

- evaluate regional SKU coverage;
- exact variant resolution where data exists;
- fallback when barcode is reused/missing;
- no assumption barcode encodes formulation revision.

## CS-074 — Label/camera/OCR identification

**Priority:** P1  
**State:** EXPLORE

**Acceptance**

- resolve brand/product/variant from front/back labels;
- request ingredient panel only when needed;
- camera permission is deliberate and explained;
- raw images handled according to privacy policy;
- user confirms uncertain match.

## CS-075 — Manual search fallback

**Priority:** P1  
**State:** SELECTED

**Acceptance**

- user can find product without camera;
- search distinguishes similarly named variants;
- regional/formulation differences are visible enough to confirm.

## CS-076 — Product-change flow

**Priority:** P1  
**State:** SELECTED

**Acceptance**

- “change product” distinct from simple refill;
- system knows old/new identity;
- path/service requirement shown simply;
- new product not available to routines until required checks complete.

## CS-077 — Level/readiness experience

**Priority:** P1  
**State:** PROVE

**Acceptance**

- enough confidence to warn before next required routine;
- uncertainty shown when exact volume cannot be known;
- app/dock says “enough for X scheduled routines” only if sensing/model supports it;
- no fake precision.

---

# 11. Phase 8 — product database and compatibility intelligence

## CS-080 — Canonical product-profile schema

**Priority:** P0  
**State:** SELECTED

**Fields at concept level**

- canonical product identity;
- market/SKU/formulation revision;
- product category/role;
- routine ordering constraints;
- application family;
- dose range;
- coverage region;
- settling interval;
- temperature constraints;
- incompatibility/interaction rules;
- physical characterization fingerprint;
- evidence status;
- source/provenance.

**Acceptance**

- schema versioned;
- evidence/provenance cannot be omitted;
- application data separated from medical efficacy claims.

**Convergence acceptance, 2026-09-10**

- Validation context includes formulation/version, delivery method, hardware/fit range, dose and required-region evidence, sequence/layer context, storage history and profile revision. Product validation is not automatic routine validation.
- Reuse evidence through justified equivalence classes rather than either testing an unbounded Cartesian product or assuming all combinations are equivalent.

## CS-081 — Evidence-state model

**Priority:** P0  
**State:** LOCKED

Internal states:

- KNOWN
- CHARACTERISED
- VALIDATED
- RESTRICTED/UNSUPPORTED

**Acceptance**

- transitions require explicit evidence rules;
- community popularity cannot auto-promote to VALIDATED;
- sunscreen/strong-actives can require stricter gates.

## CS-082 — Consumer wording for evidence states

**Priority:** P1  
**State:** EXPLORE

**Acceptance**

- test wording that communicates confidence without shaming product choice;
- avoid exposing internal regulatory jargon;
- clear difference between “recognized” and “approved for automatic use.”

## CS-083 — Reformulation detection workflow

**Priority:** P0  
**State:** EXPLORE

**Acceptance**

- ingredient/packaging/product metadata change can flag possible reformulation;
- unexpected physical signature can flag mismatch;
- product falls back to conservative state rather than inheriting old validation silently;
- user receives simple next action.

**Convergence acceptance, 2026-09-10**

- A matching barcode/flow fingerprint can be consistent with multiple formulations or contents. A mismatch can reject; a match alone cannot establish chemistry, authenticity or continued validity.

## CS-084 — Community-learning privacy model

**Priority:** P1  
**State:** PROVE

**Acceptance**

- opt-in contribution;
- collect minimum technical product/application telemetry;
- no face photos required;
- aggregation and deletion policy documented;
- no health inference required to improve product profiles.

## CS-085 — Unknown-product bounded classification

**Priority:** P0  
**State:** EXPLORE

**Acceptance**

- unknown item can be categorized without arbitrary safety claims;
- AI confidence/uncertainty retained;
- user confirmation required when identity unresolved;
- unsupported products fail safely and politely.

## CS-086 — Physical signature check

**Priority:** P0  
**State:** PROVE

**Acceptance**

- representative product families produce repeatable enough response to detect gross mismatch/clog/wrong refill;
- temperature and reservoir level effects characterized;
- signature never treated as proof of brand/product identity on its own.

---

# 12. Phase 9 — routine software and scheduling

## CS-090 — Routine object model

**Priority:** P0  
**State:** SELECTED

**Acceptance**

- routine contains ordered product/treatment stages, dependencies and schedule metadata;
- device/dock can cache configured routines locally;
- revision/history prevents silent cloud edits changing an imminent routine.

## CS-091 — Playlist-like routine editor

**Priority:** P1  
**State:** SELECTED

**Acceptance**

- users work with product/treatment cards, not technical settings;
- drag/reorder only where compatible;
- blocked sequence explains why;
- save/name/schedule in one flow;
- visual simplicity remains premium.

## CS-092 — Weekly schedule

**Priority:** P1  
**State:** SELECTED

**Acceptance**

- AM/PM slots;
- Mon–Sun recurring assignment;
- alternate-day/interval support only where useful;
- next routine obvious;
- dock preparation linked to schedule.

## CS-093 — Today-only override

**Priority:** P1  
**State:** SELECTED

**Acceptance**

- Skip stage today;
- Run Quick routine;
- Use Product B tonight;
- skip routine;
- run another saved routine;
- recurring schedule remains unchanged unless user chooses “edit schedule.”

**Convergence acceptance, 2026-09-10**

- Use CS-016: reordering/substitution can invalidate already prepared quantities, storage or sequence evidence. Show a calm re-preparation state rather than pretending an unfilled product is available.

## CS-094 — Routine compatibility guard

**Priority:** P0  
**State:** PROVE

**Acceptance**

- deterministic validated rules gate sequence/frequency/temperature constraints;
- AI suggestions cannot bypass them;
- user receives reason and safe alternatives only where evidence supports them.

**Convergence acceptance, 2026-09-10**

- Product trust states alone do not validate a layered routine. Check the complete context from CS-080/016 and preserve mandatory-stage, interval and settling constraints.
- Optional treatment conflicts should remove or defer the optional capability where the selected routine permits it, not silently remove a required facial finish.

## CS-095 — Prepared-routine behavior

**Priority:** P0  
**State:** EXPLORE

**Acceptance**

- define when dock commits next-session doses;
- handle user changing tonight’s routine after preparation;
- handle missed session without wasting/contaminating product unnecessarily;
- prevent wrong prepared routine from starting silently.

**Convergence acceptance, 2026-09-10**

- Implement the CS-016 physical preparation contract. The last prepared/default routine is executable only while its local contents, history and resources remain eligible; offline is not permission to execute stale preparation.

## CS-096 — No-phone daily operation

**Priority:** P0  
**State:** PROVE

**Acceptance**

- prepared routine start from physical control;
- user can distinguish ready/not-ready without app;
- safe abort/release without app;
- routine completion stored locally and syncs later.

---

# 13. Phase 10 — dock industrial design and ownership UX

## CS-100 — Dock archetype

**Priority:** P0  
**State:** EXPLORE

**Acceptance**

- reads as premium personal-care object/skincare organizer;
- not coffee-machine/lab appliance;
- not a transparent fluidics showcase;
- mask is rested/protected intentionally;
- form works on bathroom vanity and, if acoustic/wet constraints allow, bedroom surface.

**Convergence acceptance, 2026-09-10**

- Do not select a premium silhouette before allocating bulk interfaces, clean/service fluids, waste, thermal rejection and service access. Compare daily and weekly active-attention burden, not only docking elegance.

## CS-101 — Dock footprint study

**Priority:** P0  
**State:** PROVE

**Acceptance**

- package real bulk-product, waste, charging/service requirements;
- minimize frontal footprint and perceived mass;
- compare vertical vs low-horizontal architecture;
- choose one direction using access, cleaning, stability and visual presence;
- do not freeze dimensions before this packaging proof.

## CS-102 — Mask presentation / protection

**Priority:** P1  
**State:** EXPLORE

**Acceptance**

- facial interface protected from dust/contact when docked;
- product remains easy to grab;
- no awkward hanging straps;
- no presentation that leaves a wet interior visibly exposed.

## CS-103 — Cable concealment

**Priority:** P2  
**State:** SELECTED

**Acceptance**

- rear/under routing;
- stable strain relief;
- cable not crossed by product-loading/service gestures;
- no daily plug/unplug requirement.

## CS-104 — Bulk product bay UX

**Priority:** P0  
**State:** EXPLORE

**Acceptance**

- easy to identify correct bay;
- fill/open/close feels premium and low-mess;
- product level/identity inspectable as needed;
- bays do not make dock visually busy;
- user can clean accidental spills.

## CS-105 — Waste concealment and service

**Priority:** P0  
**State:** INTEGRATE / PROVE

**Acceptance**

- waste never mistaken for fresh product;
- removal/emptying is low-drip and low-odor;
- service part has resolved tactile seating;
- existing cartridge owner lineage remains canonical;
- user does not handle loose wet liner as normal daily routine if avoidable.

## CS-106 — Return choreography

**Priority:** P1  
**State:** PROVE

**Acceptance**

- one-hand return;
- passive/self-guided alignment;
- one soft positive settlement;
- no scrape/rattle;
- Opal acknowledgement after actual secure/connected state;
- user can immediately walk away.

## CS-107 — Pickup choreography

**Priority:** P1  
**State:** PROVE

**Acceptance**

- no latch hunt;
- no cable;
- no resistance spike;
- orientation obvious;
- wearable is already prepared before user lifts it.

## CS-108 — Night behavior

**Priority:** P2  
**State:** PROVE

**Acceptance**

- dark-room light output does not disturb sleep;
- noisy service can defer to user-approved window when safe;
- readiness remains available on demand.

**Convergence acceptance, 2026-09-10**

- Quiet timing may defer optional service. Required hygiene/thermal/charge readiness cannot be asserted when those tasks are incomplete. Bedside suitability remains an evidence question.

---

# 14. Phase 11 — session-dose and whole-system balance

## CS-110 — Session-dose quantity model

**Priority:** P0  
**State:** PROVE

**Acceptance**

- derive representative per-routine liquid mass from real products/doses;
- include cleanser, rinse water/post-flush strategy, leave-ons and sunscreen;
- define worst-case prepared routine;
- feed mass/CG study rather than assuming “few mL” is always negligible.

**Convergence acceptance, 2026-09-10**

- Include session products, prime/dead volume, interface losses, service flush demand, remaining waste, uncertainty and fault-releasable inventory. Do not count package volume as usable contents.
- Preserve existing uncontrolled-release limits while extending the graph to new product chambers. Do not assume the historical six-cycle cartridge service requirement is demonstrated for expanded routines.

## CS-111 — Microdose packaging location

**Priority:** P0  
**State:** EXPLORE

**Acceptance**

- compare candidate regions by CG, tubing/path burden, service, thermal and ID impact;
- no heavy forehead/cheek bulge;
- no visible front cartridge;
- maintain perceived thinness priorities.

## CS-112 — Multi-product isolation

**Priority:** P0  
**State:** PROVE

**Acceptance**

- each prepared leave-on product remains chemically separated until intentional application;
- cross-carryover limits defined;
- service state prevents old product from invalidating newly loaded product.

**Convergence acceptance, 2026-09-10**

- Isolation extends from bulk storage through dock receivers, valves, wearable channels, applicators and service returns. Separate reservoirs alone do not close downstream carryover. Bind this graph to CS-013/017.

## CS-113 — Missed/changed routine handling

**Priority:** P1  
**State:** EXPLORE

**Acceptance**

- safe behavior when prepared routine is not used;
- safe behavior when user changes schedule after metering;
- product waste minimized without unsafe recombination;
- state visible to user only when action needed.

**Convergence acceptance, 2026-09-10**

- Consume CS-016 for missed, altered and partly executed sessions. Account for unused/discarded product and service work in the ownership budget; no automatic redispense of uncertain doses.

---

# 15. Phase 12 — cleansing / rinse / recovery experience

## CS-120 — Cleanse user sensation

**Priority:** P0  
**State:** INTEGRATE / PROVE

**Acceptance**

- gentle distributed feel;
- no scraping/pinching;
- no aggressive “brush” sensation required for perceived efficacy;
- comfort across representative cleanser families;
- existing treatment/carrier engineering reused.

## CS-121 — Rinse completeness

**Priority:** P0  
**State:** PROVE

**Acceptance**

- representative cleanser residue reduced to defined acceptable level before leave-ons;
- no obvious foaming remains;
- no pooled water released at stage transition;
- sensory state communicates “clean face” naturally.

**Convergence acceptance, 2026-09-10**

- Distinguish residual free liquid from cleaning-product concentration and adsorbed/device residue. Preserve the legacy recovery/leakage checks, then evaluate carryover separately under CS-013.

## CS-122 — Recovery cleanliness

**Priority:** P0  
**State:** PROVE

**Acceptance**

- spent fluid directed away from fresh product paths;
- face/eye/airway external leakage stays inside engineering requirements;
- no slosh/gurgle that destroys premium perception.

## CS-123 — Cleansing duration study

**Priority:** P2  
**State:** PROVE

**Acceptance**

- duration based on cleaning/barrier evidence;
- no arbitrary 60 s default solely because competitors use it;
- user can understand longer treatment time when a real requirement exists.

---

# 16. Phase 13 — massage / physical treatment

## CS-130 — Massage role in routine

**Priority:** P1  
**State:** SELECTED

**Acceptance**

- massage is optional/scheduled, not mandatory theater;
- timing relative to cleanse/leave-on defined;
- user understands it as a treatment stage, not proof of cleansing.

## CS-131 — Massage comfort envelope

**Priority:** P0  
**State:** INTEGRATE / PROVE

**Acceptance**

- reconcile historical motion/force targets with human comfort;
- no eye/mouth/airway protected-region compromise;
- no local buzzing hot spots;
- existing treatment owner lane remains canonical.

## CS-132 — Massage acoustics

**Priority:** P2  
**State:** PROVE

**Acceptance**

- tonal character and structure-borne noise assessed on-head;
- no cheap electric toothbrush association;
- quiet enough for routine context.

---

# 17. Phase 14 — WARM / COOL

## CS-140 — Deliberate WARM experience

**Priority:** P1  
**State:** INTEGRATE / PROVE

**Acceptance**

- even/gentle/responsive;
- clear maximum skin-contact temperature and sensing policy from engineering;
- no hot spots;
- warm treatment distinguished from incidental electronics heat;
- current WARM owner package reused.

## CS-141 — COOL experience

**Priority:** P2  
**State:** EXPLORE / PROVE

**Acceptance**

- beneficial/desired user sensation established before expensive architecture;
- condensation/wet-environment interaction studied;
- not forced into TEC architecture by concept;
- no surprising cold shock.

## CS-142 — Incidental heat budget

**Priority:** P0  
**State:** PROVE

**Acceptance**

- skin-adjacent warmth outside WARM remains below a perceptual/safety target;
- optical/electronics/charging heat cannot masquerade as treatment;
- comfort measured over longest routine.

**Convergence acceptance, 2026-09-10**

- Use the longest eligible routine and each local store/cheek, not a global energy sum that hides a local deficit. Include previous treatment, prepared storage, fluid state, incidental electronics/actuator heat and dock reset. Optional modality timing follows CS-094/271.

---

# 18. Phase 15 — optical treatment

## CS-150 — Optical claims/use-case definition

**Priority:** P1  
**State:** PROVE

**Acceptance**

- decide intended consumer benefit/claim territory before freezing wavelengths/dose;
- distinguish cosmetic wellness claims from regulated claims as needed;
- do not select optical parameters solely from competitor marketing.

## CS-151 — Wavelength/dose benchmark study

**Priority:** P1  
**State:** EXPLORE

**Research starting point:** ~633 / 830 / 1072 nm competitor benchmark.

**Acceptance**

- peer-reviewed/clinical/regulatory rationale for selected bands;
- dose/irradiance/session duration selected independently;
- no requirement to match 236 LEDs or competitor PCB/layout.

## CS-152 — Optical uniformity

**Priority:** P0 if optical included in V1  
**State:** PROVE

**Acceptance**

- whole supported face receives bounded field uniformity;
- curvature/distance/fit variation studied;
- hot/cold spots mapped;
- thermal effect separated from optical treatment.

## CS-153 — Eye-safety experience

**Priority:** P0  
**State:** PROVE

**Acceptance**

- eye exposure assessed for visible and invisible bands;
- product behavior remains safe under plausible misfit/eye direction;
- user instruction for open/closed eyes is explicit;
- no “amber glasses” or shutter architecture accepted merely from research brainstorming.

## CS-154 — Optical visual UX

**Priority:** P1  
**State:** PROVE

**Acceptance**

- inactive emitters visually disappear;
- active red does not create tacky outward spectacle;
- outward leakage characterized;
- ability to use phone/laptop/TV during optical stage validated or restricted honestly.

## CS-155 — Optical placement in routine

**Priority:** P1  
**State:** SELECTED / PROVE

**Starting direction:** after rinse, before final leave-on layers.

**Acceptance**

- confirm sequence does not create conflict with specific loaded products;
- preserve clean-skin optical field;
- routine editor automatically positions optical stage where required.

---

# 19. Phase 16 — leave-on application

## CS-160 — Non-wiping application state

**Priority:** P0  
**State:** PROVE

**Acceptance**

- application interface no longer behaves like cleansing contact;
- deposited film is not broadly removed by later device motion;
- transition is repeatable across fit variation.

**Convergence acceptance, 2026-09-10**

- Consume CS-018. Retraction of massage islands is insufficient if stationary treatment surfaces or support contacts still obstruct required leave-on regions.

## CS-161 — Thin-serum application

**Priority:** P0  
**State:** PROVE

**Acceptance**

- representative watery/low-viscosity serum applied without droplets entering eyes/mouth/nostrils;
- coverage uniformity threshold defined;
- no obvious pooling/streaks after removal.

## CS-162 — Gel/shear-thinning serum application

**Priority:** P1  
**State:** PROVE

**Acceptance**

- characterize materially different flow behavior;
- application profile adapts without user technical input;
- no clogging/patchy deposit inside representative envelope.

## CS-163 — Moisturizer/lotion application

**Priority:** P0  
**State:** PROVE

**Acceptance**

- representative lotion and cream/emulsion families applied evenly enough to require no manual spreading;
- loaded product retains its expected sensory character;
- no abnormal aeration/separation caused by device handling.

## CS-164 — Multiple leave-on layers

**Priority:** P0  
**State:** PROVE

**Acceptance**

- Layer A remains substantially present after Layer B application;
- sequence/settling requirements encoded;
- incompatible combinations blocked;
- no unbounded mixing in shared interface.

## CS-165 — Post-removal finish

**Priority:** P0  
**State:** HUMAN

**Acceptance**

- no required manual re-spread;
- no large wet patches;
- no unexpected dripping;
- no visible device imprints;
- tack/finish comparable to the user’s products when applied appropriately.

---

# 20. Phase 17 — facial SPF

## CS-170 — SPF regulatory/claims map

**Priority:** P0  
**State:** BLOCKED / PROVE  
**Evidence:** REG/CLAIM

**Acceptance**

- Australian/TGA and intended launch-market requirements mapped with qualified support;
- distinguish sunscreen product regulation from device application claims;
- public wording defined for pre-validation, validation and launch states.

**Convergence acceptance, 2026-09-10**

- Start the AM feasibility/claims/required-region review alongside the first surrogate transfer work. Keep SPF evidence distinct without delaying the AM existential question until later product freeze.
- An inert deposition proxy does not establish sunscreen protection or authorize human testing. If the intended SPF-containing AM routine cannot be validated, report an explicit AM scope blocker.

## CS-171 — SPF product-family compatibility

**Priority:** P0  
**State:** PROVE

**Acceptance**

- test representative sunscreen emulsions/fluids/mineral-heavy formulas;
- identify unsupported families explicitly;
- no assumption that one transport/application mode covers all SPF products.

## CS-172 — SPF final-film uniformity

**Priority:** P0  
**State:** PROVE

**Acceptance**

- final facial film measured spatially, not inferred from pump volume;
- difficult boundaries (nose, around eyes, hairline, mouth) mapped;
- repeat across fit/face variation;
- define undercoverage stop criterion.

## CS-173 — SPF application amount

**Priority:** P0  
**State:** PROVE

**Acceptance**

- application amount tied to validated coverage/claim method;
- individual face area/coverage handled credibly;
- no fake “2 mg/cm² achieved” claim without actual method/evidence.

## CS-174 — SPF eye/airway exposure

**Priority:** P0  
**State:** PROVE

**Acceptance**

- no direct aerosol-face assumption;
- product does not deposit unacceptable sunscreen in eyes, nostrils or mouth;
- misfit/failure states included.

## CS-175 — Facial-only completion wording

**Priority:** P1  
**State:** LOCKED

**Acceptance**

- UI says facial SPF/application state only;
- user guidance never implies ears/neck/body protection;
- sunscreen reapplication guidance follows validated product/regulatory requirements, not AI improvisation.

---

# 21. Phase 18 — release, retention and whole-head removal

## CS-180 — Non-wiping release path

**Priority:** P0  
**State:** INTEGRATE / PROVE

**Acceptance**

- leave-on film preserved through actual removal motion;
- no edge drags across cheeks/nose during realistic user removal;
- current retention/quick-release owner lineage reused.

**Convergence acceptance, 2026-09-10**

- Lane 3 owns the release geometry and continuous path; Lane 1 owns the required-region/final-film acceptance input. Use one shared contact map from CS-018, not two release architectures.

## CS-181 — Emergency release

**Priority:** P0  
**State:** INTEGRATE / PROVE

**Acceptance**

- ≤ existing 2 s target;
- one-handed/tactile;
- works without power/app/network;
- failure-safe;
- no requirement to preserve skincare film in emergency state over user safety.

## CS-182 — Normal release feel

**Priority:** P1  
**State:** PROVE

**Acceptance**

- deliberate low-force initiation;
- controlled unload;
- no spring snap or strap slap;
- no hair snag;
- repeatable premium tactile signature.

---

# 22. Phase 19 — hygiene, cleaning and service

## CS-190 — Inspectable facial interface

**Priority:** P0  
**State:** SELECTED

**Acceptance**

- user can visually inspect all meaningful skin-contact surfaces;
- no permanently wet dark cavities at the face boundary;
- removable/service surfaces have obvious orientation;
- “looks clean” correlates with actual cleanability plan.

## CS-191 — Routine dock clean/service cycle

**Priority:** P0  
**State:** PROVE

**Acceptance**

- define what is cleaned every return versus periodically;
- validate removal of representative cleanser/oil/sunscreen residues;
- no unsupported “self-sanitizing” claim;
- user intervention only when genuinely needed.

**Convergence acceptance, 2026-09-10**

- Include the intended products' residue families, water/service/waste inventory, inspectability, unknown hold times and changeover burden. A dry-looking or visibly clean part is not proof of hygiene. Qualified service evidence remains required.
- Preparation receipts must identify incomplete required service, even when quiet-night policy defers further activity.

## CS-192 — Dry-state management

**Priority:** P0  
**State:** PROVE

**Acceptance**

- no stagnant retained water in user-visible/critical zones over normal storage;
- drying/service time compatible with next scheduled routine;
- odor/microbial risks reviewed by qualified experts as needed.

## CS-193 — User-cleanable parts

**Priority:** P1  
**State:** EXPLORE

**Acceptance**

- determine which parts user can remove/rinse/wipe;
- low part count;
- no orientation puzzle;
- no frequent consumable replacement without real need.

## CS-194 — Waste service experience

**Priority:** P0  
**State:** INTEGRATE / PROVE

**Acceptance**

- premium blind insertion/removal;
- no leakage/drip/odor in expected handling;
- fill state understandable;
- existing cartridge owner lane remains canonical.

## CS-195 — Reject UV-cleaning theater

**Priority:** P2  
**State:** REJECTED

Do not add UV sterilization because it sounds premium/advanced. Only reopen if a specific contamination problem and validated optical sanitation architecture justify it.

---

# 23. Phase 20 — primary HMI and physical controls

## CS-200 — Primary button force-path correction

**Priority:** P0  
**State:** INTEGRATE / BLOCKED

**Known issue**  
Prior HMI work exposed a force-path contradiction between low-force spring/landing behavior and dome actuation requirements. Do not tune around the contradiction; topology must support the actual actuation force while preserving the desired tactile signature.

**Acceptance**

- selected physical topology has a credible force path;
- no coil bind/actuation contradiction;
- continuous motion/reference is valid;
- positive stop/overtravel/return resolved;
- physical force/travel/wobble/acoustics still validated separately;
- existing HMI PR/owner lineage reused.

**Convergence acceptance, 2026-09-10**

- The exact-head green HMI gate can correctly reject the selected force path. At the 2026-09-10 review, PR #144 preserves that rejection; do not interpret passing regression tests as a functional button. Let the existing owner correct the topology, not just tune a target force curve.

## CS-201 — Primary button tactile target

**Priority:** P0  
**State:** PROVE

**Acceptance**

- near-zero perceptible lateral play;
- smooth guidance;
- deliberate progressive resistance;
- clear event;
- dense landing;
- controlled return;
- no hollow click, metallic ping or rattle;
- stable across tolerance, contamination and temperature.

## CS-202 — Primary-control accessibility

**Priority:** P1  
**State:** HUMAN

**Acceptance**

- findable by touch while worn;
- one-handed actuation;
- cannot be confused with release control;
- no tiny flush touch target.

## CS-203 — Secondary controls policy

**Priority:** P1  
**State:** LOCKED

Avoid feature-specific physical buttons. Routine selection/configuration belongs mainly in app/dock; wearable remains physically simple.

---

# 24. Phase 21 — failure states and safety-facing UX

## CS-210 — Preflight readiness summary

**Priority:** P0  
**State:** SELECTED

**Acceptance**

Before start, system knows whether:

- required product present;
- prepared dose/routine matches selection;
- waste capacity sufficient;
- battery sufficient;
- fit/wear state adequate;
- mandatory subsystem available.

If not, user is told before fluid application where possible.

**Convergence acceptance, 2026-09-10**

- READY consumes the physical preparation receipt and current eligibility from CS-016. Separate unavailable optional modes from a missing required routine stage; do not require the user to read internal engineering state names.

## CS-211 — Calm service language

**Priority:** P1  
**State:** SELECTED

**Acceptance**

- plain-language next action;
- no sensor/error codes in primary UI;
- service state severity distinguishable without alarm colors alone;
- user never feels blamed for using an unsupported product.

## CS-212 — Early-removal recovery UX

**Priority:** P0  
**State:** PROVE

**Acceptance**

- stops safely;
- tracks completed stages;
- does not mark complete;
- gives only evidence-supported next action;
- prioritizes user safety over preserving the routine.

## CS-213 — Wrong-product event

**Priority:** P0  
**State:** PROVE

**Acceptance**

- unexpected physical signature halts before face application where possible;
- app/dock asks user to check refill;
- no automatic “AI correction” that guesses a new product.

## CS-214 — Low-resource planning

**Priority:** P1  
**State:** PROVE

**Acceptance**

- warnings arrive before the scheduled routine is blocked;
- user knows which product/service needs attention and by when;
- no push-notification spam.

## CS-215 — Offline/cloud failure

**Priority:** P0  
**State:** PROVE

**Acceptance**

- cached validated product/routine continues;
- cloud-only unknown-product enrichment waits;
- no unsafe downgrade;
- sync resolves later without duplicate session state.

---

# 25. Phase 22 — app, privacy and accessibility

## CS-220 — App role discipline

**Priority:** P0  
**State:** LOCKED

App is for configuration/history/identification/service, not a mandatory remote control for every session.

## CS-221 — Home screen redesign around “next routine”

**Priority:** P1  
**State:** SELECTED

**Acceptance**

Home answers:

- what routine is next;
- whether Masck is ready;
- which one action needs attention, if any;
- last completed routine.

Avoid generic IoT dashboard clutter.

## CS-222 — Product library UX

**Priority:** P1  
**State:** SELECTED

**Acceptance**

- show loaded products and confidence/support state;
- change/refill flow clear;
- no ingredient fear-mongering;
- no beauty scoring.

## CS-223 — Privacy defaults

**Priority:** P0  
**State:** LOCKED

No default face photos, acne/pore/wrinkle scores, always-on microphone or location tracking.

## CS-224 — Camera permission UX

**Priority:** P1  
**State:** SELECTED

Only request camera during deliberate product scan and state purpose clearly.

## CS-225 — Screen-reader/scalable text/contrast

**Priority:** P1  
**State:** PROVE

Meet platform accessibility guidance; all critical routine/product/service flows usable with assistive tech.

## CS-226 — Color-independent device semantics

**Priority:** P1  
**State:** PROVE

Light state has haptic/text/behavioral redundancy. Loading bays include tactile/shape cues.

## CS-227 — One-handed service study

**Priority:** P2  
**State:** HUMAN

Test pickup, start, normal release, return and common refill/service actions.

---

# 26. Phase 23 — ownership, durability and graceful ageing

## CS-230 — Durable vs replaceable map

**Priority:** P1  
**State:** SELECTED

**Acceptance**

- durable hero parts identified;
- hygiene/wear service parts justified by actual life requirement;
- no arbitrary recurring consumables purely for revenue;
- environmental/disposal implications considered.

## CS-231 — Battery service philosophy

**Priority:** P2  
**State:** EXPLORE

**Acceptance**

- product is not intentionally disposable when battery ages;
- service/repair path chosen before production freeze;
- ownership communications honest about battery life.

## CS-232 — Cosmetic ageing

**Priority:** P2  
**State:** PROVE

**Acceptance**

- representative shell/contact finishes exposed to oils, cleanser, sunscreen, hard water, humidity, cleaning, abrasion;
- staining/yellowing/scratch failure modes identified;
- product still reads premium after realistic use.

## CS-233 — Wet-use durability

**Priority:** P0  
**State:** PROVE

**Acceptance**

- cleaning/service cycles do not degrade seals/contact materials unexpectedly;
- user-facing wet interfaces survive life-cycle target;
- no odor/residue accumulation accepted as normal ageing.

---

# 27. Phase 24 — unboxing and onboarding

## CS-240 — Packaging hierarchy

**Priority:** P2  
**State:** EXPLORE

**Acceptance**

- mask and dock are immediately legible as the hero system;
- minimal accessory count;
- no medical tray aesthetic;
- no excessive single-use plastic;
- packaging protects premium finishes and facial interface.

## CS-241 — First-run fit

**Priority:** P1  
**State:** HUMAN

**Acceptance**

- user confirms correct size/setup once;
- placement taught quickly;
- emergency release learned before first active routine;
- no long calibration ritual.

## CS-242 — First product load

**Priority:** P1  
**State:** HUMAN

**Acceptance**

- user successfully identifies and loads each intended product without cross-slot error;
- unfamiliar terms avoided;
- unsupported product handled gracefully.

## CS-243 — Starter routine

**Priority:** P2  
**State:** EXPLORE

**Acceptance**

- onboarding can build from user’s existing routine rather than imposing a MASCK regimen;
- user confirms sequence;
- AI may help organize but not prescribe unsupported actives.

---

# 28. Phase 25 — travel and portability

## CS-250 — V1 portability proof

**Priority:** P1  
**State:** PROVE

**Acceptance**

- prepared wearable performs whole supported routine away from sink/bulk bottles;
- reasonable movement/use while worn defined;
- carrying case/protection requirements understood.

## CS-251 — Future travel-module interface reserve

**Priority:** P3  
**State:** EXPLORE

**Acceptance**

- home-dock/service architecture does not make a future compact travel preparer impossible;
- no need to build travel dock before V1 core product is proven.

## CS-252 — Reject “full home dock must be portable”

**Priority:** P3  
**State:** REJECTED

Do not inflate wearable/dock complexity by forcing every home service function into a travel form factor before evidence of need.

---

# 29. Phase 26 — explicit rejected feature register

These ideas came up in exploratory research or are common competitor traps. They are **REJECTED by default**.

## CS-R01 — Flexible silicone LED-mask archetype

**State:** REJECTED

Masck is not a floppy LED sheet pressed/hovered against the face.

## CS-R02 — VR-style headgear / rear counterweight pod

**State:** REJECTED

Balance must be solved with whole-system packaging/retention, not by turning Masck into a headset.

## CS-R03 — Coffee-machine/lab-appliance dock

**State:** REJECTED

Dock must remain a premium personal-care object and be pressure-tested for compactness.

## CS-R04 — Blue/green/red RGB status language

**State:** REJECTED

Use restrained Opal-neutral language with redundant warning semantics.

## CS-R05 — Voice assistant / talking mask / Alexa integration

**State:** REJECTED

No voice gimmicks or always-listening microphone as core UX.

## CS-R06 — “Extra serum” hardware button

**State:** REJECTED

Do not encourage arbitrary extra dosing outside validated routine profiles.

## CS-R07 — Beauty/skin score

**State:** REJECTED

No pore/acne/wrinkle/beauty score by default.

## CS-R08 — UV sanitation theatre

**State:** REJECTED unless a specific validated hygiene requirement reopens it.

## CS-R09 — Automatic blue-light acne mode

**State:** REJECTED unless independent claims/safety/product research creates a new decision.

## CS-R10 — Proprietary skincare lock-in

**State:** REJECTED

## CS-R11 — Visible front plumbing / clear lab channels

**State:** REJECTED

## CS-R12 — Decorative vents / technical panelization

**State:** REJECTED

## CS-R13 — Constant beeps/buzzes as treatment proof

**State:** REJECTED

## CS-R14 — Direct aerosol sunscreen assumption

**State:** REJECTED as default architecture.

## CS-R15 — Makeup-removal scope creep

**State:** REJECTED for V1 whole-routine definition.

---

# 30. Phase 27 — whole-product integration gates

## CS-270 — Integrated digital package

**Priority:** P0  
**State:** BLOCKED until major subsystem concepts converge  
**Evidence:** DIGITAL

**Acceptance**

- one current product assembly uses canonical owner outputs;
- no duplicate cartridge/retention/HMI/treatment/thermal truths;
- mass/CG includes full-routine additions;
- protected anatomy/airway checks remain green;
- all speculative/reference geometry separated from manufactured material;
- per-component provenance and source binding retained.

## CS-271 — Complete routine digital state/geometry review

**Priority:** P0  
**State:** BLOCKED

**Acceptance**

For every routine phase, show:

- what touches/approaches skin;
- protected eye/mouth/nostril state;
- what fluid/product is present;
- which component moves/retracts at concept level;
- removal-ready condition;
- no impossible cross-phase collision/occupancy assumptions.

**Convergence acceptance, 2026-09-10**

- Review all contact shadows and structural support through CLEAN, RECOVER, optional treatment, layered application, SETTLE and normal/emergency release. Reference material identities and routine-state contracts must agree at the same source head.

## CS-272 — Full-system physical alpha

**Priority:** P0  
**State:** BLOCKED on CS-010/050/053/121/160 etc.  
**Evidence:** BENCH + HUMAN

**Acceptance**

- full-face placement/secure/start/routine/release/return demonstrated;
- selected representative routine completes autonomously;
- no manual face touch required afterward;
- airway, leakage, comfort and rapid release satisfy current evidence targets;
- limitations documented.

## CS-273 — Premium-feel alpha gate

**Priority:** P1  
**State:** BLOCKED

**Acceptance**

- button, retention, dock settlement, service cartridge and face transition show consistent tactile character;
- no cheap rattle/scrape/chatter;
- acoustics acceptable in intended environment;
- exterior/contact CMF survives repeated wet handling.

## CS-274 — Product truth review

**Priority:** P0  
**State:** recurring gate

Before any public/pitch/website claim:

- separate digitally complete from physically validated;
- separate benchmark target from achieved performance;
- separate concept intent from released capability;
- remove simulated metrics from production presentation.

---

# 31. Phase 28 — validation and claims gates

## CS-280 — Human-factors protocol

**Priority:** P0  
**State:** BLOCKED until safe physical alpha

Cover:

- placement success;
- first-10-second comfort;
- routine-duration comfort;
- vision/use activities;
- airway perception;
- release success;
- post-removal face feel;
- preference to reuse;
- service/loading error rate.

## CS-281 — Skin/barrier protocol

**Priority:** P0  
**State:** BLOCKED until appropriate ethics/expert/safe prototype path

Do not improvise clinical protocol from chat. Use qualified expertise and appropriate oversight.

## CS-282 — Optical validation protocol

**Priority:** P1 if optical in V1  
**State:** BLOCKED until optical architecture selected

Validate actual wavelength/dose/uniformity/thermal/eye-safety performance before claims.

## CS-283 — SPF validation protocol

**Priority:** P0 if SPF in V1  
**State:** BLOCKED until deposition architecture stable

Validate final application/coverage using appropriate regulatory/claims-quality methods. Volume alone is insufficient.

## CS-284 — Cleaning/hygiene validation

**Priority:** P0  
**State:** BLOCKED until service architecture stable

Demonstrate residue removal/drying/cleanability and appropriate hygiene behavior over repeated real product use.

---

# 32. Phase 29 — product/commercial usability gates

## CS-290 — Concept comprehension

**Priority:** P1  
**State:** PROVE

Users should understand in seconds:

> Masck performs my facial skincare routine for me.

If users primarily describe it as “an LED mask” or “electric face washer,” positioning/feature hierarchy has failed.

## CS-291 — Routine value proof

**Priority:** P0  
**State:** PROVE

Measure whether target users value:

- time saved;
- consistency;
- portability;
- not touching/applying products manually;
- use of existing skincare;
- premium experience.

Do not assume skincare enthusiasts want automation merely because they buy devices.

**Convergence acceptance, 2026-09-10**

- Evaluate total daily/weekly active attention, including loading, service, product waste, failures, manual starting-state prerequisites and wear inconvenience. Compare actual supported routines, not only the automatic wearing interval. Predeclare the meaningful value criterion before selection.

## CS-292 — Price research

**Priority:** P2  
**State:** EXPLORE

Use real concept/prototype studies; do not freeze A$799/A$999 from competitor prices alone.

## CS-293 — Product compatibility coverage target

**Priority:** P0, G0/G4\
**State:** EXPLORE

Define launch threshold for number/share of target-market products with validated profiles so “works with your skincare” is credible.

**Convergence acceptance, 2026-09-10**

- This is an early existential feasibility gate, not just later launch marketing. Define a representative target-user product/routine cohort before selecting the easiest compatible formulations.
- Report unsupported starting states, brands/formulation versions and complete sequences. Material narrowing toward proprietary formulations or recurring manual facial finishing requires explicit concept review.

---

# 33. Phase 30 — production-intent refinement after concept proof

This backlog intentionally does not deeply prescribe mechanics. Once the existential UX/product proofs above are green, engineering should refine:

## CS-300 — Material qualification

**Priority:** P0 later  
**State:** BLOCKED on selected surfaces/chemistry  
**Evidence:** SUPPLIER + BENCH

## CS-301 — Tolerance appearance and tactile robustness

**Priority:** P0 later  
**State:** BLOCKED  
**Evidence:** DIGITAL + BENCH + SUPPLIER

## CS-302 — DFM/assembly/service strategy

**Priority:** P0 later  
**State:** BLOCKED

## CS-303 — Supplier/component validation

**Priority:** P0 later  
**State:** BLOCKED

## CS-304 — Reliability/lifetime program

**Priority:** P0 later  
**State:** BLOCKED

## CS-305 — Regulatory/compliance plan

**Priority:** P0 later  
**State:** BLOCKED on final claims/markets

These are not reasons to postpone concept validation; they are the next layer after the product experience is shown to work.

---

# 34. Master dependency order

Section numbers above group topics; they are not a waterfall implementation schedule. The earlier sequence that placed surface/CMF work before session isolation, final-film proof and SPF feasibility is superseded by this dependency order.

1. **G0: completion domain and representative compatibility.** CS-015/014/080/094/291/293 define what success must cover. Preserve CS-000..004.
2. **G1: reduced off-face transfer evidence.** CS-010/012/013/121/160..165 use that domain and predeclared measurement criteria.
3. **G2: whole-face contact/support/release.** CS-018/050/180/181/271 run alongside G1. Reduced-region success is necessary evidence, not sufficient whole-product proof.
4. **G3: preparation, preservation and readiness.** CS-016/017/095/112/113/191/210 run in parallel and can reject an otherwise attractive face-side topology.
5. **G4: joint package and ownership feasibility.** CS-053/070/100/108/110/142/291/293 constrain all candidate architectures from the start.
6. **G5: AM SPF feasibility.** CS-170..175 start alongside G0/G1 with qualified evidence ownership. Distinct assays do not make this a deferred optional AM requirement.

Only after those conflicts are bounded should the broader fit, sensory, interface, optional-modality, service-life and manufacturing work consume major new refinement effort. Their constraints apply now; their detailed polish does not outrank existential proof.

# 35. Immediate top queue

**New primary work:** CS-015 required-region contract, CS-018 all-contact map, and the CS-010/013 off-face evidence plan. In parallel, specify CS-016 prepared-session validity and CS-017 preservation requirements. Activate each only with one named owner artifact and exact consumed interfaces.

**Parallel architecture screens:** CS-053/110 joint budgets, CS-291/293 representative routine value/compatibility, and CS-170 AM feasibility. Do not postpone these until after optional feature or exterior freeze.

**Allow existing owners to finish bounded defects:** treatment exact-collision verification, HMI force-path correction, cartridge DFM source binding, dry-side hostile rejection checks, and current retention trajectory/attachment evidence. Preserve canonical branches and exact-head results. These are enabling repairs, not permission to freeze the expanded product.

**Defer discretionary work:** new modalities, additional cosmetic surface variations, sound tuning, broad app screens, travel dock, and final whole-product Fusion packaging until their upstream questions are bounded. No tactile, protected-anatomy, cost, privacy or physical-validation requirement is weakened by this ordering.

See [the convergence review](CORE_SKETCH_CONVERGENCE_REVIEW.md) for contradictions and explicit kill/pivot conditions, and [the repository map](CORE_SKETCH_REPO_MAPPING.md) for observed owners and failure scopes.

---

# 36. How future agents should use this file

When receiving a broad instruction such as “perfect Masck,” “continue,” “work on the next important thing,” or “improve the whole product”:

1. fetch live GitHub state;
2. read this file and `CORE_SKETCH_V1.md`;
3. use the G0..G5 dependency order to select a bounded non-DONE item; preserve an existing owner, or reserve exactly one owner artifact for genuinely unowned work;
4. continue that owner lineage;
5. perform actual engineering/design/validation work;
6. commit meaningful checkpoint(s);
7. update the relevant backlog item status/notes only when evidence warrants it;
8. do not create a new feature simply because all currently obvious implementation work is inconvenient;
9. do not mark physical feel, skin response, optical safety, SPF performance or hygiene validated from digital geometry alone;
10. leave the product more coherent than you found it.

The backlog is intentionally broader than any single sprint. It is the bridge between the stable product sketch and detailed engineering execution.
