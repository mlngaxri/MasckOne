# Cell 3 physical retention and emergency-release architecture

Status: engineering baseline plus validation-gated requirements. This document does not claim measured comfort, fit, release force, release time, acoustic performance or fatigue life.

## Architecture decision

Use a three-path retention system. The crown member carries the majority of vertical weight, the occipital member reacts rearward/downward migration and pitch tendency, and the compliant facial interface supplies only the preload required for sealing/controlled contact. These functions must remain independently tunable. A single spring halo that simultaneously carries weight, establishes registration and creates facial preload is rejected as the preferred architecture because those requirements couple head-size variation directly into facial pressure.

The battery remains preferentially rear/temporal where routing and safety permit. Its exact position remains packaging-gated. Moving mass rearward is useful only while the resulting occipital pressure, wiring, service access and release trajectory remain acceptable.

## Load-path contract

Every retained mass must resolve through an explicit structural path: facial module -> bilateral side yokes -> crown/occipital junctions -> crown and occipital contact members -> head. Facial preload is a separate bilateral reaction path through the compliant interface. Harnesses, fluid lines and decorative covers are not structural retention members.

The digital quasi-static ledger in `retention_release.py` must retain the residual facial vertical reaction instead of assuming friction or straps make it disappear. CG pitch moment is also reported directly. These are sensitivity outputs only until representative headforms, pressure mapping and physical force measurements exist.

Nominal resultant/contact-area pressure is not a robust support design check. `retention_contact_robustness.py` applies bounded reaction uncertainty plus fractional and absolute effective-area loss. `retention_pressure_gradient.py` adds an eccentric-load screen using a linear pressure field and middle-third kern. `retention_migration_margin.py` adds a conservative tangential-load screen using condition-specific lower-bound friction. `retention_preload_window.py` now adds a separate fit-range closure gate: anatomical/donning path variation plus assembly uncertainty must fit inside deliberate adjustment travel without saturating the adjuster and converting residual dimensional mismatch through member stiffness into excessive or inadequate retention tension. Stiffness uncertainty is applied adversarially at saturated fits. These are screening models only. Real compliant pads, scalp curvature, interface friction, adjustment behaviour and tissue response require physical measurement.

## Quick release concept contract

The emergency release is a mechanical bilateral-side-yoke disconnect actuated from one dominant-side grip feature. The release must not require battery power, firmware, an app or a sequential menu action. The grip should be accessible from the exterior with wet fingers. The final mechanism may use a guarded pull-tab/cam or equivalent architecture, but production geometry is not frozen until a continuous trajectory exists.

Required mechanical states are `LATCHED`, `RELEASING`, `RELEASED`, and `RESET_REQUIRED`. Reset must require deliberate re-engagement and must not occur merely because the pull feature is released. A single-point release must remove retention preload sufficiently for immediate removal even if electronics are dead.

The 5 to 12 N release-force corridor remains validation-gated. Release time remains a physical human-factors requirement of no more than 2.0 s and cannot be inferred from CAD travel alone. `quick_release_validation.py` provides the aggregate evidence gate. `quick_release_trials.py` requires every physical trial independently to satisfy force, time, accidental-pull margin, reset-retention margin, wet-condition, one-hand and unpowered requirements with zero pinch or hair-entanglement failure. Digital geometry or nominal spring calculations cannot populate those fields as measured evidence.

## Geometry gates before CAD closure

The production-intent latch cannot be frozen until all of the following exist: exact yoke and crown/occipital datums; continuous release trajectory; hard-stop geometry; latch engagement depth and tolerance stack; wet-finger grip envelope; hair and pinch exclusion volumes; harness/fluid strain-relief sweep; service-tool exclusion; accidental snag load cases; one-hand left/right reach assessment; and a reset confirmation feature that is mechanically inspectable.

Release preflight uses finite moving/protected envelopes and tolerance inflation, but remains piecewise-linear preflight rather than continuous CAD collision proof. Bounds must come from controlled geometry and released tolerances rather than guessed values.

Retention geometry additionally cannot freeze from a nominal headform alone. Crown and occipital adjusters require released minimum/maximum path lengths, usable travel after hard-stop and assembly allowances, adjustment resolution, member force-extension characterization, and confirmation that adjustment does not intrude into release, hair, harness, service or exterior-surface keepouts.

## Retention DOE and physical handoff

Digital DOE must vary at minimum anterior CG, crown/occipital load split, facial preload, interface friction, support-reaction uncertainty, effective contact-area loss, support-load eccentricity, tangential inertial/service demand, head-path variation, adjuster travel, assembly length uncertainty and retention-member stiffness. Physical Alpha must then measure strap/yoke force, pressure distribution, interface friction and migration on representative headforms under dry, wet and hair-surrogate conditions, head pitch/yaw, donning variation and repeated release/reset cycles. Adjustment range must be exercised at anthropometric/path-length extremes rather than inferred from nominal CAD.

The highest-value rig is an instrumented headform with six-axis facial-module load measurement, thin pressure mapping, independent crown/occipital load cells and a force/displacement gauge on the release grip. Add wet-condition testing and hair surrogates before human release trials. A controlled tangential pull or tilt protocol should identify lower-bound static migration thresholds for each support/interface condition rather than inferring friction from material datasheets.

## Customer-friction hypotheses converted to tests

Fiddly fit becomes an untrained don/doff task with time, adjustment-count and re-adjustment metrics. Adjustment saturation becomes a fit-range test with measured path length, remaining travel and retention tension at both extremes. Slipping becomes migration measurement under wet contact and head motion. Hotspots become pressure-map p95 and spatial-gradient review. Accidental activation becomes snag/pull testing below the deliberate release corridor. Hair interaction becomes a swept-volume exclusion and surrogate-entanglement test. Service burden becomes a tool-free access and reassembly-error test. Noise/vibration transmission remains blocked until the actuator/retention assembly has measured transfer functions.

## DIGITAL_HANDOFF_DELTA

WEBSITE: future fit/removal explanation must show crown load support, occipital stabilization, deliberate physical adjustment and the single mechanical emergency-release action. Do not imply universal fit from nominal CAD or depict release as electronic/app-mediated. Do not translate calculated adjustment, pressure or friction margins into comfort claims.

APP: basic fit adjustment and removal must remain physically operable without the app. Do not imply measured strap tension or adjuster position unless production sensing exists.

ASSETS/DATA: preserve released crown/occipital path-length ranges, usable adjuster travel, hard-stop positions, force-extension data, assembly uncertainty and conditioning provenance in addition to the existing release trajectory, tolerance envelope and row-level physical evidence. Future fit animation must use released adjustment endpoints rather than arbitrary visual scaling.

CLAIMS: universal fit, pressure-free comfort, slip-resistant retention, validated adjustment range and production-ready retention remain blocked. A digitally passing preload window is sensitivity evidence only.

BLOCKERS: anthropometric/headform path-length distribution, measured force-extension curves across conditioning/ageing, production-intent adjuster travel and hard stops, adjustment resolution/backdrive/slip evidence, representative headform pressure/migration data, exact retention datums, continuous tolerance-aware CAD release sweep, wet one-hand release trials, snag/reset tests, hair/pinch tests, fatigue and vibration-transfer measurements.
