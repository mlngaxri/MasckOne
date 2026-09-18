# Masck One

Masck One is an early-stage hands-free facial-skincare wearable for people who already follow multi-step routines, exploring whether repetitive skincare steps can be automated to reduce the active time and effort those routines require.

**Current stage:** pre-commercialisation. Engineering geometry exists and digital checks and validation frameworks exist, but product-level physical validation has not begun. There is no integrated manufactured product, and the core customer, physical-performance and commercial assumptions remain to be validated.

**Reviewer baseline:** the live engineering baseline is `main` at `8d37bc322b5ebe42179685a1a0559f2fcb1b5f22` (16 September 2026). This scholarship-review branch organises public evidence and venture context around that engineering record; later documentation commits on this branch are not newer engineering releases and do not inherit physical or CI qualification from earlier revisions.

**90-second scholarship-review path:** start with the [scholarship reviewer path](docs/SCHOLARSHIP_REVIEWER_PATH.md). It gives a non-technical panel a short route through the venture position, verifiable execution, preliminary customer evidence, next evidence sequence, scholarship use and current evidence boundary. The [one-page venture snapshot](docs/VENTURE_SNAPSHOT.md) provides the fuller venture view, while the [scholarship review snapshot](docs/SCHOLARSHIP_REVIEW_SNAPSHOT.md) maps the strongest claims to representative sources and checks. For visual inspection, use the [visual evidence quicklook](docs/VISUAL_EVIDENCE_QUICKLOOK.md); use the [scholarship evidence matrix](docs/SCHOLARSHIP_EVIDENCE_MATRIX.md) and [evidence guide](docs/EVIDENCE_GUIDE.md) only for deeper audit.

The long-term vision spans cleansing and selected leave-on products. The immediate validation goal is narrower: establish whether one clearly defined part of a routine can be automated comfortably and usefully before committing to a broader first product. This is a staged validation approach; it does not mean the complete-routine engineering requirements have been met or waived.

[![Masck One documented whole-product architecture](docs/assets/scholarship-system-overview.svg)](docs/assets/scholarship-system-overview.svg)

*Documentation map of whole-product architecture. It summarises subsystem relationships already documented in the repository so a reviewer can understand the system quickly. It does not show implementation status, validated material or control flow, an integrated prototype, or physical validation. Click the diagram to inspect it at full size, then open the [visual evidence quicklook](docs/VISUAL_EVIDENCE_QUICKLOOK.md) for representative registered digital compositions, provenance and explicit evidence limits.*

## Venture snapshot

| Reviewer question | Current answer |
| --- | --- |
| **Problem being explored** | Multi-step facial-skincare routines can require repetitive active time, handling and clean-up. Masck One explores whether part of that work can be automated without creating a worse maintenance burden. |
| **Target user** | People who already follow multi-step facial-skincare routines and value reducing active routine time and effort. |
| **First use case to validate** | One clearly defined routine step that can be tested for usefulness, fit, fluid handling and maintenance burden before committing to the broader wearable-and-dock vision. The specific first step is not yet locked; structured customer evidence should determine it. |
| **What has been built** | Code-generated parametric CAD, system requirements, automated engineering check source, design records and linked subsystem exploration across fit, fluid handling, retention, waste capture, electronics and controls. The check source is inspectable framework evidence, not a recorded CI pass for the current engineering revision. |
| **Early customer learning** | An informal survey of around 20 people reportedly showed strongest interest around time savings and convenience, with concerns around comfort, maintenance and price. This is preliminary and non-conclusive, not evidence of demand or willingness to pay. |
| **Key uncertainties** | Customer value, comfort and population fit, hygiene and cleaning burden, real fluid behaviour, safety, manufacturability, unit economics and the most defensible first use case. |
| **Next evidence milestones** | Structured customer interviews, focused analysis, a physical fit prototype, core fluid-delivery testing, hygiene and cleaning investigation, and an initial manufacturing-cost model. |
| **Current stage** | Pre-commercialisation. Engineering geometry and digital checks/frameworks exist; product-level physical validation has not begun and there is no integrated manufactured product. |
| **Initial development** | The founder reports establishing the initial digital foundation over roughly two weeks in September 2026, using AI extensively to accelerate implementation and exploration. |
| **Controlled engineering baseline** | **Phase 5: waste acquisition and containment - Iteration 28 complete.** This is a repository roadmap state, not whole-product readiness. |

