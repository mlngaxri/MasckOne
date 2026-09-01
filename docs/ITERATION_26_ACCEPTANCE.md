# Iteration 26 acceptance

## Scope

Mixed-phase waste-pump packaging reservation, pump-stage routing topology, passive backflow boundary, and fault-state architecture.

## Controlled result

The digital architecture consumes the exact Iteration 25 waste-acquisition architecture SHA and the structural-frame waste-routing reservation. Five canonical regional acquisition paths remain explicitly mixed-phase, each passes through its regional transient-buffer identity and terminates at one controlled pump-inlet node. The pump stage exposes one distinct outlet node, then requires a passive backflow barrier before the Iteration 27 cartridge inlet interface.

The pump station is an identity and packaging reservation only. No physical pump candidate is selected. Package envelope, placement, orientation axis, tubing diameter, bend radius, connector standard, nominal flow, suction pressure, and discharge pressure are all intentionally unset.

## Fault-state closure

Iteration 26 defines controlled semantics for pump-off power loss, gas ingestion, liquid slugging, foam ingestion, route occlusion, backflow, protected-region pooling, cartridge missing, cartridge misinstalled, and cartridge full or reduced-retention states.

The Iteration 26 registry is cross-checked against the pre-existing mixed-phase waste fault contract so an omitted required fault cannot be hidden by deriving the test expectation from the new registry itself.

These records define required architectural responses and downstream obligations. They do not claim that sensing, detection thresholds, pump tolerance, barrier effectiveness, pooling detection, cartridge interlocks, or physical fault responses have been validated.

## Evidence boundary

Pump selection and package geometry remain unresolved pending controlled supplier and packaging evidence. Pressure-flow behavior, suction limits, mixed-phase tolerance, gas/slug/foam/contaminant handling, backflow performance, orientation behavior, recovery ratio, residual liquid, leakage, protected-region pooling response, drain/dry performance, and service performance remain validation gated.

The Iteration 25 recovery minimum of 0.90 and residual-free-liquid maximum of 400 uL remain upstream validation-gated requirements. Iteration 26 does not convert them into measured performance.

## Evidence firewall

The architecture rejects invented pump, routing, tubing, connector, flow, and pressure values; uncontrolled status promotion; incomplete or reordered fault registries; hidden or parallel route topology; pump-stage bypasses; passive-barrier bypasses; stale source hashes; uncontrolled string aliases; mutable or aliased structural-frame reservation containers and identities; and post-construction corruption of nested pump or fault records.

The structural-frame reservation boundary is checked independently of the frame SHA because equivalent Python container or string-subclass substitutions can serialize to the same JSON representation while violating the exact runtime contract consumed by Iteration 26.

Manifest generation revalidates the complete nested architecture before hashing. The route network also preserves its own mixed-phase, pump-boundary, terminal-containment, and passive-backflow invariants.

## Provenance and current-source contract

The architecture binds the exact Iteration 25 waste-acquisition SHA, the structural-frame topology SHA, and the authority revision carried by Iteration 25. Current-source validation fails closed when either direct source changes, when the frame no longer exposes exactly one exact-type waste-routing reservation, when the reservation container or identity crosses the controlled type boundary, or when Iteration 25 regional destinations no longer terminate at the controlled Iteration 26 inlet interface.

Iteration 25 remains responsible for validating its own distribution and authority sources. The structural-frame contract remains responsible for its own upstream topology.

## Downstream contract

Iteration 27 may consume the exact Iteration 26 architecture SHA, the controlled cartridge-inlet interface identity, the passive-backflow topology requirement, and the cartridge-related fault semantics.

Iteration 27 must not infer pump pressure-flow capability, suction performance, backflow effectiveness, mixed-phase tolerance, cartridge retained capacity, sealing performance, insertion reliability, interlock behavior, recovery, leakage, or hygiene performance from this digital architecture.
