# Masck One Phase 2 Iteration 12 engineering record

## Objective

Close the digital topology of the compliant-interface perimeter and protected-aperture transitions without inventing seal dimensions, material behavior or anatomical fit evidence.

## Upstream dependencies

Iteration 12 depends on the merged outputs of:

- Iteration 6 neutral facial surface;
- Iteration 7 protected eye, mouth and airway regions;
- Iteration 9 target/protected coverage segmentation;
- Iteration 10 compliant-interface contact topology;
- Iteration 11 dedicated nasal subsystem topology.

The new topology records the exact source hashes of the facial surface, coverage segmentation and compliant-interface topology so stale combinations cannot be silently mixed.

## Implementation

`src/masck_one/interface_boundaries.py` constructs the six controlled edge systems from mesh incidence rather than drawing new unsupported geometry.

The outer boundary is defined by a development-mesh edge with exactly one incident active contact triangle. Protected-aperture boundaries are defined only by an edge shared by one active contact triangle and one protected triangle belonging to the expected eye, mouth or nostril region.

Each boundary must be one closed connected loop. Edge identity, incident triangles, edge lengths and source hashes are included in the deterministic topology manifest and SHA-256 identity.

## Authority discipline

The current authority contains no numeric compliant seal/transition width and no general interface thickness. Iteration 12 therefore leaves these values explicitly unresolved and rejects numeric assignment in the boundary-definition data model.

The authority does define a 3.0 mm eye inner-edge roll radius. This is preserved only as a rigid eye-edge design reference. It is deliberately not converted into compliant-interface width, thickness, compression or pressure geometry.

## Validation boundary

The new data represents deterministic development topology only. It cannot satisfy real seal, ingress, fit, pressure, strain, comfort, material or anatomical validation gates.

## Verification introduced

Iteration 12 adds:

- source-chain/hash verification;
- six-boundary completeness verification;
- one-closed-loop-per-boundary verification;
- contact/protected edge semantic verification;
- no-unsupported-dimension regression tests;
- rigid-eye-roll-reference regression tests;
- sagittal eye/nostril boundary symmetry checks;
- deterministic topology hash checks;
- model/public API/build-manifest integration;
- a dedicated `masck_one.boundary_preflight` CI gate.

## Downstream handoff

Iteration 13 can now define the interface-to-structural-frame attachment/clamp architecture against explicit outer and protected-aperture edge identities. Actual seal/compliance profiles remain evidence-gated for later geometry/material/contact iterations.
