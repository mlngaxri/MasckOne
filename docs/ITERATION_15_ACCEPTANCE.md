# Iteration 15 acceptance record

## Scope

Iteration 15 establishes the functional structural-frame topology and mechanical datum network without inventing unsupported member geometry or material properties.

## Required acceptance conditions

Promotion requires the exact pull-request head to pass authority validation, repository and prior subsystem preflights, the Iteration-15 structural-frame preflight, the complete unit/integration suite and deterministic CAD smoke generation.

The structural topology must also satisfy:

- exact binding to the verified Iteration-13 attachment topology and registered facial mesh;
- exact inheritance of every attachment outer-perimeter edge into the perimeter structural reaction loop;
- functional-frame XY reference and status read directly from machine authority;
- center, superior, inferior, wearer-left and wearer-right mechanical datum identities derived deterministically from the authority frame reference;
- unsupported datum Z coordinates remain unresolved;
- explicit reservations for actuation, fresh fluid, waste, retention, HMI/electronics and thermal systems;
- actuation reservation preserves exactly four independent zones without inventing local mounts;
- authority frame-deflection and preferred first-mode requirements are carried with their existing statuses and not reported as passing;
- frame cross-section dimensions remain unresolved;
- frame material remains unselected;
- physical-validation eligibility remains false.

## Deliberately not attempted

Iteration 15 does not create arbitrary solid structural members merely to make the CAD look complete. Member widths/depths, local ribs, material, 3D Z placement, actuator mounts, tubing clips, retention joints and electronics mounts require downstream packaging and engineering evidence.

The current output is therefore a structural topology and datum release, not a final frame solid.

## Downstream use

Iteration 16 must keep engineering packaging and exterior-surface authority separate. Iterations 17 and 18 will resolve actuator local frames, mounts, coupling and swept volumes against this structural framework. Later DFM and automatic mass/CG iterations must not infer mass or stiffness until realized frame geometry and material data exist.
