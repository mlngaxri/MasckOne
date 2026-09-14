# Masck One

Masck One is an early-stage consumer technology venture exploring hands-free automation of facial skincare through a wearable device and supporting dock.

The initial customer hypothesis is people who already follow multi-step skincare routines and would value spending less active time on repetitive steps. The product needs to save enough effort to justify wearing, preparing and maintaining it.

The long-term vision spans cleansing and selected leave-on products. The immediate validation goal is narrower: establish whether one clearly defined part of a routine can be automated comfortably and usefully before committing to a broader first product. This is a staged validation approach; it does not mean the complete-routine engineering requirements have been met or waived.

<p align="center">
  <img src="website/images/masck-inspection-front-3q-v17c.webp" alt="Masck One digital concept render, front three-quarter view" width="48%" />
  <img src="website/images/masck-inspection-rear-3q-v17c.webp" alt="Masck One digital concept render, rear three-quarter view" width="48%" />
</p>

*Existing digital concept renders used to communicate product direction. They are not photographs of manufactured hardware and should not be read as proof of physical performance.*

## At a glance

| Area | Current position |
| --- | --- |
| **Stage** | Pre-commercialisation. Engineering CAD and software exist; an integrated manufactured product does not. |
| **Initial development** | The founder reports building the initial digital foundation over roughly two weeks in September 2026. |
| **What is inspectable here** | Code-generated parametric CAD, requirements, automated engineering checks, design records and subsystem exploration. |
| **Evidence boundary** | Digital work can support design decisions, but it does not prove customer demand, comfort, safety, hygiene, manufacturability or product performance. |
| **Controlled engineering baseline** | **Phase 5: waste acquisition and containment - Iteration 28 complete.** This is a repository roadmap state, not whole-product readiness. |

## Digital development

The merged baseline covers facial-reference and interface geometry, protected anatomical regions, structural and actuation references, fresh-water and cleanser routing, waste-handling architecture and deterministic CAD export. The [engineering authority](config/masck_one_authority.yaml) and [development roadmap](docs/DEVELOPMENT_ROADMAP.md) define that baseline.

The repository also contains system requirements, automated checks, analytical models and simulation frameworks. These support decisions and expose assumptions; integrated physical performance has not been established. Current CAD is code-generated engineering geometry, not a finished manufactured product.

## Customer learning

The founder reports an informal survey of around 20 people. Feedback highlighted time savings and convenience, alongside concerns about comfort, maintenance and price. This is an early qualitative signal, not established demand or willingness to pay. The [customer discovery notes](docs/CUSTOMER_DISCOVERY.md) separate that reported feedback from the structured research still needed.

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

I use AI extensively to generate and iterate code-based CAD, develop software, compare alternatives, organise research, draft checks and identify potential failure modes. I review and integrate that work against product requirements, system constraints and evidence standards. Version control and automated checks make the process inspectable; specialist judgement and physical measurement remain necessary where digital work cannot answer a question.

This is an independently initiated, founder-led project. AI outputs are not treated as physical evidence, unknown results stay unknown, and a passing software check does not turn a target into achieved product performance.

## Limitations: what is not proven yet

The repository does **not** currently prove:

- Customer demand or willingness to pay.
- Comfort or population fit.
- Hygiene, cleaning or maintenance practicality.
- Real fluid behaviour, delivery, leakage or recovery performance.
- Product safety.
- Manufacturing feasibility or production capability.
- Unit economics or a viable commercial model.

The [evidence guide](docs/EVIDENCE_GUIDE.md) explains which records can support each kind of claim.

## Next validation steps

The next work should turn the most important assumptions into evidence:

| Priority | Question to resolve |
| --- | --- |
| Structured customer interviews | Which recurring task is worth automating, and what would make someone change their routine? |
| Focused analysis and fit prototype | Which geometry and comfort assumptions need measurement and specialist review? |
| Core fluid-delivery feasibility | Can a selected mechanism perform its intended function under appropriate controlled testing? |
| Hygiene and maintenance investigation | Would preparation and cleaning erase the convenience benefit? |
| Initial manufacturing-cost model | Could a practical first product support a price and margin consistent with customer value? |

These are planned activities, not completed results. The [customer discovery notes](docs/CUSTOMER_DISCOVERY.md) define the commercial questions, and the [engineering work queue](docs/CORE_SKETCH_START_HERE.md) retains the technical dependencies and acceptance gates. Evidence from both should determine the initial use case and which features justify their complexity.

## Inspect the work

Use the [documentation index](docs/README.md) for a guided reading path, the [evidence guide](docs/EVIDENCE_GUIDE.md) to interpret results, and the [engineering quickstart](docs/ENGINEERING_QUICKSTART.md) to reproduce the work. [Open pull requests](https://github.com/mlngaxri/MasckOne/pulls) contain candidate work, which may differ from the merged baseline.

## Repository structure

| Location | Contents |
| --- | --- |
| [config/](config/) and [schemas/](schemas/) | Engineering authorities and validation contracts |
| [src/masck_one/](src/masck_one/) and [tests/](tests/) | Engineering logic, CAD generation and automated checks |
| [docs/](docs/) and [studies/](studies/) | Design rationale, development history and bounded investigations |
| [website/](website/) and [brand/](brand/) | Digital presentation and identity work, not physical-product evidence |
| [generated/](generated/) | Reproducible generated outputs, not independent authority |

See the [repository map](docs/REPOSITORY_STRUCTURE.md) for source precedence and retained development tooling.
