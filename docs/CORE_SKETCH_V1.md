# MASCK ONE Core Sketch v1

Status: **selected product-experience concept; not engineering authority**  
Date: 2026-09-10  
Purpose: define the durable product that engineering, industrial design, software and validation work should converge toward. Later work may refine dimensions, mechanisms, materials, timings and implementation details, but should not casually change the product promise, experience hierarchy or visual/interaction character defined here.

## 0. Authority boundary

This document is a **core sketch**, not proof that any physical behavior already works.

The following remain controlling for engineering truth:

1. `config/masck_one_authority.yaml` and its schema;
2. released source/CAD and canonical component registry;
3. accepted physical-validation evidence;
4. engineering governance and evidence firewalls.

Where this document specifies a desired behavior not yet proven, it is a **CONCEPT TARGET / PHYSICAL VALIDATION REQUIRED**. Future work must not weaken existing safety, anatomy, collision, mass, airflow, leakage, force, thermal or evidence requirements merely to match the sketch.

Research archive: `docs/research/CORE_SKETCH_DEEP_RESEARCH_2026-09-10.md`.

Execution program: `docs/CORE_SKETCH_EXECUTION_BACKLOG.md`.

---

# 1. Product definition

MASCK ONE is a **complete automated facial-skincare system**.

It is not primarily an LED mask, cleansing brush, fluid dispenser, massage device, smart wearable or app accessory. Those are capabilities inside the system.

The product hierarchy is:

**COMPLETE FACIAL ROUTINE**  
→ cleaning  
→ rinse/recovery  
→ treatment  
→ leave-on application  
→ facial protection  
→ clean non-wiping release.

The core consumer promise is:

> **Put on Masck One. Start. Continue with your life. Remove it when finished. Your supported facial skincare routine is complete.**

The corresponding internal rule is:

> **When Masck One comes off, the user should not need to touch their face again to complete that facial skincare routine.**

This rule is non-negotiable for the intended product. If physical validation ultimately proves that a key supported facial step cannot be automated safely and well, the concept must be reconsidered rather than quietly degraded into “automated cleanser plus manual skincare.”

## 1.1 What “complete” means

For supported routines, Masck One should be able to execute, as applicable:

- facial cleansing;
- fresh-water rinse and spent-fluid recovery;
- optional massage/physical treatment;
- optional deliberate WARM or COOL treatment;
- optional optical red / near-infrared treatment;
- one or more leave-on treatment/serum/essence steps;
- moisturizer;
- facial sunscreen in an AM routine when the loaded product and application profile are validated;
- a final transition and removal state that does not wipe away the leave-on layers.

Not every routine contains every stage. The product executes the **user’s saved routine**, not a fixed “all features every time” program.

## 1.2 Explicit boundary: makeup and decorative cosmetics

V1’s complete-routine promise is for **facial skincare**, not decorative cosmetics.

Automatic removal of waterproof eye makeup, mascara, foundation or other decorative cosmetics is not part of the frozen V1 promise unless separately validated later. The product should never imply that “whole routine” includes every cosmetic preparation a user may wear.

## 1.3 Explicit boundary: sunscreen coverage

Masck may eventually apply **facial sunscreen** within a validated facial coverage region. It must not imply that this replaces sunscreen required on the ears, neck, scalp, lips, body or other exposed areas.

“Facial SPF applied” may become a supported completion state only after the application process itself is validated. Dispensed volume alone is not proof of achieved protection.

---

# 2. Product character

The design thesis is:

> **CALM OUTSIDE. EXCEPTIONALLY ENGINEERED INSIDE.**

Masck One should feel like an advanced premium personal-care object whose sophistication is discovered through use rather than advertised through exposed technology.

It must not read as:

- VR/XR hardware;
- medical PPE or a respirator;
- a robotic face;
- tactical equipment;
- cyberpunk/gaming hardware;
- an LED mask with fluidics attached;
- an appliance miniaturized onto the face.

From across a room, the product should read as one calm, continuous facial volume with large intentional eye openings and a refined sculptural relationship to the nose, cheeks and lower face.

The outside should be quieter than the inside.

---

# 3. Stable system architecture

The consumer system has three primary surfaces.

## 3.1 Masck One wearable

The wearable performs the routine. It carries only the resources required for the prepared session plus the hardware necessary to execute it.

The wearable should not carry full retail quantities of skincare. The number of products a user owns must not scale linearly into excessive on-head mass.

## 3.2 Masck Dock

The dock is the ownership and preparation centre. It stores bulk skincare, accepts returned waste/service loads, charges the wearable, prepares the next routine, manages routine service and communicates readiness.

The dock should make complexity disappear rather than transfer appliance maintenance to the user.

## 3.3 Masck companion software

The companion app is for setup, product identification, routine creation/scheduling, history, service guidance and deliberate configuration.

It is **not required for ordinary configured use**.

Normal use must remain:

**pick up → place → start → remove → return**

without requiring a phone, cloud connection, account authentication or internet access.

---

# 4. Core use journey

## 4.1 Prepared state

