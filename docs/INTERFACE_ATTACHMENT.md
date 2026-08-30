# Masck One interface-to-structural-frame attachment architecture

## Scope

Iteration 13 establishes the controlled architectural boundary between the compliant facial interface and the future structural frame. It does not define production clamp geometry, a final retention member, adhesive chemistry, compression, preload, fasteners, material selection, durability, sealing performance, or a validated load path.

The implementation is intentionally source-bound to the exact verified Iteration-12 outer material boundary. The attachment contract therefore inherits the verified interface perimeter instead of recreating or approximating it from independent dimensions.

## Source chain

The attachment architecture records and hashes:

- the Iteration-12 interface-boundary topology SHA-256;
- the registered facial mesh SHA-256;
- the registered facial-surface revision;
- the authority-backed functional-frame XY reference and its status.

Any future change to the registered surface or verified interface boundary requires regeneration of the attachment architecture. This prevents stale attachment definitions from remaining apparently valid after upstream geometry changes.

## Mechanical architecture

The current development architecture is a three-role perimeter capture:

1. `ATTACHMENT_LAYER_STRUCTURAL_FRAME_SIDE`, the future structural reaction side. Iteration 13 does not create the structural frame itself; that dependency remains assigned to Iteration 15.
2. `ATTACHMENT_LAYER_COMPLIANT_INTERFACE_PERIMETER`, the exact compliant-interface outer material perimeter inherited from Iteration 12.
3. `ATTACHMENT_LAYER_RETENTION_MEMBER_SIDE`, an abstract mechanical retention role completing the capture stack. It is not a released component and has no selected material or final fastening strategy.

Every physical outer-perimeter edge is assigned exactly once. Edge indices, vertex pairs and path lengths are preserved from the verified source boundary. The architecture must remain a single closed perimeter capture and cannot consume eye, mouth or nostril protected-aperture boundaries as structural attachment paths.

## Explicitly unresolved quantities

The following values remain `None` by design and any numeric insertion is rejected by the Iteration-13 architecture until a controlled authority or downstream engineering decision supplies evidence:

- clamp-band width;
- capture depth;
- interface preload;
- fastener count;
- fastener pitch;
- interface compression percentage;
- retention-member material.

This is deliberate. The authority does not yet justify those quantities and the Iteration-15 structural frame, Iteration-14 contact framework, later material characterization and later assembly/DFM work are required before physical dimensions and loads can be promoted responsibly.

## Structural-frame dependency

The authority functional-frame reference remains `155 x 202 mm` with `DESIGN_BASELINE` status. Iteration 13 may carry that reference for dependency planning, but it must not treat it as an already-authored structural frame. The actual frame topology, datums and load paths are an Iteration-15 responsibility.

## Seal and retention distinction

The outer perimeter has a future sealing function and a structural retention function, but they are not treated as the same requirement. A mechanically captured interface does not by itself prove:

- fluid sealing;
- air or liquid ingress performance;
- compliant pressure distribution;
- sufficient retention force;
- durability;
- service life;
- manufacturing repeatability.

Those remain separate physical and downstream digital evidence gates.

## Evidence status

The Iteration-13 output is a deterministic digital attachment-topology architecture only. It is not eligible as physical validation evidence for seal performance, structural retention, load transfer, fatigue, durability, assembly performance, fit, pressure, ingress or cleansing efficacy.

## Verification

The dedicated attachment preflight verifies:

- exact source-chain binding;
- exact one-to-one outer-perimeter mapping;
- perimeter path-length conservation;
- authority-backed functional-frame reference use;
- complete controlled layer-role ordering;
- absence of invented dimensions, loads, fasteners or materials;
- explicit deferral of structural-frame topology to Iteration 15;
- preservation of the physical-evidence boundary.

The unit/adversarial tests additionally reject unsourced clamp dimensions, arbitrary fastener counts, unsourced retention materials and corrupted source topology that removes the verified outer perimeter.
