# Masck One — deterministic engineering/code-CAD repository

This repository is the controlled digital-engineering implementation of **Masck One**.

The project is intentionally strict about the difference between a value that can be encoded or checked digitally today and a physical behavior that has actually been validated. The repository may generate deterministic geometry and analysis infrastructure from the current engineering authority while still reporting physical evidence gates as `BLOCKED` or `VALIDATION_GATED`.

## Current development state

**Phase 2: compliant facial interface and nose/T-zone architecture — Iteration 11 release candidate.**

Phase 1 is complete. The current code-CAD baseline generates the rigid shell development geometry, a localized nasal-lobe membrane development reference, nominal protected apertures, four actuator packaging references, water-reservoir envelope, waste-cartridge envelope, battery packaging reference, STEP exports, and structured assertion reports. These are development artifacts, not claims that fit, cleansing efficacy, airflow, pressure, materials, or production readiness have been physically validated.

The engineering foundation now includes:

- canonical right-handed global coordinates and rigid transforms (`+X` wearer-right, `+Y` superior, `+Z` anterior);
- semantic authority-derived eye, nostril and mouth landmarks with unresolved anatomical depth kept explicit;
- external headform/reference-surface ingestion with units, handedness, provenance, hashes and rigid registration;
- a neutral facial-surface abstraction whose current planar development implementation is explicitly non-anatomical;
- conservative eye, mouth and nostril/airway protected envelopes with unresolved 3D anatomy kept evidence-gated;
- a deterministic 459-state worn-pose/misregistration regression screen using the authority's 5 mm radial and ±4° rotational limits;
- a triangle-level facial coverage mesh that partitions active targets from protected zones, preserves a dedicated nose/T-zone and nose-to-upper-lip/philtrum target region, consumes the authority's 90% aggregate / 90% T-zone / 100 mm² hole thresholds, and refuses to treat synthetic geometric success as cleansing-efficacy evidence;
- a compliant-interface topology that assigns every coverage triangle to a stable contact/T-zone/protected-opening parameter zone, conserves target/protected area exactly, preserves one connected development contact field, and keeps the true eye/mouth/nostril protected regions material-free;
- a dedicated nasal subsystem topology that partitions the active central nose/philtrum target into bridge/dorsum, left/right sidewall, nasal-lobe and philtrum roles without introducing unsupported anatomical dimensions;
- explicit localization of the authority-backed 0.30 mm center / 0.25–0.35 mm DOE thickness family to the nasal-lobe development role only;
- correction of the former broad 0.30 mm trapezoidal nasal placeholder: generated thickness CAD is now a local `nasal_lobe_membrane_reference`, while bridge/dorsum/sidewall/philtrum thickness remains unresolved until later geometry/material evidence.

## Repository principles

- Product name: **Masck One**.
- Machine ID: `MASCK_ONE`.
- `config/masck_one_authority.yaml` is the current machine-readable parameter authority.
- `schemas/masck_one_authority.schema.json` is its strict structural contract.
- Authority loading also performs deterministic semantic cross-checks before CAD generation is permitted.
- Duplicate YAML keys are rejected rather than silently overwritten.
- Generated CAD must be reproducible from source.
- Validation-gated requirements remain validation-gated until evidence closes them.
- Missing real-world evidence is represented explicitly rather than fabricated.
- Generated STEP files are build artifacts and are not source authority.

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
- `src/masck_one/nasal_preflight.py` — Iteration-11 source-chain, role, safety-exclusion and thickness-localization CI gate.

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

## Engineering preflight

```bash
python -m masck_one.preflight
python -m masck_one.nasal_preflight
```

The existing repository preflight checks the controlled runtime/dependencies and upstream engineering contracts. The Iteration-11 nasal preflight additionally checks exact upstream hashes, central target assignment closure, area conservation, bilateral sidewall balance, protected-opening exclusion, lobe-thickness localization, local lobe CAD thickness and evidence status.

## Test

```bash
python -m compileall -q src tests
python -m pytest
```

## Generate the current CAD baseline

```bash
python -m masck_one.cli --output generated
```

The build emits STEP files and `build_report.json`. Iteration 11 replaces the ambiguous `nasal_interface.step` placeholder with `nasal_lobe_membrane_reference.step`. The build report now also records deterministic coverage, compliant-interface and nasal-subsystem topology manifests. Software-verifiable failures fail the command; evidence-gated items remain explicitly `BLOCKED` instead of being reported as fabricated passes.

## Engineering governance

Read [`docs/ENGINEERING_GOVERNANCE.md`](docs/ENGINEERING_GOVERNANCE.md) before changing authoritative parameters or CAD architecture.

Read [`docs/COORDINATE_SYSTEM.md`](docs/COORDINATE_SYSTEM.md) before adding geometry, local datum frames, imported headforms/supplier CAD, fixture coordinates, pose transforms, or render-export transforms.

Read [`docs/FACIAL_REFERENCE.md`](docs/FACIAL_REFERENCE.md) before adding or consuming facial landmarks.

Read [`docs/REFERENCE_SURFACE_INGESTION.md`](docs/REFERENCE_SURFACE_INGESTION.md) before importing external reference geometry.

Read [`docs/WORN_POSE.md`](docs/WORN_POSE.md) before adding fit/misregistration regressions.

Read [`docs/COVERAGE_MESH.md`](docs/COVERAGE_MESH.md) before changing facial target regions, T-zone segmentation or coverage metrics.

Read [`docs/COMPLIANT_INTERFACE_TOPOLOGY.md`](docs/COMPLIANT_INTERFACE_TOPOLOGY.md) before changing skin-contact intent, protected openings or broad interface parameter zones.

Read [`docs/NASAL_SUBSYSTEM.md`](docs/NASAL_SUBSYSTEM.md) before changing the nose/T-zone functional partition, nasal-lobe thickness application boundary, protected nostril exclusions or philtrum continuity.

The controlled program sequence is in [`docs/DEVELOPMENT_ROADMAP.md`](docs/DEVELOPMENT_ROADMAP.md).
