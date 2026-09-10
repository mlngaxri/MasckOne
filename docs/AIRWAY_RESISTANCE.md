# Airway resistance — added breathing-resistance screen

Read this before changing `safety.airway` limits, nostril aperture geometry, or
anything that can reduce the deformed nasal opening.

## Why this exists

`config/masck_one_authority.yaml` has always stated three airway numbers:

```yaml
safety:
  airway:
    minimum_area_each_mm2: 120.0
    max_added_pressure_drop_pa:
      at_30_lpm: 10.0
      at_60_lpm: 40.0
    no_collapse_test_flow_lpm: 120.0
    no_collapse_required: true
```

Nothing related them. An aperture area sat beside two pressure limits and a
frozen safety test flow with no model connecting the three, so no candidate
aperture could be screened, no design budget existed, and the structural load
implied by the no-collapse test was never derived.

`src/masck_one/airway_resistance.py` closes that gap.

## Model

Incompressible, quasi-steady flow at the peak of the breathing cycle. Mach stays
below 0.03 at every flow considered. The added path is a short aperture in a thin
wall, so the loss is written in the standard inertial form:

```
dP = K · (ρ V² / 2)        V = Q_path / A_min
```

`K` collects contraction, wall-friction and expansion terms referenced to the
aperture velocity. At the released 1.8 mm wall the duct is hydraulically very
short (`L/D_h < 0.25`), so friction is a small correction and the
separation-driven terms dominate. Air is dry at 25 °C, 101.325 kPa
(ρ = 1.184 kg/m³, μ = 1.849×10⁻⁵ Pa·s), stated explicitly in the manifest
because every result scales with density.

## Result 1 — the two requirement points are exactly consistent

Because `dP ∝ Q²` for a fixed aperture, each flow-specific limit implies a
loss coefficient. At the released 120 mm² minimum:

| flow | V | Re | ρV²/2 | limit | implied K |
|---|---|---|---|---|---|
| 30 L/min | 2.083 m/s | 1 649 | 2.569 Pa | 10 Pa | **3.8919** |
| 60 L/min | 4.167 m/s | 3 298 | 10.278 Pa | 40 Pa | **3.8919** |

Identical to machine precision. Doubling the flow quadruples the limit, so both
points describe one geometry. That is not a coincidence worth admiring — it is a
checkable invariant, and it is now enforced.

**Design budget: K ≤ 3.89 per nostril at 120 mm².**

## Result 2 — edge treatment decides the closure margin

Screened at the binding requirement, with handbook loss coefficients
(Idelchik; Blevins) quoted as planning values with explicit spread:

| edge treatment | K (high) | ΔP at 30 L/min | area floor | margin below 120 mm² |
|---|---|---|---|---|
| sharp-edged | 2.90 | 7.45 Pa | 103.6 mm² | **13.7 %** |
| chamfered ~45° | 1.70 | 4.37 Pa | 79.3 mm² | 33.9 % |
| radiused r/D ≥ 0.2 | 1.15 | 2.95 Pa | 65.2 mm² | 45.6 % |

All three meet the requirement at nominal area. The difference is what happens
when the aperture closes — under misregistration, membrane deflection, or a
wearer whose anatomy loads the opening. Because `dP ∝ 1/A²`, margin is consumed
fast: a square-edged aperture has only **13.7 %** area closure available before
breathing resistance is out of budget, against **45.6 %** for a radiused inlet.

**A radiused or chamfered aperture inlet buys roughly 3× the closure margin of a
square edge for no change in nominal area.** On a product whose aperture is
bounded by compliant material that deflects under the very suction being
computed, that margin is the design decision, not the nominal area.

## Result 3 — a derived structural load

The frozen `no_collapse_test_flow_lpm: 120.0` implies suction across the
aperture:

| edge treatment | suction at 120 L/min |
|---|---|
| sharp-edged | **119.2 Pa** |
| chamfered | 69.9 Pa |
| radiused | 47.3 Pa |

This is a load input for the nasal membrane and compliant-interface lanes. It did
not previously exist in any form. `safety.airway.no_collapse_required` is a
`FROZEN_SAFETY_REQUIREMENT`, so the compliant structure bounding the nostril
aperture must not collapse under it.

## Enforcement

Two independent implementations of the consistency invariant, deliberately kept
separate and cross-checked against each other by
`tests/test_airway_resistance.py::test_screen_and_authority_gate_agree`:

- `authority.py` raises `AIRWAY_PRESSURE_DROP_REQUIREMENT_INCONSISTENT` during
  semantic validation — before any CAD is generated — if `limit / flow²` is not
  constant across the requirement set. Density, aperture area and path count all
  cancel from that condition, so it holds for *any* geometry: a violation is a
  defective requirement, not a hard design problem.
- `airway_resistance.py` reports `requirement_points_are_mutually_consistent`
  and always binds to the tightest budget, never the loosest.

The screen manifest is emitted into `build_report.json` as
`airway_resistance_screen`.

## What this is not

`ANALYTICAL_SCREEN_NOT_MEASURED_BREATHING_RESISTANCE`.

Real nasal airflow is cyclic, not steady. The aperture is bounded by compliant
material that deflects under the load being computed, so the area used here is
itself an assumption. `K` is only weakly Reynolds-independent above Re ≈ 10⁴ and
these flows sit at Re 1 600–6 600, which the manifest flags per point. No
allowance is made for humidity, mucus, ambient temperature, or the wearer's own
nasal resistance — which is typically far larger than anything computed here and
varies enormously between people and across the nasal cycle.

**Measured breathing resistance on physical hardware remains required.** This
screen establishes that the requirement set is satisfiable and says where the
margin goes. It does not establish that any built aperture meets it, and it says
nothing at all about perceived breathing effort or comfort.
