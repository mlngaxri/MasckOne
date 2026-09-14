# Masck One

**Masck One is an early-stage wearable-and-dock system for people who use skincare routines and want to reduce repetitive manual steps; it explores whether a comfortable hands-free device can automate part of that routine without making preparation, cleaning or maintenance worse.**

The long-term vision is a system that can support more of a skincare routine, from cleansing through selected leave-on products. The first use case I need to prove is narrower: whether a comfortable wearable can automate one defined part of skincare reliably enough to justify further development.

<p align="center">
  <img src="website/images/masck-inspection-front-3q-v17c.webp" alt="Masck One digital concept render, front three-quarter view" width="48%" />
  <img src="website/images/masck-inspection-rear-3q-v17c.webp" alt="Masck One digital concept render, rear three-quarter view" width="48%" />
</p>

*Existing digital concept renders used to communicate product direction. They are not photographs of manufactured hardware and should not be read as proof of physical performance.*

## Reviewer snapshot

| | |
| --- | --- |
| **Stage** | Pre-commercialisation. Engineering CAD and software exist; an integrated manufactured product does not. |
| **Development window** | Two-week founder-led engineering sprint to date. |
| **What is inspectable here** | Code-generated parametric CAD, requirements, automated engineering checks, design records and subsystem exploration. |
| **Evidence boundary** | Digital work can support design decisions, but it does not prove customer demand, comfort, safety, hygiene, manufacturability or product performance. |
| **Controlled engineering baseline** | **Phase 5: waste acquisition and containment - Iteration 28 complete.** This is a repository roadmap state, not whole-product readiness. |

## Current stage

Masck One is pre-commercialisation. The CAD in this repository is engineering geometry generated and checked in code. It is not a finished industrial design, and there is currently no integrated manufactured Masck One product.

Physical validation has not yet begun. The repository contains analytical and digital engineering checks, but those checks are not substitutes for fit testing, fluid testing, hygiene work, safety review or manufacturing evidence.

The merged baseline currently covers facial-reference and interface geometry, protected anatomical regions, structural and actuation references, fresh-water and cleanser routing, waste-handling architecture and deterministic CAD export. The [engineering authority](config/masck_one_authority.yaml) and [development roadmap](docs/DEVELOPMENT_ROADMAP.md) define the controlled baseline.

## What I built in two weeks

- Code-generated parametric CAD.
- System requirements and machine-readable engineering constraints.
- Automated engineering checks and regression tests.
- Documented design decisions and evidence boundaries.
- Technical exploration across fit, fluid handling, retention, waste capture, electronics and controls.

The purpose of this work was not to make the project look finished. It was to turn an idea into something structured enough to inspect, challenge and test.

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

AI is used extensively for engineering analysis, software, programmatic CAD, research, design exploration, testing and documentation. I do not present every technical detail as manually authored. I use AI as an execution multiplier, then review and integrate the work against product requirements, system constraints and evidence standards. Version control, requirements, automated checks and review make that process inspectable.

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

These are open questions, not claims hidden elsewhere in the repository.

## Next validation steps

The next work should convert the most important assumptions into evidence:

1. Structured customer interviews.
2. Simulation where it can meaningfully reduce uncertainty.
3. A focused physical fit prototype.
4. Core fluid-delivery testing.
5. Hygiene and cleaning investigation.
6. An initial manufacturing-cost model.

The immediate objective is not to add more features. It is to find out whether the venture is desirable, technically feasible and commercially worth developing further.

## How to assess the work quickly

| Question | Best place to look |
| --- | --- |
| What is Masck One trying to become? | [Product concept](docs/PRODUCT_CONCEPT.md) |
| What is actually part of the merged engineering baseline? | [Engineering authority](config/masck_one_authority.yaml) and [roadmap](docs/DEVELOPMENT_ROADMAP.md) |
| What engineering logic has been implemented? | [`src/masck_one/`](src/masck_one/) |
| What is checked automatically? | [`tests/`](tests/) and the [CI workflow](.github/workflows/ci.yml) |
| How should digital evidence be interpreted? | [Evidence guide](docs/EVIDENCE_GUIDE.md) |
| What candidate work is still being reviewed? | [Open pull requests](https://github.com/mlngaxri/MasckOne/pulls) |
| How is the repository organised? | [Documentation index](docs/README.md) and [repository map](docs/REPOSITORY_STRUCTURE.md) |

Candidate branches, green software tests, generated renders and physical measurements are different forms of evidence. The [evidence guide](docs/EVIDENCE_GUIDE.md) explains those boundaries so reviewers do not have to infer them.

## Repository structure

| Location | Contents |
| --- | --- |
| [config/](config/) and [schemas/](schemas/) | Engineering authorities and validation contracts |
| [src/masck_one/](src/masck_one/) and [tests/](tests/) | Engineering logic, CAD generation and automated checks |
| [docs/](docs/) and [studies/](studies/) | Design rationale, development history and bounded investigations |
| [website/](website/) and [brand/](brand/) | Digital presentation and identity work, not physical-product evidence |
| [generated/](generated/) | Reproducible generated outputs, not independent authority |

For technical reproduction, use the [engineering quickstart](docs/ENGINEERING_QUICKSTART.md). For a non-technical review, the sections above are intended to be sufficient.
