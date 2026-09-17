# Scholarship review snapshot

[Project overview](../README.md) · [Evidence matrix](SCHOLARSHIP_EVIDENCE_MATRIX.md) · [Visual evidence quicklook](VISUAL_EVIDENCE_QUICKLOOK.md) · [Next-stage evidence plan](SCHOLARSHIP_NEXT_STAGE.md)

Masck One is an early-stage, pre-commercialisation venture. Engineering geometry exists and digital checks/frameworks exist; product-level physical validation has not begun.

This is the canonical reviewer evidence path. It separates existing digital engineering evidence, planned validation, and physical/commercial evidence not yet obtained. Repository output demonstrates founder execution and engineering discipline; it does not demonstrate a validated product.

## 60-second evidence map

| Claim a reviewer may test | Representative evidence | What it establishes | Boundary |
| --- | --- | --- | --- |
| Parametric CAD exists | [Parametric model source](../src/masck_one/model.py) and [model checks](../tests/test_model.py) | Inspectable, code-generated geometry and digital integrity checks exist. | Not human fit, comfort, safety, manufacturability or physical performance. |
| System requirements are controlled | [Engineering authority](../config/masck_one_authority.yaml) and [authority contract tests](../tests/test_authority_contract.py) | Controlled values and dependent sources can be checked for consistency and rejected when they disagree. | Consistency does not prove the values are correct, safe or achieved by hardware. |
| Engineering evidence is source-bound | [Boundary-release tests](../tests/test_boundary_release.py) | Revision identity and digital-only evidence boundaries are checked so stale evidence can fail closed. | Not anatomical validity, physical performance or qualification of later revisions by older results. |
| Design decisions and unresolved conflicts are documented | [Whole-product convergence review](CORE_SKETCH_CONVERGENCE_REVIEW.md) | Cross-subsystem conflicts, trade-offs, unresolved dependencies and validation gates are recorded. | A documented decision is not proof the selected architecture works physically or commercially. |
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

AI is used extensively to accelerate implementation, exploration, documentation and code-based CAD. Founder judgement owns venture direction, requirements, priorities, trade-offs and final system-level decisions. AI output, synthetic tests and passing software checks are not treated as physical evidence.

## Current venture boundary

Masck One has not yet established customer demand or willingness to pay. Comfort and population fit are not established. Hygiene and cleaning practicality are not established. Real fluid delivery, recovery and leakage behaviour are not established. Safety is not established. Manufacturing feasibility and production capability are not established. Unit economics are not established. Product-level physical performance is not established.

Synthetic tests, geometry screens, simulation frameworks, source-bound checks, subsystem coverage and green CI, where present, remain digital evidence. None should be promoted into physical validation.

A founder-reported informal survey of around 20 people is preliminary only. The underlying questionnaire, recruitment method and raw response data are not available in the repository, so it does not establish demand, willingness to pay, a validated customer segment or product-market fit. See [customer discovery](CUSTOMER_DISCOVERY.md).

## Current CI boundary

The current scholarship-review documentation head has no associated pull-request workflow run. The latest completed engineering CI cited in this reviewer path is [run 35068027419](https://github.com/mlngaxri/MasckOne/actions/runs/35068027419), which tested exact revision `6f54a6934842d1acb7e609a555d1f71170029559` on 16 September 2026 and failed overall. Several preflight and contract checks passed, but unit and integration tests failed and later stages were skipped.

That run is historical digital evidence for its exact tested revision only. It does not qualify this documentation branch, later revisions, skipped stages or physical performance. The branch is not presented as a green engineering release.

## Next evidence gates

The next stage should reduce uncertainty rather than add feature breadth. Structured customer interviews should determine whether one repeated routine problem is strong enough to justify a focused first use case. If it survives that gate, focused fit/workflow work and repeatable core fluid testing should test the narrow physical assumptions. Hygiene and cleaning investigation should test whether maintenance erases the intended convenience benefit. Initial sourced manufacturing-cost modelling should test whether the surviving scope has a plausible commercial path.

Weak evidence should narrow, redesign or reject the relevant use case rather than be hidden by further digital development. The detailed sequence is in the [next-stage evidence plan](SCHOLARSHIP_NEXT_STAGE.md), while the [evidence matrix](SCHOLARSHIP_EVIDENCE_MATRIX.md) provides a deeper claim-to-source audit.
