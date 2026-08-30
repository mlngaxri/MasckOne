# Masck One neutral facial reference surface

## Purpose

Iteration 6 introduced one consistent software abstraction for the facial surface that later regions, keep-outs, interface geometry, pressure/contact models and coverage algorithms reference.

The critical rule is that **topology infrastructure is allowed to exist before anatomical evidence, but topology infrastructure must not be mislabeled as anatomical evidence**.

Iteration 10 tightened the development-mesh resolution after a downstream interface-connectivity check exposed a discretization artifact. That correction changes only the synthetic topology resolution; it does not promote the planar surface into anatomical evidence.

## Two surface classes

### 1. Planar development reference

Until a selected and properly registered headform/face reference exists, Masck One uses a deterministic planar development mesh at `Z = 0`.

This mesh:

- follows the current functional-frame XY envelope;
- is tessellated deterministically;
- is expressed in `MASCK_ONE_GLOBAL` millimetres;
- gives later algorithms stable vertices/triangles/IDs to operate on;
- supports facial-region and coverage-algorithm development;
- provides a deterministic surface on which current 2D authority landmarks may be projected for debugging/topology work.

It is explicitly tagged:

`SYNTHETIC_TOPOLOGY_ONLY_NOT_ANATOMICAL_EVIDENCE`

It can never satisfy anatomical fit, eye clearance, airway clearance, pressure, seal, anthropometric coverage or human-comfort evidence gates.

### 2. Registered external reference

A headform/face scan that has passed the Iteration-5 ingestion contract can be wrapped in the same `FacialSurface` API.

Importing it does **not** automatically make it validation evidence. `anatomical_validation_eligible` defaults to `False` and must be promoted explicitly only after the source population, intended use, registration quality and evidence status are reviewed.

## Why the development surface is planar

The current machine authority contains reliable XY baseline locations for the eye centers, nostril centers and mouth center, but it does not contain a complete authoritative facial depth map.

Inventing nose, cheek, forehead and chin depths purely to make the model look human would create false precision and would contaminate later safety calculations.

A planar topology reference is therefore intentionally less visually impressive but more rigorous. It makes the missing evidence obvious while allowing the code architecture to progress.

## Deterministic mesh generation

The development mesh is generated inside the current functional-frame ellipse using a regular canonical XY grid. Only cells whose four corners are inside the ellipse become triangles. Cell diagonals mirror across `X = 0`, and the X sample count must be odd so the sagittal plane is an explicit vertex column.

The current default is **81 × 105 samples**. Across the current 155 × 202 mm functional frame this is approximately **1.94 mm spacing in both axes**. This is a digital-resolution baseline, not an anatomical resolution claim.

### Why Iteration 10 increased the resolution

The former 41 × 53 grid was approximately 3.9 mm in each axis. Its conservative protected-zone classification produced a two-triangle, approximately 15 mm² contact island in the philtrum corridor. The underlying continuous protected-zone geometry did not actually remove that corridor; the coarse grid simply lacked enough samples to represent it while conservatively excluding triangles near the mouth and nostril keep-outs.

The compliant-interface connectivity gate correctly rejected that result rather than accepting the disconnected island. The development mesh was therefore refined to approximately 2 mm spacing. At that resolution the intended skin-contact target field is represented as one edge-connected component while the eyes, mouth and nostrils remain protected.

This correction is important for two reasons:

1. **A mesh artifact is not allowed to become a product architecture decision.** A coarse discretization cannot be used as evidence that the physical interface should contain a detached philtrum island.
2. **Refinement is not physical evidence.** A finer planar mesh still does not prove real facial fit, pressure, airway safety or cleansing efficacy.

Callers may supply explicit sample counts to `build_planar_development_surface(...)` for sensitivity and convergence studies. Downstream engineering must continue to treat important conclusions that change materially with mesh resolution as unresolved digital-model issues rather than physical truth.

The normalized mesh is hashed. A changed authority frame or changed sampling rule changes the hash and is therefore visible to regression tooling.

## Landmark projections

Current 2D facial landmarks may be projected to the nearest surface vertex in XY.

For the planar development surface these projections are marked:

`DEVELOPMENT_PROJECTION_NOT_ANATOMICAL_EVIDENCE`

The projection does not resolve the anatomical Z-depth of the landmark in `anatomy.py`. Those landmarks remain formally unresolved in 3D until a valid surface/headform registration provides the required evidence.

This separation is deliberate: the code may draw a debug marker at Z=0 without claiming that the physical eye, nostril or mouth center lies at that depth.

## Registered-source pathway

A registered external source enters through `facial_surface_from_registered_asset(...)`.

The resulting descriptor retains:

- source asset ID;
- source SHA-256;
- registration revision;
- evidence status;
- explicit anatomical-validation eligibility.

The same downstream interfaces can therefore consume either the topology-only development surface or a later evidence-bearing reference without changing coordinate semantics.

## What the planar development surface does not claim

It does not claim:

- a final human facial surface;
- a final target-population headform;
- correct facial depth at the eyes, nose, cheeks, lips, chin or forehead;
- pressure/contact validity;
- dynamic expression validity;
- fit coverage;
- airway clearance;
- cleansing efficacy;
- final membrane geometry.

Those remain later work/evidence gates.

## Change-control rule

No developer may replace the planar surface with a more face-like analytical shape and then use that shape for safety or fit validation merely because it looks plausible.

A non-planar external facial/headform surface must carry Iteration-5 provenance and registration metadata. Its eligibility for anatomical validation must be an explicit status decision, not an inference from file format or visual realism.
