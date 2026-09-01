# Cell 4 device-state and animation contract

Date: 2026-09-01
Status: SIMULATION-ONLY CONSUMER CONTRACT. No BLE, hardware telemetry, level sensing, cartridge sensing, battery sensing, real route animation or physical validation is created by this document.

## Purpose

Web and app surfaces need exact state semantics before real transport exists. Without a controlled contract, presentation code can silently invent battery percentages, cartridge sensors, hidden fluid routes or service behaviours that the hardware architecture does not support.

The executable contract is `src/masck_one/cell4_device_state.py`.

## Transport boundary

The only legal transport value is:

`SIMULATED_ONLY`

The contract explicitly exports:

- `hardware_telemetry_available = false`
- `ble_transport_available = false`
- `battery_sensor_capability_claimed = false`
- `cartridge_sensor_capability_claimed = false`
- `physical_validation_eligible = false`

These fields are not optional hints. Changing any to true is rejected by the contract.

A future real transport implementation must be introduced through a separately reviewed architecture and cannot be represented by renaming or relabeling this simulation transport.

## State vocabulary

Every presentation state that could otherwise be mistaken for hardware truth contains `SIMULATED_` in its value.

Operation states:

- `SIMULATED_IDLE`
- `SIMULATED_WET_CYCLE_ACTIVE`
- `SIMULATED_SERVICE`
- `SIMULATED_STORAGE`
- `SIMULATED_FAULT`

Battery states:

- `SIMULATED_UNKNOWN`
- `SIMULATED_READY`
- `SIMULATED_LOW`
- `SIMULATED_CHARGING`
- `SIMULATED_FAULT`

Charging states:

- `SIMULATED_UNKNOWN`
- `SIMULATED_DISCONNECTED`
- `SIMULATED_CONNECTED`
- `SIMULATED_CHARGING`
- `SIMULATED_COMPLETE`
- `SIMULATED_FAULT`

Waste-cartridge states:

- `SIMULATED_UNKNOWN`
- `SIMULATED_NOT_INSTALLED`
- `SIMULATED_INSTALLED`
- `SIMULATED_SERVICE_REQUIRED`
- `SIMULATED_FAULT`

Service states:

- `SIMULATED_NORMAL`
- `SIMULATED_SERVICE_REQUIRED`
- `SIMULATED_FAULT`

These are semantic presentation states only. They are not evidence that a sensor, switch, interlock, cycle counter or fault detector physically exists.

## Cross-state invariants

A simulated battery-charging state must be paired with the simulated charging state, and vice versa.

Simulated charging cannot overlap `SIMULATED_WET_CYCLE_ACTIVE`. This mirrors the current power/charging evidence boundary, which does not authorize active wet-cycle charging.

A simulated cartridge service requirement must propagate to `SIMULATED_SERVICE_REQUIRED`.

Any explicit simulated subsystem fault must propagate to the simulated service-fault state. Conversely, a service-fault state cannot appear without an explicit simulated subsystem fault.

These rules prevent Web/App from showing mutually inconsistent product states.

## Fluid/service animation boundary

Fluid animation is deliberately blocked with the only legal state:

`BLOCKED_PENDING_RELEASED_ROUTING`

and exact reason:

`BLOCKED_UNTIL_A_RELEASED_FLUID_ROUTING_CONTRACT_PROVIDES_EXACT_ROUTE_SOURCE_DESTINATION_PHASE_PROVENANCE`

This is necessary because Iteration 28 routing is not released on main. Cell 4 will not create an animation-only shadow route graph.

Once a routing contract is independently released, a later change may bind animation semantics to exact route IDs, source interface IDs, destination interface IDs and phase identities. Until then, Web/App may animate generic non-route visual transitions only if those visuals cannot be interpreted as real fluid paths.

## No invented battery percentage

The current contract exports categorical simulated battery states only. It intentionally does not export a numerical battery percentage because current architecture does not establish a real battery telemetry or state-of-charge sensing path.

If future firmware exposes a measured/estimated state of charge, that capability must be represented explicitly with sensor/estimator provenance, accuracy/uncertainty semantics and transport identity before consumer surfaces display it as hardware truth.

## No invented cartridge capacity or cycle count

The current waste-cartridge authority contains a validation-gated six-cycle service baseline and a validation-gated retained-capacity requirement. Neither is verified service endurance.

The simulation contract therefore does not export remaining cycles, remaining millilitres, saturation percentage or a real cartridge-full signal. `SIMULATED_SERVICE_REQUIRED` is a presentation state only.

## Web/App consumption rule

Consumers must render the simulation status visibly enough that development/demo screens cannot be mistaken for live hardware telemetry.

Consumers must not:

- remove the simulation label while continuing to use this payload;
- synthesize BLE connection status;
- infer numeric state of charge;
- infer cartridge capacity or remaining cycles;
- infer reservoir level;
- animate unreleased fluid routes;
- interpret simulated faults as validated real-device fault-detection capability;
- convert a simulated state into an efficacy, safety, availability or production-readiness claim.

## Promotion gate

A future real-device state contract requires, at minimum:

1. released hardware/firmware state sources;
2. exact transport identity and protocol revision;
3. sensor or estimator capability provenance for each exposed measurement;
4. explicit unknown/stale/error semantics;
5. route provenance for fluid animation;
6. fault-state mapping from real detection mechanisms;
7. versioned Web/App schema compatibility;
8. controlled tests proving simulated and hardware payloads cannot be confused.

Until those gates close, `SimulatedTransport` semantics remain the only allowed consumer path.
