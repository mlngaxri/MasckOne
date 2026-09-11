# Reduced-region complete-sequence evidence package

Scope: **off-face inert surrogate only**. This package organizes observations from an unpowered mechanical coupon fixture. It is not a human-use procedure, a clinical protocol, a chemical recipe, or permission to apply powered thermal/optical/mechanical treatment. Qualified laboratory and human-validation work remain separate.

It joins CS-010 / CS-012 / CS-013 / CS-160 / CS-161 / CS-163 without claiming whole-face feasibility. The objective is to discover whether the selected transfer/contact architecture can preserve sequential films while exposing every required coupon area.

## Smallest useful fixture and comparison

Use a removable, inspectable inert cheek-scale coupon with five explicitly mapped observation cells: open center, support footprint, seal footprint, acquisition edge and release edge. A removable witness guard represents a protected boundary. The existing owner supplies representative contact/support and removal geometry, with source IDs and actual continuous motion recorded. It may be a manual unpowered surrogate; actuator settings are outside this package.

Maintain paired specimens: an unobstructed reference application and the same sequence with contact, service and release. Include a no-product blank and a carryover blank. The reference is necessary to distinguish a poor application method from removal damage and naturally different material appearances. Vary starting alignment and the contact arrangement before expanding to facial geometry. No single polished nominal coupon is sufficient.

Material families for professionally selected inert test media: low-viscosity spreading liquid; shear-sensitive gel proxy; thicker lotion/emulsion proxy; film-forming final-layer proxy. Record the measured behavior and identity of each surrogate rather than calling it a validated serum, moisturiser or sunscreen. Chemistry, microbial handling and qualified product testing require appropriate laboratory selection; no formulation or mixing recipe is provided here.

## Recorded sequence

CLEAN -> RINSE/RECOVER -> THIN LEAVE-ON -> THICK LEAVE-ON -> REPRESENTATIVE FINAL LEAVE-ON -> SETTLE -> NON-WIPING RELEASE.

At each transition retain:

- specimen, surrogate, batch and source/fixture identities, timestamp and ambient observations;
- calibrated before/after photographs with consistent framing, scale and mapped cells, plus a view of every previously hidden contact footprint;
- input, recovered, retained, fixture-transfer and collected-loss masses, with balance uncertainty and blanks;
- cell-level uncovered/unknown area and deposited-material observations; averaging over the coupon is forbidden;
- a distinguishable carryover measurement for the preceding stage, including the downstream path and support/seal residue;
- the contact-state transition and continuous normal removal recording;
- final-film change between pre-release and post-release, relative to the paired reference and measurement uncertainty.

Weighing alone cannot establish spatial coverage. Photographs alone cannot establish product identity or contamination. Film-retention fraction is normalized to the comparable pre-release/reference measurement, not assumed from dispensed volume. Independent uncertainty is included conservatively at each maximum/minimum comparison. Evidence that remains hidden, occluded or below a justified measurement capability is UNKNOWN.

## Data contract and failure

`docs/contracts/reduced_region_protocol.json` is the predeclared protocol. Its numerical limits are deliberately null. A qualified reviewer must define measurement capability, inert-surrogate acceptance and repeatability criteria **before** confirmatory runs; no clinically meaningful thresholds are invented. `reduced_region_trial_template.json` records each stage and cell. Preserve raw observations alongside any reduced metrics, calibration receipts and immutable photograph records.

Run the command in `CORE_SKETCH_P0_CONTRACTS.md` against a completed record. Missing limits, missing calibration/photos, an omitted stage/cell, an unknown or occluded area, carryover above its reviewed limit, unclosed mass balance, protected-boundary deposition or insufficient final-film survival prevent a review candidate. A changed protocol digest prevents retroactively loosening limits against a favorable trial. Replicates and comparison specimens must all meet the declared scope before a reviewer accepts BENCH evidence; the parser does not authenticate or accept that evidence itself.

A successful surrogate result permits only the next bounded interface investigation: curvature, actual owner geometry, wider material-family characterization and then a registered whole-face surrogate. It does not establish safe human use, arbitrary third-party compatibility, hygiene, skin effects or efficacy. No row in this package can set SPF validated or whole-face complete. Exact SPF product/application/coverage/claim validation remains a separate qualified program.

## Architecture decisions forced by observations

| Finding | Required action |
|---|---|
| A required footprint remains blocked or recontact removes its final layer | Redesign the contact/support handoff; do not mark the footprint excluded. |
| Acceptable carryover needs excessive purge or inaccessible cleaning | Change isolation/path/service architecture; reevaluate storage, waste and dock burden. |
| Certain behavior families repeatedly fail with viable interfaces | Restrict compatibility explicitly and test whether the supported cohort still earns the product promise. |
| Dose/isolator/purge hardware cannot meet joint mass, CG and fault inventory | Change dock/session-dose architecture before growing the wearable. |
| Layer interaction or settling is incompatible with a selected routine | Mark that routine unsupported; propose a validated alternative explicitly, never report completion with a stage omitted. |
| SPF cannot meet its independent film/claim requirements | Postpone that morning routine claim explicitly; serum success is not a substitute. |
| Multiple credible interfaces cannot reach required skin and preserve films without manual finishing | Reconsider the complete-routine concept itself. Do not quietly rename an automated cleanser as complete skincare. |

Whole-face human factors, qualified product preservation, regulatory claims and supplier/process qualification remain separate evidence gates after this reduced proof. A cheaper or simpler architecture is preferred only when it preserves these obligations.
