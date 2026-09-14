# MASCK ONE Whole-Routine Resource Envelope

Status: **P0 concept/integration ledger; not proof of achieved mass, runtime, dosing or efficacy**  
Writing owner: **Lane 5 Whole-Product Conductor**  
Input owners: Lane 1 facial delivery, Lane 2 dock/session preparation, Lane 3 wearable, Lane 4 Routine OS.  
Refresh live engineering authority before every engineering decision.

## 1. Purpose

The full-routine pivot adds more than liquid volume. It adds product isolation, prepared-session storage, retained wet inventory, waste, delivery interfaces, sensing/control needs, optional treatment energy, and potentially more routine time.

Masck One therefore needs one routine-level ledger rather than a cleanser budget plus separately optimistic subsystem budgets.

A candidate routine is only resource-feasible when the same physical state closes simultaneously on:

- dry mass;
- loaded mass;
- centre of gravity;
- wearer pitch torque;
- session liquid inventory;
- fault-releasable liquid inventory;
- fresh-water availability;
- waste capacity;
- energy;
- thermal readiness;
- session-dose storage;
- dock product slots;
- routine duration;
- service burden.

## 2. Dated released-authority snapshot

Observed released `main` during this convergence pass: `eb8ba26c57222320210fa7eb15f4d69e1563cf64`.

Relevant released authority values observed:

| Quantity | Current released value | Status/use here |
| --- | ---: | --- |
| dry wearable target max | 215 g | engineering baseline; not achieved result |
| loaded absolute max | 255 g | project requirement |
| CG-Z max | 27.9 mm | engineering baseline |
| pitch torque max | 0.070 N·m | engineering baseline |
| fresh-water reservoir gross | 6.5 mL | engineering baseline |
| fresh-water reservoir minimum usable | 5.5 mL | engineering baseline |
| face water, clean cycle | 3.2 mL | validation-gated clean-cycle baseline |
| cleanser, clean cycle | 0.60 mL | validation-gated clean-cycle baseline |
| post-flush water | 0.80 mL | validation-gated clean-cycle baseline |
| nominal introduced clean-cycle liquid | 4.60 mL | validation-gated clean-cycle baseline |
| maximum initial prime | 0.40 mL | validation-gated clean-cycle baseline |
| minimum waste recovery ratio | 0.90 | validation-gated |
| residual free liquid max | 400 µL | validation-gated |
| waste retained-capacity minimum | 35 mL | validation-gated |
| historical waste service baseline | 6 cycles | validation-gated; not expanded-routine proof |
| uncontrolled total fluid-fault max | 150 µL | validation-gated |
| uncontrolled branch fluid-fault max | 50 µL | validation-gated |
| battery benchmark | 1100 mAh at 3.7 V, 22 g | packaging benchmark only |

These values are a dated snapshot for concept reconciliation. `config/masck_one_authority.yaml` remains the authority. If it moves, update this ledger rather than treating these copied values as frozen truth.

## 3. Constraint consistency

At the absolute loaded mass limit and current CG-Z maximum:

`0.255 kg × 9.80665 m/s² × 0.0279 m = 0.06977 N·m`

which is just below the 0.070 N·m pitch-torque limit.

Therefore the current constraint set leaves almost no conceptual excuse for treating loaded mass and CG as independent budgets. A heavier routine-specific front payload consumes CG/torque margin even when total mass remains below 255 g.

The former 30 mm CG-Z planning value must not be reused as current authority.

## 4. Canonical routine resource variables

Every prepared session must instantiate or explicitly mark unknown:

### Fluids

- `V_water_start_mL`
- `V_cleanser_mL`
- `V_leaveon_i_mL`
- `V_moisturiser_mL`
- `V_spf_mL`
- `V_purge_or_changeover_mL`
- `V_recovered_to_waste_mL`
- `V_residual_free_mL`
- `V_device_retained_mL`
- `V_external_loss_mL`
- `V_fault_releasable_total_mL`
- `V_fault_releasable_branch_mL`

### Mass / balance

- `m_dry_wearable_g`
- `m_session_products_g`
- `m_fresh_water_g`
- `m_retained_waste_g`
- `m_routine_specific_hardware_g`
- `m_loaded_state_g`
- `cg_xyz_loaded_mm`
- `pitch_torque_Nm`

