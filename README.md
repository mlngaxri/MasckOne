# Masck One

Masck One is an early-stage consumer technology project developing a hands-free automated facial-cleansing wearable.

The product brings together mechanical design, compliant facial contact, fluid delivery, waste capture, actuation, electronics, controls and product software. The aim is to make a repetitive skincare step more consistent and convenient while keeping safety-critical assumptions explicit and testable.

This repository contains the project's engineering code, parametric CAD, system requirements, validation tooling, development studies and supporting digital product work.

> **Development status:** pre-commercialisation and pre-production. Digital engineering is advanced, but physical fit, cleansing performance, comfort, durability, safety, manufacturability and production readiness remain subject to physical validation.

## Current program position

**Phase 5: waste acquisition and containment - Iteration 28 complete.**

The authoritative program state is stored in [`config/masck_one_authority.yaml`](config/masck_one_authority.yaml). The development roadmap and repository checks are tied to that source so the documented status cannot silently drift from the engineering state.

The current released baseline includes deterministic development geometry and verification infrastructure for:

- facial reference geometry and protected eye, mouth and airway regions
- a compliant facial-interface architecture
- four-zone actuation packaging and motion references
- fresh-water and cleanser storage and distribution architecture
- mixed-waste acquisition, pumping and cartridge handling
- subsystem reservations, source binding and collision checks
- deterministic STEP export and generated engineering manifests

These are engineering development artifacts, not claims of validated physical performance.

## Product concept

Masck One is being developed as a wearable system that can perform facial-cleansing steps without requiring the user to manually wash and rinse their face throughout the cycle.

The current product architecture is organised around six interacting systems:

| System | Role |
| --- | --- |
| Facial interface | Creates a controlled contact boundary while protecting sensitive regions and openings |
| Treatment mechanics | Provides controlled local motion across defined facial zones |
| Fresh-fluid system | Stores, meters and distributes water and cleanser |
| Waste system | Acquires used fluid and contaminants and transfers them to a removable cartridge |
| Retention and structure | Supports the wearable, maintains alignment and provides a defined removal path |
| Controls and electronics | Coordinates user input, actuation, fluid handling and future sensing capabilities |

The product is intentionally being developed as a whole system. A locally good component is not accepted if it creates a worse fit, service, safety, packaging or user-experience outcome elsewhere.

## Engineering approach

The repository is built around a simple rule: digitally checkable facts and physically validated facts are not the same thing.

Geometry, source provenance, configuration consistency, collision conditions and many interface constraints can be checked deterministically in software. Fit, comfort, tactile quality, leakage, cleansing efficacy, structural durability and human-use performance require physical evidence.

Where physical evidence does not yet exist, the repository records that state explicitly rather than turning an engineering target into an achieved claim.

This approach is reflected in the project's configuration authority, tests, preflight checks and generated reports.

## AI-assisted development

AI tools are used extensively in the development workflow to accelerate engineering analysis, coding, documentation, design iteration and research.

The project remains founder-directed. Product requirements, system architecture, priorities, user-experience decisions, acceptance criteria, trade-offs and final integration decisions are set and reviewed at the product level. AI is used as a technical multiplier across specialised work rather than as an autonomous source of product authority.

That distinction matters for a multidisciplinary hardware project. Individual outputs are useful only if they fit the wider system, preserve the intended user experience and remain consistent with the project's evidence and safety boundaries. Source control, tests and explicit engineering contracts are used to make that review process repeatable.

## Repository structure

| Path | Purpose |
| --- | --- |
| [`config/`](config/) | Engineering and product configuration authorities |
| [`schemas/`](schemas/) | Machine-readable validation contracts |
| [`src/masck_one/`](src/masck_one/) | Engineering logic, CAD generation and release tooling |
| [`tests/`](tests/) | Regression, provenance, geometry and integrity checks |
| [`studies/`](studies/) | Engineering studies and bounded design investigations |
| [`docs/`](docs/) | Design rationale, subsystem documentation and development records |
| [`generated/`](generated/) | Deterministic generated engineering outputs |
| [`website/`](website/) | Current public-facing digital product work |
| [`brand/`](brand/) | Product identity and brand assets |

For a guided documentation entry point, see [`docs/README.md`](docs/README.md).

## Engineering authority

The primary machine-readable source is:

```text
config/masck_one_authority.yaml
```

Its schema is:

```text
schemas/masck_one_authority.schema.json
```

The repository also contains a separate brand and product-identity contract. Brand intent does not override engineering authority or validation state.