The dock already knows the next scheduled routine and whether the required products are present and usable. It has prepared the wearable’s session quantities before the user reaches for it.

The user should never begin their morning by programming pumps, selecting fluid channels or waiting for a complex setup sequence.

Target user-facing state:

> **Ready for Morning Routine**

or, on the device itself, a restrained ready indication with no text required.

## 4.2 Pickup

As the user approaches or lifts Masck One:

- the dock may wake visually with a restrained Opal acknowledgement;
- the wearable releases cleanly from the dock without cable handling;
- no flap, dangling tube, exposed wet connector or awkward latch should interrupt the gesture;
- the user can understand orientation immediately from shape and tactility.

The pickup should feel closer to lifting a premium personal object from its stand than removing equipment from a charging station.

## 4.3 Placement

The desired placement experience is:

**GRAB → PLACE → SELF-ALIGN → SECURE**

The user should not perform a VR-style multi-strap adjustment ritual.

The product should guide itself into a repeatable facial position through its geometry and compliant interfaces. Retention should resolve into a clear, stable state with minimal user manipulation.

The first ten seconds should communicate:

- orientation is obvious;
- the product settles rather than clamps;
- the airway feels unquestionably open;
- the eyes remain visually usable;
- no sharp local pressure appears;
- hair is not being trapped or pulled;
- the product does not feel front-heavy;
- the user understands when placement is complete.

Fit quality is a PHYSICAL VALIDATION REQUIRED target.

## 4.4 Start

One primary physical control starts the prepared routine.

The primary control must remain usable without the app and should be operable with one hand while worn.

The interaction character is:

- dense rather than hollow;
- very low perceptible wobble/free play;
- exactly constrained intended motion;
- smooth guidance;
- deliberate progressive resistance;
- clean state transition;
- positive seating;
- controlled unloading/return;
- no metallic ping;
- no rattling, scraping, spring twang, hollow impact or cheap overtravel.

The S.T. Dupont Ligne 2 is only a reference for **perceived mechanical precision**. Its sound, exact mechanism, materials, styling and brand behavior must not be copied.

## 4.5 During the routine

The user may continue quiet, low-risk activities such as:

- working at a desk;
- reading if the eye architecture permits comfortable focus;
- watching television;
- using a phone/laptop;
- walking slowly around a familiar indoor space if validated safe.

Masck should not market use while driving, exercising vigorously, cooking over heat/flames, showering, sleeping or performing activities requiring unrestricted peripheral vision.

Drinking while worn is not a target use case unless a later mouth/retention study specifically validates it.

## 4.6 Completion and removal

Completion should be obvious but calm.

The interface should enter a final state in which active skin-contact/application surfaces no longer wipe across the freshly applied leave-on layers.

The user releases/removes the product in one controlled motion. Target removal time remains consistent with the existing rapid-release requirement.

After removal the face should ideally feel:

- clean;
- comfortable;
- evenly conditioned;
- not dripping;
- not unexpectedly tacky beyond the behavior of the user’s own loaded products;
- not unusually hot;
- free of strong pressure marks;
- complete, with no required manual facial skincare step remaining.

These are PHYSICAL VALIDATION REQUIRED experience targets.

## 4.7 Return

The user places Masck One back onto the dock.

Desired choreography:

**approach → self-locate → soft positive settlement → tiny acknowledgement → user walks away**

The user should not connect a cable, drain a hose, remove a wet bag or run a cleaning menu after ordinary use.

The dock then handles its service/preparation sequence outside the user’s attention wherever possible.

---

# 5. Routine state model

The stable concept sequence is:

**CLEAN → RINSE/RECOVER → TREAT → LEAVE-ON APPLICATION → PROTECT → RELEASE**

A more explicit full-capability routine may be:

**CLEAN → RINSE/RECOVER → MASSAGE/WARM/COOL and/or OPTICAL → SERUM/TREATMENT 1 → SERUM/TREATMENT 2 → MOISTURISE → FACIAL SPF → SETTLE → NON-WIPING RELEASE**

Stages are optional according to the saved routine and validated product rules.

## 5.1 CLEAN

Experience goal: controlled cleansing that feels purposeful but gentle.

The user may perceive subtle treatment motion and fluid presence, but the product must not rely on aggressive vibration or audible buzzing to create “proof of action.”

The cleansing stage should feel distributed rather than like isolated motors pressing on the face.

Historical treatment references such as four zones, ~40 Hz, ~0.52 mm peak-to-peak and associated force limits remain engineering/evidence inputs rather than visual UX requirements here.

## 5.2 RINSE / RECOVER

Experience goal: the face transitions from “being cleansed” to “clean and ready for treatment.”

The user should perceive a clean transition without uncontrolled dripping, suction sensation, gurgling or fluid slosh.

The system should not leave cleanser mixed into later leave-on products.

Historical water, cleanser, post-flush, recovery and leakage targets remain engineering constraints.

## 5.3 TREAT

TREAT may include one or more compatible validated treatment modalities, but the core sketch intentionally resists feature accumulation.

Selected treatment families are:

- massage/controlled physical treatment;
- deliberate WARM;
- deliberate COOL;
- red / near-infrared optical treatment.

A routine should include a treatment because the user chose or scheduled it, not because the product needs to demonstrate every capability every session.

## 5.4 SERUM / LEAVE-ON TREATMENT

Experience goal: precise, even application of a user-selected leave-on product without the cleansing interface subsequently removing it.

The user should not feel sprayed in the face, experience droplets near the eyes/airway, or need to manually spread patches after removal.

Exact deposition method remains open engineering/R&D.

## 5.5 MOISTURISE

Experience goal: final conditioning layer applied evenly with no obvious streaks or pooling.

The system should respect the loaded product’s normal sensory character rather than transform it into a generic “Masck feel.”

## 5.6 FACIAL SPF

Experience goal: a validated, even facial application with clear completion confidence and no implication of body-wide protection.

The system must not use aerosol-style direct face spraying as a default merely because it is mechanically convenient. Eye/airway exposure, film uniformity, product chemistry and relevant regulation must control the eventual approach.

## 5.7 SETTLE

Where a loaded product requires a short settling period before another layer or removal, Masck should include it automatically. The user should not have to know the reason or count seconds.

## 5.8 RELEASE

The product transitions from treatment/application geometry to a removal-ready state that preserves final leave-on layers.

The final release is part of skincare performance, not merely a retention feature.

---

# 6. Phase differentiation without activity theatre

Each stage should feel meaningfully different through the real physical behavior of that stage, while the UI remains restrained.

The sensory hierarchy is:

1. **real treatment sensation first**;
2. **subtle haptic confirmation second**;
3. **restrained light state third**;
4. **sound only when it materially improves comprehension or safety**.

Masck must not add warmth, vibration, beeps, flashes or fake motor sounds simply to reassure the user that “something is happening.”

---

# 7. Visual archetype and form language

## 7.1 Overall silhouette

Historical outer reference: approximately **172 × 210 mm XY**. This remains a useful starting envelope, not a frozen cosmetic dimension.

The face should read as one continuous premium volume rather than a frame containing many modules.

Key priorities:

- perceived thinness around the visual perimeter;
- calm central facial volume;
- large clean eye openings;
- no eye bezels or raised goggle rings;
- no fake vents;
- no arbitrary panelization;
- no visible actuator pods;
- no technical ornament pretending to be function;
- soft but controlled cheek-to-temple flow;
- lower-face termination that avoids respirator/muzzle cues;
- nasal form integrated into the whole rather than a protruding nose cone.

## 7.2 Eyes

Historical rigid opening direction before cant: about **63 × 47 mm**, with historical protected aperture references around **46 × 30 mm** and eye centers near **X=±31.5 mm, Y=+35 mm**. Exact released geometry remains governed by engineering authority.

Visual targets:

- thin-looking inner edge;
- approximately 3 mm class inner roll as a design-language reference where compatible with engineering;
- subtle eye cant rather than aggressive angled “eyes”;
- no contrasting ring around the openings;
- aperture surfaces should appear carved into the continuous shell rather than assembled as goggles.

## 7.3 Nose / central face

The nose region should read as anatomically considerate and calm, with airway function clearly respected but not visually dramatized.

No respirator grille, fake intake, nose cone or black technical insert should dominate the front view.

## 7.4 Mouth / lower face

The mouth opening remains functionally real and visually clean. Historical reference is approximately **58 × 32 mm** centered near **Y=-50 mm**.

The lower-face perimeter should avoid “jaw armor.”

## 7.5 Temple / primary control

The control should be discoverable through placement and tactility, not made visually loud. It is a signature detail only at close range.

Warm Porcelain differentiates it subtly from the Mineral Ivory shell.

## 7.6 Rear / retention

The rear architecture should be compact and visually subordinate to the face.

Do not solve balance by turning the product into a VR halo or hanging a conspicuous counterweight behind the skull.

Retention should visually disappear into the overall object as much as practical.

## 7.7 Seams

Permitted seams should correspond to genuine service/manufacturing boundaries and be choreographed with form transitions.

Forbidden seam behaviors:

- seam rings around the eyes;
- arbitrary “tech panels” on the front face;
- multiple short intersecting panel lines;
- decorative gaps with no service/manufacturing purpose;
- uneven visible gaps that imply cheap snap-fit construction.

## 7.8 Edge and highlight language

Exterior highlights should roll smoothly and continuously. The object should not use razor-sharp consumer-electronics chamfers on skin-adjacent geometry, nor over-soft toy-like radii.

The product should have a controlled family of radii rather than one global fillet value. Exact radii are to be refined through ID/CAD.

---

# 8. CMF and surface character

Selected concept palette:

- **Mineral Ivory `#E9E5DC`** — primary exterior shell;
- **Warm Porcelain `#DED9CF`** — primary user control / selected tactile detail;
- **Soft Stone `#CFC8BC`** — skin-adjacent compliant/contact material;
- **Smoke Graphite `#454542`** — rear/mechanical regions that genuinely benefit from visual recession;
- **Opal Neutral `#F2EFE7` unlit** — optical/status element.