### Energy / thermal

- `E_control_Wh`
- `E_fluid_delivery_Wh`
- `E_actuation_Wh`
- `E_optical_Wh` when scheduled
- `E_warm_cool_equivalent_Wh` or explicit preconditioned-store state when scheduled
- `E_margin_Wh`
- `thermal_ready_state`

### Time

- preparation time in dock;
- CLEAN duration;
- RINSE/RECOVER duration;
- each treatment duration;
- each leave-on application duration;
- required settling duration;
- release duration;
- post-return required service duration;
- user active-attention time.

### Dock / ownership

- number of bulk product slots required by the supported cohort;
- bulk product volumes;
- prepared-session dose slots used;
- waste service interval;
- water service interval;
- cleaning consumables, if any;
- product-changeover burden;
- routine-preparation lead time;
- overnight acoustic/service state.

Unknown values remain `UNKNOWN`, not zero.

## 5. Three mandatory planning scenarios

### Scenario S0: minimum supported complete facial routine

Required stages:

`CLEAN -> RINSE/RECOVER -> one supported finishing leave-on/moisturising stage -> required SETTLE -> NON-WIPING RELEASE`

Known cleanser-era starting point:

- face water: 3.2 mL;
- cleanser: 0.60 mL;
- post-flush water: 0.80 mL.

Unknown until Lane 1/Lane 4 evidence:

- finishing-product dose;
- added purge/changeover volume;
- deposited vs retained fractions;
- exact routine duration;
- energy beyond released clean-cycle functions.

S0 exists to prove the simplest version of the locked promise. It must still be a genuinely complete selected facial routine, not a cleanser cycle renamed complete.

### Scenario S1: normal PM

Required planning stages:

`CLEAN -> RINSE/RECOVER -> optional scheduled treatment -> leave-on treatment/serum -> MOISTURISE -> SETTLE -> NON-WIPING RELEASE`

Additional unknowns that must be closed:

- one representative serum-family dose and density;
- moisturiser-family dose and density;
- whether the application architecture requires one or multiple isolated on-head paths/chambers;
- retained dead volume and purge volume;
- treatment energy/time where selected;
- film-settle duration;
- additional service/waste generated by product transitions.

### Scenario S2: demanding AM

Required planning stages:

`CLEAN -> RINSE/RECOVER -> optional validated treatment -> leave-on 1..N -> MOISTURISE if required -> FACIAL SPF -> required SETTLE -> NON-WIPING RELEASE`

This is the budget stress case.

It must eventually include:

- multiple leave-on products from the target cohort;
- the exact facial-SPF application quantity required by the validated product/application context;
- maximum expected prepared-session product mass;
- transition/carryover allowance;
- final waste/retained inventory;
- optional optical/thermal energy only if the scheduled routine genuinely uses it;
- total routine time including SPF settling/label constraints;
- final loaded mass/CG/torque state and all meaningful intermediate wet/waste states.

Do not assign a convenient SPF or serum dose merely to close the budget. Until the selected product/application evidence exists, those entries remain unknown and S2 remains open.

## 6. Current known arithmetic and what it means

### 6.1 Nominal cleaning liquid

Current clean-cycle introduced liquid baseline:

`3.2 + 0.60 + 0.80 = 4.60 mL`

This does not include:

- leave-ons;
- moisturiser;
- SPF;
- new product-path priming;
- multi-product changeover;
- retained product in new paths;
- unexpected fault inventory.

### 6.2 Fresh-water margin

Current minimum usable fresh water is 5.5 mL against 4.0 mL of face + post-flush water in the clean-cycle baseline, before considering any additional complete-routine water demand.

Therefore the expanded architecture may have only ~1.5 mL of nominal usable-water headroom relative to those two baseline water quantities, and even that is not a qualified spare-volume allowance because prime, tolerances, service strategy and actual recovery behavior remain gated.

### 6.3 Loaded-mass upper arithmetic

If a future design were exactly at the 215 g dry target, the numerical difference to the 255 g absolute loaded maximum would be 40 g.

That 40 g is **not** a liquid allowance. It must absorb every loaded-state difference not already included in the dry definition, and the CG/torque constraint can become limiting before total mass.

### 6.4 Waste capacity

