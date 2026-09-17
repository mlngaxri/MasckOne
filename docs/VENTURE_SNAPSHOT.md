# Venture snapshot

Masck One is a pre-commercialisation venture exploring whether selected parts of a facial-skincare routine can be made less hands-on through a wearable device and supporting dock. This page is the shortest non-technical view of the venture case. It separates existing work from the evidence still needed before a first product should be defined.

## Current venture maturity

Masck One has moved beyond an idea into structured, inspectable digital development, but it has not yet earned product or market validation. The repository supports three different maturity statements that should not be collapsed into one:

| Stage | Current status | Basis |
| --- | --- | --- |
| Venture definition | Established enough to test | A problem hypothesis, target-user hypothesis, long-term product direction, controlled requirements and an evidence-gated development path are documented. |
| Digital engineering development | Substantial and inspectable | Code-based CAD, engineering geometry, automated-check source, subsystem records, integration reviews and dated repository history exist. |
| Customer, physical and commercial validation | Early / not established | The informal survey is preliminary; structured customer interviews, focused physical testing, hygiene investigation and manufacturing-cost modelling remain next-stage work. |

This distinction is the central scholarship-review point: the venture has evidence of initiative and development, while the evidence needed to justify a first product remains deliberately open.

## Progress in dates

A reviewer does not need to infer initiative from commit volume. Four dated repository milestones show the development progression:

