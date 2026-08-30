# Masck One reference-surface ingestion contract

## Purpose

External headforms, face scans, supplier reference models, FEA meshes and other geometry must never enter Masck One by visual alignment alone. Every source that can influence product geometry must carry explicit provenance, units, handedness, axis semantics, source revision/hash and a deterministic registration into `MASCK_ONE_GLOBAL`.

Iteration 5 establishes that contract. It does not add or validate a human headform.

## Required source metadata

Every reference surface requires:

- stable `asset_id`;
- source kind;
- source label;
- source revision;
- original source units;
- handedness;
- meaning of source +X, +Y and +Z;
- SHA-256 of the original source artifact or normalized source payload;
- evidence/status classification.

A model with unknown units or unknown axes is not admissible merely because it looks correctly oriented in a viewer.

## Supported source units

The ingestion layer currently recognizes:

- `mm` → 1.0 mm;
- `cm` → 10.0 mm;
- `m` → 1000.0 mm;
- `in` → 25.4 mm.

Unit normalization occurs before rigid registration.

No implicit unit inference is permitted. A 0.18-unit-wide scan is not assumed to be metres because that seems anatomically plausible.

## Handedness

The canonical Masck One frame is right-handed. Iteration 5 therefore accepts only right-handed source geometry.

A left-handed source is **not** silently mirrored. It must first be converted in a documented preprocessing step, exported as a corrected right-handed artifact, re-hashed, and then ingested as a new traceable source.

This avoids hidden reflections that can swap anatomical left/right semantics.

## Mesh contract

The internal neutral interchange representation is an immutable triangular mesh:

- finite 3D vertices;
- zero-based triangle indices;
- exactly three unique indices per triangle;
- all indices in range;
- non-degenerate triangles.

This representation is deliberately small and independent of a particular scan/vendor format. Later file-format adapters may parse STL/OBJ/PLY/STEP-derived tessellation, but all adapters must end at this same validated contract before the geometry can influence downstream calculations.

## Source hash

`source_sha256` records the original source artifact or normalized payload.

For normalized JSON-like mesh payloads, `TriangleMesh.normalized_sha256()` provides a deterministic digest over canonicalized vertices and triangle connectivity.

For binary scan files, the stored source hash should be computed from the original file bytes. The normalized-mesh hash may be stored separately because it answers a different question: whether the parsed/tessellated representation changed.

## Registration

A registered surface uses an explicit `SurfaceRegistration` containing:

- a right-handed rigid transform from unit-normalized source coordinates into `MASCK_ONE_GLOBAL`;
- registration method;
- registration revision;
- optional RMS error;
- optional maximum error;
- evidence status.

The transform is strictly rigid. Scale is handled only by the declared unit conversion. `RigidTransform` rejects reflection, shear and non-uniform scale.

This prevents a fit operation from quietly changing head size to make an alignment look better.

## Registration quality

If registration errors are known:

- RMS error must be non-negative;
- maximum error must be non-negative;
- RMS error cannot exceed maximum error.

Iteration 5 does not invent an acceptable anatomical registration threshold because that threshold depends on the future headform/scan source and its intended use. A later iteration must establish application-specific acceptance criteria before registration accuracy is promoted to `PASS` for fit/safety purposes.

## Manifest

Every ingested asset can emit a registration manifest containing:

- asset ID and source metadata;
- source SHA-256;
- source units and conversion to mm;
- handedness and axis semantics;
- registration matrix and translation;
- registration error metrics/status;
- source mesh vertex/triangle counts;
- normalized mesh SHA-256.

This manifest is the bridge between geometry and change control. A downstream report should be able to state precisely which source geometry and which registration revision it used.

## External file adapters

A future adapter for STL, OBJ, PLY, STEP, scan formats, or supplier-specific files must not bypass this layer. It must:

1. hash the original file;
2. parse the geometry without hidden scaling;
3. record source units explicitly;
4. record handedness and axis semantics explicitly;
5. create a valid triangular representation or a separately governed B-rep path;
6. apply a documented rigid registration;
7. emit traceability metadata;
8. preserve the original source as immutable evidence.

## What Iteration 5 does not claim

Iteration 5 does not claim:

- that a representative human headform has been selected;
- that current NIOSH or other headforms represent the target customer population;
- that a face scan has been registered;
- that any registration accuracy is sufficient for airway, eye, pressure or cleansing claims;
- that any external supplier geometry is production approved;
- that the existing mask shell fits a real person.

Those are intentionally deferred.

## Failure policy

The repository must reject rather than guess when it encounters:

- unknown units;
- malformed source hashes;
- left-handed sources without documented preprocessing;
- degenerate triangles;
- invalid triangle indices;
- non-rigid registration transforms;
- malformed/unknown normalized payload fields;
- impossible registration error ordering.

A blocked external geometry source is preferable to a plausible-looking but untraceable model.
