# Scholarship review snapshot

[Project overview](../README.md) · [Venture progress](VENTURE_PROGRESS.md) · [Evidence guide](EVIDENCE_GUIDE.md) · [Customer discovery](CUSTOMER_DISCOVERY.md)

Masck One is an early-stage, pre-commercialisation venture exploring whether parts of a multi-step facial-skincare routine can be automated to reduce active time and repetitive handling without creating a worse comfort, cleaning or maintenance burden.

This page is a one-page reviewer summary. It separates what has been built from what still needs customer, physical and commercial validation.

## Why the next stage matters

The venture is at an evidence inflection point. Enough controlled digital engineering now exists to define focused questions, but the evidence needed to justify a product is still weak in the areas that matter most commercially: customer problem strength, human fit and workflow, real fluid behaviour, hygiene burden and manufacturing economics.

That makes the next stage deliberately different from the work already completed. The priority is not to make the long-term concept more feature-complete. It is to test whether one narrow use case can earn continued development through stronger customer, physical and cost evidence.

| What the repository has made possible | What must happen before broader scope is justified |
| --- | --- |
| Requirements, parametric geometry, automated checks and integration records can be inspected and used to define focused tests. | Structured customer evidence must identify a sufficiently important first problem. |
| Major fit, fluid, cleaning and integration uncertainties are visible rather than hidden behind a concept render. | Focused physical work must show whether the selected use case creates net convenience in practice. |
| A bounded validation path and evidence rules already exist. | Initial manufacturing-cost evidence must show that the required complexity has a plausible commercial path. |

This is the scholarship leverage point: support can convert an unusually developed digital concept into decision-grade evidence, including evidence that may narrow, redesign or reject parts of the current vision. It is not presented as funding to finish an already-validated product.

## 60-second venture proof

| Question | Evidence-based answer |
| --- | --- |
| Is this more than an idea? | Yes in digital development: controlled requirements, code-generated parametric CAD, automated checks, design records and whole-product integration work are inspectable in the repository. No integrated manufactured product or product-level physical validation is claimed. |
| What customer problem is being tested? | Whether people who already follow multi-step skincare routines experience enough time and repetitive-handling friction for automation to create meaningful net convenience. The segment and problem strength remain hypotheses. |
| What is the first product? | Not yet locked. The immediate goal is to identify one routine task where customer value, physical feasibility and plausible economics overlap before committing to broader hardware scope. |
| What has customer research shown? | A founder-reported informal survey of around 20 people gave a preliminary signal around time and convenience, with concerns around comfort, maintenance and price. The method and raw data are not available here, so it does not establish demand or willingness to pay. |
| What happens next? | Structured customer interviews, focused simulation/analysis, a focused physical fit prototype, core fluid-delivery testing, hygiene/cleaning investigation and initial manufacturing-cost modelling. Each is intended to replace a material assumption with stronger evidence. |
| What would scholarship support change? | It would accelerate evidence generation through customer validation, prototype materials and test equipment, manufacturing/cost investigation and access to specialist human expertise, rather than funding presentation work or an assumed full product build. |
| How is AI used? | AI accelerates implementation, research, alternative generation and exploration. Founder judgement owns direction, requirements, priorities, trade-offs and final decisions. Specialist human expertise remains important for hardware, manufacturing, IP, fundraising and market entry. |

The current venture decision is therefore narrow: determine whether one first use case deserves focused physical development. The long-term wearable-and-dock concept remains a direction to earn, not a specification already validated.

## Proof already earned vs proof still required

This is the central maturity boundary for scholarship review.

| Already inspectable | Still needs evidence |
| --- | --- |
| Requirements have been translated into a controlled engineering authority and automated checks. | A specific customer problem and first use case strong enough to justify focused hardware development. |
| A reproducible code-generated parametric model and documented subsystem work exist. | Human fit, comfort and wearing-workflow evidence from a focused physical prototype. |
| Whole-product integration conflicts and unresolved technical questions are recorded rather than hidden. | Measured core fluid-delivery and recovery behaviour, plus practical hygiene and cleaning evidence. |
| Preliminary founder-reported customer feedback identifies time/convenience interest and comfort, maintenance and price concerns. | Structured customer interviews, stronger behavioural evidence and any credible pricing or willingness-to-pay evidence. |
| The repository contains an evidence-gated next-stage plan and explicit limits on what digital work proves. | Initial manufacturing-cost modelling and enough customer-value evidence to test commercial plausibility. |

The venture has therefore earned evidence of initiative, structured digital development and disciplined uncertainty management. It has not yet earned claims of product readiness, customer demand or commercial viability. Scholarship support would be used to close those specific evidence gaps.

## Fast reviewer inspection path

A reviewer can test the venture story without relying on presentation claims:

1. Read the **Venture snapshot** below for the problem, target-user hypothesis, first validation target and current evidence boundary.
2. Inspect the [engineering authority](../config/masck_one_authority.yaml) and [parametric model source](../src/masck_one/model.py) to confirm that the concept has progressed into controlled, reproducible digital engineering.
3. Read the [whole-product convergence review](CORE_SKETCH_CONVERGENCE_REVIEW.md) to see unresolved cross-system conflicts recorded rather than hidden.
4. Read the [customer discovery record](CUSTOMER_DISCOVERY.md) to see the preliminary survey evidence and its limitations, then the [venture progress page](VENTURE_PROGRESS.md) for the evidence-gated next stage.

