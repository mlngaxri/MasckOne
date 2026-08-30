# Phase 2 — Iteration 11 engineering record

## Scope

Dedicated nasal saddle / bridge / dorsum / sidewall / lobe / philtrum functional architecture, with special attention to preserving full nose/T-zone cleansing intent without occupying protected nostril/airway regions.

## Problem closed digitally

Iteration 10 created the broad compliant-interface topology but deliberately left the geometric application boundary of the authority-backed 0.30 mm nasal-lobe thickness unresolved.

At the same time, the inherited early CAD placeholder extruded an entire trapezoidal nasal saddle at 0.30 mm. Once the interface topology became explicit, those two states were inconsistent: the code was visually applying a local lobe thickness to bridge/dorsum/sidewall/philtrum regions whose thickness had not been established.

Iteration 11 resolves that inconsistency without fabricating missing material data.

## Implemented

- Added `src/masck_one/nasal_subsystem.py`.
- Added five stable nasal functional roles.
- Derived role boundaries from existing T-zone and nostril/protected geometry only.
- Removed an initially considered arbitrary sidewall-width coefficient before promotion; the final development bridge/dorsum width is anchored directly to the authority-defined nostril centerline spacing.
- Added exact central target-set reconciliation against both coverage and compliant-interface layers.
- Added area-conservation checks.
- Added bilateral sidewall symmetry checks.
- Added explicit protected-opening exclusion.
- Localized the 0.30 mm / 0.25–0.35 mm thickness family to `NASAL_LOBE` only.
- Kept bridge/dorsum, sidewalls and philtrum numerically unresolved.
- Replaced the broad 0.30 mm trapezoidal nasal CAD placeholder with a local `nasal_lobe_membrane_reference` development solid.
- Removed the full conservative nostril protected footprints from that local reference.
- Added nasal topology to `MasckOneModel`.
- Added deterministic nasal topology SHA-256 identity.
- Added nasal topology manifests to generated build reports.
- Renamed the emitted nasal STEP artifact to `nasal_lobe_membrane_reference.step`.
- Added dedicated nasal subsystem preflight and GitHub CI gate.
- Added unit, regression, integration and evidence-boundary tests.
- Added dedicated engineering and acceptance documentation.

## Deliberately not claimed

- Final 3D nasal saddle geometry.
- Anatomical bridge/dorsum dimensions.
- Material selection outside the local authority thickness reference.
- Nasal-sidewall pressure/conformity.
- Airway deformation/collapse performance.
- Airflow pressure drop.
- Fluid-ingress safety.
- Membrane strain.
- Cleansing efficacy.
- Human-fit validity.

## Promotion rule

Iteration 11 is promoted only after the exact PR head passes authority validation, repository preflight, nasal preflight, complete tests, deterministic CAD generation and all software-verifiable assertions. Any discovered failure is treated as engineering information rather than suppressed by weakening the gate.
