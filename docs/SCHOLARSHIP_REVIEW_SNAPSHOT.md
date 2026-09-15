# Scholarship review snapshot

[Project overview](../README.md) · [Venture progress](VENTURE_PROGRESS.md) · [Next-stage evidence plan](SCHOLARSHIP_NEXT_STAGE.md) · [Customer discovery](CUSTOMER_DISCOVERY.md)

Masck One is an early-stage, pre-commercialisation venture. Engineering geometry exists and digital checks/frameworks exist; product-level physical validation has not begun.

This page is the canonical reviewer evidence path. It separates existing digital engineering evidence, planned validation, and physical/commercial evidence not yet obtained.

## Venture snapshot

Masck One is exploring whether selected repetitive parts of a facial-skincare routine can be automated in a way that creates net convenience rather than replacing one burden with another. The current target-user hypothesis is people who already follow multi-step facial-skincare routines and value reducing active time and repetitive handling. This is a hypothesis, not a validated customer segment.

The long-term direction is a wearable-and-dock system that could automate selected parts of a routine. That broader vision is not a committed first-product specification. The first use case is deliberately not locked: structured customer interviews should first identify one repeated routine problem worth solving, then focused fit, fluid, cleaning and cost evidence should determine whether that narrow use case deserves deeper development.

What exists today is an inspectable digital engineering foundation: controlled requirements, parametric geometry, automated checks, source binding, documented design decisions and cross-subsystem integration work. A founder-reported informal survey of around 20 people provides only a preliminary signal, strongest around time and convenience, with concerns around comfort, maintenance and price. The method and raw data are not available, so it does not establish demand or willingness to pay.

The largest uncertainties are therefore customer problem strength, net wearable convenience, physical fit, real fluid behaviour, hygiene and cleaning burden, manufacturing feasibility and cost. The next stage is designed to replace those assumptions with evidence before the broader vision is allowed to drive more scope.

## Scholarship decision brief

The strongest case for supporting Masck One now is not that the product is close to market. It is that substantial inspectable digital work already exists, the largest remaining uncertainties are clearly identified, and the next tranche of work can be structured around decisions rather than additional presentation or feature breadth.

| What a reviewer can reasonably conclude now | What support should help determine next |
| --- | --- |
| The venture has progressed beyond an idea into controlled requirements, parametric geometry, automated checks, documented trade-offs and cross-subsystem engineering work. | Whether customers experience one routine problem strongly enough to justify a focused first use case. |
| The founder has created a reproducible engineering record and has made unsupported physical and commercial claims explicit rather than treating digital progress as product validation. | Whether fit, fluid handling and cleaning can create net convenience in focused physical tests. |
| Preliminary customer feedback provides questions worth testing, but not evidence of demand or willingness to pay. | Whether customer value and an initial manufacturing-cost model overlap enough to justify deeper hardware development. |
| The broader wearable-and-dock concept is a direction, not a locked first-product specification. | Which functions, if any, earn their way into a first product through customer, physical and cost evidence. |

A useful scholarship outcome would therefore be a better venture decision: continue a narrowly evidenced use case, redesign it, or reject it. Funding or mentorship would not convert the current repository into physical validation; it would help generate the evidence required to decide what deserves further investment.

## 60-second evidence map

| Claim a reviewer may test | Representative repository evidence | What it establishes | Boundary |
| --- | --- | --- | --- |
| Parametric CAD exists | [Parametric model source](../src/masck_one/model.py) and [model checks](../tests/test_model.py) | Inspectable, code-generated geometry and digital checking exist. | Not human fit, comfort, safety, manufacturability or physical performance. |
| System requirements are controlled | [Engineering authority](../config/masck_one_authority.yaml) and [authority contract tests](../tests/test_authority_contract.py) | Requirements and duplicated constraints can be machine-checked rather than existing only as presentation claims. | Not proof that manufactured hardware achieves those requirements. |
| Engineering evidence is source-bound | [Boundary-release tests](../tests/test_boundary_release.py) | Source revision, registered geometry identity and digital-only evidence boundaries are checked so stale evidence can fail closed. | Not anatomical validity, physical performance or qualification of later revisions by older results. |
| Design decisions and unresolved conflicts are documented | [Whole-product convergence review](CORE_SKETCH_CONVERGENCE_REVIEW.md) | Cross-subsystem conflicts, trade-offs and validation gates are recorded rather than hidden. | A documented decision is not proof the selected architecture works physically or commercially. |
| Major subsystem work is inspectable | [Subsystem evidence spot-check](SCHOLARSHIP_SUBSYSTEM_SPOTCHECK.md) | Representative face-side geometry, structure, actuation, waste and evidence-control sources can be audited quickly. | Coverage is not subsystem readiness. |

## Evidence classes

| Evidence class | Current position |
| --- | --- |
| Existing digital engineering evidence | Controlled requirements, parametric CAD, automated checks, source binding, documented design decisions and representative subsystem geometry exist in the repository. |
| Planned validation | Structured customer interviews, focused simulation/analysis, focused fit work, core fluid testing, hygiene/cleaning investigation and initial manufacturing-cost modelling are planned evidence activities. Plans and frameworks are not completed results. |
| Physical/commercial evidence not yet obtained | Customer demand, comfort, hygiene/cleaning practicality, real fluid behaviour, safety, manufacturing feasibility, unit economics and product-level physical performance remain unproven. |

## Current CI boundary

