# Cell 2 Physical ID, CMF and Human-Factors Closure

Date: 2026-09-01
Status: design contract, not physical validation
Scope: physical product only. No website or app implementation.

## 1. Root-cause diagnosis

The exterior must not be treated as a cosmetic shell over independently solved subsystems. The dominant appearance risks are caused by packaging topology: facial protected-region cutouts, side retention/load transfer, rear service volume, wet/dry separation and control/service interfaces. If those are surfaced as separate pods or arbitrary local fillets, the product reads as goggles or an engineering scaffold even when every individual surface is smooth.

The governing ID rule is therefore: **one continuous facial field, one subordinate side transition, one deliberately recessive service volume**. Functional discontinuities must terminate at intentional seams or protected apertures rather than create decorative patches.

## 2. Evidence reviewed

Current official reference material was reviewed on 2026-09-01. Apple Watch Series 11 uses a compact case with explicitly differentiated structural material/finish and discrete tactile hardware controls, including a crown, side button and band release. Dyson documents anthropometric head/face research, distributed load paths, flatter contact cushions and orientation of contact geometry to anatomy for wearable comfort. Therabody SmartGoggles documents contoured eye padding, curved adjustable retention and cleaning requirements for surfaces exposed to makeup, soap, lotion and similar contaminants.

Principles extracted, without copying geometry or trade dress:

1. Wearable thickness should be managed as an integrated section, not hidden behind local bulges.
2. Retention geometry and compliant interfaces are part of industrial design and comfort, not secondary accessories.
3. Primary controls should remain physically discoverable without visual clutter.
4. Skin-contact and contaminant-exposed materials need cleanable, low-trap transitions.
5. Service releases should be visually subordinate but mechanically legible through tactile geometry.

## 3. Exterior hierarchy contract

### ID-P01 Facial field

The rigid front carrier shall read as one continuous facial field around the protected apertures. No actuator, fluidic or electronics envelope may generate an externally legible circular or rectangular pod on the front surface.

Appearance target, digital until sample review:
- global front field uses broad curvature changes rather than local radius stacks;
- local highlight breaks are allowed only at protected apertures, functional controls, a deliberate perimeter seam, or a service boundary;
- left/right field treatment is bilaterally coherent unless a functional asymmetry is required;
- no isolated flat exterior patch larger than 900 mm2 unless justified by assembly, control or service function.

### ID-P02 Aperture neutrality

Eye, nose and mouth openings must read as protected human clearances rather than a facial expression. The upper and lower eye boundary tangent directions shall be visually calm and must not converge into an inward/downward hostile brow gesture. Nose clearance shall not be expressed as a protruding external nose cone. Mouth clearance shall remain subordinate to the overall field and preserve speech/breathing clearance defined by engineering authority.

No ID pass may reduce authoritative protected-region clearance to improve appearance.

### ID-P03 Perceived depth

Packaging depth is to be visually decomposed into a dominant thin facial field and a recessive rear/service layer. Side-view quality is evaluated by silhouette and highlight continuity, not only maximum Z dimension.

Targets for the next CAD surface pass:
- no step change in visible exterior depth greater than 3.0 mm without a functional seam or interface;
- any side hardware transition visible from front 3/4 shall use a broad lead-in whose visible longitudinal run is at least 3 times the local depth change where packaging permits;
- rear/service mass must remain inside the front-field silhouette in frontal projection wherever authoritative packaging allows;
- local rear protrusions are rejected when the same volume can be spread laterally with no mass, sealing or service penalty.

These are ID optimization targets, not frozen engineering dimensions.

## 4. Surface-quality contract

Appearance surfaces are classified A, B or C.

A: front facial field, aperture surrounds, visible side transitions. Target G2 between authored surface patches where no seam is intended.

B: rear exterior and service doors visible during normal handling. Target G1 minimum, G2 where broad highlight flow materially benefits appearance.

C: concealed assembly/service surfaces. Functional continuity only.

Automated CAD QA should report patch-boundary positional deviation and tangent-angle discontinuity for A/B boundaries when the kernel exposes those values. Initial digital gates:
- A intended-continuous boundary: positional gap <= 0.05 mm; tangent discontinuity <= 1.0 degree;
- B intended-continuous boundary: positional gap <= 0.10 mm; tangent discontinuity <= 2.0 degrees;
- no claim of physical Class-A quality until tooled/sample surfaces are inspected under controlled reflection.

Fillets are not permitted as the primary method for resolving a major mass transition. Major transitions require authored section/loft control. Fillets remain acceptable for edge safety, molding, sealing and small tactile transitions.

## 5. Seam architecture

Seams are part of the product grammar and shall not wander around packaging obstacles.

1. Primary shell seam: locate on a low-highlight-change perimeter or rearward turnover, not across the dominant front field.
2. Wet/dry boundary: never disguise a sealing requirement by deleting the serviceable joint. Instead, make the joint geometrically quiet and continuous.
3. Cartridge/service boundary: use one readable insertion direction and one tactile release event. Avoid multiple adjacent cosmetic gaps that make the rear look assembled from pods.
4. Aperture interfaces: compliant-to-rigid transitions should terminate cleanly into a controlled land, avoiding narrow dirt-catching trenches on skin/cleanser-facing surfaces.

Digital appearance gap target for intentionally visible premium seams: nominal 0.35 to 0.60 mm, selected only after stack-up analysis. This range is not a tooling release dimension.

## 6. CMF system, physical authority candidate

Hex colours are explicitly non-authoritative. Production colour requires physical master samples and supplier matching.

