# Masck One Website & App Engineering Handoff

## Purpose

This file is the sole maintained engineering handoff for the website and companion app.

Autonomous agents are **not** to build, redesign, deploy, refactor, optimize, or otherwise spend implementation time on the website or app. Their job is to engineer the physical Masck One product. After every materially released engineering iteration, they must still ask what the new product truth implies for the website and app, then record that implication here so the human-led digital work stays current.

This file is not engineering authority and does not promote physical evidence. The repository authority, schemas, released CAD/code, tests, preflights and evidence state remain controlling.

## Ownership and update rule

- **Cell 1 / Conductor owns edits to this file** to avoid multi-agent merge conflicts.
- Cells 2-5 must include a concise `DIGITAL_HANDOFF_DELTA` in their handoff whenever a material product change affects website/app requirements.
- Cell 1 must reconcile those deltas into this README after each merged engineering iteration or materially changed product architecture.
- Entries must cite the relevant iteration/PR/main SHA in plain text.
- Stale entries must be revised or marked superseded when engineering changes.
- No autonomous agent may use this README as permission to edit `products/web/` or `products/app/`.

## Status vocabulary

- `MUST_BUILD`: required for the website/app to represent the released product coherently.
- `SHOULD_BUILD`: high-value digital feature or explanation, but not required for basic fidelity.
- `OPTIONAL`: useful enhancement.
- `BLOCKED`: do not implement as factual/product-connected behavior until the named engineering/evidence dependency closes.
- `FORBIDDEN_CLAIM`: do not present publicly as established fact.

## Required entry format

For every material engineering iteration, maintain:

1. **Source**: iteration, PR and/or released main SHA.
2. **Physical product change**: what actually changed in Masck One.
3. **Website delta**: what should be added, removed, revised or animated.
4. **App delta**: what workflow, state, screen, copy or control implication exists.
5. **Required assets/data**: geometry, state definitions, renders, measurements or copy inputs the human builder will eventually need.
6. **Allowed claims**: evidence-backed statements the digital surfaces may make.
7. **Blocked/forbidden claims**: what remains validation-gated.
8. **Priority/dependency**: MUST_BUILD / SHOULD_BUILD / OPTIONAL / BLOCKED and the release/evidence dependency.

---

# Current engineering-to-digital backlog

Baseline checked against repository main `7eda0e80d28b068f40c716b94c4b3c9b7f8da085` on 2026-09-01. This list is a handoff backlog, not evidence of completed website/app implementation.

## Iteration 21: cleanser storage architecture

**Physical product change**
- Cleanser storage/refill architecture became a controlled product subsystem.
- Compatibility, purge behavior and real-world service burden remain evidence-bounded rather than universal.

**Website delta**
- `MUST_BUILD`: explain that the product is designed around user-supplied compatible cleanser rather than a proprietary cleanser-only proposition.
- `SHOULD_BUILD`: show refill/service interaction once final service geometry is released.
- `FORBIDDEN_CLAIM`: "works with every cleanser" or equivalent universal-compatibility language.

**App delta**
- `SHOULD_BUILD`: reserve a cleanser/refill guidance state.
- `BLOCKED`: automatic cleanser level, compatibility detection or remaining-cycle telemetry unless later hardware explicitly provides it.

**Required future inputs**
- final fill/service geometry; validated cleanser envelope; purge/cleaning instructions; any real sensing architecture.

## Iteration 22: dual fresh-fluid pump packaging

**Physical product change**
- Water and cleanser pumping remain distinct controlled paths with evidence-safe packaging semantics.

**Website delta**
- `SHOULD_BUILD`: internal cutaway/technical sequence can distinguish water and cleanser metering paths.
- Keep animation conceptual unless exact released route geometry exists.

**App delta**
- `BLOCKED`: pump speed/flow/pressure telemetry, pump-health readout or remote pump control unless later hardware/firmware authority explicitly adds it.
- `SHOULD_BUILD`: future fault/help copy may explain fluid-delivery faults once actual detection semantics exist.

## Iteration 23: fresh-fluid manifold topology

**Physical product change**
- Controlled topology now reserves 18 water and 6 cleanser outlets while preserving fluid identity.

**Website delta**
- `MUST_BUILD`: when showing internal distribution, depict water and cleanser as distinct branches and preserve the 18/6 architecture if still current at build time.
- `BLOCKED`: visually implying verified equal flow, pressure balance or efficacy from topology alone.

**App delta**
- No direct app control implied.
- `OPTIONAL`: explanatory cycle visualization may reference distribution phases, but must not masquerade as live measured fluid telemetry.

## Iteration 24: protected outlet and groove intent

**Physical product change**
- 24 outlet/groove intents are associated with active facial target regions while maintaining protected-zone clearance in development geometry.

**Website delta**
- `MUST_BUILD`: product explainer should communicate targeted facial distribution and avoidance of protected eye/mouth/airway regions without implying physical ingress validation.
- `SHOULD_BUILD`: once final registered geometry exists, use a truthful face-map or product cutaway rather than decorative/random fluid lines.

**App delta**
- `OPTIONAL`: cycle-progress visualization may later represent facial regions/zones.
- `BLOCKED`: per-region measured coverage or efficacy scores until physical evidence exists.

## Iteration 25: mixed-phase waste acquisition topology

**Physical product change**
- Five controlled facial waste-acquisition region intents preserve mixed air/liquid/foam/contaminant semantics and hand off toward active waste pumping.

**Website delta**
- `MUST_BUILD`: explain contained used-liquid acquisition as a core differentiator.
- `SHOULD_BUILD`: show collection regions and flow direction only from released geometry, not invented paths.
- `FORBIDDEN_CLAIM`: leak-proof, mess-free under all orientations, or verified recovery percentage until physical validation closes.

