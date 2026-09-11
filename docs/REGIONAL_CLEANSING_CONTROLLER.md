# Deterministic regional cleansing candidate

The current implementation is a **simulation and off-face mechanical candidate**. It cannot issue device commands or select human-use limits. No clinical, cosmetic-effectiveness, human-fit or production qualification is implied. `Envelope` rejects human-use scope, missing limits block, and every receipt identifies DIGITAL_SIMULATION. The published baseline contains no numerical human treatment table.

## Decisions that shape both hardware and control

1. Oil tendency, present surface oil and dryness are independent axes. Oily and dry are not logical opposites. Baseline history does not overwrite the current observation.
2. Independent evidence is compared on matching variables and phase. It is not averaged. A mismatch reduces confidence and selects review. Reported discomfort and recent burden cannot be cancelled by a normal sensor result.
3. Oily appearance does not itself authorize more force, motion or chemical exposure. A future bounded operating table needs separate evidence; this code does not derive it from appearance.
4. Every addressed region keeps its own ceiling and completion cells. A shared channel is allowed only if every region it touches permits the next increment. If a completed region remains mechanically coupled to an unfinished one, the hardware cannot implement the requested independent plan.
5. A gentle/review table must be componentwise no more permissive than baseline. Reducing action cannot silently remove the rinse requirement. Unknown critical answers, placement, prior burden or treatment limits block contact rather than becoming a permissive default.

The AAD's general cleansing guidance favours gentle non-abrasive washing and cautions against scrubbing. That supports rejecting automatic escalation; it does not validate a powered mask, force, stroke, duration or personalized dose. [AAD, Face washing 101](https://www.aad.org/public/everyday-care/skin-care-basics/care/face-washing-101).

## Questionnaire and estimator

`QUESTIONNAIRE` contains twenty versioned question records, each naming the discriminated variable, answer family and whether regional overrides are allowed. It covers usual/current oil and dryness separately; flaking; current discomfort; water/product discomfort; recent cleansing/repeated cleansing/exfoliation/hair removal/stress; product film/change; wetness; environmental change; asymmetry; obstructing hair; and answer confidence.

This is a decision-oriented question model, not a validated questionnaire. The two temporal pairs distinguish usual tendency from present state. Recent-cleanse and repeated-cleanse questions distinguish an unrecorded event from cumulative repetition. Film/wetness/context qualify observations; they do not add intensity. Left/right differences request regional evidence instead of assigning a face average. Demographic/ethnicity fields are not part of cleansing inference and unrecognized fields are rejected.

UNKNOWN is valid for every answer. It is never NO or consent. Noncritical uncertainty selects GENTLE_REVIEW; critical uncertainty selects BLOCKED_REVIEW. Risk flags are PRESENT, NOT_REPORTED or UNKNOWN, not diagnoses. Confidence refers only to agreement of the observed cosmetic proxies, not validated skin tolerance. No probability is invented. Contradictory answers remain review conditions. Questions require later usability/discrimination studies before onboarding is finalized.

## Physical observations and limitations

| Signal | Candidate role | Required boundary |
| --- | --- | --- |
| Surface oil proxy before wetting | Independent check of current reported oil | Exact region, known product film, calibration identity, valid interval, quality and no declared confounder required. No accepted calibration ships. |
| Hydration-deficit proxy before wetting | Independent check of current reported dryness | Cannot substitute for irritation/barrier assessment. Contact method, pressure, ambient conditions and existing products require characterization. |
| Contact/placement and upper force bound | Execution gating and load integral | Must be region-specific; whole-mask closure is not proof all regions are seated. |
| Stage displacement / tangential travel | Motion integral and overtravel gating | Commanded stroke alone is not measured displacement. |
| Metered delivery and recovery observation | Exposure and rinse/recovery accounting | Delivered mass is not residue removal. Recovery confirmation remains externally evidenced. |

