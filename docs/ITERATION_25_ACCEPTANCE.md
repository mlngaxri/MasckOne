# Iteration 25 acceptance

## Scope

Facial waste gutters, capillary-path intent, and regional transient-buffer topology.

## Controlled result

The digital architecture defines five canonical acquisition regions and gives every region the same explicit mixed-phase semantics: air, liquid, foam, and contaminant. Every region terminates at the Iteration 26 waste-pump inlet interface and is classified `WET_DRAINABLE` for downstream hygiene/service design.

The current authority recovery minimum of 0.90 and residual-free-liquid maximum of 400 uL are carried only as validation-gated requirements. They are not measured results.

## Deliberately unresolved

Gutter width/depth/cross-section, capillary feature geometry, transient-buffer capacity, registered skin-facing paths, suction pressure, pressure loss, orientation response, foam handling, contaminant tolerance, recovery ratio, residual liquid, drain/dry time, leakage, cleanability, service burden, and physical performance remain unresolved pending registered geometry and mixed-phase bench evidence.

## Evidence firewall

The architecture rejects invented dimensions/capacity, incomplete or reordered region sets, mutable region containers, uncontrolled phase/service/evidence states, physical-evidence promotion, non-finite or boolean numeric aliases, and hostile string subclasses at controlled boundaries. Manifest generation revalidates each nested region and the architecture itself, so post-construction corruption cannot silently mint a new trusted provenance hash. The waste phase is never simplified to liquid-only flow.

## Provenance/current-source contract

Iteration 25 does not trust a mutually consistent caller-supplied hash graph as proof of currentness. `validate_iteration25_source_graph()` first requires the supplied `Authority` data and validation provenance to match a fresh load of the repository machine authority and repository schema. It then recursively reconstructs every supplied Iteration 15/20-24 dataclass graph so constructor invariants are re-run after any possible post-construction mutation.

A deterministic canonical source graph is rebuilt from that freshly validated repository authority: planar development surface -> protected volumes and coverage -> compliant-interface boundary release -> attachment -> structural frame -> water and cleanser storage -> fresh pump packaging -> distribution manifold -> Iteration 24 distribution geometry. The supplied water, cleanser, frame, pump, manifold, coverage, protected-volume and distribution objects must match that canonical runtime graph recursively, including exact nested dataclass, container, scalar types and values. Serialized-manifest equality alone is not accepted because it can erase runtime type distinctions.

The only supported extension is controlled cleanser compatibility evidence, which is reconstructed through the existing `with_compatibility_evidence()` path and remains `EVIDENCE_ATTACHED_REQUIRES_ENGINEERING_REVIEW`; it cannot auto-promote physical validation.

This closes the Iteration 25 boundary against post-construction corruption, same-value runtime aliases, a fully self-consistent graph rebuilt from mutated in-memory authority data, and an old internally consistent source graph presented alongside the current live authority. It does not make the repository-wide `Authority` class globally immutable for unrelated consumers. Instead, this Cell 4 boundary refuses to trust an in-memory authority object unless it still matches the freshly loaded repository source exactly.

The architecture also retains the direct Iteration 24 SHA, authority revision, validation-gated recovery requirement, and residual-liquid requirement checks as defense in depth.

## Downstream contract

Iteration 26 may consume the canonical region identities, mixed-phase semantics, hygiene class, unresolved geometry/buffer states, waste-pump destination, and the exact Iteration 25 architecture SHA only after the canonical repository-rooted source-graph gate and exact-head release tests pass. It may not infer pump pressure/flow, tubing dimensions, buffer capacity, recovery, leakage, orientation independence, hygiene performance, or cleansing efficacy from this topology.

The current canonical gate intentionally authenticates the released planar-development engineering lineage. A future registered-anatomy or supplier-evidence lineage requires its own explicit released provenance contract; it may not be substituted merely because local hashes agree.