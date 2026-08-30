# Masck One interface perimeter and protected-aperture transitions

## Purpose

Iteration 12 establishes the controlled edge topology for the compliant facial interface. It identifies where the contact field terminates at the outer perimeter and where it transitions to the protected eye, mouth and nostril openings.

This is an edge-topology and functional-intent layer. It does not define final seal width, transition width, compression, membrane thickness, material, stiffness, pressure, ingress performance or 3D anatomical conformity because the current engineering authority does not provide evidence sufficient to freeze those properties.

## Controlled boundary set

Six boundary systems are extracted directly from the exact Iteration-10/11 development surface and interface segmentation:

1. `INTERFACE_BOUNDARY_OUTER_PERIMETER`
2. `INTERFACE_BOUNDARY_EYE_LEFT`
3. `INTERFACE_BOUNDARY_EYE_RIGHT`
4. `INTERFACE_BOUNDARY_MOUTH`
5. `INTERFACE_BOUNDARY_NOSTRIL_LEFT`
6. `INTERFACE_BOUNDARY_NOSTRIL_RIGHT`

The outer perimeter consists of mesh edges incident to one active contact triangle. Each protected-aperture transition consists only of edges shared by one contact triangle and one protected triangle of the corresponding eye, mouth or nostril region.

## Functional intent

The outer perimeter carries compliant-interface and fluid-containment intent. Protected-aperture boundaries carry compliance, fluid-exclusion/containment and protected-opening exclusion intent.

These are architectural intents, not measured seal-performance claims. A later interface geometry/material iteration must determine the actual width, profile, compression and constitutive behavior needed to deliver those functions.

## Dimension authority discipline

The current authority does not define a numeric compliant perimeter seal width, protected-aperture transition width, or general interface thickness. All six boundary definitions therefore carry:

- `nominal_transition_width_mm = None`
- `nominal_interface_thickness_mm = None`
- `material_status = UNSELECTED_VALIDATION_GATED`
- `geometry_status = EDGE_TOPOLOGY_ONLY_WIDTH_PROFILE_AND_3D_CONFORMITY_UNRESOLVED`

Iteration 12 explicitly rejects attempts to insert an unsupported numeric transition width or interface thickness into the boundary-definition object.

## Eye inner-edge roll reference

The engineering authority contains a 3.0 mm eye inner-edge roll radius. Iteration 12 preserves this value on the left and right eye transition definitions only as:

`RIGID_EYE_INNER_EDGE_DESIGN_BASELINE_REFERENCE_NOT_COMPLIANT_PROFILE`

It is not used as a compliant membrane roll radius, seal width, thickness or contact-pressure parameter.

No analogous roll radius is defined by the authority for mouth or nostril transitions, so none is invented.

## Topological invariants

The builder verifies that:

- all six boundary systems are present;
- each boundary is one closed edge loop on the current development mesh;
- no mesh edge is assigned to more than one controlled boundary;
- every protected-aperture edge separates exactly one active contact triangle from exactly one protected triangle;
- protected-region identity matches the boundary definition;
- no protected region reaches the outer development perimeter unexpectedly;
- the source surface, coverage segmentation and compliant-interface topology hashes are preserved;
- neutral left/right eye and nostril transition discretizations remain sagittally balanced;
- the result receives a deterministic SHA-256 identity;
- the topology cannot be promoted to anatomical validation evidence.

## What this iteration proves

It proves that downstream CAD now has a deterministic answer to where the compliant field must terminate or transition around the face on the current development reference. It prevents later geometry from silently bridging an eye, mouth or nostril protected opening, losing a perimeter segment, or introducing an unsupported seal dimension as if it were authoritative.

## What this iteration does not prove

Iteration 12 does not prove:

- seal effectiveness;
- liquid ingress protection;
- facial fit;
- pressure distribution;
- local membrane strain;
- comfort;
- compression set;
- material compatibility;
- final aperture-edge profile;
- final perimeter profile;
- 3D anatomical conformity;
- cleansing efficacy.

Those remain downstream digital and physical evidence gates.