The >=35 mL retained-capacity requirement appears much larger than one 4.6 mL introduced clean cycle, but this cannot be used to assert a six-cycle complete-routine service interval. Recovery, retained products, leave-on non-recovery, purge/changeover waste and service fluids change the load case.

## 7. Mass/CG states that must be evaluated

Do not check only one nominal full state. At minimum evaluate:

1. dock-prepared, full session doses, fresh waste cartridge;
2. immediately after placement;
3. mid-clean with fluid redistributed on face/path;
4. maximum front-side wet inventory state;
5. post-recovery with waste accumulated;
6. leave-on stages with different chambers emptied asymmetrically;
7. final leave-on / pre-release;
8. interrupted routine at worst plausible inventory distribution;
9. waste-near-service state;
10. any asymmetric fault or single-branch retained-fluid state relevant to comfort/safety.

For each, record total mass and actual CG, not a nominal assumed centroid.

## 8. Energy states that must be evaluated

Battery feasibility cannot use capacity alone. For each routine:

- begin from a defined state of charge;
- account for control electronics;
- fluid handling;
- 40 Hz actuation if used;
- optical treatment if used;
- sensing;
- release reserve;
- fault handling;
- required communication that remains local;
- energy margin;
- any thermal preconditioning burden that is actually on-device.

The battery remains a benchmark, not production freeze.

A valid routine must preserve sufficient reserve for safe release and shutdown even if a nonessential treatment stage is curtailed.

## 9. Duration and ownership value

Track two different time quantities:

1. **wear time**: how long Masck is on the face;
2. **active attention time**: how long the user is actually servicing or interacting with it.

The product may still create value with a longer wall-clock routine if active attention is dramatically lower, but this must be measured later rather than assumed.

Routine duration must not be shortened below physical/product requirements simply to reach a marketing number.

The dock must also track active attention per week for:

- adding products;
- adding water;
- removing waste;
- cleaning/service;
- changeover;
- resolving errors.

If total ownership attention approaches or exceeds the manual skincare friction Masck is meant to remove, that is a product-level warning even if the wearable itself performs well.

## 10. Dock slot-count implication

The mask does not need a bulk reservoir for every product in the user's week. The dock needs enough bulk-product associations to support the target routine cohort, while the wearable loads only the exact session products.

Do not freeze a slot count from intuition. Determine it from:

- target-user routine research;
- number of distinct products used across AM/PM/week;
- maximum products in one supported routine;
- swap frequency users will tolerate;
- footprint target;
- preservation/changeover constraints.

The dock study should report coverage of real routine cohorts versus slot count rather than “more compartments is better.”

## 11. Promotion gates

The resource architecture cannot reach integrated digital freeze until:

- S0, S1 and S2 have all required variables either measured/bounded or explicitly blocked by a named evidence owner;
- no scenario is made to pass by assigning unknown values to zero;
- current engineering authority is consumed directly;
- all meaningful loaded/interrupted states satisfy mass/CG/torque constraints in the selected geometry;
- water/waste/service capacity covers the selected ownership model;
- energy closes with safe-release reserve;
- session-dose package volume closes without forcing a bulky front-heavy wearable;
- dock slot/footprint/service burden is consistent with the Core Sketch UX;
- SPF remains blocked until its exact application evidence supplies the required inputs.

## 12. Immediate next data requests by lane

**Lane 1**
- representative dose/deposition ranges from bench work, with product density where needed;
- residual and carryover quantities;
- session-dose path/chamber count demanded by credible application architectures.

**Lane 2**
- bulk slot study;
- isolated session-dose storage overhead;
- product-contact dead volume;
- changeover/service fluid and waste;
- actual dock preparation/service timing and power later.

**Lane 3**
- current dry mass ledger;
- spatial locations of added session-dose/application hardware;
- realistic loaded-state CG and torque across fit/sizing candidates.

**Lane 4**
- exact stage/routine definitions used for S0/S1/S2;
- product evidence context and settle/sequence constraints;
- readiness rule that rejects a session when required resource data is insufficient.

**Lane 5**
- maintain the single ledger;
- prevent subsystem budgets from double-counting spare mass/energy/volume;
- remove optional modalities before weakening the complete-routine promise if the shared budget cannot close.
