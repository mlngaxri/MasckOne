# MASCK ONE Core Sketch Decision Log

Status: **product-concept decision record**  
Date established: 2026-09-10

Use this file for decisions that materially alter or defend the stable Core Sketch. Ordinary implementation details belong in subsystem docs/PRs instead.

## D-001 — Complete routine is the product

**Decision:** MASCK ONE is defined by autonomous completion of a supported facial skincare routine, not by any one treatment modality.

**Reason:** Cleansing-only automation does not preserve the portability/convenience thesis if the user must then manually apply leave-on products.

**Consequence:** Cleanse, treatment, leave-on application, protection and non-wiping release are organized under one routine state model.

## D-002 — User’s own skincare is the default ecosystem

**Decision:** MASCK should adapt to third-party consumer skincare rather than require MASCK formulations.

**Reason:** A proprietary skincare requirement would force MASCK to compete simultaneously as a chemistry brand and would weaken the promise that the system executes the routine the user already values.

**Consequence:** Product identification, characterization, compatibility and bounded adaptive application become core platform capabilities.

## D-003 — Bulk product lives in the dock

**Decision:** The dock stores bulk products; the wearable carries only the session quantities required for the prepared routine.

**Reason:** Product variety must not destroy loaded mass, CG, comfort or exterior quality.

**Consequence:** Dock preparation, session-dose isolation and whole-product mass/CG are P0 work.

## D-004 — AI is subordinate to deterministic safety

**Decision:** AI may identify, classify, organize and estimate; it may not override hard application/safety rules.

**Reason:** Product identity and formulation behavior are uncertain inputs, and user-facing skincare automation cannot rely on an unconstrained model deciding dose/compatibility/safety.

**Consequence:** Product profiles, evidence states, physical checks and deterministic bounds remain the execution authority.

## D-005 — Scheduled routines are core UX

**Decision:** Users can create recurring AM/PM/day-of-week routines and today-only overrides.

**Reason:** The dock can prepare the likely next session automatically, reducing ordinary use to grab/place/start/remove/return.

**Consequence:** Routine object model, weekly schedule, local cache and prepared-routine change handling are required.

## D-006 — Optical treatment is a capability, not the archetype

**Decision:** Red/NIR/deeper-NIR treatment may be integrated if justified and validated, but MASCK is not designed as an LED mask.

**Reason:** The product’s differentiation is whole-routine automation; copying LED-mask form language would compromise hygiene, premium ID and complete-routine hierarchy.

**Consequence:** Competitor wavelength/count information is benchmark research only. MASCK optical geometry/electronics/UX remain original.

## D-007 — CurrentBody implementation is not copied

**Decision:** Public CurrentBody specifications may benchmark output territory; hardware layout, firmware, mask geometry, LED count and visual execution are not design authority.

**Reason:** CurrentBody hardware is proprietary and its flexible silicone-mask architecture conflicts with MASCK’s product language.

## D-008 — Makeup is outside V1 complete-routine scope

**Decision:** Decorative cosmetics are a separate category from the V1 complete facial-skincare promise.

**Reason:** Waterproof eye makeup/foundation removal would substantially expand contact, eye-area, chemistry and validation scope.

**Consequence:** Future agents must not add automatic makeup removal implicitly.

## D-009 — Facial SPF remains a high-rigor separate proof problem

**Decision:** Facial sunscreen application is desirable and remains in the target routine, but is not assumed solved by dispensing a known volume.

**Reason:** Final protection depends on appropriate application amount, spatial film uniformity, boundaries and regulatory/claims requirements.

**Consequence:** SPF has its own P0 validation lane and may not use direct aerosol spraying as the default assumption.

## D-010 — Non-wiping release is skincare functionality

**Decision:** Final release geometry/behavior must preserve leave-on layers.

**Reason:** A technically successful application stage that is wiped away during removal violates the complete-routine promise.

**Consequence:** Release is jointly owned by retention/removal and leave-on application verification.

## D-011 — Calm sensory grammar

**Decision:** Normal state language is restrained Opal-neutral light, limited haptics and near-silent operation.

**Reason:** Warmth, buzzing, beeping and rainbow state colors are often activity theatre rather than treatment evidence and conflict with the premium personal-care direction.

**Consequence:** No routine chirps, RGB bars, intentional metallic ping or visible LED-strip decoration.

## D-012 — Limited size family + adaptive fit is the current hypothesis

