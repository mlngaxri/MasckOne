# Reduced-region measurement reduction

Lane 1 implementation, 14 October 2026. CS-010/012/013/160/161/163 and G1 remain **PROVE**. This increment supplies reproducible computational reduction for the existing unpowered, off-face inert-surrogate proof package. It changes neither owner fixture geometry (#157/#158), the engineering authority, nor any physical acceptance threshold.

## Problem and hypothesis

The released trial checker consumes manually supplied fractions and error bars. It cannot reveal an omitted loss inventory, inadequate blank subtraction or a denominator indistinguishable from zero. A good coupon average can also conceal a stripped support footprint. Hypothesis: independent bounded per-cell reduction makes those limitations explicit before a reviewer interprets clean-to-leave-on or release results.

`src/masck_one/reduced_region_metrology.py` calculates mass closure, previous-material carryover, final-film retention and a paired unobstructed-reference comparison. The existing `core_sketch_trial.py` also now validates every supplied metric/uncertainty even when limits are null or its sibling measurement is absent. Unknown limits still block review. This fixes a parser hole; it does not authorize a bench run.

## Inputs and physical measurement contract

`docs/contracts/reduced_region_metrology_template.json` contains five explicit cells and **no measured values**. It deliberately produces blockers. Populate one record for each specimen/stage, bind the predeclared protocol SHA-256, and identify the inert preceding/current material. Retain raw observations, photographs and calibrated measurement receipts with each record. Do not populate a missing measurement with zero.

Each populated quantity has exactly these fields:

```json
{
  "value": 0.0,
  "uncertainty": 0.0,
  "unit": "g",
  "source_record": "replace-with-immutable-raw-record-reference",
  "calibration_record": "replace-with-calibration-reference"
}
```

The zeros above describe field types, **not available measurements or assumed uncertainty**. Both values must be independently supplied; zero uncertainty needs justification. `uncertainty` is an absolute worst-case bound. The reducer makes no statistical confidence claim. Signal measurements must already be calibrated to material mass in grams. Uncalibrated optical intensity, dispensed dose, pump execution or estimated nominal film thickness cannot substitute.

Required observations per cell:

| Group | Distinct measurements | Meaning and unresolved laboratory work |
|---|---|---|
| `mass_closure` | introduced, recovered, retained, fixture transfer, collected loss | All are masses, with disjoint final inventories. `introduced` must include measured starting inventory when a preceding layer is present. Do not recount internal transfers or earlier recovered waste. Resolve spatial inventory recovery, evaporation and collection losses using the selected inert material/method. |
| `carryover_fraction` | preceding-material residual and its blank; sampled total mass and its blank | The method must distinguish the preceding material in the downstream sample. The two calibrated masses share a mass basis; a flow fingerprint is insufficient. |
| `film_retention` | same-cell before/after release masses and their blanks | The before denominator is mapped local pre-release film, not commanded or dispensed product. Local pooling/redistribution remains visible. |
| `reference_film_retention` | paired reference before/after masses and blanks | Comparable unobstructed reference distinguishes release damage from natural evolution or the application method. Matching times, substrates, materials and calibration remain reviewer obligations. |

`previous_material_distinguishable` is an explicit declaration, never automatically inferred. Source/calibration references and protocol bindings are checked for structure, not authenticated. Identification, measurement capability, repeatability and suitable test media require qualified laboratory selection. This package contains no chemistry recipe, powered treatment, human-use instruction or experiment authorization.

## Conservative calculations and acceptance

For measured nonnegative mass `m` with absolute uncertainty `u`, use `[max(0,m-u), m+u]`. Sum disjoint inventory endpoints. Signed mass closure is introduced minus the four final inventories; report both signed bounds and the largest absolute endpoint. This detects both unexplained loss and over-recovery. Interval sums are conservative even with correlated errors; any correlation-based tightening needs a separately reviewed method.

Subtract blank intervals crosswise before computing ratios. A blank-corrected signal wholly below zero is unresolved; a denominator whose lower bound is zero is unresolved. For nonnegative numerator `[a,b]` and positive denominator `[c,d]`, report `[a/d,b/c]`. Do not clip fractions to one: a lower bound above one is inconsistent or indicates redistribution/pooling and blocks method interpretation. A zero nominal residual can still have a positive upper carryover bound.

The reference comparison reports specimen-retention minus reference-retention bounds. It does not divide away reference loss or apply a universal acceptance tolerance. Every required cell retains its own metrics and blockers. Missing or bad seal/support evidence cannot be compensated by a good central cell.

To transfer a ratio into the existing trial's nominal-plus-uncertainty representation, a reviewer can use interval midpoint and half-width; compare upper bound to maximum carryover and lower bound to minimum retention. No automatic transfer is implemented: spatial coverage, pooling, protected-boundary deposition, photos, stage order, exact-layer identity, methods and reviewed limits still need the existing independent protocol checks. Mass data alone cannot establish coverage. A method screen never becomes a BENCH acceptance receipt.

## Reproduce

From the repository root with the project Python 3.13 environment:

```sh
PYTHONPATH=src python -m masck_one.reduced_region_metrology \
  --input docs/contracts/reduced_region_metrology_template.json \
  --output generated/reduced_region/metrology_unknown.json
python -m pytest -q tests/test_reduced_region_metrology.py \
  tests/test_core_sketch_contracts.py tests/test_regional_cleansing.py \
  tests/test_routine_completion.py
```

A successful CLI exit means record parsing/reduction succeeded, **not that the trial passed**. The blank template emits 26 method blockers and null metrics. Reports bind canonical raw input bytes and reducer source SHA-256. `bench_evidence_accepted`, `whole_face_complete`, `human_use_authorized`, `spf_validated` and `acceptance_limits_established` remain false even for a complete synthetic input.

Baseline at live-main `faae3cec8b80d201c3b7f82c2f29d4bb766cad09`: 124 existing targeted tests passed. This change adds analytical endpoint, missing-cell, zero-denominator, unit/identity-method, overflow/nonfinite, impossible-fraction and null-limit parser regressions. All numerical values in tests are synthetic software inputs.

Next physical dependency: demonstrate calibration and repeatability of spatial film/carryover measurements, predeclare acceptance limits, then collect independent reference/contact/release records. Next digital task: consume authenticated, scope-bound records under the existing evidence producer once that provenance service exists. No hardware feasibility, skin compatibility, cleanser effectiveness or SPF protection is established here.
