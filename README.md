# Masck One — deterministic engineering/code-CAD repository

This repository is the controlled digital-engineering implementation of **Masck One**, the founding hero product of the broader **MASCK** master brand.

MASCK is being structured as a premium automated personal-care hardware brand rather than a company permanently limited to one mask form factor. Execution remains deliberately narrow: this repository is for making Masck One exceptional, not for inventing a speculative portfolio.

The project is intentionally strict about the difference between a value that can be encoded or checked digitally today and a physical behavior that has actually been validated. The repository may generate deterministic geometry and analysis infrastructure from the current engineering authority while still reporting physical evidence gates as `BLOCKED` or `VALIDATION_GATED`.

## Current development state

**Phase 5: waste acquisition and containment — Iteration 28 complete.**

Phases 1 to 5 of [`docs/DEVELOPMENT_ROADMAP.md`](docs/DEVELOPMENT_ROADMAP.md) are
complete. `project.development_phase` and `project.completed_iteration` in
`config/masck_one_authority.yaml` are the single source of truth for this
position; the roadmap, this README and `build_report.json` are all checked
against them by `tests/test_program_position.py`, so they cannot drift apart
silently.

The current code-CAD baseline generates rigid shell development geometry, a
localized nasal-lobe membrane development reference, nominal protected
apertures, four actuator packaging references, water-reservoir envelope,
waste-cartridge envelope, battery packaging reference, per-solid verified STEP
exports, and structured assertion reports. These are development artifacts. They
are not claims that fit, cleansing efficacy, airflow, pressure, materials,
tactile quality or production readiness have been physically validated.

Released capability by phase:

- **Phase 1 — foundations and human reference.** Canonical right-handed global
  coordinates and rigid transforms (`+X` wearer-right, `+Y` superior, `+Z`
  anterior); authority-derived eye, nostril and mouth landmarks with unresolved
  anatomical depth kept explicit; external headform ingestion with units,
  handedness, provenance, hashes and rigid registration; a neutral facial-surface
  abstraction whose current planar development implementation is explicitly
  non-anatomical; conservative eye/mouth/airway protected envelopes; a
  deterministic 459-state worn-pose regression screen at the authority's 5 mm
  radial and ±4° rotational limits; and a triangle-level coverage mesh that
  partitions active targets from protected zones and refuses to treat synthetic
  geometric success as cleansing-efficacy evidence.
- **Phase 2 — compliant facial interface.** Contact/T-zone/protected-opening
  parameter zones with exact area conservation and one connected contact field;
  a nasal subsystem partitioned into bridge/dorsum, sidewall, lobe and philtrum
  roles; the authority-backed 0.30 mm nasal-lobe thickness family localized to
  the lobe role only; perimeter and aperture-edge boundaries; interface-to-frame
  attachment; and a nonlinear contact-simulation framework with evidence-gated
  material cards.
- **Phase 3 — rigid structure and actuation.** Structural-frame datum network
  and subsystem reservations; Class-A surface workflow and deviation governance;
  four actuator local frames and development envelopes; coupling, swept volumes
  and collision assertions; and the actuation parameter/sensitivity framework.
- **Phase 4 — fresh fluid delivery.** Water-reservoir and cleanser-storage
  architecture, pump packaging and tubing interfaces, a parametric manifold
  branching model, and skin-facing distribution grooves with protected-region
  outlet-direction rules.
- **Phase 5 — waste acquisition and containment.** Facial waste gutters and
  regional buffers, mixed-phase waste-pump packaging and fault states, keyed
  cartridge insertion and service geometry, and complete fresh/waste routing,
  bend-radius, dead-volume and service-clearance checks.

Known open dependency: the structural frame is still **topology and reservations
only**. `structural_frame.py` reports
`load_validation_status="BLOCKED_PENDING_REALIZED_GEOMETRY_MATERIAL_AND_ANALYSIS_PHYSICAL_EVIDENCE"`,
and no released load-bearing frame B-rep exists. Treatment reaction, retention
load paths, installed cartridge extraction and dry-side support all stack on
that gap. See [`docs/STRUCTURAL_FRAME_TOPOLOGY.md`](docs/STRUCTURAL_FRAME_TOPOLOGY.md).

## Repository principles

- Product name: **Masck One**.
- Machine ID: `MASCK_ONE`.
- Parent brand: **MASCK**.
- `config/masck_one_authority.yaml` is the current machine-readable engineering parameter authority.
- `schemas/masck_one_authority.schema.json` is its strict structural contract.
- `config/masck_brand_authority.yaml` is the machine-readable brand/product-identity contract and never overrides engineering authority.
- `schemas/masck_brand_authority.schema.json` is its strict structural contract.
- Authority loading also performs deterministic semantic cross-checks before CAD generation is permitted.
- Duplicate YAML keys are rejected rather than silently overwritten.
- Generated CAD must be reproducible from source.
- Validation-gated requirements remain validation-gated until evidence closes them.
- Missing real-world evidence is represented explicitly rather than fabricated.
- Generated STEP files are build artifacts and are not source authority.

