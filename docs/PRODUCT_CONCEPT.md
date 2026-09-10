# Masck One Product Concept

Status: **product concept and experience intent; not engineering authority**  
Updated: 2026-09-10

This document preserves the current core product thesis for Masck One and the product-level implications that engineering, industrial design and digital work should respect unless the concept is deliberately revised.

It is not a substitute for released engineering authority or physical evidence. `config/masck_one_authority.yaml`, released code/CAD, source-bound manifests, CI evidence and physical validation remain controlling for what Masck One can actually be claimed to do. Where this document describes future capability, treat it as product intent and an R&D requirement, not as proof that the capability exists.

## 1. Non-negotiable product thesis

Masck One is not intended to settle for being only an automated cleanser or a generic beauty-treatment mask.

The defining product promise is:

> **Put Masck One on, start one routine, continue with something else, remove it, and the complete facial skincare routine is finished.**

A successful routine must not require the user to return to a bathroom or vanity to add a serum, moisturiser, sunscreen or another ordinary facial-skincare step after Masck One is removed.

This full-routine requirement is central to the portability proposition. If a normal required facial-skincare step must still be performed manually after use, the primary reason for Masck One to exist is weakened.

The target experience remains:

`GRAB -> PLACE -> SELF-ALIGN / SECURE -> ONE START -> COMPLETE ROUTINE -> RELEASE -> REMOVE -> RETURN`

The exact sequence within `COMPLETE ROUTINE` is configurable by routine and may include only the stages appropriate to that routine.

## 2. Complete-routine execution

The working routine architecture is:

`CLEAN -> RINSE / RECOVER -> PHYSICAL / OPTICAL TREATMENT -> LEAVE-ON TREATMENT -> MOISTURISE -> SPF WHEN REQUIRED -> NON-WIPING RELEASE`

Not every session needs every stage. Morning, evening and scheduled treatment routines may differ.

Examples of product-level routine structures include:

- morning: cleanse -> optional optical/treatment stage -> serum/treatment -> moisturiser -> SPF;
- evening: cleanse -> optional optical/thermal/mechanical treatment -> serum/treatment -> moisturiser;
- minimal routine: cleanse -> moisturiser;
- scheduled treatment night: cleanse -> selected treatment sequence -> moisturiser.

Routine order, compatibility and final claims require formulation-specific and physical validation. The sequence above is product intent, not a blanket claim that every product combination is safe or effective.

## 3. Portability means complete untethered execution

Masck One should be genuinely untethered during a routine and should not require the user to remain at a sink.

Portability does not mean carrying full retail bottles, weeks of fluid or every ownership function on the face. The wearable should carry only the fluids and energy needed for the prepared routine. Bulk storage, waste handling, cleaning, charging, thermal reset and routine preparation should be moved to the dock wherever practical.

The intended value is reduction of active human attention, not necessarily minimum wall-clock duration. A Masck routine may take longer in elapsed time than a fast manual routine while still being valuable if the user is free to perform other normal activities safely during the automated sequence.

The product should therefore optimize for:

- very low active setup effort;
- no sink tether during treatment;
- no manual facial-skincare step after removal;
- low service frequency;
- predictable, quiet completion;
- a return-to-dock action that closes the ownership loop.

## 4. Dock-prepared, session-dose fluid architecture

The dock should own bulk product storage and servicing. The wearable should carry only session-scale doses or a deliberately small number of prepared routines.

Conceptually the dock may maintain isolated product reservoirs for categories such as:

- cleanser;
- leave-on treatment / serum slot 1;
- leave-on treatment / serum slot 2 or optional additional treatment slots;
- moisturiser;
- sunscreen;
- other future product classes only when technically justified.

The exact slot count is not frozen by this document.

While docked, Masck One should ultimately be able to perform as much of the following ownership loop as practical:

`RETURN -> IDENTIFY INVENTORY -> HANDLE WASTE -> CLEAN / PURGE REQUIRED PATHS -> CHARGE -> THERMAL RESET -> METER NEXT ROUTINE -> VERIFY -> READY`

The user should not need to pour several products into tiny wearable reservoirs before each routine.

A strong architecture is a removable or serviceable session cassette / micro-reservoir system that receives only the required doses for the next routine. Bulk reservoirs remain in the dock.

## 5. Broad compatibility with the user's existing skincare

The product direction is **not** to force users into proprietary MASCK skincare formulations.

