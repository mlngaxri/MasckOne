# MASCK ONE Digital Product Vision

Status: **product and digital experience vision; not engineering authority**  
Updated: 2026-09-04

This document defines the intended MASCK ONE website, companion app, backend and commercial digital experience. It is deliberately downstream of physical engineering authority. `config/masck_one_authority.yaml`, released engineering code/CAD, validation evidence and `DIGITAL_PRODUCT_HANDOFF_README.md` remain controlling for what the hardware actually supports and what may be claimed publicly.

A digital feature may be visually and architecturally finalized before the physical dependency exists, but it must remain capability-gated and may not masquerade as live hardware behavior. Simulated development data must never ship as real telemetry.

## 1. Product ecosystem

MASCK ONE is one product expressed through three tightly related surfaces:

1. **Physical MASCK ONE** — the primary product. Basic use, safety-critical operation and emergency removal must remain possible without the app unless future released engineering authority explicitly changes that rule.
2. **MASCK ONE mobile app** — a real iOS and Android companion for ownership, use history, device settings when a compatible device is actively worn, care, service, troubleshooting and account/preorder management.
3. **MASCK ONE marketing website** — an Awwwards-level product showcase that explains the product, systems and evidence, presents the actual companion-app UI, and supports real commercial interactions without overstating hardware readiness.

The brand rule across all three surfaces is: **quiet interface, expressive product, expressive physics**. The product and useful interaction should carry attention; decorative UI and excessive copy should not.

## 2. Mobile app platform target

The companion app is intended to ship as a genuine mobile application across modern iOS and Android phones, with responsive layouts that remain usable on common tablet sizes where supported.

The implementation should use a shared cross-platform codebase unless native platform requirements later justify divergence. A TypeScript React Native / Expo architecture is the default digital direction because it permits one maintainable iOS/Android application while retaining native navigation, haptics, accessibility and BLE integration paths. This is a software architecture preference, not a physical-product requirement.

The app must be built as a real application, not a static prototype. Screens whose hardware functions are not yet available must still be production-quality UI backed by explicit capability interfaces rather than hard-coded pretend telemetry.

## 3. App information architecture

The target app should stay small and ownership-focused rather than becoming a generic smart-device dashboard.

### Home

Home should answer, at a glance:

- what the user last did with MASCK ONE;
- whether a compatible device is connected;
- whether the device is currently confirmed as worn when the hardware can provide that state;
- the most useful next action;
- care/service reminders only when supported by real data or explicit user-entered state.

The screen must remain useful even with no device connected.

### Sessions

The app should provide a clear history of previous MASCK ONE uses once the released device can report or synchronize session data.

Target non-health session metrics include:

- session date/time;
- session duration when available;
- completed/interrupted state when available;
- product mode or user-selectable configuration used, but only for modes/settings actually released by hardware;
- setting snapshot for the session where supported;
- weekly/monthly use count;
- total recorded sessions;
- service or cartridge events associated with use where supported.

These are **device-usage metrics**, not skin-health, medical or beauty scores. The app must not invent skin analysis, treatment efficacy, hydration, acne, pore, cleansing-quality or similar health/cosmetic metrics.

Until session telemetry is released, the complete visual treatment and data architecture may be finalized with clearly development-only fixtures, while production builds show truthful empty/disconnected states.

### Device

The Device surface should contain connection state, wear state, supported settings and contextual controls.

Control is permitted only when all of the following are true:

1. a compatible MASCK ONE is actively connected through the released device transport;
2. the device advertises the relevant control capability;
3. the hardware provides a sufficiently trustworthy worn/not-worn state;
4. the current state is `CONFIRMED_WORN` for controls that require the product to be worn;
5. no released safety interlock forbids the command.

If any prerequisite is absent, the app must disable the control and explain the immediate reason without fabricating a state.

The app must never replace the physical emergency release or make basic safe removal dependent on Bluetooth, network access, a phone or an account.

### Care and service

Care should include:

- cleanser/refill guidance;
- cartridge servicing;
- routine cleaning;
- storage guidance;
- troubleshooting by observable symptom;
- hardware-specific maintenance only when released engineering geometry supports it.

Universal cleanser compatibility, exact cartridge life, exact remaining fluid and automatic service prediction remain blocked unless physically validated and sensed.

