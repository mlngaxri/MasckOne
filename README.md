# Masck One

Masck One is an early-stage consumer technology venture developing a hands-free automated facial-skincare wearable and supporting dock. The aim is to complete a supported skincare routine, from cleansing to leave-on application, with less manual work.

Skincare routines can involve several products, repeated application and time at a sink or mirror. The product thesis is that automating one step leaves much of that effort intact. Masck One explores whether an integrated wearable can handle the sequence while keeping preparation, cleaning and maintenance practical. Whether that delivers enough value for people to adopt it remains a customer-validation question.

This repository contains engineering code, parametric CAD, requirements, automated checks and design records. Masck One is **pre-commercialisation: digital development is underway; an integrated, physically validated product has not been demonstrated.**

## The product being developed

The intended experience is to prepare the device at its dock, put it on, run a selected routine and remove it without needing to finish the supported facial routine by hand. Compatibility with a useful range of existing skincare products is a design goal, not an established capability.

| System | Intended role |
| --- | --- |
| Facial interface and treatment mechanics | Position the device and control where contact occurs |
| Product storage and delivery | Keep products separate and deliver them in the required sequence |
| Waste recovery and cartridges | Capture used liquid and support practical servicing |
| Retention, structure and removal | Support the wearable and allow controlled removal without wiping off the final application |
| Electronics, controls and software | Coordinate device states, routines and supported product information |
| Dock and preparation | Support charging, loading, cleaning and session preparation |

The difficult part is making these systems work together. A seal that helps liquid recovery may obstruct application; a support that improves fit may disturb a leave-on layer during removal. Those conflicts shape the architecture. The [product concept](docs/PRODUCT_CONCEPT.md) and [convergence review](docs/CORE_SKETCH_CONVERGENCE_REVIEW.md) record the broader intent and unresolved feasibility questions.

## What exists today

The merged engineering baseline includes parametric facial-reference and interface geometry, protected anatomical regions, structural and actuation references, fresh-water and cleanser paths, waste-handling architecture, and deterministic CAD export. Source code, machine-readable requirements and regression checks make these digital decisions inspectable and reproducible.

Its controlled roadmap position is **Phase 5: waste acquisition and containment - Iteration 28 complete.** This describes the engineering baseline in [the authority](config/masck_one_authority.yaml) and [development roadmap](docs/DEVELOPMENT_ROADMAP.md). It does not mean the complete skincare product is built or physically validated. The broader routine concept extends beyond that baseline.

Further subsystem work and proof tooling are under review in [open pull requests](https://github.com/mlngaxri/MasckOne/pulls). A candidate branch, a passing software check and a measured physical result are different forms of evidence. The [evidence guide](docs/EVIDENCE_GUIDE.md) explains how to inspect each without confusing their scope.

Physical fit, comfort, liquid containment, application coverage, product compatibility, hygiene, removal behaviour and safety remain validation questions. Digital geometry cannot establish those results. Manufacturing capability, cost and customer demand also remain to be established.

## Founder role and AI-assisted development

The founder directs the product and system architecture: defining the intended experience, requirements and constraints; decomposing the work; setting priorities; comparing approaches; and resolving trade-offs across disciplines. That includes rejecting a locally attractive solution when it harms the overall product, and deciding when another digital iteration cannot answer a question that needs measurement.

AI is used extensively for engineering analysis, software, programmatic CAD, research, design exploration, testing and documentation. This is not a claim that every technical detail was manually engineered by the founder. The founder's responsibility is to direct, question and integrate that work, preserve the design intent and judge what the available evidence supports.

Requirements, version control, automated checks and review make the development traceable. AI outputs are not physical evidence. Unknown results stay unknown, reference geometry remains distinct from manufactured material, and tests do not turn targets into achieved performance.

## Next milestones

The immediate engineering priority is to test the assumptions that determine whether a complete routine is feasible: coverage, separation between stages, preservation of the final application and removal. The [current engineering work queue](docs/CORE_SKETCH_START_HERE.md) links the proof gates, dependencies and integration work.

Alongside that work, the venture needs customer discovery about routine effort, willingness to wear the device and acceptable maintenance; product and manufacturing advice; and a credible cost and commercialisation path. These are upcoming activities, not traction claims. What is learned should determine which features progress and which assumptions need to change. Dates in planning documents are targets, not evidence of readiness.

## Explore the repository

Start with the [documentation index](docs/README.md), use the [evidence guide](docs/EVIDENCE_GUIDE.md) to inspect the work, or follow the [engineering quickstart](docs/ENGINEERING_QUICKSTART.md) to reproduce it with the controlled Python/CadQuery environment.

| Location | Contents |
| --- | --- |
| [config/](config/) and [schemas/](schemas/) | Engineering authorities and validation contracts |
| [src/masck_one/](src/masck_one/) and [tests/](tests/) | Engineering logic, CAD generation and automated checks |
| [generated/](generated/) | Generated engineering outputs, not independent authority |
| [docs/](docs/) and [studies/](studies/) | Design rationale, development history and bounded investigations |
| [website/](website/) and [brand/](brand/) | Digital presentation and identity work, not physical-product evidence |

The [repository map](docs/REPOSITORY_STRUCTURE.md) explains source precedence and retained development tooling. Technical collaboration should start from the relevant requirements and evidence gaps; the repository is not a set of instructions for unvalidated human use.
