# MASCK ONE Product Concept

Status: **product concept and target experience; not engineering authority**  
Updated: 2026-09-10

This document records the current highest-level product intent for Masck One so that concept development is not lost across implementation work. It defines what the product is trying to become, what user experience is non-negotiable, and which major architectures should be investigated next.

It does **not** prove that any newly described capability is feasible, safe, manufacturable, clinically effective, regulatory-cleared, cost-effective or present in released CAD. `config/masck_one_authority.yaml`, released engineering code/CAD, exact-head validation evidence and physical test results remain controlling for engineering truth. If concept intent conflicts with released engineering evidence, the conflict must stay explicit until engineering is changed and revalidated.

## 1. Core product thesis

Masck One should not settle for being only an automated cleanser or a treatment mask that still requires the user to return to the bathroom and manually complete the rest of their facial skincare routine.

The core product promise is:

> **Put Masck One on, start the routine, continue with something else, remove Masck One, and the complete facial skincare routine is finished.**

The strongest definition of completion is:

> **When Masck One comes off, the user should not need to touch their face again to complete that facial skincare routine.**

This makes **whole-routine execution and portability** first-class concept requirements rather than optional future features.

Masck One is therefore best understood as an **adaptive automated facial-skincare platform**, not merely a cleanser, LED mask, massage mask, or proprietary skincare brand.

### Completion boundary after whole-product review

The promise applies to the selected supported facial session, including every region required by its product/application profiles and a validated normal release. Legacy aggregate cleansing coverage, a commanded pump quantity or retraction of massage islands alone cannot establish completion. Stationary supports, seals and thermal/fluid contact surfaces must also be accounted for. Required facial regions may not be silently excluded to make the device pass.

“Supported” is an evidence boundary, not permission to quietly narrow the product to easy aqueous formulations or omit a required facial finish. The compatibility cohort and total ownership benefit must be established early. An unavailable required stage means the selected routine is incomplete. Completion does not replace future label-required care/reapplication or sunscreen on other exposed regions.

See [the convergence review](CORE_SKETCH_CONVERGENCE_REVIEW.md) for the twenty conflicts, surviving architecture and explicit kill/pivot conditions. No engineering authority or human-use limit is changed by that review.

## 2. Portability means complete routine portability

Portability is only meaningful if Masck removes the need to return to a sink, vanity or product shelf for remaining facial-skincare steps.

A concept in which Masck performs cleansing but the user must then return to manually apply serum, moisturiser or sunscreen weakens the primary value proposition. The target is a genuinely untethered routine once the wearable has been prepared by its dock.

The dock may remain a home base for filling, cleaning, charging and preparation. The **routine itself** should be executable away from the dock.

The target ownership loop is:

`RETURN -> DOCK PREPARES -> GRAB -> PLACE -> START -> COMPLETE ROUTINE -> RELEASE -> REMOVE -> DONE -> RETURN`

The dock should absorb as much recurring ownership friction as practical so the user does not have to refill small chambers or service multiple fluid paths before every session.

## 3. Complete facial-routine state machine

The target routine is staged rather than attempting to perform incompatible functions simultaneously.

A representative morning sequence is:

`CLEAN -> RINSE/RECOVER -> optional PHYSICAL/OPTICAL TREATMENT -> LEAVE-ON TREATMENT/SERUM -> MOISTURISE -> FACIAL SPF -> required SETTLE -> NON-WIPING RELEASE`

A representative evening sequence is:

`CLEAN -> RINSE/RECOVER -> optional PHYSICAL/OPTICAL TREATMENT -> LEAVE-ON TREATMENT/SERUM -> MOISTURISE -> required SETTLE -> NON-WIPING RELEASE`

Exact steps are user-, product- and evidence-dependent. Individual stages may be skipped where appropriate. The product should not run every available modality merely because the hardware contains it.

### Contact-state transition

A complete-routine Masck probably requires at least two facial-interface states:

1. **Contact/treatment state** for cleansing, controlled mechanical treatment and fluid recovery where skin contact is useful.
2. **Leave-on application state** in which cleansing/treatment contact elements retract or otherwise stop wiping the skin while serum, moisturiser and SPF are applied.

