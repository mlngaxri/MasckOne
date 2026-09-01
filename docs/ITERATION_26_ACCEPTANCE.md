# Iteration 26 acceptance

## Scope

Mixed-phase waste-pump packaging reservation, pump-stage routing interfaces, and explicit fault-state architecture.

## Controlled result

Iteration 26 introduces one canonical waste-pump station bound to the exact Iteration 25 waste-acquisition architecture and the structural frame's `FRAME_RESERVATION_WASTE_ROUTING` reservation. The station preserves the Iteration 25 `MIXED_AIR_LIQUID_FOAM_CONTAMINANT` phase semantics from the acquisition handoff through the pump stage.

Two controlled routing interfaces are defined: the Iteration 25 acquisition-to-pump boundary and a downstream handoff reserved for Iteration 27 cartridge architecture. The downstream interface does not define cartridge insertion, sealing, retained capacity, service geometry, or internal cartridge topology.

The architecture also defines the complete Iteration 26 pump-stage fault registry for power loss/pump-off, stall/no-motion, gas ingestion, liquid slugging, foam ingestion, contaminant ingestion, upstream occlusion, downstream occlusion, backflow risk, and protected-region pooling risk. Detection, mitigation implementation, and physical validation remain explicitly unresolved or validation-gated. A fault record cannot be interpreted as proof of successful recovery or containment.

The authority recovery minimum of 0.90 and residual-free-liquid maximum of 400 uL remain carried as validation-gated requirements only. Iteration 26 does not convert them into measured pump performance.

## Deliberately unresolved

Pump supplier/component selection, pump principle, package envelope, placement, orientation, tubing inner diameter, bend radius, connector standard, mixed-phase flow rate, suction pressure, pressure loss, power, acoustics, priming behavior, foam tolerance, contaminant tolerance, gas handling, liquid-slug handling, orientation response, leakage, recovery ratio, residual free liquid, backflow performance, fault sensing, control implementation, drain/dry behavior, service trajectory, cleanability, hygiene performance, durability, and physical performance remain unresolved pending controlled geometry, supplier evidence, downstream architecture, and mixed-phase bench evidence.

## Evidence firewall

The architecture rejects invented package/routing/hydraulic values, incorrect or aliased stage interfaces, incomplete/reordered/mutable route and fault sets, physical-evidence promotion, non-finite or boolean numeric aliases, hostile string subclasses at controlled identity/status boundaries, stale Iteration 25 sources, stale authority requirements, and stale structural-frame reservations. Manifest generation revalidates the station, routes, faults, and architecture before minting a deterministic provenance hash.

## Provenance/current-source contract

Iteration 26 binds the exact Iteration 25 architecture SHA, structural-frame topology SHA, authority revision, recovery requirement, and residual-liquid requirement. Current-source validation revalidates the Iteration 25 architecture against its Iteration 24 distribution dependency and current authority before accepting the Iteration 26 snapshot.

## Downstream contract

Iteration 27 may consume the canonical waste-pump outlet interface, mixed-phase semantics, exact Iteration 26 architecture SHA, and validation-gated waste requirements. It may not infer pump package geometry, pressure/flow capability, recovery, leakage, backflow performance, fault-detection coverage, or containment performance from this digital architecture.
