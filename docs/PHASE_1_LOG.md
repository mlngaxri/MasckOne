# Phase 1 — repository engineering foundation

## Iteration 1 — deterministic repository integrity

### Scope

This intentionally small iteration does not change Masck One product geometry. It establishes the repository as a controlled engineering environment before deeper CAD work continues.

### Implemented

- Controlled product/package naming.
- Python runtime declaration.
- Exact runtime dependency versions for the currently verified toolchain.
- Exact test/schema-support dependency versions.
- Reproducible package entry points for CAD generation and repository preflight.
- Repository-wide naming guard.
- Authority-load/name/project-ID checks.
- Required-source-structure check.
- Generated-artifact source-control policy.
- Phase 1 repository-integrity tests.
- GitHub Actions CI definition.
- Engineering governance document.

### Required evidence before promotion

The iteration is considered complete only when:

1. `python -m compileall -q src tests` succeeds.
2. `python -m pytest` succeeds.
3. `python -m masck_one.preflight` reports `PASS` after installation.
4. `python -m masck_one.cli --output <temporary-output>` reports `PASS`.
5. All emitted STEP files used by the current baseline can be imported back by CadQuery/OpenCascade.
6. No legacy product naming appears in source-controlled text.

### Explicitly not attempted in this iteration

- No Class-A exterior redesign.
- No new facial surface assumptions.
- No actuator repositioning.
- No fluid-manifold geometry changes.
- No physical validation status promotion.

Those are intentionally deferred so repository controls exist before geometry complexity grows.