The final release must avoid dragging treatment surfaces across freshly applied leave-on products. A credible **non-removing final application and release architecture** is therefore a major new R&D requirement.

The exact implementation is open. Candidates may include retractable contact surfaces, separated application structures, distributed transfer elements, controlled larger-aperture microfluidic deposition, or another architecture that survives physical testing. Fine aerosolisation around the eyes, nose or mouth should not be assumed to be acceptable.

## 4. User keeps their existing skincare products

Masck One should adapt to the products the user already chooses rather than requiring a MASCK-only formulation ecosystem.

The design ambition is to support the **broad practical range of ordinary facial-skincare liquids, essences, serums, gels, lotions, emulsions, creams, cleansers and sunscreens**. The system should learn how to deliver the product instead of forcing the product to be reformulated for the machine.

This is an ambitious compatibility target, not permission to claim literal compatibility with every substance. Hard physical, material, safety, formulation, regulatory or application limits must remain explicit when they are discovered.

The long-term user proposition is:

> **You do not change your skincare routine for Masck. Masck learns how to execute your skincare routine.**

## 5. Product identification: Masck must know what is loaded

Masck should never be expected to identify an anonymous liquid purely from appearance or flow behaviour. Identity and dispensing behaviour are separate problems.

When the user loads or changes a product, the system should identify it once using a combination of:

- barcode or QR scanning where available;
- camera recognition of the front label;
- OCR of exact product name and variant;
- user search/selection as a fallback;
- ingredient-list and packaging scan where needed to distinguish variants or reformulations;
- user confirmation when identity is uncertain.

The product record should ultimately distinguish more than brand and marketing name. Where possible it should track exact SKU, market/region and formulation/version so a reformulation cannot silently inherit an obsolete application profile.

A physical flow fingerprint may then check whether measured behaviour is consistent with the recorded product; a matching fingerprint cannot chemically authenticate the contents or prove that a formulation is unchanged. If measured behaviour changes materially, Masck should stop or ask whether the product was changed rather than blindly continuing.

## 6. Growing product/application database

The Masck product database should improve as more users introduce different skincare products.

A product record may include:

- manufacturer, brand, product and variant identity;
- category and normal routine position;
- formulation/version evidence;
- nominal dose ranges where known and validated;
- application family;
- measured pressure/flow response;
- temperature sensitivity;
- pump/valve/application settings;
- zone/coverage pattern;
- settling interval;
- material compatibility evidence;
- cleaning/changeover requirements;
- known incompatibilities;
- validation status.

Community use may accelerate discovery and physical characterisation but must not itself create a safety or efficacy claim.

The database should distinguish conceptually between states such as:

- **KNOWN**: exact product identity is known;
- **CHARACTERISED**: dispensing/application behaviour has been measured sufficiently to create a bounded profile;
- **VALIDATED**: MASCK has completed the required application/compatibility validation for automated use;
- **RESTRICTED / UNSUPPORTED**: automatic application is not permitted under the current evidence or hardware envelope.

As more units use the same exact product/version, aggregated non-sensitive engineering telemetry could improve the robustness of its physical delivery model across temperature, fill level, device variation and product batches. No health or skin-condition data is required for this learning loop.

## 7. Adaptive application engine

The central new technical concept is an **adaptive application engine**.

Different products should not receive identical application profiles. Estimates may guide characterisation, but automatic consumer application requires an eligible validated product/routine context. Identity, preserved formulation, delivery behaviour, required coverage and sequence compatibility remain separate evidence. Two validated products do not automatically form a validated layered routine.

The high-level control chain is:

`IDENTIFY -> LOAD PROFILE -> PHYSICAL CALIBRATION -> BOUNDED APPLICATION PLAN -> CLOSED-LOOP DELIVERY -> VERIFY -> LEARN`

Useful physical feedback may include pressure, flow, pump displacement, temperature, reservoir state and other measurements justified by the final architecture. These measurements should be used to understand how the product is actually moving through Masck rather than trusting a database value blindly.

An application profile may eventually encode concepts such as:

`{dose, routine_position, product_family, flow_model, pressure_limits, delivery_mode, coverage_pattern, spreading_behavior, settling_time, temperature_limits, changeover_rules}`

The implementation must remain deterministic at the safety boundary.

## 8. AI role

