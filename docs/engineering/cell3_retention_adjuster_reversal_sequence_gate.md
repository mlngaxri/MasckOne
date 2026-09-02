# Cell 3 retention-adjuster reversal-sequence gate

Status: physical-mechanism sensitivity gate. This does not establish fit, comfort, durability or usability.

The static hysteresis gate bounds direction-dependent lost motion at one state. That is insufficient for a repeatedly adjusted wearable because tooth wear, cable seating, compliant take-up and contamination can change reversal behaviour with cycle count. A beginning-of-life and end-of-life pair can also miss an intermediate failure.

`retention_adjuster_reversal_sequence.py` therefore evaluates every cycle-indexed reversal checkpoint. Conservative lost motion is measured lost motion plus uncertainty. Every checkpoint independently gates both geometric lost motion and the resulting tension deadband through retention-member stiffness. The first failing cycle is retained. A zero-cycle baseline and strictly increasing cycle count are mandatory. Apparent improvement in conservative lost motion fails closed rather than being credited as recovery, because irreversible wear or settling evidence requires investigation before a later favourable trace can erase an earlier state.

This is deliberately separate from the existing wear-sequence gate. Endpoint-span wear, pitch drift, anti-backdrive degradation and reversal lost motion are different physical failure modes and must remain independently observable.

## DIGITAL_HANDOFF_DELTA

WEBSITE: do not describe adjustment as repeatable or precise from beginning-of-life fit alone. If physical qualification establishes a required final adjustment direction or take-up action, a future fit tutorial must show it exactly.

APP: no dependency change. Basic fit and emergency removal remain physically operable without app access. Do not display inferred adjuster precision unless production sensing exists.

ASSETS/DATA: preserve cycle-indexed bidirectional displacement traces, reversal direction, effective lost motion, retention tension, specimen, conditioning state and calibration provenance. Do not collapse reversal evidence into a single end-of-life scalar.

CLAIMS: repeatable adjustment, low hysteresis, durable fit precision and lifetime endpoint coverage remain blocked until production-intent conditioned sequences close.

BLOCKERS: cycle-indexed bidirectional traces on production-intent adjusters across dry, wet, cleanser-contaminated, hair-contaminated and aged conditions; physically justified lost-motion and tension-deadband limits; correlation to pressure/migration; untrained fit-adjustment trials; and root-cause disposition of any non-monotonic reversal behaviour.
