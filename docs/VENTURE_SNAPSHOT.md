# Venture snapshot

I am developing Masck One as a pre-commercialisation venture exploring whether selected parts of a facial-skincare routine can be made less hands-on through a wearable device and supporting dock. This page is the shortest non-technical view of my venture case. I separate existing work from the evidence I still need before I should define a first product.

## Current venture maturity

I have moved Masck One beyond an idea into structured, inspectable digital development, but I have not yet earned product or market validation. I separate the current maturity into three different statements:

| Stage | Current status | Basis |
| --- | --- | --- |
| Venture definition | Established enough to test | I have documented a problem hypothesis, target-user hypothesis, long-term product direction, controlled requirements and an evidence-gated development path. |
| Digital engineering development | Substantial and inspectable | I have built and organised code-based CAD, engineering geometry, automated-check source, subsystem records, integration reviews and a dated repository history. |
| Customer, physical and commercial validation | Early / not established | My informal survey is preliminary; structured customer interviews, focused physical testing, hygiene investigation and manufacturing-cost modelling remain next-stage work. |

This distinction is central to how I present Masck One for scholarship review: I can show initiative and development through inspectable outputs, while the evidence needed to justify a first product remains deliberately open.

## Progress in dates

I do not rely on commit volume as evidence of initiative. Five dated repository milestones show how my work has progressed:

