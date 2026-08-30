# Phase 2 Iteration 12: perimeter and protected-aperture transitions

## Scope

Iteration 12 establishes deterministic material/no-material edge topology for the compliant facial interface. It does not define a seal width, transition profile, general membrane thickness, compression target, material model, contact pressure, ingress performance, fit performance or cleansing efficacy.

## Upstream baseline

This iteration is built from the verified Iteration 11A mainline state. The earlier Iteration 12 candidate was not reused as a merge base because it diverged before Iteration 11A and would have regressed the merged CAD thickness-verification hardening.

## Boundary decomposition

The coverage mesh retains six source-region provenance partitions: outer perimeter, left eye, right eye, mouth, left nostril and right nostril. Those labels are useful because each transition edge can still identify the exact protected-region triangle on its non-contact side.

They are not six independent physical boundaries. The conservative left/right eye protected envelopes overlap across the sagittal plane, and the conservative left/right nostril envelopes overlap as well. Requiring each labelled partition to form its own closed loop is therefore a decomposition error.

Physical loop integrity is evaluated on four systems:

1. outer interface perimeter;
2. bilateral eye protected union;
3. mouth protected opening;
4. bilateral nostril/airway protected union.

All six provenance partitions remain explicit, but only the four physical systems are required to be single closed edge loops.

## Source-chain hardening

The facial-surface descriptor source SHA identifies the original source artifact. A registered external surface can therefore share that source SHA with another rigid registration of the same asset. Iteration 12 records the registered mesh SHA and registration revision separately.

The controlled release path additionally verifies the coverage triangle identities and centroids against the current registered mesh. A stale coverage revision from another registration of the same source asset is rejected. The numerical centroid comparison budget is a software identity check only, not a manufacturing or physical tolerance.

## Release manifest

The build report exports each interface-boundary edge record, including:

- deterministic edge index;
- source-region boundary ID;
- physical-boundary ID;
- vertex pair;
- incident triangle IDs;
- contact triangle ID;
- protected triangle ID where applicable;
- edge length.

This makes the exported topology reconstructable rather than exposing only aggregate counts and lengths.

## Authority discipline

The authority does not currently provide a compliant seal width, edge-transition width, general interface thickness, compression profile or material constitutive behavior. Those fields remain unresolved. Numeric insertion is rejected.

The existing eye inner-edge roll radius is retained only as a rigid-edge design reference. It is explicitly not promoted to compliant seal/profile geometry.

## Evidence gates left open

Digital closure of this iteration does not close seal performance, fluid ingress, facial fit, pressure distribution, membrane strain, durability, hygiene, airway performance, anatomical validation or cleansing efficacy. Those require the later material, simulation and physical-evidence iterations in the controlled roadmap.
