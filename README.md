# Masck One — deterministic engineering/code-CAD repository

This repository is the controlled digital-engineering implementation of **Masck One**.

The project is intentionally strict about the difference between a value that can be encoded in CAD today and a physical behavior that has actually been validated. The repository may generate deterministic geometry from the current engineering authority while still reporting physical evidence gates as `BLOCKED` or `VALIDATION_GATED`.

## Current development state

**Phase 1: repository engineering foundation — in progress.**

The existing code-CAD baseline currently generates the rigid shell development geometry, dedicated nasal/T-zone interface, nominal protected apertures, four actuator packaging references, water-reservoir envelope, waste-cartridge envelope, battery packaging reference, STEP exports, and a structured assertion report. These are development artifacts, not a claim that fit, cleansing efficacy, airflow, pressure, materials, or production readiness have been physically validated.

## Repository principles

- Product name: **Masck One**.
- Machine ID: `MASCK_ONE`.
- `config/masck_one_authority.yaml` is the current machine-readable parameter authority used by the baseline generator.
- `schemas/masck_one_authority.schema.json` is the strict structural contract for that authority.
- Authority loading also runs deterministic semantic cross-checks before CAD generation is permitted.
- Duplicate YAML keys are rejected rather than silently overwritten.
- Generated CAD must be reproducible from source.
- Validation-gated requirements remain validation-gated until evidence closes them.
- Missing real-world evidence is represented explicitly rather than fabricated.
- Generated STEP files are build artifacts and are not source authority.

## Controlled toolchain

The currently verified Phase 1 toolchain is:

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

## Phase 1 preflight

```bash
python -m masck_one.preflight
```

Preflight checks the controlled runtime/dependencies, authority contract, product identity, required source structure, and repository naming invariant.

## Test

```bash
python -m compileall -q src tests
python -m pytest
```

## Generate the current CAD baseline

```bash
python -m masck_one.cli --output generated
```

The build emits STEP files and `build_report.json`. Software-verifiable failures fail the command; evidence-gated items remain explicitly `BLOCKED` instead of being reported as fabricated passes.

## Engineering governance

Read [`docs/ENGINEERING_GOVERNANCE.md`](docs/ENGINEERING_GOVERNANCE.md) before changing authoritative parameters or CAD architecture.

Development progress is recorded in [`docs/PHASE_1_LOG.md`](docs/PHASE_1_LOG.md).