These colors define visual intent, not qualified production pigments.

## 8.1 Exterior finish

Target character:

- satin-matte rather than dead chalky matte;
- soft, broad highlights;
- low fingerprint visibility;
- premium dry touch;
- no rubberized soft-touch coating that becomes sticky with age;
- no high-gloss “medical white” front shell;
- no fake metal paint.

## 8.2 Skin-contact material

Target character:

- soft but not gummy;
- low tack against clean skin;
- non-absorbent;
- visually inspectable;
- easy to wipe/rinse where user service is expected;
- resistant to staining from common skincare;
- no textile foam exposed to wet product paths.

Specific material family/grade remains a qualification task.

## 8.3 Branding

- MASCK is the master brand.
- M-Cut remains the provisional master mark.
- M/1 is the compact product designation.
- Aperture Mark is the micro-mark associated with the primary control.

Branding should be sparse enough that the product can sit on a bathroom counter without reading as promotional merchandise.

No repeated “MASCK” wordmarks across visible surfaces.

---

# 9. Fit and sizing philosophy

Selected direction: **limited size family + strong passive/adaptive fit**, not fully custom fabrication and not “one rigid shape fits everyone.”

Concept target:

- approximately 2–3 primary face-size families if validation requires it;
- within each size, compliant geometry and retention accommodate normal facial variation;
- sizing is resolved once during onboarding/purchase;
- ordinary use thereafter requires no repeated fitting ritual.

The final number of sizes remains validation-dependent.

## 9.1 Placement behavior

The user should not manage five independent straps/tension points.

Desired experience:

**place → small automatic/self-guided settling motion → secure state**.

Any adjustment that remains should be infrequent and visually hidden.

## 9.2 Weight and balance

Existing historical goals remain important anchors:

- dry mass ≤ ~215 g;
- loaded mass < ~255 g;
- CG Z ≤ ~30 mm;
- wearer torque ≤ ~0.070 N·m.

The full-routine concept makes **session-dose architecture** mandatory because leave-on products must not destroy these ergonomic targets.

The user should experience the product as close to the face, stable and balanced, not as a shell pulling forward from the cheeks/nose.

---

# 10. Vision, eyes and ordinary activity

Masck should preserve useful forward vision through the large eye openings.

Product target:

- comfortable laptop/phone/TV viewing for many users;
- enough peripheral awareness for careful movement around a familiar indoor environment;
- no requirement to close the eyes throughout ordinary non-optical stages;
- no clear lens or visor across the entire eye opening unless a future safety requirement forces it.

During optical treatment, the system must respect the actual eye-safety architecture and may restrict visual behavior if needed. The product should explain such restrictions simply.

Glasses compatibility is a dedicated validation track. The concept should aim either to accommodate common slim frames safely or provide a clearly acceptable alternative use state, rather than assume all users remove corrective lenses without consequence.

---

# 11. Hair, ears, jewelry and facial variation

The stable product experience should account for real bathroom use:

- long hair should be able to sit outside the primary retention path without being pinched;
- placement should not require perfect hair preparation;
- common small earrings should ideally remain clear of the product;
- larger/hoop earrings may need a documented remove-before-use boundary;
- common ear piercings should not sit under a hard moving retention contact;
- facial hair in beard/moustache regions may alter cleansing/application and must be explicitly studied rather than assumed equivalent to bare skin;
- the interface should tolerate reasonable variation in nose projection, cheek prominence, jaw width and brow structure.

---

# 12. Sensory grammar

Masck needs one coherent language across wearable and dock.

## 12.1 Light

Default language: **Opal Neutral**, not RGB mode colors.

Light should appear integrated into material rather than as a visible LED strip.

Recommended semantics:

- **off / invisible:** asleep or no reason to communicate;
- **soft steady Opal:** ready / healthy / prepared;
- **slow restrained Opal movement:** preparing, servicing or transitioning;
- **brief Opal acknowledgement:** command accepted / successful docking;
- **reduced or absent light:** active routine when additional light would be distracting;
- **clear but still restrained warning behavior:** attention needed;
- **safety-critical alert:** allowed to become more salient than the normal brand grammar.

Do not use blue=clean, green=done, red=error as the normal consumer language. Color must not be the only carrier of meaning.

## 12.2 Haptics

Haptics are for state confirmation, not entertainment.

Potential uses:

- primary-control acceptance;
- fit/secure confirmation if physically meaningful;
- routine completion;
- safety-interlock notification.

Haptics should not buzz continuously through stages merely to prove operation.

## 12.3 Sound

Normal operation should be quiet enough for a bedroom or calm bathroom environment.

Desired character:

- no startup jingle;
- no spoken prompts from the mask;
- no repeated chirps for phase transitions;
- no intentional mechanical ping;
- no loud pump/gurgle/slosh cues;
- no “medical monitor” beeping;
- completion sound, if retained at all, should be optional, extremely restrained and unnecessary when haptic/light cues are available.

The best normal sound is often **nothing**.

