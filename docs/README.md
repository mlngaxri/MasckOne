# Masck One documentation

This directory contains the engineering rationale, subsystem specifications, validation rules and development records behind the source code and generated CAD.

**Current stage:** pre-commercialisation. Engineering geometry exists and digital checks and validation frameworks exist, but product-level physical validation has not begun. There is no integrated manufactured product, and the core customer, physical-performance and commercial assumptions remain to be validated.

**Scholarship reviewer entry:** start with the [one-page scholarship review snapshot](SCHOLARSHIP_REVIEW_SNAPSHOT.md). It is the single canonical reviewer-facing evidence page: its 60-second evidence map links directly to representative parametric CAD, controlled requirements, automated checks, documented trade-offs and subsystem evidence, while keeping planned validation and unproven physical/commercial claims separate. The [scholarship evidence matrix](SCHOLARSHIP_EVIDENCE_MATRIX.md) is a supporting audit for reviewers who want more claim-by-claim detail, not a second canonical entry point. Use the [evidence guide](EVIDENCE_GUIDE.md) only where a claim needs deeper engineering inspection. This keeps the primary path shallow: README → snapshot → representative source/check.

**Reviewer source precedence:** when a scholarship summary and an engineering-owner source differ, the engineering-owner source at the revision cited by the snapshot wins. Scholarship pages organise and explain evidence; they do not create engineering authority, promote an evidence state, or qualify a later revision. A reviewer should therefore treat the pinned source/check behind a claim as the auditable record and the surrounding scholarship text as a bounded summary of that record.

