# MASCK ONE Core Sketch Deep Research Archive — 2026-09-10

Status: **research archive; not engineering authority and not automatically accepted product intent**

Purpose: preserve the complete deep-research output that informed the current core-sketch work. This file is intentionally archival. Some ideas below were later rejected or superseded by the triaged core sketch and execution backlog. Future work must treat `docs/CORE_SKETCH_V1.md` and `docs/CORE_SKETCH_EXECUTION_BACKLOG.md` as the actionable product-definition layer, and must continue to defer to released engineering authority for physical truth.

---

# Masck One: Complete Autonomous Facial-Skincare System (Core Sketch)

**Executive Summary:** Masck One is a wearable appliance that **automates an entire facial skincare routine** from start to finish. The user simply **places Masck on the face and presses a button**; when it releases minutes later, the routine is complete. Masck first **cleanses and gently rinses** the skin (recovering the fluids), then optionally performs an **LED phototherapy treatment**, and finally **applies the user’s own serum, moisturizer and, in the morning routine, SPF** — all **in one sequence with no further user steps**. By dividing bulk product storage into a home **dock** and carrying only microdoses in the mask, Masck remains highly **portable and lightweight**. A key design goal is **barrier safety**: fluidic cleansing and sonic action are tuned so as not to worsen transepidermal water loss beyond a gentle manual wash. Sunscreen application is designed to deliver a validated final film rather than merely a metered volume. The system uses a growing **product profile database** to recognize and meter the user’s own skincare products (via barcode/OCR/label parsing) into routine slots. Intelligence in Masck’s dock and app orchestrates schedules (e.g. alternating Day/Night routines) and adapts application parameters to each formula, but **AI does not replace validated application recipes or safety limits**. Offline and privacy-conscious, Masck One only operates within bounded application rules.

## Product Mission and Non-negotiables

Masck One’s mission is unequivocal: **“Put on Masck, press start, take it off, and your facial skincare routine is done.”** To achieve this, Masck must:

- **Automate 100% of steps for the supported facial skincare routine** without requiring the user to touch the face between start and finish. Any break in this chain (for example needing to apply moisturizer by hand) violates the core promise.
- **Preserve skin-barrier comfort and integrity** relative to an appropriate gentle manual routine. This remains a physical-validation requirement.
- **Adapt to the user’s own products** rather than force proprietary MASCK skincare. Users load their familiar cleanser, serums, moisturizer and sunscreen, which Masck identifies and applies through a validated profile system.
- **Deliver true routine portability**: after preparation in the dock, the wearable performs the routine without a sink, bottles or manual leave-on application.
- **Preserve evidence honesty**: especially for sunscreen, correct metering does not equal proven protection. Final deposition, uniformity and relevant regulatory claims require physical validation.

## User Personas and Willingness-to-Pay Research Notes

Likely early users include skincare enthusiasts and premium beauty-tech adopters who value consistency, time saving, validated performance and refined object quality. Prior market research observed premium home beauty devices in the several-hundred-dollar range, supporting exploration of premium positioning, but no retail price is frozen by this research archive.

## Routine Flow & UX Research Concepts

Research explored a sequence of **CLEAN → RINSE/RECOVER → TREAT (LED) → APPLY SERUM → APPLY MOISTURIZER → APPLY SPF (AM only) → RELEASE**. Distinct state changes were considered useful, provided they do not rely on fake activity or unnecessary noise.

- **CLEAN:** active, controlled cleansing with the user’s loaded cleanser and deliberately mild physical sensation.
- **RINSE/RECOVER:** removal of cleanser and spent fluid, with a clear transition toward a clean-face state.
- **TREAT / OPTICAL:** mechanically quiet optical treatment performed on clean skin before leave-on products.
- **SERUM:** transition to non-cleansing leave-on application, avoiding subsequent wiping.
- **MOISTURIZER:** broader final conditioning layer, again without later contact that strips it away.
- **SPF:** morning-only facial sunscreen stage, requiring evidence of appropriate final coverage before any protection claim.
- **RELEASE:** non-wiping withdrawal so leave-on layers survive removal.

**Scheduling & overrides:** users can define routine templates such as Morning, Night and Treatment Night; assign them by weekday/time; and make one-session changes such as “skip LED tonight” without altering the recurring schedule. Normal daily use should not require opening the app.

## Product Database & Identification Research Concepts

