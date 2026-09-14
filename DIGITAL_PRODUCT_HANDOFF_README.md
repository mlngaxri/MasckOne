# Masck One digital product handoff

## Purpose

This document connects the released engineering state of Masck One to the website, companion app and other public-facing digital work.

Its purpose is simple: digital experiences should explain the product clearly without presenting development geometry, engineering targets or future capabilities as validated product performance.

Engineering authority remains with the released source, configuration, tests, preflight checks and evidence state. This handoff translates that information for digital product work; it does not override it.

## Source of truth

Before using a technical statement, visual or interaction in the website or app, verify it against the current released `main` branch and the relevant engineering authority.

The primary engineering source is:

```text
config/masck_one_authority.yaml
```

The current program position is tracked in:

```text
docs/DEVELOPMENT_ROADMAP.md
```

Do not rely on an old screenshot, render, branch or concept document when a newer released source exists.

## Evidence vocabulary

The digital product should preserve the repository's distinction between design intent and validated performance.

| State | Meaning for digital work |
| --- | --- |
| `MUST_BUILD` | Required for a faithful digital representation |
| `SHOULD_BUILD` | High-value product or information architecture |
| `OPTIONAL` | Useful but nonessential |
| `BLOCKED` | Do not present as implemented or factual until the named dependency closes |
| `FORBIDDEN_CLAIM` | Do not present as an achieved product result without supporting evidence |

## Current fluid-system representation

The released engineering architecture separates fresh water, cleanser and mixed waste as distinct fluid domains. The system includes controlled source, pump, distribution, acquisition, waste-pump and cartridge handoffs.

This supports accurate high-level explanation of the product architecture. It does not, by itself, establish measured pressure balance, leak resistance, cleansing efficacy, exact prime volume, recovery efficiency or orientation-independent operation.

### Website

`MUST_BUILD`: technical cutaways or fluid animations should preserve the released direction of flow and keep fresh water, cleanser and mixed waste visually distinct.

`BLOCKED`: do not depict hidden tubing, branch geometry, cartridge internals, service trajectories or backflow hardware as factual unless the relevant realized geometry has been released.

`BLOCKED`: do not imply verified equal flow, measured pressure balance, exact prime or purge behaviour, measured dead volume, verified waste recovery or cleansing efficacy from digital topology alone.

### App

Future maintenance and troubleshooting information may follow the real subsystem taxonomy once corresponding device capabilities exist.

`BLOCKED`: reservoir level, cleanser level, waste level, prime completion, live flow rate, leak detection, cartridge-full detection, pump-health telemetry and live route visualisation unless released hardware contains and validates the required sensing and telemetry.

### Assets and data

Technical visualisations should use released geometry and stable subsystem identities wherever possible. Decorative internal routing should not be presented as a literal representation of the device.

Simulated, development or placeholder data must remain distinguishable from measured device telemetry.

## Product claims

The digital product may accurately state that Masck One is being engineered around separate fresh-water, cleanser and mixed-waste paths, controlled distribution and waste handling.

The following should not be presented as established facts until supported by physical evidence:

- leak-proof or orientation-independent operation
- universal cleanser compatibility
- clinically proven or guaranteed cleansing performance
- measured waste-recovery efficiency
- verified comfort or fit across a population
- exact runtime or cartridge life
- verified thermal or electrical safety
- sensing or telemetry capabilities that are not physically implemented
- production-ready materials, tolerances or manufacturing processes that have not been qualified

Engineering targets may be discussed as targets when clearly labelled as such. They should not be converted into achieved claims.

## Product imagery

Public imagery should follow the current released exterior and product-intent sources rather than stale concept geometry.

Protected eye, mouth and airway regions must remain protected in both technical visuals and product explanations. Development reference geometry should not be presented as final manufactured material.

Where internal geometry is still unresolved, an abstract explanatory visual is preferable to a realistic-looking but invented mechanism.

## Retention and removal

Any digital explanation of retention or removal should follow the current released mechanical architecture.

Basic product removal must never be presented as dependent on the app. Claims about one-hand removal, wet-use performance, release force, release time, accidental-release immunity or universal fit require physical validation before they are stated as achieved results.

## Companion software

The companion software is intended to support the product rather than create capabilities that the hardware does not possess.

Future software may include setup, routine configuration, maintenance guidance and device status where those states are supported by released hardware and firmware.

Safety-critical behaviour should remain hardware-grounded unless the engineering authority explicitly establishes otherwise.

## Working process

For each significant digital-product update:

1. Confirm the relevant product state against released `main`.
2. Identify the exact engineering source behind any technical claim or visual.
3. Separate implemented capability from future product intent.
4. Use released geometry for literal technical representation.
5. Keep simulated data visibly separate from measured data.
6. Treat missing hardware or evidence as a product dependency, not as a reason to invent a UI state.

The goal is a digital experience that is ambitious and visually strong while remaining technically credible.