Automated checks are evidence of engineering discipline only when their result is stated accurately. The exact scholarship-review head before this documentation-only edit, `1697c2df4b0b0d77cfa8bf96317182d7999fd3a5`, ran engineering CI on 16 September 2026 and failed overall in run `35004150358`. Source binding, compilation, the engineering-authority contract, product-identity contract, repository preflight and Iteration 11 to 16 preflights passed. Unit and integration tests then failed, so deterministic CAD smoke, exact release-provenance verification, generated-package integrity and CAD review-artifact preservation were skipped. The separate integrity-ratchets job passed repository integrity ratchets, failed pinned-commit provenance, and therefore skipped program-position consistency.

Accordingly, this branch is not presented as a green engineering release. Passing preflights demonstrate that specific digital guards executed successfully at that exact revision; they do not override the failed suite, qualify skipped stages, transfer qualification to this later documentation commit, or constitute physical validation.

## Current venture boundary

Masck One is pre-commercialisation. The repository demonstrates disciplined digital engineering through source binding, controlled requirements, automated checks, documented trade-offs and explicit UNKNOWN or validation-required states. It does not demonstrate a validated product.

Customer demand and willingness to pay are not established. Comfort and population fit are not established. Hygiene and cleaning practicality are not established. Real fluid delivery, recovery and leakage behaviour are not established. Safety is not established. Manufacturing feasibility and production capability are not established. Unit economics are not established. Product-level physical performance is not established.

Synthetic tests, geometry screens, framework readiness, subsystem coverage and green CI, where present, remain digital evidence. None should be promoted into physical validation.

## Verifiable development progression

The dates below are Git commit dates, not retrospective claims about when physical capability was achieved. They provide a short audit trail showing how the venture moved from controlled engineering foundations to whole-product integration and then external-review discipline.

| Date | Inspectable milestone | Venture signal |
| --- | --- | --- |
| 30 August 2026 | [Authority-contract implementation](https://github.com/mlngaxri/MasckOne/commit/910d4fd1a03164e032847e590331cd7cddf51d8d) and [facial-reference landmark contract](https://github.com/mlngaxri/MasckOne/commit/9c427d5faec3687c1a1422c6bea3edd9394bffb3) | Requirements, automated checks and a reproducible engineering structure became inspectable repository outputs. |
| 10 September 2026 | [Whole-product Core Sketch convergence](https://github.com/mlngaxri/MasckOne/commit/0044a55885000480a873b5761742341038b24b6a) and [authority reconciliation](https://github.com/mlngaxri/MasckOne/commit/0c0ccb1d1b3356ed0001e5e53f318973a2893e08) | Development expanded into explicit cross-subsystem conflicts, constraints and evidence gates rather than treating subsystem work as independently complete. |
| 14 September 2026 | [Public scholarship-review baseline](https://github.com/mlngaxri/MasckOne/commit/b4a105ea4483a6285be7d55fd527baea30ce6412) | The engineering record was reorganised for external scrutiny with clearer separation between digital work, planned validation and unsupported claims. |

This chronology demonstrates initiative through dated, inspectable outputs. It does not imply that the speed of repository development equals physical product maturity, and it does not hide the extensive use of AI described below.

## Customer and commercial evidence

A founder-reported informal survey of around 20 people produced a preliminary signal around time and convenience, with concerns around comfort, maintenance and price. The underlying questionnaire, recruitment method and raw response data are not available in the repository, so this does not establish demand, willingness to pay, a validated customer segment or product-market fit. See the [customer discovery record](CUSTOMER_DISCOVERY.md).

## What happens next

The next stage is deliberately narrower than adding features. Structured customer interviews should identify whether a sufficiently important first problem exists. Focused simulation and analysis should reduce high-risk uncertainty before hardware spend. A focused physical fit prototype and core fluid-delivery testing should then test the narrow wearable workflow and wet-system assumptions. Hygiene and cleaning investigation should test whether maintenance erases the intended convenience benefit. Initial manufacturing-cost modelling should test whether required complexity has a plausible commercial path. Weak evidence should narrow, redesign or reject the relevant use case rather than be hidden by further digital scope.

The detailed evidence gates and minimum useful outputs are recorded in the [next-stage evidence plan](SCHOLARSHIP_NEXT_STAGE.md).

## What scholarship support would change

Scholarship support would be used to improve the quality of evidence, not to make the venture look more finished than it is.

| Support area | Evidence it should enable | Decision it should improve |
| --- | --- | --- |
| Structured customer validation | Consistent interview records focused on routine friction, first-use-case priority, maintenance tolerance and pricing assumptions. | Whether a sufficiently important customer problem exists and which first use case deserves testing. |
| Prototype materials and test equipment | Focused fit and workflow prototypes plus repeatable core fluid-delivery measurements. | Whether the selected wearable workflow is physically credible enough for deeper development. |
| Hygiene and cleaning investigation | Documented servicing, cleaning and contamination-risk observations rather than assumed convenience. | Whether maintenance burden undermines the proposed customer value. |
| Manufacturing and cost investigation | A sourced first-pass manufacturing-cost model and specialist input on practical fabrication choices. | Whether product scope and likely cost can plausibly coexist before further hardware investment. |
| Specialist collaboration | Review from people with relevant hardware, manufacturing, IP, fundraising and market-entry experience. | Which assumptions require expert challenge before they become expensive commitments. |

No budget or spending commitment is implied by this table. The standard is that support should leave behind inspectable evidence that makes the next venture decision better.

## Founder and AI roles

AI is used extensively to accelerate implementation, research, alternative generation and engineering exploration. Founder judgement owns product direction, requirements, priorities, trade-offs and final decisions. AI-assisted digital work is not presented as independent physical proof, and specialist human expertise remains necessary where practical experience, measurement and regulated or manufacturing judgement matter.