The intended conclusion is deliberately bounded: there is substantial inspectable founder-led development, but the venture has not yet earned claims of customer demand, physical product performance or viable unit economics.

## Evidence classes at a glance

| Evidence class | What exists now | Reviewer interpretation |
| --- | --- | --- |
| Existing digital engineering evidence | [Parametric CAD](../src/masck_one/model.py), [controlled requirements](../config/masck_one_authority.yaml), [automated checks](../tests/test_authority_contract.py), source binding and documented design trade-offs. | Inspectable engineering discipline and digital consistency. It is not physical validation. |
| Planned validation | Customer interviews, focused fit and fluid tests, hygiene/cleaning investigation and initial manufacturing-cost modelling are defined as next evidence activities. | A plan or protocol shows what will be tested; it does not count as a completed result. |
| Physical/commercial evidence not yet obtained | Product-level customer demand, comfort, hygiene/cleaning practicality, real fluid behaviour, safety, manufacturing feasibility, unit economics and physical performance. | These remain open claims and must not be inferred from CAD, simulation, synthetic tests or CI. |

## Venture snapshot

| Reviewer question | Current position |
| --- | --- |
| Problem being explored | Multi-step skincare routines can involve repeated handling, active time and clean-up. The venture is testing whether automation can remove enough of that friction to justify a wearable system. |
| Target user hypothesis | People who already follow multi-step facial-skincare routines and value reducing active routine time and effort. This is not yet a validated customer segment. |
| Long-term direction | A wearable-and-dock system that could automate selected parts of a skincare routine. This is a product vision, not a committed first-product specification or a claim of working physical capability. |
| First validation target | One clearly defined routine task where customer value, physical feasibility and plausible economics overlap. The specific first use case is deliberately not locked until structured customer evidence is stronger. |
| What exists now | Controlled requirements, code-generated parametric CAD, automated engineering checks, design records, subsystem exploration and whole-product integration work that can be inspected in the repository. |
| Early customer evidence | The founder reports a small informal survey of around 20 people. The strongest reported interest was around time and convenience; concerns included comfort, maintenance and price. The underlying questionnaire, recruitment method and raw response data are not in the repository, so this is preliminary and non-conclusive. |
| What is not proven | Customer demand, willingness to pay, comfort and population fit, hygiene and cleaning practicality, real fluid behaviour, safety, manufacturability, production capability, unit economics and product-level physical performance. |
| Current venture decision | Determine whether a narrow first use case deserves focused physical development before expanding the broader concept. |

## Near-term decision sequence

The next stage is organised around three decisions rather than around adding features.

| Decision | Minimum evidence before deciding | If evidence is weak |
| --- | --- | --- |
| 1. Which problem is worth solving first? | Structured customer interviews showing a repeated routine friction and how people currently deal with it. | Narrow, change or reject the first-use-case hypothesis before deeper hardware spend. |
| 2. Can a wearable remove more friction than it creates? | Focused analysis followed by fit, fluid and cleaning evidence for the selected use case. | Simplify the workflow or mechanism, reconsider the wearable form, or stop that path. |
| 3. Is there a plausible product case? | Initial manufacturing-cost assumptions considered alongside customer-value and pricing evidence. | Reduce scope, change architecture or reconsider the commercial model before expanding the broader vision. |

This sequence is deliberately narrower than the long-term wearable-and-dock concept. A larger feature set is not treated as progress unless the preceding evidence supports it.

## First evidence sprint

The immediate work should produce decision-grade evidence before broader product development resumes. The sequence is intentionally staged so weak customer evidence can prevent unnecessary hardware spend.

| Stage | Output that should exist at the end | Gate to continue |
| --- | --- | --- |
| Customer problem | Structured interview notes and a short synthesis of repeated routine friction, current workarounds and rejection reasons. | A specific problem is repeated strongly enough to define a narrow first-use-case hypothesis. |
| Risk reduction | Focused simulation or analysis records identifying which fit, fluid and workflow assumptions cannot be resolved digitally. | The remaining physical questions are narrow enough to test without building the full product vision. |
| Physical evidence | A focused fit prototype record, core fluid-delivery test results and cleaning/hygiene observations for the selected use case. | Evidence suggests the wearable can create net convenience without an obviously disproportionate physical or maintenance burden. |
| Commercial check | An initial manufacturing-cost model using sourced component, process and assembly assumptions, considered alongside customer-value evidence. | There is enough overlap between plausible product complexity, cost and customer value to justify the next development cycle. |

A failed gate is a useful result. It should cause the use case, mechanism, workflow or commercial model to be narrowed or changed rather than being hidden by additional features. None of these sprint outputs is claimed as completed today.

## Evidence of initiative

The repository shows progression through inspectable outputs rather than presentation claims.

