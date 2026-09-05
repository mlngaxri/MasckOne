# Cell 4 realized mixed-waste backbone

Status: provisional digital CAD engineering baseline, not physical validation.

Current main source: `5fce2a43a34d8be49256677a35af60c906dc1653`.
Authority revision: `2026-08-30-R1`.
Authority blob: `2608dda483b995539de422290371c219668a1527`.
Controlled waste-topology blob: `ace02ee529070465b11832f475771125636312cb`.
World frame: frozen Masck One authority datum, millimetres, +X wearer right, +Y superior, +Z anterior.

## Realized scope

`realized_waste_backbone.py` realizes the three controlled mixed-waste backbone segments without collapsing the passive backflow stage:

1. `ROUTE-WASTE-ACQUISITION-TO-PUMP-I26`, stage `ACQUISITION_TO_PUMP`.
2. `ROUTE-WASTE-PUMP-TO-BACKFLOW-BARRIER-I26`, stage `PUMP_TO_PASSIVE_BACKFLOW_BARRIER`.
3. `ROUTE-WASTE-BARRIER-TO-CARTRIDGE-I27`, stage `PASSIVE_BACKFLOW_BARRIER_TO_CARTRIDGE_HANDOFF`.

For these backbone segments, the controlled route ID is also the routing-ledger segment ID. Every segment carries its exact controlled stage, source interface, target interface, `MIXED_AIR_LIQUID_FOAM_CONTAMINANT` identity, world-coordinate line or XY-arc centerline primitives, deterministic bounds and centerline length, explicit internal-area provenance, geometric dead-volume arithmetic, realized arc radius where an arc exists, a provisional service-envelope radius, and evidence status.

The adjusted centerlines total approximately 64.255 mm and produce approximately 0.291 mL geometric volume at the provisional 2.4 mm circular internal-diameter seed.

## Integration correction in this revision

The previous acquisition handoff began inside the authority-derived mouth hard envelope, and the previous lower `x=-62 mm` leg was too close to the current Cell 2 tapered lower shell for the provisional service reservation. The revised wearer-left inferior route shifts those sections laterally inward while preserving all controlled fluid identities and topology.

A control-profile screening against Cell 2 branch head `372ae29bffd9d2b3d9f78430b84362aa8977e1c7` indicates about 3.6 mm additional inward margin beyond the provisional 3.2 mm route envelope in the tight lower profile region. This is digital source screening only. It is not a B-rep collision certificate, a production clearance, or physical service evidence.

The current Cell 3 recovery branch resolves to released passive-routing work and does not provide a newer controlled realized 3D mechanism or service envelope. Exact mechanism swept-volume clearance therefore remains blocked rather than inferred.

## Explicit provisional baselines

The 2.4 mm circular internal-diameter seed is a Cell 4 engineering baseline used only for controlled geometric accounting. It is not a supplier tubing dimension.

The 2.0 mm service-clearance value is a reservation only. Together with the provisional 1.2 mm fluid radius, it defines a 3.2 mm digital route envelope for conservative screening. It is not a measured service trajectory clearance.

No supplier minimum bend requirement has been selected. Bend requirement and bend margin remain unset even where the digital route has a realized 8.0 mm arc radius.

Pump inlet/outlet and passive-barrier inlet/outlet component separation remains package-selection work. Route endpoints are controlled handoff datums, not selected supplier component envelopes.

## Evidence firewall

This realization does not establish pressure-flow performance, measured priming or purge volume, recovery ratio, external leakage, reverse leakage, orientation independence, foam handling, contaminant tolerance, cartridge capacity, serviceability, hygiene performance, cleansing efficacy, or physical safety.

Geometric dead volume is only world-centerline length multiplied by controlled provisional internal area. It must not be relabeled as measured prime or purge demand.

## Remaining release gates

Before promotion beyond a provisional CAD baseline, the rebased exact head still requires the complete engineering CI and deterministic CAD smoke build, direct inspection of generated outputs, independent Cell 5 hostile review, and Cell 1 release integration.

Whole-product B-rep collision against the accepted Cell 2 exterior and a controlled realized Cell 3 mechanism/service envelope remains a downstream integration gate. Selected pump and barrier envelopes, connector access, tubing or channel selection, supplier bend requirement, deformation/service trajectory, cartridge insertion/removal, drain low points, retained pockets, and wet/dry boundary crossings remain unresolved.