## 12.4 Motion

Visible/mechanical motion should feel controlled and purposeful:

- smooth onset;
- no sudden face slap;
- no uncontrolled snap;
- resolved endpoint;
- controlled return;
- no chatter;
- no perceptible loose mechanism continuing after the state is reached.

---

# 13. Optical treatment

Optical treatment is a capability inside the complete routine, not the product identity.

## 13.1 Benchmark direction

CurrentBody-class consumer systems provide a useful market benchmark for red / near-IR / deeper near-IR treatment, including public wavelength examples around:

- ~633 nm red;
- ~830 nm near-infrared;
- ~1072 nm deeper near-infrared.

These wavelength values are **research benchmarks**, not a frozen Masck architecture. Masck must independently establish the wavelengths, dose, irradiance, uniformity, session duration, thermal behavior and safety appropriate to its claims.

The competitor’s LED count is irrelevant as a target. Masck should optimize delivered optical field, not clone a count or PCB arrangement.

## 13.2 Inactive appearance

When optical treatment is off:

- individual emitters should not dominate the inner visual field;
- no dotted “LED costume” should be visible from normal viewing distance;
- optics should feel integrated into the facial architecture.

## 13.3 Active experience

Visible red light may be perceptible, but the experience should remain controlled rather than turning the user into a glowing novelty object.

The design should minimize unnecessary outward light leakage while preserving the treatment field and eye safety.

The user should know whether normal visual tasks are permitted during the optical stage. If eyes must remain closed or a particular task is unsafe, the system should state that clearly rather than infer compliance.

## 13.4 Optical timing in the routine

Default concept order is optical treatment on cleansed skin **before final leave-on layers**, unless later evidence supports another sequence for a specific validated routine.

---

# 14. Deliberate WARM / COOL

Thermal treatment must be intentional.

## 14.1 WARM

WARM should feel:

- gentle;
- even;
- controlled;
- deliberate;
- responsive;
- free of hot spots.

It must not feel like electronics/battery heat leaking into the face.

## 14.2 COOL

COOL should feel calm and controlled, not startlingly cold or wet-condensing.

The concept does not require a specific refrigeration architecture.

## 14.3 Incidental heat rule

Outside a deliberate WARM state, the user should not interpret device self-heating as a treatment feature. Uncontrolled face-adjacent warmth is a defect, not “proof it is working.”

---

# 15. Product loading

Loading skincare into Masck should be an occasional ownership task, not part of each routine.

## 15.1 Desired loading flow

**Choose slot → identify product → confirm exact product/version → load → close → system checks → Ready.**

The app may support:

1. scan barcode/QR;
2. camera recognition of front/back label;
3. OCR brand/product/variant;
4. manual search fallback;
5. ingredient/formulation confirmation where needed.

The dock then knows what is physically assigned to each product bay.

## 15.2 Product identity is separate from fluid behavior

Masck should never pretend that looking at an anonymous liquid proves its identity.

Identity comes primarily from the user’s loading action and product metadata.

Physical sensing/calibration answers a different question:

> “Does the material in this path behave consistently with the product/profile we expect?”

That can help detect a wrong refill, changed formula, clog or other mismatch.

## 15.3 Slot experience

The consumer should not see “Valve 3” or “Reservoir Channel B.”

Slots are associated with understandable roles/products in software, while physical geometry should provide tactile and visual mistake resistance.

Color alone must never determine correct loading.

## 15.4 Product changing

Changing a product should be explicit:

**Change product → identify new product → system confirms whether path/service change is needed → load → verify → available for routines.**

The system should not silently assume that the same bottle identity remains forever.

---

# 16. Product database

Masck’s long-term compatibility system is a product/application database, not a generic AI guess engine.

Conceptual product profile:

`PRODUCT IDENTITY + FORMULATION VERSION + ROLE + ROUTINE RULES + APPLICATION FAMILY + DOSE RANGE + DELIVERY CONSTRAINTS + COVERAGE + SETTLING/TIMING + TEMPERATURE LIMITS + COMPATIBILITY/INTERACTION RULES + EVIDENCE STATE`

## 16.1 Internal evidence states

Use four core internal states:

### KNOWN
Exact identity is resolved but application behavior may not yet be sufficiently characterized.

### CHARACTERISED
Masck has enough product/application behavior information to model or calibrate delivery within a bounded envelope, but this does not automatically equal validated consumer use.

### VALIDATED
The product/application profile has passed the evidence standard required for its supported use.

### RESTRICTED / UNSUPPORTED
The current system should not automatically apply it.

## 16.2 Community learning

When users encounter the same product, aggregate non-sensitive application telemetry may improve characterization if the user has opted into such contribution.

However:

> **Popularity is not validation.**

A thousand uneventful community uses do not automatically promote a safety-critical sunscreen/active to VALIDATED.

## 16.3 Reformulation

Product identity should eventually distinguish as needed:

**brand + product + SKU/market + formulation/version**, with batch/lot information where relevant.

If packaging/ingredients materially differ from the known profile, the system should treat it as a possible reformulation and return to a conservative state.

