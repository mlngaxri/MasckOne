# Mass, centre of gravity and head load

Read this before changing anything in `mass:` in the authority, or before moving
mass anteriorly to solve a packaging problem.

## The defect this found

The authority stated four wearer-load limits and cross-checked none of them:

```yaml
mass:
  dry_target_max_g: 215.0
  loaded_absolute_max_g: 255.0
  cg_z_max_mm: 30.0          # <- previous value
  pitch_torque_max_Nm: 0.070
```

They are not independent. For a mask worn on a face, pitch torque is what the
other three produce:

```
τ = m · g · z_cg
```

Evaluating the worst *permitted* configuration — the heaviest allowed product at
the highest allowed CG:

| corner | mass | CG | τ | limit | result |
|---|---|---|---|---|---|
| dry | 215 g | 30 mm | 0.06325 N·m | 0.070 | OK, +9.6 % |
| **loaded** | **255 g** | **30 mm** | **0.07502 N·m** | **0.070** | **exceeds by 7.2 %** |

**A Masck One built exactly to its own stated maxima was not compliant** — and it
failed at the loaded condition, which is the worn, in-use case that actually
determines what the wearer's neck carries. Every individual limit could be met
while the set as a whole was violated.

## Resolution

Three closures were available:

| change | new value | cost |
|---|---|---|
| cap loaded mass | 237.9 g (from 255) | −17.1 g of mass budget |
| **cap CG height** | **27.99 mm (from 30)** | **−2.0 mm of anterior packaging** |
| raise torque limit | 0.0750 N·m | more load on the wearer's neck |

The torque limit is the only one of the four that is a *human* requirement — it
bounds what the neck carries. It holds. Mass and CG are design variables.

Between them, CG carries far more leverage per unit:

```
dτ/dz = 2.50 mN·m per mm of anterior CG shift   (at 255 g)
dτ/dm = 0.294 mN·m per gram                     (at 30 mm)
```

Recovering the 5.0 mN·m of excess costs either **2.0 mm of CG** or **17.1 g of
mass** — and 17 g out of 255 g is a far harder thing to find on a wet appliance
than 2 mm of depth. `cg_z_max_mm` was therefore tightened to **27.9 mm**, which
closes the set at every allowed mass with a small deliberate margin below the
27.99 mm bound.

This is a tightening, not a relaxation. Nothing was weakened to make a check
pass.

### Enforcement

`authority.py` raises `MASS_BALANCE_LIMIT_SET_DOES_NOT_CLOSE` during semantic
validation, before any CAD is generated, if any allowed (mass, CG) corner
exceeds the torque limit. The gate catches the defect from either side: raising
`loaded_absolute_max_g` breaks closure just as reverting `cg_z_max_mm` does.
`mass_balance.py` implements the same relation independently and the two are
cross-checked against each other.

### Moment-arm assumption

The arm is the CG's anterior offset in the Masck One datum frame, which is how
`cg_z_max_mm` and `pitch_torque_max_Nm` are stated relative to each other. The
true arm about the atlanto-occipital joint is larger by the joint-to-datum
offset, so **every torque here is a lower bound** on what the neck actually
sees. Closing the set in this frame is necessary, not sufficient.

## The mass ledger

`mass_balance.py` also carries the whole-product ledger. It will not invent mass.

The repository holds packaging **envelopes**, not manufactured material, and an
envelope bounds a volume rather than establishing what is inside it. Every entry
declares an evidence class:

| class | counts toward product mass |
|---|---|
| `MEASURED` | yes |
| `SUPPLIER_DATASHEET` | yes |
| `DERIVED_FROM_AUTHORITY` | yes |
| `MATERIAL_AND_REALIZED_VOLUME` | yes |
| `ENVELOPE_UPPER_BOUND` | **no** |
| `UNRESOLVED` | **no** |

An `UNRESOLVED` entry may not also assert a mass — it is recorded at 0 g and the
ledger reports its total as a lower bound.

`REQUIRED_MASS_COVERAGE` lists every subsystem that must carry a mass before a
total may be called product mass. Anything not supplied is **materialised as
`UNRESOLVED`, not omitted**: a ledger that silently skips the structural frame
and reports its liquid charge as complete is worse than no ledger at all.

### Current state

| | |
|---|---|
| established mass | **7.08 g** (water and cleanser charge) |
| dry budget | 215 g |
| unresolved subsystems | **19 of 21** |
| status | `INCOMPLETE_LEDGER_TOTAL_IS_A_LOWER_BOUND_NOT_PRODUCT_MASS` |

Only the liquid charges are derivable today: the authority fixes the volumes and
water density is known. Cleanser is carried at water density with the assumption
recorded on the entry — cleanser formulation density is unresolved.

Everything else — shell, frame, four actuators, pumps, manifold, cartridge,
battery, electronics, retention, thermal — has no mass evidence. The 215 g dry
target is therefore **entirely unretired**. Retiring it needs realized geometry
plus material assignment, or supplier datasheets, per subsystem.

## What this is not

Not measured mass, not a measured CG, not dynamic head load during motion, and
not a comfort or neck-fatigue result. Quasi-static only; head acceleration
during normal use is out of scope. A closed limit set means the requirements are
mutually satisfiable — it says nothing about whether any built product meets
them.
