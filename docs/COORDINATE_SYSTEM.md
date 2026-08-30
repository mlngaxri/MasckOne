# Masck One canonical coordinate and datum contract

## Purpose

Every future CAD component, simulation mesh, validation fixture, supplier model, render export, mass-location entry, protected-volume definition, and worn-pose transform must be interpretable in one unambiguous spatial convention.

This document defines the software contract established in Phase 1 / Iteration 3. It does **not** introduce new anthropometric or product geometry. The source numerical origin and axis meanings remain the machine authority in `config/masck_one_authority.yaml`.

## Global frame

The canonical frame is named:

`MASCK_ONE_GLOBAL`

The current frozen datum is:

- origin: `(0, 0, 0)` mm
- `+X`: wearer's right
- `+Y`: superior
- `+Z`: anterior, away from the face

The frame is right-handed:

`+X × +Y = +Z`

The code rejects left-handed or non-orthonormal datum frames.

## Principal datum planes

Three principal planes are derived directly from the global frame:

### `MASCK_ONE_SAGITTAL_X0`

- equation: `X = 0`
- normal: `+X`
- positive signed distance is toward the wearer's right

This plane is the neutral-baseline symmetry reference. Mirroring across it changes only the sign of X.

### `MASCK_ONE_TRANSVERSE_Y0`

- equation: `Y = 0`
- normal: `+Y`
- positive signed distance is superior

### `MASCK_ONE_CORONAL_Z0`

- equation: `Z = 0`
- normal: `+Z`
- positive signed distance is anterior / away from the face

These names are stable machine identifiers. They must not be reused for different planes later.

## Units

Spatial coordinates are represented in millimetres unless a caller explicitly states another unit. The authority's registered length unit is `mm`.

`Point2`, `Point3`, `Vector3`, `DatumFrame`, `DatumPlane`, and `RigidTransform` do not perform implicit unit conversion. A caller importing geometry expressed in metres, inches, pixels, mesh units, or any supplier-local unit must convert it before constructing canonical Masck One points.

## Typed spatial primitives

### `Point2`

Used for a point in an XY plane, particularly authority-defined aperture centers that do not yet have an authoritative Z coordinate.

A point is not a vector. The type distinction is deliberate so future transforms cannot accidentally translate a direction vector.

### `Point3`

Used for a Cartesian location.

### `Vector3`

Used for direction, offset, normal, axis, or displacement.

Vectors support deterministic dot product, cross product, norm, normalization and scaling.

A zero-length vector cannot be normalized.

### `Matrix3`

Used internally for 3D rotation matrices.

A `RigidTransform` accepts only a matrix that is:

- finite;
- orthonormal within the controlled numerical tolerance;
- determinant `+1`;
- therefore right-handed and free of scale/shear/reflection.

### `RigidTransform`

Maps points/vectors from one stated frame into another.

The transform is represented as:

`p_destination = R * p_source + t`

Vectors are transformed as:

`v_destination = R * v_source`

Translation is never applied to vectors.

The inverse is calculated analytically using `R^T` and is tested with round trips.

## Rotation sign convention

Positive rotation follows the right-hand rule around the positive axis.

Examples tested by CI:

- positive `+90°` about Z maps `+X` toward `+Y`;
- positive `+90°` about Y maps `+Z` toward `+X`.

This matters for later actuator axes, worn-pose transforms, headform registration, ray directions, keep-out geometry and render exports.

## Pose-construction implementation convention

`RigidTransform.from_extrinsic_xyz(...)` provides one explicit software convention for six-degree-of-freedom poses.

Inputs are:

- translation in global XYZ;
- roll about fixed/global X;
- pitch about fixed/global Y;
- yaw about fixed/global Z.

The resulting rotation is:

`Rz(yaw) * Ry(pitch) * Rx(roll)`

This ordering is an **implementation convention**, not a promoted physical requirement. Any external tool using a different Euler convention must convert explicitly rather than reinterpreting the same three numbers.

## Transform composition

`transform_a.followed_by(transform_b)` means:

1. apply `transform_a`;
2. then apply `transform_b`.

The method name is intentionally verbose so code does not depend on ambiguous multiplication-order intuition.

CI tests the composition order with a non-commuting translate/rotate example.

## Local datum frames

A future subsystem may define a local `DatumFrame` only if all of the following are explicit:

- unique stable name;
- origin expressed in `MASCK_ONE_GLOBAL`;
- local +X axis expressed in global coordinates;
- local +Y axis expressed in global coordinates;
- local +Z axis expressed in global coordinates;
- axes orthonormal and right-handed;
- source/status for the frame definition.

No important subsystem is allowed to rely on an undocumented CAD workplane whose relation to the global frame is unknown.

Examples of future named frames may include facial-reference, shell, nasal, actuator, cartridge, halo, battery, supplier-component, fixture and render-export frames. Their positions are not invented in Iteration 3; they are added only when their authority becomes explicit.

## Authority adapters

`authority_point2(...)` and `authority_point3(...)` convert coordinate arrays from the machine authority into typed point objects.

This removes call-site-specific assumptions such as one file treating a pair as `(X, Y)` while another silently treats it as `(Y, X)`.

Current eye, mouth and nostril center consumption in the CAD generator has been migrated through the typed spatial API without intentionally changing their geometry.

## Sagittal mirroring

Neutral bilateral geometry can use the canonical sagittal-plane mirror operation.

For the current global frame:

`(x, y, z) -> (-x, y, z)`

Future asymmetric anthropometric/headform data must **not** be forced to obey bilateral symmetry merely because this helper exists. It is a deterministic baseline tool, not a claim that human faces are symmetric.

## Signed distance

`DatumPlane.signed_distance(point)` returns positive distance in the plane normal direction and negative distance opposite it.

This will later support:

- rigid keep-out checks;
- symmetry checks;
- support-plane distances;
- component-side classification;
- service-clearance diagnostics;
- geometric assertions.

It does not replace full surface-to-surface signed-distance algorithms for dynamic anatomical keep-outs.

## CAD integration rule

Raw tuples are acceptable only at the final boundary to a third-party CAD API that requires tuples.

Within Masck One engineering code, meaningful positions and directions should be represented by typed spatial objects first, then converted at that boundary using `as_tuple()`.

Iteration 3 migrates current aperture centers and packaging-center translations to this pattern while preserving the existing CAD baseline.

## External geometry import rule

Before any headform, supplier STEP, scan, FEA mesh, CFD mesh, or render model becomes authoritative in the project, its import adapter must record:

1. source coordinate system;
2. source units;
3. handedness;
4. axis meanings;
5. source origin;
6. transform into `MASCK_ONE_GLOBAL`;
7. revision/hash of the source artifact;
8. validation that the transform is rigid unless deliberate scaling is separately documented upstream.

A visually correct orientation is not sufficient provenance.

## Numerical discipline

Spatial primitives reject NaN and infinite values.

Rigid transforms reject scale, reflection and shear.

Frames reject zero-length, non-orthogonal and left-handed axis sets.

Round-trip tolerances used in unit tests are intentionally much tighter than mechanical tolerances because they validate mathematical implementation, not manufacturing capability.

## What Iteration 3 does not claim

This iteration does not establish:

- a final facial surface;
- final facial landmarks beyond coordinates already in the machine authority;
- dynamic eye geometry;
- dynamic mouth geometry;
- deformable airway geometry;
- population-fit validity;
- final shell datum location beyond the existing global convention;
- final actuator local frames;
- final cartridge/halo/battery datums;
- physical alignment accuracy.

Those require later engineering authority and/or physical evidence.

## Regression requirement

A future change to the global origin, handedness, axis semantics, rotation convention, datum names, or transform-composition semantics is a system-level breaking change.

Such a change must not be made as an isolated convenience edit. It requires explicit authority/change-control review and regression across CAD, simulation, validation, mass/CG, fluidics, electronics, renders, fixtures, website assets and any exported supplier geometry that depends on the previous convention.