Masck maintains a product library spanning cleanser, serum/essence, moisturizer and sunscreen classes. Users identify products when loading them using barcode/QR, packaging/label recognition, OCR/search and, where useful, ingredient-list confirmation. The system then links that identity to an application profile.

Unknown products may undergo a bounded physical flow/application calibration. Community usage can accelerate identification and characterization, but **formal safety/application validation is not crowdsourced**. A useful internal trust ladder is:

- **KNOWN:** identity resolved.
- **CHARACTERISED:** application behavior sufficiently characterized.
- **VALIDATED:** Masck has verified the intended application profile to its required evidence standard.
- **RESTRICTED / UNSUPPORTED:** not permitted for automated application in the current system.

Reformulations must be treated as potentially distinct from prior SKUs/formulation revisions.

## Dock & Wearable Division Research Concepts

The research strongly supported separating **bulk storage in the dock** from **session microdoses in the wearable**. The dock can store the user’s bulk skincare products, clean/service the fluid path, manage waste, charge the wearable, reset thermal functions and meter the next routine’s isolated session quantities into the mask.

The wearable should carry only the quantities required for the next routine so the number of supported skincare products does not directly translate into large on-head product mass.

Earlier brainstorming suggested several bulk slots for cleanser, one or more treatments, moisturizer and SPF. Exact slot count, volumes and internal transport mechanisms remain unresolved and must be derived from UX/product-compatibility requirements rather than copied from this archive.

A future travel-support architecture was also considered: the V1 home dock should not preclude a later compact travel module, but V1 should not depend on that accessory.

## Adaptive Application Engine Research Concepts

The system concept requires adaptive application across materially different product classes. Product identity, known profile information and measured flow/pressure response can inform a bounded delivery profile. The controller should detect material deviation from an expected product signature and stop or request confirmation rather than blindly apply an unknown material.

A unique product-level requirement is a **two-state facial interface**: contact/near-contact behavior suitable for cleansing and recovery, followed by a leave-on application state that does not subsequently wipe the deposited layer away. Exact mechanisms are intentionally outside this core-sketch research.

## SPF Deposition Research Notes

Sunscreen is the hardest leave-on stage because application quality depends on final-film amount and uniformity, not just dispensed volume. Regulatory and dermatology sources commonly discuss standardized sunscreen test/application quantities near 2 mg/cm², while real users often underapply. Therefore Masck must eventually validate its actual facial deposition process and avoid implying protection to ears, neck or body regions it does not cover.

The deep-research draft mentioned mist/spray approaches. That is **not an accepted architecture**. Aerosolization near the face raises inhalation and eye-exposure concerns and must not be treated as the default solution. The stable core sketch only requires a validated, non-wiping, uniform final-film result.

## Optical Treatment Research Notes

Research used CurrentBody Series 2 as a functional benchmark for a three-band optical treatment around **633 nm red, 830 nm near-IR and 1072 nm deep near-IR**. A benchmark around premium consumer irradiance and roughly 10-minute treatment durations was explored. These numbers are **not automatically frozen MASCK specifications** and the CurrentBody LED count, PCB, mask geometry, firmware and optical layout are not to be cloned.

Masck’s optical system must be original, integrated into the rigid/semi-rigid facial architecture, visually disappear when inactive, respect eye safety and fit the complete-routine hierarchy. Optical treatment is a capability within Masck, not the identity of the product.

## Sensory Language Research Concepts

The research supported a deliberately quiet interface: a restrained status light, subtle haptics only where they carry real information, silence through most treatment stages, and a clear completion state. It rejected the idea that warmth, buzzing or beeping should be used merely to prove that the product is “working.”

Earlier exploratory wording used blue/amber/green state colors and completion chimes. Those are **not accepted MASCK language** and are superseded by the Opal-neutral sensory grammar in the triaged core sketch.

## Fit, Sizing and Accessibility Research Concepts

Research considered one-handed operation, large eye openings, compatibility with common hair arrangements, tactile loading features for low-vision/color-blind users, app accessibility labels and rapid emergency removal. Earlier generic references to VR-like straps are superseded and must not guide the Masck visual or placement experience.

The preferred stable direction is limited-size/hybrid fit with strong passive adaptation and self-alignment, avoiding a multi-strap adjustment ritual.

## Hygiene and Maintenance Research Concepts