### CMF-01 Mineral shell
Rigid PC/ABS exterior. Warm low-chroma mineral neutral, approximately Munsell N8 to N8.5 value with a slight warm bias as the exploration region. Low-gloss fine texture intended to suppress fingerprints and make small scratches less contrasty than a piano-gloss shell. Avoid chalky porous texture that traps cleanser or makeup.

Finish target for sample ladder: 10, 18 and 25 GU at 60 degrees, measured on supplier plaques. Select only after wet/dry contamination and cleanability testing.

### CMF-02 Skin interface
Silicone/LSR or validated compliant skin-contact material. Slightly warmer and visually softer than the rigid shell, with deliberately lower specular sharpness. The material difference should remain visible at close range so users can understand what is compliant and washable. No translucent skin-contact material unless it serves a validated functional purpose.

### CMF-03 Service/tactile accents
Controls, quick-release tactile land and cartridge grip may use a restrained darker mineral/graphite neutral for discoverability. Accent area should remain small enough that the face does not acquire a mechanical or aggressive expression. Colour alone may not be the only service cue.

### CMF validation ladder
For each candidate material/finish, test physical plaques or representative molded samples for water spotting, cleanser residue, sebum, common facial cosmetic contamination, repeated damp-cloth cleaning, scratch visibility, gloss shift and colour delta after ageing. Final Delta E tolerance must be negotiated across actual PC/ABS, silicone/LSR and any TPU system rather than assumed from digital colour values.

## 7. Physical UX contract

### Controls
CLEAN remains the dominant control. MASSAGE is secondary. COOL/WARM status must follow current engineering gating and may not be implied as validated merely because physical legends exist. Primary controls need tactile differentiation that can be identified while worn. Use geometry, spacing and surface texture, not colour alone.

Target minimum active tactile land: 10 mm equivalent diameter for primary finger-operated controls, with at least 2 mm clear tactile separation between adjacent control lands. This is a prototype usability target and must be tested on representative hardware.

### Don/doff and quick release
Quick release must be reachable by either hand without placing fingers near an eye aperture. Release direction must not drive the rigid shell toward the face. Hair-catching split lines, exposed hooks and pinch gaps along retention paths are prohibited. The release shall communicate state by a mechanically distinct seated position and tactile event, without requiring the app.

### Cartridge/service
The cartridge grip shall be accessible with wet fingers and shall not require fingernail purchase. Target grip relief depth exploration: 0.6, 0.9 and 1.2 mm with broad radiused transitions. Service motion should be single-axis until the final seating event where packaging permits. Any vent or fluid port exposed during service must be visually differentiated from a finger grip to reduce misuse.

### Cleaning
Normal wipe/flush paths shall avoid blind exterior cosmetic trenches narrower than the cleaning implement or finger access expected in use. Skin/cleanser-facing transitions should prefer open radii and drainable geometry. Appearance surfaces that routinely contact residue must be inspectable by the user.

## 8. Human-fit red-team gates

A multi-view review is required for front, front 3/4 left/right, side, top, underside, rear, worn, service-open and exploded states.

Reject the candidate if any review shows:
- goggle-like paired eye pods;
- downward/inward eye geometry creating an angry expression;
- a nose cone or beak-like front projection;
- a continuous thick annulus that reads as a toilet-seat/ring silhouette;
- side retention hardware that appears bolted onto the shell;
- rear service mass wider than necessary or visually unsupported;
- a seam crossing a high-visibility highlight field without functional necessity;
- inaccessible residue traps;
- quick-release operation that can pinch hair or drive hardware toward the face;
- a service grip requiring nails or high precision while wet.

## 9. Quantified next-CAD checks

The next geometry iteration should expose stable named measurements rather than face/edge indices:

- `ID_FRONT_FIELD_MAX_Z`
- `ID_SIDE_TRANSITION_RUN_L/R`
- `ID_SIDE_TRANSITION_DEPTH_L/R`
- `ID_REAR_FRONTAL_OVERHANG_L/R/T/B`
- `ID_EYE_UPPER_TANGENT_L/R`
- `ID_EYE_LOWER_TANGENT_L/R`
- `ID_SERVICE_GRIP_DEPTH`
- `ID_PRIMARY_SEAM_GAP_NOMINAL`
- `ID_CONTROL_TACTILE_LAND_CLEAN`
- `ID_CONTROL_TACTILE_LAND_SECONDARY`

Regression tests should compare these named measurements against explicit design-contract ranges. Appearance tests must never reference unstable kernel face numbers.

## 10. Release status

This document deliberately does not freeze production colour, gloss, texture, seam gap, Class-A status or universal fit. Those require physical samples, tolerance analysis and representative-user evaluation. It does freeze the industrial-design decision hierarchy and the rejection criteria used to prevent packaging-driven visual degradation.

## DIGITAL_HANDOFF_DELTA

WEBSITE: future product imagery should show a continuous calm facial field, recessive side/rear packaging and explicit compliant-versus-rigid material hierarchy. Do not depict front actuator pods, a nose cone, aggressive eye geometry or unsupported glossy finishes.

APP: no implementation change. Physical controls remain usable and discoverable without the app; digital status should not imply COOL/WARM capability beyond engineering release state.

ASSETS/DATA: future renders should distinguish mineral rigid shell, softer warm skin interface and small darker tactile/service accents. Hex values are not physical CMF authority.

CLAIMS: do not claim Class-A production surfacing, universal fit, production colour matching, stain resistance or scratch resistance until physical validation is complete.

BLOCKERS: final exterior surface release depends on authoritative subsystem packaging, tolerance stack-up, representative fit evaluation, molded CMF plaques/samples and physical cleanability/service testing.
