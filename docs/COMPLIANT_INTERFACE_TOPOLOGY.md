# Masck One — compliant facial-interface topology

## Purpose

Iteration 10 establishes the first controlled representation of the **main compliant skin-contact interface**. It answers a narrow but important engineering question before detailed membrane CAD is attempted:

> Which parts of the facial reference are intended to be compliant cleansing/contact targets, which parts are protected openings, and which parameter families are allowed to govern each region?

The implementation is in `src/masck_one/interface_topology.py` and is derived from the Iteration-9 coverage mesh. It is intentionally a topology and parameterization layer, not a claim that the final membrane shape, material, pressure field or cleansing efficacy has been proven.

## Functional parameter zones

Every coverage triangle is assigned exactly once to one of eight stable interface zones:

1. `INTERFACE_GENERAL_FACE` — general compliant facial cleansing field.
2. `INTERFACE_T_ZONE_FOREHEAD` — forehead portion of the development T-zone.
3. `INTERFACE_T_ZONE_NOSE_PHILTRUM` — central nose/T-zone and nose-to-upper-lip target field.
4. `INTERFACE_OPENING_EYE_LEFT` — left eye protected opening.
5. `INTERFACE_OPENING_EYE_RIGHT` — right eye protected opening.
6. `INTERFACE_OPENING_MOUTH` — mouth protected opening.
7. `INTERFACE_OPENING_NOSTRIL_LEFT` — left nostril/airway protected opening.
8. `INTERFACE_OPENING_NOSTRIL_RIGHT` — right nostril/airway protected opening.

The first three zones have skin-contact/cleansing intent. The five opening zones explicitly have **no interface-material intent** in the protected footprint.

## Nose and upper-lip continuity

The central T-zone assignment inherits the Iteration-9 requirement that the nose-to-upper-lip/philtrum region remains an active cleansing target except where the true nostril and mouth safety exclusions remove material.

This is deliberate: the nostrils are protected airways, but the surrounding external nose, nasal sidewall target field and skin between the nose and upper lip must not silently disappear from the cleansing architecture.

Iteration 10 does **not** yet define the detailed nasal saddle boundary, bridge/dorsum geometry or local aperture-edge transitions. Those are Iterations 11 and 12.

## Thickness discipline

The engineering authority contains one numeric membrane-thickness family that is directly relevant here:

- nasal-lobe center thickness: **0.30 mm**;
- nasal-lobe DOE: **0.25 / 0.30 / 0.35 mm**;
- authority status: validation-gated.

Iteration 10 preserves these values in `NasalLobeThicknessAuthority`, but deliberately does **not** paint 0.30 mm over the entire central T-zone.

That would be an unsupported extrapolation because the authority does not yet define the geometric boundary of the dedicated nasal-lobe subsystem. The numeric nasal thickness therefore remains attached to an explicit application state:

`BOUNDARY_UNRESOLVED_UNTIL_DEDICATED_NASAL_SUBSYSTEM`

The general face and forehead T-zone also remain without invented numeric thickness values. Their material, thickness and stiffness parameters are left unresolved until later interface-geometry/material iterations can close them legitimately.

## Topological invariants

The Iteration-10 builder enforces or verifies:

- every Iteration-9 coverage triangle receives exactly one interface-zone assignment;
- contact intent agrees exactly with cleansing-target intent;
- protected eye, mouth and nostril regions never become contact/cleansing triangles;
- contact area equals the Iteration-9 target area;
- protected-opening area equals the Iteration-9 protected area;
- T-zone contact area equals the Iteration-9 T-zone target area;
- current development contact topology remains one edge-connected field;
- the nose-to-upper-lip target area remains present;
- all topology results receive deterministic SHA-256 identity;
- the topology cannot be promoted to anatomical validation evidence.

## What this iteration proves

It proves that the software/CAD authority now has a deterministic, traceable and regression-tested answer for the **functional topology** of the compliant facial interface.

It prevents several classes of silent CAD error before detailed geometry exists: accidentally covering an airway, omitting the philtrum, dropping a T-zone target, assigning the same region twice, creating a disconnected contact island, or applying an authority value outside its defined subsystem.

## What this iteration does not prove

Iteration 10 does not prove:

- fit on human faces;
- final 3D facial conformity;
- facial pressure;
- membrane strain;
- friction;
- local stiffness;
- silicone/material selection;
- seal performance;
- ingress protection;
- cleansing efficacy;
- actuation efficiency;
- long-term durability or hygiene.

Those remain downstream digital and physical evidence gates.
