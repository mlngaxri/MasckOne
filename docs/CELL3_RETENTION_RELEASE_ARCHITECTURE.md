# Cell 3 physical retention and emergency-release architecture

Status: engineering baseline plus validation-gated requirements. This document does not claim measured comfort, fit, release force, release time, acoustic performance or fatigue life.

## Architecture decision

Use a three-path retention system. The crown member carries the majority of vertical weight, the occipital member reacts rearward/downward migration and pitch tendency, and the compliant facial interface supplies only the preload required for sealing/controlled contact. These functions must remain independently tunable. A single spring halo that simultaneously carries weight, establishes registration and creates facial preload is rejected as the preferred architecture because those requirements couple head-size variation directly into facial pressure.

The battery remains preferentially rear/temporal where routing and safety permit. Its exact position remains packaging-gated. Moving mass rearward is useful only while the resulting occipital pressure, wiring, service access and release trajectory remain acceptable.

## Load-path contract

Every retained mass must resolve through an explicit structural path: facial module -> bilateral side yokes -> crown/occipital junctions -> crown and occipital contact members -> head. Facial preload is a separate bilateral reaction path through the compliant interface. Harnesses, fluid lines and decorative covers are not structural retention members.

The digital quasi-static ledger in `retention_release.py` must retain the residual facial vertical reaction instead of assuming friction or straps make it disappear. CG pitch moment is also reported directly. These are sensitivity outputs only until representative headforms, pressure mapping and physical force measurements exist.

## Quick release concept contract

The emergency release is a mechanical bilateral-side-yoke disconnect actuated from one dominant-side grip feature. The release must not require battery power, firmware, an app or a sequential menu action. The grip should be accessible from the exterior with wet fingers. The final mechanism may use a guarded pull-tab/cam or equivalent architecture, but production geometry is not frozen until a continuous trajectory exists.

Required mechanical states are `LATCHED`, `RELEASING`, `RELEASED`, and `RESET_REQUIRED`. Reset must require deliberate re-engagement and must not occur merely because the pull feature is released. A single-point release must remove retention preload sufficiently for immediate removal even if electronics are dead.

The 5 to 12 N release-force corridor remains validation-gated. Release time remains a physical human-factors requirement of no more than 2.0 s and cannot be inferred from CAD travel alone. `quick_release_validation.py` provides the aggregate evidence gate. `quick_release_trials.py` adds the stronger closure rule: every physical trial must independently satisfy force, time, accidental-pull margin, reset-retention margin, wet-condition, one-hand and unpowered requirements with zero pinch or hair-entanglement failure. A favourable aggregate, mean, median, minimum or maximum may not hide a failing individual trial. Digital geometry or nominal spring calculations cannot populate those fields as measured evidence.

## Geometry gates before CAD closure

The production-intent latch cannot be frozen until all of the following exist: exact yoke and crown/occipital datums; continuous release trajectory; hard-stop geometry; latch engagement depth and tolerance stack; wet-finger grip envelope; hair and pinch exclusion volumes; harness/fluid strain-relief sweep; service-tool exclusion; accidental snag load cases; one-hand left/right reach assessment; and a reset confirmation feature that is mechanically inspectable.

Release preflight now has two geometry levels. The legacy centreline-to-point check is retained for simple regression cases. `release_capsule_clearance` adds finite moving-feature radius and finite protected-region radius, so a centreline that appears clear cannot hide overlap of the physical latch/yoke/grip envelope with a harness, hair, pinch or protected-region envelope. `release_capsule_tolerance_clearance` additionally consumes bounded moving-body, protected-body and datum uncertainties using conservative Minkowski inflation. These remain piecewise-linear preflight tools, not continuous CAD collision proof, and their bounds must come from controlled geometry and released tolerances rather than guessed values.

## Retention DOE and physical handoff

Digital DOE must vary at minimum anterior CG, crown/occipital load split, facial preload and interface friction. Physical Alpha must then measure strap/yoke force, pressure distribution and migration on representative headforms under dry and wet interface conditions, head pitch/yaw, donning variation and repeated release/reset cycles. Pressure and comfort claims remain blocked until those data exist.

The highest-value rig is an instrumented headform with six-axis facial-module load measurement, thin pressure mapping at forehead/cheeks/nasal-adjacent support, independent crown/occipital load cells and a force/displacement gauge on the release grip. Add wet-condition testing and hair surrogates before human release trials.

## Customer-friction hypotheses converted to tests

Fiddly fit becomes an untrained don/doff task with time, adjustment-count and re-adjustment metrics. Slipping becomes migration measurement under wet contact and head motion. Hotspots become pressure-map p95 and spatial-gradient review, not subjective reassurance. Accidental activation becomes snag/pull testing below the deliberate release corridor. Hair interaction becomes a swept-volume exclusion and surrogate-entanglement test. Service burden becomes a tool-free access and reassembly-error test. Noise/vibration transmission remains blocked until the actuator/retention assembly has measured transfer functions.

## DIGITAL_HANDOFF_DELTA

WEBSITE: future fit/removal explanation must show crown load support, occipital stabilization and the single mechanical emergency-release action. Do not depict release as electronic or app-mediated. Do not present force or removal-time targets as achieved until every qualifying physical trial closes its gate.

APP: basic removal must never depend on the app. Any future device-state display should distinguish latched/ready from service/reset-required only when physical sensing actually exists. Physical validation fails if any recorded qualifying release requires power, two hands or a dry-only condition.

ASSETS/DATA: future mechanism animation requires the released continuous latch/yoke trajectory, verified finite swept volume, released tolerance envelope, and mechanically correct reset trajectory. Centreline paths alone are explicitly insufficient. Preserve row-level physical trial data, not aggregate summaries alone: wet one-hand peak force, removal time, accidental-pull load, reset-retention load, pinch/hair outcomes and wet/unpowered/one-hand qualification for every trial.

CLAIMS: do not claim universal fit, pressure-free comfort, sub-2-second removal, accidental-release immunity, collision-safe release, quiet operation or production-ready retention until the corresponding physical evidence closes its gate. Release claims require every qualifying trial to pass, not merely a favourable aggregate statistic.

BLOCKERS: representative headform pressure/migration data, exact retention datums, controlled finite-body bounds, continuous tolerance-aware CAD release sweep, latch tolerance stack, row-level wet one-hand force/time trials, accidental snag/pull tests, reset-retention tests, hair/pinch tests, fatigue and vibration-transfer measurements.
