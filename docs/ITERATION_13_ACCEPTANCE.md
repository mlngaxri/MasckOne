# Iteration 13 acceptance record

## Scope

Iteration 13 establishes the interface-to-structural-frame attachment/clamp architecture at the deterministic topology and role level.

## Required acceptance conditions

The iteration is eligible for promotion only when all applicable conditions below pass on the exact pull-request head:

- authority schema and semantic validation passes;
- repository preflight passes;
- Iteration-11 nasal preflight passes;
- Iteration-12 interface-boundary preflight passes;
- Iteration-13 attachment preflight passes;
- the complete unit/integration test suite passes;
- deterministic CAD smoke generation passes;
- every verified physical outer-perimeter edge maps exactly once into the attachment architecture;
- attachment source hashes match the exact verified upstream boundary and registered mesh;
- path length is conserved from the source boundary;
- protected eye, mouth and nostril boundaries are not repurposed as structural attachment paths;
- the only structural-frame dimensional reference carried forward is the authority functional-frame baseline;
- structural-frame topology remains explicitly deferred to Iteration 15;
- clamp width, capture depth, preload, fastener count, fastener pitch, interface compression and retention-member material remain unresolved rather than guessed;
- physical-validation eligibility remains false;
- seal, retention-load, durability, assembly, fit, pressure, ingress, anatomy and cleansing-efficacy gates remain unpromoted.

## Architecture decision

The controlled development architecture is mechanical perimeter capture represented by three explicit roles: future structural-frame side, compliant-interface perimeter, and abstract retention-member side.

This is an architecture candidate, not a production component freeze. It selects the topology of the interface-to-frame relationship without pretending that downstream structural geometry, material behavior, compression, preload, fastening or manufacturing decisions are already known.

## Deliberately not attempted

Iteration 13 does not define final clamp geometry, seals, adhesives, fasteners, compression, preload, retention force, fatigue life, final materials, assembly tooling, frame topology, compliant contact behavior or human-fit performance.

## Downstream dependencies

Iteration 14 consumes the interface architecture when creating the evidence-gated nonlinear membrane/contact simulation framework.

Iteration 15 consumes the attachment roles and authority frame reference when creating the actual structural-frame topology and load-path datum network.

Later assembly, DFM, hygiene and physical validation iterations must convert the current unresolved attachment quantities into evidence-backed decisions before production release.
