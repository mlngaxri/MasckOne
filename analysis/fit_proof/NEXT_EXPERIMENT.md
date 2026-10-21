# One experiment: observed seating on an inert adjustable reference

Purpose: replace the missing registered surface, local accommodation and capture
observability inputs with measured, revision-bound data. No person, cleansing
fluid, powered treatment, heater or optical emitter is part of this experiment.
No human-use acceptance threshold is specified.

## Article and configuration

Use one rigid, metrologically registered mounting frame representing the selected
owner's alignment/support locations. Attach removable inert coupons representing
its actual candidate support/seal profiles. Their source IDs and manufactured
revisions must be recorded. If an owner cannot provide a profile and allowed
motion, mark that channel UNKNOWN; do not substitute an arbitrary spring.

Use a replaceable reference surface with the nominal, asymmetry and eye-spacing
witness geometries. These are synthetic bench articles, not anatomically validated
headforms. Provide access from the back for position measurement and removable
markers. Include independent eye, mouth, nasal and off-landmark cheek fiducials.
The measurement frame must not constrain a degree of freedom that is supposed to
be tested for passive acquisition. Any positioning stage must disengage before
an acquisition measurement; otherwise only imposed registration is measured.

## Instrumentation and observations

- A calibrated six-axis positioning reference or independent tracked fiducials
  records initial pose, final pose and the intervening motion.
- Surface metrology records coupon profiles and the full registered surface;
  report point uncertainty and spatial resolution, not only landmark error.
- Displacement probes record local support/seal travel and repeatable seating.
- Force measurement, if used, records the applied bench load and reaction, without
  interpreting either as safe human pressure. Friction and hysteresis are measured,
  never imported as convenient assumed coefficients.
- Independent cameras or probes observe protected-boundary surrogates and false
  seating. Record the contact sequence and any support loss, trapping, or multiple
  terminal states. A contact indicator is not proof of fluid sealing.

First qualify instrument repeatability on a rigid reference and repeated returns
to one imposed pose. Keep calibration, fixture compliance and measurement error
separate from candidate compliance. Then test recorded nominal/asymmetric/spacing
configurations and a small, explicitly listed subset of the campaign's starting
poses. Duplicate placements distinguish systematic false seating from noise.

## Result semantics

**FAIL for the surrogate hypothesis:** independently measured wrong registration,
protected-surrogate contact, loss of a required support, or two different stable
seats despite the same apparently acceptable sparse observables. Record uncertainty
so a near-boundary observation is not called a definite conflict.

**PASS for a qualified bench criterion only:** all required observations exist and
satisfy a criterion established by an identified engineering requirement or a
qualified measurement-method comparison. This is not whole-product or human fit.
No preset percentage of successful starts is invented here.

**INCONCLUSIVE:** missing profile/source identity, unqualified measurement method,
resolution too coarse to separate alternatives, incomplete trajectory, or missing
support/travel observation. An absence of measured collision is not a pass when
measurement coverage is incomplete.

## Data returned to this proof

Supply the surface with coordinate transform and calibration uncertainty; support
locations and measured allowed-travel intervals; observed initial/final trajectories;
contact sequence; repeated terminal-state distributions; and independent sparse
versus full-field errors. Each record names exact article/owner revisions and
measurement method. These are future measured adapters, not controller limits.

This experiment can determine whether sparse datum observability, local differential
accommodation or aperture spacing is the first real limitation. It enables a
comparison of one versus two interface sizes without prematurely adding on-face
adjustment hardware. It does not establish population coverage, comfort, pressure
safety, sealing, emergency human removal, durability or skincare effectiveness.