Masck One should aim to work with the broad practical range of normal consumer facial-skincare liquids, essences, serums, gels, lotions, creams, cleansers and sunscreens that fall inside a physically and chemically supportable compatibility envelope.

The phrase "all products" must never be interpreted literally as permission to dispense any unknown liquid. The system needs explicit limits for material compatibility, rheology, particulate content, solvent system, temperature, pumpability, residue, cleaning, dosing and user safety.

The strategic principle is:

> **The user should not have to change their skincare routine for Masck. Masck should learn how to execute the user's routine.**

Supporting a wide product range is therefore primarily an adaptive identification, transport, dosing and application-control problem rather than a requirement that third-party brands reformulate specifically for Masck.

## 6. Product identification

Masck must know what product is present in each reservoir. It must not infer product identity solely from the physical behaviour of an anonymous liquid.

A robust identification flow should combine several signals where available:

1. barcode or QR identification;
2. camera / label recognition;
3. exact product-name search and user confirmation;
4. ingredient-list / packaging scan for variant and reformulation checks;
5. SKU, market and formulation-version metadata where available;
6. physical flow fingerprint as a consistency check, not as the sole identity mechanism.

The user should normally identify a product once when a reservoir is filled or changed. Masck should remember that identity until the user changes it or the measured behaviour becomes inconsistent with the recorded product.

If a reservoir expected to contain Product A exhibits strongly inconsistent pressure / displacement / flow behaviour, the system should fail safely and ask whether the product was changed rather than blindly continuing.

## 7. Growing product database

Masck should maintain a product/application database that can expand as more owners use different skincare products.

A product record may eventually contain:

- exact identity and formulation/version metadata;
- product category and intended routine position;
- known physical / rheological family;
- validated dose range;
- permitted delivery mechanism(s);
- pressure / flow / temperature bounds;
- distribution or spreading parameters;
- settling interval;
- path-cleaning / purge requirements;
- known material or sequence incompatibilities;
- validation status;
- version history.

Community use can accelerate discovery and characterization but must not automatically become safety evidence.

Suggested conceptual states are:

- `KNOWN`: exact product identity exists;
- `CHARACTERIZED`: dispensing behaviour is understood sufficiently for engineering use;
- `VALIDATED`: application method has passed the required MASCK validation for the intended use;
- `RESTRICTED` or `UNSUPPORTED`: automatic application is not permitted.

Exact state names and release criteria belong in future software / validation authority.

The database should preserve reformulation awareness. The same consumer-facing product name may change composition over time, so identity should not rely only on brand plus product name when stronger version information is available.

## 8. Adaptive application engine

Different skincare products should not be forced through one fixed application profile.

Masck should ultimately be able to adapt parameters such as:

- dose;
- delivery mode;
- pressure / pump profile;
- flow rate;
- applicator selection or active zone;
- deposition pattern;
- spreading motion;
- facial coverage map;
- temperature bounds;
- settling time;
- purge / cleaning sequence.

A conceptual application flow is:

`PRODUCT ID -> DATABASE PROFILE OR CONSERVATIVE ESTIMATE -> FLOW / PRESSURE CHECK -> BOUNDED APPLICATION PARAMETERS -> DELIVERY -> DELIVERY VERIFICATION`

The difficult product requirement is not merely pumping fluid. It is producing a reproducible final skin film across a curved, moving, person-specific facial surface without unacceptable contamination, removal of prior layers, pooling, inhalation risk, eye exposure or residue inside the device.

## 9. AI role and deterministic safety boundary

AI may become useful, but the Masck One concept must not depend on an unconstrained AI making safety-critical skincare decisions.

Useful AI roles include:

- resolving product identity from labels, packaging and public/manufacturer information;
- matching a newly encountered product to a known physical/application family;
- interpreting ingredient lists and manufacturer directions as inputs to a conservative profile proposal;
- helping organize user-created routines and schedules;
- detecting likely product-version changes;
- improving application-profile prediction as the characterized-product dataset grows;
- explaining routine conflicts or unavailable stages to the user.

Hard safety and delivery limits must remain deterministic and independently enforced. AI must not be able to override pressure, temperature, dose, wear-state, eye/airway, compatibility, material, sequence or other released safety constraints.

A useful layered model is:

1. deterministic safety and device controller;
2. MASCK application intelligence / calibration model;
3. user-facing routine assistant.

