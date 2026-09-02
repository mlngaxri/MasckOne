# Cell 4 physical fluidics geometry closure gate

Date: 2026-09-02
Status: physical engineering preflight contract, not physical validation
Scope: fluidics, packaging, hygiene and service only. No website or app implementation.

## Root cause

Iteration 28 now closes a 63-segment fluid interface graph: 54 fresh-fluid segments and 9 mixed-waste segments. The additional waste segment is not optional bookkeeping. It preserves the released passive backflow barrier as a distinct physical interface between waste-pump discharge and cartridge handoff. Realized centerlines, internal cross-sections, bend radii, dead volumes and service clearances remain unset. A complete topology therefore cannot establish prime burden, pressure loss, trapped volume, drainability, bend compliance, service collision or packaging feasibility.

The executable module `fluid_geometry_evidence.py` creates the smallest downstream evidence layer needed to close those quantities without weakening the firewall. It does not backfill guessed dimensions into Iteration 28.

## Required CAD extraction

For every controlled segment, the next CAD pass must export stable segment ID, centerline length, internal cross-sectional area, realized minimum bend radius and minimum service clearance. Tubing or channel bend requirements must carry controlled supplier or validated internal provenance. Service clearance must be evaluated against the actual insertion/removal trajectory plus deformation envelope, not a static bounding-box gap.

Cross-section area is authoritative for dead-volume arithmetic. A nominal diameter is insufficient for non-circular grooves, manifolds or molded channels. Geometric dead volume is `centerline length x internal area` integrated along the route where area varies. The current executable helper covers constant-area segments; variable-area geometry requires discretized/integrated CAD export rather than an equivalent-diameter shortcut.

## Prime and purge semantics

Geometric dead volume is not prime volume. Prime/purge burden must separately account for entrained air, compliant expansion, wetting retention and mixed-phase behavior. The module therefore exposes a conservative prime-bound structure instead of equating route fill volume with observed prime demand. The authority clean-cycle initial-prime requirement remains validation-gated.

## Fresh-fluid closure sequence

First realize water reservoir pickup-to-pump and cleanser source-to-pump routes with orientation-aware pickup geometry. Then realize pump-to-manifold routes. Then resolve manifold branches and branch-to-outlet routes against the structural frame. Finally resolve outlet-to-groove handoffs with protected-region keepouts. Water and cleanser identities remain separate through every segment. No shared upstream wet volume is permitted merely to simplify packaging unless a reviewed architecture explicitly accepts cross-contamination and metering consequences.

For each route, record the lowest and highest local elevations in representative worn, fill, service and storage orientations. This is needed to identify gas traps, drain traps and unintended siphon paths. A centerline that fits in one nominal pose is not orientation closure.

## Waste closure sequence

Waste remains air/liquid/foam/contaminant mixed phase. Realize all five regional acquisition routes to the controlled waste-pump inlet, then the acquisition-to-pump segment, pump discharge to passive backflow barrier, passive backflow barrier to cartridge inlet, and cartridge inlet to retention region. The two barrier-adjacent segments must remain separate in CAD export, hydraulic analysis and service reasoning. Collapsing them into a direct pump-to-cartridge route would erase a containment-critical component from the physical model.

The physical model must reserve transient gas fraction and foam volume instead of sizing only from liquid ledger volume. Before physical Alpha, add explicit transient-buffer volume at each acquisition region or demonstrate through testing that the common suction path can absorb local slugs without overflow into protected regions. Backflow protection must be physically located. Its forward pressure loss, cracking behavior where applicable, reverse leakage, wet-contaminant behavior, orientation sensitivity and post-service state require physical evidence. A check-valve symbol or digital route boundary is not containment evidence.

## Hygiene and service gate

Every wet cavity must be classified as one of: routinely flushed, user-wipe-accessible, removable washable, sealed single-use waste, or dry-only. Any cavity outside those classes is a design defect until justified. Wet routes must be assessed for gravity drainability in the prescribed storage/service pose. Non-drainable residual pockets require either a controlled purge/dry mechanism or physical evidence that retained residue is acceptable.

Cartridge removal must not require the user to touch a waste-wetted seal face. The passive backflow barrier and its adjacent wetted interfaces must have an explicit hygiene class and must not create an inaccessible retained-waste pocket. Fresh refill and waste service trajectories must remain physically distinct enough to reduce cross-contact. Service-clearance calculations must include wet-finger grip envelope and seal compression/decompression travel.

## Efficacy-oriented fluid fixture

Build a transparent facial-route fixture using the released outlet/groove topology. Instrument water and cleanser feeds separately. Measure delivered mass by region, time to first wetting, regional wetting uniformity, residual volume after purge, recovered waste mass, escaped liquid mass and protected-region intrusion. Instrument waste-pump inlet and both sides of the passive backflow barrier so pressure loss, gas/foam passage and reverse leakage can be separated from cartridge effects. Repeat at nominal worn pose plus bounded pitch/roll cases and with a viscosity ladder representing candidate cleanser classes.

Do not use these fixture results as cleansing-efficacy evidence. They establish delivery/recovery potential and expose starvation, pooling, gas locking, foam choking, backflow-barrier restriction and orientation sensitivity before human efficacy work.

## Acceptance metrics to establish before fixture release

The engineering team must set controlled acceptance limits for regional delivered-volume imbalance, time-to-wet spread, escaped-liquid mass, protected-region intrusion, recovery fraction, residual retained volume, prime volume, purge duration, barrier forward pressure loss and reverse leakage. Numerical limits must come from product requirements and risk analysis, not be invented by this document.

## Power and thermal dependency

Route realization must precede final dry-bay closure because pump placement, harness crossings and service motion determine peak-current wiring, connector exposure and local heat paths. The backflow barrier also contributes hydraulic resistance and therefore can move the waste pump operating point. No battery runtime or thermal claim is promoted here. Once route geometry and barrier evidence are available, Cell 4 should update pump hydraulic operating-point bounds and convert them into electrical load ranges before selecting a production cell.

## DIGITAL_HANDOFF_DELTA

WEBSITE: future fluid-route visuals must wait for realized released centerlines. The passive backflow barrier must be shown as a distinct physical interface if internal routing is ever visualized. Do not depict hidden tubing, manifold branches, cartridge internals or barrier geometry from topology alone.

APP: no implementation change. Do not expose reservoir level, waste level, prime completion, flow rate, leak detection, backflow-barrier state or cartridge-full sensing unless physical sensing architecture is later released.

ASSETS/DATA: future route assets require all 63 exact segment IDs, released centerlines, source/destination/phase identity and revision provenance. Mixed waste must remain visually and semantically distinct from fresh water and cleanser. Pump-to-barrier and barrier-to-cartridge are separate mixed-waste segments.

CLAIMS: leak-proof, orientation-independent, universal-cleanser, exact prime volume, exact recovery fraction, backflow performance and cleansing-efficacy claims remain blocked pending physical evidence.

BLOCKERS: realized 3D centerlines, internal cross-sections, supplier bend specifications, service/deformation trajectories, orientation extrema, mixed-phase transient buffer geometry, backflow-device physical selection and characterization, drain/dry closure and instrumented fluid-fixture data.
