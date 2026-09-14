# Reading the engineering evidence

[Project overview](../README.md) · [Documentation index](README.md)

Masck One has a digital engineering baseline and a broader product concept under development. This guide helps distinguish what is implemented in a particular checkout from what is proposed or still needs measurement.

## A short inspection route

| Question | Evidence to inspect | What it does not establish |
| --- | --- | --- |
| What is the product trying to do? | [Product concept](PRODUCT_CONCEPT.md) and [convergence review](CORE_SKETCH_CONVERGENCE_REVIEW.md) | That every proposed capability exists or is feasible |
| What controls the merged engineering baseline? | [Engineering authority](../config/masck_one_authority.yaml), its [schema](../schemas/masck_one_authority.schema.json), and the [roadmap](DEVELOPMENT_ROADMAP.md) | Completion of the expanded whole-routine product |
| Can the digital work be reproduced? | [Source](../src/masck_one/), [tests](../tests/), [quickstart](ENGINEERING_QUICKSTART.md) and [CI runs](https://github.com/mlngaxri/MasckOne/actions/workflows/ci.yml) | Physical performance from a green software result |
| Where are integration assumptions challenged? | [Contact and occlusion matrix](CORE_SKETCH_CONTACT_OCCLUSION_MATRIX.md) and [routine resource envelope](CORE_SKETCH_ROUTINE_RESOURCE_ENVELOPE.md) | Measured values where inputs remain unknown |
| What physical proof is required next? | [Reduced-region proof package](CORE_SKETCH_REDUCED_REGION_PROOF_PACKAGE.md) and [status board](CORE_SKETCH_STATUS_BOARD.md) | A completed experiment merely because a protocol exists |

For example, inspection of protected-region geometry can show that a generated part respects a defined digital exclusion volume. It cannot show that the device is comfortable, fits a population or remains safe when worn. Likewise, a fluid-route model can establish connectivity without measuring delivery, leakage or recovery.

## Main, candidate work and historical records

`main` is the merged baseline. [Open pull requests](https://github.com/mlngaxri/MasckOne/pulls) contain proposed changes and subsystem investigations. Some are drafts awaiting integration or evidence. Their number and test results are not measures of product readiness.

Examples of candidate work are [facial-interface contact and proof tooling, PR #157](https://github.com/mlngaxri/MasckOne/pull/157) and [adversarial fit and registration tooling, PR #158](https://github.com/mlngaxri/MasckOne/pull/158). Follow the live PR state to see whether a proposal has subsequently merged. Synthetic cases and off-face measurement plans in these workstreams do not establish human fit or product efficacy.

When assessing a result, match the recorded source commit and inputs to the run being cited. An older green run does not qualify a later change. A PR description or dated status board can lag the current branch; inspect its latest commit and checks before treating it as current. The repository's provenance checks and evidence records are retained for this reason.

Development documents sometimes use `cell`, `lane` or `owner` for a workstream and its responsible development process. These are coordination terms, not employee counts. `Core Sketch` names the whole-product concept series; `CS-` identifiers track its work items. Existing names and paths remain where they are used by contracts, links or historical evidence.

## What remains open

Physical contact, comfort, coverage, carryover between products, liquid containment, hygiene, material compatibility, thermal/electrical behaviour and reliable removal require appropriate measurement and review. Manufacturing, supplier qualification and compliance require their own evidence. Product demand and a viable business model require customer and commercial learning.

`BLOCKED`, `VALIDATION_GATED`, `REFERENCE_ONLY` and unknown values are meaningful limits. A blocked plan may demonstrate that the software rejects an unsupported operation; it does not demonstrate that the operation has become physically possible. Planning deadlines and generated assets do not override those limits.
