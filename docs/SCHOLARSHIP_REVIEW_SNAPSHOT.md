# Scholarship review snapshot

[Project overview](../README.md) · [Evidence matrix](SCHOLARSHIP_EVIDENCE_MATRIX.md) · [Visual evidence quicklook](VISUAL_EVIDENCE_QUICKLOOK.md) · [Next-stage evidence plan](SCHOLARSHIP_NEXT_STAGE.md)

Masck One is an early-stage, pre-commercialisation venture. Engineering geometry exists and digital checks/frameworks exist; product-level physical validation has not begun.

This is the canonical reviewer evidence path. It separates existing digital engineering evidence, planned validation, and physical/commercial evidence not yet obtained. Repository output demonstrates founder execution and engineering discipline; it does not demonstrate a validated product.

Engineering-source links below are deliberately bound to live `main`, which is the engineering authority. Scholarship documentation may advance independently and must not be read as a newer engineering release.

## Venture snapshot

| Reviewer question | Current position |
| --- | --- |
| Problem being explored | Multi-step facial-skincare routines can require repetitive active time, handling and clean-up. Masck One explores whether part of that work can be automated without creating a worse preparation or maintenance burden. |
| Target user hypothesis | People who already follow multi-step facial-skincare routines and value reducing active routine time and effort. This is not yet a validated segment. |
| Long-term direction | A wearable-and-dock system capable of automating selected parts of a broader facial-skincare routine. This is a product direction, not a committed or physically validated specification. |
| First use case | Not yet locked. The next customer work should identify one recurring routine task worth testing before broader product scope is earned. |
| What has been built | Controlled requirements, code-generated parametric CAD, automated engineering checks, design records and linked subsystem exploration across fit, fluid handling, retention, waste capture, electronics and controls. |
| Early customer learning | A founder-reported informal survey of around 20 people indicated strongest interest around time savings and convenience, with concerns around comfort, maintenance and price. The underlying survey evidence is not in the repository, so this is preliminary and non-conclusive. |
| Key uncertainties | Customer value, acceptable workflow and comfort, population fit, hygiene and cleaning burden, real fluid behaviour, safety, manufacturability, unit economics and the most defensible first use case. |
| What happens next | Structured customer interviews, focused simulation/analysis, a focused physical fit prototype, core fluid-delivery testing, hygiene/cleaning investigation and initial manufacturing-cost modelling. These are planned evidence steps, not completed results. |

The commercial discipline is deliberate: customer evidence should earn the right to spend on focused hardware; physical evidence should earn the right to deepen the architecture; customer value and sourced cost evidence should earn the right to broaden product scope. A weak result should narrow, redirect or stop the relevant use case rather than be hidden by more feature development.

## First-use-case selection gate

The first use case should be selected from evidence rather than from the breadth of the long-term concept. Structured interviews should identify candidate routine tasks, then compare them on the same questions: is the task repeated often enough to matter; does it create meaningful active-time, handling or clean-up burden; would reducing that burden create clear user value; can the workflow be tested without building the full wearable-and-dock vision; do comfort, hygiene or maintenance requirements risk cancelling the convenience benefit; and is there a plausible path to a manufacturable scope at a cost users may accept?

No candidate currently passes this gate. The output of customer discovery should therefore be a decision: advance one narrow use case into focused physical testing, narrow or change the proposition, reject the current candidates, or remain inconclusive and gather more evidence. This prevents existing engineering work from becoming a reason to commit to a product customers have not validated.

## 60-second evidence map