| Date | Inspectable milestone | Venture significance |
| --- | --- | --- |
| 30 August 2026 | [Authority-contract implementation](https://github.com/mlngaxri/MasckOne/commit/910d4fd1a03164e032847e590331cd7cddf51d8d) and [facial-reference landmark contract](https://github.com/mlngaxri/MasckOne/commit/9c427d5faec3687c1a1422c6bea3edd9394bffb3) | The project moved beyond an idea into controlled requirements, automated checks and reproducible engineering structure. |
| 10 September 2026 | [Whole-product convergence work](https://github.com/mlngaxri/MasckOne/commit/0044a55885000480a873b5761742341038b24b6a) and [authority reconciliation](https://github.com/mlngaxri/MasckOne/commit/0c0ccb1d1b3356ed0001e5e53f318973a2893e08) | Development expanded from isolated digital subsystems to explicit cross-subsystem conflicts, constraints and unresolved integration questions. |
| 14 September 2026 | [Public scholarship-review baseline](https://github.com/mlngaxri/MasckOne/commit/b4a105ea4483a6285be7d55fd527baea30ce6412) | The engineering record was reorganised for external review with clearer evidence boundaries and a distinction between digital work, planned validation and unsupported claims. |

Rapid digital progress does not imply rapid physical validation. The point of the chronology is to show sustained founder execution, traceable decisions and increasing evidence discipline.

## Reviewer evidence trail

A reviewer does not need to infer initiative from repository size or commit count. The following trail connects venture claims to inspectable outputs and keeps the evidence boundary visible.

| Venture signal | Inspectable output | What it supports | What it does not support |
| --- | --- | --- | --- |
| Requirements have been translated into engineering work | [Engineering authority](../config/masck_one_authority.yaml) and [authority contract tests](../tests/test_authority_contract.py) | Requirements are explicit enough to be checked and changed deliberately rather than existing only as presentation claims. | Achievement of those requirements in manufactured hardware. |
| The concept has progressed into reproducible digital engineering | [Parametric model source](../src/masck_one/model.py) and [model checks](../tests/test_model.py) | A reviewable, code-generated geometry and checking workflow exists. | Human fit, comfort, safety or physical performance. |
| Digital evidence is bound to its source rather than treated as timeless proof | [Boundary-release tests](../tests/test_boundary_release.py) | Source revision and registered geometry identity are checked so changed or stale digital evidence can fail closed; the checks also preserve a digital-only evidence label. | Anatomical validity, human fit, physical performance or qualification of a later source revision by an older passing result. |
| Cross-system trade-offs are being confronted | [Whole-product convergence review](CORE_SKETCH_CONVERGENCE_REVIEW.md) | Subsystem conflicts and unresolved integration questions are recorded rather than hidden behind a concept render. | A physically integrated or production-ready product. |
| Customer uncertainty is being treated separately from engineering progress | [Customer discovery record](CUSTOMER_DISCOVERY.md) | Preliminary learning is distinguished from the structured research still required. | Demand, willingness to pay, a validated segment or product-market fit. |
| External review has been made possible without inflating maturity | [Evidence guide](EVIDENCE_GUIDE.md) and [venture progress](VENTURE_PROGRESS.md) | Reviewers can trace outputs, limitations and next evidence needs directly. | Any upgrade in physical or commercial evidence merely because documentation is clearer. |

## What happens next

The next stage should reduce uncertainty in sequence rather than increase feature count.

| Next activity | Evidence sought | Decision it should enable |
| --- | --- | --- |
| Structured customer interviews | Repeated examples of real routine friction, existing alternatives, objections and reasons people would or would not change behaviour | Select, narrow or reject the first use case. |
| Focused simulation and analysis | Better bounds on high-risk assumptions before hardware spend | Identify which questions genuinely need physical testing first. |
| Focused physical fit prototype | Measured observations about geometry, wearing workflow and fit assumptions | Decide whether the selected use case deserves deeper wearable development. |
| Core fluid-delivery testing | Controlled measurements of delivery and recovery behaviour | Continue, redesign or reject the fluid approach. |
| Hygiene and cleaning investigation | Evidence about preparation, cleaning burden and sanitation requirements | Determine whether maintenance erases the intended convenience benefit. |
| Initial manufacturing-cost modelling | Sourced component, process and assembly assumptions | Test whether plausible product cost can overlap with demonstrated customer value. |

These are planned evidence-generating activities, not completed results.

## Founder and AI roles

AI is used extensively to accelerate implementation, research, alternative generation and engineering exploration. Founder judgement owns product direction, requirements, priorities, trade-offs and final decisions.

The repository does not present AI-assisted digital work as independent physical proof. Specialist human expertise and collaboration remain important for hardware, manufacturing, IP, fundraising and market entry, particularly where practical experience and measurement are required.

## Current evidence posture

Masck One is not an idea-only application, because substantial inspectable digital engineering and venture-development work already exists. It is also not presented as a validated product. The next milestone is stronger customer, physical and commercial evidence for a narrow first use case, followed by a decision on whether the broader wearable-and-dock vision has earned further scope.