## Brand and product identity

The selected brand architecture is intentionally broader than the first product:

- **MASCK** is the master company/brand.
- **M-Cut** is the current provisional standalone master-mark direction.
- **Masck One** is the founding hero product.
- **M/1** is a compact product designation, not the company logo.
- The long-term territory is premium automated personal-care hardware, while near-term execution remains overwhelmingly focused on Masck One.

The primary physical control is intended to become a recurring MASCK interaction: dense, precise, quiet, highly constrained and mechanically satisfying, with the master M-Cut integrated into the surface/optical architecture rather than printed decoration. The current exterior language explicitly rejects goggle eye rings, VR/headset cues, respirator/medical PPE character, tactical panels and fake technical detailing.

Read [`docs/BRAND_ARCHITECTURE.md`](docs/BRAND_ARCHITECTURE.md) before changing product naming, master-mark role, M/1 usage, CMF direction, primary-control brand behavior or the no-goggle exterior language. Read [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md) for the engineering-versus-brand source hierarchy.

Normal release export now emits `brand_identity.json` beside the engineering manifests. It is product/interaction/CMF intent, not physical performance evidence, production material qualification or trademark clearance.

## Digital product vision

The repository also carries a deliberately **non-authoritative** digital product vision for the marketing website, companion app, commercial backend and future connected-device experience. Read [`docs/DIGITAL_PRODUCT_VISION.md`](docs/DIGITAL_PRODUCT_VISION.md) for the target iOS/Android app, usage-session experience, capability-gated wear-state/device controls, Supabase-backed account/reservation architecture, website app showcase and preorder path.

That document defines product intent and software architecture only. It does not override `config/masck_one_authority.yaml`, released engineering code/CAD, validation evidence or [`DIGITAL_PRODUCT_HANDOFF_README.md`](DIGITAL_PRODUCT_HANDOFF_README.md). Future BLE, wear detection, session telemetry, device control, measured performance and paid preorder activation remain gated by their physical/commercial dependencies.

Key engineering modules:

- `src/masck_one/spatial.py` — canonical points, vectors, datums and rigid transforms.
- `src/masck_one/anatomy.py` — semantic facial landmark/reference layer.
- `src/masck_one/reference_surfaces.py` — external mesh provenance/unit/registration boundary.
- `src/masck_one/facial_surface.py` — neutral facial-surface abstraction.
- `src/masck_one/protected_volumes.py` — eye/mouth/airway safety-exclusion topology.
- `src/masck_one/worn_pose.py` — deterministic misregistration regression engine.
- `src/masck_one/coverage.py` — facial-region segmentation, target/protected area accounting and coverage metrics.
- `src/masck_one/interface_topology.py` — main compliant facial-interface contact/protected topology and parameter-zone authority boundary.
- `src/masck_one/nasal_subsystem.py` — dedicated bridge/dorsum/sidewall/lobe/philtrum functional partition and local lobe-thickness boundary.
- `src/masck_one/nasal_preflight.py` — nasal source-chain, role, safety-exclusion and thickness-localization CI gate.
- `src/masck_one/interface_boundaries.py` — perimeter, seal/compliance zones and aperture-edge transitions.
- `src/masck_one/interface_attachment.py` — interface-to-structural-frame attachment and clamp architecture.
- `src/masck_one/contact_simulation.py` — nonlinear membrane/contact framework with evidence-gated material cards.
- `src/masck_one/structural_frame.py` — frame datum network and subsystem reservations (topology only; no released load-bearing B-rep).
- `src/masck_one/surface_workflow.py` — Class-A exterior surface workflow and deviation governance.
- `src/masck_one/actuator_frames.py`, `actuator_coupling.py`, `actuation_parameters.py` — four actuator local frames, load paths, swept volumes and sensitivity framework.
- `src/masck_one/water_reservoir.py`, `cleanser_storage.py`, `distribution_manifold.py`, `distribution_geometry.py` — fresh fluid delivery.
- `src/masck_one/waste_acquisition.py`, `waste_pump_architecture.py`, `waste_cartridge.py`, `waste_routes.py` — waste acquisition, transport and containment.
- `src/masck_one/component_registry.py` — canonical component/interface registry and source binding.
- `src/masck_one/export.py`, `step_integrity.py`, `release_package.py` — deterministic export, per-solid STEP round-trip verification and package integrity.
- `src/masck_one/integration_contract.py` — edit-ownership map for concurrent sprint lanes (navigation only; live GitHub is authoritative for PR/branch state).
- `src/masck_one/brand_identity.py` — strict MASCK master-brand / Masck One product-identity loader and deterministic manifest producer.