---

# 17. Unknown-product flow

When the user scans a product Masck does not recognize:

1. Masck attempts exact identity resolution from barcode/label/search/ingredients.
2. If identity remains uncertain, it asks the user to confirm rather than guessing silently.
3. It classifies the product’s likely routine role and physical family only within bounded categories.
4. The dock may perform a small controlled flow/application-characterization check.
5. The product is assigned an evidence state.
6. Only if the state allows use does it become available in routine building.

User-facing language should be calm and nonjudgmental.

Prefer:

> **Masck hasn’t characterised this product yet.**

over:

> **Bad product / incompatible skincare.**

When something cannot be used:

> **This product isn’t supported for automatic application yet.**

---

# 18. AI role

AI may help Masck understand and organize skincare, but it does not own safety.

## 18.1 Appropriate AI uses

- resolve product names/variants from packaging images;
- interpret ingredient lists/manufacturer instructions;
- classify product role/type;
- map an unknown product toward an existing application family;
- assist users in arranging their own routines;
- explain why a stage is unavailable or constrained;
- help maintain a large product knowledge base.

## 18.2 AI must not

- diagnose skin conditions by default;
- invent unvalidated active combinations;
- exceed hard dose/application limits;
- override wear/airway/thermal/fluid/safety interlocks;
- claim a product is safe because an LLM thinks its ingredient list “looks fine”;
- freely alter a saved routine without user intent;
- convert uncertainty into confident treatment advice.

Architecture principle:

**IDENTIFY → RETRIEVE/ESTIMATE PROFILE → PHYSICAL CHECK → DETERMINISTIC BOUNDS → APPLY → VERIFY**

The AI can assist with retrieval/estimation. The safety/application controller owns the bounds.

---

# 19. Routine intelligence

Masck should remember and execute routines, not merely run modes.

## 19.1 Routine templates

Examples:

- Everyday AM;
- Everyday PM;
- Treatment Night;
- Recovery Night;
- Quick AM.

A routine contains the products and optional device treatments selected by the user within validated compatibility rules.

## 19.2 Schedule

Routines may be assigned by:

- AM / PM;
- day of week;
- selected recurring days;
- alternate-night or interval patterns where a validated rule exists;
- user-defined time windows.

The schedule prepares the **next likely routine**, but the user remains able to choose another prepared/available routine.

## 19.3 Temporary exceptions

One-day changes must not destroy the recurring schedule.

Examples:

- Run Quick AM today;
- Skip optical treatment tonight;
- Use Serum B tonight only;
- Skip the routine;
- Run PM routine early.

The app should visually distinguish **Today only** from **Edit schedule**.

## 19.4 Compatibility rules

Masck may warn or block when validated product rules identify a real incompatibility, sequence issue, temperature limit or interval requirement.

The system should explain the immediate reason without presenting itself as a dermatologist.

---

# 20. Routine editing UX

Routine construction should feel closer to arranging a playlist than programming an appliance.

User sees meaningful cards/stages:

**Cleanser**  
**Optical**  
**Treatment / Serum**  
**Moisturizer**  
**Facial SPF**

They can reorder only where validated rules allow it.

The app should make the recommended/required sequence clear, but avoid exposing technical pump/application settings.

Routine creation flow:

**New Routine → choose purpose/name → add loaded products/treatments → resolve any conflicts → choose schedule → save.**

Default names should be useful and editable.

---

# 21. Dock product experience

The dock is a premium home object, not a miniature laboratory or countertop coffee machine.

## 21.1 Presence

It should be appropriate on:

- a bathroom vanity;
- dressing table;
- bedroom surface if service noise/moisture handling permits.

It should feel intentional when visible for years.

## 21.2 Target scale

The dock should be as compact as the bulk-product/waste/service requirements permit. The core sketch rejects casually accepting a “small appliance” footprint without pressure to minimize it.

A useful ID target is a footprint closer to a **premium compact skincare organizer / charging object** than a kitchen appliance. Exact dimensions remain a packaging study.

## 21.3 Product display

Preferred direction: Masck One should appear **rested/protected and intentionally presented**, not hanging like equipment.

The dock should conceal the least attractive service elements:

- waste;
- wet connectors;
- tubing;
- raw bottle necks;
- service pumps/valves;
- cleaning residue.

Bulk skincare level may be visible through a controlled interface if it genuinely improves use, but should not turn the dock into a transparent laboratory.

## 21.4 Cable

Power cable routing should disappear behind/under the dock in normal view. User should not interact with the cable daily.

## 21.5 Night behavior

The dock should become visually quiet in a dark room. No bright always-on indicator. Readiness may be checked on touch/approach/app rather than broadcasting all night.

## 21.6 Service noise

Routine service should be scheduled/controlled so it does not produce conspicuous late-night pump cycles beside a bed where avoidable.

---

# 22. Dock ownership loop

The conceptual loop is:

**RETURN → CHECK → WASTE/SERVICE → CLEAN/DRY PATHS AS REQUIRED → CHARGE → THERMAL RESET → METER NEXT ROUTINE → READY**

