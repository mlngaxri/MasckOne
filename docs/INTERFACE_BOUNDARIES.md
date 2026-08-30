# Masck One interface perimeter and protected-aperture transitions

## Purpose

Iteration 12 establishes controlled material/no-material edge topology for the compliant facial interface. It identifies where the active contact field terminates at the outer perimeter and where it transitions into protected eye, mouth and nostril regions.

This is an edge-topology and functional-intent layer. It does not define final seal width, transition width, compression, general membrane thickness, material, stiffness, pressure, ingress performance or 3D anatomical conformity because the current engineering authority does not support freezing those properties.

## Provenance partitions and physical boundaries

Six source-region provenance labels are retained:

1. `INTERFACE_BOUNDARY_OUTER_PERIMETER`
2. `INTERFACE_BOUNDARY_EYE_LEFT`
3. `INTERFACE_BOUNDARY_EYE_RIGHT`
4. `INTERFACE_BOUNDARY_MOUTH`
5. `INTERFACE_BOUNDARY_NOSTRIL_LEFT`
6. `INTERFACE_BOUNDARY_NOSTRIL_RIGHT`

These labels identify which protected-region triangle lies on the non-contact side of each transition edge. They are not assumed to be six separate physical loops.

The conservative left/right eye protected regions overlap across the sagittal plane, and the left/right nostril protected regions overlap as well. Their labelled edge chains are therefore provenance partitions of larger physical boundaries. Physical closure is evaluated on four systems:

- outer interface perimeter;
- bilateral eye protected union;
- mouth protected opening;
- bilateral nostril/airway protected union.

This distinction prevents an implementation artifact, region labelling, from being mistaken for material topology.

## Edge semantics

Outer-perimeter edges have exactly one incident active contact triangle. Protected-aperture transition edges have one active contact triangle and one protected triangle. Each edge keeps its deterministic vertex pair, incident triangle IDs, contact triangle ID and protected triangle ID.

The release manifest exports those edge identities plus both provenance and physical-boundary IDs, so downstream tooling can reconstruct and independently verify the digital transition topology.

## Registered-mesh source binding

The facial-surface descriptor source SHA identifies the source artifact. Different registrations of the same asset may therefore share that source SHA. Iteration 12 separately records the registered mesh SHA and registration revision.

The controlled release path also checks the coverage triangle identities and centroids against the current registered mesh. Coverage generated from another registration of the same source asset is rejected. The comparison tolerance is a numerical software-identity budget only, not a product or manufacturing tolerance.

## Dimension authority discipline

The authority does not define a numeric compliant perimeter seal width, protected-aperture transition width or general interface thickness. Boundary definitions therefore retain unresolved values, with material selection and physical behavior validation gated to later work. Unsupported numeric transition width or general interface thickness is rejected.

The authority eye inner-edge roll radius is preserved on the eye provenance definitions only as a rigid-edge design reference. It is not used as a compliant membrane roll radius, seal width, membrane thickness or contact-pressure parameter. No analogous roll radius is invented for mouth or nostril transitions.

## Digital invariants

The controlled Iteration-12 path requires:

- all six provenance partitions to remain present;
- all four physical material/no-material boundary systems to be present and each form one closed connected loop;
- every aperture transition edge to retain exact contact/protected source-region semantics;
- no mesh edge to be assigned to multiple provenance boundaries;
- no protected region to reach the outer development perimeter unexpectedly;
- registered-mesh and registration-revision provenance to remain explicit;
- left/right provenance discretizations to remain sagittally balanced on the neutral development surface;
- deterministic SHA-256 identification;
- no promotion to anatomical or physical validation evidence.

## Evidence boundary

Iteration 12 does not prove seal effectiveness, liquid-ingress protection, facial fit, pressure distribution, membrane strain, comfort, compression set, material compatibility, final edge profiles, 3D anatomical conformity, airway performance or cleansing efficacy. Those remain downstream simulation and physical-evidence gates.
