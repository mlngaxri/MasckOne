# MASCK ONE All-Contact / Occlusion Matrix

Status: **CS-018 product-interface working contract; not physical validation**  
Writing owner: **Lane 1 Complete-Routine Facial Delivery**  
Required consumers: Lane 3 Wearable Human Factors/ID, Lane 5 Whole-Product Conductor.  
Refresh against live owner geometry before using this matrix for CAD decisions.

## 1. Purpose

Masck One cannot satisfy a complete leave-on routine if any necessary face-facing support, seal or treatment element permanently hides skin that the selected routine claims to finish.

This matrix makes those shadows explicit before the product spends more effort polishing mechanisms around an impossible contact topology.

State vocabulary:

- `CONTACT`: intended skin contact in that phase.
- `NEAR`: close to skin but not intended to carry load or wipe the film.
- `CLEAR`: must be sufficiently removed from the required application domain for the next operation.
- `TRANSITION`: changing support/contact state; swept interaction matters.
- `N/A`: not participating in that phase.
- `UNKNOWN`: current geometry/evidence does not justify a stronger statement.

`CLEAR` is a functional requirement, not a fixed displacement value.

## 2. Current concept matrix

| Face-facing class | Placement / fit | Clean | Rinse / recover | Treatment | Leave-on | Settle | Normal release | Main P0 question |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| perimeter wet seal | CONTACT | CONTACT | CONTACT | CONTACT or NEAR | **TRANSITION/CLEAR where it shadows required skin** | CLEAR/NEAR | TRANSITION → CLEAR | How is previously sealed skin finished without losing wet containment earlier? |
| facial support / alignment pads | CONTACT | CONTACT | CONTACT | CONTACT | **CLEAR or staged support transfer** | CLEAR/NEAR | TRANSITION → CLEAR | What carries the product while each shadowed patch becomes accessible? |
| facial retention reaction contacts | CONTACT | CONTACT | CONTACT | CONTACT | **UNKNOWN; must not permanently shadow a required final region** | UNKNOWN | release path | Can retention load be transferred away from finished facial skin before final application/release? |
| moving treatment / massage islands | NEAR/CONTACT as required | CONTACT where cleaning uses them | CONTACT/NEAR | CONTACT | **CLEAR** unless validated application-through-contact exists | CLEAR | CLEAR | Existing treatment geometry must not remain the assumed final support topology. |
| stationary treatment annuli / carrier rims | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | **CLEAR REQUIRED if skin-shadowing** | CLEAR | CLEAR | Astra identified these as a deeper risk than the moving islands alone. Exact current shadow map required. |
| WARM / COOL contact plates | N/A/NEAR | N/A | N/A | CONTACT when scheduled | **CLEAR before final leave-on unless the plate is outside required application domain** | CLEAR | CLEAR | Current thermal owner uses stationary contact plates; determine their exact facial shadows and exit state. |
| optical carrier / emitters | NEAR | N/A | N/A | NEAR during optical treatment | NEAR/CLEAR from fluid application path | NEAR | N/A | Optical hardware should not become a physical shadow or wipe surface; eye safety remains separate. |
| water / cleanser distribution surface | NEAR/CONTACT depending final architecture | active | active | N/A or cleared | **CLEAR or converted to non-wiping application role** | CLEAR/NEAR | CLEAR | Shared face-side wet architecture must not carry cleanser residue into leave-ons. |
| leave-on distribution surface | N/A | isolated | isolated | isolated/standby | active, preferably non-wiping over finished regions | CLEAR/NEAR | CLEAR | Thin and thick products may require different delivery families; do not assume one outlet solves both. |
| nose/airway boundary structures | CONTACT/NEAR as safety requires | CONTACT/NEAR | CONTACT/NEAR | CONTACT/NEAR | must preserve airway and avoid uncontrolled migration | unchanged safety state | release safely | Coverage around the nose must not weaken airway/protected-anatomy requirements. |
| eye-aperture boundary structures | CONTACT/NEAR as required | protected | protected | protected; optical boundary if used | protected from fluid migration | protected | release without dragging periocular skin | A large eye opening does not justify applying product into the protected aperture. |
| mouth-aperture boundary structures | CONTACT/NEAR as required | protected | protected | protected | protected from fluid migration | protected | release without lip/perioral drag | Perioral skin and mouth aperture need separate region semantics. |
| temporary fitting/alignment feature | CONTACT during placement only | should be out of active required region unless intentionally retained | same | same | **CLEAR** before any final film it would shadow | CLEAR | CLEAR | No alignment aid may create a permanent cosmetic shadow merely because placement is easier. |

