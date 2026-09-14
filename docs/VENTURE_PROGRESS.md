# Venture progress

[Project overview](../README.md) · [Evidence guide](EVIDENCE_GUIDE.md) · [Customer discovery](CUSTOMER_DISCOVERY.md)

Masck One is pre-commercialisation. Engineering geometry exists and digital checks and validation frameworks exist, but product-level physical validation has not begun. There is no integrated manufactured product, and customer demand, physical product performance and viable unit economics remain unproven.

This page gives a scholarship reviewer a short evidence-based view of what has been done, what remains uncertain and what should happen next.

## Progress that can be inspected now

| Venture progress | Inspectable repository evidence | What it demonstrates | What it does not prove |
| --- | --- | --- | --- |
| Controlled product definition | [Engineering authority](../config/masck_one_authority.yaml), [product concept](PRODUCT_CONCEPT.md) and [development roadmap](DEVELOPMENT_ROADMAP.md) | Requirements, architecture and development state are recorded rather than existing only as an idea or presentation. | That the requirements are physically achievable or commercially justified. |
| Digital engineering build-out | [Engineering source](../src/masck_one/), [tests](../tests/) and [engineering quickstart](ENGINEERING_QUICKSTART.md) | Parametric geometry, engineering logic and automated checks have been implemented in a reproducible repository. | Human fit, comfort, safety, fluid performance, manufacturability or product readiness. |
| Whole-product integration work | [Convergence review](CORE_SKETCH_CONVERGENCE_REVIEW.md), [status board](CORE_SKETCH_STATUS_BOARD.md) and [contact/occlusion matrix](CORE_SKETCH_CONTACT_OCCLUSION_MATRIX.md) | Cross-subsystem conflicts and unknowns are being tracked instead of being hidden behind a polished concept. | That those conflicts have been solved physically. |
| Early commercial learning | [Customer discovery](CUSTOMER_DISCOVERY.md) | A founder-reported informal survey of around 20 people provides a preliminary signal around time/convenience, with concerns around comfort, maintenance and price. | Representative demand, willingness to pay, customer conversion or product-market fit. |
| Public evidence discipline | [Evidence guide](EVIDENCE_GUIDE.md) | Digital work, planned validation and unsupported claims are separated explicitly for external review. | Additional product maturity by itself. |

