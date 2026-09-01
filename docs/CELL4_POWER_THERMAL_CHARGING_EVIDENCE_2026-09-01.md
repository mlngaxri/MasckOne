# Cell 4 power, thermal and charging evidence boundary

Evidence date: 2026-09-01
Region priority: Australia
Status: CONTROLLED DIGITAL EVIDENCE BOUNDARY. This document does not select a production battery, close Iteration 31 or 33, establish an exact runtime, certify electrical safety, select a charging connector, or establish a skin-safe temperature.

## Purpose

Cell 4 needs power and thermal reasoning before the later battery/electronics and WARM/COOL roadmap iterations, but the current released repository is only through Iteration 27. The correct action is therefore to create the evidence and calculation contract now without presenting later roadmap architecture as released.

The executable implementation is `src/masck_one/power_thermal_contract.py`.

## Current authority battery reference

The machine authority currently carries EEMB LP603450HA as a packaging benchmark at 3.7 V nominal, 1100 mAh, 34.5 x 52.0 x 6.3 mm and 22 g, with status `PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE`.

Fresh public evidence checked 2026-09-01 still lists LP603450HA at 3.7 V, 1100 mAh and 22 g on EEMB's product catalogue:

- https://www.eemb.com/products-58

The authority values imply 4.07 Wh by simple nominal-voltage x nameplate-capacity arithmetic. This is a reference-energy figure only. It does not include discharge-rate behaviour, voltage sag, BMS limits, conversion efficiency, usable state-of-charge window, ageing, temperature, peak-current capability, pack protection, harness losses or any measured Masck One duty cycle. It therefore cannot be converted into a runtime or cycles-per-charge claim.

The exact manufacturer part number, current datasheet revision, protection configuration, cell versus pack construction, connector/termination, transport documentation and procurement provenance must be obtained before this candidate can move beyond packaging-reference status.

## Complete power-load ledger

The controlled ledger contains the following loads in canonical order:

1. actuator array
2. water pump
3. cleanser pump
4. mixed-phase waste pump
5. control electronics
6. physical HMI
7. WARM subsystem
8. COOL reservation
9. standby

Every load currently starts `UNRESOLVED`. An unresolved load cannot carry a power number, duration, duty factor or evidence ID.

A load may later become `BOUNDED_MODEL_INPUT` only when lower and upper power plus duration bounds have explicit provenance. `MEASURED` is reserved for controlled hardware evidence. Once every load is bounded, the executable contract may calculate minimum and maximum cycle energy. That result remains `MODELED_ENERGY_BOUND_ONLY_NOT_RUNTIME_EVIDENCE`.

The model intentionally does not expose a battery-runtime calculation. A defensible runtime model later requires at least measured or supplier-controlled battery discharge behaviour over the relevant peak/average load profile, protection and conversion losses, usable capacity policy, ageing/temperature derating and a controlled operating-state sequence.

## Peak-current closure

Energy alone is insufficient. Later Iteration 31 work must also close simultaneous peak-current cases, including actuator transients coincident with pump operation, control/HMI operation and any thermal subsystem demand. The current authority contains actuator mechanical force requirements but not electrical input power, motor efficiency, driver loss or current waveforms. Those quantities must not be inferred from mechanical force alone.

Required evidence before electrical architecture selection:

- representative actuator voltage/current waveforms at controlled mechanical load and operating frequency;
- water, cleanser and waste-pump current versus representative fluidic operating points;
- controller, HMI and standby measurements;
- WARM input-power bounds tied to a thermal model and sensor/control strategy;
- charge-path current and conversion-loss measurements once architecture exists;
- transient supply droop and protection response on the selected pack architecture.

## Charging convention due diligence

### Therabody

TheraFace Mask currently ships with a USB-C charging cable. Its public specifications list approximately 120 minutes in LED mode and 60 minutes in vibration mode. Its manual instructs charging through a USB-C port inside the mask and says the device should be powered off for charging.

Sources checked 2026-09-01:

- https://www.therabody.com/products/theraface-mask
- https://www.therabody.com/on/demandware.static/-/Library-Sites-TheragunSharedLibrary/default/dwd288b452/pdf/TheraFaceMask_UserManual_GLOBAL_WF_23.05.31_VA.pdf

Interpretation: USB-C is normal and understandable for premium facial hardware. Therabody runtime values are not comparable Masck One evidence because its electrical loads, wet-path architecture and operating modes are different.

### Apple Watch

Apple currently sells a magnetic Apple Watch fast-charging cable terminating in USB-C and provides explicit battery service pathways. Apple Australia states Apple Watch batteries are designed to retain up to 80 percent of original capacity at 1,000 complete charge cycles, subject to real-use variation.

Sources checked 2026-09-01:

- https://www.apple.com/au/shop/watch/accessories/chargers-adapters
- https://www.apple.com/au/batteries/service-and-recycling/
- https://support.apple.com/en-au/watch/repair

Interpretation: a proprietary device-side interface can be commercially acceptable when it materially improves sealing, alignment or wearability, while standard USB-C may remain on the supply side. Apple cycle-life information cannot be applied to Masck One.