AI should orchestrate a bounded system, not invent arbitrary chemistry or diagnose skin conditions.

## 10. Scheduled routines

Masck should support user-defined day-scheduled routines.

A user may define routines such as `A`, `B`, `C` and assign them to days of the week or morning/evening periods. For example, Monday may run Routine A, Tuesday Routine B, Wednesday Routine A, and so on.

The schedule should be editable by the user and deterministic by default. AI may assist with organization or surface conflicts, but should not silently alter the user's regimen.

The dock can use the schedule to prepare the correct session doses ahead of time, verify that required products are present, and notify the user only when an actual service or refill action is required.

Scheduled routines also allow modalities such as mechanical treatment, warming/cooling or optical treatment to appear only on sessions where they are appropriate rather than being forced into every use.

## 11. Wearable mass, packaging and center of gravity

The full-routine concept must not be implemented by simply adding large product compartments across the mask.

Bulk fluid belongs in the dock. The wearable should carry only session-scale doses.

Fluid mass is only part of the problem. The valves, pumps, chambers, seals, tubing, manifolds and applicators required to isolate products can dominate volume and mass if not consolidated carefully.

New full-routine packaging must therefore be co-optimized with:

- current dry-mass and loaded-mass requirements;
- current CG and torque requirements;
- battery placement;
- thermal stores and contact hardware;
- retention load path;
- airway and protected anatomy;
- treatment actuators and reaction structure;
- cartridge / waste architecture;
- serviceability and cleanability.

Session reservoirs / cassette mass should be placed as close as practical to the whole-product center of mass and head-supporting structure rather than creating a heavy anterior fluid stack.

Existing mass and CG authority remain controlling until deliberately changed through engineering authority. The full-routine concept does not authorize weakening ergonomic mass or torque requirements merely to add features.

## 12. Contact phase versus leave-on phase

The current cleansing and mechanical-treatment architecture uses controlled facial contact. Leave-on products create a different requirement: the device must not apply a serum, moisturiser or sunscreen and then wipe a large fraction of it back off during later contact or removal.

Masck should therefore investigate an explicit two-state facial-interface architecture:

### Contact / cleansing state

Used for cleansing, rinsing/recovery and any treatment that legitimately requires controlled facial contact.

### Leave-on / finish state

The broad cleansing/treatment interface retracts or otherwise disengages from the skin sufficiently to permit leave-on application and final release without wiping away the deposited film.

A successful concept may use distributed non-contact deposition, retractable applicators, controlled transfer elements or another architecture. No deposition method is selected by this document.

The product-level requirement is stronger than a specific mechanism:

> **After the final leave-on stage, Masck must be able to release and be removed without materially undoing the application it just performed.**

This is a major R&D gate.

## 13. Sunscreen is a special application class

Facial SPF is strategically important because a morning routine is not complete if the user must manually return to apply facial sunscreen.

Sunscreen must not be treated as just another low-risk serum profile. Dose, evenness, final film integrity, product-specific instructions and applicable regulatory/claims requirements matter directly to protection.

Masck must not claim that dispensing the nominal amount of an SPF product automatically delivers the labelled protection. Device-applied sunscreen needs dedicated physical validation of final facial coverage and appropriate performance.

Fine aerosolization around the eyes, nose, mouth or airway should not be assumed as the solution. The final architecture must explicitly manage inhalation, ocular exposure, protected openings and film uniformity.

Masck One's full-routine promise is a **complete facial skincare routine**. It does not imply that facial SPF application replaces sunscreen required on exposed ears, neck or body.

## 14. Optical / LED treatment opportunity

Masck One should investigate integrating a premium red / near-infrared optical-treatment subsystem if the added mass, power, heat, optical safety, BOM and packaging burden remain justified by evidence and consumer value.

CurrentBody Series 2 may be used as a **competitive functional benchmark only**, not as implementation authority. Publicly discussed wavelength families around 633 nm red, 830 nm near-infrared and 1072 nm near-infrared are useful benchmark inputs for research, but Masck must develop its own optical geometry, emitter count, carrier, driver electronics, thermal design, baffling, eye-protection strategy, firmware and dose validation.

Do not copy proprietary PCB layouts, firmware, industrial design, protected geometry or undocumented treatment logic.

Emitter count is not itself a performance requirement. The design target should be based on validated wavelength, irradiance, uniformity, facial coverage, treatment distance, dose, thermal behaviour, electrical safety and eye safety.