AI can make the platform substantially more scalable, but AI is not a substitute for safe fluid mechanics or validated control.

The preferred architecture has three layers:

### Layer 1: hard safety and machine controller

Deterministic rules, validated bounds, interlocks and state-machine transitions. AI must not be able to override protected anatomy, unsafe pressure/temperature limits, unsupported chemistry states, wear-state interlocks or other safety-critical controls.

### Layer 2: Masck application intelligence

Uses exact product identity, known application data and physical sensor response to choose and adapt a bounded delivery profile. For an unknown product, AI may help classify it from product metadata and ingredient information and map it to a known physical application family, but the device should still perform physical calibration and remain inside deterministic limits.

### Layer 3: user-facing routine intelligence

Helps the user create, organize and schedule routines from products they already own and from hardware modes that actually exist. It should not diagnose skin conditions or freely invent active-ingredient combinations. Recommendations must stay inside validated product/routine constraints.

The proprietary long-term value is more likely to be the combination of **product database + physical application models + calibration data + routine execution system** than training a foundation model from scratch.

## 9. Scheduled routines

Masck should support day-scheduled and time-scheduled routines so the user configures a regimen once and the system prepares it automatically.

Example concept:

- Monday: Routine A
- Tuesday: Routine B
- Wednesday: Routine A
- Thursday: Routine C
- Friday: Routine A
- weekend: user-selected or scheduled variants

A routine may define the ordered skincare products plus available physical/optical treatment modes. Morning and evening schedules can differ.

The dock should know the next scheduled routine, verify that required products are present, meter the required session quantities and surface only meaningful attention requests such as insufficient product, a changed/unknown product, a required cleaning cycle or another real blocker.

The schedule should be user-editable and deterministic. AI may help construct or simplify a schedule, but it should not silently change a user's routine.

## 10. Dock holds bulk product; wearable carries session doses

The wearable should **not** carry full bottles or weeks of product. That would unnecessarily increase mass, volume and facial moment.

The preferred architecture is:

- larger reusable product reservoirs, removable reservoirs or product adapters live primarily in the dock;
- the dock meters only the quantities needed for the next routine into Masck;
- the wearable contains multiple isolated **session-dose micro-reservoirs** or a compact session cassette;
- the wearable executes the prepared routine away from the dock;
- the dock handles charging, waste/service, fluid-path preparation, changeover and thermal reset where possible.

The exact number of bulk product slots is not frozen. The system should be able to represent a realistic enthusiast routine with cleanser, multiple optional treatment/serum products, moisturiser and SPF without requiring nightly manual refilling.

Product changes should be occasional ownership events rather than per-session chores. Removable reservoir modules may be preferable to asking a user to drain and clean a chamber every time they change serum.

### Prepared is not permanently ready

The dock prepares a particular versioned session, not an unlimited permission to run a schedule. Its receipt binds physical contents, product/formulation identity, storage history, service result, profile/hardware versions and resource state. Hold times and preservation limits need evidence; none is assumed here. A late substitution, expired dose, uncertain partial delivery or incomplete service must revalidate or invalidate readiness. Saved routines remain intact when a temporary eligible session changes.

Bulk storage does not select universal decanting into open tanks. Retail-package functions and compatibility with Masck storage/contact materials must be preserved through a qualified interface. No dilution or formulation change is assumed to make the user's skincare compatible.

## 11. Mass, centre of gravity and ergonomics

Whole-routine functionality must not destroy the wearable's comfort.

Added product capacity should be treated primarily as a **packaging and mechanism problem**, not as permission to hang bulk fluid on the face. Session quantities themselves should be small compared with full retail containers; the larger mass risk is the collection of valves, manifolds, pumps, reservoirs, tubing and support structure.

Concept rules:

- keep only session quantities on-head where practical;
- place dense fluid/control hardware near the head rather than far anterior to the face;
- investigate a compact central, crown-adjacent, temple-balanced or rear-biased session cassette instead of distributed front-shell bulk reservoirs;
- co-optimise fluid hardware with battery, thermal stores, electronics and retention so one subsystem does not independently consume the CG budget;
- preserve symmetry unless an asymmetric architecture demonstrably improves total mass properties;
- include filled/part-filled/empty reservoir states in future mass-property sweeps;
- authority-backed total mass, CG and facial torque constraints remain controlling until formally changed.

