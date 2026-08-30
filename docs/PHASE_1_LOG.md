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

---

## Iteration 3 — canonical spatial and datum contract

### Scope

This iteration deliberately avoids inventing new facial, actuator, fluid or shell geometry. It establishes the mathematical/spatial infrastructure that every later geometry-bearing subsystem must use so coordinates, vectors, transforms, symmetry operations, local frames and imported reference data cannot acquire inconsistent axis conventions.

### Implemented

- Added `src/masck_one/spatial.py` as the canonical spatial API.
- Added finite-value validation for all spatial primitives.
- Added typed `Point2`, `Point3` and `Vector3` objects.
- Added explicit point-versus-vector behavior so translations cannot be applied accidentally to directions.
- Added vector dot product, cross product, norm, normalization and scaling.
- Added immutable `Matrix3` rotation support.
- Added right-handed rotation constructors around global X, Y and Z.
- Added determinant and orthonormal/right-handed validation.
- Added `RigidTransform` with explicit point and vector transformation semantics.
- Added analytical rigid-transform inverse.
- Added unambiguous `followed_by(...)` transform-composition semantics.
- Added an explicit extrinsic XYZ pose-construction convention using `Rz * Ry * Rx`.
- Added `DatumFrame` with mandatory right-handed orthonormal axes.
- Added `DatumPlane` with signed-distance and projection operations.
- Added `CanonicalDatums.from_authority(...)`, deriving the spatial contract directly from the frozen authority rather than duplicating the origin/axis definitions.
- Added stable principal datum identifiers:
  - `MASCK_ONE_GLOBAL`;
  - `MASCK_ONE_SAGITTAL_X0`;
  - `MASCK_ONE_TRANSVERSE_Y0`;
  - `MASCK_ONE_CORONAL_Z0`.
- Added canonical sagittal mirroring.
- Added `authority_point2(...)` and `authority_point3(...)` adapters so authority coordinate arrays cannot acquire call-site-specific ordering semantics.
- Migrated current eye, mouth and nostril center consumption in CAD generation through typed authority adapters.
- Migrated current packaging-center translations through `Point3` before crossing the CadQuery tuple API boundary.
- Added canonical datums to every `MasckOneModel` instance.
- Added a dedicated spatial-contract preflight check.
- Added a detailed `docs/COORDINATE_SYSTEM.md` contract for future CAD, simulation, fixtures, supplier imports and render exports.
- Added adversarial/unit tests covering handedness, sign conventions, mirror behavior, rigid inverse round trips, transform ordering, frame round trips, projection, zero vectors, non-finite values, non-orthonormal matrices and left-handed frames.
- Exposed spatial primitives lazily at the package boundary without forcing CadQuery import for authority-only operations.

### Evidence required before merge

1. Existing authority/schema validation remains `PASS`.
2. Canonical datum origin remains exactly `(0, 0, 0)` mm.
3. Axis semantics remain `+X wearer-right`, `+Y superior`, `+Z anterior`.
4. `+X × +Y = +Z` and determinant of all accepted frame rotations is `+1`.
5. Positive Z and Y rotation sign tests pass.
6. Rigid-transform inverse round trips recover representative points/vectors within numerical tolerance.
7. Transform-composition order is proven by a non-commuting translate/rotate test.
8. Left-handed and non-orthonormal frames are rejected deterministically.
9. NaN/infinite spatial inputs are rejected deterministically.
10. Existing CAD model tests remain unchanged in engineering outcome.
11. Deterministic CAD smoke build remains `PASS` after typed-coordinate migration.
12. Repository preflight reports Phase 1 / Iteration 3 and the spatial contract passes.
13. GitHub Actions completes successfully on the pull-request head before merge.

### Explicitly not attempted in this iteration

- No final facial-reference surface.
- No new anthropometric landmark values.
- No dynamic eye/mouth/airway keep-out geometry.
- No new actuator placements.
- No shell Class-A redesign.
- No fluid-routing changes.
- No final subsystem-local datum positions whose authority is not yet explicit.
- No physical validation status promotion.

The next iteration can establish the first canonical facial-reference and landmark layer because all future geometry now has a tested coordinate/transform contract beneath it.