### WHOOP

WHOOP currently offers a Wireless PowerPack and Basic Charger as separate charging accessories. Its public product material advertises 14+ day device battery life and charging options designed around continuous wear.

Sources checked 2026-09-01:

- https://www.whoop.com/us/en/thelocker/introducing-whoop-5-0-and-whoop-mg/
- https://shop.whoop.com/au/en/collections/5-0-batteries/

Interpretation: a specialized charging architecture can be justified when it removes a major use interruption. Masck One has a different duty cycle and a contaminated wet subsystem, so WHOOP's architecture and runtime cannot be copied or used as evidence.

## Current Masck One charging decision

The controlled state is:

`USB_C_PREFERRED_IF_INGRESS_ELECTRICAL_AND_SERVICE_ARCHITECTURE_PERMIT`

with status:

`COMMERCIAL_PREFERENCE_ONLY`

This is deliberately weaker than `ARCHITECTURE_SELECTED`.

Current digital boundary rules are:

- charging during an active wet cleansing cycle is not authorized by current evidence;
- core charge/fault recovery cannot require the app;
- ingress protection is not verified;
- electrical protection is not verified;
- no connector location, receptacle sealing strategy, charging voltage/current, charger IC or external PSU rating is frozen.

Iteration 31 must compare at least: sealed USB-C receptacle, protected/recessed USB-C with closure, and a sealed device-side magnetic/contactless approach with standard external supply where appropriate. The comparison must include ingress risk, contamination trapping, cleaning access, accidental wet charging, connector cycle life, cable replacement burden, travel convenience, repairability, BOM/assembly burden and compliance implications.

## Thermal uncertainty register

The executable contract contains eight mandatory thermal risks:

1. battery self-heating
2. charging heat
3. actuator heat
4. pump heat
5. control-electronics heat
6. WARM skin-adjacent heat
7. wet/dry boundary heat transfer
8. COOL condensation/dew-point risk

All eight are currently `BLOCKED` and carry no temperature numbers.

A thermal gate may become `BOUNDED_MODEL` only when it has ordered model bounds, a unit and provenance. A claim-relevant closure requires controlled measurement and the later product safety/compliance process. No current result authorizes the phrases `skin-safe temperature`, `safe to charge while wet`, `cooling is condensation-free`, or an exact allowable surface temperature.

## WARM and COOL decision logic

WARM should not be sized from a desired skin temperature alone. Later design must solve from heater input, local heat spreading, contact/non-contact geometry, ambient conditions, wet-film convection/evaporation, sensor placement, control latency, single-fault behaviour and the cold/hot bounds of real hardware.

COOL remains an experimental reservation. Its commercial value must be weighed against condensation, added power, thermal hardware mass, sealing complexity and cleaning burden. If a passive or no-COOL architecture meets the intended user experience, the lower-complexity path should win.

## Battery and electrical validation procurement plan

For benign engineering characterization, the alpha lab package should include a calibrated power analyser/current measurement path, programmable current-limited bench supply, electronic load appropriate to the selected low-voltage architecture, battery/pack interface fixtures, thermocouples or RTDs at defined nodes, non-contact thermal imaging for correlation, environmental temperature/humidity measurement, and representative harness/connector samples.

Abuse, transport, short-circuit, overcharge, thermal-runaway or other hazardous battery-safety testing belongs with appropriately equipped qualified laboratories and the selected battery/pack supplier. It is not an ordinary prototype-bench activity.

SGS Australia publicly lists testing against standards including IEC 62133 and UN 38.3 transportation requirements as well as electrical, environmental, life-cycle and safety testing. This is a pathway reference, not a declaration of Masck One's final compliance scope.

Source checked 2026-09-01:

- https://www.sgs.com/en-au/services/battery-and-accumulators

The exact compliance matrix must be scoped after target markets, battery/pack architecture, charging supply, wireless functions and product classification are controlled.

## Evidence gates before later promotion

Before a production battery decision, require exact manufacturer/part/revision evidence, pack construction and protection responsibility, dimensional/tolerance data, peak and continuous current capability over expected temperature, ageing/cycle data, charge specification, storage limits, transport evidence, traceability, supply continuity and supplier change-control terms.

Before a runtime statement, require a closed measured cycle-energy ledger plus controlled usable battery energy under representative load, ageing and temperature conditions.

Before a charging-cadence statement, require measured cycle energy, user-cycle frequency assumptions with provenance, standby drain and charge behaviour.

Before a thermal claim, require bounded modeling followed by controlled physical testing at relevant ambient, wet/dry, fault and ageing conditions.

Before supplier approval, continue to use the separate Cell 4 supplier-qualification firewall. Public battery or charger marketing remains reference evidence only.

## Claims firewall

This package does not support: exact runtime, exact cycles per charge, production battery selected, USB-C selected, waterproof charging, charge-while-wet safety, skin-safe temperature, condensation-free cooling, battery cycle life, regulatory approval, or production readiness.
