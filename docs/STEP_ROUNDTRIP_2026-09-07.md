# STEP volume accounting correction

Source investigated: PR #130 `753898f947ec951175b5f17893145f55b6439af1`.
Failed exact CI: run `34084674096`, 771 passed, one failed, four subtests passed.
Exploratory reproduction used CadQuery 2.8.0 / OCP 7.9.3.1.1 on Python 3.12;
the required release gate remains the repository Python 3.13 workflow.

The assertion compared a compound mass integral with the sum of separate solid
integrals. OCC's numerical integration depends on compound grouping/reference
point. This is not a valid identity at the asserted precision.

| Measurement | mm3 |
|---|---:|
| Sum of original individual solid default volumes | 63061.69511024539 |
| Original compound default volume, before STEP | 63061.955360524385 |
| Imported compound default volume | 63061.95552073894 |
| Grouping discrepancy already present before export | 0.260250278995 |

There are five solids: one shell and four disconnected local membrane regions.
All survive both standalone and assembly exports. Material membership is unchanged.
Shell/membrane overlap is zero. Explicit `fix()` changes none of the measured
volumes. Bidirectional original/imported material differences return zero at the
kernel's modeling tolerance. This does not establish mathematical surface identity.

With identical per-solid adaptive integration at `1e-12`, shell read-back delta
is approximately `3.45e-9 mm3`. The four membrane solid deltas are respectively
`4.08e-12`, `-5.70723581e-6`, `6.18e-13`, and `0.0001283191532 mm3`.
Those membrane values agree between standalone and assembly STEP. The membrane
bounding tolerance contracts by approximately `6e-7 mm` on read-back. Remaining
small read-back differences are kernel representation/tolerance effects; they
are not corrected by further `fix()` calls. Box references are unchanged;
actuator reference drift is at most approximately `2.57e-10 mm3`.

The replacement gate checks each solid independently using the same integration
method, a `0.0002 mm3` absolute volume ceiling and a `2e-6 mm` bounding-coordinate
ceiling. The volume ceiling rounds the largest observed `0.00012832 mm3` residual
up to the next `0.0001 mm3`; it does not scale with part size. Both directions of
material difference must independently remain below `1e-7 mm3`. These are kernel
diagnostics, not manufacturing allowances. No geometry is healed to force a pass.

The exporter performs these checks before publishing any staged package and
records both original and actual exported per-solid measurements. The reported
component volume retains source geometry semantics; exported volume is a separate
field. Hostile regressions remove/add solids, move parts, move an internal cavity
without changing total volume or outer bounds, and remove `0.000125 mm3` internally.
The latter is smaller than the volume allowance and must still fail the independent
material-difference check. Overlapping development solids preserve multiplicity.

The full exact-source workflow, CAD smoke, generated package verification and
independent review remain required. This correction does not establish product
geometry closure or physical readiness.
