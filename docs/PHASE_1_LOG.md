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

---

## Iteration 2 — strict machine-authority contract

### Scope

This iteration deliberately leaves product geometry unchanged. Its sole engineering objective is to make the machine-readable authority difficult to corrupt accidentally before additional CAD subsystems depend on it.

### Implemented

- Added authority schema version `1.0.0`.
- Expanded the explicit unit registry to cover every physical quantity family currently encoded by the authority.
- Replaced ambiguous subsystem-wide status labels with more granular status metadata where the controlling authority distinguishes requirement classes.
- Added Draft 2020-12 JSON Schema validation with `additionalProperties: false` at controlled authority nodes.
- Added controlled authority-status vocabulary.
- Added exact product ID/name, unit-symbol, commercial-state and architecture-count constraints where these are presently authoritative.
- Added duplicate YAML-key rejection before schema validation so repeated keys cannot silently overwrite engineering values.
- Added deterministic semantic cross-checks for:
  - frozen datum origin;
  - functional-frame versus outer-envelope ordering;
  - shell nominal/minimum wall ordering;
  - neutral eye/nostril symmetry and mouth centerline;
  - duplicated airway area and local-dimension consistency;
  - airflow pressure-drop ordering;
  - uncontrolled branch/total liquid-volume ordering;
  - pressure-limit ordering;
  - membrane-strain ordering;
  - quick-release force-range ordering;
  - membrane center-point inclusion in DOE;
  - actuator angle center-point inclusion in DOE;
  - transient versus continuous actuator-force ordering;
  - usable versus gross reservoir volume;
  - CLEAN-cycle fluid-ledger closure;
  - cartridge service-capacity plus 25% authority margin;
  - dry versus loaded mass limit ordering;
  - rib-ratio range ordering;
  - Class-A RMS versus maximum deviation ordering;
  - paid-preorder state versus private-gate consistency;
  - protected requirement/status classification anchors.
- Added an explicit `masck-one-authority-check` command.
- Added authority-contract validation as its own CI gate before preflight/tests/CAD generation.
- Added adversarial tests that intentionally corrupt the authority and require deterministic rejection.
- Updated repository preflight to require the schema and report Phase 1 / Iteration 2.

### Evidence required before merge

1. Authority JSON Schema itself validates under Draft 2020-12.
2. Current authority passes schema validation with zero issues.
3. Current authority passes semantic validation with zero issues.
4. Duplicate-key adversarial test fails the malformed YAML before value overwrite.
5. Unknown status, unknown property and changed unit-symbol adversarial cases are rejected.
6. Cross-field drift cases are rejected by the intended semantic rule.
7. Existing CAD tests continue to pass unchanged.
8. Deterministic CAD smoke build remains `PASS`.
9. GitHub Actions completes successfully on the pull-request commit.

### Explicitly not attempted in this iteration

- No new facial geometry.
- No datum-system expansion beyond validating the existing frozen origin/axes.
- No new safety keep-out geometry.
- No change to actuator placement.
- No change to fluid topology.
- No change to shell Class-A surface.
- No physical validation status promotion.

The next iteration may establish the canonical coordinate/datum API because the authority it consumes is now contract-validated first.
