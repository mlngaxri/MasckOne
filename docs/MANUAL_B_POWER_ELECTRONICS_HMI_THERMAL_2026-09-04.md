# Manual B power, electronics, HMI and thermal package

## Integration basis

This package is stacked on Manual A mechanical head `d49966019e03132edd95d0ad8a390d285a0740c7` so collision checks consume the exact Manual A frame, halo, yokes, latch, quick-release sweep and cartridge removal sweep without copying Manual A implementation.

Live `main` at reconstruction was `b2c2d2d94972e4615e281e86e2feddaaa3c4e0c8`. Exterior PR #62 head `aa250eba05b594c085be4c374f784f20f705750d` and fluidics PR #61 head `4b08dc4b111b3d7795c282cbf178876050a58bdf` were open and unmerged, so they are read-only integration references rather than released geometry dependencies.

## Battery and dry bay

The EEMB LP603450HA remains only the authority packaging benchmark. The CAD package places its exact authority envelope in a shallow central rear dry bay, close to the head and inside the rear halo visual field. A separate design-baseline fault/swelling clearance volume surrounds the cell, and the carrier is geometrically outside that reservation so it does not intentionally compress the benchmark pouch faces. The clearance values are Manual B CAD baselines, not supplier swelling limits or abuse-test evidence.

The dry bay includes a rear-service closure, PCB placeholder, support tray, four PCB mounting datums, connector-interface datums and a board-level fuse/protection/charging-power reservation. PCB outline, components, connector families, fasteners, creepage/clearance, EMC, antenna and production sealing remain unresolved. No BLE antenna reservation is added because no current controlled wireless hardware requirement was found in live authority.

## Harness

Thirteen deterministic clearance-envelope routes connect battery, PCB, four actuator electrical handoffs, fresh-water pump bulkhead, cleanser pump bulkhead, waste pump bulkhead, physical HMI, two WARM reservations, bounded COOL reservation and charging interface. The route solids are packaging clearances, not selected wire OD, insulation construction or bend-radius proof. Wet package handoffs terminate at dry-side sealed-bulkhead reservations.

The implementation checks these envelopes against current released water and cartridge envelopes and against the complete sampled Manual A quick-release and cartridge service sweeps. It does not claim closure against future Cell 4 centerlines until that geometry is released.

## Charging

A low-highlight left-lower rear charging access reservation is physically packaged with a dry-side harness interface and structural volume. Connector type, contact retention, ingress/IP rating, certification and active wet-cycle charging remain unselected or unauthorized. The reservation does not imply USB-C or any other connector has been selected.

## Physical HMI

Current authority does not encode a four-control list. Existing Manual B UX architecture requires CLEAN-first, app-independent operation, while the program prompt carries the historical four-control constraint. The CAD therefore realizes four side-control lands in the order `CLEAN`, `POWER`, `WARM`, `COOL`, with CLEAN larger and dominant, while every mapping remains `FORMAL_PRODUCT_DECISION_REQUIRED_BEFORE_CONTROL_MAPPING_FREEZE`.

Travel, accidental-activation guard space, sealed actuation stack and a flush status-window reservation are packaged. Switch hardware, legends, LED/light-pipe hardware, sealing method, actuation force and usability remain unresolved. Emergency mechanical removal remains Manual A and does not depend on app or powered HMI.

## WARM and COOL

Two shallow cheek-side WARM reservations provide physical room for a sealed heater/sensor/spreader/insulation stack and dedicated wiring handoffs. Heater technology, temperature limits, control sensing and skin-safety evidence remain physical gates.

COOL is limited to a small experimental volume inside existing dry-bay depth. It is not an MVP dependency and carries no cooling, dew-point or condensation-closure claim.

## Power ledger

The ledger carries the authority battery benchmark voltage and nameplate capacity without deriving runtime. It enumerates actuators, three pumps, electronics, HMI/status, WARM and experimental COOL as controlled load identities. Their power remains unset pending selected hardware or controlled supplier/measurement evidence. Total power and runtime are intentionally `None`; runtime is explicitly not validated.

## Evidence boundary

All geometry is deterministic digital CAD packaging evidence only. It is not battery qualification, ingress/IP certification, EMC, electrical safety, thermal safety, connector durability, wet-finger HMI validation, service-life validation, runtime validation or production release evidence.
