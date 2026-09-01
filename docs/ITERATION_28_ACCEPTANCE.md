# Iteration 28 acceptance

## Scope

Complete fresh/waste operational interface routing ledger with explicit bend-radius, dead-volume and service-clearance check states.

## Controlled result

Iteration 28 closes the current digital fluid interface graph without inventing physical route geometry. The ledger contains 62 unique controlled operational segments: 54 fresh-fluid segments and 8 mixed-waste segments.

The fresh-fluid ledger covers both source-to-pump paths, both pump-to-manifold paths, both manifold branch interiors, all 24 branch-to-outlet paths and all 24 outlet-to-skin-facing-groove handoffs. Water and cleanser identities remain isolated throughout the graph.

The waste ledger covers all five regional acquisition paths into the controlled waste-pump inlet, the acquisition-to-pump stage, the pump-to-cartridge handoff and the cartridge-inlet-to-retention-region path. Mixed air/liquid/foam/contaminant semantics are preserved throughout the waste graph.

The clean-cycle maximum initial prime value of 0.40 mL is carried only as a `VALIDATION_GATED` requirement. It is not interpreted as measured or computed route dead volume.

## Quantitative check result

Digital topology continuity is confirmed for every ledger segment. Quantitative routing closure is not yet possible because the upstream architecture intentionally does not contain the geometry required to calculate it.

For every segment, centerline length, internal diameter, minimum bend-radius specification, realized minimum bend radius, dead volume and service clearance remain unset. Bend-radius checks are blocked pending controlled centerlines, tubing selection and supplier bend specifications. Dead-volume checks are blocked pending centerline length and internal cross-section geometry. Service-clearance checks are blocked pending complete 3D assembly geometry, service trajectories and deformation envelopes.

This blocked state is the correct engineering result. It must not be rewritten as a pass, fail or estimated numerical value.

## Evidence firewall

Iteration 28 rejects invented route dimensions or volumes, fabricated quantitative passes, crossed or aliased interfaces, missing/reordered/mutable/duplicated segment ledgers, stale upstream architecture hashes, stale authority revision or prime requirement, mixed fresh/waste identities, non-finite or boolean numeric aliases, hostile string subclasses and post-construction corruption.

No digital route record can be promoted to physical validation evidence.

## Provenance/current-source contract

Current-source validation revalidates the complete fresh chain through water storage, cleanser storage, fresh pumps, manifold and Iteration 24 distribution geometry, including coverage/protected-volume dependencies. It separately revalidates the waste chain through Iterations 25, 26 and 27. The exact source SHAs for fresh pump, manifold, distribution, waste acquisition, waste pump, waste cartridge and structural frame are bound into the Iteration 28 manifest.

## Downstream contract

Iteration 29 may rely on the fact that the current digital fluid interface graph is complete and identity-consistent. It may not infer route packaging clearance, bend-radius compliance, dead volume, prime performance, pressure loss, leakage, recovery, serviceability or physical fit. Retention geometry must continue to respect the fresh/waste frame reservations until realized route geometry closes those blocked checks.
