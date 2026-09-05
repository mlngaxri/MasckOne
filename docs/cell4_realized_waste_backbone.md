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

The deterministic release exporter now reconstructs the validated current Cell 4 release and emits its release manifest, all three route manifests and total geometric dead volume in `build_report.json`. This makes the existing deterministic CAD smoke exercise the realized routing source graph rather than leaving the new geometry outside the smoke path.

## Source-integrity closure

Cell 5 rejected the prior release binding because it compared source SHA and authority revision only against constants owned by the same module. That could remain internally consistent after an upstream authority or routing change.

The current release path rebuilds the authority, structural frame, distribution geometry, waste acquisition and waste-pump architecture from repository-current sources. The upstream `WastePumpArchitecture` validates the complete inherited source graph before its deterministic architecture digest is accepted. A well-formed but stale 64-hex architecture digest and a changed current distribution/source graph are hostile regression cases and must fail closed.

The realized geometry manifest retains the authored-against Git SHA only as historical provenance. It is not used as proof that current routing authority is unchanged.

## Integration corrections in this revision

The first realization placed the acquisition handoff inside the authority-derived mouth hard envelope and used a lower `x=-62 mm` leg too close to the Cell 2 tapered lower shell for the provisional service reservation. Those sections were moved inward while preserving controlled route identities and topology.

Cell 5 then found that Route A's full 3.2 mm provisional service envelope still intersected the actuator 3 B-rep released on `main`. The acquisition handoff is therefore moved laterally from `(-44, -34, 12) mm` to `(-52, -34, 12) mm`, with its pump endpoint unchanged at `(-48, -44, 16) mm`. This preserves the Route A centerline length and geometric-volume arithmetic. Direct CadQuery distance against the released actuator 3 B-rep increases from approximately 1.939 mm to approximately 5.116 mm, leaving approximately 1.916 mm of digital margin beyond the 3.2 mm provisional route-envelope radius. A targeted regression rebuilds the current released product model and requires Route A's full service-envelope radius to clear the released rigid shell and every released actuator envelope. This is digital B-rep reservation evidence only, not selected tubing, deformation, serviceability or physical clearance evidence.

Current Cell 2 PR #70 head is `9e0b7a7c5d05106b2782a7346873af9a688668ee`. Route A centerline Z spans 12 to 16 mm and its full provisional envelope reaches Z = 19.2 mm; the candidate crown inner-material guard remains approximately Z = 20.1 mm. A source-profile screen through the current five-station side body retains more than 13 mm horizontal inward margin beyond the provisional 3.2 mm route envelope in the Route A band. This is candidate-source screening only, not a merged cross-branch B-rep certificate.

Current Cell 3 PR #71 head is `a2a3d659a380ccba1ac20621e56be9a2aa6bc104`. Its right-side slider withdrawal reservation is X `[73.5, 100.0]`, Y `[-5.0, 5.0]`, Z `[-22.5, -15.5]` mm. The realized waste route remains entirely wearer-left and anterior of that reservation, so the current candidate-source broad-phase screen is clear. Full post-release head-removal trajectory remains unresolved and is not inferred from the slider reservation.

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

Selected pump and barrier envelopes, connector access, tubing or channel selection, supplier bend requirement, deformation/service trajectory, cartridge insertion/removal, drain low points, retained pockets, wet/dry boundary crossings, and full Cell 3 post-release removal trajectory remain unresolved.