Skin-adjacent materials must be non-absorptive, cleanable, inspectable and resistant to residue accumulation. The dock is expected to handle most routine service automatically, but the user must be able to visually understand whether the facial interface is clean. Dark hidden crevices, permanently wet pockets and “trust us” hygiene are unacceptable.

Earlier research floated automatic purge cycles, replaceable gaskets and washable contact parts. These remain product-level candidates; exact cleaning chemistry and mechanisms are not frozen here.

## Failure-State UX Research Concepts

The device should fail calmly and actionably for low product, product mismatch, empty slot, poor seating, early removal, unavailable stage, missed docking and offline conditions. Errors should use plain-language guidance rather than codes. Safety-critical states may escalate, but normal service states should not become alarm theatre.

## Offline, Privacy and Data Research Concepts

Once configured, Masck must remain usable offline without a phone, cloud session or account authentication. Camera/OCR is for deliberate product identification, not continuous face observation. The default product concept does not include skin scoring, beauty scores, pore/acne grading, passive facial surveillance or anxiety-producing dashboards.

## AI and Learning Research Concepts

AI is an **orchestrator and estimator**, never the safety authority. It may help identify products, classify unknown formulations, retrieve relevant application families and assist with routine organisation. Hard dose, sequence, compatibility, wear-state and safety limits remain deterministic. Over time, aggregate product/application telemetry could refine application profiles, but model output must stay bounded by validated envelopes.

## Manufacturing / CMF Research Notes

The exploratory report mentioned ABS/polycarbonate shells, skin-safe silicone/TPE, matte/satin surfaces and premium neutral colors. The stable MASCK CMF direction supersedes that generic wording:

- Mineral Ivory `#E9E5DC` shell
- Warm Porcelain `#DED9CF` user control
- Soft Stone `#CFC8BC` facial contact
- Smoke Graphite `#454542` rear/mechanical
- Opal Neutral `#F2EFE7` unlit optical/status language

Specific production material grades/processes remain engineering selections requiring qualification.

## Unboxing Research Concepts

The research supported a compact, restrained kit: mask, dock, essential power/service accessories and minimal onboarding material. No tangled cables, clinical trays or oversized manuals. The first-run experience should move directly from product reveal to product loading, fit confirmation and first routine.

## Validation Research Notes

The research proposed several evidence paths that remain useful as concept-validation prompts, not frozen study protocols:

- compare post-routine skin-barrier/hydration indicators with a suitable gentle manual control;
- validate sunscreen final-film uniformity and relevant protection claims using appropriate standardized methods;
- test the complete sequence on a reduced cheek/full-routine rig before committing the entire face architecture;
- run usability studies for placement, comfort, routine completion, service/loading and willingness to adopt;
- separately study willingness to pay rather than deriving price from competitor MSRP alone.

## Archived Feature Matrix

The original research grouped these areas: automated cleansing, fluid rinse/recovery, optical treatment, multi-product dosing, non-wiping interface transition, adaptive dosing/application intelligence, bulk dock, session micro-reservoirs, portable operation, product database/identification, mobile scheduling and a possible future travel dock.

Items such as voice assistants, face displays, RGB lighting, generic skin moisture scoring, automatic blue-light modes, UV-cleaning theatre and VR-style fit are **not accepted** merely because they appeared in exploratory research.

## Research Sources Preserved from the Deep-Research Session

The research session drew on:

- peer-reviewed work on sonic/manual facial cleansing and post-cleansing skin hydration/TEWL;
- peer-reviewed sunscreen-application literature discussing standardized application density and real-world underapplication;
- FDA/TGA sunscreen-use and regulatory guidance;
- CurrentBody Series 2 public optical specifications as a market benchmark, not an engineering source;
- premium beauty-device and wearable UX precedents.

The exact external links/citation snapshots originated in the deep-research session and should be independently re-verified before being promoted into an engineering or regulatory decision.

---

## Archive interpretation rules

1. This file preserves **all substantive ideas from the research report**, including ideas later rejected.
2. A feature appearing here does not make it selected.
3. `docs/CORE_SKETCH_V1.md` is the selected product-experience direction.
4. `docs/CORE_SKETCH_EXECUTION_BACKLOG.md` is the triaged step-by-step work program.
5. `config/masck_one_authority.yaml`, released CAD/code and accepted physical evidence remain controlling for engineering truth.
