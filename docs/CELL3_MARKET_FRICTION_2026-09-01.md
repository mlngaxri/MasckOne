# Cell 3 market-friction evidence, 2026-09-01

Status: public-market observations translated into engineering hypotheses. These observations are not Masck One validation evidence and do not justify copying third-party geometry or mechanisms.

## Evidence sampled

1. CurrentBody Australia Trustpilot, accessed 2026-09-01: recent Series 2 feedback includes a small-face user reporting a roughly 3 cm chin stand-off, unclear strap setup requiring YouTube, and nose discomfort that could be reduced by loosening. Other recent reviews praise simple use, automatic treatment shutoff and good facial contouring. Source: https://au.trustpilot.com/review/currentbody.com.au
2. The Guardian CurrentBody Multi Light Therapy LED mask review, published 2026-07-12: reviewer found straps fiddly and instructions insufficient, noted slight nose pressure/red marking, and found the chin strap impaired flat packing for travel. Source: https://www.theguardian.com/thefilter/2026/jul/12/currentbody-skin-multi-light-therapy-led-mask-review
3. CurrentBody community discussion, 2026-03-04 to 2026-03-05: one report describes unusable identical straps; a reply reports facial marks at nose/upper lip and choosing unstrapped supine use to relieve pressure. Treat as anecdotal hypothesis input only. Source: https://www.reddit.com/r/CurrentBody/comments/1rkzlc7/identical_straps_sent_cant_use_the_mask/
4. FOREO support, accessed 2026-09-01: devices can be used manually after initial setup, without continuing app dependency; cleaning is described as soap/water, rinse, dry. Source: https://www.foreo.com/support/faq/general
5. FOREO LUNA 4 manual, accessed 2026-09-01: explicit physical travel-lock gesture is provided and cleaning is a short direct procedure. Source: https://www.foreo.com/manuals/luna-4
6. Therabody TheraFace Mask Glo manual mirror, accessed 2026-09-01: cleaning is required after each use, the device is not waterproof, USB-C charging is used, and storage/transport conditions are explicit. Source: https://device.report/manual/19462059

## Masck One engineering hypotheses derived from recurring friction

### Fit and retention

H-FIT-01: Retention adjustment must not be the primary compensator for facial geometry mismatch. Tightening a retention system to recover local contact can create pressure hotspots elsewhere. Cell 3 therefore requires retention load-path checks to be evaluated separately from skin-interface conformity.

H-FIT-02: Nose bridge, nose/T-zone, upper-lip/perioral and chin regions are explicit hotspot/stand-off adversarial regions. Any later registered geometry and retention DOE must report contact/clearance behavior at those regions rather than only global fit.

H-FIT-03: Don/doff and adjustment semantics must be understandable without an app or external video. The mechanism contract should converge toward a small number of physically legible adjustment actions and deterministic states.

### Retention architecture

H-RET-01: Retention must tolerate expected fit adjustment without creating an ambiguous half-engaged state. Every retained state needs a deliberate structural load path; every released state needs an unambiguous disengaged condition.

H-RET-02: Strap/component handedness or mating errors should be made difficult by geometry or explicit identity, not left to instruction text. Future retention parts should receive stable IDs and compatibility checks suitable for assembly/service verification.

### Quick release and service

H-QR-01: Quick release remains one-hand, wet, unpowered and firmware-independent. Validation protocol must include wet grip access, pinch/hair hazards, accidental-release resistance and a complete collision-checked trajectory.

H-SVC-01: Service and cleaning burden is a first-class mechanism requirement. Wet-zone parts should expose clear service states and avoid requiring app connectivity merely to clean, dry, remove or reinstall user-serviceable parts.

### Travel and accidental activation

H-TRAVEL-01: Retention and service geometry should be evaluated for storage envelope and snag-prone protrusions. A mechanism that only fits safely when fully assembled on-face is insufficient for a premium portable appliance.

H-STATE-01: Product-state architecture should include a deterministic physical travel/inhibit state or equivalent hardware-level accidental-activation protection. App-only locking is not sufficient.

### Interaction and state clarity

H-STATE-02: Core physical operation must remain intelligible without an app. Web/App may mirror authoritative state but must not become the sole source of readiness, service or release truth.

H-STATE-03: Automatic cycle termination is a useful low-burden pattern, but Masck One must distinguish normal cycle completion, user stop, mechanical/service inhibit and fault termination so consumers cannot display impossible or misleading combinations.

## Required downstream adversarial checks

When controlled geometry and physical inputs become available, Cell 3 should add or consume protocols covering: facial-size/shape retention DOE; nose/upper-lip/chin hotspot and stand-off reporting; retention slip under representative head motion; wet one-hand release; hair/pinch clearance; accidental release; service-state collision; travel/storage envelope; assembly compatibility; cleaning-state accessibility; and physical-control versus app-state reconciliation.

No item above is a PASS claim. It is a dated hypothesis/requirements input for subsequent controlled simulation and bench/human-factors validation.