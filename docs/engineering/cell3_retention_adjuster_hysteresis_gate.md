# Cell 3 retention-adjuster hysteresis gate

Status: physical-mechanism sensitivity gate. This document does not establish fit, comfort, durability or usability.

Static travel and pitch are insufficient to close a real retention adjuster. Backlash, tooth clearance, cable seating, compliant take-up and interface settling can create direction-dependent lost motion after the user reverses adjustment direction. A mechanism can therefore expose enough nominal stable positions yet fail to reproduce the same physical fit when approached from opposite directions.

`retention_adjuster_hysteresis.py` adds an explicit reversal gate. Measured lost motion and its uncertainty are combined adversarially. The resulting displacement is converted through retention-member stiffness into a tension deadband, and it is deducted from first-to-last reachable discrete span so endpoint fit coverage cannot rely on motion that disappears after reversal.

This gate complements the existing static, wear and condition-sequence adjuster models. It must eventually consume production-intent bidirectional force/displacement measurements. Thresholds remain validation-gated and must be justified from pressure, migration and human fit evidence rather than selected to make the digital model pass.

## DIGITAL_HANDOFF_DELTA

WEBSITE: a future fit tutorial should show adjustment being finalized from a defined direction if physical validation demonstrates direction-dependent settling. Do not claim precise or repeatable fit from detent count alone.

APP: basic fit remains physical and app-independent. Do not infer strap tension or fit from commanded adjuster position unless production sensing measures the actual mechanical state.

ASSETS/DATA: preserve bidirectional commanded position, actual path-length response, reversal point, measured lost motion, member force/tension, specimen, cycle count and conditioning provenance. Future mechanism animation must not visually imply zero backlash unless released hardware supports it.

CLAIMS: repeatable adjustment, precise fit, retained endpoint coverage and low adjustment hysteresis remain blocked until bidirectional physical measurements close the gate across required conditions and durability states.

BLOCKERS: production-intent bidirectional displacement/force traces, justified lost-motion and tension-deadband limits, wet/cleanser/hair-contaminated and aged measurements, pressure/migration correlation, and untrained fit-adjustment trials.