The target is many available products **without many grams of unnecessary carried product**.

## 12. LED / photobiomodulation concept

A red / near-infrared optical treatment layer appears technically plausible and may add enough independent treatment value to justify investigation if BOM, thermal, power, thickness and validation burden remain acceptable.

CurrentBody Series 2 is a **functional benchmark only**, not a design to clone. Publicly discussed benchmark classes include approximately 633 nm red, 830 nm near-infrared and 1072 nm deeper near-infrared emitters. Exact LED count, package, spacing, drive electronics, optical carrier, firmware, dose and mechanical implementation are not authority and must be independently engineered.

CurrentBody's hardware/firmware is not treated as open source. Masck must not copy proprietary implementation, industrial design, PCB layout, firmware or protected mechanism details. Prior-art, patent, regulatory and freedom-to-operate review are required before any commercial freeze.

The concept target is to reproduce or exceed the **useful optical outcome**, not a competitor's BOM:

- justified wavelength selection;
- controlled irradiance and dose;
- facial coverage uniformity;
- controlled emitter-to-skin distance;
- eye safety and baffling;
- low unnecessary heat at the skin;
- acceptable electrical and thermal load;
- hygienic non-contact integration where practical.

The current 236-LED competitor count is not sacred. Masck should use whatever original optical architecture best satisfies coverage, dose, mass, cost, power and thermal constraints.

A natural whole-routine position for optical treatment is after cleansing/rinse/recovery and before leave-on serum/moisturiser/SPF layers, subject to later optical/formulation evidence.

## 13. Skin-barrier preservation is a concept-level requirement

Masck must not pursue 'maximum stripping' or 'deeper cleaning' as an end in itself.

The target is **effective cleansing with minimum necessary disturbance**. Physical validation should eventually compare Masck with an appropriate gentle manual-cleansing control for cleansing performance and skin-barrier impact.

A successful product must not earn portability by degrading the user's skincare routine. If the automated cleansing/treatment sequence causes unacceptable irritation, barrier disruption, dehydration or other adverse skin response, the architecture must be changed rather than marketing around the problem.

This document makes no clinical or dermatological performance claim.

## 14. Leave-on layering and non-wiping removal

Serum, moisturiser and sunscreen introduce a new requirement that does not exist in a cleanser-only architecture: Masck must apply a product and then avoid simply taking that product back off on its contact surfaces.

The final application system therefore needs to prove:

- controllable dose;
- appropriate spatial distribution;
- acceptable layer-to-layer interaction;
- no unacceptable cross-contamination between product circuits;
- appropriate settling or spreading time;
- no large residual pickup by the mask;
- a release/removal path that does not wipe the finished layers away.

This is one of the highest-priority new physical proof problems.

## 15. Sunscreen is a special hard case

SPF application should be treated as its own validation problem rather than merely another moisturiser-like fluid.

Masck must not infer that dispensing a labelled sunscreen automatically reproduces the protection stated on the bottle. The automated application system would need to establish appropriate dose, uniformity and final film performance through suitable testing and regulatory review.

The product promise should remain **complete facial skincare routine** rather than claiming that Masck replaces sunscreen application to every exposed body area.

If reliable automated facial SPF cannot be achieved, that is a direct challenge to the complete-morning-routine vision and should trigger a serious architecture review rather than being hidden.

## 16. Makeup/cosmetics boundary

'Complete facial skincare routine' is not automatically equivalent to 'complete cosmetics removal'. Heavy or waterproof eye makeup may create requirements that conflict with protected eye geometry and should remain an explicit unresolved problem.

The product must not silently claim complete automated makeup removal until it has an evidence-backed architecture for the relevant cosmetic load and protected regions. Market validation must determine whether this boundary weakens the proposition for important customer groups.

## 17. Hygiene, cleaning and changeover

A whole-routine platform will fail if ownership maintenance becomes more annoying than manual skincare.

The target is for the dock to automate or greatly simplify:

- fluid-path preparation;
- residue management;
- waste handling;
- reservoir/session-dose metering;
- product-change flushing or isolated-reservoir swap;
- charging;
- thermal reset;
- readiness verification.

