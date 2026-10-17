# Resource envelope arithmetic

`assess_resources` is an unvalidated planning screen over the canonical ledger.
It never promotes unresolved hardware mass or position to zero, and internal
recovery never adds a second copy of transferred liquid.

`session_water_ml` is water consumption demand, including prime and purge.
`inputs.prepared_water_charge_ml` is a separate `[lower, upper]` starting water
inventory. When absent, its lower bound is demand's lower bound and its upper
remains unknown. The loaded-mass calculation uses this charge, rather than
consumption demand. Gross reservoir capacity is only a capacity screen; it does
not establish an actual fill or usable delivered volume. Charge sufficiency
requires demand's upper to fit prepared charge's lower for the whole range
to work. A demand lower exceeding charge's upper definitely violates sufficiency;
overlapping ranges cross the limit, and an unknown upper remains unresolved. Neither this check nor a gross-capacity check
establishes a usable delivery allowance for dead volume or inaccessible liquid.

`optical_selected` and `thermal_selected` accept explicit booleans or unknown
(null/absent). Unknown choices retain the corresponding inventory/resource
unknowns and block closure. Numbers, strings and containers are rejected.

`assess_electrical_envelope(plan, envelope)` derives duration, battery-side
energy and conservative peak-power bounds for the exact validated plan stage
inventory. Its input is:

```json
{
  "background": {"average_power_W": [1, 2], "peak_power_W": [2, 3]},
  "stages": [
    {"id": "exact-plan-stage-id", "duration_s": [10, 20],
     "average_power_W": [2, 4], "peak_power_W": [4, 6]}
  ]
}
```

The caller must supply one stage row per plan stage, without extras or duplicates.
These example numbers illustrate the format only. The background inventory is
explicit and continuously active across all sequential stages. Each numeric
quantity may be null (unresolved); an empty background object preserves unknown
power instead of implying no load. A declared zero inventory requires explicit
zero power bounds. Each stage energy is `(stage average + background average)`
multiplied by duration, divided by 3600 for Wh. Inter-stage waits must be included
as stages in the selected plan or in a stage's duration; there is no hidden
unpowered interval.

Independent stage/background peak times are not assumed to coincide. A combined
peak lower is the maximum of stage peak lower, background peak lower and combined
average lower. Its upper is the sum of peak uppers; this is a conservative
possible-coincidence bound. The routine peak is the maximum across stage peaks.
Unknown inventories propagate even through nominal multiplication by zero.
Non-finite inputs and arithmetic overflow are rejected.

This API establishes neither battery capability nor hardware authorisation.
Thermal-state energy and dock reset energy remain separate from electrical
energy: converting thermal/optical outputs to electrical loads requires measured
or justified efficiency and time profiles. Caller power inputs must already
include any selected thermal/optical electrical consumers. The envelope does not
infer their wattage or certify complete physical consumer inventory.