| Claim a reviewer may test | Representative evidence | What it establishes | Boundary |
| --- | --- | --- | --- |
| Parametric CAD exists | [Parametric model source](https://github.com/mlngaxri/MasckOne/blob/main/src/masck_one/model.py) and [model checks](https://github.com/mlngaxri/MasckOne/blob/main/tests/test_model.py) | Inspectable, code-generated geometry and digital integrity checks exist. | Not human fit, comfort, safety, manufacturability or physical performance. |
| System requirements are controlled | [Engineering authority](https://github.com/mlngaxri/MasckOne/blob/main/config/masck_one_authority.yaml) and [authority contract tests](https://github.com/mlngaxri/MasckOne/blob/main/tests/test_authority_contract.py) | Controlled values and dependent sources can be checked for consistency and rejected when they disagree. | Consistency does not prove the values are correct, safe or achieved by hardware. |
| Engineering evidence is source-bound | [Boundary-release tests](https://github.com/mlngaxri/MasckOne/blob/main/tests/test_boundary_release.py) | Revision identity and digital-only evidence boundaries are checked so stale evidence can fail closed. | Not anatomical validity, physical performance or qualification of later revisions by older results. |
| Design decisions and unresolved conflicts are documented | [Whole-product convergence review](https://github.com/mlngaxri/MasckOne/blob/main/docs/CORE_SKETCH_CONVERGENCE_REVIEW.md) | Cross-subsystem conflicts, trade-offs, unresolved dependencies and validation gates are recorded. | A documented decision is not proof the selected architecture works physically or commercially. |
| Major subsystem work is inspectable | [Subsystem evidence spot-check](SCHOLARSHIP_SUBSYSTEM_SPOTCHECK.md) | Representative face-side geometry, structure, actuation, waste and evidence-control sources can be audited quickly. | Coverage is not subsystem readiness. |

Representative requirement checks include duplicated nostril/airway opening requirements, the clean-cycle fluid ledger and minimum waste-cartridge capacity. The authority-contract tests deliberately perturb controlled inputs and require mismatches to fail. These checks verify repository consistency, not measured airway, fluid or cartridge performance. Requirements marked `VALIDATION_GATED` remain unproven until qualifying evidence exists.

## Evidence classes

| Evidence class | Current position |
| --- | --- |
| Existing digital engineering evidence | Controlled requirements, parametric CAD, automated checks, source binding, documented design decisions and representative subsystem geometry exist in the repository. |
| Planned validation | Structured customer interviews, focused analysis, physical fit/workflow work, core fluid testing, hygiene/cleaning investigation and initial manufacturing-cost modelling are planned. Plans, fixtures, protocols and frameworks are not completed results. |
| Physical/commercial evidence not yet obtained | Customer demand, comfort, hygiene/cleaning practicality, real fluid behaviour, safety, manufacturing feasibility, unit economics and product-level physical performance remain unproven. |

## What the repository demonstrates

The strongest current evidence is disciplined digital engineering rather than code volume. Requirements are machine-readable; dependent sources are checked against controlled values; digital evidence is tied to source identity; trade-offs and contradictions are recorded; and unresolved questions remain explicitly `UNKNOWN`, `VALIDATION_GATED`, blocked or otherwise bounded rather than being promoted into achieved performance.

The repository contains linked exploration across facial interface and treatment mechanics, product storage and delivery, waste recovery, retention and structure, actuation, electronics and controls, and dock/preparation concepts. This is evidence of system-level exploration and integration work, not proof that those subsystems are complete or physically compatible.

AI is used extensively to accelerate implementation, exploration, documentation and code-based CAD. Founder judgement owns venture direction, requirements, priorities, trade-offs and final system-level decisions. AI output, synthetic tests and passing software checks are not treated as physical evidence. Specialist human expertise and collaboration remain important for hardware, manufacturing, IP, fundraising and market entry.

## Current venture boundary

Masck One has not yet established customer demand or willingness to pay. Comfort and population fit are not established. Hygiene and cleaning practicality are not established. Real fluid delivery, recovery and leakage behaviour are not established. Safety is not established. Manufacturing feasibility and production capability are not established. Unit economics are not established. Product-level physical performance is not established.

Synthetic tests, geometry screens, simulation frameworks, source-bound checks, subsystem coverage and green CI, where present, remain digital evidence. None should be promoted into physical validation.

A founder-reported informal survey of around 20 people is preliminary only. The underlying questionnaire, recruitment method and raw response data are not available in the repository, so it does not establish demand, willingness to pay, a validated customer segment or product-market fit. See [customer discovery](CUSTOMER_DISCOVERY.md).

## Current CI boundary

Live engineering `main` is currently `8d37bc322b5ebe42179685a1a0559f2fcb1b5f22`. No pull-request workflow run is associated with that exact revision, and the current scholarship-review documentation head likewise has no associated pull-request workflow run. Therefore neither current head is presented as CI-qualified.

The latest completed engineering CI cited in this reviewer path is [run 35068027419](https://github.com/mlngaxri/MasckOne/actions/runs/35068027419), which tested exact revision `6f54a6934842d1acb7e609a555d1f71170029559` on 16 September 2026 and failed overall. Several preflight and contract checks passed, but unit and integration tests failed and later stages were skipped.

That run is historical digital evidence for its exact tested revision only. It does not qualify live `main`, this documentation branch, later revisions, skipped stages or physical performance. The repository is not presented here as a current green engineering release.

## Next evidence gates

The next stage should reduce uncertainty rather than add feature breadth. Structured customer interviews should determine whether one repeated routine problem is strong enough to justify a focused first use case. If it survives that gate, focused fit/workflow work and repeatable core fluid testing should test the narrow physical assumptions. Hygiene and cleaning investigation should test whether maintenance erases the intended convenience benefit. Initial sourced manufacturing-cost modelling should test whether the surviving scope has a plausible commercial path.

Scholarship support would be directed at evidence generation rather than presentation: prototype materials and test equipment for focused fit, fluid and cleaning work; manufacturing and cost investigation; and structured customer validation. No budget is asserted here because no repository-supported budget has been established.

Weak evidence should narrow, redesign or reject the relevant use case rather than be hidden by further digital development. The detailed sequence is in the [next-stage evidence plan](SCHOLARSHIP_NEXT_STAGE.md), while the [evidence matrix](SCHOLARSHIP_EVIDENCE_MATRIX.md) provides a deeper claim-to-source audit.