**App delta**
- `SHOULD_BUILD`: future maintenance/troubleshooting content should distinguish delivery faults from waste-recovery/service faults.
- `BLOCKED`: waste-recovery percentage or residual-liquid telemetry unless later sensing and validation explicitly support it.

## Iteration 26: mixed-phase waste pump architecture

**Physical product change**
- Waste pumping is explicitly treated as mixed-phase transport with controlled fault semantics rather than simple clean-water pumping.

**Website delta**
- `SHOULD_BUILD`: technical animation can explain active removal of used liquid, air and foam once route/geometry authority is released.
- Do not depict a specific production pump or pressure-flow behavior until selected and evidenced.

**App delta**
- `SHOULD_BUILD`: future fault UX should support waste-path blockage/service guidance if actual device detection semantics are implemented.
- `BLOCKED`: live pump/fault telemetry until real sensors/firmware exist.

## Iteration 27: waste cartridge architecture

**Physical product change**
- Cartridge insertion, sealing, capacity reservation and service interfaces are now part of the controlled architecture.
- The cartridge external bounding volume is not treated as usable retained capacity.

**Website delta**
- `MUST_BUILD`: show the replaceable/serviceable waste-cartridge concept and intended insertion/removal experience once final service geometry is released.
- `SHOULD_BUILD`: use exploded/service storytelling to make containment understandable.
- `FORBIDDEN_CLAIM`: exact retained volume, cycle count or leak performance as measured fact until validation supports it.

**App delta**
- `MUST_BUILD`: reserve cartridge/service workflow in information architecture.
- `BLOCKED`: automatic cartridge presence/fullness/remaining-cycle detection unless later hardware includes validated sensing.

## Iteration 28: full fresh/waste routing closure

**Current state**
- Active engineering work. Do not treat as released until exact-main/queue state confirms it.

**Website delta once released**
- `MUST_BUILD`: update any cutaway/exploded/fluid animation to use the released route identities and actual geometry available at that point.
- `BLOCKED`: inventing bend radii, tubing routes, dead volume, prime behavior or service clearance when those remain unresolved.

**App delta once released**
- `SHOULD_BUILD`: update maintenance/troubleshooting taxonomy to mirror real source -> pump -> distribution -> acquisition -> waste-pump -> cartridge architecture.
- No live route visualization unless telemetry exists.

---

# Upcoming hardware areas and anticipated digital implications

These are planning notes only. They must be rewritten from released engineering truth when each capability lands.

## Iteration 29: retention / halo / occipital / crown

**Website**
- likely `MUST_BUILD`: fit/retention explanation, donning sequence, perceived-bulk and load-distribution story.

**App**
- likely `SHOULD_BUILD`: fit/setup guidance.
- `BLOCKED`: fit sensing or retention-force readout unless hardware supports it.

## Iteration 30: one-hand wet unpowered quick release

**Website**
- likely `MUST_BUILD`: clear safety/service explanation showing the release is mechanical and unpowered.

**App**
- app must never become required for emergency release.
- likely `SHOULD_BUILD`: safety education/troubleshooting only.

## Iteration 31: battery/electronics dry bay

**Website**
- likely `SHOULD_BUILD`: charging and wet/dry isolation explanation once architecture is released.

**App**
- battery/status UX becomes meaningful only to the extent real telemetry and firmware interfaces exist.
- runtime claims remain validation-gated.

## Iteration 32: physical HMI

**Website**
- `MUST_BUILD`: product interaction story must match final physical controls exactly.

**App**
- any remote controls must remain subordinate to physical safety and device authority.
- do not invent modes, controls or sensors for digital richness.

---

# Cross-cutting website requirements derived from engineering

- Every product animation should ultimately map to released geometry/state truth, not decorative mechanism invention.
- Protected eye, mouth and airway regions must remain visually and verbally protected.
- Do not convert engineering targets into achieved claims.
- Clearly distinguish intended operation from physically validated performance.
- Final product imagery must use current released exterior geometry and CMF, not stale concept forms.
- When a hardware revision changes visible geometry, service sequence, fluid route, HMI, retention or cartridge interaction, the website backlog must be updated.

# Cross-cutting app requirements derived from engineering

- Never imply BLE, telemetry, sensing or remote control that the hardware does not actually implement.
- Safety-critical functions must not depend on app availability unless explicitly authorized by engineering authority.
- App state names must match released product-state terminology.
- Simulated/development data must remain visibly separate from real device telemetry.
- Maintenance workflows must follow actual refill, cleaning, cartridge and service architecture.
- New hardware faults should trigger a review of app error states, troubleshooting and user recovery flows.

# Claims firewall

Unless released evidence later supports them, the website/app must not claim or imply:

- universal cleanser compatibility;
- guaranteed cleansing efficacy;
- clinically proven performance;
- leak-proof or orientation-independent operation;
- verified comfort or pressure safety;
- exact runtime/cycle endurance;
- exact cartridge service life;
- verified thermal comfort/safety;
- measured waste-recovery performance;
- certified materials/compliance not actually obtained;
- sensors, telemetry or connected capabilities not actually implemented.

# Human builder workflow

When manually developing the website or app:

1. Start from the newest entries in this file.
2. Verify the referenced engineering iteration is actually released on `main`.
3. Pull exact current geometry/state/assets from the engineering repo where appropriate.
4. Build the digital experience yourself.
5. Do not edit engineering authority to make the digital experience easier.
6. If the desired website/app behavior requires a hardware capability that does not exist, treat it as a product question rather than silently faking it in UI.