### Account and preorder

The app and website should share a real account/commercial backend. A user should be able to create an account, manage contact details, register interest/reservation/preorder state and later associate owned devices when the product reaches that stage.

## 4. Wear-state detection is a required future product capability

The final connected-product vision requires the physical product to expose a robust `worn_state` or equivalent signal to the companion app.

The engineering implementation is intentionally not prescribed here. It may ultimately use contact, proximity, retention/latch state, pressure/contact sensing, a validated combination of signals, or another released architecture.

Digital requirements are:

- states must distinguish at least `UNKNOWN`, `NOT_WORN` and `CONFIRMED_WORN`;
- transient or stale state must fail closed for wear-gated controls;
- the app must display state changes without implying greater certainty than the hardware provides;
- control availability derives from capability/state rather than from a decorative UI toggle;
- the state contract must be versioned so later hardware revisions remain compatible.

This requirement is a **product dependency**, not evidence that such sensing exists today.

## 5. Device control and settings

The final UI should be aesthetically complete even before physical control transport is released.

The software should expose a `DeviceAdapter` / capability boundary such that real BLE or future transport can replace development adapters without redesigning the app.

The final control surface may include settings only after the hardware exposes them. Do not hard-code speculative controls as production features. Each control should be generated from or checked against a released capability descriptor.

Production behavior:

- connected + capability present + required wear state confirmed → control enabled;
- connected but not worn → wear-gated control disabled;
- state unknown/stale → control disabled;
- disconnected → control disabled, app remains otherwise useful;
- unsupported setting → control absent rather than fake-disabled forever.

Development builds may use simulated adapters for UI testing, but fixtures must be visually/dev-environment labelled and excluded from production telemetry.

## 6. Backend and commercial architecture

The target digital backend is a real production-capable service rather than browser-only fake interactions.

### Supabase

Supabase is the preferred first backend for:

- authentication;
- user profile/account records;
- preorder/reservation records;
- device ownership records when supported;
- synchronized session history when device telemetry exists;
- user-entered care/service state where useful;
- row-level security and privacy boundaries;
- optional realtime synchronization where it materially improves UX.

The schema should be versioned and migrations committed to the repository.

### Preorder/payment path

The website must have a genuinely functioning commercial interaction rather than a decorative preorder button.

Current engineering authority has `paid_preorder_gate: false`, so the live system must distinguish **real reservation/interest capture** from **charging a customer**.

Build now:

- real account creation/sign-in;
- real preorder/reservation form validation;
- real Supabase persistence;
- confirmation state and account view;
- duplicate/idempotency handling;
- email/status architecture where a transactional provider is configured;
- final payment-step UI and backend interface behind a capability/launch gate.

When the paid-preorder gate is legitimately opened, a PCI-compliant provider such as Stripe should handle payment; raw card details must never be stored in Supabase. Until then, production must not charge while claiming an authorized paid preorder exists.

The design of the paid flow can be finalized now so activation later is an integration/configuration change rather than a redesign.

## 7. Website app showcase

The marketing website must visibly showcase the companion app as a first-class product feature.

This showcase must use the **actual app UI**, not an independently drawn fake phone interface that can drift from the real application.

Preferred workflow:

- app screens/components are the source of truth;
- deterministic app screenshots or shared design assets are exported from the real app build;
- the website presents those screens in an interactive product-phone composition;
- scroll/pointer choreography may transition through Home, Sessions, Device, Care and service states;
- website copy explains the value of the app without pretending unavailable telemetry is already live.

Example visual story:

1. phone enters beside the physical product;
2. session history cards resolve into view;
3. the device view transitions from disconnected to a clearly labelled future/capability-backed connected state in development previews only;
4. controls reveal only where wear state is confirmed in the real product state machine;
5. care/service UI transitions to the physical cartridge/product imagery.

The website may use sophisticated animation, but app screenshots and metrics shown publicly must remain truthful to the release state. Development previews can use labelled simulated data; production marketing must not pass fixtures off as real user telemetry.

## 8. Brand and UI design system

Website, app and website app-showcase must feel unmistakably related while respecting their different jobs.

### Shared character

- calm;
- premium;
- tactile;
- intelligent;
- minimal without becoming sterile;
- advanced without looking futuristic for its own sake;
- product-showcase rather than fashion/editorial spectacle.

