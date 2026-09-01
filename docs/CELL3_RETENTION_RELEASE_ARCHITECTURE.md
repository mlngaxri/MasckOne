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

The 5 to 12 N release-force corridor remains validation-gated. It is not a PASS criterion in this digital model. Release time remains a physical human-factors requirement of no more than 2.0 s and cannot be inferred from CAD travel alone.

## Geometry gates before CAD closure

The production-intent latch cannot be frozen until all of the following exist: exact yoke and crown/occipital datums; continuous release trajectory; hard-stop geometry; latch engagement depth and tolerance stack; wet-finger grip envelope; hair and pinch exclusion volumes; harness/fluid strain-relief sweep; service-tool exclusion; accidental snag load cases; one-hand left/right reach assessment; and a reset confirmation feature that is mechanically inspectable.

The current sampled trajectory helper is intentionally weaker than a continuous swept-volume solver. It may detect obvious clearance loss, but it must never be used to claim continuous collision safety.

## Retention DOE and physical handoff

Digital DOE must vary at minimum anterior CG, crown/occipital load split, facial preload and interface friction. Physical Alpha must then measure strap/yoke force, pressure distribution and migration on representative headforms under dry and wet interface conditions, head pitch/yaw, donning variation and repeated release/reset cycles. Pressure and comfort claims remain blocked until those data exist.

The highest-value rig is an instrumented headform with six-axis facial-module load measurement, thin pressure mapping at forehead/cheeks/nasal-adjacent support, independent crown/occipital load cells and a force/displacement gauge on the release grip. Add wet-condition testing and hair surrogates before human release trials.

## Customer-friction hypotheses converted to tests

Fiddly fit becomes an untrained don/doff task with time, adjustment-count and re-adjustment metrics. Slipping becomes migration measurement under wet contact and head motion. Hotspots become pressure-map p95 and spatial-gradient review, not subjective reassurance. Accidental activation becomes snag/pull testing below the deliberate release corridor. Hair interaction becomes a swept-volume exclusion and surrogate-entanglement test. Service burden becomes a tool-free access and reassembly-error test. Noise/vibration transmission remains blocked until the actuator/retention assembly has measured transfer functions.

## DIGITAL_HANDOFF_DELTA

WEBSITE: future fit/removal explanation must show crown load support, occipital stabilization and the single mechanical emergency-release action. Do not depict release as electronic or app-mediated.

APP: basic removal must never depend on the app. Any future device-state display should distinguish latched/ready from service/reset-required only when physical sensing actually exists.

ASSETS/DATA: future mechanism animation requires the released continuous latch/yoke trajectory and verified swept volume. Current sampled trajectory data is insufficient for cinematic mechanism claims.

CLAIMS: do not claim universal fit, pressure-free comfort, sub-2-second removal in users, accidental-release immunity, quiet operation or production-ready retention.

BLOCKERS: representative headform pressure/migration data, exact retention datums, continuous release sweep, latch tolerance stack, wet one-hand force/time tests, hair/pinch tests, fatigue and vibration-transfer measurements.