The user should ordinarily experience only RETURN and READY.

The system should not make hidden cleaning claims that cannot be inspected or validated.

---

# 23. Session-dose architecture

This is a product-level requirement, independent of exact mechanisms.

The dock owns bulk product. The wearable carries **isolated session quantities**.

Reasons:

- protects on-head mass and CG;
- enables many routine products without storing full bottles on the face;
- simplifies “grab and go” routine execution;
- lets the dock prepare a scheduled routine in advance;
- limits the quantity involved in an on-head leak/failure;
- enables deliberate product separation.

The microdose package should be located with whole-product balance in mind. It must not become a heavy forehead or cheek cartridge merely because fluid access is convenient.

---

# 24. Portability

“Portable” means the **whole supported facial routine can be executed away from a sink and bottles once the wearable is prepared**.

The V1 home dock may remain a home base.

The architecture should leave room for a later compact travel preparation/service module, but V1 should not be compromised by forcing every dock function into travel size prematurely.

A user taking a prepared Masck One to another room, hotel desk or office should not need loose skincare bottles during the session.

---

# 25. Hygiene visibility

Hygiene confidence must be physically legible.

User should be able to inspect the facial interface and see:

- cleanable skin-adjacent surfaces;
- no dark residue traps;
- no obvious pooled fluid;
- no permanently wet sponge/foam;
- no maze of exposed channels at the skin boundary.

Where automated cleaning occurs, the product should still provide a credible way to inspect/service the parts that matter.

The premium feeling comes partly from **knowing what touched your clean face is itself clean**.

---

# 26. Failure-state UX

Failure states should preserve trust.

## 26.1 Low product

Before it becomes a mid-routine problem:

> **Moisturizer needs a refill before tomorrow morning.**

The system should predict readiness far enough ahead when sensing/model confidence permits.

## 26.2 Empty product

If a required product is unavailable, the system should not silently substitute another product or omit a required step while still calling the routine complete.

## 26.3 Wrong / unexpected product

If physical behavior materially disagrees with the assigned product profile:

> **This refill doesn’t match the product expected in this slot. Check what was added.**

## 26.4 Reformulation suspected

> **This product may have changed formula. Masck needs to check it before automatic use.**

## 26.5 Poor fit / seating

Do not begin a stage requiring validated placement if the required fit state is not achieved.

User-facing instruction should explain the immediate action, not expose sensor codes.

## 26.6 Early removal

System stops safely, records which stages completed, and does **not** falsely mark the routine complete.

It should tell the user what remains without automatically prescribing a risky recovery action.

## 26.7 Stage unavailable

If one scheduled stage cannot run, the user should know before routine start where possible.

The system must not degrade invisibly.

## 26.8 Offline

Configured local routines continue to work. Cloud/database enrichment waits until connectivity returns.

## 26.9 App unavailable

Physical start, safe operation and safe release remain available.

---

# 27. Accessibility

Accessibility is part of the core experience, not an app-only afterthought.

Requirements/targets:

- one-handed normal operation where practical;
- tactile physical orientation of the wearable and docked product bays;
- no critical instruction encoded by color alone;
- app supports screen-reader semantics, scalable text and sufficient contrast;
- no tiny engraved labels required to perform routine service;
- haptic/light redundancy for users who cannot hear a completion sound;
- visible/text alternative for users who cannot perceive haptics;
- loading openings/grips usable without high pinch strength where practical;
- emergency/quick release obvious by touch.

---

# 28. Privacy

Masck is not a skin-surveillance product by default.

## 28.1 Default exclusions

No default:

- continuous face camera;
- acne score;
- pore score;
- “beauty score”;
- wrinkle ranking;
- skin-age leaderboard;
- emotional inference;
- always-listening microphone;
- location tracking merely for personalization.

## 28.2 Camera use

Camera access may be requested deliberately for product barcode/packaging/ingredient recognition. The app should state why it is needed.

## 28.3 Product-learning data

If users opt in to aggregate product/application learning, collect the minimum useful technical/product information. Do not require face photos or sensitive health data merely to improve flow profiles.

---

# 29. Offline independence

Once the device and routines are configured, normal use must not depend on:

- internet access;
- phone proximity;
- logged-in cloud session;
- external AI availability;
- subscription authentication.

Loss of cloud service must not make the physical skincare appliance unusable.

---

# 30. Ownership over years

Masck One is the durable hero object.

The concept should distinguish:

## Durable

- primary wearable shell/structure;
- dock body;
- major user controls;
- core electronics/functional architecture subject to serviceability decisions.

## Service / replaceable where needed

- skin-contact elements with genuine wear/hygiene life;
- fluid-contact consumable/service elements;
- seals/liners/filters only where their replacement is justified;
- battery through a deliberate service strategy rather than planned product disposal.

The dock and mask should age visually like premium personal-care hardware, not like a two-year gadget with trendy RGB/graphics.

---

# 31. Unboxing and onboarding

The initial experience should establish simplicity immediately.

Kit should contain only what is genuinely required:

