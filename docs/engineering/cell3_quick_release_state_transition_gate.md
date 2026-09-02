# Cell 3 quick-release mechanical state-transition gate

Status: digital mechanism preflight only. This does not establish release safety, force, time, usability, collision clearance or durability.

The emergency release now has an explicit physical state-transition gate. A production-intent mechanism must demonstrate `LATCHED -> RELEASING -> RELEASED -> RESET_REQUIRED -> LATCHED` in order. The released state requires physical latch disengagement, and letting go of the grip after release must leave the mechanism non-latched until a deliberate reset action restores engagement. This closes a safety-relevant loophole in which a spring-biased latch could appear to release in a sampled trajectory but automatically re-engage as soon as the user releases the pull feature.

`quick_release_state_machine.py` is intentionally not firmware. It consumes sampled mechanical state evidence and fails closed when the distinct release event, post-release grip-relaxation state, or deliberate reset engagement is absent. Engagement thresholds are screening inputs pending released latch geometry and physical tolerance evidence. Continuous swept-volume collision proof, wet one-hand force/time validation, hair/pinch testing and reset durability remain separate gates.

## DIGITAL_HANDOFF_DELTA

WEBSITE: a future removal explanation must show a mechanically distinct released state and must not animate the mechanism snapping back to latched merely because the user lets go of the release grip. Reset is a separate deliberate physical action.

APP: emergency removal remains independent of power, firmware and app availability. Do not present software confirmation as necessary to achieve or maintain the released state.

ASSETS/DATA: preserve the released physical state sequence, latch engagement versus travel, grip-engaged state, reset trajectory and tolerance provenance. Exact future animation requires the production continuous trajectory, not these sampled state semantics alone.

CLAIMS: self-reset resistance, release distinctness, reset reliability and emergency-removal usability remain blocked as achieved claims. This model is `DIGITAL_SENSITIVITY_ONLY`.

BLOCKERS: production-intent latch engagement geometry and tolerances, continuous release/reset CAD sweep, hard-stop definition, wet one-hand physical trials, grip-release-before-reset trials, repeated reset durability, snag testing, hair/pinch exclusion evidence and mechanically inspectable reset confirmation.