| Date | Verifiable milestone | Venture-level significance |
| --- | --- | --- |
| 30 August 2026 | [Controlled requirements and facial-reference geometry](https://github.com/mlngaxri/MasckOne/commit/910d4fd1a03164e032847e590331cd7cddf51d8d) | Product intent began becoming inspectable engineering artefacts rather than remaining only a concept. |
| 10 September 2026 | [Whole-product convergence work](https://github.com/mlngaxri/MasckOne/commit/0044a55885000480a873b5761742341038b24b6a) | Work progressed into explicit cross-subsystem conflicts, trade-offs and evidence gates. |
| 14 September 2026 | [Public scholarship-review baseline](https://github.com/mlngaxri/MasckOne/commit/b4a105ea4483a6285be7d55fd527baea30ce6412) | Existing work, planned validation and unsupported claims were separated for external scrutiny. |
| 16 September 2026 | [Current engineering baseline](https://github.com/mlngaxri/MasckOne/commit/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22) | The public engineering record continued to be curated, including removal of obsolete concept renders rather than presenting them as current evidence. |

This chronology demonstrates sustained digital execution over the public repository's first weeks. It does not demonstrate customer traction, physical validation, revenue, partnerships or product readiness. The [full founder execution timeline](SCHOLARSHIP_FOUNDER_EXECUTION_TIMELINE.md) provides the claim boundaries and next evidence handoff behind these milestones.

## The venture in one page

| Question | Current position | Evidence boundary / next decision |
| --- | --- | --- |
| What problem is being explored? | Multi-step facial-skincare routines can require repeated active handling and time. The venture is exploring whether a device can reduce that burden. | The importance and frequency of this problem still need structured customer validation. |
| Who is the target user? | The initial hypothesis is people who already follow multi-step facial-skincare routines and value reducing active time and repetitive handling. | This is a target-user hypothesis, not a validated segment. |
| What is the first product use case? | Not yet locked. The broader wearable-and-dock concept is a long-term direction, not a committed first-product specification. | Structured customer evidence should identify one routine task where customer value, physical feasibility and plausible economics overlap. |
| What has been built? | Inspectable requirements, engineering geometry, code-based CAD, automated-check source, subsystem records and whole-product integration work exist in the repository. | This demonstrates active digital development, not customer demand, physical performance, comfort, safety, manufacturability or product readiness. |
| What customer evidence exists? | A founder-reported informal survey of around 20 people provides a preliminary, non-conclusive signal. Time/convenience was the strongest reported interest; comfort, maintenance and price were recurring concerns. | The underlying questionnaire, recruitment method and response data are not complete enough in the repository for independent assessment. Structured interviews are the next step. |
| What are the largest uncertainties? | Whether a sufficiently important first problem exists; whether fitting, loading, cleaning and storage still create net convenience; whether core fit and fluid behaviour work physically; whether hygiene is practical; and whether manufacturing cost can overlap with customer value. | These questions remain open. Digital engineering or AI-assisted analysis cannot close the physical and commercial ones by itself. |
| What happens next? | Structured customer interviews; focused simulation and analysis; a focused physical fit prototype; core fluid-delivery testing; hygiene and cleaning investigation; and initial manufacturing-cost modelling. | Each activity should produce evidence that can advance, narrow, redesign or reject the relevant path. They are planned activities, not completed results. |

## What a reviewer can verify now

The venture is not presented as idea-only because its development history is inspectable. At engineering `main` revision [`8d37bc322b5ebe42179685a1a0559f2fcb1b5f22`](https://github.com/mlngaxri/MasckOne/tree/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22), a reviewer can inspect the [controlled engineering authority](https://github.com/mlngaxri/MasckOne/blob/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22/config/masck_one_authority.yaml), [code-based parametric model](https://github.com/mlngaxri/MasckOne/blob/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22/src/masck_one/model.py), [automated authority-contract checks](https://github.com/mlngaxri/MasckOne/blob/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22/tests/test_authority_contract.py) and [whole-product convergence review](https://github.com/mlngaxri/MasckOne/blob/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22/docs/CORE_SKETCH_CONVERGENCE_REVIEW.md).

No pull-request-triggered workflow run is recorded for that exact engineering revision. The linked automated-check source is therefore inspectable framework evidence, not evidence that current `main` has a recorded CI pass.

The [founder execution timeline](SCHOLARSHIP_FOUNDER_EXECUTION_TIMELINE.md) links dated repository milestones to commits so progress can be checked through outputs and chronology rather than accepted as a founder claim. The [claim ledger](SCHOLARSHIP_CLAIM_LEDGER.md) separately marks what those outputs do and do not establish.

This verification path is intentionally narrow. It demonstrates sustained, structured digital development. It does not convert repository activity into evidence of customer demand, physical validation, revenue, partnerships or technical performance.

## Long-term vision versus first validation target

The long-term direction is a wearable-and-dock system that could automate selected parts of a facial-skincare routine. It should not determine the first-product scope simply because more functions can be designed digitally.

The immediate objective is to identify one use case that repeatedly matters to customers, can create net convenience after fitting and maintenance are considered, can be reduced to focused physical tests, and has a plausible path to manufacturing economics. Weak evidence should narrow, change or reject the use case rather than trigger more feature development.

## How the first use case will be chosen

The first use case should be earned by evidence rather than selected from the breadth of the long-term concept. Before scope is locked, a candidate should pass five linked questions:

| Decision question | Evidence needed | If evidence is weak |
| --- | --- | --- |
| Does the problem matter often enough? | Repeated patterns from structured interviews with the target-user hypothesis. | Narrow the segment, change the problem or stop pursuing that use case. |
| Does the device create net convenience? | Customer workflow evidence that accounts for fitting, loading, cleaning and storage, not just active treatment time. | Simplify the workflow or reject the use case. |
| Can the core interaction be tested physically? | A focused fit prototype and core fluid-delivery tests that isolate the relevant physical questions. | Redesign or reduce scope before broader prototyping. |
| Can hygiene and maintenance be acceptable? | Cleaning and hygiene investigation tied to the actual first-use workflow. | Change the architecture or reject the workflow. |
| Is there a plausible commercial path? | Initial sourced manufacturing-cost modelling considered alongside customer value and price sensitivity. | Reduce cost or scope before treating the concept as a product candidate. |

No candidate currently passes all five gates. This is a selection framework for the next evidence stage, not a claim that a first product has been chosen or validated.

## How support would become evidence

Scholarship support would be most useful when converted into structured customer validation, prototype materials and test equipment for focused fit, fluid and cleaning questions, and manufacturing and cost investigation. No funding amount, technical result or commercial outcome is assumed.

AI is used extensively to accelerate implementation, research, alternative generation and engineering exploration. Founder judgement owns venture direction, requirements, priorities, trade-offs and final decisions. Specialist human expertise and collaboration remain important for hardware, manufacturing, IP, fundraising and market entry.

## Current evidence boundary

Masck One has substantial inspectable digital-development evidence. It does not currently prove customer demand or willingness to pay, comfort or population fit, hygiene and cleaning practicality, real fluid behaviour, product safety, manufacturing feasibility, viable unit economics or product-level physical performance.

For the supporting evidence, see [Venture progress](VENTURE_PROGRESS.md), [Customer discovery](CUSTOMER_DISCOVERY.md), [Founder execution timeline](SCHOLARSHIP_FOUNDER_EXECUTION_TIMELINE.md), [Claim ledger](SCHOLARSHIP_CLAIM_LEDGER.md) and [Next-stage evidence plan](SCHOLARSHIP_NEXT_STAGE.md).
