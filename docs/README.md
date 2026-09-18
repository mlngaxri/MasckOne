# Masck One documentation

This directory contains the engineering rationale, subsystem specifications, validation rules and development records behind the source code and generated CAD.

If you are reviewing the venture rather than reproducing the engineering work, start with the [project README](../README.md). It summarises the problem, current stage, digital development, limitations and next validation steps without requiring you to read the internal engineering record.

The repository separates three kinds of information:

1. **Engineering authority**: machine-readable parameters and contracts that control generation and validation.
2. **Design documentation**: rationale, interfaces, constraints and current subsystem decisions.
3. **Development evidence**: studies, validation records and bounded investigations that support decisions without being promoted beyond their evidence.

## Choose a reading path

| What you want to understand | Start here |
| --- | --- |
| The product, my role, progress and present stage | [Project overview](../README.md) |
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
