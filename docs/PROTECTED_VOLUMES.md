# Masck One protected eye, mouth and airway geometry

## Purpose

Iteration 7 converts the current authority-defined apertures and rigid-clearance baselines into explicit protected-zone objects that later CAD, outlet placement, region segmentation and worn-pose checks can consume.

The critical distinction is between **what is digitally defined now** and **what still requires anatomical/dynamic evidence**.

The current authority provides neutral XY aperture geometry and required rigid clearance values. It does not yet provide expression-dependent 3D eye, jaw, lip or deformable airway surfaces. Iteration 7 therefore creates conservative 2.5D exclusions and deliberately keeps the true dynamic 3D signed-distance gates blocked.

## Protected targets

Five stable zones exist:

- `MASCK_ONE-PROTECTED-EYE-LEFT`
- `MASCK_ONE-PROTECTED-EYE-RIGHT`
- `MASCK_ONE-PROTECTED-MOUTH`
- `MASCK_ONE-PROTECTED-NOSTRIL-LEFT`
- `MASCK_ONE-PROTECTED-NOSTRIL-RIGHT`

These IDs are intended to remain stable when later evidence replaces the current analytical footprint with registered/dynamic anatomical geometry.

## Eye zones

Each eye begins with the authority visual aperture:

- width: 46.0 mm
- height: 30.0 mm
- center X: ±31.5 mm
- center Y: +35.0 mm
- lateral cant magnitude: 4°
- required rigid dynamic-keepout clearance: 8.5 mm

The analytical protected footprint expands the aperture by 8.5 mm on every side, producing a nominal envelope size of 63.0 × 47.0 mm before later anatomy-dependent refinement.

This does **not** establish eyelid, globe, cheek, brow or expression geometry in Z.

## Mouth zone

The mouth uses:

- center: X=0, Y=-50.0 mm
- aperture: 58.0 × 32.0 mm
- required rigid dynamic-keepout clearance: 9.5 mm

The resulting analytical protected envelope is 77.0 × 51.0 mm in the neutral XY reference.

This does not represent jaw opening, smile, speech, lip protrusion or other expression-dependent motion.

## Nostril/airway zones

For each nostril, the authority defines:

- center X: ±10.5 mm
- center Y: -7.5 mm
- minimum deformed opening area: 120 mm²
- minimum local opening dimension: 8.0 mm
- required rigid dynamic-airway clearance: 7.5 mm

Iteration 7 constructs a circular analytical opening whose diameter is the larger of:

1. the 8.0 mm minimum local dimension; and
2. the diameter of a circle having area 120 mm².

The clearance is then added outside that analytical opening.

This is a conservative digital reference footprint. It does not prove nostril shape, alar deformation, breathing-state geometry, membrane intrusion behavior or pressure drop.

## Why Z is intentionally unbounded

Every Iteration-7 `ProtectedVolume` has the policy:

`UNBOUNDED_UNTIL_REGISTERED_ANATOMICAL_SURFACE`

That means a point whose XY projection lies inside a protected footprint is treated as excluded regardless of its Z coordinate for current topology/safety-screen purposes.

This is intentionally conservative. Choosing an arbitrary front/back depth would create a false route around the protected zone and could later permit geometry or an outlet to be placed behind a safety boundary that has never actually been measured.

The unbounded policy will be replaced only when a registered anatomical source and explicit dynamic-volume construction justify finite 3D boundaries.

## What can pass now

The repository may report `PROTECTED_ZONE_XY_BASELINES = PASS` when it verifies that:

- all five protected targets exist;
- their centers derive from the semantic facial-reference layer;
- aperture dimensions/minima derive from the authority;
- eye clearance is exactly 8.5 mm;
- mouth clearance is exactly 9.5 mm;
- nostril clearance is exactly 7.5 mm;
- neutral bilateral eye/nostril geometry remains symmetric;
- the Z policy remains unresolved/conservative;
- none of these analytical zones is labeled as anatomical-validation evidence.

## What must remain blocked

The following checks remain blocked after Iteration 7:

- dynamic eye signed distance;
- dynamic mouth signed distance;
- dynamic airway signed distance;
- airway pressure drop;
- compliant intrusion/airway-collapse behavior.

Those require registered anatomy and/or physical/validated simulation evidence.

A successful planar hard-envelope test must never be used as evidence that those dynamic checks have passed.

## Use by later subsystems

Later iterations may use these protected footprints to:

- exclude unsafe outlet locations;
- exclude cleansing/coverage area that is genuinely a safety opening;
- test deterministic worn-pose offsets;
- reserve structural clearance;
- prohibit actuator/membrane features from crossing protected XY footprints while 3D evidence is absent;
- construct regression fixtures.

Any subsystem using the zones must preserve their evidence status and must not reinterpret the 2.5D representation as a measured human volume.

## Replacement rule

When registered headform/face data and dynamic anatomical models become available, the new 3D volumes must retain traceability to:

- source asset/revision/hash;
- registration revision/error;
- expression/breathing state;
- construction algorithm;
- required authority clearance;
- validation status.

Replacing the current analytical zone is a controlled evidence promotion, not a cosmetic CAD edit.