## Initial founder execution

Over roughly two weeks, I established the initial digital engineering foundation for Masck One: defining the intended product direction, requirements, constraints and trade-offs while using AI extensively to accelerate code-generated parametric CAD, software implementation, research, alternative generation and engineering checks.

The resulting repository contains system requirements, automated engineering check source, documented design decisions and linked technical exploration across fit, fluid handling, retention, waste capture, electronics and controls. The check source demonstrates an inspectable checking framework; it does not establish a recorded CI pass for the current engineering revision. This chronology demonstrates founder initiative and decision ownership; it does not imply that every implementation artefact was authored manually or independently of AI assistance.

The merged baseline includes facial-reference and interface geometry, protected anatomical regions, structural and actuation references, fresh-water and cleanser routing, waste-handling architecture and deterministic CAD export. The [engineering authority](config/masck_one_authority.yaml) and [development roadmap](docs/DEVELOPMENT_ROADMAP.md) define that controlled baseline.

The repository also contains analytical models and simulation frameworks used to test assumptions and expose conflicts before physical prototyping. These are engineering tools, not physical validation. Current CAD is code-generated engineering geometry, not a finished manufactured product.

## Customer learning

The founder reports an informal survey of around 20 people. Feedback highlighted time savings and convenience, alongside concerns about comfort, maintenance and price. This is an early qualitative signal, not established demand or willingness to pay. The [customer discovery notes](docs/CUSTOMER_DISCOVERY.md) separate that reported feedback from the structured research still needed.

## Commercial questions being tested

The commercial case is deliberately being treated as a set of hypotheses rather than as a proven market opportunity.

| Question | Why it matters | Evidence still needed |
| --- | --- | --- |
| Which routine step creates enough frustration or repetitive effort to justify automation? | This determines whether there is a narrow first product worth building before attempting the broader wearable-and-dock vision. | Structured interviews and observation of real routines. |
| Does saved active time outweigh fitting, loading, cleaning and maintenance effort? | Convenience only matters if the system removes more friction than it introduces. | Customer research plus focused physical workflow testing. |
| What comfort and maintenance burden will users accept? | The strongest preliminary concerns already include comfort and maintenance. | Physical fit work, cleaning investigation and structured interviews. |
| What price could be justified by the value created? | A technically interesting product is not commercially useful if customer value and manufacturing cost cannot support the same price range. | Willingness-to-pay research and an initial manufacturing-cost model. |
| Which functions belong in a first product, and which should remain part of the longer-term vision? | Limiting scope can reduce technical risk, cost and servicing burden while producing clearer evidence sooner. | Combined customer, engineering and cost evidence. |

No answer in this table is treated as resolved. The near-term goal is to identify a first use case where customer value, physical feasibility and plausible economics overlap, then decide whether broader automation deserves further development.

## System being explored

| System | Intended role |
| --- | --- |
| Facial interface and treatment mechanics | Position the wearable and control where contact occurs |
| Product storage and delivery | Keep products separate and deliver them in the required sequence |
| Waste recovery and cartridges | Capture used liquid and support practical servicing |
| Retention, structure and removal | Support the wearable and allow controlled removal |
| Electronics, controls and software | Coordinate device states, routines and supported product information |
| Dock and preparation | Support charging, loading, cleaning and session preparation |

The main engineering challenge is integration. A decision that helps one subsystem can create a problem elsewhere, so the architecture is treated as a whole product rather than a collection of independent features. The broader intent and unresolved conflicts are documented in the [product concept](docs/PRODUCT_CONCEPT.md) and [convergence review](docs/CORE_SKETCH_CONVERGENCE_REVIEW.md).

## Founder role and AI-assisted development

I direct the product and system architecture: defining the intended experience, requirements and constraints; breaking the work into problems; setting priorities; comparing approaches; resolving trade-offs; and deciding what the available evidence actually supports.

I use AI extensively to accelerate code-based CAD, software development, research, alternative generation and engineering checks. I set the direction, requirements and trade-offs, and make the final system-level decisions. Version control and automated checks make the work inspectable; specialist judgement and physical measurement remain necessary where digital work cannot answer a question.

This is an independently initiated, founder-led project. AI outputs are not treated as physical evidence, unknown results stay unknown, and a passing software check does not turn a target into achieved product performance.