## 3. Support continuity rule

Clearing contact is not enough. Masck must remain safely supported while contacts change state.

For every transition into leave-on application, Lane 1 and Lane 3 must together provide:

1. the contacts carrying wearer/device reaction immediately before the transition;
2. the contacts or non-facial load paths carrying it during transition;
3. the contacts, if any, permitted during leave-on;
4. every required skin patch shadowed before transition;
5. the application action that finishes each newly exposed patch;
6. evidence that an already finished patch is not subsequently wiped;
7. a separate emergency release path that remains available regardless of film state.

A design that clears every applicator but leaves the product unsupported is not a solution. A design that remains stable by permanently covering required final skin is also not a solution.

## 4. Shadow accounting

For each exact future face-facing solid/contact patch, create a stable shadow ID and map it to the CS-015 required-region set.

Required fields:

- participant ID;
- canonical owner/source;
- contact class;
- routine phases present;
- intended load/support role;
- nominal facial shadow region(s);
- protected-domain relationship;
- transition state before leave-on;
- strategy for finishing the shadowed patch;
- normal-release path relationship;
- evidence state;
- unresolved blocker.

Do not convert a geometric visibility calculation into evidence of deposited film. Geometry can prove a path is available; BENCH evidence must prove the application actually works.

## 5. Mandatory negative controls

Before accepting any final contact architecture, deliberately test/reference these failures:

- a stationary support that never clears and leaves a visible untreated island;
- a support that clears only after the surrounding final film is applied and drags through that film;
- a support-transfer path that momentarily loses safe device support;
- a release path that preserves most film globally but strips one required local region;
- a support/contact element that intrudes into a protected eye/nose/mouth domain while solving coverage.

The validation system should be able to distinguish and reject each failure.

## 6. Owner-specific next actions

### Treatment owner / PR #135 lineage

- export or otherwise identify the exact skin-shadow footprint of every moving island **and stationary face-adjacent carrier/support** in current candidate geometry;
- do not redesign treatment purely from this concept file;
- return exact shadow/sweep evidence to Lane 1;
- existing collision/B-rep failures remain with treatment owner.

### Thermal owner / PR #143 lineage

- provide current plate/contact footprints and whether they can become non-contact before leave-on stages;
- do not infer whole-face compatibility from thermal bench geometry;
- retain deliberate WARM/COOL physical-validation gates.

### Retention / wearable owner / PR #141 lineage

- identify any facial reaction/contact that persists through leave-on and release;
- establish how support transfers during the normal non-wiping release sequence;
- emergency/unpowered release stays independent and higher priority than film preservation.

### Face-side fluid/application owner

- map cleanser/water interfaces and future leave-on interfaces to the same required-region coordinate semantics;
- quantify shared-contact carryover risk;
- establish how newly exposed seal/support shadows receive product.

### Whole-product conductor

- reject any integrated candidate that has a required region with no credible access/finish path;
- keep region coverage, support continuity and release preservation visible as separate gates.

## 7. Promotion condition

CS-018 remains `PROVE` until there is a source-bound phase map for actual current candidate geometry and evidence that:

- every required facial patch has a credible access/application state;
- support continuity remains safe during state changes;
- protected anatomy remains protected;
- normal release does not require broad wiping of already finished skin;
- emergency release remains independent;
- whole-face/human questions remain explicitly open until tested.

A reduced cheek-rig pass cannot close CS-018 for the whole face.
