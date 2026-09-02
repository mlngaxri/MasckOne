# Cell 3 release trace coverage gate

Status: physical-test evidence discipline. This gate does not establish a population reliability, comfort, safety or usability claim.

Passing force-displacement traces from a single specimen or a small number of repeated benign pulls can create false closure. `quick_release_trace_coverage.py` therefore requires explicit specimen, cycle and condition coverage in addition to the existing per-trace mechanism gate. Every included trace must itself close. Duplicate specimen/condition/cycle identities fail closed, and calibration provenance is mandatory.

The default minimum of three specimens and three cycles per required specimen/condition combination is a screening protocol floor only. It is not statistically justified production validation and must not be represented as such. Production DV/PV sample size, confidence/reliability targets, ageing states, contamination states, anthropometric reach conditions and environmental conditioning remain to be defined from the hazard analysis and validation plan.

This closes a specific evidence loophole: many successful pulls on one favourable latch cannot substitute for between-specimen variation, and one failing trace cannot be hidden by a favourable aggregate.

## DIGITAL_HANDOFF_DELTA

WEBSITE: no new interaction implementation. Do not describe emergency-release effort, tactile quality or repeatability as validated merely because a demonstration specimen works repeatedly.

APP: no dependency change. Emergency release remains mechanical, one-hand and unpowered; app state must not be used as release evidence.

ASSETS/DATA: preserve specimen ID, cycle index, physical condition, calibration ID and the associated row-level force-displacement trace. Future released data schemas must retain failures and outliers rather than publishing only summary curves.

CLAIMS: repeatable release, production consistency and condition robustness remain blocked. The screening floor in this gate is not a reliability claim and cannot support universal or production-level language.

BLOCKERS: hazard-derived DV/PV sample plan, production-intent specimens, ageing/contamination/environment matrices, calibrated wet traces, hair/pinch evidence, continuous tolerance-aware CAD sweep and untrained one-hand human-factors trials.