Oil-strip photometry is a defensible characterization comparator, but entails contact and consumables; it is not selected as twelve wearable cartridges. Its manufacturer describes transparency measurement of a contacted strip. An optical shine sensor cannot simply inherit that calibration or distinguish product film from sebum. [Courage + Khazaka, Sebumeter measurement principle](https://www.courage-khazaka.com/en/scientific-products/occupational-health/occupational-health/151-sebumeter-e).

The conservative current choice is no wearable skin-type sensor claim. The typed observation interface rejects stale, wet-phase, confounded, duplicate or unaccepted readings. Operational placement/load/displacement/fluid feedback remains necessary independently of cosmetic personalization. Production sensors, signal conditioning and fault cutoffs are unresolved with their hardware owners. No camera, ML, disease classifier or telemetry service was added.

## Regional execution

`estimate` -> `prescription` -> `plan` -> `RegionalLedger` / `SessionLedger` -> simulation receipt. Core Sketch routine completion, prepared-session validity and product preservation remain external canonical consumers. A cleansing receipt never reports whole-routine completion.

The ledger integrates conservative interval observations:

- contact duration;
- load impulse, upper force multiplied by contact interval;
- absolute tangential path;
- upper force multiplied by path as a shear proxy, not biological stress;
- cleanser volume and residence time;
- water volume and rinse volume after the latest cleanser dose;
- pass starts, replay/sequence identity and telemetry age.

Cleanser residence continues while idle, rinsing and recovering until recovery is confirmed. Stopping a motor does not stop chemical exposure. Actual overrun is retained and faults latch. A missed sample blocks authorization rather than inventing zero burden. Cleanup may still be observed after a stop; the stopped region cannot become COMPLETE. Recent history must supply explicit prior burden. Unknown prior burden is not zero. The upstream history owner must define qualified time windows and preserve records across restart; persistence is not implemented here.

States are NOT_STARTED, IN_PROGRESS, CLEANSED, RINSED_RECOVERED, COMPLETE, with separate PROTECTED, EXCLUDED and BLOCKED. Completion compares exact expected classifications and cells, so relabeling a required region as excluded cannot pass. Geometry/telemetry receipts remain simulation evidence; a software boolean is not a physical coverage measurement.

The planner exposes ceilings for water, cleanser, preload, stroke, path, contact time, passes and rinse. These are not recommended treatment targets. Command duration stays null without an evidenced application recipe. Whole-session supply limits constrain the sum across regions.

## Hardware realization and fit

The existing off-face source now has four isolated rows, each with separate water, cleanser and mixed-waste passages, traversing three coupon columns. It therefore presents twelve individually accounted observation cells. No common gallery reconnects the fluids or rows. The external selector/pump/valve fixture and leakage isolation are not implemented or qualified. Its columns are scan locations; moving between them with contact or flow still active must account for every swept cell, not just the destination.

A real whole-face implementation still needs region-addressable fluid isolation and a way to unload any completed region from a shared cleansing motion. Existing four-zone massage hardware cannot be assumed to independently control all fifteen conceptual facial regions. The off-face cassette, guides, pin capture and catch shutter establish a reduced-region geometry only. Its stage travel is not a human facial treatment recipe. Existing shell, retention, airway, wet graph and emergency release owners are unchanged.

`cleansing_fit.py` selects only explicitly supplied multidimensional study envelopes. Width, length, forehead/cheek/nose/chin/jaw projection, nose width, bilateral asymmetry, local curvature and hair-state support must all match. An empty catalogue rejects all fit claims. No invented human size ranges or scaled protected apertures ship. A small size family plus local passive compliance remains a hypothesis pending registered face data and the retention/interface owners. Synthetic min/max/asymmetric tests validate the predicate only.

The fixture uses analytic, inspectable parts and relieved guidance; its feel, seal drag and wear are not established. Material classes and density are unqualified. Wearable mass and CG contributions remain unknown. Main authority remains controlling, including joint loaded-mass, CG and torque limits.

## Remaining evidence and integration

DIGITAL: whole-face registered geometry, regional actuation/isolation capability, sensor mounting and independent limit hardware; whole-head release and package/resource integration. BENCH: observation calibration, fluid isolation, distribution, residue removal, force/displacement accuracy, wear and film preservation. HUMAN: supported fit and any cosmetic cleansing tolerance/effectiveness. SUPPLIER: components, materials and manufacturing capability. REG/CLAIM: separate claims assessment, especially SPF.

Future profiles, schedules, community templates and advisory ML may provide context above this contract. They cannot supply a trusted operating envelope, change a local ceiling, erase consumed burden, override placement, or promote simulation evidence to physical validation. This branch does not implement those systems.