### Product imagery

Final imagery must follow current released exterior geometry and the strongest properly qualified physical-ID direction. Reject goggles, Venetian/masquerade styling, superhero forms, VR forms, aggressive eye geometry, nose cones, front actuator pods and unsupported glossy sci-fi finishes.

### Typography

Typography is not considered frozen by this document. Before final release, the digital team must research currently available, properly licensed high-quality type families and compare them in rendered context. The final system should have a distinctive display voice, an exceptionally readable UI/body face and a restrained technical/metadata voice. Font selection must be based on visual quality, licensing, performance, variable-font support and mobile legibility rather than familiarity.

### Motion

Motion should explain product behavior or create tactile brand character. Key display text may use high-quality interactive deformation/dissolve/wind/bend effects on desktop, but those effects must remain readable, performant and brand-consistent. The team may study publicly available Awwwards/Codrops/WebGL/creative-development references and licensed/open demonstrations, then implement original production code rather than copying proprietary site code.

The existing coded MASCK/ONE moving banners remain the only banner/ribbon treatment. Do not introduce static banner artwork.

## 9. Website commercial experience

The final website should contain, in addition to Architecture / Systems / Proof where still appropriate:

- a restrained but visually strong companion-app showcase;
- a real preorder/reservation interaction connected to the backend;
- clear product/account state after submission;
- legal/evidence-safe wording based on the current paid-preorder and physical-validation gates.

Commercial functionality must not weaken the art direction. A preorder interface should feel like part of the same product system, not an ecommerce template pasted under an Awwwards landing page.

## 10. Data and privacy principles

- collect only data needed for an actual feature;
- no health/skin scoring by default;
- no location permission by default;
- no camera permission by default;
- Bluetooth permission only when a real device integration exists;
- notifications only for real user value and truthful triggers;
- clear separation between local, cloud and device-originated data;
- production fixtures must never be stored as real session telemetry;
- Supabase row-level security must prevent cross-user access;
- secrets belong in environment/secret management, never committed source.

## 11. Build-now versus dependency-gated matrix

### BUILD AND FINALIZE NOW

- complete iOS/Android app codebase and visual system;
- Home, Sessions, Device, Care, Service, Account and preorder UX;
- responsive mobile layouts and interaction states;
- accessibility, hover/press/focus/haptic states where platform-appropriate;
- local/session data model;
- device adapter/capability interfaces;
- `worn_state` UI and state machine;
- simulated development adapter excluded from real telemetry;
- Supabase auth/profile/preorder schema;
- real reservation/interest persistence;
- payment-provider abstraction and final payment UI behind launch gate;
- website app showcase using real app UI;
- website account/preorder interaction;
- shared design tokens/assets where appropriate;
- final product imagery pipeline;
- production-quality empty/disconnected/unsupported states.

### DEPENDENCY-GATED

- live BLE/device transport until hardware protocol exists;
- trustworthy wear-state signal until physical sensing/state architecture exists;
- live session synchronization until device records/exports it;
- remote/device control until released capabilities and safety rules allow it;
- exact fluid/waste/cartridge telemetry until sensors exist and are validated;
- paid charging while `paid_preorder_gate` is false;
- any performance/efficacy claim lacking physical evidence.

The visual design and software interfaces for dependency-gated features should nevertheless be finalized now so later hardware integration replaces adapters/data sources rather than forcing a visual redesign.

## 12. Definition of digital completion

The digital program is complete when:

- the marketing website is direct-deployed, responsive, accessible, performant and visually release-quality;
- final product imagery is consistent with current product truth;
- the website includes the actual app experience and real backend-backed reservation/preorder interaction;
- the companion app runs as a real iOS/Android application from one maintained codebase;
- the app has final visual states for connected, disconnected, worn, not worn, unknown, supported and unsupported capabilities;
- real backend/account/reservation paths are tested end to end;
- development-only hardware simulation cannot leak into production as real data;
- future BLE/wear-state/session/control integrations have explicit interfaces and tests;
- website and app share one product/brand truth rather than diverging mockups;
- all public claims still pass the current engineering handoff and evidence gates;
- remaining blockers are genuinely physical-hardware, validation, payment-activation or store-signing dependencies rather than unfinished digital design.
