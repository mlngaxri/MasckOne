# Masck One structural frame topology and datum network

## Scope

Iteration 15 establishes the controlled functional structural-frame skeleton at topology and datum level. It converts the verified interface attachment into a traceable structural reaction loop, defines authority-derived frame datums and reserves downstream subsystem interfaces.

It does not invent a structural member cross-section, material, 3D Z placement, actuator mount, routing geometry, retention mount, deflection result, modal result, fatigue life or physical load capacity.

## Source chain

The topology is bound to the exact Iteration-13 interface-attachment SHA-256 and registered facial-mesh SHA-256. The complete attachment outer-perimeter edge sequence is inherited into the structural perimeter reaction path without duplicate or omitted edges.

This preserves the controlled material boundary and avoids independently redrawing a structural perimeter that could silently diverge from the compliant-interface attachment.

## Functional frame reference

The machine authority provides the `155 x 202 mm` functional-frame XY reference with `DESIGN_BASELINE` status. Iteration 15 uses that reference only to establish the canonical XY mechanical datum network:

- center at X = 0, Y = 0;
- superior reference at Y = +101 mm;
- inferior reference at Y = -101 mm;
- wearer-left reference at X = -77.5 mm;
- wearer-right reference at X = +77.5 mm.

All datum Z coordinates remain unresolved. The current datum network is an authority-derived XY reference, not released 3D member geometry.

## Structural reaction topology

The first controlled load-path object is the closed perimeter reaction loop inherited from the interface attachment. Its purpose is to represent where the future frame must accept interface-capture reactions while preserving separation from the protected eye, mouth and nostril openings.

No beam, rib or ring cross-section is assigned. A false solid frame generated from an arbitrary width or depth would create unsupported stiffness, mass, collision and manufacturing assumptions, so Iteration 15 explicitly rejects that shortcut.

## Reserved downstream interfaces

The topology contains explicit reservation identities for:

- four-zone actuation;
- fresh water and cleanser routing;
- waste acquisition/routing;
- halo/occipital/crown retention;
- HMI and electronics dry-bay integration;
- WARM/COOL thermal-system integration.

Only the actuation interface count is numerically defined, because the four independently controllable zones are frozen architecture. Local positions, envelopes and mount details remain assigned to their downstream iterations.

## Analysis requirements carried forward

The machine-authority structural requirements remain attached to the topology:

- frame deflection p95 <= 0.40 mm, `ENGINEERING_BASELINE`;
- preferred first structural mode > 250 Hz, `VALIDATION_GATED`.

Iteration 15 does not report either requirement as passing. Meaningful structural analysis requires realized member geometry, material properties, boundary conditions, loads and appropriate verification.

## Material and cross-section evidence discipline

`cross_section_dimensions_mm` and `material_selection` remain explicitly unresolved. The data model rejects numeric cross-section insertion or material selection at this stage.

This prevents later calculations from silently treating an arbitrary development section as a mass, stiffness, modal or fatigue truth.

## Evidence boundary

The current structural topology is not physical validation evidence for deflection, vibration, strength, fatigue, retention loads, impact, fit, comfort or durability. It is a deterministic dependency and datum contract that later structural geometry and analysis must consume.
