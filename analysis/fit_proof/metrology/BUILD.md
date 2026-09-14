# Fit metrology test equipment, revision 1

UNPOWERED. OFF FACE. SYNTHETIC REFERENCES, NOT HUMAN HEADFORMS. No treatment.
This package owns test equipment only. PR157 owns contact topology and fluid/film
experiments. Production owner profiles are not manufactured by this generator.

## Architecture and build order

`python -m masck_one.fit_metrology_rig --out generated/fit_metrology`
generates local component STEP, imposed/disengaged assembly STEP, separate
reference-only withdrawal sweeps and a manifest. Use the repository-qualified
Python/CadQuery runtime. `--pose tx ty tz rx ry rz` generates a different indexed
cassette, not a product adjustment. Rotations are extrinsic XYZ, Rz Ry Rx.

1. Fabricate BASE, SURFACE_CARRIER, four SURFACE_POSTs and two retained locating
   pins. BASE top is Z=-100; carrier top Z=-28. Four M5 bolts clamp the surface
   flange through posts; use nuts at the accessible top flange. Two M3 screws
   retain each locating pin's underside flange. Round left pin plus relieved
   right slot avoid redundant lateral locating constraints.
2. Fabricate the pose-specific four INDEXED_LEGs and four ROD_CLAMPs. M5 base
   screws engage the legs' blind pilot sockets after threading; two top M5 screws
   per clamp engage inclined pilots aligned to the cassette. Do not mix legs
   from different pose IDs. Two 8 x 500 mm rods and eight adjustable collars
   establish inner and outer jaw stops. Tighten rod split clamps before indexing.
3. Install JAW_LEFT and JAW_RIGHT on both rods. Nominal jaw centers X=±146;
   acquisition endpoints X=±201, a 55 mm outward travel in cassette-local X.
   Inner collar centers ±132; outer collars ±215. Qualify straightness, parallelism
   and guide drag; the 8.2 mm bore is fixture clearance, not a precision claim.
4. COUPON_HOST sits on three Z pads, two Y datums and one X datum. Four M4 top
   screws, one right-side X screw and one positive-Y screw provide imposed-mode
   seating. Thread the 3.3 mm pilot bores; use nonmarring bench screw tips, record
   the actual hardware. Neither tightening torque nor force is a human limit.
5. Mount three optical target pads with M3 fasteners. Two independent probe posts
   use M5 mounting interfaces. Their targets must remain independent of the pose
   fixture. Attach instruments with qualified adapters matching these interfaces.
6. Install CALIBRATION_INSERT before any candidate coupon or synthetic surface.
   Measure its five target heights and relative coordinates independently; CAD
   dimensions are nominal truth, not an as-built calibration certificate.

All dimensions except the synthetic field and authority coordinate system are
**fixture convenience**. Suggested inspection targets are measurement-method
inputs to be qualified, not fabrication capability or product requirements.
No material stiffness, friction, mass density or manufacturing process is qualified.
Select stable fixture stock, establish its dimensional repeatability, then record
measured density/stiffness only if a criterion consumes them. No adhesive is a
structural constraint in this package.

## Synthetic surfaces

A closed spline-section loft reproduces the existing 2.5D field. Source target
ellipse/cells remain reference domains; the rectangular skirt is fixture support.
Every surface has a common clamped flange and a witness/generator identity.
Scan the installed top surface and datums; the reported interpolation check is
sampled and cannot replace that scan. Protected-boundary analogs are registered
optical overlays from source landmarks/footprints, not anatomical cavities.

Include nominal, chin false-seat, asymmetric, high eye-spacing, and the exact
nearest conditional candidate/nonpassing pair. The last pair differs by only
0.0000458 mm of an input parameter. Preserve both digital identities, but do not
manufacture two supposedly distinguishable articles unless the metrology proves
that distinction. Neither is a qualified human pass/fail surface.

## Imposed mode versus acquisition

Imposed mode is a calibration/measurement state. The three Z, two Y and one X
contacts deliberately locate the host. Acquisition begins only after every clamp
is independently confirmed clear and BOTH jaws reach their outer stops. Withdraw
Z screw tips above local Z=41 and lateral screws clear of the host, then withdraw
jaws. Record the entire release, including possible disturbance. The measured pose
at final fixture disengagement is the initial acquisition pose; the commanded
cassette pose is never substituted for it. Jaw-body continuous translation clears
the rigid host; screws, instruments and owner coupons require separate inspection.

After release the stage contributes zero intended DOFs of constraint. All actual
reaction must come from revision-bound owner coupons. Eight empty two-M3 ports on
the host are **EMPTY/UNKNOWN**, not substitute springs. Do not perform acquisition
with an unsupported host. An independent guard/catcher, if used by the laboratory,
must be outside the observed motion domain; any contact invalidates that run.

No force/friction/capture result follows from the rod stage or CAD. A fixture that
continues to carry reaction cannot be used to demonstrate passive acquisition.
Record remaining constraints, support channels and fixture deflection explicitly.

## Inspection and service

Check all nominal mating planes, rod alignment, endpoint stops, bolt engagement,
probe clearance, target visibility and repeated remove/replace drift. Scan the
actual coupons and record their owner SHA and manufacturing revision. Unload and
remove M3/M5 fasteners for service; no contact profile is bonded permanently into
this rig. Missing coupon geometry is an upstream dependency, not permission to
invent a new production support.