The short [repository chronology](EVIDENCE_GUIDE.md#verifiable-repository-chronology) shows how this work accumulated through inspectable commits. Rapid digital progress should not be interpreted as rapid physical validation.

## Evidence maturity at a glance

This is a venture-stage map, not a readiness score. It is intended to make the strongest evidence and the largest gaps visible in one scan.

| Evidence area | Current evidence state | Next evidence needed |
| --- | --- | --- |
| Customer problem | Preliminary founder-reported feedback only. Time/convenience appears to be the strongest interest signal; comfort, maintenance and price are recurring concerns. | Structured interviews focused on real routine friction, existing alternatives, rejection reasons and willingness to change behaviour. |
| Digital engineering | Substantial inspectable work exists: requirements, parametric geometry, automated checks, design records and cross-subsystem integration analysis. | Continue only where analysis can reduce uncertainty before hardware testing; digital work should not substitute for measurement. |
| Fit and wearing workflow | Not physically validated. Current work is digital geometry, requirements and validation planning. | A focused physical fit prototype with measured observations against a narrow first-use-case question. |
| Fluid delivery, recovery and hygiene | Architectures, routes and test concepts exist digitally; product-level physical behaviour is not established. | Controlled core fluid-delivery and recovery tests, followed by cleaning and hygiene investigation. |
| Manufacturing and economics | Engineering constraints are being considered, but manufacturing feasibility, production capability and viable unit economics are not proven. | Initial process and assembly assumptions, sourced cost estimates and a first manufacturing-cost model. |
| Broad wearable-and-dock vision | Product direction only. It should not be read as a committed first-product specification. | Expand scope only after a narrower use case passes customer, physical and commercial evidence gates. |

The asymmetry is deliberate: the project currently has much stronger digital-development evidence than customer, physical or commercial validation. The next stage should close that gap rather than maximise feature count.

## Product vision versus first validation target

The long-term direction is a wearable-and-dock system that could automate selected parts of a facial-skincare routine. That is a product vision, not a claim that every function belongs in a first product or already works.

The initial target user hypothesis is people who already follow multi-step facial-skincare routines and value reducing the active time and repetitive handling those routines require. This remains a hypothesis to test, not a validated customer segment.

The immediate objective is narrower: identify one routine task where customer value, physical feasibility and plausible economics overlap, then test that use case before expanding scope. The first use case is deliberately not locked until structured customer evidence is stronger.

### How the first use case will be selected

The first use case should earn its way into development rather than being chosen because it is technically interesting. A candidate should meet all four conditions below strongly enough to justify focused physical testing.

| Selection condition | Evidence required before committing |
| --- | --- |
| Repeated customer friction | Structured interviews identify the same routine task as a real source of time, effort or inconvenience, rather than only positive reactions to the concept. |
| Net convenience | The likely benefit is not obviously cancelled by fitting, loading, cleaning, maintenance or storage burden. |
| Testable physical path | The core fit and fluid questions can be reduced to focused prototypes and measurements without building the full wearable-and-dock system first. |
| Commercial plausibility | Early cost assumptions and customer-value evidence leave a credible path to a product whose complexity is justified. |

Failure on any condition is a reason to narrow, change or reject the use case. Repository activity and feature count are not substitutes for passing these evidence gates.

## What happens next

| Next step | Evidence sought | Decision enabled |
| --- | --- | --- |
| Structured customer interviews | Repeated examples of real routine friction, alternatives already used and reasons people would reject the concept | Select, narrow or reject the first use case. |
| Focused simulation and analysis | Better bounds on high-risk assumptions before spending on hardware | Decide which questions genuinely need physical testing first. |
| Focused physical fit prototype | Measured evidence about geometry, wearing workflow and fit assumptions | Determine whether the selected use case deserves deeper wearable development. |
| Core fluid-delivery testing | Controlled measurements of delivery and recovery behaviour for the selected use case | Continue, redesign or reject the fluid approach. |
| Hygiene and cleaning investigation | Evidence about preparation, cleaning burden and sanitation requirements | Determine whether maintenance erases the convenience benefit. |
| Initial manufacturing-cost modelling | Sourced estimates for major parts, processes and assembly assumptions | Test whether plausible product cost can overlap with customer value. |

These are planned evidence-generating activities, not completed results.

## Commercial uncertainty register

The commercial case is not treated as an assumed consequence of technical progress. The next stage should reduce the uncertainties below before the broader product vision is allowed to drive additional complexity.

| Commercial uncertainty | Current evidence | Next evidence | Venture decision |
| --- | --- | --- | --- |
| Is there a sufficiently important first problem? | Preliminary founder-reported feedback points most strongly to time and convenience, but the sample is small and non-conclusive. | Structured interviews centred on recent routine behaviour, recurring friction and existing workarounds. | Select, narrow or reject the first use case. |
| Does the device create net convenience? | Comfort, maintenance and price already appear as concerns; no physical workflow evidence exists. | Fit, preparation, loading, cleaning and storage observations alongside customer interviews. | Continue only if saved effort is not cancelled by ownership burden. |
| Can the first use case justify its product complexity? | Digital architecture exists, but no first-product scope has earned commercial validation. | Compare the minimum useful feature set with the physical mechanisms and servicing it requires. | Remove functions, simplify the architecture or reject an over-complex use case. |
| Can plausible manufacturing cost overlap with customer value? | No validated unit economics or willingness-to-pay evidence exists. | Sourced component, process and assembly assumptions plus customer pricing research. | Continue, reduce scope, change architecture or reconsider the business model. |
| When should the broader wearable-and-dock vision expand? | It remains a long-term direction rather than a validated first-product specification. | Customer, physical and cost evidence showing that another function adds enough value to justify added complexity. | Expand only after the narrower product case has earned support from evidence. |

This register is intentionally qualitative until sourced customer and manufacturing evidence exists. It does not assign invented market size, price, margin, conversion or revenue figures.

## Evidence-gated use of scholarship support

Support should be deployed in the order that reduces the largest uncertainty, not spread across every part of the long-term concept at once. No funding amount or outcome is assumed here.

| Support would be used for | When that spend becomes justified | Evidence it should produce | If the evidence is weak |
| --- | --- | --- | --- |
| Structured customer validation | Immediately, because the first use case is not yet locked. | Interview records showing whether a recurring routine problem is strong enough to justify focused development. | Narrow, change or reject the use case before spending heavily on hardware. |
| Prototype materials and test equipment | After a first-use-case hypothesis is strong enough to reduce to specific fit, workflow and fluid questions. | Measured observations from focused fit, delivery, recovery and cleaning tests. | Redesign the mechanism or stop that path rather than treating prototype activity as progress by itself. |
| Manufacturing and cost investigation | Once a candidate first-use-case architecture is defined well enough for credible process and assembly assumptions. | Sourced process, component and assembly inputs for an initial cost model. | Reduce scope, change the architecture or reconsider whether the product can create enough value for its complexity. |
| Specialist human collaboration | At decisions where practical expertise can materially challenge founder and AI-assisted assumptions. | External scrutiny of hardware, manufacturing, IP, fundraising and market-entry risks that cannot be resolved through repository work alone. | Record the challenged assumption and update the development path instead of preserving it for consistency with the original concept. |

This sequencing is intended to make scholarship support a force multiplier for evidence. It deliberately avoids treating a more complete-looking prototype, a larger feature set or a more polished presentation as proof of venture progress.

## How scholarship support would change the evidence base

Scholarship support would be most useful when converted into evidence rather than presentation work. Prototype materials and test equipment could support focused fit, fluid and cleaning experiments. Manufacturing and cost investigation could challenge process, assembly and unit-cost assumptions. Structured customer validation could test the first-use-case hypothesis more rigorously.

AI is used extensively to accelerate implementation, research, alternative generation and engineering exploration. Founder judgement owns product direction, requirements, trade-offs and final decisions. Specialist human expertise remains important for hardware, manufacturing, IP, fundraising and market entry, particularly where digital exploration cannot replace practical experience or measurement.

## Founder execution signal

The repository history shows a short, inspectable progression from controlled engineering foundations to whole-product integration work and then to an external-review evidence baseline. The dated milestones are recorded in the [verifiable repository chronology](EVIDENCE_GUIDE.md#verifiable-repository-chronology).

What matters for scholarship review is not commit volume. The stronger signal is the sequence of decisions and outputs: requirements and source authority were established, reproducible engineering source and automated checks were built, cross-subsystem conflicts were made explicit, and the venture record was then reorganised around customer, physical and commercial uncertainty rather than presenting the concept as finished.

AI has been used extensively throughout that process to accelerate implementation, research and exploration. The founder remains responsible for product direction, requirements, trade-offs and final decisions. The repository therefore demonstrates initiative through inspectable outputs and decision structure without implying that all implementation was produced manually or that digital progress is equivalent to physical product maturity.

## Current decision posture

The venture is far enough developed digitally to support targeted validation, but not far enough validated to justify claims of product readiness or proven demand. The next stage should therefore optimise for learning rate: reduce the largest customer, physical and commercial uncertainties before increasing product breadth.