| Date | Verifiable milestone | Venture-level significance |
| --- | --- | --- |
| 30 August 2026 | [Controlled requirements and facial-reference geometry](https://github.com/mlngaxri/MasckOne/commit/910d4fd1a03164e032847e590331cd7cddf51d8d) | I began turning product intent into inspectable engineering artefacts rather than leaving it only as a concept. |
| 10 September 2026 | [Whole-product convergence work](https://github.com/mlngaxri/MasckOne/commit/0044a55885000480a873b5761742341038b24b6a) | I progressed into explicit cross-subsystem conflicts, trade-offs and evidence gates. |
| 14 September 2026 | [Public scholarship-review baseline](https://github.com/mlngaxri/MasckOne/commit/b4a105ea4483a6285be7d55fd527baea30ce6412) | I separated existing work, planned validation and unsupported claims for external scrutiny. |
| 16 September 2026 | [Engineering baseline](https://github.com/mlngaxri/MasckOne/commit/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22) | I continued curating the public engineering record, including removing obsolete concept renders rather than presenting them as current evidence. |
| 18 September 2026 | [Current engineering baseline](https://github.com/mlngaxri/MasckOne/commit/becf782bf809543ba4b83ecab689204b2458de7d) | I continued tightening the public documentation and evidence trail while keeping physical and commercial uncertainties explicit. |

This chronology shows sustained digital execution over the public repository's first weeks. I do not treat it as evidence of customer traction, physical validation, revenue, partnerships or product readiness. The [full execution timeline](SCHOLARSHIP_EXECUTION_TIMELINE.md) provides the claim boundaries and next evidence handoff behind these milestones.

## The venture in one page

| Question | Current position | Evidence boundary / next decision |
| --- | --- | --- |
| What problem am I exploring? | Multi-step facial-skincare routines can require repeated active handling and time. I am exploring whether a device can reduce that burden. | I still need structured customer validation to establish the importance and frequency of this problem. |
| Who is my target user? | My initial hypothesis is people who already follow multi-step facial-skincare routines and value reducing active time and repetitive handling. | This is a target-user hypothesis, not a validated segment. |
| What is the first product use case? | I have not locked it yet. The broader wearable-and-dock concept is my long-term direction, not a committed first-product specification. | I want structured customer evidence to identify one routine task where customer value, physical feasibility and plausible economics overlap. |
| What have I built? | I have created inspectable requirements, engineering geometry, code-based CAD, automated-check source, subsystem records and whole-product integration work in this repository. | This demonstrates active digital development, not customer demand, physical performance, comfort, safety, manufacturability or product readiness. |
| What customer evidence do I have? | I conducted an informal survey of around 20 people. It provides a preliminary, non-conclusive signal: time/convenience was the strongest reported interest; comfort, maintenance and price were recurring concerns. | My underlying questionnaire, recruitment method and response data are not complete enough in the repository for independent assessment. Structured interviews are my next step. |
| What are my largest uncertainties? | Whether a sufficiently important first problem exists; whether fitting, loading, cleaning and storage still create net convenience; whether core fit and fluid behaviour work physically; whether hygiene is practical; and whether manufacturing cost can overlap with customer value. | These questions remain open. Digital engineering or AI-assisted analysis cannot close the physical and commercial ones by itself. |
| What happens next? | I plan structured customer interviews; focused simulation and analysis; a focused physical fit prototype; core fluid-delivery testing; hygiene and cleaning investigation; and initial manufacturing-cost modelling. | Each activity should produce evidence that lets me advance, narrow, redesign or reject the relevant path. These are planned activities, not completed results. |

## What a reviewer can verify now

I do not present Masck One as idea-only because my development history is inspectable. At live engineering `main` revision [`becf782bf809543ba4b83ecab689204b2458de7d`](https://github.com/mlngaxri/MasckOne/tree/becf782bf809543ba4b83ecab689204b2458de7d), a reviewer can inspect the [controlled engineering authority](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/config/masck_one_authority.yaml), [code-based parametric model](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/src/masck_one/model.py), [automated authority-contract checks](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/tests/test_authority_contract.py) and [whole-product convergence review](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/docs/CORE_SKETCH_CONVERGENCE_REVIEW.md).

The [execution timeline](SCHOLARSHIP_EXECUTION_TIMELINE.md) links dated repository milestones to commits so my progress can be checked through outputs and chronology rather than accepted as a claim from me. The [claim ledger](SCHOLARSHIP_CLAIM_LEDGER.md) separately marks what those outputs do and do not establish.

I keep this verification path intentionally narrow. It demonstrates sustained, structured digital development. I do not use repository activity as evidence of customer demand, physical validation, revenue, partnerships or technical performance.

## Long-term vision versus first validation target

My long-term direction is a wearable-and-dock system that could automate selected parts of a facial-skincare routine. I do not want the breadth of that vision to determine first-product scope simply because more functions can be designed digitally.

My immediate objective is to identify one use case that repeatedly matters to customers, can create net convenience after fitting and maintenance are considered, can be reduced to focused physical tests, and has a plausible path to manufacturing economics. If the evidence is weak, I should narrow, change or reject the use case rather than add more features.

## How I will choose the first use case

I want the first use case to be earned by evidence rather than selected from the breadth of the long-term concept. Before I lock scope, a candidate should pass five linked questions:

| Decision question | Evidence needed | If evidence is weak |
| --- | --- | --- |
| Does the problem matter often enough? | Repeated patterns from structured interviews with my target-user hypothesis. | I narrow the segment, change the problem or stop pursuing that use case. |
| Does the device create net convenience? | Customer workflow evidence that accounts for fitting, loading, cleaning and storage, not just active treatment time. | I simplify the workflow or reject the use case. |
| Can I test the core interaction physically? | A focused fit prototype and core fluid-delivery tests that isolate the relevant physical questions. | I redesign or reduce scope before broader prototyping. |
| Can hygiene and maintenance be acceptable? | Cleaning and hygiene investigation tied to the actual first-use workflow. | I change the architecture or reject the workflow. |
| Is there a plausible commercial path? | Initial sourced manufacturing-cost modelling considered alongside customer value and price sensitivity. | I reduce cost or scope before treating the concept as a product candidate. |

I do not currently have a candidate that passes all five gates. This is my selection framework for the next evidence stage, not a claim that I have chosen or validated a first product.

## Commercial questions I need to earn answers to

I do not yet have evidence for a price, unit economics or a viable business model, so I do not present invented commercial numbers. Instead, I have reduced commercial uncertainty to a sequence of decisions that can be tested alongside the first use case:

| Commercial question | Evidence I need | Decision it informs |
| --- | --- | --- |
| Is the problem valuable enough to pay to solve? | Structured interviews that probe current alternatives, inconvenience and price sensitivity without treating stated interest as a purchase commitment. | Whether a first-use-case candidate deserves further development. |
| What does the minimum useful product actually need? | Customer workflow evidence combined with focused physical results. | Which functions belong in the first scope and which should remain part of the longer-term vision. |
| What is likely to drive cost? | Sourced manufacturing assumptions for the narrowed architecture, materials, components, assembly and consumable or maintenance requirements where relevant. | Whether I should simplify architecture, change scope or continue cost investigation. |
| Can likely cost and customer value plausibly overlap? | Early cost modelling considered against customer evidence, including price sensitivity. | Whether there is enough commercial plausibility to justify broader product development. |

This keeps commercial thinking connected to evidence rather than to a speculative valuation, launch price or margin. If the likely cost structure cannot support the value customers describe, I should change the product before treating it as commercially viable.

## Decisions the next evidence should unlock

I want the next stage to change decisions, not simply create more documents or features. I will use each evidence stream to answer a specific venture question:

| Evidence I plan to obtain | Decision it should let me make |
| --- | --- |
| Structured customer interviews | Decide whether the time/convenience problem is important and repeated enough to justify a first-use-case candidate, and which routine task deserves focus. |
| Focused simulation and analysis | Decide which assumptions are worth carrying into physical testing and which should be rejected or narrowed before spending on prototypes. |
| Focused physical fit prototype | Decide whether the basic wearable interaction is credible enough to continue, or whether fit, access or comfort constraints require architectural change. |
| Core fluid-delivery testing | Decide whether the minimum fluid interaction for the selected use case is physically credible enough for further development. |
| Hygiene and cleaning investigation | Decide whether the proposed workflow can remain convenient once cleaning and maintenance are included, or whether the architecture needs to change. |
| Initial manufacturing-cost modelling | Decide whether likely product scope and cost can plausibly overlap with customer value and price sensitivity before broader development. |

I will treat a negative result as useful evidence. If a core assumption fails, my next step should be to narrow, redesign or stop that path rather than use scholarship support to make the concept appear more complete.

## Next milestone sequence

I am deliberately sequencing the next stage so later spending depends on earlier evidence rather than on the breadth of the long-term concept.

| Milestone | Work | Evidence required before progressing |
| --- | --- | --- |
| 1. Establish the customer problem | I will run structured interviews with my target-user hypothesis, focused on current routines, time burden, fitting/loading/cleaning trade-offs and price sensitivity. | I need a repeatable problem and workflow pattern strong enough to nominate one first-use-case candidate. If it does not emerge, I will narrow or change the use case before physical work expands. |
| 2. Test the minimum physical case | I will use focused simulation/analysis, a physical fit prototype, core fluid-delivery testing, and hygiene/cleaning investigation for the nominated use case. | I need direct observations showing whether the core interaction is feasible enough to continue and what must change. I will not treat these tests as product-level validation. |
| 3. Test whether the case could become a product | I will build initial manufacturing-cost modelling using sourced assumptions, considered alongside customer value and price sensitivity. | I need a first evidence-based view of whether scope, likely cost and customer value can plausibly overlap. If they cannot, I will reduce scope, redesign or stop before broader product development. |

Scholarship support would therefore help me accelerate an evidence sequence rather than a feature roadmap: customer validation first, focused physical evidence second, and commercial feasibility third. The detailed outputs expected from each activity are defined in [Next evidence deliverables](SCHOLARSHIP_NEXT_EVIDENCE_DELIVERABLES.md).

## Where I need specialist collaboration

I use AI extensively to accelerate implementation, research, alternative generation and engineering exploration, but I do not treat AI output or my own digital work as a substitute for specialist judgement where the evidence depends on real hardware, commercial practice or regulated professional advice.

| Area | My role | Specialist contribution I expect to need |
| --- | --- | --- |
| Hardware and physical testing | I set the product questions, requirements, test intent and trade-offs. | Appropriate mechanical, materials and testing expertise to challenge assumptions and help turn digital hypotheses into defensible physical evidence. |
| Manufacturing and cost | I define the use case and cost questions that matter to the venture. | Manufacturing and supplier expertise to test process assumptions, sourcing constraints, tolerances and realistic cost drivers. |
| IP | I decide what technical and commercial directions I want to pursue. | Qualified IP advice before I make decisions that depend on patentability, freedom to operate or protection strategy. |
| Fundraising and market entry | I own the venture direction and the evidence I choose to present. | Experienced commercial guidance on financing, go-to-market choices and the standard of evidence expected at later stages. |

I see collaboration as part of the next evidence stage, not as a way to borrow credibility. My responsibility remains to decide what Masck One should test, make the trade-offs, and change direction when evidence does not support the current path.

## How I would turn support into evidence

I would use scholarship support to accelerate structured customer validation, obtain prototype materials and test equipment for focused fit, fluid and cleaning questions, and investigate manufacturing and cost. I am not assuming any funding amount, technical result or commercial outcome.

I use AI extensively to accelerate implementation, research, alternative generation and engineering exploration. I retain responsibility for venture direction, requirements, priorities, trade-offs and final decisions. I also expect specialist human expertise and collaboration to be important for hardware, manufacturing, IP, fundraising and market entry.

## Current evidence boundary

I have substantial inspectable digital-development evidence for Masck One. I do not currently have evidence proving customer demand or willingness to pay, comfort or population fit, hygiene and cleaning practicality, real fluid behaviour, product safety, manufacturing feasibility, viable unit economics or product-level physical performance.

For the supporting evidence, see [Venture progress](VENTURE_PROGRESS.md), [Customer discovery](CUSTOMER_DISCOVERY.md), [Execution timeline](SCHOLARSHIP_EXECUTION_TIMELINE.md), [Claim ledger](SCHOLARSHIP_CLAIM_LEDGER.md) and [Next-stage evidence plan](SCHOLARSHIP_NEXT_STAGE.md).
