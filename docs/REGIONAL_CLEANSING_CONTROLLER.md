# Deterministic regional cleansing intelligence

The selected Lane 1 path is `interpret_form → estimate → resolve → plan → authorize_footprint / ingest_footprint → record_stage → completion`. It supersedes PR #154's exact-category comparison and combined rinse/recovery gate, while retaining its conservative budget kernel. This continuation changes software and requirements, not the released off-face CAD.

**Execution remains OFF_FACE_SIMULATION only.** No accepted physical calibration, numeric human-use table, personalized human treatment recipe, diagnosis or efficacy claim ships. Missing limits, history bounds or placement cannot become default permission. A proposed profile is not authorization to use a powered device on a person.

## Three separate decisions

| Layer | Implemented output | Authority boundary |
| --- | --- | --- |
| Personalization | Independent ordinal requests for cleanser, mechanical action, contact time and passes; raw regional dimensions and explanations | No physical operating numbers |
| Qualified limits | `Envelope` plus `FactorPolicy`, explicit provenance and scope | Caller-supplied simulation inputs only; no built-in treatment table |
| Execution | Remaining regional/session budgets, exact affected cells, observed stage evidence | No device I/O; independent physical protection remains a hardware requirement |

Oil, dryness, sensitivity and stress are not one “skin type.” Baseline and current conditions remain separate, including oily baseline/current dryness, dry baseline/current surface oil, left/right differences and oily forehead/dry cheeks. Baseline oil explains change over time; it never overrides a current reading. Baseline dryness and reported sensitivity/stress provide independent caution. A sensor cannot cancel discomfort, recent exfoliation, repeated cleansing or uncertain contact suitability.

The AAD's general guidance supports gentle nonabrasive cleansing and avoiding scrubbing. It does **not** establish the force, stroke, chemical exposure, timing or efficacy of an automated mechanism. No powered-treatment threshold is derived from it. [AAD, Face washing 101](https://www.aad.org/public/everyday-care/skin-care-basics/care/face-washing-101).

## Onboarding contract and UX

`cleansing_onboarding.py` owns the selected 20-question content. Every record includes its latent variable, temporal scope, global/regional scope, purpose, distinction from neighboring questions, plain-language prompt, answer choices and help text. `form_contract()` is renderable UI data, not an app implementation. Wording/discrimination and completion burden remain usability-validation requirements.

The sequence covers usual experience, current observations, comfort, recent care, acquisition conditions and regional detail. “Tight or stretched,” “shiny or greasy,” flakes and product discomfort replace skin-type or barrier terminology. The two usual/current pairs discriminate temporary change. Recent-wash/repeated-wash answers cross-check repetition. Product film and wetness qualify observations, rather than increasing action. Facial-hair presence is passed to placement assessment; it is not a cleansing-intensity variable. Ethnicity and other demographic inputs are absent and rejected at the form boundary.

No answer is preselected. Every question permits “I'm not sure”; per-answer uncertainty is retained. Regional values may override a face-wide response. Declared left/right differences require regional current answers rather than silently copying the global answer. Named text regions, optional expansion and non-colour-only presentation support a later accessible UI.

The history period and prepared-cleanser label must come from their canonical owners and be shown in the form. Missing context makes the associated answer UNKNOWN. Survey acquisition, expiry and context identity are also explicit. A stale/unbound survey cannot be rehabilitated by a fresh sensor reading. Unknown critical responses require targeted review; an uncertain “No” cannot cancel a possible concern. No recovery window or survey lifetime is invented here.

## Quantitative observations and comparison

`QuantitativeObservation` carries region, feature, measured value, units, absolute uncertainty bound, sensor/calibration identities, acquisition/expiry, acquisition conditions, quality and confounders. `Calibration` supplies the accepted mapping, valid raw span, condition ranges, validity and maximum age. Raw data and rejection reasons remain in the profile. Wrong units/sensor, stale clocks, unaccepted calibration, wet phase, missing conditions and out-of-range values do not get clamped into valid readings.