The full module set is larger than this list; see `src/masck_one/` and
[`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md).

## Controlled toolchain

The currently verified toolchain is:

- Python 3.13.x
- CadQuery 2.8.0
- jsonschema 4.26.0
- PyYAML 6.0.3
- pytest 9.0.2 for development/testing

Install in an isolated environment:

```bash
python -m pip install -e ".[dev]"
```

## Validate the engineering authority

```bash
python -m masck_one.authority
```

This performs strict JSON Schema validation followed by deterministic semantic checks. It does not claim physical validation; it establishes that the digital authority is explicit and internally self-consistent.

## Validate the brand/product identity contract

```bash
python -m masck_one.brand_identity
# or, after installation:
masck-brand-check
```

This validates the parent/product split, M-Cut/M/1 roles, primary-control identity, CMF token structure, no-goggle exterior constraints and the explicit provisional evidence boundary.

## Engineering preflight

```bash
python -m masck_one.preflight
python -m masck_one.nasal_preflight
python -m masck_one.boundary_preflight
python -m masck_one.attachment_preflight
python -m masck_one.contact_simulation_preflight
python -m masck_one.structural_frame_preflight
python -m masck_one.surface_workflow_preflight
```

The repository preflight checks the controlled runtime/dependencies and upstream engineering contracts. The nasal preflight additionally checks exact upstream hashes, central target assignment closure, area conservation, bilateral sidewall balance, protected-opening exclusion, lobe-thickness localization, local lobe CAD thickness and evidence status. CI additionally runs the boundary, attachment, contact-simulation, structural-frame and Class-A surface-workflow preflights; see `.github/workflows/ci.yml` for the released gate order.

## Test

```bash
python -m compileall -q src tests
python -m pytest
```

## Generate the current CAD baseline

```bash
python -m masck_one.cli --output generated
```

The build emits STEP files, `component_registry.json`, `brand_identity.json` and `build_report.json`. The nasal thickness solid is exported as `nasal_lobe_membrane_reference.step`, deliberately named for the local development role it represents rather than as a whole nasal interface. The build report also records deterministic coverage, compliant-interface, nasal-subsystem and source-bound brand/product identity manifests. Software-verifiable failures fail the command; evidence-gated items remain explicitly `BLOCKED` instead of being reported as fabricated passes.

## Engineering governance

Read [`docs/ENGINEERING_GOVERNANCE.md`](docs/ENGINEERING_GOVERNANCE.md) before changing authoritative parameters or CAD architecture.

Read [`docs/COORDINATE_SYSTEM.md`](docs/COORDINATE_SYSTEM.md) before adding geometry, local datum frames, imported headforms/supplier CAD, fixture coordinates, pose transforms, or render-export transforms.

Read [`docs/FACIAL_REFERENCE.md`](docs/FACIAL_REFERENCE.md) before adding or consuming facial landmarks.

Read [`docs/REFERENCE_SURFACE_INGESTION.md`](docs/REFERENCE_SURFACE_INGESTION.md) before importing external reference geometry.

Read [`docs/WORN_POSE.md`](docs/WORN_POSE.md) before adding fit/misregistration regressions.

Read [`docs/COVERAGE_MESH.md`](docs/COVERAGE_MESH.md) before changing facial target regions, T-zone segmentation or coverage metrics.

Read [`docs/COMPLIANT_INTERFACE_TOPOLOGY.md`](docs/COMPLIANT_INTERFACE_TOPOLOGY.md) before changing skin-contact intent, protected openings or broad interface parameter zones.

Read [`docs/PROCESS_CAPABILITY.md`](docs/PROCESS_CAPABILITY.md) before tightening any tolerance or choosing a part split that places a visible seam.

Read [`docs/MULTI_AGENT_INTEGRITY.md`](docs/MULTI_AGENT_INTEGRITY.md) before changing a pinned ratchet value, and before adding a skip, deleting a test or widening a tolerance. Several agents and more than one toolchain edit this repository concurrently; CI rejects silent weakening in about 1.5 seconds.

Read [`docs/MASS_BALANCE.md`](docs/MASS_BALANCE.md) before changing any `mass:` limit or moving mass anteriorly to solve a packaging problem.

Read [`docs/AIRWAY_RESISTANCE.md`](docs/AIRWAY_RESISTANCE.md) before changing `safety.airway` limits, nostril aperture geometry or anything that reduces the deformed nasal opening.

Read [`docs/NASAL_SUBSYSTEM.md`](docs/NASAL_SUBSYSTEM.md) before changing the nose/T-zone functional partition, nasal-lobe thickness application boundary, protected nostril exclusions or philtrum continuity.

The controlled program sequence is in [`docs/DEVELOPMENT_ROADMAP.md`](docs/DEVELOPMENT_ROADMAP.md).
