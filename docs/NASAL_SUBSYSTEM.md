# Masck One — dedicated nasal subsystem development topology

## Purpose

Iteration 11 establishes the first controlled **dedicated nasal subsystem** beneath the broader compliant-interface topology created in Iteration 10.

The purpose is not to claim a final anatomical nose surface. The current neutral facial surface is still a planar development reference and therefore cannot establish real bridge height, dorsum curvature, alar deformation, nostril motion, nasal-sidewall conformity or fit pressure.

Instead, this iteration closes a narrower but essential design-control problem:

> The external nose and nose-to-upper-lip region must remain explicit cleansing targets, the true nostril/airway protected areas must remain excluded, and the authority's local nasal-lobe thickness must not silently spread into bridge, dorsum, sidewall or philtrum regions whose thickness is not yet supported.

Implementation: `src/masck_one/nasal_subsystem.py`.

## Five controlled functional roles

Every active triangle in the Iteration-9/10 central nose/philtrum target field is assigned exactly once to one of five stable functional roles:

- `NASAL_BRIDGE_DORSUM`
- `NASAL_SIDEWALL_LEFT`
- `NASAL_SIDEWALL_RIGHT`
- `NASAL_LOBE`
- `NASAL_PHILTRUM`

All five are cleansing/contact-intent roles. Protected nostril triangles are not part of this role partition at all; they remain controlled by the protected-volume layer.

The role partition must conserve the complete central T-zone target area and must not duplicate or omit a triangle.

## Development-boundary derivation

No freehand anatomical dimensions are introduced.

The current role boundaries are derived only from existing controlled geometry:

- the central T-zone stem bounds from the Iteration-9 coverage definition;
- the authority-derived left/right nostril centers;
- the conservative nostril protected-envelope dimensions;
- the neutral sagittal symmetry baseline.

The lobe development Y band is bounded by the superior/inferior extent of the existing conservative nostril envelopes, clipped to the T-zone stem. Its development half-width is limited by the same existing central stem/protected-envelope geometry.

The bridge/dorsum development half-width is anchored directly to the authority-defined nostril-center spacing: the central band extends from the sagittal plane to the left/right nostril centerlines. This is a deterministic CAD-development partition, **not** a statement that the anatomical dorsum has this width.

Above the lobe band, triangles inside that central band are assigned to bridge/dorsum; remaining left/right triangles become sidewalls. Below the lobe band, remaining central-target triangles become the philtrum role.

This priority produces a complete, non-overlapping functional partition while preserving the evidence boundary.

## Thickness localization

The engineering authority supplies:

- nasal-lobe center thickness: **0.30 mm**;
- nasal-lobe DOE: **0.25 / 0.30 / 0.35 mm**;
- status: validation-gated.

Iteration 10 correctly preserved those values without assigning them to the entire central T-zone. Iteration 11 now gives them an explicit development application boundary: **only `NASAL_LOBE` carries the numeric thickness family.**

The following roles intentionally remain numerically unresolved:

- bridge/dorsum;
- left sidewall;
- right sidewall;
- philtrum.

Assigning `0.30 mm` to any of those regions would be an unsupported extrapolation and is rejected by tests/assertions.

## Correction to the legacy nasal CAD placeholder

Before Iteration 11, the code generated a broad trapezoidal nasal saddle and extruded the entire shape at `0.30 mm`. That geometry was a useful early placeholder, but once the interface authority became more explicit it created an inconsistency: a local nasal-lobe thickness was visually and geometrically applied to regions whose thickness had never been established.

Iteration 11 removes that ambiguity.

The generated `nasal_interface` model field now contains a component named:

`nasal_lobe_membrane_reference`

Its status is:

`DEVELOPMENT_LOCAL_THICKNESS_REFERENCE`

The solid is limited to the derived lobe development band, uses the authority-backed `0.30 mm` local thickness, and subtracts the **full conservative nostril protected footprints** rather than merely cutting the smaller nominal airway circles.

This is still a development reference, not the final 3D conforming silicone membrane.

## Airway and nostril safety separation

The nasal role builder consumes only triangles that are already active targets in the coverage layer. Because the coverage layer excludes protected nostril footprints, a protected airway triangle cannot be reintroduced by the nasal subsystem.

The Iteration-11 preflight checks this explicitly.

This does not close dynamic airway safety. The following still require later geometry and physical evidence:

- deformed nostril area under load;
- local minimum airway dimension under load;
- dynamic signed distance under worn pose;
- no-collapse behavior at the authority test flow;
- pressure drop at 30/60 L/min;
- liquid ingress under fault conditions;
- nasal-sidewall conformity and pressure.

## Philtrum continuity

The skin between the external nose and upper lip remains an explicit cleansing/contact target through `NASAL_PHILTRUM`.

The role is generated from central target triangles below the derived lobe band and above the existing mouth-protected boundary. It therefore cannot silently vanish merely because the nearby nostril and mouth regions are safety exclusions.

## Determinism and provenance

The nasal topology stores SHA-256 references to:

- the source facial surface;
- the coverage segmentation;
- the compliant-interface topology.

The complete role definitions, derived boundaries and triangle assignments produce their own deterministic `topology_sha256`.

A topology generated from a different upstream surface/coverage/interface pair is rejected rather than treated as equivalent.

## CAD versus anatomy

Iteration 11 distinguishes three things that must not be conflated:

1. **Functional role topology** — digitally deterministic now.
2. **Local lobe-thickness development reference** — digitally deterministic now from authority.
3. **Final conforming nasal membrane geometry and behavior** — still unresolved and evidence-gated.

The development topology has `anatomical_validation_eligible = false`.

It cannot close fit, pressure, strain, airflow or cleansing efficacy by itself.

## Acceptance invariants

Iteration 11 is acceptable only if:

- every central nose/philtrum target triangle is assigned exactly once;
- the coverage and interface central-target triangle sets are identical;
- total nasal-role area equals the central target area;
- all five roles have non-zero development area;
- left/right sidewall areas remain sagittally balanced on the neutral symmetric baseline;
- no protected nostril triangle enters a nasal contact role;
- the philtrum role remains non-empty;
- only `NASAL_LOBE` receives the `0.30 mm` / `0.25–0.35 mm` numeric thickness authority;
- bridge/dorsum, sidewalls and philtrum remain without invented numeric thickness;
- generated lobe reference CAD has `0.30 mm` Z thickness and is explicitly development-only;
- source hashes and topology hash remain deterministic;
- existing upstream authority, preflight, tests and CAD assertions continue to pass;
- dynamic airway, pressure, strain and efficacy checks remain blocked until their real evidence exists.

## What comes next

Iteration 12 will add the perimeter interface/seal/compliance zones and the transitions around protected apertures. That work must consume this dedicated nasal topology rather than recreate nose/philtrum semantics independently.
