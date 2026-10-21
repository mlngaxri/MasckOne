# Interaction force-travel metrology

`masck_one.interaction_metrology` accepts separate inward loading and outward
unloading legs. Displacement is non-negative inward travel from a stated datum;
force is the non-negative compressive magnitude on **both** legs. Reverse the
unloading leg internally to integrate its positive work magnitude. The reported
signed hysteresis is loading work minus unloading work; negative values remain
visible for diagnosis. N mm equals mJ. Equal nominal stroke endpoints are required;
sample spacing and sample counts can differ. Dwell and reversal data must be
segmented before analysis.

Each sample carries absolute displacement and force error bounds. Segment work
bounds use the minimum/maximum possible positive segment width multiplied by the
minimum/maximum average endpoint force. Summing these interval bounds is
conservative, including where shared endpoints correlate errors. These bounds
apply to trapezoidal sample work under monotonic underlying legs; they do not
bound unobserved curvature, dynamic response or unsupplied calibration/datum
errors. They are absolute bounds, not statistical confidence intervals.

Windowed least-squares force residual RMS and force gradient expose local changes.
Their meaning depends on sample spacing, window width, noise, loading speed and
intentional snap-through. They have no acceptance threshold and do not establish
perceived smoothness, friction, acoustic quality, wear or fatigue. Provenance must
be explicitly measured or synthetic with source and interaction labels; declaring
measured provenance is caller input, not authentication of the instrument record.

Run the deterministic software comparison with
`PYTHONPATH=src python studies/interaction_metrology_comparison.py`. It compares a
linear stimulus with an invented ripple at the existing primary-control owner's
1.07 mm stroke context. Forces and error bounds are invented test inputs. Owner
candidate in [PR #144](https://github.com/mlngaxri/MasckOne/pull/144), observed
2026-10-15 at short revision `9fb64aa`, explicitly rejects the V11 series
spring force path before dome trip. This is candidate context, not a release
binding or an immutable source pin. This work neither repairs that rejection nor
changes the button, retention, frame or exterior geometry.

## Off-face coupon fixture planning CAD

`masck_one.interaction_coupon_fixture.build_fixture()` returns a pocketed nest,
an explicitly reference-only cylindrical coupon and a separate flat pusher.
The pocket provides coupon location and leaves a floor; a smaller pusher avoids
contacting the pocket walls at the displayed separated starting position. These
parts support planning an independent coupon compression instrument setup, not
mounting a Masck assembly. Dimensions and clearances are unvalidated planning
values. The coupon material, machine coupling, load cell, alignment procedure,
stiffness, operating load, compliance correction and calibration remain undefined.
No printed or machined fixture is qualified by valid solids or volume checks.

Example geometry export in a development environment:

```python
import cadquery as cq
from masck_one.interaction_coupon_fixture import build_fixture
for name, shape in build_fixture().items():
    cq.exporters.export(shape, f"{name}.step")
```

Before collecting physical evidence, define and record the instrument chain,
calibration, fixture compliance, datum, speed, sampling, alignment, uncertainty
budget and repeated specimen protocol. Free return needs a separately recorded
time/displacement series; these quasi-static legs cannot establish return time or
seating stability.
