# Iteration 19 acceptance: actuation parameters and impedance handoff

Iteration 19 binds the CLEAN actuation parameter contract directly to authority revision 2026-08-30-R1 and the released actuator, displacement and coupling architectures.

Digitally controlled values are the 40 Hz CLEAN baseline, 0.52 mm peak-to-peak displacement, 61 degree axis baseline, the authority 50/55/61/67/72 degree angle DOE, and the 0.20 N continuous / 0.60 N transient requirements with their validation-gated meaning preserved.

No frequency DOE is invented because the machine authority supplies only a frequency baseline. The impedance handoff schema explicitly separates PREDICTED records from MEASURED records. Measured records require actual force, displacement and phase observations plus evidence provenance; predicted records are forbidden from carrying measured fields.

This release does not demonstrate actuator force capability, membrane impedance, acoustic behavior, durability or cleansing efficacy. Those remain evidence-gated.
