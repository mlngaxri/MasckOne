# Scholarship review snapshot

[Project overview](../README.md) · [Subsystem evidence spot-check](SCHOLARSHIP_SUBSYSTEM_SPOTCHECK.md) · [Evidence guide](EVIDENCE_GUIDE.md) · [Customer discovery](CUSTOMER_DISCOVERY.md)

Masck One is an early-stage, pre-commercialisation venture. Engineering geometry exists and digital checks/frameworks exist; product-level physical validation has not begun.

This page is the canonical reviewer evidence path. It separates existing digital engineering evidence, planned validation, and physical/commercial evidence not yet obtained.

## 60-second evidence map

| Claim a reviewer may test | Representative repository evidence | What it establishes | Boundary |
| --- | --- | --- | --- |
| Parametric CAD exists | [Parametric model source](../src/masck_one/model.py) and [model checks](../tests/test_model.py) | Inspectable, code-generated geometry and digital checking exist. | Not human fit, comfort, safety, manufacturability or physical performance. |
| System requirements are controlled | [Engineering authority](../config/masck_one_authority.yaml) and [authority contract tests](../tests/test_authority_contract.py) | Requirements and duplicated constraints can be machine-checked rather than existing only as presentation claims. | Not proof that manufactured hardware achieves those requirements. |
| Engineering evidence is source-bound | [Boundary-release tests](../tests/test_boundary_release.py) | Source revision, registered geometry identity and digital-only evidence boundaries are checked so stale evidence can fail closed. | Not anatomical validity, physical performance or qualification of later revisions by older results. |
| Design decisions and unresolved conflicts are documented | [Whole-product convergence review](CORE_SKETCH_CONVERGENCE_REVIEW.md) | Cross-subsystem conflicts, trade-offs and validation gates are recorded rather than hidden. | A documented decision is not proof the selected architecture works physically or commercially. |
| Major subsystem work is inspectable | [Subsystem evidence spot-check](SCHOLARSHIP_SUBSYSTEM_SPOTCHECK.md) | Representative face-side geometry, structure, actuation, waste and evidence-control sources can be audited quickly. | Coverage is not subsystem readiness. |

## Representative automated checks

The repository uses checks to detect digital inconsistency, not to substitute software results for measurements. Representative checks include authority-contract tests that reject inconsistent duplicated requirements, model checks that test generated geometry against encoded constraints, and boundary-release tests that reject stale or incorrectly classified evidence. A passing check means the encoded digital contract passed for that source revision. It does not mean a person has worn a safe, comfortable product or that fluid, hygiene, manufacturing or commercial performance has been demonstrated.

## Evidence classes

| Evidence class | Current position |
| --- | --- |
| Existing digital engineering evidence | Controlled requirements, parametric CAD, automated checks, source binding, documented design decisions and representative subsystem geometry exist in the repository. |
| Planned validation | Structured customer interviews, focused fit work, core fluid testing, hygiene/cleaning investigation and initial manufacturing-cost modelling are planned evidence activities. Plans and frameworks are not completed results. |
| Physical/commercial evidence not yet obtained | Customer demand, comfort, hygiene/cleaning practicality, real fluid behaviour, safety, manufacturing feasibility, unit economics and product-level physical performance remain unproven. |

## Current venture boundary

Masck One is pre-commercialisation. The repository demonstrates disciplined digital engineering through source binding, controlled requirements, automated checks, documented trade-offs and explicit UNKNOWN or validation-required states. It does not demonstrate a validated product.

Customer demand and willingness to pay are not established. Comfort and population fit are not established. Hygiene and cleaning practicality are not established. Real fluid delivery, recovery and leakage behaviour are not established. Safety is not established. Manufacturing feasibility and production capability are not established. Unit economics are not established. Product-level physical performance is not established.

Synthetic tests, geometry screens, framework readiness, subsystem coverage and green CI, where present, remain digital evidence. None should be promoted into physical validation.

## Customer and commercial evidence

A founder-reported informal survey of around 20 people produced a preliminary signal around time and convenience, with concerns around comfort, maintenance and price. The underlying questionnaire, recruitment method and raw response data are not available in the repository, so this does not establish demand, willingness to pay, a validated customer segment or product-market fit. See the [customer discovery record](CUSTOMER_DISCOVERY.md).

## Next evidence stage

The next stage is deliberately narrower than adding features. Structured customer interviews should identify whether a sufficiently important first problem exists. Focused physical fit, fluid and cleaning work should then test whether a wearable removes more friction than it creates. Initial manufacturing-cost modelling should test whether required complexity has a plausible commercial path. Weak evidence should narrow, redesign or reject the relevant use case rather than be hidden by further digital scope.

## Founder and AI roles

AI is used extensively to accelerate implementation, research, alternative generation and engineering exploration. Founder judgement owns product direction, requirements, priorities, trade-offs and final decisions. AI-assisted digital work is not presented as independent physical proof, and specialist human expertise remains necessary where practical experience, measurement and regulated or manufacturing judgement matter.