Key principles include:

- one controlled source for engineering parameters
- reproducible CAD generation from source
- explicit separation between manufactured material and reference geometry
- protected anatomy treated as a hard design constraint
- validation-gated requirements remain open until evidence closes them
- generated STEP files are outputs, not the source of engineering truth
- source movement and stale provenance fail closed where relevant

## Key technical areas

The codebase covers a broader system than a conventional CAD repository. Representative modules include:

- `spatial.py`: canonical coordinates, points, vectors and rigid transforms
- `anatomy.py`: semantic facial landmarks and references
- `protected_volumes.py`: eye, mouth and airway exclusion geometry
- `worn_pose.py`: misregistration and worn-pose screening
- `coverage.py`: treatment-region and protected-area accounting
- `interface_topology.py`: compliant facial-interface topology
- `nasal_subsystem.py`: dedicated nasal functional partition
- `contact_simulation.py`: evidence-gated contact-analysis framework
- `structural_frame.py`: structural datum and subsystem reservation architecture
- `actuator_frames.py` and related modules: four-zone actuation references
- `water_reservoir.py`, `cleanser_storage.py` and distribution modules: fresh-fluid architecture
- `waste_acquisition.py`, `waste_pump_architecture.py`, `waste_cartridge.py` and `waste_routes.py`: mixed-waste architecture
- `component_registry.py`: canonical component and interface identity
- `export.py`, `step_integrity.py` and `release_package.py`: deterministic release and STEP verification

See [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md) for the broader source hierarchy.

## Toolchain

The currently controlled Python engineering environment uses:

- Python 3.13.x
- CadQuery 2.8.0
- jsonschema 4.26.0
- PyYAML 6.0.3
- pytest 9.0.2

Install the project in an isolated environment:

```bash
python -m pip install -e ".[dev]"
```

## Validation and tests

Validate the engineering authority:

```bash
python -m masck_one.authority
```

Run repository preflight:

```bash
python -m masck_one.preflight
```

Run the complete test suite:

```bash
python -m compileall -q src tests
python -m pytest
```

Generate the current deterministic CAD baseline:

```bash
python -m masck_one.cli --output generated
```

The release build produces STEP files and structured manifests used to verify source identity, geometry integrity and development status.

## Documentation

Useful starting points:

- [`docs/DEVELOPMENT_ROADMAP.md`](docs/DEVELOPMENT_ROADMAP.md): controlled development sequence
- [`docs/CORE_SKETCH_START_HERE.md`](docs/CORE_SKETCH_START_HERE.md): current whole-product concept entry point
- [`docs/ENGINEERING_GOVERNANCE.md`](docs/ENGINEERING_GOVERNANCE.md): engineering change and evidence rules
- [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md): source hierarchy and repository organisation
- [`docs/COORDINATE_SYSTEM.md`](docs/COORDINATE_SYSTEM.md): global and local coordinate conventions
- [`docs/FACIAL_REFERENCE.md`](docs/FACIAL_REFERENCE.md): facial reference model
- [`docs/COMPLIANT_INTERFACE_TOPOLOGY.md`](docs/COMPLIANT_INTERFACE_TOPOLOGY.md): facial-interface architecture
- [`docs/STRUCTURAL_FRAME_TOPOLOGY.md`](docs/STRUCTURAL_FRAME_TOPOLOGY.md): current structural-frame state
- [`docs/DIGITAL_PRODUCT_VISION.md`](docs/DIGITAL_PRODUCT_VISION.md): companion digital-product direction
- [`DIGITAL_PRODUCT_HANDOFF_README.md`](DIGITAL_PRODUCT_HANDOFF_README.md): engineering-to-digital handoff rules

## Current limitations

The repository is deliberately conservative about readiness claims. Current digital work does not establish, by itself:

- consumer fit across a representative population
- comfort or skin-contact pressure in physical use
- cleansing efficacy
- leak resistance or retained waste capacity
- structural strength, fatigue life or drop durability
- battery runtime or electrical safety
- thermal safety or performance
- manufacturing process capability
- production tolerances
- regulatory or clinical claims

Those questions require physical prototypes, measurement and, where applicable, qualified external testing.

## Project direction

The immediate objective is to converge the current digital architecture into a coherent physical prototype, validate the assumptions that cannot be resolved in software, and use those results to drive the next engineering and commercial decisions.

Masck One is being developed as a product first, not as a collection of disconnected technical demonstrations. The repository exists to make that development traceable, reproducible and honest about what is known, what is assumed and what still needs to be proven.