The user should not be expected to manually clean several tiny product packets after each routine.

Separate chemistries must remain isolated where required. Reusable wetted paths need credible contamination, compatibility and cleaning strategies before the platform can claim broad product support.

## 18. Core validation / kill questions

The complete-routine concept should earn the right to continue through evidence. High-value proof questions include:

1. Can Masck cleanse effectively without unacceptable additional skin-barrier disruption?
2. Can it rinse/recover fluid without leakage or uncomfortable residue?
3. Can one application engine handle the practical rheology range from low-viscosity essence/serum through lotions and creams using adaptive control?
4. Can leave-on products be distributed reproducibly across real facial geometry?
5. Can multiple product stages remain adequately isolated and layered without the machine removing prior layers?
6. Can the final mask release preserve the finished facial film?
7. Can facial sunscreen application be validated to the required coverage/protection standard?
8. Can the complete system remain comfortable within mass, CG, torque, thermal and retention limits?
9. Can the dock make multi-product ownership low-maintenance rather than creating nightly refill/cleaning work?
10. Do users actually choose the complete Masck routine repeatedly over manual skincare when given both options?
11. Can all of this be manufactured at a retail price and gross margin that support the business?

Failure of one candidate mechanism is not automatically failure of the product thesis. Repeated failure of fundamentally different architectures against a core requirement should trigger a product-level rethink.

## 19. Commercial/product boundary

The current concept deliberately avoids making MASCK become a skincare-formulation company merely to make the hardware work.

The competitive advantage should be the ability to **identify, characterise, dose, sequence and physically apply the user's chosen skincare products automatically**.

The platform may still require bounded compatibility rules, validated product records and conservative behaviour for unknown formulations. Broad compatibility is a technical ambition that must be earned with data, not a universal marketing claim made in advance.

## 20. Relationship to existing Masck One engineering

Most existing work remains relevant to this broader concept:

- exterior / industrial design;
- facial fit and protected anatomy;
- retention and quick release;
- cleansing and water delivery;
- waste recovery and cartridge service;
- treatment/massage mechanics;
- WARM/COOL development;
- dry-side packaging;
- battery/electronics/HMI;
- dock architecture;
- deterministic CAD, source provenance and evidence firewalls.

Major new or substantially expanded work introduced by the whole-routine requirement includes:

- multi-product bulk storage and dock metering;
- isolated session-dose reservoirs/cassette;
- adaptive transport across broad skincare rheology;
- product identity and application database;
- product-change and contamination architecture;
- non-wiping leave-on deposition;
- contact-to-non-contact/retracted facial-interface transition;
- serum/moisturiser/SPF application evidence;
- scheduled routine orchestration;
- AI-assisted product classification/application-profile selection under deterministic limits;
- optional original LED/photobiomodulation architecture if justified by system cost/weight/benefit;
- whole-product mass/CG re-optimisation with filled fluid states.

These additions reduce the percentage-complete estimate for the **expanded product vision** relative to the former cleanser/treatment-only definition. Existing subsystem evidence remains valuable; it must not be discarded or misrepresented as proof of the new capabilities.

## 21. Immediate concept-level engineering priority

The highest-value next architecture study is a **complete-routine proof path**, beginning with a reduced facial/cheek rig before committing to full-mask geometry.

A useful proof sequence is:

`CLEAN -> RINSE/RECOVER -> TREAT/OPTICAL AS APPLICABLE -> SERUM -> MOISTURISE -> FINAL LEAVE-ON/SPF CASE -> NON-WIPING RELEASE`

The rig should focus on whether fundamentally different product rheologies can be transported, distributed, layered and left on the skin-facing test surface without cross-contamination or removal by the mechanism.

SPF should be treated as a dedicated hard-case validation program rather than assumed solved by success with serum or moisturiser.

At the same time, a packaging study should determine how many isolated session doses can be carried while preserving Masck One's mass, centre-of-gravity and facial-torque targets.

## 22. Product sentence

The working concept sentence is:

> **Masck One is an adaptive wearable system that automatically executes the user's complete facial skincare routine using the products they already choose. The dock prepares it, the mask understands and applies the routine, and when the mask comes off the facial routine is finished.**

This sentence is product intent, not a current performance claim.