**Three fast requirement spot-checks:** the [engineering authority at the audited engineering baseline](https://github.com/mlngaxri/MasckOne/blob/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22/config/masck_one_authority.yaml) defines duplicated nostril/airway opening requirements, a clean-cycle fluid ledger and a minimum waste-cartridge capacity; the paired [authority contract tests at the same revision](https://github.com/mlngaxri/MasckOne/blob/8d37bc322b5ebe42179685a1a0559f2fcb1b5f22/tests/test_authority_contract.py) deliberately perturb each of those inputs and require the repository to reject the resulting mismatch. This demonstrates fail-closed consistency checking, not measured airway, fluid or cartridge performance. It can show that controlled values and dependent sources agree; it cannot establish that those values are correct, safe or effective for human use. Requirements marked `VALIDATION_GATED` remain unproven until qualifying physical evidence exists.

**Planned validation is separately inspectable:** the [reduced-region proof package](CORE_SKETCH_REDUCED_REGION_PROOF_PACKAGE.md) and [status board](CORE_SKETCH_STATUS_BOARD.md) show bounded proof work and unresolved gates. A protocol, fixture concept or validation gate is evidence of planning only; it is not a completed experiment and must not be read as physical performance.

**Subsystem coverage is not subsystem validation:** the repository contains linked digital work across facial interface, structure/retention, actuation, fluid/waste handling, controls and dock/service concepts, but coverage is uneven and several interactions remain explicitly unresolved. A subsystem appearing in a concept, requirement, CAD model, analysis framework or convergence record means that the dependency is inspectable; it does not mean that subsystem is complete, integrated, physically demonstrated or equally mature. The [whole-product convergence review](CORE_SKETCH_CONVERGENCE_REVIEW.md) is the appropriate source for those cross-subsystem conflicts and proof priorities.

**Reviewer claim guardrail:** the repository supports statements such as “parametric engineering geometry exists”, “requirements are controlled”, “automated digital check source exists” and “physical validation is planned”. It does not support a claim that current `main` has a recorded CI pass unless a workflow result is associated with that exact revision. It also does not support statements such as “working product”, “validated fit”, “proven cleansing or fluid performance”, “safe for human use”, “manufacturing-ready” or “commercially validated”. Customer demand, comfort, hygiene/cleaning, real fluid behaviour, safety, manufacturing feasibility, unit economics and product-level physical performance remain unproven.

If you are reviewing the venture rather than reproducing the engineering work, start with the [project README](../README.md). It summarises the problem, current stage, digital development, limitations and next validation steps without requiring you to read the internal engineering record.

The repository separates three kinds of information:

1. **Engineering authority**: machine-readable parameters and contracts that control generation and validation.
2. **Design documentation**: rationale, interfaces, constraints and current subsystem decisions.
3. **Development evidence**: studies, validation records and bounded investigations that support decisions without being promoted beyond their evidence.

## Choose a reading path

| What you want to understand | Start here |
| --- | --- |
| Scholarship review: strongest claims, evidence classes and limitations in one page | [Scholarship review snapshot](SCHOLARSHIP_REVIEW_SNAPSHOT.md) |
| The product, founder role, progress and present stage | [Project overview](../README.md) |
| The strongest existing visuals and what they do or do not prove | [Visual evidence index](VISUAL_EVIDENCE_INDEX.md) |
| Initial customer, reported feedback and next research questions | [Customer discovery](CUSTOMER_DISCOVERY.md) |
| What the repository actually demonstrates | [Evidence guide](EVIDENCE_GUIDE.md) |
| How to run the engineering work | [Engineering quickstart](ENGINEERING_QUICKSTART.md) |
| Where files belong and which source takes precedence | [Repository map](REPOSITORY_STRUCTURE.md) |
| What to work on next | [Current engineering work queue](CORE_SKETCH_START_HERE.md) |

The controlled iteration roadmap describes the merged engineering baseline. The broader product concept and open subsystem proposals are not claims of completed hardware.

## Product and program

- [`DEVELOPMENT_ROADMAP.md`](DEVELOPMENT_ROADMAP.md): controlled development sequence and completed iterations
- [`CORE_SKETCH_START_HERE.md`](CORE_SKETCH_START_HERE.md): entry point for the current whole-product concept
- [`PRODUCT_CONCEPT.md`](PRODUCT_CONCEPT.md): product-intent evolution and broader design thesis
- [`BRAND_ARCHITECTURE.md`](BRAND_ARCHITECTURE.md): product naming and identity structure
- [`DIGITAL_PRODUCT_VISION.md`](DIGITAL_PRODUCT_VISION.md): companion app, website and connected-product direction

## Engineering governance

- [`ENGINEERING_GOVERNANCE.md`](ENGINEERING_GOVERNANCE.md): change control and evidence boundaries
- [`REPOSITORY_STRUCTURE.md`](REPOSITORY_STRUCTURE.md): source hierarchy and ownership
- [`COORDINATE_SYSTEM.md`](COORDINATE_SYSTEM.md): canonical coordinate conventions
- [`PROCESS_CAPABILITY.md`](PROCESS_CAPABILITY.md): manufacturing capability assumptions and limits
- [`MOLDABILITY.md`](MOLDABILITY.md): moldability and part-split considerations
- [`COST_PRESSURE.md`](COST_PRESSURE.md): cost-sensitive engineering decisions

## Facial interface and safety

- [`FACIAL_REFERENCE.md`](FACIAL_REFERENCE.md): facial reference model
- [`REFERENCE_SURFACE_INGESTION.md`](REFERENCE_SURFACE_INGESTION.md): external reference-geometry ingestion
- [`WORN_POSE.md`](WORN_POSE.md): worn-pose and misregistration screening
- [`COVERAGE_MESH.md`](COVERAGE_MESH.md): target-region and protected-area accounting
- [`COMPLIANT_INTERFACE_TOPOLOGY.md`](COMPLIANT_INTERFACE_TOPOLOGY.md): facial-interface topology
- [`NASAL_SUBSYSTEM.md`](NASAL_SUBSYSTEM.md): nasal interface partition and constraints
- [`AIRWAY_RESISTANCE.md`](AIRWAY_RESISTANCE.md): airway-related requirements and evidence limits
- [`CONTACT_SIMULATION_FRAMEWORK.md`](CONTACT_SIMULATION_FRAMEWORK.md): contact-analysis framework

## Mechanical and product architecture

- [`STRUCTURAL_FRAME_TOPOLOGY.md`](STRUCTURAL_FRAME_TOPOLOGY.md): current structural-frame architecture
- [`MASS_BALANCE.md`](MASS_BALANCE.md): mass, centre-of-gravity and torque governance
- [`ROUTINE_COMPLETION.md`](ROUTINE_COMPLETION.md): rules for reporting treatment-stage completion
- [`CLEANSING_PLAN_COMPILER.md`](CLEANSING_PLAN_COMPILER.md): treatment-plan reachability and hardware-footprint constraints

## Reading the evidence correctly

A document may describe a selected architecture without proving physical performance. Terms such as `BLOCKED`, `VALIDATION_GATED`, `REFERENCE_ONLY` and similar evidence states are intentional. They distinguish digital closure from physical validation.

Where a physical property has not been measured, the documentation should not be read as a claim that the product already achieves it.

## Development workflow

The project uses AI-assisted engineering workflows alongside source control, testing and explicit engineering contracts. AI-generated analysis or implementation is not treated as authority by default. Product requirements, system architecture, acceptance criteria, integration decisions and evidence promotion remain subject to project-level review.

Some internal documents retain workflow-specific terminology because they support reproducibility and source provenance. They should be read as development infrastructure, not as product claims or marketing material.
