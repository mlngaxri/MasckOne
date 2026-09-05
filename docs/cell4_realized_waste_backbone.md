# Cell 4 realized mixed-waste backbone

Status: provisional digital CAD engineering baseline, not physical validation.

Authored-against Git provenance: `5fce2a43a34d8be49256677a35af60c906dc1653`.
World frame: frozen Masck One authority datum, millimetres, +X wearer right, +Y superior, +Z anterior.

The authored-against Git SHA is historical provenance only. Release freshness is not self-certified from that SHA or from a copied authority revision. Trusted release build, manifest and manifest-hash paths reconstruct the repository-current fluid source graph internally, call `WastePumpArchitecture.validate_current_sources(...)`, bind the live `WastePumpArchitecture.architecture_sha256`, and exact-compare every realized route ID, stage, phase, source and target against that live architecture. A caller-supplied source bundle cannot certify a trusted release manifest.

## Realized scope

`realized_waste_backbone.py` realizes the three controlled mixed-waste backbone segments without collapsing the passive backflow stage:

1. `ROUTE-WASTE-ACQUISITION-TO-PUMP-I26`, stage `ACQUISITION_TO_PUMP`.
2. `ROUTE-WASTE-PUMP-TO-BACKFLOW-BARRIER-I26`, stage `PUMP_TO_PASSIVE_BACKFLOW_BARRIER`.
3. `ROUTE-WASTE-BARRIER-TO-CARTRIDGE-I27`, stage `PASSIVE_BACKFLOW_BARRIER_TO_CARTRIDGE_HANDOFF`.

For these backbone segments, the controlled route ID is also the routing-ledger segment ID. Every segment carries its exact controlled stage, source interface, target interface, `MIXED_AIR_LIQUID_FOAM_CONTAMINANT` identity, world-coordinate line or XY-arc centerline primitives, deterministic bounds and centerline length, explicit internal-area provenance, geometric dead-volume arithmetic, realized arc radius where an arc exists, a provisional service-envelope radius, and evidence status.

The adjusted centerlines total approximately 64.255 mm and produce approximately 0.291 mL geometric volume at the provisional 2.4 mm circular internal-diameter seed.

## Source-integrity closure

Cell 5 rejected the prior release binding because it compared source SHA and authority revision only against constants owned by the same module. That could remain internally consistent after an upstream authority or routing change.

The current release path rebuilds the authority, structural frame, distribution geometry, waste acquisition and waste-pump architecture from repository-current sources. The upstream `WastePumpArchitecture` validates the complete inherited source graph before its deterministic architecture digest is accepted. A well-formed but stale 64-hex architecture digest and a changed current distribution/source graph are hostile regression cases and must fail closed.

The realized geometry manifest retains the authored-against Git SHA only as historical provenance. It is not used as proof that current routing authority is unchanged.

## Integration correction in this revision

The previous acquisition handoff began inside the authority-derived mouth hard envelope, and the previous lower `x=-62 mm` leg was too close to the Cell 2 tapered lower shell for the provisional service reservation. The revised wearer-left inferior route shifts those sections laterally inward while preserving all controlled fluid identities and topology.

Cell 2 advanced during this work. The current Cell 2 branch head is `8f165049c4ff95cc706f2e106c8b58c3876f6b6f`, with current `exterior_surface.py` blob `b04f2651cf035e0cc3744be8b7e8eb7e68de0feb`. The route occupies Z = 12 to 16 mm. Cell 2's newer anterior-crown material begins conservatively above about Z = 20.1 mm, while the lower side-profile station scales and normalized tapered perimeter used by the route-envelope screen remain applicable in the route Z band. Re-screening therefore retains about 3.6 mm additional inward profile margin beyond the provisional 3.2 mm route envelope in the tight lower region. This is source-profile screening only, not a B-rep collision certificate, production clearance, or physical service evidence.

The current Cell 3 recovery branch remains at `8a5f7b60edaea36f9cfcd33770375127d1e70e65` and provides no newer controlled realized 3D mechanism or service envelope than released `main`. Exact mechanism swept-volume clearance therefore remains blocked rather than inferred.

## Explicit provisional baselines

The 2.4 mm circular internal-diameter seed is a Cell 4 engineering baseline used only for controlled geometric accounting. It is not a supplier tubing dimension.

The 2.0 mm service-clearance value is a reservation only. Together with the provisional 1.2 mm fluid radius, it defines a 3.2 mm digital route envelope for screening. It is not a measured service trajectory clearance.

No supplier minimum bend requirement has been selected. Bend requirement and bend margin remain unset even where the digital route has a realized 8.0 mm arc radius.

Pump inlet/outlet and passive-barrier inlet/outlet component separation remains package-selection work. Route endpoints are controlled handoff datums, not selected supplier component envelopes.

## Evidence firewall

This realization does not establish pressure-flow performance, measured priming or purge volume, recovery ratio, external leakage, reverse leakage, orientation independence, foam handling, contaminant tolerance, cartridge capacity, serviceability, hygiene performance, cleansing efficacy, or physical safety.

Geometric dead volume is only world-centerline length multiplied by controlled provisional internal area. It must not be relabeled as measured prime or purge demand.

## Remaining release gates

The exact changed head requires the complete engineering CI and deterministic CAD smoke build, direct generated-output inspection, independent Cell 5 hostile re-review, and Cell 1 release integration.

Whole-product B-rep collision against the accepted Cell 2 exterior and a controlled realized Cell 3 mechanism/service envelope remains a downstream integration gate. Selected pump and barrier envelopes, connector access, tubing or channel selection, supplier bend requirement, deformation/service trajectory, cartridge insertion/removal, drain low points, retained pockets, and wet/dry boundary crossings remain unresolved.