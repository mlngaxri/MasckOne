# Iteration 26 acceptance

## Scope

Single-owner mixed-phase waste-pump architecture, mandatory passive backflow-barrier topology, repository-rooted current-source composition, and explicit fault-state intent.

## Reconciliation decision

The repository temporarily carried two divergent Iteration 26 implementations. The reconciled release retains one architecture only. It preserves the stronger passive-barrier topology from the original Cell 4 design and the stronger live Iteration 25 source-proof composition from the separately developed packaging implementation. The superseded direct pump-to-cartridge implementation is removed.

## Controlled result

Iteration 26 defines one canonical waste-pump station bound to the exact Iteration 25 waste-acquisition architecture and the structural frame's `FRAME_RESERVATION_WASTE_ROUTING` reservation. Mixed air, liquid, foam, and contaminant semantics are preserved through every waste route stage.

The downstream route is explicitly three-stage:

1. Iteration 25 acquisition interface to waste pump station.
2. Pump outlet to a mandatory passive backflow-barrier reservation.
3. Barrier outlet to the Iteration 27 cartridge inlet handoff.

There is no controlled direct pump-outlet-to-cartridge route. Backflow is therefore represented both as a known fault state and as a topology constraint. The barrier is only a digital reservation. No valve, check element, cracking pressure, reverse-leakage value, placement, envelope, or performance is selected or claimed.

The architecture defines controlled fault intent for pump-off power loss, pump stall/no-motion, gas ingestion, liquid slugging, foam ingestion, contaminant ingestion, upstream occlusion, downstream occlusion, backflow risk, protected-region pooling risk, cartridge missing, cartridge misinstallation, and cartridge full or reduced-retention state. Detection, mitigation implementation, interlock realization, and physical fault performance remain unresolved or validation-gated.

The authority recovery minimum of 0.90 and residual-free-liquid maximum of 400 uL remain validation-gated requirements only. Iteration 26 does not convert them into measured pump, barrier, or containment performance.

## Provenance/current-source contract

Iteration 26 does not accept the Iteration 25 SHA as sufficient proof by itself. Both construction and current-source validation call the hardened Iteration 25 current-source boundary with the live authority, live Iteration 24 distribution, and the exact caller-supplied structural frame.

Iteration 25 then authenticates the repository authority/schema, reconstructs omitted inherited siblings from the canonical released graph, exact-compares the supplied distribution and structural frame against that graph, and recursively rejects stale or post-construction-corrupted inherited objects. This prevents Iteration 26 from presenting a different equal-hash frame while Iteration 25 internally validates another canonical frame.

Iteration 26 additionally binds the exact Iteration 25 architecture SHA, structural-frame topology SHA, authority revision, recovery requirement, and residual-liquid requirement. These checks are defense in depth after the repository-rooted inherited-source proof.

## Deliberately unresolved

Pump supplier/component selection, pump principle, package envelope, placement, orientation, tubing inner diameter, bend radius, connector standard, mixed-phase flow rate, suction pressure, discharge pressure, pressure loss, power, acoustics, priming behavior, foam tolerance, contaminant tolerance, gas handling, liquid-slug handling, orientation response, leakage, recovery ratio, residual free liquid, passive-barrier component selection, barrier cracking pressure, reverse leakage, backflow effectiveness, cartridge sealing/capacity/interlocks, fault sensing, control implementation, drain/dry behavior, service trajectory, cleanability, hygiene performance, durability, and all physical performance remain unresolved pending controlled geometry, supplier evidence, downstream architecture, and mixed-phase bench evidence.

## Evidence firewall

The architecture rejects invented pump or passive-barrier package data; invented tubing, connector, flow, pressure, cracking-pressure, or leakage values; direct barrier bypass; reversed/crossed/aliased route stages; incomplete, reordered, or mutable route/fault sets; physical-evidence promotion; non-finite and boolean numeric aliases; hostile string subclasses at controlled boundaries; stale Iteration 25 sources; stale or aliased structural frames; stale authority requirements; and post-construction corruption of nested station, barrier, route, or fault records.

Manifest generation revalidates the complete architecture and every nested controlled record before minting its deterministic provenance hash.

## Downstream contract

Iteration 27 may consume the exact Iteration 26 architecture SHA, mixed-phase semantics, the barrier-outlet-to-cartridge handoff identity, cartridge-related fault semantics, and validation-gated waste requirements only after this reconciled Iteration 26 state is independently released.

Iteration 27 may not infer pump package geometry, pressure-flow capability, recovery, leakage, passive-barrier effectiveness, cartridge retained capacity, sealing performance, interlock reliability, fault-detection coverage, containment performance, hygiene performance, or physical efficacy from this digital architecture.