**Decision:** Develop toward the smallest viable size family, likely 2–3 sizes if evidence requires, with strong passive/adaptive fit.

**Reason:** One rigid universal size is unlikely to respect facial variation; individually custom hardware creates unnecessary ownership/manufacturing burden before evidence requires it.

**Consequence:** Anthropometric/fit testing decides the final count.

## D-013 — Offline normal use

**Decision:** Once configured, normal routine execution and safe release work without cloud/phone/internet.

**Reason:** A daily personal-care appliance should not become unusable because an external service is unavailable.

## D-014 — No skin-surveillance product by default

**Decision:** No continuous face camera, beauty score, acne/pore/wrinkle scoring, emotional inference or always-listening microphone by default.

**Reason:** Those features are not required to execute the core routine and add privacy/anxiety/product-drift cost.

## D-015 — Dock is premium personal care, not laboratory/kitchen appliance

**Decision:** The dock must be pressure-tested for compactness, visual calm and home suitability.

**Reason:** A technically convenient oversized service station would undermine the ownership experience and portability thesis.

## D-016 — Full research is preserved, not blindly selected

**Decision:** Exploratory deep-research output is archived in full, while selected/rejected ideas are triaged separately.

**Reason:** The team should retain useful research without allowing generic competitor/gadget ideas to become accidental requirements.

## D-017 — Completion is required-region and context specific

**Decision:** CS-015 defines complete selected-session evidence; legacy aggregate cleansing coverage and pump telemetry cannot certify a finished leave-on routine.

**Reason:** Required patches, stationary support shadows and layered-product context were not fully represented by the earlier completion wording.

**Consequence:** CS-018 accounts for every contact state. No protected region or required stage is silently removed. Normal non-wiping release and immediate unpowered emergency release retain different acceptance conditions. D-010's shared responsibility is implemented by Lane 1 acceptance input and one Lane 3 release-geometry producer.

## D-018 — Readiness binds physical preparation

**Decision:** A versioned prepared-session contract is selected; READY is conditional at use, not permanent after docking.

**Reason:** Overrides, missed routines, hold history, changed contents and partial delivery can invalidate an otherwise valid schedule.

**Consequence:** CS-016 belongs to Lane 4; Lane 2 supplies the physical receipt. No duplicate uncertain dose, stale-ready promotion or silent network dependence. Saved routines remain distinct from temporary sessions.

## D-019 — Product preservation is separate from identity

**Decision:** Dock bulk storage is retained, but no universal open refill/decant interface is selected. Product validation is scoped to its formulation, storage, delivery and routine context.

**Reason:** A correct label and plausible flow behavior cannot prove unchanged formulation, preservation or compatible layers.

**Consequence:** CS-017 and strengthened CS-080/094 are existential work. No AI/community promotion, assumed shelf life or formulation modification is used to evade the gate.

## D-020 — Replace the topic-order waterfall with six proof gates

**Decision:** G0..G5 in the backlog control new work admission. SPF-containing AM feasibility and real compatibility/ownership value begin early alongside reduced-region evidence.

**Reason:** The previous sequence could spend heavily on ID and optional features before discovering a full-routine contradiction.

**Consequence:** CS-293 becomes P0; qualified physical unknowns stay blocked. Bounded current-owner corrections can finish in parallel; a green legacy suite does not freeze the expanded product.

## D-021 — Retain five lanes, assign one producer per interface

**Decision:** The five outcome lanes survive; the shared-artifact table in the five-lane plan resolves writing ownership and acceptance responsibilities.

**Reason:** Joint responsibility without one geometry/schema producer risks parallel architectures at the contact/release, dose/preparation and mass-budget boundaries.

**Consequence:** Existing owner branches are preserved. New Lane 4 work needs explicit activation; the conductor integrates and cannot override protected geometry or physical-validation criteria.

## D-022 — One concept lineage, no silent authority changes

**Decision:** PR #148 is the canonical concept continuation. PR #147's product thesis was reviewed for unique requirements; its complete-routine, product-choice, barrier, makeup-boundary and SPF cautions are retained in this lineage. Its conservative-estimate language does not authorize unknown-product application.

**Reason:** Two concurrent concept documents must not become competing architecture truth.

**Consequence:** Reconcile PR #147 as superseded after publishing this update. Preserve its history. Machine engineering and brand authority remain unchanged; the Aperture/M-Cut primary-control assignment is recorded under CS-043 for the existing owners.