Only two cosmetic comparison features are currently supported: a pre-wet surface-oil proxy and a pre-wet hydration-deficit proxy. Neither implies a measured barrier state or diagnosis. A tightness answer is not inherently equivalent to a capacitance reading: the mapping itself requires characterization. Optical shine cannot automatically distinguish skincare film from oil. No wearable sensing technology or specification is invented.

The interval coordinate is a **semantic study scale**, not a biological threshold. LOW/MODERATE/HIGH occupy equal thirds of 0..1. A calibration must independently justify any mapping into that coordinate. No such physical mapping ships. The observed raw value and continuous interval are retained; categorical wording is an explanation only. Legacy ordinal observations remain an explicitly labeled coarse adapter.

For survey interval `S` and observation interval `O`, the evidence distance is `max(0, O.low - S.high, S.low - O.high)`. Overlap/touch is compatible; a positive gap smaller than one answer-bin is minor variation; separation of at least one bin is material contradiction. These are transparent software classification conventions, **not clinically established differences**. An observation spanning more than one answer-bin has insufficient resolution for supported comparison. Low-quality or unavailable evidence is INSUFFICIENT even when broad intervals overlap. Confidence is evidence sufficiency, not an invented probability or assurance of tolerance.

Measurement uncertainty and conformity decisions are distinct subjects in the JCGM guides. This implementation exposes bounded uncertainty and decision rules; it does not claim a GUM-compliant measurement system. [BIPM/JCGM publications](https://www.bipm.org/en/committees/jc/jcgm/publications).

Minor variation can retain a bounded proposal. A material contradiction generates question-specific review and observation-specific reacquisition requests while reducing the relevant request. Reported discomfort, changed/unbound product or unconfirmed contact suitability blocks the proposal. Wetness/product film/context change prevents confirmed personalization. A conservative fallback for a named context is possible only if that context is explicitly included in the externally evidenced factor policy; the default list is empty. It never gets labeled confirmed personalization. This avoids making “wash before the machine can wash” an implicit requirement, without pretending a confounded measurement is valid.

## Relative prescriptions and monotonicity

The four request levels are MINIMUM, REDUCED and REFERENCE. MINIMUM is a request class, **not zero dose**, and no numeric factors ship. More supported current oil may change chemical exposure need while leaving mechanical action, contact time and passes unchanged. Dryness, sensitivity, surface stress and recent burden cap the dimensions independently. Unknown oil supplies no additional demand; unknown dryness/risk supplies maximum caution. Widening intervals, losing evidence or reducing quality must never increase any request or resolved ceiling.

The explicit `FactorPolicy` maps each request to a nondecreasing factor in [0,1]. The factor table is a separate qualification dependency, not a UX preference. Mechanical and time caps also restrict their load integral; force/path caps restrict the shear proxy. Water ceiling and qualified minimum rinse are retained, not discounted. An empty feasible action envelope blocks. An effective-envelope digest binds the full profile, factor table and absolute policy. Old family labels are compatibility explanations only; the new planner rejects legacy family tables rather than silently ignoring them.

The output consists of **ceilings**, not a duration-to-run or cleansing-success prediction. Command targets and the minimum effective application recipe remain unqualified. There is no “keep cleaning until it looks cleaner” loop. Future optimization must minimize burden inside an evidenced outcome envelope, not maximize use of each ceiling.

## Regional execution and completion

Every required domain/region/cell has explicit identity. The kernel integrates contact duration, upper force × contact duration, absolute tangential path, upper force × path as a shear proxy, cleanser volume, cleanser residence, water and pass starts. The shear proxy is not biological stress. Tick values represent observed conservative interval bounds, not motor commands.

Recent history requires an explicit upper bound, complete qualified window, region/domain identity and source. A successful software log or user-reported event alone cannot establish that bound. Unknown is not zero. Prior exposure constrains regional action; only current-session consumption debits current supply. Persistence/restart recovery remains with the history/session owner and cannot erase consumed burden.

Chemical residence continues during idle, rinse and recovery until recovery is evidenced. Overruns remain recorded and faults latch. A missing sample blocks authorization. Cleaning authorization reserves necessary rinse water. Cleanup telemetry can still be recorded after a fault, but faulted regions cannot become COMPLETE. This module does not invent a fault-cleanup treatment: the hardware owner must provide the independently qualified cleanup/release path.

The stage states are NOT_STARTED, IN_PROGRESS, CLEANSED, RINSED, RECOVERED and COMPLETE, with PROTECTED, EXCLUDED and BLOCKED separate. Per-cell status additionally distinguishes action in progress but unproved. `StageEvidence` binds session, domain, region, stage, affected cells, sequence, telemetry chain, observation basis and source digest. Bare cell lists, elapsed time, issued commands and wrong-session receipts cannot advance completion. Rinse requires both measured quantity and all rinse-cell outcomes; recovery requires its own all-cell evidence. Partial rinse/recovery cannot hide behind full cleaning coverage.

An already cleansed cell cannot receive more cleaning just because another cell in its region remains unfinished. A protected/excluded cell cannot be silently relabeled required or vice versa. A required blocked or unproved cell prevents cleansing completion. Even a complete cleansing simulation cannot report whole-routine or physical completion.

## Minimum hardware capabilities

`cleansing_requirements.py` owns the machine-readable capability contract. Independent **accounting and interruption** are required; a dedicated motor, pump or oil sensor per facial cell is not. Chemical delivery must be separable from mechanical action; both must be stoppable for every completed or exhausted footprint. Rinse and recovery need independent outcome observation. Placement, interval force/path/stroke, delivered quantities and complete affected cells must be observable or conservatively bounded.

`ChannelFootprint` binds all continuously affected cells, including travel, rather than just destination cells. Every affected region authorizes its own bounds. Shared telemetry must include all affected regions; any overrun remains recorded and faults the shared action. Common supplies, multiplexed valves or moving applicators are allowed if isolation and complete paths are evidenced. Sharing uses the intersection of ceilings. It cannot prove the more demanding region is finished.

`control_partition()` computes the distinct demand classes for a snapshot. A synthetic test represents 20 cells with four demand classes; that does not prescribe 20 mechanisms, nor prove the current four-zone massage hardware covers a whole face. The minimum installed channel count remains dependent on registered continuous footprints and measured outcomes. The existing 15 Core Sketch conceptual regions must not be collapsed into a face-average score. No new hardware, size family, sensor package or fit claim is produced in this software pass.

## Handoff, checks and remaining evidence

Run `python -m masck_one.cleansing_requirements OUTPUT_DIRECTORY` to emit `cleansing_intelligence.json`: selected questionnaire, typed field lists, capabilities, exact source hashes/Git blobs, authority/Core Sketch identities and source head. Dirty source is explicitly marked. CI exports this at the actual PR head. No numeric human table or accepted physical calibration is embedded.

Focused tests exercise minor/material contradictions, low-confidence asymmetry, interval widening, missing/stale/confounded evidence, regional combinations, critical uncertainty, context fallbacks, local exhaustion, shared action, per-cell holes, history provenance, source/session replay and external-field injection. These verify software invariants, not physical cleansing performance.

BENCH: sensor measurands/calibration, product-film confounding, interval telemetry and stage-outcome observability. HUMAN: question comprehension/discrimination, supported fit, cosmetic tolerance and effectiveness. SUPPLIER: sensing/control components and manufacturability. REG/CLAIM: any external performance or protection claims. Numeric absolute limits, relative factors, observation lifetimes/history windows and effective recipes remain qualification dependencies.

Routine OS, product identity/preservation, prepared-session validity, community templates, saved profiles, advisory ML and logging remain outside the controller. They may supply properly bound context through the narrow interfaces; none may substitute a treatment table, erase burden, bypass a stop or promote DIGITAL_SIMULATION to physical evidence. The existing hardware, protected anatomy, airway, mass/CG and other subsystem owners remain unchanged.