- Masck One;
- Masck Dock;
- essential power hardware;
- essential removable/service parts;
- concise onboarding material.

No giant bag of adapters, medical-looking accessory trays or thick setup manual.

Target onboarding:

**unbox → power dock → optional app/account setup → confirm size/fit → identify/load products → build or accept a simple starter routine → dock prepares → first use.**

The app may guide setup, but fundamental safe removal and device identity should be understandable without reading a long manual.

---

# 32. Feature hierarchy

## Tier A — identity-defining

These define whether the product is still Masck One:

- complete supported facial routine in one wear session;
- cleansing + rinse/recovery + leave-on application;
- non-wiping transition/removal;
- user’s own skincare products;
- dock-held bulk products + wearable session doses;
- prepared grab/place/start/remove/return UX;
- premium calm rigid/semi-rigid facial object;
- balanced comfortable hands-free wear;
- offline physical operation;
- visible hygiene confidence.

## Tier B — signature capability

Important differentiators that support the core promise:

- scheduled AM/PM/day routines;
- adaptive product identification/application profiles;
- growing validated product database;
- physical treatment/massage;
- deliberate WARM / COOL;
- red/NIR optical treatment;
- facial SPF application once validated;
- premium dock auto-preparation/service;
- dense quiet primary-control feel.

## Tier C — supporting

- app history;
- service guidance;
- optional notifications;
- product depletion forecasting;
- user-controlled data contribution;
- future travel module compatibility.

Features must not be added merely because they fit in Tier C.

---

# 33. No-feature rules

Unless future evidence demonstrates an exceptional reason, Masck One should **not** acquire:

- a display on the face;
- talking speakers/voice assistant;
- Alexa/Siri-style gimmick integration as a core feature;
- gamification, streak pressure or beauty leaderboards;
- skin/beauty score by default;
- RGB status bars;
- visible LED-strip decoration;
- proprietary skincare lock-in;
- arbitrary “Masck serum ecosystem” requirement;
- decorative vents;
- fake cooling vents;
- fake AI theater;
- app-required every-session operation;
- complicated multi-strap fitting ritual;
- VR-style halo/counterweight appearance;
- visible product plumbing;
- transparent lab-machine aesthetic;
- constant beeping/buzzing;
- intentional metallic ping;
- unnecessary treatment modes added only to match competitors;
- automatic blue-light treatment simply because another beauty device offers it;
- UV-cleaning theater without a validated need and evidence path;
- uncontrolled warmth passed off as treatment;
- social feed/community gamification;
- continuous face surveillance;
- direct aerosol face spraying as a default sunscreen/product application assumption.

---

# 34. Target specification anchors

These are concept/engineering anchors that future work should reconcile, not silently change.

| Area | Core-sketch anchor | Status |
|---|---|---|
| Product envelope | ~172 × 210 mm XY historical outer reference | refine against live authority |
| Functional frame | ~155 × 202 mm historical | engineering-controlled |
| Shell wall | ~1.8 mm historical | engineering-controlled |
| Eye centers | ~±31.5, +35 mm | engineering-controlled |
| Eye protected aperture reference | ~46 × 30 mm | engineering-controlled |
| ID eye-opening direction | ~63 × 47 mm before cant where compatible | concept target |
| Mouth aperture | ~58 × 32 mm at (0,-50) | engineering-controlled |
| Deformed nostril area | ≥120 mm² historical | evidence/engineering constraint |
| Airway | ≤10 Pa @30 L/min; ≤40 Pa @60 L/min historical | evidence/engineering constraint |
| Dry mass | ≤215 g | engineering target |
| Loaded mass | <255 g | engineering target |
| CG Z | ≤30 mm | engineering target |
| Torque | ≤0.070 N·m | engineering target |
| Quick release | ≤2.0 s | engineering target |
| Retention | 5–12 N historical | engineering/validation target |
| Exterior | Mineral Ivory #E9E5DC | selected CMF intent |
| Primary control | Warm Porcelain #DED9CF | selected CMF intent |
| Contact | Soft Stone #CFC8BC | selected CMF intent |
| Recessed mechanical | Smoke Graphite #454542 | selected CMF intent |
| Status/optical unlit | Opal Neutral ~#F2EFE7 | selected CMF intent |
| Optical benchmark | ~633 / 830 / 1072 nm research benchmark | not frozen until validated |

---

# 35. Definition of core-sketch success

The Core Sketch is being respected when a future design still produces this experience:

1. The user’s products live in the Masck ecosystem without being replaced by Masck-branded chemistry.
2. The dock quietly prepares the next scheduled facial routine.
3. The user lifts one calm premium object.
4. It self-aligns and secures without a strap ritual.
5. One precise physical action starts it.
6. Masck cleans, rinses, treats and applies the saved leave-on routine while the user does something else.
7. The product does not rely on noise, heat or light theater to feel advanced.
8. It releases without wiping away the final routine.
9. The face feels complete.
10. The user returns the product to the dock and walks away.
11. Complexity remains inside the system.

If later work produces a technically impressive device but loses that experience, it has drifted from Masck One.
