# Scholarship review snapshot

[Project overview](../README.md) · [Venture progress](VENTURE_PROGRESS.md) · [Founder execution timeline](SCHOLARSHIP_FOUNDER_EXECUTION_TIMELINE.md) · [Customer discovery](CUSTOMER_DISCOVERY.md) · [Next-stage evidence plan](SCHOLARSHIP_NEXT_STAGE.md)

Masck One is a pre-commercialisation venture exploring whether selected parts of a facial-skincare routine can be made less hands-on through a wearable device and supporting dock. Engineering geometry, requirements, code-based CAD, automated checks and design records exist. Product-level physical validation has not begun.

This is the short reviewer path. It separates what has been built from what still needs customer, physical and commercial evidence. For a dated, commit-linked record of execution, see the [founder execution timeline](SCHOLARSHIP_FOUNDER_EXECUTION_TIMELINE.md).

Engineering-source links below are pinned to live engineering `main` revision `8d37bc322b5ebe42179685a1a0559f2fcb1b5f22`, verified on 17 September 2026. Scholarship documentation may advance independently and must not be read as a newer engineering release.

## Venture snapshot

| Question | Current position |
| --- | --- |
| Problem being explored | Whether routine skincare can require less active time and repetitive handling without creating greater fitting, cleaning, maintenance or ownership burden. |
| Target user hypothesis | People who already follow multi-step facial-skincare routines and value reducing active routine time. This is not yet a validated segment. |
| Long-term direction | A wearable-and-dock system that could automate selected routine steps. This is a direction, not a committed first-product specification. |
| First testable use case | Deliberately not locked. Structured customer evidence should identify one repeated routine problem worth solving before broader hardware scope is justified. |
| What has been built | Controlled requirements, parametric engineering geometry, automated checks, documented design decisions and cross-subsystem integration work that can be inspected in the repository. |
| Early customer research | A founder-reported informal survey of around 20 people is preliminary and non-conclusive. The strongest reported interest was time/convenience; concerns included comfort, maintenance and price. It does not establish demand or willingness to pay. |
| Key uncertainties | Customer value, fit and comfort, real fluid behaviour, hygiene and cleaning burden, safety, manufacturing feasibility and unit economics remain unproven. |
| What happens next | Structured customer interviews, focused simulation/analysis, a focused physical fit prototype, core fluid-delivery testing, hygiene/cleaning investigation and initial manufacturing-cost modelling. |

## 60-second engineering evidence map

| Claim a reviewer may test | Representative evidence | What it establishes | Boundary |
| --- | --- | --- | --- |
| Parametric CAD exists | [Parametric model source](https://github.com/mlngaxri/MasckOne/blob/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22/src/masck_one/model.py) and [model checks](https://github.com/mlngaxri/MasckOne/blob/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22/tests/test_model.py) | Inspectable, code-generated geometry and digital integrity checks exist. | Not human fit, comfort, safety, manufacturability or physical performance. |
| System requirements are controlled | [Engineering authority](https://github.com/mlngaxri/MasckOne/blob/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22/config/masck_one_authority.yaml) and [authority contract tests](https://github.com/mlngaxri/MasckOne/blob/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22/tests/test_authority_contract.py) | Controlled values and dependent sources can be checked for consistency. | Consistency does not prove the values are correct, safe or achieved by hardware. |
| Engineering evidence is source-bound | [Boundary-release tests](https://github.com/mlngaxri/MasckOne/blob/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22/tests/test_boundary_release.py) | Revision identity and digital-only evidence boundaries are checked. | Not anatomical validity, physical performance or qualification of later revisions by older results. |
| Design decisions are documented | [Whole-product convergence review](https://github.com/mlngaxri/MasckOne/blob/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22/docs/CORE_SKETCH_CONVERGENCE_REVIEW.md) | Cross-subsystem conflicts, trade-offs, unresolved dependencies and validation gates are recorded. | A documented decision is not proof the architecture works physically or commercially. |
| Major subsystems have inspectable digital coverage | [Whole-product convergence review](https://github.com/mlngaxri/MasckOne/blob/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22/docs/CORE_SKETCH_CONVERGENCE_REVIEW.md) and [compliant interface topology](https://github.com/mlngaxri/MasckOne/blob/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22/docs/COMPLIANT_INTERFACE_TOPOLOGY.md) | Facial interface, structure/retention, actuation and fluid/waste interactions are represented in system-level digital engineering records rather than isolated feature claims. | Coverage means the subsystem interactions are documented and reviewable, not that any subsystem has passed physical verification. |

## Evidence boundary

The repository demonstrates active venture development through inspectable outputs. It does not currently prove customer demand or willingness to pay; comfort or population fit; hygiene, cleaning or maintenance practicality; real fluid delivery, leakage or recovery behaviour; product safety; manufacturing feasibility; viable unit economics; or product-level physical performance.

Synthetic tests, geometry screens, simulation frameworks and software checks remain digital evidence unless qualifying physical measurements exist. Rapid digital progress should not be interpreted as rapid physical validation.

## Evidence before expansion

The broader wearable-and-dock vision should not determine first-product scope. Customer evidence should first earn the right to test a focused use case physically. Focused physical evidence should then earn the right to investigate a product architecture more deeply. Customer value plus sourced cost evidence should earn the right to consider broader scope.

Weak evidence should narrow, change or reject a use case rather than be hidden by additional feature development.

## How scholarship support converts to evidence

Scholarship support would be most useful when directed to structured customer validation, prototype materials and test equipment for focused fit/fluid/cleaning questions, and manufacturing and cost investigation. No funding amount or outcome is assumed. The purpose is to replace important assumptions with evidence, not to make the concept look more complete.

AI is used extensively to accelerate implementation, research, alternative generation and engineering exploration. Founder judgement owns venture direction, requirements, priorities, trade-offs and final decisions. Specialist human expertise and collaboration remain important for hardware, manufacturing, IP, fundraising and market entry.

See [Venture progress](VENTURE_PROGRESS.md) for the fuller reviewer-facing progression and [Next-stage evidence plan](SCHOLARSHIP_NEXT_STAGE.md) for the evidence gates.