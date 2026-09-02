# Cell 3 release force-displacement evidence gate

Status: physical-test gate. No release-force, work, usability or safety claim is established by this document.

A single peak-force number is insufficient evidence for the emergency-release mechanism. A nominally acceptable peak can hide a short force spike, incomplete latch travel, excessive pull work, or a mechanism that reaches maximum force at the end of travel without a mechanically distinct release event.

`quick_release_force_trace.py` therefore consumes measured force-displacement samples and separately gates peak force, achieved travel, post-latch force drop and integrated pull work. Work is integrated trapezoidally in N*mm, numerically equal to mJ. Travel must be strictly monotonic so malformed or reversed traces fail closed. The 5 to 12 N peak corridor remains a validation target. The default 80 mJ work ceiling and 2 N post-latch drop are engineering screening thresholds only and must be replaced or confirmed through physical human-factors evidence before release.

This gate complements, rather than replaces, `quick_release_trials.py`. Trial-level wet, one-hand, unpowered success still governs basic release qualification. Force-displacement traces add mechanism-level evidence about what the user's hand actually experiences through the pull stroke.

## DIGITAL_HANDOFF_DELTA

WEBSITE: do not reduce the release interaction to a claimed force number. Any future explanation should depict one continuous mechanical pull followed by an unambiguous released state, but must not imply validated effort or tactile quality until physical traces and human testing close.

APP: no change to emergency-removal dependency. Release remains mechanically operable without power, firmware or app access. Do not infer latch state from a force trace unless a production sensor exists.

ASSETS/DATA: preserve row-level force-displacement traces with test condition, specimen/cycle identity and calibration provenance. Future exact mechanism animation requires the released physical trajectory and latch transition location, not a generic easing curve.

CLAIMS: peak release force, pull work, tactile release distinctness and completed travel remain blocked as achieved claims until measured traces close the relevant gates across qualifying specimens and conditions.

BLOCKERS: calibrated wet-condition force-displacement traces, production-intent latch travel, specimen and cycle coverage, physically justified work/drop thresholds, continuous tolerance-aware CAD sweep, hair/pinch evidence and untrained one-hand removal trials.