An attractive product sequence is to place optical treatment after cleansing/recovery and before leave-on products, so optical delivery is not unpredictably altered by a final moisturiser or sunscreen layer.

Optical treatment should not be included merely to create visible 'working' theatre. Any retained modality must justify its cost, power, mass and treatment time.

## 15. Ownership and interaction quality

The full-routine architecture must preserve the existing MASCK product character:

**CALM OUTSIDE. EXCEPTIONALLY ENGINEERED INSIDE.**

Additional reservoirs, applicators, emitters, sensors and valves must not turn the exterior into VR, medical, robotic, cyberpunk or gaming hardware.

The user experience should remain quieter and simpler as internal complexity increases.

Primary interaction remains one deliberate start action, with minimal necessary feedback and no gratuitous buzzing, beeping, lighting or 'technology theatre'. Service interactions should follow the existing premium tactile target: broad acquisition, low-drag guidance, progressive take-up, disappearance of play, one resolved state transition, dense controlled landing and independent abuse stops.

## 16. Skin-barrier and routine-integrity requirement

Masck One must not pursue 'deeper cleaning' as an end in itself.

The cleansing objective is effective removal of the intended soil / sunscreen / sebum / removable cosmetic load with the minimum necessary disturbance to the skin.

Future physical validation should compare Masck against an appropriate gentle manual-cleansing control for both cleansing performance and barrier / irritation outcomes. The product should not be promoted on the basis of barrier superiority unless that is actually demonstrated.

The complete automated routine must also prove that sequential application does not create unacceptable cross-contamination, pilling, pooling, dilution, removal of previous layers or unpleasant residue.

## 17. Makeup boundary

The product promise is the complete **facial skincare routine**. Heavy or waterproof cosmetic removal, especially around protected eye regions, is a separate unresolved use case unless and until Masck can perform it safely and effectively.

This boundary must be tested with real target users because a requirement for manual makeup removal may weaken the portability proposition for some customer groups.

Do not silently market Masck as a complete makeup-removal system without evidence.

## 18. Core concept validation gates

The following are existential product questions, not optional polish:

- can Masck cleanse effectively without unacceptable skin-barrier disruption or irritation?
- can the fluid architecture handle the practical skincare-product rheology space without becoming too heavy, large, dirty or maintenance-intensive?
- can leave-on products be dosed and distributed reproducibly?
- can successive layers be applied without substantially undoing previous layers?
- can the device release without wiping away the final film?
- can facial SPF be applied with sufficiently reliable amount and uniformity to justify the intended claims?
- can the dock make ownership easier rather than simply relocating tedious maintenance?
- can a useful number of product reservoirs / prepared doses coexist with current mass, CG, torque, airway, anatomy and industrial-design constraints?
- do target users repeatedly choose the product over their normal routine when both are available?
- is willingness to pay compatible with a manufacturable BOM and healthy business economics?

Failure of one architecture is not automatically failure of the concept. Repeated failure of fundamentally different architectures against the same core requirement is evidence for redesign or reconsideration.

## 19. Immediate architectural implications

Future subsystem work should treat the following as active concept requirements:

- preserve full-routine completion as the target, not cleanser-only convergence;
- add a source-bound concept for dock-side bulk product storage and automated routine preparation;
- investigate session-dose micro-reservoir / cassette packaging near the whole-product CG;
- map the practical product classes and rheology envelope the application engine must support;
- define product identity / formulation-version architecture;
- design a deterministic product/application profile model;
- investigate flow/pressure sensing sufficient for calibration and mismatch detection;
- develop contact-to-leave-on transition concepts;
- develop non-wiping final application / release concepts;
- treat sunscreen deposition as a separate high-rigor workstream;
- investigate independent red/NIR optical treatment integration without copying competitor implementation;
- extend the digital product vision to scheduled routines, reservoir inventory, product identity, compatibility state and dock preparation while preserving capability gates;
- preserve existing mass, CG, protected anatomy, evidence, material/reference separation and physical-validation firewalls throughout.

## 20. Product sentence

The current concept can be summarized as:

> **Masck One is a portable, hands-free facial-skincare platform that learns the products and routines a user already chooses, prepares the required session automatically, and executes the complete facial routine so that when the device comes off, the user is done.**

That sentence is product intent, not a release claim. The engineering and validation program exists to determine whether Masck One can earn the right to make it true.
